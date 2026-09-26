# TOEFL iBT® Practice Test 1

This is TOEFL Local Lab's default example: **TOEFL iBT® Practice Test 1**. The questions come from the [ETS-hosted Practice Test 1 PDF](https://www.in.ets.org/content/dam/ets-india/pdfs/toefl/toefl-ibt-full-length-practice-test-1.pdf), not synthetic example questions. The local question PDF was verified against that download on 2026-09-14 (Asia/Shanghai; later exports record their own local re-verification date in `provenance.json`): both have SHA-256 `33e37aac4324d36a01af7ac0eb67b06aa438dfdf4fc96e31f4bdb72d9b8d9a2d` (3,544,309 bytes, 36 pages).

This lightweight package contains all prepared questions, source-derived playback clips, extracted explanations, discussion portraits and review images. Original PDFs and full MP3 tracks are optional and excluded from Git. Companion audio/explanations came from separately supplied local sources, not the official PDF URL. See [NOTICE.md](NOTICE.md).

## Install and practice

From the repository root, after [installing the application](../../README.md):

```sh
npm run demo
npm start
```

Open [http://127.0.0.1:4173](http://127.0.0.1:4173), select the official student sample 1, and choose a whole test or **R / L / W / S**. An empty homepage and **Help & setup** also provide **Try Practice Test 1**. Source questions and audio stay in English; the site's **EN / 中文** selector changes application controls. Only the root project README is bilingual; this package guide and the detailed documentation stay in English.

Installation uses prepared files and requires no OCR, question download, or private collection. Repeating the action reuses an existing verified `student-1`. An installed full personal catalog keeps its other archives and saved practice records.

## Included scope and timing limits

| Section | Question items | Screens | Source task arrangement |
| --- | ---: | ---: | --- |
| Reading | 40 | 22 | Two modules, each 20 items/11 screens |
| Listening | 34 | 34 | Module 1: 18 items; Module 2: 16 items |
| Writing | 12 | 12 | 10 Build a Sentence, 1 Email, 1 Academic Discussion |
| Speaking | 11 | 11 | 7 Listen and Repeat, 4 Interview |
| **Total** | **97** | **79** | Four sections, nine modules, twelve task types |

A reading cloze screen contains multiple answer blanks, so item and screen counts differ. The local flow is Reading → Listening → Writing → Speaking, preserving the supplied modules and tasks.

**Reading, Listening, and Writing support eligible strict practice. Speaking and the whole test remain guided:** the first Interview question has an unresolved mismatch between the supplied paper and audio versions. The package retains that warning and the source evidence; it does not replace the question, synthesize audio, or weaken source checks to unlock strict mode. Completeness describes the included source content, not a claim that every scope is eligible for strict timing.

The source PDF is a paper adaptation, not an exact replica of the live test. Application rules retain their documented limits and approximate local settings in [the rules documentation](../../docs/OFFICIAL_RULES.md). Objective references support local answer checks; writing and speaking retain saved responses and self-assessment rather than official ETS scores.

The [2026-09-26 timing audit](../../docs/OFFICIAL_RULES.md#practice-test-1-timing-audit-2026-09-26) confirms Email 7 minutes, Discussion 10 minutes, Interview 45 seconds per matched question, and the Repeat 8–12-second range. The exact Reading, Listening, sentence-building and seven-item repeat defaults remain local practice settings. New v6 sessions retain a repeat question's original timing position when filtered and keep only unmatched Interview question 1 untimed; questions 2–4 use 45 seconds each. This creates ten runtime stages from the same nine source modules. Existing saved sessions are unchanged.

The paper edition's Reading module 1 contains 20 items. The observed online sampler has 17 and one small cloze wording difference; the package keeps its PDF wording and source counts. The newer cloze editor retains underlines while typing and changes font/width on focus/blur, without changing the source edition. See [the dated comparison](../../docs/EXAM_UI_REFERENCE.md#live-reading-interaction-checked-on-2026-09-26).

## Package format

- `manifest.json` describes the package and binds its required files to hashes.
- `exam.json` holds the native curated `student-1` exam, including source identities, modules, tasks, the runtime-only profile, and eligibility limits.
- `catalog.json` describes the archive and its source files.
- Optional `materials/` originals stay local and are ignored by Git. Their identities, hashes, English filenames and original installation paths are recorded in `manifest.json` and `provenance.json`; they are not required payload files.
- `assets/` contains prepared audio clips, original question crops, and discussion portraits.
- `provenance.json` retains evidence of source/asset identity and the official PDF download comparison. `text-corrections.json` retains source-bound extraction corrections.
- [NOTICE.md](NOTICE.md) distinguishes the source materials' rights from the project code license.

| Required group | Files | Bytes |
| --- | ---: | ---: |
| Prepared assets: 33 WAV, 16 JPG, 3 PNG | 52 | 17,195,702 |
| Exam, catalog, provenance, text corrections | 4 | 622,915 |
| **Total payload** | **56** | **17,818,617 (about 17.8 MB)** |

The manifest and this README/NOTICE are additional files. A first install copies 55 files and merges the separately verified catalog. It creates `generated/` content without requiring or creating original `data/` sources. No cloud download is needed after dependency setup.

The provenance-aware runtime verifies the prepared question content and media. It explicitly reports that omitted original PDFs/full MP3s were not reverified on the new machine. Source identities and original hashes remain auditable metadata, not fabricated local files. Stored answer explanations, derived images and playback remain available; missing original-file links are hidden, and the resource library labels them **Original not installed**. Corrupted required media or provenance still blocks practice.

The 13 optional originals retain their English local filenames, such as `toefl-ibt-practice-test-1.pdf` and `practice-test-1-companion-explanations.pdf`. Existing full/private installations are reused with their original checks; do not delete their source files or overwrite saved plans to convert them. Test a new runtime-only installation in a separate project directory if an old full-source install must be retained.

This is a native application package, not the custom portable-pack authoring format. Do not submit its `exam.json` to `npm run import:pack`; use `npm run demo` to install it. For your own resources, follow [the portable import guide](../../docs/IMPORTING.md). Synthetic import fixtures live under `tests/fixtures/` and are not installed for users.

If a new installation reports missing or changed bundled files, restore this complete directory from the same repository revision and retry. Do not change checksum values to bypass a mismatch. Back up `storage/`, `data/`, and `generated/` before updates, following [the user guide](../../docs/USER_GUIDE.md).
