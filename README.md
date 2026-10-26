# FixLens — hackathon scaffold (MOCK ONLY)

Meta Global AI Developer Hackathon, Indie solo track, Build for Your World.
Entrant: Wen Sun. Builder: Mila (Wen focuses on his Google sprint).

**Do not mistake this for the finished product.** The segmentation and
diagnosis here are fixed mock output so the flow can be demoed and tested
with zero cost. No paid API is called, no key is stored in this repo, and
nothing here has been submitted or published.

## Run it locally

```bash
cd ~/workspace/fixlens
python3 run.py            # or: python3 run.py --port 8000
# open http://127.0.0.1:8000/ and upload any photo
```

Requirements: Python 3.11+ only, standard library only — no pip installs.

Endpoints:

- `GET /` — upload page
- `GET /health` — `{"status": "ok", "provider": "mock"}`
- `POST /api/diagnose` — multipart form, `photo` file field, returns JSON:
  `region` (x/y/width/height fractions + label) and `diagnosis`
  (fault, severity, likely_cause, repair_steps, parts, ticket_draft).

## Run the tests

```bash
cd ~/workspace/fixlens
python3 -m unittest discover -s tests -v
```

The smoke test starts the real HTTP server on an ephemeral port and
drives health → upload page → multipart upload → JSON assertions, plus
a test that the Meta provider stub raises instead of calling anything.

## Files

- `PLAN.md` — one-page plan, demo scope, mock-vs-real, remaining steps.
- `fixlens/providers.py` — provider interface, `MockProvider` (used),
  `MetaModelProvider` (stub: base_url `https://api.meta.ai/v1`, models
  `sam-3.1` and `muse-spark-1.3`; raises, never calls).
- `fixlens/app.py` — stdlib HTTP server + upload page + `/api/diagnose`.
- `run.py` — local entry point.
- `tests/test_smoke.py` — smoke tests (unittest, stdlib only).

## How to swap mock → Meta API later (after credits land, Wen confirms)

1. Wen confirms on dev.meta.ai: $150 credits visible on Billing, a
   payment method on file, Spend Limit notification set.
2. Implement `MetaModelProvider.analyze()` in `fixlens/providers.py`:
   SAM 3.1 for segmentation (image + text prompt → region), Muse Spark
   for diagnosis (photo + region → the exact JSON shape the mock
   already returns). Keep the provider interface unchanged.
3. Change the server to select the provider explicitly (today it
   refuses to start with anything but `mock` — that guard is intentional
   and must be removed deliberately, not accidentally).
4. Re-run the test suite, then re-run the demo with real fault photos.

## Still needed from Wen (before the demo is real)

- 2–3 real sample fault photos (leak stain, crack, etc.).
- Ticket wording approval (names, property address, urgency phrasing).
- Confirmation that credits have landed, before any real API call.
