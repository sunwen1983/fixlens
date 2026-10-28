"""Provider layer for FixLens.

Design rule: the app never talks to a model directly. It talks to a
provider, and providers are swappable. The mock provider is for local
demo; the Meta Model API provider (SAM 3.1 + Muse Spark) is wired
since credits landed Oct 26, 2026, and reads its key only from the
MODEL_API_KEY environment variable — never from this file or git
history. Keys belong in the Meta account (dev.meta.ai), never here.

Provider interface (what the real integration must implement later):
  segment(image_bytes, prompt) -> Region
      Find the faulty area in the photo. Prompt is a short text hint
      such as "water stain" or "wall crack".
  diagnose(image_bytes, region, notes) -> Diagnosis
      Produce the structured diagnosis for the segmented region.
  analyze(photo_bytes, filename, notes, scenario) -> Analysis
      Convenience wrapper: segment, then diagnose, and bundle both.

No prices appear anywhere in this module. Time/difficulty figures are
ranges explicitly labelled as estimates, and responsibility hints are
hints only — never a legal determination.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, replace

SEVERITIES = ("low", "moderate", "urgent")


@dataclass(frozen=True)
class Region:
    """Faulty area as fractions of image width/height (0.0–1.0)."""

    x: float
    y: float
    width: float
    height: float
    label: str = "faulty area"

    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "label": self.label,
        }

    def is_valid(self) -> bool:
        return (
            0.0 <= self.x < 1.0
            and 0.0 <= self.y < 1.0
            and 0.0 < self.width <= 1.0
            and 0.0 < self.height <= 1.0
            and self.x + self.width <= 1.0
            and self.y + self.height <= 1.0
        )


@dataclass(frozen=True)
class Part:
    item: str
    quantity: str  # e.g. "1", "1 tub" — never a price
    note: str = ""

    def to_dict(self) -> dict:
        return {"item": self.item, "quantity": self.quantity, "note": self.note}


@dataclass(frozen=True)
class Ticket:
    """A repair ticket DRAFT. Nothing here is ever sent automatically.

    All names/addresses are clearly fake example data. The editable
    fields are property, tenant, and landlord; the app may override
    them from the upload form, but status stays "draft".
    """

    title: str
    fault: str
    severity: str
    description: str
    next_steps: list[str] = field(default_factory=list)
    property: str = "Example Property, Unit A"
    tenant: str = "Example Tenant"
    landlord: str = "Example Landlord"
    status: str = "draft"  # draft only — never "sent"

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "fault": self.fault,
            "severity": self.severity,
            "description": self.description,
            "next_steps": list(self.next_steps),
            "property": self.property,
            "tenant": self.tenant,
            "landlord": self.landlord,
            "status": self.status,
        }

    def draft_text(self) -> str:
        # Multi-line: a ticket copied to a landlord/tenant reads far
        # better broken into labeled lines than as one long sentence.
        steps = "\n".join(f"- {s}" for s in self.next_steps) \
            if self.next_steps else "TBD"
        return (
            f"[DRAFT — not sent]\n"
            f"Repair ticket: {self.title}\n"
            f"Property: {self.property}\n"
            f"Fault: {self.fault}\n"
            f"Severity: {self.severity}\n"
            f"{self.description}\n"
            f"Next steps:\n{steps}"
        )


@dataclass(frozen=True)
class Diagnosis:
    fault: str
    fault_type: str  # e.g. "water_leak_stain"
    severity: str  # low | moderate | urgent
    severity_reason: str  # triage reasoning: why this severity
    likely_cause: str
    safety_warnings: list[str] = field(default_factory=list)
    repair_steps: list[str] = field(default_factory=list)
    parts: list[Part] = field(default_factory=list)
    difficulty: str = ""  # easy | moderate | hard (estimate)
    estimated_time: str = ""  # range, labelled as an estimate
    responsibility_hint: str = ""  # hint only, never a legal ruling
    ticket: Ticket | None = None

    def to_dict(self) -> dict:
        ticket = self.ticket.to_dict() if self.ticket else None
        return {
            "fault": self.fault,
            "fault_type": self.fault_type,
            "severity": self.severity,
            "severity_reason": self.severity_reason,
            "likely_cause": self.likely_cause,
            "safety_warnings": list(self.safety_warnings),
            "repair_steps": list(self.repair_steps),
            "parts": [p.to_dict() for p in self.parts],
            "difficulty": self.difficulty,
            "estimated_time": self.estimated_time,
            "responsibility_hint": self.responsibility_hint,
            "ticket": ticket,
            # Backwards-compatible flat draft for older readers.
            "ticket_draft": self.ticket.draft_text() if self.ticket else "",
        }


@dataclass(frozen=True)
class Analysis:
    region: Region
    diagnosis: Diagnosis

    def to_dict(self) -> dict:
        return {"region": self.region.to_dict(),
                "diagnosis": self.diagnosis.to_dict()}


_MOCK_DISCLAIMER = (
    "This is a MOCK diagnosis: verify the cause on site before acting."
)


def _ticket(title: str, fault: str, severity: str, description: str,
            next_steps: list[str]) -> Ticket:
    return Ticket(title=title, fault=fault, severity=severity,
                  description=description, next_steps=next_steps)


# Deterministic mock scenarios. Keyword matching is deliberate: the
# demo can show three-plus distinct faults without any network call.
# The default scenario (no keyword matched) is the leak stain, which
# is also the demo's fault.
_SCENARIOS: dict[str, dict] = {
    "leak": {
        "region": Region(0.25, 0.30, 0.50, 0.40, "water stain (mock region)"),
        "diagnosis": Diagnosis(
            fault="Water stain / suspected leak (MOCK — not a real diagnosis)",
            fault_type="water_leak_stain",
            severity="moderate",
            severity_reason=(
                "Water damage spreads and can cause mould if left, but "
                "there is no sign here of active flooding, so this is "
                "moderate rather than urgent. Active flooding or water "
                "near electrics would raise it to urgent."
            ),
            likely_cause="Possible slow plumbing leak above the stain.",
            safety_warnings=[
                "SAFETY FIRST: if water is near outlets, switches, or "
                "wiring, do not touch wet areas; switch power off at "
                "the breaker only if it is safe to do so.",
                "If you smell gas, leave the property and call "
                "emergency services — do not use electrical switches.",
                _MOCK_DISCLAIMER,
            ],
            repair_steps=[
                "1. Inspect the plumbing directly above the stain.",
                "2. Dry the area and watch 24–48h for growth or change.",
                "3. Repair the source first, then patch and repaint.",
            ],
            parts=[
                Part(item="Pipe sealant / joint tape", quantity="1"),
                Part(item="Patching compound", quantity="1 tub"),
                Part(item="Interior paint (match existing)", quantity="1 quart"),
            ],
            difficulty="moderate",
            estimated_time=(
                "Inspection 30–60 min; drying 24–48 h; repair time "
                "site-dependent (estimates only)"
            ),
            responsibility_hint=(
                "Hint only: plumbing systems are usually the "
                "landlord's responsibility — confirm the source first; "
                "this is not a legal determination."
            ),
            ticket=_ticket(
                "Ceiling water stain — inspect plumbing above",
                "Water stain / suspected leak", "moderate",
                "Tenant reported a ceiling stain. Landlord to inspect "
                "the plumbing above and confirm the source before "
                "scheduling repair.",
                ["Landlord inspects plumbing above the stain.",
                 "Schedule repair once the source is confirmed."],
            ),
        ),
    },
    "crack": {
        "region": Region(0.20, 0.45, 0.60, 0.15, "wall crack (mock region)"),
        "diagnosis": Diagnosis(
            fault="Wall crack (MOCK — not a real diagnosis)",
            fault_type="wall_crack",
            severity="moderate",
            severity_reason=(
                "Most hairline cracks are cosmetic, but a widening, "
                "diagonal, or door/window-sticking crack can signal "
                "movement — only an inspection can tell which, so "
                "this stays moderate until inspected."
            ),
            likely_cause="Possible settlement or plaster shrinkage; "
            "structural movement not ruled out.",
            safety_warnings=[
                "SAFETY FIRST: do not attempt a structural repair "
                "yourself.",
                "If the crack is widening, doors or windows stick, "
                "or there is sagging, get a professional inspection "
                "promptly.",
                _MOCK_DISCLAIMER,
            ],
            repair_steps=[
                "1. Photograph and measure the crack; re-check in 2 weeks.",
                "2. If stable and hairline: fill, sand, and repaint.",
                "3. If widening or structural signs appear: stop and "
                "get a professional inspection.",
            ],
            parts=[
                Part(item="Crack filler", quantity="1 tube"),
                Part(item="Sandpaper (fine grit)", quantity="2 sheets"),
                Part(item="Interior paint (match existing)", quantity="1 quart"),
            ],
            difficulty="easy (cosmetic) — moderate if structural",
            estimated_time=(
                "Cosmetic assessment 30–60 min (estimate); "
                "inspection longer if structural signs appear"
            ),
            responsibility_hint=(
                "Hint only: structural/wall issues are usually the "
                "landlord's responsibility; cosmetic touch-ups vary — "
                "confirm after inspection."
            ),
            ticket=_ticket(
                "Wall crack — measure and monitor, then repair",
                "Wall crack", "moderate",
                "Tenant reported a wall crack. Landlord to measure it "
                "and check for widening or sticking doors/windows "
                "before deciding cosmetic vs professional repair.",
                ["Landlord measures and photographs the crack.",
                 "Re-check in 2 weeks; escalate if widening."],
            ),
        ),
    },
    "mould": {
        "region": Region(0.30, 0.20, 0.40, 0.35, "mould spot (mock region)"),
        "diagnosis": Diagnosis(
            fault="Mould spot (MOCK — not a real diagnosis)",
            fault_type="mould_spot",
            severity="moderate",
            severity_reason=(
                "Mould can affect health and usually signals damp, "
                "so it needs a source check rather than surface "
                "cleaning alone — moderate, rising to urgent if it "
                "is widespread or anyone has breathing problems."
            ),
            likely_cause="Possible damp from a leak or poor ventilation.",
            safety_warnings=[
                "SAFETY FIRST: do not disturb a large mould area "
                "without protection; wear a mask and gloves.",
                "If anyone in the home has breathing problems, seek "
                "advice promptly and ventilate the room.",
                _MOCK_DISCLAIMER,
            ],
            repair_steps=[
                "1. Find and fix the damp source (leak or ventilation).",
                "2. Clean the spot with a mould cleaner; dry fully.",
                "3. Re-check after 2 weeks; if it returns, the source "
                "was not fixed.",
            ],
            parts=[
                Part(item="Mould cleaner", quantity="1 bottle"),
                Part(item="Protective mask and gloves", quantity="1 set"),
                Part(item="Dehumidifier (borrow or hire)", quantity="1"),
            ],
            difficulty="moderate",
            estimated_time=(
                "Cleaning assessment 1–2 h (estimate); fixing the "
                "damp source takes longer"
            ),
            responsibility_hint=(
                "Hint only: often the landlord's if caused by a leak "
                "or structural damp; ventilation-related cases vary — "
                "confirm the cause first."
            ),
            ticket=_ticket(
                "Mould spot — find damp source, then clean",
                "Mould spot", "moderate",
                "Tenant reported a mould spot. Landlord to check for "
                "a leak or ventilation problem before cleaning, so "
                "it does not simply return.",
                ["Landlord checks for leak / ventilation cause.",
                 "Clean and dry once the source is fixed."],
            ),
        ),
    },
    "paint": {
        "region": Region(0.15, 0.35, 0.70, 0.30, "peeling paint (mock region)"),
        "diagnosis": Diagnosis(
            fault="Peeling paint (MOCK — not a real diagnosis)",
            fault_type="peeling_paint",
            severity="low",
            severity_reason=(
                "Peeling paint is usually cosmetic and does not "
                "spread damage quickly — low, unless the peeling "
                "reveals damp or a leak underneath."
            ),
            likely_cause="Possible age, moisture, or poor surface prep.",
            safety_warnings=[
                "SAFETY FIRST: if the paint may be old lead paint, "
                "do not sand or scrape it dry — get advice first.",
                "Check underneath for damp before repainting.",
                _MOCK_DISCLAIMER,
            ],
            repair_steps=[
                "1. Check underneath for damp or a leak.",
                "2. Scrape loose paint, sand smooth, and prime.",
                "3. Repaint with matching interior paint.",
            ],
            parts=[
                Part(item="Scraper and sandpaper", quantity="1 set"),
                Part(item="Primer", quantity="1 quart"),
                Part(item="Interior paint (match existing)", quantity="1 quart"),
            ],
            difficulty="easy",
            estimated_time="Prep + repaint: half a day (estimate)",
            responsibility_hint=(
                "Hint only: cosmetic repainting often falls to the "
                "landlord between tenancies; confirm the arrangement."
            ),
            ticket=_ticket(
                "Peeling paint — check for damp, then repaint",
                "Peeling paint", "low",
                "Tenant reported peeling paint. Landlord to check "
                "underneath for damp, then scrape, prime, and repaint.",
                ["Landlord checks underneath for damp.",
                 "Scrape, prime, and repaint."],
            ),
        ),
    },
}

_KEYWORDS: dict[str, str] = {
    "leak": "leak", "stain": "leak", "water": "leak", "damp": "leak",
    "crack": "crack",
    "mould": "mould", "mold": "mould", "mildew": "mould",
    "paint": "paint", "peel": "paint",
}


def pick_scenario(filename: str = "", notes: str = "",
                  scenario: str = "") -> str:
    """Deterministic scenario selection (mock only).

    An explicit scenario wins; otherwise keywords in the filename or
    notes decide; otherwise the leak stain (the demo fault) is used.
    """
    if scenario and scenario in _SCENARIOS:
        return scenario
    text = f"{filename} {notes}".lower()
    for keyword, name in _KEYWORDS.items():
        if keyword in text:
            return name
    return "leak"


class Provider:
    """Interface the real Meta integration must implement later."""

    def segment(self, _image_bytes: bytes, _prompt: str = "") -> Region:
        raise NotImplementedError

    def diagnose(self, _image_bytes: bytes, _region: Region,
                 _notes: str = "") -> Diagnosis:
        raise NotImplementedError

    def analyze(self, photo_bytes: bytes, filename: str = "",
                notes: str = "", scenario: str = "") -> Analysis:
        region = self.segment(photo_bytes, notes)
        return Analysis(region=region,
                        diagnosis=self.diagnose(photo_bytes, region, notes))


class MockProvider(Provider):
    """Deterministic fake provider for local demo and tests.

    It ignores the photo bytes' content and returns the scenario's
    fixed region + structured diagnosis, so the UI and JSON shape can
    be built and tested with zero API cost. Do not mistake this output
    for a real diagnosis.
    """

    def segment(self, _image_bytes: bytes, prompt: str = "") -> Region:
        name = pick_scenario(notes=prompt)
        return _SCENARIOS[name]["region"]

    def diagnose(self, _image_bytes: bytes, region: Region,
                 notes: str = "") -> Diagnosis:
        # The region label identifies the scenario in mock mode.
        for name, data in _SCENARIOS.items():
            if data["region"].label == region.label:
                return data["diagnosis"]
        return _SCENARIOS["leak"]["diagnosis"]

    def analyze(self, photo_bytes: bytes, filename: str = "",
                notes: str = "", scenario: str = "") -> Analysis:
        if not photo_bytes:
            raise ValueError("photo bytes are empty")
        name = pick_scenario(filename, notes, scenario)
        data = _SCENARIOS[name]
        diagnosis = data["diagnosis"]
        # Notes may override the ticket's editable example fields.
        return Analysis(region=data["region"], diagnosis=diagnosis)


def _media_type(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\x89PNG"):
        return "image/png"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes.startswith(b"GIF8"):
        return "image/gif"
    if image_bytes.startswith(b"RIFF") and b"WEBP" in image_bytes[:12]:
        return "image/webp"
    return "image/jpeg"


def _data_url(image_bytes: bytes) -> str:
    import base64

    return f"data:{_media_type(image_bytes)};base64," + base64.b64encode(
        image_bytes).decode("ascii")


def photo_data_url(image_bytes: bytes) -> str:
    """Public data URL for the uploaded photo (used for the box overlay)."""
    return _data_url(image_bytes)


# SAM output_text grammar (official docs): one line per frame,
# each record = object id + box + mask, box first. Mask payload is
# base85 and may contain "~"/"!" inside, so only the first char after
# "H,W," is the encoding marker.
_SAM_RECORD_RE = re.compile(
    r"(\d+)<\|box;x1=(\d+);y1=(\d+);x2=(\d+);y2=(\d+);w=(\d+);h=(\d+)"
    r"(?:;c=[\d.]+)?\|>"
    r"<\|mask;x=0;y=0(?:;c=[\d.]+)?;data=(\d+),(\d+),([~!])([^|]*)\|>"
)


def parse_sam_output_text(text: str) -> list[dict]:
    """Parse SAM output_text into box+mask records.

    Returns one dict per record: object_id, frame (from the <Nf>
    marker preceding it), pixel box, and raw mask payload. Raises
    ValueError when SAM completed with zero matches.
    """
    records: list[dict] = []
    frame = 0
    # Split on frame markers, keeping each frame's records together.
    for chunk in re.split(r"<(\d+)f>", text or ""):
        if chunk.isdigit():
            frame = int(chunk)
            continue
        for match in _SAM_RECORD_RE.finditer(chunk):
            (obj, x1, y1, x2, y2, w, h, mh, mw, enc, payload) = match.groups()
            records.append({
                "object_id": int(obj), "frame": frame,
                "x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2),
                "w": int(w), "h": int(h),
                "mask_height": int(mh), "mask_width": int(mw),
                "mask_encoding": enc, "mask_payload": payload,
            })
    if not records:
        raise ValueError(
            "No obvious fault found in this photo — please try a "
            "clearer, closer photo of the fault.")
    return records


def _largest_sam_record(records: list[dict]) -> dict:
    """Pick the largest-area SAM box.

    A photo can hold several stains/cracks; the first record is
    arbitrary order, the largest area is the fault the user most
    likely photographed.
    """
    return max(records, key=lambda r: (r["x2"] - r["x1"] + 1)
               * (r["y2"] - r["y1"] + 1))


def _sam_record_to_region(record: dict, label: str) -> Region:
    # x2/y2 are inclusive in SAM's grammar, hence the +1.
    x = record["x1"] / record["w"]
    y = record["y1"] / record["h"]
    width = min(1.0 - x, (record["x2"] - record["x1"] + 1) / record["w"])
    height = min(1.0 - y, (record["y2"] - record["y1"] + 1) / record["h"])
    region = Region(x=x, y=y, width=width, height=height, label=label)
    if not region.is_valid():
        raise ValueError(f"SAM box out of bounds: {record}")
    return region


_CONCEPTS: dict[str, str] = {
    "leak": "water stain", "crack": "wall crack",
    "mould": "mould", "paint": "peeling paint",
}


def concept_for(filename: str = "", notes: str = "",
                scenario: str = "") -> str:
    """Map a fault to the single short noun phrase SAM needs.

    SAM takes exactly one concept per request: lists, commands and
    questions are unreliable per the official docs, so this never
    passes raw user text through as the prompt.
    """
    if scenario and scenario in _CONCEPTS:
        return _CONCEPTS[scenario]
    name = pick_scenario(filename, notes, scenario)
    return _CONCEPTS[name]


def _extract_output_text(response: dict) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]
    texts = []
    for item in response.get("output", []) or []:
        if item.get("type") != "message":
            continue
        for part in item.get("content", []) or []:
            if part.get("type") == "output_text" and part.get("text"):
                texts.append(part["text"])
    return "".join(texts)


_DIAGNOSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "fault": {"type": "string"},
        "fault_type": {"type": "string"},
        "severity": {"type": "string",
                     "enum": ["low", "moderate", "urgent"]},
        "severity_reason": {"type": "string"},
        "likely_cause": {"type": "string"},
        "safety_warnings": {"type": "array", "items": {"type": "string"}},
        "repair_steps": {"type": "array", "items": {"type": "string"}},
        "parts": {"type": "array", "items": {
            "type": "object",
            "properties": {"item": {"type": "string"},
                           "quantity": {"type": "string"},
                           "note": {"type": "string"}},
            "required": ["item", "quantity"],
            "additionalProperties": False}},
        "difficulty": {"type": "string"},
        "estimated_time": {"type": "string"},
        "responsibility_hint": {"type": "string"},
    },
    "required": ["fault", "fault_type", "severity", "severity_reason",
                 "likely_cause", "safety_warnings", "repair_steps",
                 "parts", "difficulty", "estimated_time",
                 "responsibility_hint"],
    "additionalProperties": False,
}


class MetaModelProvider(Provider):
    """Real Meta Model API provider (SAM 3.1 + Muse Spark).

    Verified against the official docs (Oct 26, 2026): both models go
    through POST {base}/responses; SAM's input is one user message
    with input_text = a single short noun phrase plus input_image;
    Spark structured output on Responses uses text.format, NOT
    response_format (that returns 400).

    The key is NEVER in this file: it comes from the MODEL_API_KEY
    environment variable only. No key -> every method raises, so the
    server guard (app.py) can refuse to start in meta mode.
    Mask raster decoding is deliberately left to the official
    meta-sam-parser library in a follow-up: this step uses SAM's box
    (converted to fractional Region coordinates) and keeps the raw
    mask payload on the record for that follow-up.

    Retries: 429 / 5xx / 404 model_not_found (the intermittent cloud
    failure seen in Discord) up to 3 attempts with backoff. 400 is
    never retried: the request itself is wrong.
    """

    BASE_URL = "https://api.meta.ai/v1"
    SEGMENTATION_MODEL = "sam-3.1"
    DIAGNOSIS_MODEL = "muse-spark-1.3"
    _RETRYABLE = {404, 429, 500, 502, 503, 504}

    def __init__(self, api_key: str | None = None,
                 request_fn=None):
        # request_fn(payload) -> response dict: injectable seam so
        # tests can run the full parse path with zero network.
        self.api_key = api_key if api_key is not None else os.environ.get(
            "MODEL_API_KEY", "")
        self._request_fn = request_fn

    def _require_key(self) -> str:
        if not self.api_key:
            raise RuntimeError(
                "MODEL_API_KEY is not set: set it in the environment "
                "before using the Meta provider. The key is never "
                "stored in this repo.")
        return self.api_key

    def _call(self, payload: dict) -> dict:
        if self._request_fn is not None:
            return self._request_fn(payload)
        key = self._require_key()
        data = json.dumps(payload).encode("utf-8")
        last_error: Exception | None = None
        for attempt in range(3):
            req = urllib.request.Request(
                f"{self.BASE_URL}/responses", data=data, method="POST",
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=120) as res:
                    return json.loads(res.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code not in self._RETRYABLE or attempt == 2:
                    raise RuntimeError(
                        f"Meta Model API error {exc.code}: "
                        f"{exc.read().decode('utf-8', 'replace')[:3000]}"
                    ) from exc
                time.sleep(0.5 * (2 ** attempt))
        raise RuntimeError(f"Meta Model API call failed: {last_error}")

    def _sam_region(self, image_bytes: bytes, concept: str) -> Region:
        """SAM box for a concept, with one broader-concept retry.

        If the specific concept (e.g. "water stain") matches nothing,
        retry once with "damage" before giving up: a live demo should
        not die on the first photo. If both match nothing, the
        friendly zero-match error surfaces (never a bare 400).
        """
        attempts = [concept] + ([] if concept == "damage" else ["damage"])
        for attempt in attempts:
            payload = {
                "model": self.SEGMENTATION_MODEL,
                "input": [{
                    "type": "message", "role": "user",
                    "content": [
                        {"type": "input_text", "text": attempt},
                        {"type": "input_image",
                         "image_url": _data_url(image_bytes)},
                    ],
                }],
            }
            text = _extract_output_text(self._call(payload))
            try:
                records = parse_sam_output_text(text)
            except ValueError:
                continue
            record = _largest_sam_record(records)
            return _sam_record_to_region(record, f"{attempt} (SAM region)")
        raise ValueError(
            "No obvious fault found in this photo — please try a "
            "clearer, closer photo of the fault.")

    def segment(self, image_bytes: bytes, prompt: str = "") -> Region:
        if not image_bytes:
            raise ValueError("photo bytes are empty")
        self._require_key()
        concept = concept_for(notes=prompt)
        return self._sam_region(image_bytes, concept)

    def diagnose(self, image_bytes: bytes, region: Region,
                 notes: str = "") -> Diagnosis:
        if not image_bytes:
            raise ValueError("photo bytes are empty")
        self._require_key()
        prompt = (
            "You are a home-repair triage assistant. Look at the photo "
            "and the segmented faulty region "
            f"(x={region.x:.2f}, y={region.y:.2f}, "
            f"width={region.width:.2f}, height={region.height:.2f}, "
            f"label={region.label}). User notes: {notes or 'none'}. "
            "Return a structured diagnosis: fault type, severity with "
            "a reason, likely cause, safety warnings FIRST (water "
            "near electrics, gas smell, structural risk, lead paint), "
            "ordered repair steps, and a parts list with QUANTITIES "
            "ONLY — never prices, never currency amounts. Difficulty "
            "and time must be labelled estimates. The landlord/tenant "
            "responsibility field is a hint only, never a legal ruling."
        )
        payload = {
            "model": self.DIAGNOSIS_MODEL,
            "input": [{
                "type": "message", "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image",
                     "image_url": _data_url(image_bytes)},
                ],
            }],
            "text": {"format": {
                "type": "json_schema",
                "name": "FixLensDiagnosis",
                "schema": _DIAGNOSIS_SCHEMA}},
        }
        text = _extract_output_text(self._call(payload))
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Muse Spark returned non-JSON structured output") from exc
        if raw.get("severity") not in SEVERITIES:
            raise RuntimeError(
                f"Muse Spark returned invalid severity: {raw.get('severity')!r}")
        parts = [Part(item=p.get("item", ""), quantity=p.get("quantity", ""),
                      note=p.get("note", ""))
                 for p in raw.get("parts", [])]
        ticket = _ticket(
            f"{raw['fault']} — repair",
            raw["fault"], raw["severity"],
            f"Likely cause: {raw['likely_cause']}",
            list(raw["repair_steps"][:2]),
        )
        return Diagnosis(
            fault=raw["fault"], fault_type=raw["fault_type"],
            severity=raw["severity"],
            severity_reason=raw["severity_reason"],
            likely_cause=raw["likely_cause"],
            safety_warnings=list(raw["safety_warnings"]),
            repair_steps=list(raw["repair_steps"]),
            parts=parts, difficulty=raw["difficulty"],
            estimated_time=raw["estimated_time"],
            responsibility_hint=raw["responsibility_hint"],
            ticket=ticket,
        )

    def analyze(self, photo_bytes: bytes, filename: str = "",
                notes: str = "", scenario: str = "") -> Analysis:
        if not photo_bytes:
            raise ValueError("photo bytes are empty")
        self._require_key()
        # Concept must come from scenario/filename/notes, not from
        # segment()'s prompt-only mapping, so pass it explicitly.
        concept = concept_for(filename, notes, scenario)
        region = self._sam_region(photo_bytes, concept)
        return Analysis(region=region,
                        diagnosis=self.diagnose(photo_bytes, region, notes))


def get_provider(name: str = "mock"):
    """Return a provider by name. Only 'mock' is usable today."""
    if name == "mock":
        return MockProvider()
    if name == "meta":
        # Returned, not called: the app must refuse to serve with it
        # (see app.py) rather than attempt a real API call.
        return MetaModelProvider()
    raise ValueError(f"unknown provider: {name!r}")


def with_ticket_overrides(diagnosis: Diagnosis, fields: dict) -> Diagnosis:
    """Override a ticket's editable example fields; status stays draft."""
    if diagnosis.ticket is None:
        return diagnosis
    overrides = {}
    for key in ("property", "tenant", "landlord"):
        value = (fields.get(key) or "").strip()
        if value:
            overrides[key] = value
    if not overrides:
        return diagnosis
    return replace(diagnosis, ticket=replace(diagnosis.ticket, **overrides))
