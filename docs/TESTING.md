# Testing and local acceptance tools

English | [简体中文](TESTING.zh-CN.md)

## Standard checks

```sh
npm test
npm run build
```

`npm test` runs type checking, UI tests, backend/security tests, and source/import tests. For focused work:

```sh
npm run typecheck
npm run test:ui
npm run test:api
npm run test:data
```

API tests use temporary directories and independent SQLite files. Source tests read the private collection without adding test questions. A public checkout skips checks whose private materials/manifests are absent; report those as skips, not as validated private content. The CI workflow installs dependencies in `.venv/` and runs tests/build on a clean public checkout.

The historical 2026-09-05 log `tmp/qa/client-expiry-v5-tests.log` records 80 UI, 146 backend/security, and 28 data/import checks: 254 total. Those counts belong to that code snapshot. After a change, run relevant checks and record the actual results; do not reuse historical counts or screenshots to claim the new version passed. See [ACCEPTANCE.md](ACCEPTANCE.md).

## Important behavioral coverage

- Server deadlines, Begin transitions, automatic stage continuation, one-time source playback, stale/current-question requests, idempotence, background intervals, and recovery.
- Source/curation hashes, original direction bindings, response clocks starting after directions, and preservation of reading content embedded in instructions.
- Missing-letter inputs, token drag/reorder, duplicate tokens, fixed text/punctuation, editor word count, internal clipboard, and undo/redo.
- Frozen objective `scoreSnapshot`, restart and scoring-engine changes, explicit `legacy-recomputed` history, late recordings, and self-assessment including valid zero scores.
- Mistake eligibility, mastery/repeated mistakes, last-error review, version changes, and strict isolation; objective and self-assessed section summaries remain distinct.
- Same-question final video frame retention and clearing on question change.
- Bilingual application chrome and custom-resource import behavior, with original question content preserved.

Synthetic fixtures and test audio must be explicitly identified and kept out of real `data/`, `generated/`, and user `storage/`. The intentionally bundled public demo is separately identified as original demonstration content; it is not one of the private source archives.

## Browser fixture with an adjustable test clock

These source-based QA tools require the private Experience 1 collection and are not required for ordinary installation or public CI.

```sh
npm run build
.venv/bin/python scripts/e2e_fixture.py serve --reset --port 4176
```

