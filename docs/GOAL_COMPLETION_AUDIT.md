# Historical examination-fidelity goal audit

Audit date: 2026-09-05, with a 2026-09-06 follow-up. This records the earlier goal of matching 2026 test flow, timing, and current official screens. It is not the completion audit for the later bilingual/open-source documentation work. A working local configuration does not prove all official production rules.

| Earlier requirement | Evidence at the audit | Conclusion |
| --- | --- | --- |
| Use existing personal materials locally, no sales | Healthy local service, SQLite, 393 learning files, eighteen archives, no payments/membership | Implemented local personal use |
| Questions must come from sources | Text, choices, original media, and visuals bound to source/evidence hashes; unsupported scopes disabled | No fabricated items to fill official counts |
| Exact official timing and sequence | Verified Email 7 min, Discussion 10 min, Interview 45 sec; other values from PDF or local defaults; Build 360 sec unverified | Full exact production parity not proved |
| Official interface match | Current Sampler Reading/Listening/Build/Email/Discussion and source PDF layouts observed; no invented listening portraits | Observed layout/behavior reproduced; all production states not proved |
| Local answers, recording, results | SQLite, segmented audio, frozen objective scores, per-section review and self-assessment; restart persistence | Implemented; raw/self scores are not official calibrated scores |
| Mistake review | Wrong → retry correct → mastered → original wrong review retained → restart | Implemented |
| Complete an actual imported archive in browser | Experience 1: nine stages, 79 screens, 97 units, 43 media requests, eleven complete recordings, 68 non-speaking answers, objective 84/84; fifteen terminal checks | Passed for the recorded final build |

The browser run did not speed clocks or skip original media. Normal Next submitted Reading/Listening/Writing early; Speaking used natural recording windows. The microphone was explicitly synthetic, and writing answers were test responses, not official model answers or proof of real speech quality.

The audit reread backend, build, archive, and rule hashes against the recorded reports. The local service then ran on 127.0.0.1:4173. Evidence: `tmp/qa/current-goal-completion-audit.json` and `tmp/qa/final-full-exam-browser/summary.json`. Local `tmp/` evidence is not shipped in a public checkout.

## Missing direct evidence at that time

The Sampler Build task showed no clock; source PDFs showed only remaining time. Rechecking Technical Manual physical pp. 22/30, Specifications p. 6, Teacher Test 1 p. 27, and Writing Lesson Plans pp. 2/4/7 did not establish an initial limit. Classroom exercise duration and estimated whole-section time were not substituted.

The next step was a current official timed reference showing the initial Build clock. At one point the Mac was locked and no attempt was made to bypass it. That was a temporary observation, not a permanent access claim. Tests could not close the evidence gap by assuming six minutes or generalizing partial Sampler behavior.

## Later changes and evidence boundaries

The user subsequently reported cloze overlap. A frontend-only spacing change passed 1280/900/600-pixel browser checks, ten original blank answers saved/scored 10/10, and 79 UI regressions. That frontend was newer than the earlier full-run build; source questions, keys, backend, and timing were unchanged. Evidence: `tmp/qa/cloze-spacing-browser.json`.

The official session later became readable again. Writing expiry and Speaking instructions were observed; v5 implemented the corresponding expiry acknowledgement. On 2026-09-06 the complete original archive passed again with the cloze fix and v5 state, letting Discussion naturally consume all 600 seconds. Final modal CSS was checked independently at wide/narrow viewports; compiled JS was unchanged, with a later backend version-label correction only. The normal service moved to v5 and old sessions retained frozen rules. Build's initial official time remained unverified.
