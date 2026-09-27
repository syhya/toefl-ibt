# Architecture and developer notes

TOEFL Local Lab is a single-user local web application. React renders the practice interface; FastAPI owns the session state and exposes only the content permitted at the current stage; SQLite and local media directories preserve the user's work. Internet access is needed to install dependencies or obtain materials, not for ordinary practice after setup.

## Repository map

| Path | Responsibility |
| --- | --- |
| `src/App.tsx`, `src/pages.tsx`, `src/components.tsx` | Application navigation, catalog, preparation, history, and shared controls |
| `src/Exam.tsx`, `src/Questions.tsx` | Examination stages and source-based question interactions |
| `src/types.ts` | Frontend contracts for questions, sessions, answers, and review |
| `src/Documentation.tsx`, `scripts/check_docs.py` | Allowlisted Markdown navigation, README-only bilingual policy, and repository-link validation |
| `public/styles.css`, `public/fonts/` | Local presentation and licensed fonts |
| `backend/app.py` | HTTP routes, request validation, active/review projection, and asset authorization |
| `backend/engine.py` | Versioned examination state machine, deadlines, navigation, and scoring |
| `backend/storage.py` | SQLite persistence and recording metadata |
| `backend/catalog.py`, `backend/integrity.py` | Catalog capabilities and source/derived-asset validation |
| `backend/presentation.py` | Validation and allowlisting of structured presentation blocks |
| `backend/reading_layout.py`, `shared/reading-layouts.json` | Source-bound paragraph and line-break projection for active practice and review, without mutating saved plans or embedding private passages |
| `backend/media.py` | Recording containers and playback preparation |
| `backend/mistakes.py`, `backend/explanations.py` | Cross-session mistake review and source-based/local explanations |
| `backend/reviewed_explanations.py`, `shared/example1-explanations.{en,zh-CN}.json` | Bilingual Practice Test 1 rationales bound to reviewed question/key fingerprints, served only in review or authorized guided feedback |
| `backend/practice_groups.py` | Source-ordered module/category groups, membership fingerprints, and aggregate progress |
| `shared/rules.json` | Versioned timing, evidence levels, and navigation policy |
| `examples/ets-practice-test-1/` | Complete prepared exam, derived assets, optional-source provenance, and file manifest |
| `backend/example_pack.py` | Verified installation of the bundled curated example, preserving native modules and timing metadata |
| `backend/packs.py` | Separate portable custom-pack schema and untimed import |
| `scripts/` | Installation, startup, source import, and isolated QA utilities |
| `tests/`, `backend/tests/` | UI, API, security, import, and source-data checks |
| `data/`, `generated/`, `storage/` | Local materials, derived catalog, and user records; excluded from Git |

## Request and state flow

1. The frontend reads catalog metadata and a selected exam's capabilities.
2. Starting a session freezes its selected route, source content, and rule version. An existing session does not silently acquire new timing rules after an update.
3. The engine selects the stage: instructions, media playback, response, recording, expiry acknowledgement, or completion.
4. The API returns the current question through an explicit allowlist. Reference answers, explanations, transcripts, and original evidence files belong to review, not the active response contract.
5. Answer/event requests identify the session and question. The server checks the current stage and deadline before accepting the operation. A stale response cannot become an answer to the next question.
6. Completion freezes objective results once. Review adds self-assessments and recording status without rewriting the original objective score snapshot.

The frontend timer is a display of a server deadline, not the authority for elapsed time. Refreshing, backgrounding a tab, or restarting a client does not create a new deadline. Test clock advancement exists only in isolated QA tools.

## Structured question content

Questions use `presentationSchema: structured-v1`, `structuredContentStatus`, and typed `stemBlocks`. Supported material includes paragraphs, instructions, titles, messages, dialogue, lists, tables, highlighted sentences, form-position diagrams, and essential visuals. Inputs remain explicit: `choices`, `passageTemplate` and `blanks`, or `tokens` and `slots`.

Cloze placeholders represent missing letters only. Given prefixes and suffixes remain in the passage. Build-a-Sentence slots preserve printed fixed words, punctuation, duplicate tokens, and distractors. Do not derive a new prompt from the reference answer.

Only necessary source photographs, portraits, scenes, or maps belong in active `assets`. They require a specific semantic alternative description, `role: essentialVisual`, and high-resolution source evidence. Original full-question crops belong in review-only `sourceEvidenceAssets`. `source.page` is a one-based physical PDF page; `source.originalNumber` is the printed question number, which may differ from the application's position.

For the curated private importer, a `source-verified` label alone is insufficient: manifests bind source hashes, page identity, content identity, visual bounds, and derived-file hashes. Portable custom resources are a separate authoring workflow; their validation does not certify ETS provenance. See the [import guide](IMPORTING.md).

## Bundled example and portable packs

The default newcomer dataset is the complete source-based `examples/ets-practice-test-1/` package. Its manifest binds the native exam and required prepared/metadata files. The example installer checks these dependencies before registration and preserves source question IDs, modules, timing eligibility, and audio segmentation. It reuses an already installed `student-1`, preserving a full personal catalog and existing sessions. Installation runs locally without OCR or the private collection. The current audio edition explicitly chooses the supplied Interview question 1 audio variant and retains the paper prompt for review. All four sections and the full test are source-eligible for local strict practice. An explicit `--upgrade` moves an installed lightweight v2 example to v3 while preserving saved plans and immutable old resources; private imports are not replaced.

The default bundle has the allowlisted `runtime-only` profile (version 3; verified v2 installs remain supported). It installs 53 prepared assets and metadata, retaining the 13 source identities as optional references. `backend/prepared_sources.py` permits absent originals only when the profile, provenance hash, source records, structured-content hashes and runtime-asset map agree. A missing/changed required asset, corrupted proof, conflicting source record, or present-but-corrupt original still fails verification. Other archives keep the original full-source gate. Optional original filenames are English; source URLs/IDs remain stable for old installations.