Open [the isolated fixture](http://127.0.0.1:4176). It uses `tmp/qa/e2e-sandbox` with independent source snapshots and SQLite. Each reading route contains two real source screens representing branch/task behavior, not a full official test. In another terminal:

```sh
.venv/bin/python scripts/e2e_fixture.py advance 700
.venv/bin/python scripts/e2e_fixture.py status
```

The fixture clock in `tmp/qa/e2e-clock.json` also advances with real time. Production has no HTTP clock-setting endpoint. The 420-second Email, 600-second Discussion, and 45-second Interview rules are not shortened; only the isolated clock moves. `tmp/qa/e2e-fixture-manifest.json` contains QA source/answer information and is not served by the production API.

After changing the frontend:

```sh
npm run build
.venv/bin/python scripts/e2e_fixture.py sync-ui
```

Confirm the browser loads that build. Stop the old fixture before rebuilding with `--reset`; reset only rebuilds its marked tool-owned temporary directory. Do not combine old sessions, screenshots, and build hashes into evidence for a new revision.

## Explicit synthetic microphone

```sh
.venv/bin/python scripts/e2e_fixture.py serve --synthetic-mic --port 4176
```

This is off by default. It injects a Web Audio sine source only into the temporary fixture and displays **E2E / SYNTHETIC MICROPHONE**. It does not open the real microphone. Stopping tracks closes the oscillator/AudioContext, and `sync-ui` retains the chosen mode. Production source, build, and main service do not contain this injection.

A natural-window test uses normal-speed original media and lets the server expire the recording window; do not advance, skip, refresh, or pause that run. Three historical rounds of seven repeats plus four interviews covered MediaRecorder, automatic stop, segments, final markers, and playback. The v4 report `tmp/qa/2026-09-05-source-ui-speaking.json` records the build, no-fast-forward evidence, and visual limits at the time.

A synthetic run does not establish real microphone permission, input selection, or voice quality. Calibration in ETS does not validate this local app. Sampler visual observation did not record/upload a person's voice.

## Real-time server workflow

```sh
.venv/bin/python scripts/realtime_smoke.py
```

This uses port 4175, temporary SQLite, copied catalog/backend, authorized source media, and natural deadlines for Experience 1. Default maximum is three hours; progress/result is `tmp/qa/realtime-report.json`.

The current tool copies derived assets and hard-links only unchanged original files. An earlier 4,127.039-second run also hard-linked derived assets, as its report notes. That was an HTTP/server test: it did not play sound, operate a browser, or test a microphone. It does not validate later v4/v5 features. Temporary databases/links are removed at completion, retaining reports without user answers.

## Actual catalog, isolated user records

```sh
.venv/bin/python scripts/qa_full_catalog_preview.py --port 4177
```

Open [the preview](http://127.0.0.1:4177). This uses actual `data/`, `generated/`, and `dist/`, source gates, and natural time, but redirects SQLite/recordings to `tmp/qa/full-catalog-preview/storage/`. It does not inject questions or synthetic audio or write QA answers to 4173. Ordinary practice still uses `npm start`.

Check representative viewport sizes, internal material scrolling, blanks, tokens, long-writing editors, and speaking timers. Current source-based examination presentation uses local Open Sans and a 1024×768 proportional canvas. DOM geometry alone is not visual proof. Existing `output/playwright/official-*.png` files cover tasks but some predate font, canvas, directions, or final-frame changes; always identify the build.

Historical `tmp/qa/final-video-frame-ui.json` records a natural original-video → 45-second response → automatic stop check, with a PNG matching the source frame and playable audio. Question-change clearing has separate UI regression coverage. The tested local build predates later listening changes.

## Official reference and device boundaries

The authorized Sampler review covered welcome, volume, three reading tasks, listening playback/answers, Build, Email, and Discussion. Public CSS directly supports Open Sans and 1024-pixel width; 768 height is derived from toolbar/content structure and supported by the observed 4:3 canvas. Ordinary body text was compared at 16px/21px line height, with source-specific content styles retained.

Observed Reading/Listening/Build screens had no timer; Email first showed 06:56 and Discussion 09:34 remaining. Do not convert these remaining values, missing local clocks, or Sampler counts into production specifications. Email's Time Remaining screen retains the countdown and editor/undo state through Back. Listening's visible disabled choices during short-response playback and manual unanswered Next checks must not prevent server expiry. See [EXAM_UI_REFERENCE.md](EXAM_UI_REFERENCE.md).

A complete source-archive browser/restart test passed for the recorded build. Real microphone/voice quality and physical sleep/network-loss scenarios remain distinct. Neither tests nor layout observations reproduce ETS's proprietary calibration, adaptation, or scoring. See [rules](OFFICIAL_RULES.md) and [materials](MATERIALS.md).

## Full source-archive browser acceptance

```sh
.venv/bin/python scripts/qa_full_catalog_preview.py --port 4185 --tag final-full-20260905
.venv/bin/python scripts/qa_full_exam_browser.py --port 4185 --browser final-full-exam
```

The preview writes only SQLite/recording data under its tagged temporary storage. Before running the driver, prepare an isolated headless browser named `final-full-exam` with explicitly injected synthetic microphone and media telemetry, choose complete strict practice, and stop on the first Reading Begin page. This is an advanced QA prerequisite, not an automatic general-purpose launch command. QA-only `tmp/qa/final-full-exam-answers.json` uses original verified objective keys and two test essays, not official model responses; never import it into the catalog.

The driver types letters, selects original choices, moves tokens, and uses the editor through the UI, waiting for save before normal Next. It does not write answers directly through the API, skip audio, or accelerate time. Speaking stops naturally. Early normal submission means the total run is shorter than exhausting every timer; do not call automation duration the official test duration.

Terminal checks cover all sections, 68 non-speaking answers, 84 original objective units, eleven matching complete recordings, browser errors, source/build hashes, real token reordering, and Email Back preservation. Reports live in `tmp/qa/final-full-exam-browser/`; an earlier layout-discovery pass remains separately in `tmp/qa/full-exam-discovery-20260905/`.

The 2026-09-05 pre-expiry run completed nine stages / 79 screens / 97 units in 1,157.197 seconds, with 43 original media playbacks, eleven decodable recordings, objective 84/84, restart consistency, and fifteen terminal checks. The later v5 command added `--exercise-writing-expiry academic_discussion`; it ran 1,793.006 seconds, naturally consumed Discussion's 600 seconds, then continued to Speaking. Its final summary superseded the prior one at `tmp/qa/final-full-exam-browser/summary.json`. Subsequent modal CSS/version-label checks used separate evidence; `tmp/qa/writing-expiry-visual/summary.json` explicitly used a test clock and is not a second natural ten-minute wait.
