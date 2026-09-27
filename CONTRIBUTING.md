# Contributing

Contributions to usability, localization, accessibility, import tooling, documentation, and reliability are welcome. Start with the [README](README.md), [architecture](docs/ARCHITECTURE.md), and [testing guide](docs/TESTING.md).

## Development setup

Use Node.js 22.12 or later and Python 3.10 or later. From the repository root:

```sh
./scripts/install.sh
npm start
```

For frontend development, keep the backend running in one terminal and start Vite in another:

```sh
.venv/bin/python -m backend --port 4173
npm run dev
```

Vite proxies `/api` to the local service. The bundled TOEFL iBT® Practice Test 1 is the complete newcomer reference set; the rest of the original private exam collection and its full curation manifests are not part of a public checkout. See [resource import](docs/IMPORTING.md) to author or install your own content.

## Making a change

1. Describe the problem and expected behavior in an issue, or explain a small fix directly in a pull request.
2. Use a focused branch, such as `codex/improve-import-errors`. Keep unrelated formatting and content changes out of the patch.
3. Read the code around the change. Preserve frozen session rules, server-owned deadlines, recording integrity, and active/review content separation.
4. Keep English and Simplified Chinese UI text and the root README versions synchronized. Maintain every other Markdown document in English only. Keep exam prompts, names, answers, and source evidence in their original language. Maintain the English and Simplified Chinese project-authored explanation manifests together, with matching question fingerprints and equivalent reasons and correction notices.
5. Add meaningful regression coverage for changed behavior. A visual adjustment can be verified in the browser; do not add a test merely to duplicate CSS values.
6. Run the relevant tests and production build, and report exactly what ran and what was skipped.

```sh
npm test
npm run build
npm run check:docs
git diff --check
```

Private source-data tests skip when their materials are absent. That is expected for public contributions and is not proof that a private collection passed validation. Do not copy private assets into the repository to make those tests run.

## Code and comments

Use TypeScript for frontend contracts and Python for the local API/import logic. Follow nearby naming and formatting. `npm run format` formats the supported frontend files; review its diff before including unrelated changes.

Write new technical comments and docstrings in clear English. Explain why an invariant exists: for example, why a late answer is rejected, why a source hash is checked, or why an audio group plays only once. Keep comments accurate when behavior changes. Prefer small functions with explicit inputs over hidden global mutations. Never encode an answer key in a display-only field.

## Materials, rules, and licenses

Only contribute material you have the right to distribute. Keep private PDFs, OCR text, additional third-party question banks, answer keys, personal recordings, credentials, and account-specific URLs out of contributions. The deliberately bundled TOEFL iBT® Practice Test 1 is listed in its [source notice](examples/ets-practice-test-1/NOTICE.md); corrections should retain its source identity and attribution. The MIT license covers project code, not third-party exam content; font licenses are kept with their files.

When changing the bundled example, keep every required manifest-listed derived/metadata file, preserve hashes for unchanged bytes, and update the exporter's English filename mapping. Verify installation in a clean directory without private resources before claiming that a checkout is self-contained. Only the allowlisted lightweight profile can omit originals through its verified provenance contract. Do not expand that exception to private archives or ignore missing required runtime files.

A new timing or scoring claim needs a primary source and an evidence classification. Observed remaining time does not prove initial time. Do not relabel a local approximation as an official rule, create missing source questions, or claim ETS score conversion without validated evidence. Source-specific import changes should retain original identity and auditable correction records.

## Pull request checklist

- Explain the user problem, change, and resulting behavior.
- List tests, browser checks, skips, and relevant limitations.
- Include before/after screenshots for layout changes, with no private content unless authorized for publication.
- Update English documentation; keep the root README and interface text synchronized in both languages.
- Confirm no personal materials, answer records, large generated files, secrets, or unrelated files are included.

No automated deployment or publishing is required. A maintainer reviews the contribution before merging. For security issues, use [SECURITY.md](SECURITY.md) instead of posting sensitive details publicly. Everyone participating follows the [Code of Conduct](CODE_OF_CONDUCT.md).
