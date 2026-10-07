# TOEFL iBT 2026 rules and simulation boundaries

First checked: 2026-08-31; independently rechecked: 2026-09-05. Applies to the test introduced on 2026-01-21. This is a dated evidence record, not a claim that all linked pages were rechecked during the bilingual documentation update. Sources are ETS pages, technical documents, and official samples; screenshots in the private `data/` collection support observations about those specific materials. See the [independent verification](ets-2026-verification.md).

Timing for all fifteen installed iBT arrangements was re-audited on **2026-10-04** against ETS's content page, blueprint, teacher sample and Test Overview. See the [current collection audit](#collection-timing-audit-2026-10-04). The September 26 sample audit below is retained as historical evidence; this timing review does not refresh unrelated scoring or test-day claims.

The application is not an ETS examination client. **Strict timing means enforcing a selected local practice configuration, not reproducing every production examination rule, screen, or scoring system.**

## Evidence levels

| Level | Meaning |
| --- | --- |
| `verified` | An explicit ETS statement supports the sequence, count, or time. |
| `observed_material` | A supplied PDF directly shows the interface or clock; it does not establish all current production rules. |
| `approximation` | A necessary local default whose exact official value was not established. |
| `unsupported` | Public evidence and available materials cannot reproduce the capability. |

The structured contract is `shared/rules.json`. `referenceElapsed` is a duration reference, not an answer timer. A `null` verified value means unknown, not zero.

## Collection timing audit: 2026-10-04

**v9 fixes inconsistent local clocks across the installed iBT collection. It does not claim that ETS publishes exact deadlines for every task.** Pack 1–6 and Paid 1–2 previously overrode the browser's 30-minute Reading preset with the old Pack screenshots' 11:30/09:00 clocks. Paid 1's lower route mixed 11:30 with the 15:00 fallback. The source observations are valid for that supplied preview edition, but silently overriding the selected practice profile was inconsistent and prevented users from adjusting these archives.

New sessions for Experience, Student, Teacher, Pack and Paid now use the same Reading profile: **15:00 + 15:00 = 30:00**. This retains the user's existing equal allocation, and is explicitly a practice configuration. The current ETS overview says approximately 30 minutes; its blueprint estimates 18–21 minutes for a router and 9 for a second module, so neither source establishes 15-minute official module deadlines. The old screenshots and their timing metadata remain unchanged for provenance.

| Task | New strict iBT session | Evidence level |
| --- | --- | --- |
| Reading | Two separate 15-minute clocks; no time carried between modules | Local equal-allocation profile; approximate section total from ETS |
| Listening | 20 seconds for response/conversation/announcement; 30 for academic talk, after audio | Supplied-material observation, not a universal ETS exact window |
| Build a Sentence | 6 minutes shared by the task | Local approximation; an exact official initial limit remains unconfirmed |
| Write an Email | 7 minutes shared by reading and writing | Explicit ETS rule |
| Academic Discussion | 10 minutes shared by reading and writing | Explicit ETS rule |
| Listen and Repeat | 8/8/10/10/10/12/12 seconds, retaining verified per-item source windows | ETS confirms 8–12 seconds; the exact sequence is a local/source preset |
| Take an Interview | 45 seconds for each answer after the prompt, without preparation | Explicit ETS rule |

Strict iBT sessions freeze the standard profile on the server and ignore customized browser practice presets. Guided iBT practice honors its saved Reading settings even when a legacy source module contains a different clock. Essentials and other untimed supplements remain untimed. Existing sessions retain their frozen plans, rules, accepted answers and scores; begin a new session to use v9.

Directions do not consume an answer budget. Reading/Build navigation cannot restart their shared deadline. Listening/Speaking stimulus playback precedes each response window; shared recordings are not replayed for every question. The overview's approximately **29/23/8 minutes** for Listening/Writing/Speaking includes form-dependent activity and does not establish three freely distributable answer clocks. Questions and recordings are neither shortened nor padded to force those totals.

