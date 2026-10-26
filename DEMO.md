# FixLens — 60-second demo storyboard

Demo fault (default mock scenario): a ceiling water stain / suspected
leak. One fault, one photo, no extra features. Record in this exact
order; timings add up to 60 seconds.

## Shot by shot

| Time | Shot | What the viewer sees / hears |
|------|------|------------------------------|
| 0–5s | Photo | "A tenant sends this photo: a stain on the ceiling." Upload the photo. |
| 5–15s | Segmentation overlay | The faulty region is highlighted on the photo. "FixLens first finds *where* the fault is — SAM 3.1 segmentation — so the diagnosis is grounded in a visible area, not the whole photo." (In the current mock build, this region is fixed demo output; the real SAM 3.1 call replaces it once credits land.) |
| 15–30s | Diagnosis card | Fault + severity + triage reason. "Moderate: water damage spreads and can cause mould, but there is no active flooding here." Then the safety box, read first: water near electrics, gas-smell warning. |
| 30–45s | Checklist + parts | Tickable repair steps in order (inspect plumbing above → dry 24–48h → repair source, then patch and repaint) and a parts list with quantities only — no prices. |
| 45–60s | Ticket draft | "And one click drafts the repair ticket — property, fault, severity, next steps — marked DRAFT, nothing sent." End card: problem, Meta tools, repo link. |

## Narration rules for the recording

- Say the fault, the severity, and the safety warning out loud; do not
  skip the safety box.
- Say "mock" once, honestly, when the segmentation overlay appears:
  the flow is real, the model output in this build is mock until the
  Meta Model API calls are wired (credits pending).
- Do not claim a price, a guaranteed repair time, or a legal ruling
  on landlord vs tenant responsibility. Times are estimates; the
  responsibility line is a hint only.

## One-paragraph pitch (for judges)

FixLens solves a problem its builder knows firsthand as a landlord: a
tenant sends a blurry photo of "something wrong" and the landlord has
to guess what it is, how urgent it is, what parts to buy, and how to
write it up. FixLens turns that photo into a grounded diagnosis — SAM
3.1 segments the faulty area, Muse Spark reasons over the photo and
the region to produce a severity-triaged diagnosis, an ordered repair
checklist, a parts list, and a draft landlord–tenant repair ticket.
Today the app runs end to end in mock mode (stdlib-only Python, zero
cost, tests green); the provider interface is built so the real SAM
3.1 and Muse Spark calls slot in unchanged once the $150 Meta Model
API credits land.
