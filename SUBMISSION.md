# FixLens — submission checklist (due Nov 4, 9:00 PM ET)

Hackathon: Meta Global AI Developer Hackathon, Indie solo track,
theme: Build for Your World. Entrant: Wen Sun (solo).

Status key: ✅ done · ⏳ pending (known work) · ❓ TBD — depends on
the official rules / submission format, which have NOT been verified
from an official source yet. Nothing in this file claims an official
scoring rule; third-party scoring summaries are NOT treated as official.

## Checklist

| Item | Status | Notes |
|------|--------|-------|
| Working app, mock end to end | ✅ done | Upload → region → diagnosis → checklist/parts → draft ticket; stdlib only; tests green. |
| Structured diagnosis schema | ✅ done | Fault type, severity + triage reason, cause, safety-first warnings, ordered steps, parts (no prices), difficulty/time estimates, responsibility hint, draft ticket. |
| Mock fault scenarios (≥3) | ✅ done | Leak stain, wall crack, mould spot, + peeling paint; deterministic, keyword/explicit selection. |
| Demo storyboard + judge pitch | ✅ done | See DEMO.md (60s, shot by shot). |
| Judge-facing README | ✅ done | Problem/solution/Meta tools (honestly mock-labelled)/run instructions. |
| Public repo | ✅ done (by parent, not this task) | https://github.com/sunwen1983/fixlens — do NOT push again from this task. |
| Real SAM 3.1 + Muse Spark calls | ⏳ pending | Blocked on credits: implement behind the existing provider interface once Wen confirms credits on Billing + card + Spend Limit. |
| Real fault photos (2–3) | ⏳ pending | Needs Wen's photos; mock demo photo is placeholder only. |
| Ticket wording approval | ⏳ pending | Example property/tenant/landlord placeholders; needs Wen's approval before any ticket text is final. |
| Demo video (60s, real flow) | ⏳ pending | Record after real API wiring + real photos, following DEMO.md. |
| Hackathon portal submission | ⏳ pending | Submission step itself is Wen/Mila's later decision — never auto-submitted from this repo. |
| Official rules verified (pre-work / existing code / AI-tool clauses) | ❓ TBD | Must be checked against the official rules once they are published/accessible; the mock build makes no claim about them. |
| Submission format (video length, repo link, description fields) | ❓ TBD | Same as above — verify from the official portal/rules, not from third-party summaries. |
| Judging criteria / scoring weights | ❓ TBD | Not claimed here. Do not cite third-party percentages as official. |

## Remaining work once credits arrive (~Oct 28, 2 business days)

1. Wen confirms: $150 credits visible on Billing, payment method on
   file, Spend Limit notification set.
2. Wire `MetaModelProvider.segment()` + `.diagnose()`; keep the exact
   JSON shape the mock returns; remove the mock-only server guard
   deliberately; re-run all tests.
3. Replace mock photos with Wen's real fault photos; re-run the demo.
4. Wen approves ticket wording; record the 60s demo video.
5. Verify the official rules + submission format, then submit via the
   portal before Nov 4, 9:00 PM ET.

## Must NOT be done yet (from this task)

- No submission to the hackathon portal.
- No push to GitHub (parent reviews and pushes).
- No paid API calls, no API key creation/storage.
- No contact with anyone, no public post beyond the existing repo.
- No real tenant/landlord names or addresses in code or docs.
