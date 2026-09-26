# Local materials and import validation

This document describes the original private collection and its specialized importer. New users should install the [bundled Practice Test 1](../examples/ets-practice-test-1/README.md); use [portable resources](IMPORTING.md) for additional custom content. The full-collection counts below are dated private snapshots, not the size of the example. Private original bytes, generated banks, OCR, and full curation manifests stay local, except for the explicitly prepared example subset described next.

## Included example versus private collection

`examples/ets-practice-test-1/` contains one native `student-1` exam: 97 items / 79 screens and 52 prepared assets (33 WAV, 16 JPG, 3 PNG). Four metadata JSON files make **56 required hash-checked files, 17,818,617 bytes**; the manifest and two Markdown files are additional. The 13 original sources (2 PDFs / 11 MP3s) are optional references and remain excluded from Git. No private source collection or original-file download is required.

Optional local original filenames are English. The manifest maps them to unchanged installation paths; original material IDs, bytes, source URLs, and existing private filenames remain compatible. The bundled correction subset covers 40 screens / 74 fields. Companion explanations/audio have separate attribution from the ETS-hosted question paper. See [source notice](../examples/ets-practice-test-1/NOTICE.md).

## Dated private inventory

The 2026-09-05 inventory contained 396 files: 393 learning resources and three excluded `.DS_Store` files. Resources comprised 56 PDFs (1,582 pages, 1,348 scanned/not directly extractable), 319 audio files, and eighteen videos. All 321 resources in the 2026-09-02 baseline retained their bytes; 72 original MP3s were added from ETS's matching teacher audio packages.

## Repeatable private import

Install the import requirements and Tesseract's English language data, then run from the repository root:

```sh
.venv/bin/python scripts/import_materials.py --ocr-all --jobs 6
```

Normal startup reuses `generated/` and does not rerun OCR or upload questions/recordings. The teacher supplement resides in its source directories' `official-audio/`. `.venv/bin/python scripts/attach_teacher_audio.py` verifies the 72 originals offline; `--install` only fills missing files from a matching local official ZIP and does not overwrite different content. Its private manifest binds official links, package/file hashes, PDF pages, and original transcript hashes. Audio is attached after structured verification, active transcripts are removed, and strict capability is then computed.

A changed PDF or a cache without matching source hash requires fresh page rendering. Pack column OCR also binds the actual rendered page hash. Old unbound caches are not relabeled as current. Routine startup does not invoke extraction.

`scripts/attach_pack_directions.py` restores Pack/Paid directions after structured validation. Its private manifest preserves source rules/scenarios, pages, and explicit source-audio intervals: 33 modules retain text; 44 audio segments serve 22 modules and thirteen listening groups. Group titles play only at group start and do not consume answer time. Missing reliable direction audio remains text; it is not synthesized.

Back up `data/`, complete `generated/`, and matching `scripts/verified_*.json` together. The September 5 snapshot used ten private curation manifests; the later source-text repair added `verified_text_corrections.json` to the full private import contract. The public example instead has its own self-contained metadata subset. Automatic audio verification and `humanReviewed` are distinct. Missing or mismatched hashes close affected strict scopes and require recheck, rather than inventing questions from OCR or numbering.

## Outputs

| File | Purpose |
| --- | --- |
| `generated/catalog.json` | Base resources, archives, supplementary catalog, capabilities/limits |
| `generated/exams/*.json` | Original order, source file/page/number, module, audit status |
| `generated/question-bank.json` | Deduplicated content with occurrence references |
| `generated/deduplication.json` | Duplicate references, key conflicts, resolutions/evidence |
| `generated/audit.json` | File coverage, counts, keys, assets, media links, strict eligibility |
| `generated/extracted/*.json` | Native/OCR text and page coordinates; not an active answer endpoint |
| `generated/media-segments.json` | Source intervals, confidence, excluded waits, version differences |

Portable packs add `generated/pack-catalogs/` registries; their authoring validation is separate from the curated private pipeline. Complete exam JSON includes review keys and must never be sent directly to an active frontend. API allowlists generate legal current content; answers, explanations, and transcripts are available through review.

## Data conventions

