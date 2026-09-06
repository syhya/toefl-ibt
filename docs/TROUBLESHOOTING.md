# Troubleshooting

English | [简体中文](TROUBLESHOOTING.zh-CN.md)

Start with the symptom below. Keep a copy of your `storage/` before changing local data. Ordinary startup does not need a full OCR import.

| Symptom | What to check and do |
| --- | --- |
| `node` or `python3` not found | Install Node.js 22.12+ and Python 3.10+, reopen the terminal, and check `node --version` / `python3 --version`. |
| `.venv` is missing or imports fail | Run `./scripts/install.sh` from the project root. It installs dependencies inside the project. On Windows use the manual README commands. |
| `npm ci` fails | Check the required Node version and network access to the package registry. Keep `package-lock.json`; do not delete it merely to hide a dependency failure. |
| The local address does not open | Keep `npm start` running. Use `http://127.0.0.1:4173`, not a directly opened HTML file. Read the terminal startup error. |
| Port 4173 is already in use | Reuse your existing instance or stop it normally. Alternatively run `npm start -- --port 4174` and open that port. Browser permissions/language are per origin. |
| The page still has the old interface | Run `npm run build`, restart the backend, then reload. `npm start` only auto-builds when the build is absent, not after every source edit. |
| Vite starts but API requests fail | Run the backend on 4173; the development proxy is configured for that port. Vite's page normally runs on 5173. |
| The catalog is empty | Use Try the demo or `npm run demo`; otherwise import a portable pack. A public checkout has no private question bank. |
| Import says the ID exists | Identical content is safe to repeat. For changed content, use the CLI with `--replace` or choose a genuinely new ID. |
| Import rejects unknown fields | Use the portable input schema, not a generated exam JSON. Check field spelling/types against [IMPORTING.md](IMPORTING.md). |
| A JSON pack with media fails in the website | Import its folder via `npm run import:pack -- "/path/to/pack.json"`; the browser JSON importer is text-only. |
| A media path is rejected | Keep files inside the pack directory and use relative paths with `/`. Avoid `..`, hidden components, symlinks, and unsupported extensions; check size limits. |
| Audio cannot be decoded or duration cannot be read | Confirm the file opens in a media player and is a supported format. Install project dependencies. Changing a filename extension does not convert audio. |
| Private PDF import cannot find files/manifests | It only handles the original known collection and matching private `verified_*.json`; those are not shipped. Use portable packs for new content. |
| OCR is unavailable | Install Tesseract separately with English `eng` data; verify `tesseract --list-langs`. The public demo/JSON workflow does not require OCR. |
| Strict mode is disabled | Inspect resource validation. Custom packs and Essentials are untimed; source mismatches, absent audio, or unverified segmentation can disable private strict scopes. |
| An old session says its sources changed | It keeps its frozen content/history. Restore matching source assets to review/retry where required, or start a new practice using the current revision. Do not rewrite old answers to match new keys. |
| No sound plays | Check browser/site mute, OS output, preparation volume, and autoplay permission. Use the page's available retry/recovery controls; strict audio faults are recorded. |
| Microphone permission denied | Grant access for this local origin in browser settings and for the browser in OS privacy settings; select the intended input and test playback. |
| Recording shows pending/incomplete | Keep the site and service running for upload retries. Do not clear browser data. Missing segment/finalization state is distinct from audible quality. |
| Recording plays but cannot seek | Complete recordings may need local container-index rebuilding. Project FFmpeg uses stream copy; if it fails, original segments remain. |
| Deadline continued after refresh/sleep | Expected: the server owns time. Refresh does not reset a timed practice. A late answer is not accepted for the next question. |
| Review/library is blocked | Finish or explicitly end the active strict session. Its restrictions also cover other tabs/sessions. |
| Scores differ from a published ETS scale | The app reports raw reliable objective results and separate self-assessment; it does not produce calibrated official ETS scores. |
| Some question text remains English after switching to Chinese | Source material is intentionally preserved. The selector translates application chrome and help, not test content. |

## Safe diagnostics

From the repository root:

```sh
node --version
python3 --version
npm run typecheck
```

With the service running, open [the health endpoint](http://127.0.0.1:4173/api/health). A normal response identifies the local service/storage; do not paste full catalog, answers, or recordings into a public issue. Include the revision, OS/browser, concise error, and steps using the demo if possible. See [CONTRIBUTING.md](../CONTRIBUTING.md) and [SECURITY.md](../SECURITY.md).

## Backup and recovery

Wait for pending browser recording uploads, stop the service with Control+C, then copy all of `storage/`, `data/`, and `generated/`. Private imported collections also need their matching curation manifests. A running SQLite main file alone is not a complete backup because WAL may contain recent data; browser-only pending drafts are separate.

To move to another machine, restore resources and storage, recreate `.venv/`/`node_modules/` through installation, build, and start. Do not copy a virtual environment between operating systems. Keep old resource revisions referenced by historical sessions. There is no remote account from which missing local data can be recovered automatically.
