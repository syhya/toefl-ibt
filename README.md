# TOEFL Local Lab

English | [简体中文](README.zh-CN.md)

**Powered by GPT-6 Astra.** This project currently uses GPT-6 Astra during development to explore the model's limits in building, testing, debugging, and documenting a complete application. Ordinary practice runs locally and does not require a model API.

A local TOEFL-style practice website with English and Simplified Chinese navigation, structured questions, writing editors, countdowns for supported curated materials, microphone recording, and saved review. Built with **React + TypeScript + Vite, FastAPI, and SQLite**. After installation and resource import, ordinary practice runs offline without accounts or cloud AI services.

**Included sample:** [TOEFL iBT® Practice Test 1](examples/ets-practice-test-1/README.md) covers all four sections with prepared audio, images, and bilingual explanations. It is ready to install without original PDFs or private materials. See the [source notice](examples/ets-practice-test-1/NOTICE.md) for attribution.

This is an independent practice tool, not an ETS product. Strict mode enforces the selected local rules; some timing values are explicitly documented approximations. It does not reproduce ETS's proprietary adaptation or convert raw accuracy into official 1–6 or 120-point scores. See [rules and evidence](docs/OFFICIAL_RULES.md).

## Quick start

Prerequisites: **Node.js 22.12+**, **Python 3.10+**, and a current Chrome or Edge browser. Internet access is needed for the initial dependency installation. Run these commands from the repository root on macOS or Linux:

```sh
./scripts/install.sh
npm run demo
npm start
```

Open **[http://127.0.0.1:4173](http://127.0.0.1:4173)**. Keep the terminal running; **Control+C** stops the service. Do not open `index.html` directly.

`npm run demo` installs the included sample and preserves existing practice records. Use **EN / 中文** to switch application controls and the sample’s explanations. Original questions and audio retain their source language.

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

## Add resources

Open **Help & setup** to import a text-only JSON pack, or use the CLI for a folder with audio, images, video, or source PDFs:

```sh
npm run import:pack -- "/absolute/path/to/my-practice/pack.json"
```

Refresh the website and select the imported title. Custom packs are untimed guided resources. To update a changed pack with the same ID, add `--replace`; existing sessions retain frozen content and revisioned assets. Start a new practice to see updated content.

See the [import guide](docs/IMPORTING.md) for supported question types, media, updates, and backups. To author your own questions, start with the [minimal JSON example](docs/IMPORTING.md#minimal-complete-pack).

## Practice and review

- Start a whole available archive or use **R / L / W / S** for one section. The task library groups consecutive questions by source test, module/part, and category; each entry starts the complete group.
- Guided practice supports pause; specialized sessions offer audio replay and instant answers only when explicitly enabled before starting. Full-test sessions keep those aids off; completed-session review remains available. Strict mode is available only for eligible curated scopes and uses server deadlines and navigation restrictions. Supplementary resources, including custom packs and Essentials, stay untimed.
- Timed reading blanks retain one underline per missing letter while editing, expand to monospace input, and contract completed answers to paragraph text on blur; choices preserve source text. Sentence building supports tokens and fixed fragments. Email/discussion use split source/editor layouts and word count.
- Speaking saves local recording segments, tracks incomplete uploads, and supports playback/download. Test the real microphone on this local site before relying on it.
- History preserves accepted answers, objective results, writing, recordings, and rubric self-assessment. A mistake collection retains previous errors and later mastery.

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

The application has no cloud sync or multi-user authentication. Keep it local, and keep personal materials, generated catalogs, recordings, and private curation files out of Git. MIT applies to project code; third-party learning resources retain their original rights. See the [security policy](SECURITY.md) and [materials guide](docs/MATERIALS.md).

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

## Documentation

The [documentation index](docs/README.md) provides an overview of the available guides and technical references.

- [User guide](docs/USER_GUIDE.md): Learn how to choose a practice mode, work through each section, record speaking responses, review results, and back up your progress.
- [Import guide](docs/IMPORTING.md): Create and import question packs, attach media, and update existing resources.
- [Troubleshooting](docs/TROUBLESHOOTING.md): Resolve installation, startup, microphone, playback, and recording-recovery problems.
- [Architecture](docs/ARCHITECTURE.md): Understand the frontend, local API, database, session lifecycle, and scoring design.
- [Testing](docs/TESTING.md): Run automated checks and use the browser verification workflows.
- [Changelog](CHANGELOG.md): Review features, fixes, and release notes.

## Contributing

Bug reports, feature suggestions, documentation improvements, and pull requests are welcome. Read the [contribution guide](CONTRIBUTING.md) for development setup, coding conventions, and the checks to run before submitting changes.

Please follow the [Code of Conduct](CODE_OF_CONDUCT.md) when participating. To report a vulnerability, follow the reporting instructions in the [security policy](SECURITY.md).

## License

The project source code is released under the [MIT License](LICENSE). The bundled Open Sans font is distributed under the [SIL Open Font License](public/fonts/OFL-OpenSans.txt).

Third-party questions, audio, images, and other learning resources remain subject to their original rights and licenses. See the [materials guide](docs/MATERIALS.md) for attribution and source information.
