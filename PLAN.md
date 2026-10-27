# FixLens — one-page plan

Meta Global AI Developer Hackathon, Indie solo track, theme: Build for Your World.
Entrant: Wen Sun (landlord; this is a problem he knows firsthand).
Built during the hackathon. Submission due Nov 4, 9:00 PM ET.
Status: Meta provider WIRED (credits landed Oct 26, 2026; key from
env only). Live verification with a real photo is still pending;
nothing has been submitted yet.

## The problem (one sentence)
A tenant sends a blurry photo of "something wrong" and the landlord has to
guess what it is, how urgent it is, what parts to buy, and how to write it
up — FixLens turns that photo into a diagnosis, a repair checklist, a parts
list, and a landlord–tenant repair ticket.

## User flow
1. Photo — user uploads a photo of a home fault (leak stain, crack,
   peeling paint, mould spot, broken fixture).
2. Segmentation — SAM 3.1 segments the faulty area and returns a region
   (mask / bounding box) so the diagnosis is grounded in a visible area,
   not just "the whole photo".
3. Diagnosis — Muse Spark reads the photo + the segmented region and
   returns structured output: fault type, severity, likely cause,
   repair steps, parts list, estimated effort.
4. Checklist + parts — the app renders a repair checklist and a parts
   list the landlord can actually shop from.
5. Ticket — the app drafts a landlord–tenant repair ticket (what, where,
   how urgent, what happens next) ready to send.

## Scope for the demo video
Show exactly one fault, end to end, in this order:
photo upload (5s) → highlighted faulty region (10s) → diagnosis card:
fault + severity (15s) → repair checklist + parts list (15s) →
generated ticket draft (15s). One fault, one photo, no extra features.
Anything else (multi-photo, history, tenant messaging, cost estimates)
is explicitly OUT of scope for the demo.

## What is mock vs real in this build
- MOCK (works today, no API): `MockProvider` returns a deterministic
  region + extended structured diagnosis for one of four scenarios
  (water stain/leak, wall crack, mould spot, peeling paint), picked
  by an explicit form choice or by filename/notes keywords. The
  upload page renders the photo with a red-box overlay, safety
  warnings first, then diagnosis, checklist, parts (quantities only,
  no prices), and a DRAFT ticket with editable example fields. The
  JSON shape, the rendering, and the tests all run against this mock.
- REAL (wired Oct 26, 2026, after credits landed): `MetaModelProvider`
  in `fixlens/providers.py` calls the Meta Model API: base_url
  `https://api.meta.ai/v1`, models `muse-spark-1.3` (diagnosis) and
  `sam-3.1` (segmentation, largest-area box). It holds no key and
  reads it only from the `MODEL_API_KEY` environment variable. Live
  verification with a real photo is still pending; canned-response
  tests cover parsing, structured output, and retries.

## Remaining steps
1. Mac live test: run a real fault photo through meta mode
   (`FIXLENS_PROVIDER=meta`, key in env only) and confirm the SAM
   box and Spark diagnosis come back; fix any retry/parsing issue
   from the raw error.
2. Replace the mock demo photo with Wen's real sample fault photos
   (at least one leak stain and one crack) and re-run the demo.
3. Wen approves the ticket wording (landlord/tenant names, address,
   urgency language) before any ticket text is shown as final.
4. Record a real 3-minute demo video following the script in DEMO.md.
5. Submit via the hackathon portal before Nov 4, 9:00 PM ET — that
   submission step is Wen's/Mila's later decision, not part of this
   build.

## What Wen still needs to supply
- Mac live-test result (pass, or the raw error).
- 2–3 real sample fault photos (leak stain, crack, etc.).
- Ticket wording approval (names, property address, how urgency is phrased).
