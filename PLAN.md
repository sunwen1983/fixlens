# FixLens — one-page plan

Meta Global AI Developer Hackathon, Indie solo track, theme: Build for Your World.
Entrant: Wen Sun (landlord; this is a problem he knows firsthand).
Build period: Oct 26 – Nov 4, 2026. Submission due Nov 4, 9:00 PM ET.
Status of this scaffold: MOCK-ONLY. No paid API has been called, no key is
stored anywhere, and nothing has been submitted or published.

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

## Scope for a 60-second demo
Show exactly one fault, end to end, in this order:
photo upload (5s) → highlighted faulty region (10s) → diagnosis card:
fault + severity (15s) → repair checklist + parts list (15s) →
generated ticket draft (15s). One fault, one photo, no extra features.
Anything else (multi-photo, history, tenant messaging, cost estimates)
is explicitly OUT of scope for the demo.

## What is mock vs real in this scaffold
- MOCK (works today, no API): `MockProvider` returns a fixed region and
  a fixed structured diagnosis for any uploaded photo. The upload page,
  the JSON shape, the checklist/parts/ticket rendering, and the tests
  all run against this mock.
- REAL (stub only, NOT wired, NOT called): `MetaModelProvider` in
  `fixlens/providers.py` records the intended integration only:
  base_url `https://api.meta.ai/v1`, models `muse-spark-1.3`
  (diagnosis) and `sam-3.1` (segmentation). It holds no key, reads no
  key from disk, and raises instead of calling anything. Tests assert
  that it raises. Do not wire it until credits arrive AND Wen confirms.

## Remaining steps once credits arrive (~Oct 28, 2 business days)
1. Wen confirms on his own account: $150 credits visible on the Billing
   page, a payment method on file, and a Spend Limit notification set.
2. Swap the provider: implement SAM 3.1 segmentation (image + text prompt
   → mask/box) and Muse Spark structured diagnosis (photo + region →
   fault/severity/steps/parts/ticket fields) behind the provider
   interface, keeping the exact JSON shape the mock already returns.
3. Replace the mock demo photo with Wen's real sample fault photos
   (at least one leak stain and one crack) and re-run the demo.
4. Wen approves the ticket wording (landlord/tenant names, address,
   urgency language) before any ticket text is shown as final.
5. Record a real 60-second demo video following the script above.
6. Submit via the hackathon portal before Nov 4, 9:00 PM ET — that
   submission step is Wen's/Mila's later decision, not part of this
   scaffold.

## What Wen still needs to supply
- 2–3 real sample fault photos (leak stain, crack, etc.).
- Ticket wording approval (names, property address, how urgency is phrased).
- Confirmation that credits have landed (Billing page) before any real
  API call is made.
