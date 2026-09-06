# Architecture and developer notes

English | [简体中文](ARCHITECTURE.zh-CN.md)

TOEFL Local Lab is a single-user local web application. React renders the practice interface; FastAPI owns the session state and exposes only the content permitted at the current stage; SQLite and local media directories preserve the user's work. Internet access is needed to install dependencies or obtain materials, not for ordinary practice after setup.

## Repository map

| Path | Responsibility |
| --- | --- |
| `src/App.tsx`, `src/pages.tsx`, `src/components.tsx` | Application navigation, catalog, preparation, history, and shared controls |
| `src/Exam.tsx`, `src/Questions.tsx` | Examination stages and source-based question interactions |
| `src/types.ts` | Frontend contracts for questions, sessions, answers, and review |
| `public/styles.css`, `public/fonts/` | Local presentation and licensed fonts |
| `backend/app.py` | HTTP routes, request validation, active/review projection, and asset authorization |
| `backend/engine.py` | Versioned examination state machine, deadlines, navigation, and scoring |
| `backend/storage.py` | SQLite persistence and recording metadata |
| `backend/catalog.py`, `backend/integrity.py` | Catalog capabilities and source/derived-asset validation |
| `backend/presentation.py` | Validation and allowlisting of structured presentation blocks |
| `backend/media.py` | Recording containers and playback preparation |
| `backend/mistakes.py`, `backend/explanations.py` | Cross-session mistake review and source-based/local explanations |
| `shared/rules.json` | Versioned timing, evidence levels, and navigation policy |
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

## Scoring and history

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
