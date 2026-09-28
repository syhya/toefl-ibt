# Private source reconstruction: 2026-09-28

This reconstruction rebuilds the deleted private question bank from the retained original PDFs and recordings. It is separate from installing the public [Practice Test 1 example](../examples/ets-practice-test-1/README.md).

## Reconstruction inventory

The working inventory contains 18 archives: 15 iBT arrangements and three supplementary TOEFL Essentials archives. It lists 1,811 archival items across 1,514 native question screens. These are collection counts, not a claim of 18 independent full tests: duplicate occurrences and both branches of Paid Practice Test 1 are included. A selected exam route uses only its applicable branch. Essentials remains separate from iBT timing and scoring.

The retained collection has 321 original files. Another 72 matching original teacher audio files were restored, bringing the source inventory to 393. ETS publishes the teacher practice resources and audio downloads on its [Preparing Students page](https://www.ets.org/toefl/teachers-advisors-agents/ibt/teaching/preparing-students.html). The local inventory records the individual file identities and hashes; the website itself does not establish this collection's file count.

The default public example remains the unchanged v3 audio edition: 97 items / 79 screens. The reconstructed private collection, original materials, and private authoring records are not shipped in Git.

## Source fidelity and missing content

Original question PDFs remain unchanged. Reconstructed question text, word banks, fixed fragments, paragraphs, options, and necessary illustrations retain their source page and file identity. Full question images are review evidence rather than active question screens.

Answer-key corrections retain the supplied answer, the corrected answer, and the supporting question, passage, or audio evidence. Paper/audio wording differences remain explicit source variants. Matching filenames or question numbers alone do not prove that a recording belongs to a question. Unresolved answers are excluded from objective scoring; unavailable prompts are not replaced by invented or synthesized exam content.

Paid Practice Test 2 explicitly omits Build a Sentence questions 7–10. Two speaking prompts are absent from the supplied Essentials 2 material. These omissions are recorded separately; they are not silently filled from another test or counted as recovered questions.

Directions and scenarios are checked separately from question prompts. Existing titles inside a stimulus are not played twice. Where the supplied source has only written instructions and no matching recording, the audit records that limitation explicitly.

## Recovery evidence and backups

The recovered snapshot's proof records belong under `generated/recovery/2026-09-28/`. They bind source files and pages, reconstructed question content, derived assets, audio intervals, corrections, and remaining limitations. They are private local evidence, not public question-bank content.

Keep the following together in a dated backup:

- `data/`, including the restored original teacher audio.
- The **entire** `generated/` directory, including exams, media, extraction caches, and recovery proofs.
- The matching private reconstruction authoring inputs, correction records, and audit scripts. Preserve these outside temporary working directories before cleanup.

Also back up `storage/` to retain local attempts and recordings. Source reconstruction and historical score preservation are separate concerns.

The legacy import workflow described in [Materials](MATERIALS.md) depended on private `scripts/verified_*.json` manifests. Running that importer alone cannot recreate the newly reviewed recovery proofs from raw PDFs or OCR. Do not treat it as a substitute for restoring the complete recovered snapshot and its matching authoring backup. Routine application startup should reuse the installed generated files.

## Validation status

The installed snapshot passed all 18 source-integrity gates and recovered-data acceptance checks, including 5,004 per-item assertions. Nineteen complete API walkthroughs cover every archive and both Paid 1 routes, using isolated synthetic responses and recordings rather than personal attempts. Original-file hashes, question structure, answer checks, audio intervals, directions, deduplication counts and exclusions are checked separately.

Thirteen iBT archives support full local strict practice. Experience 2 Listening remains source-text study because one supplied conversation omits a paragraph printed in the PDF. Paid 2 Writing and full strict practice remain disabled because four Build items are missing; its other verified sections remain available. Essentials stays untimed. Eighteen disputed scoring units are retained but excluded from automatic scoring. Existing documented timing approximations are unchanged; these are not official ETS scores or calibrated adaptive tests.

The public Practice Test 1 file remains byte-for-byte unchanged. No personal attempt was created by the recovery checks. This validation does not claim a new human-microphone run or complete visual browser inspection; browser automation was unavailable because its security-policy check could not be completed. The API and component checks do not establish universal pixel-for-pixel equivalence with ETS.
