# TOEFL iBT 2026 rules and simulation boundaries

First checked: 2026-08-31; independently rechecked: 2026-09-05. Applies to the test introduced on 2026-01-21. This is a dated evidence record, not a claim that all linked pages were rechecked during the bilingual documentation update. Sources are ETS pages, technical documents, and official samples; screenshots in the private `data/` collection support observations about those specific materials. See the [independent verification](ets-2026-verification.md).

The application is not an ETS examination client. **Strict timing means enforcing a selected local practice configuration, not reproducing every production examination rule, screen, or scoring system.**

## Evidence levels

| Level | Meaning |
| --- | --- |
| `verified` | An explicit ETS statement supports the sequence, count, or time. |
| `observed_material` | A supplied PDF directly shows the interface or clock; it does not establish all current production rules. |
| `approximation` | A necessary local default whose exact official value was not established. |
| `unsupported` | Public evidence and available materials cannot reproduce the capability. |

The structured contract is `shared/rules.json`. `referenceElapsed` is a duration reference, not an answer timer. A `null` verified value means unknown, not zero.

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
