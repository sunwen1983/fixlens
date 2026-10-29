# FixLens — photograph a home fault, get a diagnosis and a repair ticket

**Judge version.** A tenant sends a blurry photo of
"something wrong." FixLens finds *where* the fault is, says *what* it
is and *how urgent* it is, and drafts what to do next: an ordered
repair checklist, a parts list (quantities only, no prices), and a
landlord–tenant repair ticket marked DRAFT — nothing is ever sent
automatically.

## The problem

As a landlord, Wen Sun gets photos like this from tenants and has to
guess: what is it, how urgent is it, what parts do I buy, and how do
I write it up? FixLens turns that one photo into an answer.

## The solution (what works today)

1. **Photo** — upload a photo of a home fault.
2. **Segmentation** — the faulty area is highlighted on the photo.
3. **Diagnosis** — fault type, severity *with triage reasoning*,
   likely cause, safety warnings shown first (water / electrical /
   gas-adjacent faults), repair steps in order, parts list,
   difficulty and estimated time (ranges, labelled estimates), and a
   landlord-vs-tenant responsibility *hint* (never a legal ruling).
4. **Ticket** — a draft ticket with editable example fields
   (property / tenant / landlord) and status `draft`.

Four deterministic mock faults are built in: water stain / leak, wall
crack, mould spot, and peeling paint — pick one in the upload form
or let the filename/notes pick it. In meta mode the region comes
from SAM 3.1 instead, and the upload page renders the photo itself
with the region drawn on it: a red box plus, when the optional
parser is installed, a translucent red pixel mask inside the box —
the segmentation is visible, not just a line of text.

## How it works (pipeline)

One photo flows through two Meta models, each doing the job the
other cannot:

1. **Concept** — the fault is mapped to a single short noun phrase
   ("water stain", "wall crack", …). SAM takes exactly one concept
   per request, so raw user text is never passed through as the
   prompt.
2. **Segment (SAM 3.1)** — SAM returns a pixel box plus a pixel
   mask for the concept. The largest-area box wins (a photo can
   hold several stains/cracks); on zero matches it retries once
   with the broader concept "damage", then fails with a friendly
   message instead of a bare error.
3. **Mask overlay** — the mask payload is decoded with Meta's
   official `meta-sam-parser` (optional, zero-dependency itself)
   and rendered as a semi-transparent red PNG inside the box by a
   pure-stdlib encoder. Without the parser, or on any decode
   failure, the page degrades to box-only — a mask problem never
   breaks a diagnosis.
4. **Diagnose (Muse Spark 1.3)** — Spark receives the photo plus
   the segmented region and returns structured output
   (`text.format` JSON schema): fault type, severity *with a
   reason*, likely cause, safety warnings first, ordered repair
   steps, parts with quantities only (never prices), difficulty
   and time as labelled estimates, and a responsibility hint.
   Severity is validated against the allowed set; the ticket is
   always `draft`.
5. **Ticket** — the result page shows the photo with its overlay,
   the safety-first diagnosis, and an editable ticket draft with a
   copy button. Nothing is ever sent automatically.

Why two models and not one: a single image model would diagnose
the whole photo without grounding — the "simple image analyzer"
failure mode. SAM answers *where* (a visible region the user can
check), Spark answers *what, how urgent, and what next* (structured
reasoning about that region). The grounding is what makes the
diagnosis checkable.

## Verified on (real numbers, no invented metrics)

- 4 mock scenarios (water stain, wall crack, mould, peeling
  paint): full flow end to end, deterministic outputs.
- 1 real photo (ceiling water stain, Oct 27–28, 2026): real SAM
  3.1 + real Muse Spark end to end, in-page rendering. The SAM
  box hugged the stain, and the pixel mask highlighted the stain
  itself inside the box (verified on a Mac, Oct 28). Total API
  cost for the real-photo run: ~$0.01 (SAM per image + Spark
  tokens).
- No other real photos have been run yet — the demo video will
  use real home/rental fault photos, not web images.

## Meta tools used — honestly labelled

- **SAM 3.1** (segmentation) and **Muse Spark 1.3** (diagnosis) run
  through the Meta Model API (`https://api.meta.ai/v1`).
- **The Meta provider is wired, not a stub.** Credits ($150) landed
  Oct 26, 2026; `MetaModelProvider` implements SAM (single short noun
  phrase per request, pixel box converted to fractional coordinates,
  largest-area box wins) and Spark (structured output via
  `text.format`, severity validated, ticket always draft, parts
  quantities only). The key comes only from the `MODEL_API_KEY`
  environment variable — never from code or git history — and the
  server refuses to start in meta mode without it.
