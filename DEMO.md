# FixLens — 3-minute demo video storyboard

Official requirement (Participant Guide, verified Oct 26): the
submission video is THREE minutes, and it must only highlight
features, code, and functionality built during the Hackathon. The
60-second core below is the spine; the extra beats use the remaining
time to show the full workflow (not just an image analysis) and to
state clearly what was built during the event.

Demo fault (default mock scenario): a ceiling water stain / suspected
leak. One fault, one photo, no extra features. Record in this exact
order; timings add up to 180 seconds.

## Shot by shot

| Time | Shot | What the viewer sees / hears |
|------|------|------------------------------|
| 0–20s | Problem, firsthand | "As a landlord, I get photos like this: 'something is wrong.' Guessing costs days." Show the tenant photo. State: built during this hackathon, solo Indie track, Build for Your World. |
| 20–30s | Photo | "A tenant sends this photo: a stain on the ceiling." Upload the photo. |
| 30–50s | Segmentation overlay | The faulty region is highlighted on the photo with a red box. "FixLens first finds *where* the fault is — SAM 3.1 segmentation — so the diagnosis is grounded in a visible area, not the whole photo." Record this shot with the live Meta API call. |
| 50–80s | Diagnosis card | Fault + severity + triage reason. "Moderate: water damage spreads and can cause mould, but there is no active flooding here." Then the safety box, read first: water near electrics, gas-smell warning. |
| 80–120s | Checklist + parts | Tickable repair steps in order (inspect plumbing above → dry 24–48h → repair source, then patch and repaint) and a parts list with quantities only — no prices. Stress: this is a multi-step workflow ending in action, not a one-label image analysis. |
| 120–160s | Ticket draft | "And one click drafts the repair ticket — property, fault, severity, next steps — marked DRAFT, nothing sent." Show the ticket fields and the DRAFT status. |
| 160–180s | Close | End card: problem, Meta tools used (SAM 3.1 + Muse Spark via Meta Model API), public repo link, and what was built during the hackathon. |

## Narration rules for the recording

- Say the fault, the severity, and the safety warning out loud; do not
  skip the safety box.
- Record with the REAL API calls — a mock-only video risks
  failing Stage One judging (must reasonably use Meta Model API
  and/or Meta open-weight models). Mock mode may be used for
  rehearsal timing only, never for the submitted video.
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
The app runs end to end in mock mode and with the live Meta API
(SAM 3.1 + Muse Spark), stdlib-only Python, tests green.
