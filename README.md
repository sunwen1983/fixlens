# FixLens — photograph a home fault, get a diagnosis and a repair ticket

**60-second version for judges.** A tenant sends a blurry photo of
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
or let the filename/notes pick it.

## Meta tools used — honestly labelled

- **SAM 3.1** (segmentation) and **Muse Spark 1.3** (diagnosis) are
  the intended Meta Model API models (`https://api.meta.ai/v1`).
- **Today they are NOT live calls.** This build runs in mock mode:
  the provider interface (`segment` → region, `diagnose` → structured
  JSON) is real and tested, but the model outputs are fixed demo
  data. No paid API has been called, no key is stored anywhere, and
  the Meta provider stub raises instead of calling — tests assert
  that. The real calls slot into the same interface once the $150
  Meta Model API credits land and Wen confirms.
- Why Meta tools matter here: SAM grounds the diagnosis in a visible
  region instead of the whole photo, and Muse Spark turns that region
  plus the photo into structured, triaged reasoning — not free text.

## Run it locally (60 seconds)

```bash
cd fixlens
python3 run.py            # http://127.0.0.1:8000/ — upload any photo
python3 -m unittest discover -s tests -v   # full test suite
```

Requirements: Python 3.11+, standard library only — no pip installs.
Endpoints: `GET /` (upload page), `GET /health`,
`POST /api/diagnose` (multipart `photo` + optional `scenario`,
`notes`, `property`, `tenant`, `landlord`).

## Project structure

- `PLAN.md` — one-page plan, demo scope, mock-vs-real, remaining steps.
- `DEMO.md` — 60-second demo storyboard + one-paragraph judge pitch.
- `SUBMISSION.md` — submission checklist for Nov 4, 9:00 PM ET.
- `fixlens/providers.py` — provider interface, `MockProvider`
  (4 deterministic scenarios), `MetaModelProvider` (stub, raises).
- `fixlens/app.py` — stdlib HTTP server, upload page with rendered
  safety-first result, validation (empty/missing/oversize uploads).
- `run.py` — local entry point (mock only; refuses other providers).
- `tests/test_smoke.py` — HTTP smoke tests: schema fields, all mock
  scenarios, validation errors, mock-only guard, stub refusal.

## How to swap mock → Meta API later (after credits land, Wen confirms)

1. Wen confirms on dev.meta.ai: $150 credits visible on Billing, a
   payment method on file, Spend Limit notification set.
2. Implement `MetaModelProvider.segment()` (SAM 3.1: image + prompt →
   region) and `.diagnose()` (Muse Spark: photo + region → the exact
   JSON shape the mock already returns).
3. Remove the server's mock-only guard deliberately (it refuses any
   other provider today by design).
4. Re-run the test suite, then re-run the demo with real fault photos.

## Still needed before the demo is real

- 2–3 real sample fault photos (leak stain, crack, etc.).
- Ticket wording approval (example names/address are placeholders).
- Confirmation that credits have landed, before any real API call.
- Official hackathon rules / submission format — see SUBMISSION.md
  (marked TBD until the official rules are verified; nothing here
  claims an official scoring rule).