The audit also closes an API completeness gap: requesting a missing second-module branch now fails instead of silently starting only module 1. Explicit common-module question selections remain available for guided practice. Catalogue section counts now distinguish question items (including each cloze blank) from screens.

Evidence rechecked: [ETS current content and structure](https://www.ets.org/toefl/test-takers/ibt/about/content.html), [ETS blueprint, PDF pages 2–3](https://www.eu.ets.org/pdfs/toefl/toefl-enki-test-specifications-2026.pdf), [teacher sample 1](https://www.ets.org/content/dam/ets-org/pdfs/toefl/toefl-ibt-teachers-resources-practice-test-1.pdf), and [ETS Test Overview](https://www.ets.org/content/dam/ets-org/pdfs/toefl/toefl-ibt-test-overview.pdf). Pack Begin-page clocks were also checked against the supplied PDFs. Recording screenshots already showing 7 or 3 seconds remaining were rejected as initial repeat-window evidence.

## Practice Test 1 timing audit: 2026-09-26

The v6–v8 results in this section are historical. For current precedence and strict-mode behavior, use the v9 audit above.

**The bundled `student-1` sample does not have fully verified official deadlines for every part.** Its Reading and Listening clocks, sentence-building limit, and exact repeat sequence are practice settings. The initial v6 audit retained a 20:30 Reading preset, which did not provide a 30-minute practice run. Following that correction, v7 initially used 21:00/09:00 from the blueprint estimates. **The current v8 default is 15:00/15:00**, following the user's preference to split 30 minutes evenly between this fixed paper's two 20-item modules. This is a personal practice allocation, not a newly verified official deadline or a reproduction of adaptive module timing.

The [current ETS overview](https://www.ets.org/toefl/test-takers/ibt/about/content.html) gives approximate base times of Reading 30 minutes / 50 items, Listening 29 / 47, Writing 23 / 12, and Speaking 8 / 11, excluding directions. The bundled paper instead has 40 Reading and 34 Listening items. Its paper adaptation and the live adaptive test are different forms; neither proportional scaling nor dividing these totals establishes the paper's missing clocks.

| Example 1 part | Current default for a new session | Official evidence and assessment |
| --- | --- | --- |
| Reading Module 1: Complete the Words, Daily Life, Academic Passage | **15:00 shared** by 20 items on 11 screens | User-selected equal allocation for this fixed practice paper, not a verified official initial clock. |
| Reading Module 2: the same three task types | **15:00 shared** by 20 items on 11 screens | The same equal-allocation practice preset. It does not claim to reproduce the blueprint's adaptive second-module estimate. |
| Listening Module 1: 18 questions | **20 seconds/question** for Response, Conversation and Announcement; **30 seconds/question** for Academic Talk | The sample confirms per-question timing, without numeric windows. The 20/30-second defaults are observations from another supplied pack, not verified universal limits. |
| Listening Module 2: 16 questions | **20/30 seconds/question**, by the same task types | Same qualification; audio playback and answer windows are separate. |
| Build a Sentence: 10 questions | **06:00 shared** across all ten | Sample confirms a task clock but no starting value. Six minutes remains approximate; neither 6:00 nor 6:50 is established by the official sources checked. |
| Write an Email | **07:00**, including reading and writing | Explicitly confirmed in the sample paper and Test Overview. |
| Write for an Academic Discussion | **10:00**, including reading and writing | Explicitly confirmed in the sample paper and Test Overview. |
| Listen and Repeat: 7 questions | **8 / 8 / 10 / 10 / 10 / 12 / 12 seconds** after the respective prompts | ETS confirms a maximum window of **8–12 seconds** per sentence, not this sample's exact seven-value sequence. The sequence remains a local preset. |
| Take an Interview: question 1 | **45 seconds** after the original audio in the v3 audio edition | The user selected the original-audio variant, whose wording matches the ETS Test Overview. It differs from the paper PDF; setup/review disclose that difference. Legacy paper sessions remain untimed. |
| Take an Interview: questions 2–4 | **45 seconds each** after the matched audio | ETS explicitly confirms 45 seconds per question; no preparation period. Fixed in v6: question 1 no longer disables these questions' timers. |

Sources: [ETS-hosted student paper](https://www.in.ets.org/content/dam/ets-india/pdfs/toefl/toefl-ibt-full-length-practice-test-1.pdf), [Test Overview, physical pages 14–15, 17 and 19 in the 28-page version fetched for this audit](https://www.ets.org/pdfs/toefl/toefl-ibt-test-overview.pdf), and [blueprint, physical pages 2–3](https://www.eu.ets.org/pdfs/toefl/toefl-enki-test-specifications-2026.pdf). The blueprint labels its times as estimates and includes a pre-launch revision caveat. The student paper was downloaded again and still matches the package's 36-page source SHA-256 `33e37aac4324d36a01af7ac0eb67b06aa438dfdf4fc96e31f4bdb72d9b8d9a2d`. The fetched Test Overview SHA-256 is `ce5e0eef3ea47b9964b0b1b034e96fa3b2aa0681347f17b381196cb0661249f0`; pagination differs from older copies.

### Clock behavior and fixes

- Reading and sentence-building use a **shared** budget. Selecting only a subset of those questions retains the whole task/module budget; it is not a newly verified per-question limit. Start pages now state this explicitly.
- Directions wait for Begin without consuming the response budget. Reading/Writing clocks start at Begin, continue through within-module navigation, and do not carry unused time to the next task. Listening/Speaking answer clocks start after their audio sequence ends. Delayed or repeated events cannot restart an expired response window.
- v6 selects repeat durations by the original source position before filtering. Previously, practising the sixth or seventh sentence alone incorrectly gave the first sentence's 8 seconds. Each now retains its configured 12 seconds; explicit source timing and custom practice presets remain respected.
- v6 separated adjacent matched and unmatched audio items in the earlier paper edition (ten runtime stages, with Interview question 1 untimed). The current v3 audio-edition package instead has four matched Interview prompts, nine runtime stages, and eligible local strict Speaking/full-test practice. This is an explicitly selected source variant, not a claim that the audio matches the different paper prompt.
- Start pages show the actual budget and distinguish an ETS-specified value, a source configuration, a local default, or untimed study. Old sessions keep their frozen plan, deadlines and rules; they are not relabelled or retimed. Start a new session to use the current rules.

The v8 default Reading budgets sum to **30:00** (15:00 + 15:00); the previous 11:30/09:00 preset summed to only **20:30**. Unchanged earlier browser presets (11:30/09:00 and 21:00/09:00) upgrade automatically, while customized settings and source-specific module limits retain precedence. Deliberately saving a custom 11:30 value is also supported and survives reloads. Listening response windows sum to **12:40**, plus **6:24.75** of unique prepared audio clips, or about **19:05** if every response window is used in full. The local 30-minute Reading allocation targets the overview total, but does not make this 40-item paper equivalent to the current adaptive Reading test. The Listening sum still describes the prepared paper and local windows, not the current adaptive test's 29-minute overview. Writing defaults sum to 23 minutes, which does **not** prove that sentence-building must be exactly 6 minutes. The v3 audio edition has complete per-question Speaking windows. Its overall elapsed time depends on its original clips and transitions; no universal eight-minute section deadline is imposed.

The v6 audit verification: **644 checks passed** (196 UI, 413 API/security, 35 data/import), plus production build and an isolated minimal-package browser check of the English/Chinese Reading start-page notice. Regression coverage includes filtered repeat positions, post-audio deadlines, matched questions following untimed study, shared-budget navigation, frozen old sessions, strict source gates, and a full 79-screen prepared-package API walkthrough. Test clocks are simulated; this is not an 83–89-minute real-time exam validation. Local logs are in `tmp/qa/example1-timing/` and are not required distribution files.

The subsequent v7 Reading-profile correction passed **649 checks** (200 UI, 414 API/security, 35 data/import), production build and browser verification of the 21:00/09:00 module clocks and navigation without resetting or carrying over time. Added regression checks cover unchanged legacy preset migration, preservation of customized settings, the 30-minute sum, separate module deadlines and old v6 frozen Reading sessions. Logs are under `tmp/qa/reading-profile/`.

The current v8 equal-allocation preset passed **663 checks** (204 UI, 424 API/security, 35 data/import) and production build. Both module clocks are 15 minutes; migration tests cover earlier default profiles and deliberate custom allocations. Saved sessions retain their previous rules and deadlines. Logs are under `tmp/qa/balanced-reading/`.

## Confirmed test sequence

The order is **Reading → Listening → Writing → Speaking**. Reading and Listening each have two adaptive stages; Writing and Speaking are linear. Sources: [ETS Technical Manual, IV-1 and II-7](https://rr.ets.org/index.php/etsrr/article/download/28/17/34).

The website's base overview is shown below. Instructions are excluded, and adaptation may change question counts and elapsed time; ETS suggests allowing approximately two hours overall. These are not four fixed section-wide deadlines. [ETS content and structure](https://www.ets.org/toefl/test-takers/ibt/about/content.html)

| Section | Tasks | Base items | Approximate base time |
| --- | --- | ---: | ---: |
| Reading | Complete the Words; Read in Daily Life; Read an Academic Passage | 50 | 30 min |
| Listening | Choose a Response; Conversation; Announcement; Academic Talk | 47 | 29 min |
| Writing | Build a Sentence; Write an Email; Academic Discussion | 12 | 23 min |
| Speaking | Listen and Repeat; Take an Interview | 11 | 8 min |

The blueprint estimates Reading router 18–21 minutes and second module 9 minutes; Listening router 18 minutes and second module lower 7 / upper 11 minutes. These estimates include route differences and carry a pre-release revision caveat. They do not replace the actual module/question clock. [ETS blueprint, pp. 2–3](https://www.eu.ets.org/pdfs/toefl/toefl-enki-test-specifications-2026.pdf)

## Timing and navigation

| Task | Confirmed rule | Remaining uncertainty or local constraint |
| --- | --- | --- |
| Reading | Module clock; Next/Back within a module; no return to module 1 after entering module 2 | Preserve each archive's timing evidence; do not assume one initial duration for every test. |
| Listening | Individual question clock; no return after Next; recording plays once | Public text did not establish a universal 20-second answer window. |
| Build a Sentence | 10 items; move given tokens; task has a clock | Neither 6:00 nor 6:50 initial time was confirmed; a remaining-time screenshot is insufficient. |
| Write an Email | One task; 7 minutes including reading and writing | Unused sentence-building time is not carried over. |
| Academic Discussion | One task; 10 minutes; an effective answer is recommended to contain at least 100 words | Word guidance is not a submission gate or an automatic zero-score rule. |
| Listen and Repeat | Seven sentences, heard/repeated once; no preparation; maximum recording windows 8–12 seconds | The per-item sequence 8/8/10/10/10/12/12 comes from the supplied screenshots. |
| Take an Interview | Four questions; no preparation; 45 seconds each | Do not add old-format 15/30-second preparation periods. |

Navigation and response timing: [Teacher Practice Test 1, physical pp. 3, 15, 27, 29–30, 33–34](https://www.ets.org/content/dam/ets-org/pdfs/toefl/toefl-ibt-teachers-resources-practice-test-1.pdf). Speaking windows: [Test Overview, pp. 17–18](https://www.ets.org/content/dam/ets-org/pdfs/toefl/toefl-ibt-test-overview.pdf). Single listening playback and sentence-building count: [Specifications, pp. 6, 12](https://www.eu.ets.org/pdfs/toefl/toefl-enki-test-specifications-2026.pdf).

Strict practice disallows replay, seeking, playback-rate changes, timer pause, and cross-module return. Local fault recovery records interruptions; it is not an ETS proctor decision. Audio and microphone should be checked before starting. Home testing does not permit self-directed breaks, and Writing disables spelling/grammar assistance and outside paste. A normal web application cannot provide production application lockdown. [ETS home test day](https://www.ets.org/toefl/test-takers/ibt/test-day/at-home-test-day.html), [Technical Manual, IV-2](https://rr.ets.org/index.php/etsrr/article/download/28/17/34).

## Timing directly observed in supplied Pack 1

Source: **TPO Pack 1 — Question Paper** (`mat-e028047bd7f0` in the local `generated/catalog.json`). The catalog retains its original filename and path; this is an English documentation label. Page numbers below are physical PDF pages. Key pages were rendered and page-top clocks were OCR-checked.

| Page | Observation | Permitted use |
| --- | --- | --- |
| 2 | Reading module 1 Begin screen shows 00:11:30 | Evidence for this material only |
| 18 | Reading module 2 Begin screen shows 00:09:00 | Evidence for this material only |
| 27, 30, 37, 39, 42, 43, etc. | Response/conversation/announcement questions show 00:00:20 | Supports the corresponding local 20-second default |
| 48, 49, 51, 66 | Academic Talk questions show 00:00:30 | Supports a local 30-second default |
| 35, 38, 41, 47, etc. | No answer countdown while stimulus plays | Keep playback and response stages separate |
| 74 | Build instructions show 00:05:47 remaining | Does not establish initial 6:00 or 6:50 |
| 75–84 | Build includes Review/Back | Supports within-task navigation |
| 92–98 | Repeat windows are 8, 8, 10, 10, 10, 12, 12 seconds | Supports this collection's local sequence |
| 101 | Interview shows 00:00:45 | Agrees with official text |

The PDF overview lists older ranges of 35–48 Reading and 35–45 Listening items; screenshot date/version is unknown. A TOEFL mark alone does not establish current production behavior. Verify other archives separately and label manual defaults as practice settings.

## Scoring and unsupported capabilities

The software can compare reliable objective keys, save writing and speech, and support rubric self-assessment. Official Reading/Listening scoring uses calibration and equating, not a linear correct-rate conversion to 1–6. Sentence building is scored 0/1; individual long-writing and speaking responses use their respective 0–5 rubrics, while ETS's scoring engine is proprietary. [Technical Manual, III-1–III-2](https://rr.ets.org/index.php/etsrr/article/download/28/17/34).

The private collection's `writing-rubrics.pdf` and `speaking-rubrics.pdf` are review/self-assessment references, not a local official scoring engine. Unsupported claims include real ETS routing thresholds, item-calibration parameters, unscored-item detection, score-conversion tables, ETS AI/human scoring, proctoring/lockdown, and universal production pixel/behavior parity. The local 70% upper/lower threshold is simulated routing, not ETS adaptation.

## Data requirements and later observations

Strict availability requires complete verified questions, order, task types, necessary media, and segmentation for the selected scope. Reliable keys determine the scoreable denominator. A source-complete question with an unresolved key may remain timed while its ambiguous unit is excluded from scoring; Pack 3 has two such blanks. Do not substitute synthetic speech, guessed media, full unsplit tracks, or placeholder questions for missing official content.

The early official sample visit reached only a form. On 2026-09-05 an authorized current Sampler session was observed for Reading, Listening, Build, Email, and Discussion. Email first showed 06:56 and Discussion 09:34 remaining; these were not measured initial values. Build showed no clock. The Sampler's direct transitions differ from some supplied Begin pages and do not override formal timing evidence. See [interface observations](EXAM_UI_REFERENCE.md).

Later that day, Discussion expiry retained the read-only question beneath a `Writing Time Expired` dialog; Continue proceeded to Speaking instructions. New v5 sessions freeze `writingExpiryAcknowledgement`: Email/Discussion expiry retains accepted answers and the original deadline until Continue. Old sessions keep their frozen behavior. This observed-client rule is not generalized to unseen Reading, Listening, Build, or speaking expiry states.
