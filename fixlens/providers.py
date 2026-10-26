"""Provider layer for FixLens.

Design rule: the app never talks to a model directly. It talks to a
provider, and providers are swappable. Today only the mock provider is
usable. The Meta Model API provider is a clearly-marked stub: it holds
no key, reads no key, and raises instead of calling anything, because
credits are still pending and no key has been configured.

Do NOT add a real API key to this file, to any file in this repo, or to
git history. Keys belong in the Meta account (dev.meta.ai), never here.

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
        steps = "; ".join(self.next_steps) if self.next_steps else "TBD"
        return (
            f"[DRAFT — not sent] Repair ticket: {self.title}. "
            f"Property: {self.property}. Fault: {self.fault}. "
            f"Severity: {self.severity}. {self.description} "
            f"Next steps: {steps}."
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
# is also the 60-second demo's fault.
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


class MetaModelProvider(Provider):
    """STUB — intended Meta Model API integration. NOT wired.

    Intended endpoints (for later, after credits land and Wen confirms):
      base_url: https://api.meta.ai/v1
      segmentation model: sam-3.1
      diagnosis model: muse-spark-1.3

    This class deliberately has no api_key attribute, reads no
    environment variable, and every method raises. That way no code
    path in this scaffold can accidentally spend credits or call a
    paid API. Wiring it is a separate, explicitly-approved step.
    """

    BASE_URL = "https://api.meta.ai/v1"
    SEGMENTATION_MODEL = "sam-3.1"
    DIAGNOSIS_MODEL = "muse-spark-1.3"

    def segment(self, _image_bytes: bytes, _prompt: str = "") -> Region:
        raise RuntimeError(
            "Meta Model API provider is NOT wired: no key is configured "
            "and credits are still pending. Use MockProvider."
        )

    def diagnose(self, _image_bytes: bytes, _region: Region,
                 _notes: str = "") -> Diagnosis:
        raise RuntimeError(
            "Meta Model API provider is NOT wired: no key is configured "
            "and credits are still pending. Use MockProvider."
        )

    def analyze(self, _photo_bytes: bytes, _filename: str = "",
                _notes: str = "", _scenario: str = "") -> Analysis:
        raise RuntimeError(
            "Meta Model API provider is NOT wired: no key is configured "
            "and credits are still pending. Use MockProvider. Do not call "
            "this provider until credits are confirmed and Wen approves."
        )


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
