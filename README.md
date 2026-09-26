# TOEFL Local Lab

English | [简体中文](README.zh-CN.md)

**Powered by GPT-6 Astra.** This project currently uses GPT-6 Astra during development to explore the model's limits in building, testing, debugging, and documenting a complete application. Ordinary practice runs locally and does not require a model API.

A local TOEFL-style practice website with English and Simplified Chinese navigation, structured questions, writing editors, countdowns for supported curated materials, microphone recording, and saved review. Built with **React + TypeScript + Vite, FastAPI, and SQLite**. After installation and resource import, ordinary practice runs offline without accounts or cloud AI services.

**The default sample is [TOEFL iBT® Practice Test 1](https://www.in.ets.org/content/dam/ets-india/pdfs/toefl/toefl-ibt-full-length-practice-test-1.pdf), the official student practice paper for the revised TOEFL iBT.** Its questions come from this ETS-hosted PDF, referred to throughout the documentation as **TOEFL iBT® Practice Test 1 — Question Paper**. The prepared package includes all four sections, segmented companion audio, extracted explanations, and necessary images; original PDFs and full audio tracks are not shipped. The companion files are separate sources, not downloads from the PDF link; see the [source notice](examples/ets-practice-test-1/NOTICE.md). The local question PDF was verified byte-for-byte against the ETS download on 2026-09-14 (Asia/Shanghai); its SHA-256 is recorded in the notice. The rest of the author's private collection and personal recordings are not included.

This is an independent practice tool, not an ETS product. Strict mode enforces the selected local rules; some timing values are explicitly documented approximations. It does not reproduce ETS's proprietary adaptation or convert raw accuracy into official 1–6 or 120-point scores. See [rules and evidence](docs/OFFICIAL_RULES.md).

## Quick start

Prerequisites: **Node.js 22.12+**, **Python 3.10+**, and a current Chrome or Edge browser. Internet access is needed for the initial dependency installation. Run these commands from the repository root on macOS or Linux:

```sh
./scripts/install.sh
npm run demo
npm start
```

Open **[http://127.0.0.1:4173](http://127.0.0.1:4173)**. Keep the terminal running; **Control+C** stops the service. Do not open `index.html` directly.

The included **TOEFL iBT® Practice Test 1** contains **97 question items across 79 screens**: Reading 40 items/22 screens, Listening 34/34, Writing 12/12, and Speaking 11/11. It retains source modules, corrected structured text, audio, discussion portraits, reference answers, and review evidence. Choose **Try Practice Test 1** on an empty homepage or run `npm run demo`; repeating installation reuses an existing `student-1` without replacing personal records. **Reading, Listening, and Writing support eligible strict practice; Speaking and the whole test remain guided because Interview question 1 has an unresolved paper/audio version mismatch.** No substitute question or synthesized audio is inserted to bypass this warning. The default interface is English; **EN / 中文** changes application controls and the root README. Detailed guides remain in English, and source questions/audio retain their language.

The installation script creates `.venv/`, installs locked frontend dependencies and Python dependencies, and builds `dist/`. It does not run OCR, download private learning materials, or alter global Homebrew/FFmpeg. macOS users can subsequently double-click [`scripts/start.command`](scripts/start.command).

### Manual installation

For a POSIX shell:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt -r requirements-import.txt
npm ci
npm run build
npm run demo
npm start
```

For Windows PowerShell, use the virtual environment's Windows path:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend/requirements.txt -r requirements-import.txt
npm ci
npm run build
.venv\Scripts\python.exe scripts/install_example.py
npm start
```

The convenience `.sh`/`.command` scripts and npm commands that call `.venv/bin/python` use POSIX paths; on Windows invoke the corresponding Python script with `.venv\Scripts\python.exe`, or use WSL. CI is configured for Linux; local verification has used macOS, not every Windows/device combination.

To choose another port: `npm start -- --port 4174`. The service binds only to `127.0.0.1`. See [troubleshooting](docs/TROUBLESHOOTING.md) if startup fails.

## What a new checkout needs

Keep the tracked [`examples/ets-practice-test-1/`](examples/ets-practice-test-1/README.md) directory with the application code: **56 hash-checked files, approximately 17.8 MB**, plus its manifest and documentation. It includes all prepared questions, 33 WAV clips, 16 review images and 3 portraits. The two original PDFs and eleven full MP3s are optional, excluded from Git, and not needed for a new installation.

The lightweight installer validates prepared content, every required media asset, and hash-bound provenance. It records original-source identities without claiming to reverify omitted originals. Original-file download links are unavailable until matching originals are locally installed; stored explanations, answers, images, and segmented playback remain usable. A new user needs no private `data/`, `generated/`, or `storage/`, and no external material download. Existing full/private installations retain their original source checks and files. Keep personal data out of Git and retain the [source notice](examples/ets-practice-test-1/NOTICE.md).

## Add resources

Open **Help & setup** to import a text-only JSON pack, or use the CLI for a folder with audio, images, video, or source PDFs:

```sh
npm run import:pack -- "/absolute/path/to/my-practice/pack.json"
```

Refresh the website and select the imported title. Custom packs are untimed guided resources. To update a changed pack with the same ID, add `--replace`; existing sessions retain frozen content and revisioned assets. Start a new practice to see updated content.

The [TOEFL iBT® Practice Test 1 reference package](examples/ets-practice-test-1/README.md) documents its contents and source attribution. It uses the curated example installer; do not upload its internal `exam.json` through the custom JSON importer. The [import guide](docs/IMPORTING.md) separately explains portable custom packs, supported question types, media, updates, and backup. Start with the guide's [minimal JSON example](docs/IMPORTING.md#minimal-complete-pack) when authoring your own questions. Small synthetic examples are confined to test fixtures and are not installed for users.

The separate `scripts/import_materials.py` pipeline handles the original full private PDF collection with its matching `scripts/verified_*.json` curation records. Those full-collection inputs are not publicly distributed; the bundled Practice Test 1 is already prepared and does not require that importer. It is not a universal PDF converter; adding a PDF alone does not create validated questions. Portable packs let new users start without that collection or OCR.

## Practice and review

- Start a whole available archive or use **R / L / W / S** for one section. The task library groups consecutive questions by source test, module/part, and category; each entry starts the complete group.
- Guided practice supports pause; specialized sessions offer audio replay and instant answers only when explicitly enabled before starting. Full-test sessions keep those aids off; completed-session review remains available. Strict mode is available only for eligible curated scopes and uses server deadlines and navigation restrictions. Supplementary resources, including custom packs and Essentials, stay untimed.
- Timed reading blanks retain one underline per missing letter while editing, expand to monospace input, and contract completed answers to paragraph text on blur; choices preserve source text. Sentence building supports tokens and fixed fragments. Email/discussion use split source/editor layouts and word count.
- Speaking saves local recording segments, tracks incomplete uploads, and supports playback/download. Test the real microphone on this local site before relying on it.
- History preserves accepted answers, objective results, writing, recordings, and rubric self-assessment. A mistake collection retains previous errors and later mastery.

The bundled paper edition and the observed online sampler differ: the sample's first Reading module has 20 items, while the observed online page showed 17, with one wording difference in the cloze passage. Matching the input interaction does not change the PDF version or remove questions; see [the dated interface comparison](docs/EXAM_UI_REFERENCE.md#live-reading-interaction-checked-on-2026-09-26).

Refresh and backgrounding do not reset timed deadlines. New completed sessions freeze objective score snapshots; source/rule updates do not silently rewrite past results. Follow the [user guide](docs/USER_GUIDE.md) for modes, tasks, recovery, scoring boundaries, and backups.

## Local data and privacy

| Path | Content |
| --- | --- |
| `data/` | Your original/private materials and copied portable-pack revisions |
| `generated/` | Normalized exams, pack registries, OCR, and derived media/assets |
| `storage/practice.sqlite3` | Sessions, accepted answers, timers, events, and scores |
| `storage/segments/` | Original microphone recording segments |
| `storage/playback/` | Rebuildable playback containers |

Browser IndexedDB can also hold recording uploads that have not yet reached the local server. Wait for those uploads before clearing browser data. For a backup, stop the service and copy **all of `storage/`, `data/`, and `generated/`**, plus private curation files if used. Do not copy only the main live SQLite file while omitting its WAL. JSON session export contains answers and recording references; audio needs a separate download or directory backup.

The application has no cloud sync or multi-user authentication. Keep it local. Keep personal learning materials, generated local catalogs, recordings, and private curation manifests out of Git. The deliberately included `examples/ets-practice-test-1/` reference set is documented separately in its [notice](examples/ets-practice-test-1/NOTICE.md). MIT applies to project code and does not relicense third-party exam content. See [security policy](SECURITY.md) and [materials](docs/MATERIALS.md).

## Development

```sh
npm test
npm run build
```

Tests cover types, UI, API, security, and import/source integrity. Private-data checks skip when their collection is absent; that is expected in a public checkout and is not a private-bank validation pass. See [testing](docs/TESTING.md) for focused commands and optional isolated browser tools.

For separate frontend/backend development, run each in its own terminal:

```sh
.venv/bin/python -m backend --port 4173
npm run dev
```

Vite normally serves port 5173 and proxies `/api` to 4173. After production code changes, rebuild and restart the local service. Architecture, invariants, and code-comment conventions are documented in [architecture](docs/ARCHITECTURE.md) and [contributing](CONTRIBUTING.md).

## Documentation and project policies

Only the project README is bilingual ([简体中文](README.zh-CN.md)). All other project documentation is maintained in English; application controls still support both languages.

| Topic | Documentation |
| --- | --- |
| All documents | [Documentation index](docs/README.md) |
| Getting started and practice | [User guide](docs/USER_GUIDE.md) |
| Importing your resources | [Import guide](docs/IMPORTING.md) |
| Problems and recovery | [Troubleshooting](docs/TROUBLESHOOTING.md) |
| Developer design | [Architecture](docs/ARCHITECTURE.md) |
| Contributions | [Contributing](CONTRIBUTING.md) |
| Security | [Security policy](SECURITY.md) |
| Community | [Code of conduct](CODE_OF_CONDUCT.md) |
| Changes | [Changelog](CHANGELOG.md) |

Historical [acceptance](docs/ACCEPTANCE.md) and [data audits](docs/DATA_QA.md) describe dated private collection/builds, not content bundled with a public checkout or certification of all current ETS states.

Project code is licensed under [MIT](LICENSE). Open Sans has its own [SIL Open Font License](public/fonts/OFL-OpenSans.txt). Third-party learning resources remain under their original rights.
