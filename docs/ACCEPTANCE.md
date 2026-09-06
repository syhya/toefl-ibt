# Local application acceptance record

English | [简体中文](ACCEPTANCE.zh-CN.md)

## Bilingual and open-source onboarding verification — 2026-09-06

The current update was verified against both the installed private collection and a separate public-only copy without original PDFs, generated private exams, or private curation manifests.

| Check | Current result |
| --- | --- |
| English/Chinese interface | 101 UI tests passed, including live switches without losing answers, editor history, settings, ratings, countdowns, or recording state |
| API and resource import | 185 backend/security checks passed in the working project; portable JSON validation, local media, idempotent import, revision updates, and preserved old assets covered |
| Existing source collection | 28 data/import checks passed; all 18 runtime source gates passed, with 1,518 structured screens and 14 strict-capable archives |
| Public-only installation | `./scripts/install.sh`, `npm ci`, tests, and production build passed without private learning resources |
| Public-only tests | 290 checks passed; 24 checks requiring private source data skipped as expected (one backend, 23 source-data checks) |
| Bilingual documentation | 46 paired Markdown files and 267 repository links passed the checker; all 44 in-app document endpoints returned readable content |
| Browser onboarding | English default, Chinese switch, demo import, reading choices/cloze entry, saved 3/3 review, and restart recovery verified in isolated storage |
| Documentation reader | English/Chinese formatted import guides, code blocks, local document navigation, language persistence, and safe Markdown rendering verified |
| Existing user data | Online SQLite backup taken; all 19 stored session JSON records were identical immediately after the service restart |

Production frontend builds successfully; the Markdown renderer is loaded separately when documentation opens. Local evidence is retained in `tmp/qa/bilingual-release/verification.json` and `output/playwright/bilingual-import-guide-*.png`. These checks do not repeat the historical full-length microphone examination below. CI is configured in the repository; no remote CI run or public release is claimed.

Historical examination verification updated 2026-09-06, for `2026-09-05-client-expiry-v5`. This record distinguishes automatic regression, actual browser observations, explicitly synthetic microphone input, and remaining real-device work. Earlier reports prove their recorded revisions only. The bilingual/open-source update has separate current evidence; the private counts here are not bundled public content.

## Dated delivered scope

- React/TypeScript/Vite, FastAPI/SQLite, isolated installation, and macOS launcher; local answers, source playback, recording, and review without cloud AI or account/payment features.
- Reading → Listening → Writing → Speaking, server deadlines/expiry, navigation limits, one-time source playback, separate writing windows, automatic recording stop, and interruption recovery. Source Begin stages and within-section audio continuation retain their own timing.
- Private collection: 393 resources (56 PDFs, 319 audio, eighteen video), plus three system files; eighteen archives (fifteen iBT, three Essentials), 1,815 units / 1,518 screens / 1,608 unique questions, fourteen strict-eligible. Original 321 resources unchanged; 72 matching teacher audio files added without new questions.
- All 1,518 screens source-structured. Essential visuals: 469 crops / 742 references, including eighty Build screens / 160 portrait occurrences and eighteen Discussion tasks / 54 portraits. Full-question evidence: 1,084 review-only crop references.
- Cross-session mistakes, frozen objective scores, selected-scope section results, and separate subjective self-assessment. Unreliable keys excluded, no simulated official writing/speaking grading.
- Strict active/review/source/other-session separation, source gates over originals, ten curation files, and 1,886 derived hashes. No claimed ETS lockdown, proctoring, or proprietary adaptation.

## Checks and their exact scope