- **Live verification is done.** The wired provider passed a real
  end-to-end run Oct 27, 2026 (real SAM 3.1 + Muse Spark on a
  ceiling water-stain photo, ~$0.01 charged, in-page rendering),
  and the pixel-mask overlay was verified on a Mac Oct 28 (mask
  hugs the stain inside the box). The suite is 41 tests,
  including an official-encoder round-trip for mask decoding.
- Mock mode is still available (`FIXLENS_PROVIDER` unset = mock):
  the provider interface (`segment` → region, `diagnose` → structured
  JSON) is shared, but mock outputs are fixed demo data. No key is
  stored anywhere in either mode.
- Why Meta tools matter here: SAM grounds the diagnosis in a visible
  region instead of the whole photo, and Muse Spark turns that region
  plus the photo into structured, triaged reasoning — not free text.

## Run it locally

```bash
cd fixlens
python3 run.py            # http://127.0.0.1:8000/ — upload any photo
FIXLENS_PROVIDER=meta MODEL_API_KEY=<your key> python3 run.py
                          # same page, live SAM + Muse Spark (key in env only)
python3 -m unittest discover -s tests -v   # full test suite
```

Requirements: Python 3.11+, standard library only — no pip installs,
except one optional package for the pixel-mask overlay (below).

Mask overlay (optional): with Meta's official parser installed, the
photo also gets a pixel-level SAM mask highlight inside the red box:

```bash
pip install "meta-sam-parser==0.1.0"   # zero-dependency itself
```

Without it, the app still works exactly as before — red box only.
The mask is decoded with Meta's own parser (never hand-rolled), and
any decode failure degrades to box-only rather than breaking the
diagnosis.
Endpoints: `GET /` (upload page), `GET /health`,
`POST /api/diagnose` (multipart `photo` + optional `scenario`,
`notes`, `property`, `tenant`, `landlord`).

## Project structure

- `PLAN.md` — one-page plan, demo scope, mock-vs-real, remaining steps.
- `DEMO.md` — 3-minute demo storyboard + one-paragraph judge pitch.
- `SUBMISSION.md` — submission checklist for Nov 4, 9:00 PM ET.
- `fixlens/providers.py` — provider interface, `MockProvider`
  (4 deterministic scenarios), `MetaModelProvider` (wired: SAM 3.1 +
  Muse Spark via the Meta Model API, key from env only).
- `fixlens/app.py` — stdlib HTTP server, upload page with the photo
  + red-box region overlay and safety-first result, validation
  (empty/missing/oversize uploads).
- `run.py` — local entry point (mock by default; meta mode requires
  `FIXLENS_PROVIDER=meta` + `MODEL_API_KEY`, otherwise refuses to start).
- `tests/test_smoke.py` — HTTP smoke tests: schema fields, all mock
  scenarios, validation errors, photo data URL for the overlay.
- `tests/test_meta_provider.py` — canned-response tests: SAM parsing
  (largest box wins, friendly zero-match message), Spark
  `text.format`, 404 retry / no retry on 400.

## Meta mode today (wired Oct 26, 2026, after credits landed)

1. Credits confirmed on dev.meta.ai: $150 visible on Billing, a
   payment method on file, Spend Limit notification set — done by
   Wen on his own account.
2. `MetaModelProvider.segment()` (SAM 3.1: image + short concept →
   largest-area region) and `.diagnose()` (Muse Spark: photo + region
   → the exact JSON shape the mock already returns) are implemented
   and tested with canned responses.
3. Live verification (done Oct 27 late): a real fault photo ran
   through meta mode and the box + diagnosis came back, in-page
   rendering, ~$0.01 charged — before recording the demo video.

## Still needed before the demo is real

- Mac live-test result for meta mode: DONE Oct 27 late (real
  SAM 3.1 + Muse Spark end-to-end, in-page rendering).
- 2–3 real sample fault photos (leak stain, crack, etc.) — still
  needed; web photos were live-test only, video must use real faults.
- Ticket wording: DONE — wording delegated to Mila Oct 27, content
  unchanged, reformatted to labeled multi-line (example
  names/address remain placeholders).
- Official hackathon rules / submission format — see SUBMISSION.md
  (verified against the official participant guide Oct 26, 2026).
