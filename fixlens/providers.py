"""Provider layer for FixLens.

Design rule: the app never talks to a model directly. It talks to a
provider, and providers are swappable. Today only the mock provider is
usable. The Meta Model API provider is a clearly-marked stub: it holds
no key, reads no key, and raises instead of calling anything, because
credits are still pending and no key has been configured.

Do NOT add a real API key to this file, to any file in this repo, or to
git history. Keys belong in the Meta account (dev.meta.ai), never here.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Region:
    """Faulty area as fractions of image width/height (0.0–1.0)."""

    x: float
    y: float
    width: float
    height: float
    label: str = "faulty area"


@dataclass(frozen=True)
class Part:
    item: str
    quantity: str
    note: str = ""


@dataclass(frozen=True)
class Diagnosis:
    fault: str
    severity: str  # low | moderate | urgent
    likely_cause: str
    repair_steps: list[str] = field(default_factory=list)
    parts: list[Part] = field(default_factory=list)
    ticket_draft: str = ""


@dataclass(frozen=True)
class Analysis:
    region: Region
    diagnosis: Diagnosis

    def to_dict(self) -> dict:
        return {
            "region": {
                "x": self.region.x,
                "y": self.region.y,
                "width": self.region.width,
                "height": self.region.height,
                "label": self.region.label,
            },
            "diagnosis": {
                "fault": self.diagnosis.fault,
                "severity": self.diagnosis.severity,
                "likely_cause": self.diagnosis.likely_cause,
                "repair_steps": list(self.diagnosis.repair_steps),
                "parts": [
                    {"item": p.item, "quantity": p.quantity, "note": p.note}
                    for p in self.diagnosis.parts
                ],
                "ticket_draft": self.diagnosis.ticket_draft,
            },
        }


class MockProvider:
    """Deterministic fake provider for local demo and tests.

    It ignores the photo bytes and always returns the same plausible
    analysis, so the UI and JSON shape can be built and tested with
    zero API cost. Replace the demo photo later; do not mistake this
    output for a real diagnosis.
    """

    def analyze(self, _photo_bytes: bytes, _filename: str = "") -> Analysis:
        return Analysis(
            region=Region(x=0.25, y=0.30, width=0.50, height=0.40,
                          label="water stain (mock region)"),
            diagnosis=Diagnosis(
                fault="Water stain / suspected leak (MOCK — not a real diagnosis)",
                severity="moderate",
                likely_cause="Possible slow plumbing leak above the stain "
                "(MOCK — verify on site before acting).",
                repair_steps=[
                    "1. (MOCK) Check the plumbing directly above the stain.",
                    "2. (MOCK) Dry the area and watch 24h for growth/change.",
                    "3. (MOCK) Repair the source, then patch and repaint.",
                ],
                parts=[
                    Part(item="Pipe sealant / joint tape", quantity="1"),
                    Part(item="Patching compound", quantity="1 tub"),
                    Part(item="Interior paint (match existing)", quantity="1 quart"),
                ],
                ticket_draft=(
                    "[DRAFT — MOCK] Repair ticket: water stain on ceiling. "
                    "Severity: moderate. Next step: landlord to inspect the "
                    "plumbing above and confirm the source before scheduling "
                    "repair. (Tenant/landlord names and property address to "
                    "be filled in by Wen before any real ticket is used.)"
                ),
            ),
        )


class MetaModelProvider:
    """STUB — intended Meta Model API integration. NOT wired.

    Intended endpoints (for later, after credits land and Wen confirms):
      base_url: https://api.meta.ai/v1
      segmentation model: sam-3.1
      diagnosis model: muse-spark-1.3

    This class deliberately has no api_key attribute, reads no
    environment variable, and its analyze() raises. That way no code
    path in this scaffold can accidentally spend credits or call a
    paid API. Wiring it is a separate, explicitly-approved step.
    """

    BASE_URL = "https://api.meta.ai/v1"
    SEGMENTATION_MODEL = "sam-3.1"
    DIAGNOSIS_MODEL = "muse-spark-1.3"

    def analyze(self, _photo_bytes: bytes, _filename: str = "") -> Analysis:
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
