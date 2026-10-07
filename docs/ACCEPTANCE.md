# Local application acceptance record

## Current version verification: v0.1.1 — 2026-10-07

Package metadata and the lockfile identify **v0.1.1**. The timing, fixed-route, item-count and source-correction updates below are included in this local version commit; a Git tag or remote release has not been published.

- Fresh required checks passed: **744 tests** (213 UI, 492 API/security, 39 data/import) and **5,004 recovered-data subtests**. Twenty-five historical/optional tests were skipped. Type checking, production build, documentation links and whitespace checks passed.
- Private source files, generated question banks/proofs, test logs and personal storage remain excluded from Git. The installed correction is checked locally; it is not distributed as a new public question package.
- This packaging check did not repeat the October 4 browser walkthrough. Its observations and remaining source/timing limitations are recorded below. Logs for the current validation are in `tmp/qa/version-0.1.1/`.

## Timing and data audit: 2026-10-04

The [collection timing audit](OFFICIAL_RULES.md#collection-timing-audit-2026-10-04) covers every installed iBT arrangement and both Paid 1 routes. New strict sessions freeze v9; legacy sessions keep their existing clocks and content.

- **744 tests passed**: 213 UI, 492 API/security and 39 data/import, plus **5,004 recovered-data subtests**. Twenty-five historical/optional checks were skipped. Production build, documentation links and whitespace checks passed.
- All 18 runtime source-integrity gates passed. Question counts remain 1,811 items / 1,514 screens. Paid 1 Reading Q24's truncated option and wrong supplied key were corrected against the matching complete Pack question; previous originals and proof remain intact. Unique content now totals 1,640 units, with 17 unresolved scoring units excluded.
- Tests cover current timers on all installed routes, strict exclusion of browser custom timing, actual guided Reading overrides, post-audio windows, unchanged source data, preserved old sessions, unavailable fixed branches and cloze item/screen counts.
- A real-browser check used Pack 1 strict Reading in an isolated preview: both English and Chinese direction pages show 15:00, the countdown begins at Begin, and Next/Back retain the running clock. No browser errors/warnings were captured. This was not a timed full examination or microphone test.
- Known original gaps remain: Paid 2 Build questions 7–10, Essentials 2's two absent speaking prompts, and the Experience 2 listening text/audio mismatch. Their existing strict/availability restrictions remain in place. Passing structural and hash checks does not claim every original answer is correct.

Local timing test logs and screenshot are under `tmp/qa/full-catalog-preview-timing-20261004/`. The additive source correction and replay script are under `generated/recovery/2026-10-04/`. Personal session/recording storage was not used for tests.

## Previous working-tree verification: 2026-09-29

The [private source reconstruction](SOURCE_RECOVERY.md) restores 18 archives, 1,514 screens and 1,811 archival items from 393 original files. The public Practice Test 1 v3 file remains unchanged.

- **686 tests passed**: 213 UI, 453 API/security and 20 data/import, plus **5,004 recovered-data subtests**. Twenty-five checks requiring the older, deleted private curation or paper edition were skipped; the new recovered snapshot has separate source/proof, layout, media and grading tests. Type checking, production build, documentation and whitespace checks passed.
- All 18 source-integrity gates passed. Nineteen isolated complete API paths cover every archive and both Paid 1 branches with synthetic responses and recording takes. No personal sessions were used.
- Thirteen archives have complete local strict scopes. Experience 2 Listening has a paper/audio omission; Paid 2 Writing lacks four original Build items. Those incomplete scopes remain unavailable for strict practice. Essentials remains untimed, and 18 unresolved scoring units remain unscored.
- Recovery checks preserve the installed public sample's bytes and existing storage. Audio/paper differences are disclosed in review. The portable Essentials decoder uses the project-bundled FFmpeg without altering original audio files.

This is source reconstruction and local protocol validation, not official ETS scoring or a fresh human-microphone/browser run. Browser automation could not complete its security-policy check. Local evidence is in `tmp/recovery-v1/` and the installed immutable proofs in `generated/recovery/2026-09-28/`.

## Earlier bilingual-explanation verification: 2026-09-27

The application version is **0.1.0**. This record describes the dated local checks below; see the [changelog](../CHANGELOG.md) for release history. All 79 current Practice Test 1 screens and the retained paper Interview 1 now have English and Simplified Chinese explanations selected by the interface language.

- **701 checks passed**: 212 UI, 454 API/security, and 35 data/import. Type checking, production build, documentation links, and whitespace checks passed.
- Both explanation manifests cover the same 80 question fingerprints and preserve reference keys, reference sentences, all 20 cloze fragments, distractor coverage, and correction notices. Regressions cover immediate language switching, mismatched translations, immutable saved answers/scores, authorized guided feedback, and strict-session isolation.
- A fresh minimal-package browser check confirmed English and Chinese bodies, distractor reasons, authorship labels, and warning notices for the seminar and shopping questions. The browser console reported no errors or warnings. Screenshots are in `output/playwright/explanation-en.png` and `output/playwright/explanation-zh-CN.png`; isolated sample data is in `tmp/qa/bilingual-explanations/`.

This update does not change dependencies, grading keys, session timing, source media, or the bundled example payload. The preceding September 26 walkthrough below remains the evidence for complete exam and recording flow; it was not repeated for this localization change.

## Earlier English-explanation verification: 2026-09-26

The current example is **Practice Test 1 · Audio edition**, lightweight profile v3: 97 items / 79 screens, nine stages, and 57 required payload files totaling **18,326,505 bytes**. All four sections have eligible local strict practice. The first Interview prompt intentionally follows the supplied original audio, whose wording matches ETS Test Overview page 19, while preserving the different paper prompt in review. No synthetic prompt or examiner video is claimed.

- **693 checks passed**: 210 UI, 448 API/security, 35 data/import; production build and documentation checks passed. The preceding dependency audit reported zero npm vulnerabilities and no Python dependency conflicts; this update changes no dependencies.
- The [Practice Test 1 explanation audit](TEXT_FIDELITY.md#practice-test-1-explanation-audit-2026-09-26) covers all 79 screens / 97 items and retains all current grading keys. Every screen has source-bound English guidance, with a separate note for the legacy paper Interview 1. Both installed editions matched all 79 corresponding notes. A fresh minimal-package browser check confirmed seminar and shopping rationales, English content under Chinese controls, and removal of stale companion-conflict text, with no console errors. Regression checks preserve stored answers and frozen scores and withhold notes when the question/key changes.
- A clean minimal install completed all 79 screens in an API walkthrough: 84/84 objective units and eleven playable synthetic recording takes. Original files and the private source collection were absent.
- Browser checks reproduced the sentence-builder cross-question gap-index defect before the fix, then verified that the next question starts at gap 1 while earlier answers remain saved. Original Interview 1 audio decoded and played to its 15.94-second end without a media error. Review distinguishes original prompts from response recordings and discloses the audio/paper variants.
- Upgrade regressions cover explicit v2→v3 installation, unchanged old session bodies and source audio, new post-audio 45-second Interview windows, no active transcript leakage, and rollback after a post-publication validation failure. Private imported archives are not replaced.
- All eighteen private source-integrity gates passed. Of 192 sentence-building questions, 150 have explicit verified token orders; all 150 now reconstruct to an accepted answer. The detected fixed-literal punctuation discrepancy in Pack 3 is handled without accepting wrong words/order or changing frozen score snapshots. The other 42 questions were not part of this token-order check. All 33 cloze screens' verified reference units also passed.

This does not claim a fresh human-microphone end-to-end run: recording behavior was checked with mocks and explicit synthetic test audio. Browser playback and source integrity do not prove universal production-ETS timing, every source word's transcription, or official scoring. General audit logs are under `tmp/qa/current-version-audit/`; the current explanation audit and test/build logs are under `tmp/qa/example1-explanations/`.

## Earlier balanced-reading verification: 2026-09-26

v8 uses the user-selected balanced Reading preset: **15:00 + 15:00 = 30:00** for the fixed sample's two 20-item modules. This replaces the v7 21:00/09:00 preset without claiming official module timing. Source-specific durations and frozen sessions remain unchanged; default browser profiles migrate while explicit custom settings are retained.

- **663 checks passed**: 204 UI, 424 API/security, 35 data/import, plus type checking and production build.
- Regression checks cover both 15-minute module clocks, their 30-minute sum, old session deadlines, migration from both earlier default profiles, and preservation of deliberately saved custom allocations.
- Local logs: `tmp/qa/balanced-reading/`.

## Earlier reading-layout verification: 2026-09-26

The [reading layout audit](TEXT_FIDELITY.md#reading-layout-audit-2026-09-26) restores verified paragraph and line boundaries in 23 emails and two academic passages, covering 73 associated screens. The source-specific display projection does not mutate source files, saved plans, answers, timers or scores; original same-line signatures are retained.

- **659 checks passed**: 200 UI, 424 API/security, 35 data/import; type checking and production build passed.
- A fresh minimal-package browser run confirmed the workshop email's salutation, body, closing and sender in separate paragraphs, and the longer invitation's body paragraphs and two-line signature. The fix also works in existing-session review without optional original PDFs.
- Local logs and source comparisons: `tmp/qa/reading-layout/`. This is a text-flow audit, not a new claim of complete source-frame or typography parity.

## Earlier Reading-profile verification: 2026-09-26

v7 replaces the 20:30 default Reading budget with a **21:00 + 09:00 = 30:00** practice profile based on ETS blueprint estimates. It is still labelled as a local allocation, not an official initial clock for the 40-item paper. The unchanged legacy browser preset upgrades, while custom settings, source-specific durations and saved plans retain their values.

- **649 checks passed**: 200 UI, 414 API/security, 35 data/import, plus type checking and production build.
- An isolated minimal-package browser run showed Module 1 at 21:00, kept its running deadline through navigation to the last screen, and then showed Module 2 at 09:00 without carrying unused time across. API tests cover expiry, untimed Begin screens and old v6 Reading deadlines.
- Local logs: `tmp/qa/reading-profile/`. The sample content and payload files are unchanged.

## Earlier timing audit verification: 2026-09-26

The [Practice Test 1 timing audit](OFFICIAL_RULES.md#practice-test-1-timing-audit-2026-09-26) rechecked official sources and separated verified deadlines from local presets. v6 fixes filtered repeat timing, isolates the unmatched Interview prompt instead of removing all Interview timers, and displays timing evidence on start pages. Source questions, bundle payload, strict eligibility, and saved-session plans are unchanged.

- **644 checks passed**: 196 UI, 413 API/security, 35 data/import; type checking and production build passed.
- New minimal install verified in an isolated browser: English and Chinese timing notices render correctly. Repeat source positions, shared clocks, post-audio deadlines, mixed timed/untimed Interview flow, old frozen sessions and all 79 prepared question screens passed API regression checks.
- Exact Reading/Listening deadlines, the sentence-building starting value, and the exact seven-repeat sequence are still not established for this paper. No official full-test timing equivalence is claimed.

Logs are under `tmp/qa/example1-timing/`. The minimal-package and earlier full-source results below remain evidence for their own revisions, not additional fresh-environment claims for v6.

## Earlier minimal-package verification: 2026-09-26

The then-current default was the **runtime-only** Practice Test 1 package: 56 required payload files, 17,818,617 bytes (about 17.8 MB), with all 13 original PDFs/full MP3s excluded from Git. No original-source `data/` folder, private curation set, or external material download was needed for the fresh installation. Dependencies were reused from the local development environment; this is not a fresh dependency-download or remote Linux-CI claim.

- Full local suite: **632 passed** (193 UI, 404 backend/security, 35 data/import), plus type checking and production build.
- Published-file-only checkout: **607 passed, 25 private-dependent checks skipped**; first `npm run demo` copied 55 files and merged the catalog, and the second call reused the installation without copying files.
- Complete four-section API walkthrough: all **79 screens / 97 items**, 68 saved non-speaking responses, **84/84 objective units**, and eleven complete, playable recording takes. This uses an explicit test clock and synthetic one-second WAV recordings; it is not a natural full-length test, real microphone check, or assessment of speech quality.
- Browser check on the isolated new installation: sample visible, strict Reading opens at 11:30, source text and missing-letter input render and save, Tab navigation works, and no console error was observed.
- Integrity regression: missing/corrupt required media, altered provenance, mismatched source descriptors, false profile markers, and present-but-corrupt originals fail. Omitted originals are reported as not reverified; the prepared assets remain hash-checked. Private archives retain full-source checks.
- Source limits remain: first Interview prompt has unmatched paper/audio versions; full-test and Speaking strict mode stay disabled. Other supported sections retain their timers.

Local logs and evidence are under `tmp/qa/minimal-release/`. The earlier full-original-package results below remain historical. The [example README](../examples/ets-practice-test-1/README.md) describes the current payload and optional-source boundary.

## Earlier full-source bundle verification: 2026-09-26

This earlier review checked the then-current local code, README pair, English-only guides, and complete Practice Test 1 bundle. It did not change exam content, publish a GitHub release, rerun the long microphone examination, or freshly re-fetch the historical ETS rule sources. Earlier dated sections remain evidence for their own revisions.

| Check | Result for the earlier full-source working tree |
| --- | --- |
| Full local test suite | 620 passed: 192 UI, 393 backend/security, 35 data/import; type checking passed |
| Isolated source-only checkout | No private `data/`, `generated/`, `storage/`, or private curation manifests before sample installation; existing local dependency installations reused |
| First sample install | CLI installed only `student-1`: 97 items / 79 screens, 13 originals, 68 copied files; the separately validated catalog was merged |
| Repeat install | `reused: true`, zero copied files; existing native example retained |
| Isolated-checkout suite | 595 passed: 192 UI, 392 backend/security, 11 data/import; 25 private-dependent checks skipped (1 backend, 24 data) |
| Source and packaging | All 69 payload hashes passed; 13 English material filenames matched the exporter mapping; 52 derived assets and all source references retained |
| Strict eligibility | Reading/Listening/Writing available; Speaking and full strict test remain disabled for the recorded Interview question 1 source mismatch |
| Documentation | Only root README has EN/zh-CN editions; other Markdown is English-only; links and local section anchors checked |
| Production build | Passed in the isolated source tree; no browser microphone or real-device claim is added by this build |

The local host used Node.js 25.9.0 and Python 3.14.3 on macOS. This is not a fresh dependency-download test or a run on the configured Linux CI host/minimum supported versions. The [testing guide](TESTING.md#validate-a-clean-sample-installation) documents the repeatable clean-sample flow.

Logs and the machine-readable report are under `tmp/qa/docs-consistency-20260926/`, excluded from the repository. The public [example README](../examples/ets-practice-test-1/README.md) is the current package inventory. The September 5–8 full-private-bank counts and former bilingual-document totals below are historical, not today's public sample or documentation policy.

## Source-text repair — 2026-09-07–08

The full private reimport applied 653 verified field corrections across 398 of 1,518 screens. A second import reproduced the corrected values. All 572 checks passed (187 UI, 354 backend/security, 31 data/import), and the production build passed. Directly reopening the user-reported completed listening session showed the correct `I’ll have…` and `It’s a nice room.` options, retained selected IDs D and C, and preserved its answer map and score snapshot. All 29 stored session rows were byte-for-byte unchanged after restart and that review request; all 18 runtime source checks passed. Details: [source text fidelity](TEXT_FIDELITY.md), with local proof in `tmp/qa/text-fidelity-20260907/final-verification.json`.

## Bilingual and open-source onboarding verification — 2026-09-06

That September 6 update was verified against both the installed private collection and a separate public-only copy without original PDFs, generated private exams, or private curation manifests. It predates the current real-source example package.

| Check | Result at that date |
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
