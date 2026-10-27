# FixLens — submission checklist (due Nov 4, 9:00 PM ET)

Hackathon: Meta Global AI Developer Hackathon, Indie solo track,
theme: Build for Your World. Entrant: Wen Sun (solo).

Status key: ✅ done · ⏳ pending (known work).

Official rules VERIFIED Oct 26 from the Participant Guide (pasted by
Wen from the logged-in event page): public repo required; solo allowed
(max team 4); demo must only highlight features built during the
Hackathon; new work only (all FixLens code in this repo was built Oct
26 onward, during the event — the Oct 24 registration was a concept
only, no code); submission via the CV platform by Nov 4, 9:00 PM ET,
with a THREE-minute demo video (not 60 seconds); judging Stage One is
pass/fail (fits theme + reasonably uses Meta Model API / open-weight
models), Stage Two weights Impact 30% / Meta tooling 25% / Demo 25% /
Technical depth 20%; Indie track prizes: 1st $150K, 2nd $100K, 3rd $75K,
4th $50K, 5th $25K (total Indie $400K of the $1M pool). Workshops: Oct
27 Agents 101, Oct 28 Agents 102, Oct 30 Fireworks/Muse Open; weekday
Discord office hours 10–11 AM ET; judging Nov 5–8; closing Nov 9.

Anti-project risk to avoid: "Simple Image Analyzers" are listed as a
generic anti-project example. FixLens must therefore demo the full
workflow (segment → triage → checklist → parts → ticket), not just
"photo in, label out."

## Checklist

| Item | Status | Notes |
|------|--------|-------|
| Working app, mock end to end | ✅ done | Upload → region → diagnosis → checklist/parts → draft ticket; stdlib only; tests green. |
| Structured diagnosis schema | ✅ done | Fault type, severity + triage reason, cause, safety-first warnings, ordered steps, parts (no prices), difficulty/time estimates, responsibility hint, draft ticket. |
| Mock fault scenarios (≥3) | ✅ done | Leak stain, wall crack, mould spot, + peeling paint; deterministic, keyword/explicit selection. |
| Demo storyboard + judge pitch | ✅ done (updated Oct 26) | See DEMO.md (3-minute video, shot by shot, per official guide). |
| Judge-facing README | ✅ done | Problem/solution/Meta tools (honestly mock-labelled)/run instructions. |
| Public repo | ✅ done | https://github.com/sunwen1983/fixlens — pushes by Mila on Wen's go-ahead (most recently Oct 27, commit 8b66379). |
| Real SAM 3.1 + Muse Spark calls | ✅ wired Oct 26, live verification pending | Provider implemented + canned-response tests green; Mac live test with a real photo is the remaining step. |
| Real fault photos (2–3) | ⏳ pending | Needs Wen's photos; mock demo photo is placeholder only. |
| Ticket wording approval | ⏳ pending | Example property/tenant/landlord placeholders; needs Wen's approval before any ticket text is final. |
| Demo video (3 min, real flow) | ⏳ pending | Record after live verification + real photos, following DEMO.md. A mock-only video risks Stage One failure. |
| Hackathon portal submission | ⏳ pending | Via CV platform by Nov 4, 9:00 PM ET; repo public, video accessible, contributors listed. Never auto-submitted from this repo. |
| Official rules verified | ✅ done Oct 26 | Participant Guide (logged-in page, pasted by Wen): see header above. Pre-work rule: demo must only highlight work built during the Hackathon — FixLens code qualifies (built Oct 26 onward). |
| Submission format | ✅ done Oct 26 | 3-minute video + public repo + submission page fields, per guide. |
| Judging criteria / scoring weights | ✅ done Oct 26 | Stage One pass/fail; Stage Two Impact 30 / Meta tooling 25 / Demo 25 / Tech depth 20. |

## Remaining work

1. Mac live test: run a real fault photo through meta mode and
   confirm the SAM box + Spark diagnosis; fix any retry/parsing
   issue from the raw error.
2. Wen's real fault photos (at least one leak stain, one crack);
   re-run the demo with them.
3. Wen approves ticket wording; record the 3-minute demo video.
4. Submit via the CV platform before Nov 4, 9:00 PM ET (official
   rules + format already verified Oct 26).

## Must NOT be done yet

- No submission to the hackathon portal until live verification +
  demo video are ready and Wen confirms the submission.
- No real tenant/landlord names or addresses in code or docs.
- No contact with anyone, no public post beyond the existing repo.