The bundle carries only the example's `provenance.json` and `text-corrections.json`, installed under `generated/assets/ets-practice-test-1/`. `verificationInputs.textCorrectionsPath` selects its hash-bound errata; corrections are already applied in the prepared questions. Historical correction projection still requires actual matching original bytes and does not weaken that guard for omitted files. These are not the full private `scripts/verified_*.json` collection, and checksums are not publisher digital signatures.

Portable custom packs use the separately validated authoring schema in `backend/packs.py` and remain untimed supplementary resources. The native example exam must not be accepted as an arbitrary portable JSON import: internal provenance and strict-mode fields are not user-authored capabilities. The tiny synthetic `tests/fixtures/portable-pack.json` is confined to import tests and is never the installed welcome dataset. See [TOEFL iBT® Practice Test 1 package details](../examples/ets-practice-test-1/README.md) and [importing resources](IMPORTING.md).

## Documentation language and routes

Only root `README.md` / `README.zh-CN.md` are maintained as a language pair. All other project Markdown is English-only, including `docs/`, policies, example notices, and the font README. `GET /api/documentation/{locale}/{document}` uses an explicit file allowlist and rejects symlinks/path traversal. For non-README documents, both `en` and legacy `zh-CN` routes return the English file with `Content-Language: en`. Only the root README follows the requested language.

The frontend requests English guide content and sets the article's language accordingly, while toolbar controls retain the chosen UI language. Reading an English guide does not switch the application language. README language links retain their explicit language-selection behavior. `scripts/check_docs.py` enforces the root pair, rejects extra translated editions, and checks local Markdown links.

## Scoring and history

Practice Test 1 uses project-authored English and Simplified Chinese explanations for all 79 current screens, plus a separate note for the retained paper Interview 1. These are explicitly not ETS-authored. A fingerprint binds each rationale to the question, choices, reference key, source identity and audio identity; changed content or an unresolved key withholds the note instead of attaching a stale explanation. Display-only reading paragraph restoration preserves that binding. The original companion extracts remain archival source data, but are not attributed as the source of these new rationales. Review and authorized feedback return the English note with an authored Simplified Chinese translation. Both records must match the same question fingerprint; missing or mismatched translations withhold the rationale. The UI selects the text, reasons, warning notices, and label for the current language without refetching or changing saved session state. Original imported source quotations remain verbatim; older English-only review payloads remain readable. This display layer never changes saved questions, submitted answers or grading keys and requires no bundle upgrade. See the [explanation audit](TEXT_FIDELITY.md#practice-test-1-explanation-audit-2026-09-26).

Reliable objective answers contribute to a raw correct/total count. Unresolved answer conflicts are excluded from the denominator. Writing and speaking retain the response and allow rubric-based self-assessment; they are not automatically converted into official ETS scores.

`scoreSnapshot` records the selected objective results, denominator, scoring engine version, and time at completion or explicit termination. Older records without a snapshot are identified as `legacy-recomputed`, rather than being retroactively represented as frozen historical scores. Late valid recording segments and later self-assessment do not change that objective snapshot.

The mistake collection derives from completed, actually answered, objectively scoreable questions. It retains error history after a correct retry. Question-version changes do not silently replace a historical answer key; unavailable or changed sources can disable direct retry while preserving review.

## Recording lifecycle and storage

MediaRecorder produces indexed segments. The server stores original segments without overwriting an existing segment with different bytes. A recording take also has a final segment count and ending reason. A missing final marker or segment leaves the take incomplete even if some audio plays.

Interrupted recording creates a new take; old takes remain. Browser IndexedDB retains segments awaiting upload so a temporary service outage can be retried. Once a supported recording is complete, the local FFmpeg dependency can rebuild a seekable container using stream copy, without re-encoding or changing the original segments.

| Location | Meaning |
| --- | --- |
| `storage/practice.sqlite3` | Sessions, answers, deadlines, events, scores, and recording metadata |
| `storage/practice.sqlite3-wal`, `storage/practice.sqlite3-shm` | SQLite runtime sidecar files when present |
| `storage/segments/` | Original recording segments |
| `storage/playback/` | Rebuildable playback cache |
| Browser IndexedDB | Pending uploads; not included in a filesystem-only backup |

Stop the service before copying all of `storage/`, or use a correct SQLite online-backup procedure. Copying only the live main database can miss WAL updates.

## Local security boundary

The service binds to `127.0.0.1`. It has no multi-user authentication or proctoring model. An active strict session blocks parallel practice, historical score probing, review, original source access, and other sessions' media where those would bypass the practice restrictions. Assets are authorized by the current question and phase, not merely by knowing an identifier.

This boundary protects the application's own workflow. A person with access to the machine can still open their own PDFs or inspect local files; the project is not an operating-system lockdown client. Read [SECURITY.md](../SECURITY.md) before changing network exposure or adding remote access.

## Extending the project

For a new question interaction, update the type contract, structured validation, active projection, renderer, source importer, and meaningful behavior tests together. Keep answer-bearing fields out of active API responses. For timing changes, retain evidence, version the rule contract, and test frozen-session compatibility. Add comments to explain invariants and non-obvious decisions, especially stage transitions, source hashes, and deadline handling; avoid comments that only repeat the code.

For interface changes, keep original exam content separate from translated application chrome. A language switch must not mutate answers, question identifiers, recording state, or deadlines. For import changes, validate a complete candidate before installing it and preserve existing user records. See [CONTRIBUTING.md](../CONTRIBUTING.md) and [TESTING.md](TESTING.md).