- `source.page` is a one-based physical PDF page; `source.originalNumber` preserves printing. Missing/restarted source numbering is recorded separately from local ordering.
- `type` selects the interaction; `taskType` distinguishes the twelve new-format tasks, including daily/academic reading and response/conversation/announcement/talk listening.
- Cloze retains `prefix`, optional `suffix`, `missingLetters`, `fullWord`, `length`, and `acceptedAnswers`. A `{{blankId}}` replaces only missing letters, exactly once. Unresolved private-source keys remain `null` with conflict evidence and are excluded from objective denominators.
- Build preserves original token order, duplicates, extras, and fixed text. `{id: ...}` is a token slot; `{fixed: ...}` is printed text. `expectedTokenOrder` belongs to review/scoring and never active output. Validation checks whether original tokens/fixed words can form the supplied reference; punctuation/case alone should not create false errors. Source contradictions retain `sourceReferenceAnswer`, `answerConflict`, and `resolutionEvidence`.
- Reading paragraph relations and spacing are retained. A screenshot does not establish reliable structure. All 1,518 dated private screens were structured.
- `audio` references original or verified segmented media. Shared passages use `groupId` and play once per group. `cueAudio` is separate; source response waits are excluded from the stimulus.

## Structured presentation and source images

`presentationSchema: structured-v1`, `structuredContentStatus`, and typed `stemBlocks` describe paragraphs, messages, dialogue, lists, tables, highlighted sentences, form diagrams, and questions. Existing choices/templates/tokens/slots remain interactive. Source-verified curated entry requires page-level evidence, not one OCR pass.

Full-question crops are `sourceEvidenceAssets` with `reviewOnly: true`. Active images are only necessary high-resolution source photographs, people, scenes, and maps with `role: essentialVisual`, `highResolution: true`, specific semantic `alt`, and an `essential_visual` block or dialogue `avatarAssetIndex`. Text, tables, highlights, and form positions are HTML/DOM content, not full-question screenshots.

All eighteen Discussion tasks retain professor/two-student turns and portrait indices `[0,1,2]`: 54 occurrences reuse 48 crops from sixteen unique source pages, with Paid versions reusing corresponding Pack sources. Sixty Pack Build tasks and twenty Paid references retain 160 portrait occurrences from 120 source crops, in original speaker order. Paper tasks without portraits receive no invented people. Missing punctuation is restored as fixed slots after source review, without adding blank positions/tokens/keys.

Pack 4 Daily Q11–12 share the original 184×184 social-post icon from physical p. 4; the p. 5 occurrence records `stimulusSource`. Frames, scrollbars, and phone outlines are UI, not screenshots of whole text.

Each structured record binds source SHA, physical page, pre-import identity, and old crop SHA; cross-page materials retain `stimulusSource`. Visuals additionally bind normalized crop bounds, scale, output hash, and dimensions. `extract_structured_visuals.py` rebuilds at source resolution, not by enlarging old JPEGs; missing specs or identity mismatches fail import.

UI font evidence is separate from question provenance. Current observed public-client CSS confirms default Open Sans, stored locally with its license; embedded source fonts remain source-specific. See [interface evidence](EXAM_UI_REFERENCE.md).

## Scores, snapshots, and mistakes

Sessions freeze the selected route's original content, keys, answers, and source digest. New completion/termination saves objective `scoreSnapshot` once, including numerator/denominator, engine version, and time. Later keys/code do not silently recalculate it. Older records without snapshots are labeled `legacy-recomputed`, using their old content with current scoring code, without writing a false historical snapshot.

Late valid audio and self-assessment may update review/recording completeness but not frozen objective counts. Source integrity, score snapshots, and recording completeness are separate states, none equivalent to ETS certification.

Mistakes include completed, actually answered, reliably scoreable objective errors. Unanswered items, only unresolved blanks, and subjective self-scores are not false objective mistakes. Correct retries mark mastery while retaining error count and last-error review; later errors can reopen review. Text/media/key changes produce different versions, preserving old records and disabling unmatched direct retries.

## Collection limits

The fifteen iBT arrangements include duplicates and genuine upper/lower branches; they are not fifteen independent unique tests. Original folder names containing “paid” remain source identifiers, not purchase/membership features. Three Essentials archives are supplementary and never use iBT strict/adaptive timing or scoring.

Fourteen iBT arrangements became strict-eligible after teacher audio supplementation. Student 1 remains ineligible for a complete strict mock because Interview Q1's paper/audio versions disagree. Teacher Listening/Speaking's ninety existing tasks expose only original printed instructions/questions/choices while transcripts remain review-only. Three source MP3s with trailing wait use auditable WAV intervals; full originals stay archived. Missing/changed media disables affected strict scopes rather than generating substitute official questions.

Objective counts are practice comparisons; long writing and speech use rubric self-assessment, not uncalibrated official 1–6/120 conversion. Final interactive/deduplicated counts, branches, issues, and eligibility come from the particular import's `audit.json`, not the phrase “included in the catalog.”