| Check | Recorded result and boundary |
| --- | --- |
| Historical `npm test` | Types passed; 80 UI + 146 backend/security + 28 data/import = 254, no private-data skips. `tmp/qa/client-expiry-v5-tests.log` records that snapshot. |
| Earlier complete browser archive, before cloze spacing fix | Experience 1: nine stages / 79 screens / 97 units; 1,157.197 natural seconds with ordinary early Next; 43 normal-speed original media plays totaling 499.376664 seconds; 68 non-speaking answers, objective 84/84, eleven auto-stopped downloadable/decodable recordings. Real token reorder, Email Back retention, restart answers/scores/audio, fifteen terminal checks passed. Synthetic microphone and test essays. `tmp/qa/full-exam-fontfix-before-20260905-223242-26d5fa71/report/summary.json`. |
| Later v5 full flow and writing expiry | Same complete archive in 1,793.006 seconds; 43 media plays / 499.376664 seconds, eleven complete playable recordings, objective 84/84. Discussion naturally exhausted 600 seconds, became read-only expired, Continue entered Speaking. Restart preserved three record classes; seventeen terminal checks. Final modal CSS checked separately at 1280/600, JS byte-identical; backend then changed version label only, with 146 regressions. `tmp/qa/final-full-exam-browser/summary.json`, `tmp/qa/writing-expiry-visual/summary.json`. |
| Production build | TypeScript/Vite passed for the recorded build; screenshots must identify that build rather than an old fixture. |
| Source gates | Eighteen archives, 393 learning files, ten manifests, 1,886 derived hashes passed; not all passing sources are complete strict exams. |
| Source/import | Traceable text/options/tokens/keys/pages/assets, no inventory placeholders; changed-PDF cache invalidation, column source binding, and repeat import checked. [DATA_QA.md](DATA_QA.md). |
| Original directions | Thirty-three Pack/Paid modules preserve rules/scenarios; 44 WAV directions for 22 modules / thirteen groups. Independent PCM/source checks excluded duplicate titles, a misclassified lecture, and one unstable interval. Text remains where reliable audio is absent. Seventeen scopes / 439 response screens replayed; directions do not consume answer time. |
| Short-response Listening UI | Fourteen checks passed on the recorded latest build: two original directions/stimulus play normally; original options disabled during playback with portrait/position; unanswered Next does not reset the 20-second deadline; completion freezes accepted answer. `tmp/qa/final-listening-ui.json`. |
| Cloze spacing | Font, spacing, baseline, whole-word wrapping, inside focus outline, and separate marks fixed prefix overlap. 1280/900/600 geometry/input/delete/Tab checks, ten original blanks saved/scored 10/10, 79 UI checks/build passed. This later UI patch did not change source/rules; earlier full-run screenshots do not prove it. `tmp/qa/cloze-spacing-browser.json`. |
| Reading instruction content | Six notices and three ads had body/title merged into Read instructions; display extraction preserves the remaining original text and does not truncate Essentials instructions. UI regression passed. |
| Current Sampler comparison | Welcome, volume, three reading tasks, listening short response/conversation/talk playback, Build, Email/Discussion observed. Reading/Listening/Build lacked visible clocks; Email 06:56 and Discussion 09:34 were remaining values. Email Time Remaining keeps counting with Back/Continue. Sampler counts are not production counts. No assistant-recorded human voice. |
| Font/canvas | Public CSS directly confirms Open Sans and 1024 width. 768 height is derived from structure and supported by 4:3 observation. Local fonts/license saved; no universal scaling/font claim. |
| Student notice browser | Student 1 Q11/Q12 title/subtitle/body/Next/Back passed. `tmp/qa/final-reading-build-ui.json` covers notices only, not unexecuted drag/email tests. |
| Native Chrome drag/drop | Actual token-to-slot and placed-token reordering passed. Click/keyboard/duplicate/fixed/extra cases have separate regression coverage. |
| Recording/media chain | Three rounds of seven repeats plus four interviews, original-speed media and natural response windows, explicit synthetic input. Automatic start/stop, segment upload, finalization, playback/completeness passed; one used v4. Not a real microphone test. |
| Original video final frame | One original Interview MP4 played once; response PNG matched the video's source frame byte-for-byte; natural 45-second stop and 44.997-second playable recording with no interruption. Change-of-question clearing has separate UI coverage. `tmp/qa/final-video-frame-ui.json` predates later Listening changes. |
| Score history | New completion freezes objective snapshot/results/engine/time; restart/future code does not rewrite it. Late audio and valid zero self-score stay separate; legacy without snapshot is marked recomputed. |
| Mistakes/section summaries | Actual answered scoreable errors only, later mastery and last-error review retained, source/key versions distinct; separate objective denominator and self-assessed count/mean. |
| Mistake browser loop | Original wrong 0/1 → UI retry correct 1/1 → mastered → old wrong zero-score review; two snapshots survive isolated restart. `tmp/qa/final-persistence-ui.json`. |
| Isolation/recovery | Expired/late/current-question/idempotent requests, background intervals, unskippable audio, duplicate tabs, offline upload retries, changed sources, and old history covered. |
| Installation/service history | Install script previously ran successfully, including AES PDF dependencies; no full reinstall was performed merely for that documentation update. `npm start` served 4173, health/home/current JS/CSS 200, eighteen archives/fourteen strict. Old 4177/4178 test services stopped. `tmp/qa/final-launch.json`. |

## Earlier long run and revision limits

An earlier Experience 1 HTTP/server run lasted 4,127.039 seconds, with nine stages, fifty expiry advances, 43 media reads, five image reads, and zero errors. It was not browser playback or a real microphone test and predates source gates, v4 flow, scoring, and UI changes. Some earlier evidence used hard-linked derived files rather than fully frozen copies; the reports disclose this. Do not rewrite historical observations or call them proof of later features.

## Real devices and unpublished rules

1. Grant this local app actual microphone permission, check real levels, record your own response, and verify playback/download. Permission/calibration in ETS does not validate this app, and synthetic input does not validate voice quality.
2. Complete browser/restart acceptance passed for the recorded final build. Physical sleep/network loss and voice quality remain separate scenarios; automated deadline/offline recovery checks are not a real-device long run.
3. Build's initial six minutes remains a local default without direct official confirmation. Proprietary selection, calibration, equating, subjective grading, and official score conversion remain outside local proof. Layout follows observed Sampler/PDF states, not unseen universal production parity.

## Local evidence locations

- Final full run: `tmp/qa/final-full-exam-browser/{summary,progress,review,playback}.json`; earlier discovery in `tmp/qa/full-exam-discovery-20260905/`.
- Historical complete logs: `tmp/qa/final-test-output.log`, `client-expiry-v5-ui.log` (80), `client-expiry-v5-final-api.log` (146), and 28 data checks in `client-expiry-v5-tests.log`. A version-contract check ties backend version to `shared/rules.json`.
- UI screenshots: `output/playwright/official-*.png`, some predating font/canvas/directions/final-frame changes; see [EXAM_UI_REFERENCE.md](EXAM_UI_REFERENCE.md).
- Speaking: `tmp/qa/recording-finalize-report.json`, `2026-09-05-speaking-final-review.json`, `2026-09-05-source-ui-speaking.json` and corresponding telemetry/review records.
- Source/directions: `tmp/qa/teacher-audio-migration-20260905/`, `build-source-visuals-20260905/`, `daily-source-visuals-20260905/`, `pack-directions-audit-20260905/`. QA did not overwrite source materials or real user answers.
- Historical server/routes: `tmp/qa/realtime-report.json`, `browser-flow-report.json`, `reading-upper-report.json`, `listening-upper-report.json`, `real-catalog-ui-report.json`.

Private/local QA evidence is not shipped in a clean public checkout. New validation for bilingual onboarding must be recorded separately rather than inheriting these historical results. Tool instructions: [TESTING.md](TESTING.md). Rule evidence: [OFFICIAL_RULES.md](OFFICIAL_RULES.md), [independent verification](ets-2026-verification.md).
