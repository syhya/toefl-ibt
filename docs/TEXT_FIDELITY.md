# Source text fidelity and transcription corrections

On 2026-09-07, two reported listening options exposed transcription defects in the private source collection. The source page says **“I’ll have to get back to you on that.”** and **“It’s a nice room.”**, while the structured text had dropped letters, apostrophes, and spaces. A structured schema or a file hash proves consistency with an imported record; it does not by itself prove that OCR copied the visible source correctly.

## Corpus review and resulting corrections

| Reviewed source group | Review scope | Confirmed field corrections |
| --- | --- | --- |
| Packs 1–3 | 246 screens; fresh English-only OCR for all source images; 1,764 text leaves compared, additional complete-option/body coverage checks, all seven cloze paragraphs and thirty Build images checked | 176 across 98 screens |
| Packs 4–6 | 251 screens; independent OCR comparison of 1,735 nontrivial fields, prompt/choice review, and complete cloze/Email/Discussion source checks | 83 across 49 screens |
| Experience, Student, Teacher, Essentials | 839 screens and 8,120 inventoried text leaves; independent source-page OCR (163 paper pages plus 286 Essentials pages), candidate visual adjudication, all seventy paper Build crops checked | 280 across 188 screens |
| Source-equivalent paid aliases | Inherit only exact matching fields from their explicitly linked canonical Pack source | 114 additional field occurrences |

The complete catalog has **1,518 question screens**. The review produced **653 field corrections on 398 screens**, including canonical aliases. A field occurrence is not an additional question. Automatic field comparison and manual visual adjudication are distinct: the record does not claim that every character was independently read by a human.

Corrections include missing initial `I`, apostrophes, merged words, truncated options, text from a following passage accidentally included in an option, capitalization, and omitted printed sentence literals/punctuation. For example, Pack 2 Reading module 1 question 14 option B was truncated to `To avoid a`; its original is `To avoid additional charges`.

Printed source anomalies such as `presense`, `assitance`, `robiotics`, `The store`, and `Artic` were retained where the original really contains them. This is a transcription audit, not a grammar rewrite or an answer-key audit. ASR-only review transcripts with no corresponding printed passage are outside the image-to-text verification scope. No audio or test timing was changed.

## Reproducible correction mechanism

The private `scripts/verified_text_corrections.json` manifest binds each change to its question ID, original material ID, physical PDF page, source SHA-256, exact field path, before/after text, and review evidence. The private PDF importer now requires this manifest with the other curation files. Reimport reapplies these exact corrections after source structuring and media attachment, before final content hashes and catalog publication. A missing/stale correction cannot silently revert the corrected catalog to raw OCR text.

The implementation is in `backend/text_corrections.py`. Allowed paths are textual leaves. Choice IDs, word-block indices, answer order, gap lengths, media URLs, and deadlines are not rewrite targets. Build reference-answer changes are restricted to capitalization-only equality; answer letters cannot change. Source-verified sentence prefaces and final punctuation are display metadata, not new response gaps.

The importer validates all correction candidates before publishing corrected exam metadata. Early raw exam/question-bank writes have been deferred. Original PDF/audio files are untouched. The complete private import and errata manifest remain excluded from Git; the selected public example subset is described below.

## Bundled Practice Test 1 subset

`examples/ets-practice-test-1/text-corrections.json` includes 71 verified field corrections across 39 of that example's 79 screens in the current v3 audio edition (the prior paper edition had 74 across 40). Its provenance and manifest bind the original material IDs/hashes; `verificationInputs.textCorrectionsPath` points to the installed subset under `generated/assets/ets-practice-test-1/`. The three removed correction occurrences belonged to the replaced paper Interview 1 prompt; its original wording stays in the audio-version comparison. A new installation does not need the full private errata file. The example's English bundle filenames do not alter correction identities or installed source references.

The later Complete the Words change only affects input presentation and normalization during new typing. The observed online phrase “than any other group activity” differs from “than of any other group activity” printed in the supplied Student 1 PDF; the extra `of` is therefore retained, not treated as an OCR error. See [the 2026-09-26 interface comparison](EXAM_UI_REFERENCE.md#live-reading-interaction-checked-on-2026-09-26).

## Existing practice and review

Current and historical question displays can apply a hash-bound correction when the original source hash/page and exact old field match. A direct review/export/feedback request refreshes the current catalog before projection. The database's original plan, submitted answers, media references, deadlines, and frozen score snapshot remain intact. Review identifies corrected text explicitly.

New practice uses the corrected source text. One corrected fixed-slot comma also makes the original valid sentence in `teacher-2-w-build-7` reachable by the existing grader; historical scores are not retroactively rewritten. Restart/review tests confirm that old selected choice IDs display the corrected option text without changing the selected ID or historical result.

## Reading layout audit: 2026-09-26

The reported Practice Test 1 workshop email had merged its salutation, body, closing and sender into one paragraph. The source PDF's physical page 10 separates them: the closing and sender each occupy their own paragraph. Its longer invitation on page 11 also has multiple body paragraphs, followed by a signature with an ordinary line break.

The review covered **32 distinct reading emails across 92 associated question screens**, including source-equivalent aliases. It restores boundaries in **23 emails / 63 screens**. Two academic passages in Teacher Practice Test 1 also lost source paragraph starts, affecting ten more screens: **25 reading texts / 73 screens fixed in total**. The two other single-paragraph academic candidates in Experience Days 2 and 3 really are continuous paragraphs and remain unchanged. No additional salutation/signoff candidates were found outside the message blocks.

This is source-specific: Pack 1's webinar signature and Student Practice Test 2's heating-maintenance signature are printed on one line and remain that way. There is no global rule that inserts a newline after every occurrence of “regards.” Two teacher emails duplicated the reading instruction inside the body; only that repeated copy is removed, while the identical preceding instruction remains visible.

`shared/reading-layouts.json` stores source identities, PDF hashes, exact normalized-text hashes and reviewed character spans. It does **not** publish private passage text or source images. `backend/reading_layout.py` applies the boundaries after transcription corrections, at the active/review display boundary; an unknown ID, different source page, changed wording or invalid span leaves the content alone. The two academic passages retain their printed hard paragraph starts without introducing extra blank lines. The renderer also preserves existing explicit newlines in messages, paragraphs, lists and dialogue.

Original question files, bundle hashes, saved session plans, choices, answers, audio, timers and score snapshots are unchanged. Existing practice and review receive the same corrected layout without reimporting materials or retiming an attempt. This audit addresses source text flow, not universal pixel-for-pixel equivalence of every source frame, font or color.

Validation: **659 checks passed** (200 UI, 424 API/security, 35 data/import), plus production build. Browser inspection on a fresh minimal-package installation confirmed the reported email's four paragraphs and the long invitation's body paragraphs and signature line break. API regressions verify active/historical consistency, unchanged stored plans and answers, source/text mismatch rejection, and all available audited source records. Local screenshots and comparison records are under `tmp/qa/reading-layout/`; they are not distribution files.

## Practice Test 1 explanation audit: 2026-09-26

All **79 current question screens / 97 items** were reviewed against their question text, passages, supplied transcripts and reference keys. The original PDF's answer tables on physical pages 14, 15, 26, 27 and 33 were visually checked. Its SHA-256 is `33e37aac4324d36a01af7ac0eb67b06aa438dfdf4fc96e31f4bdb72d9b8d9a2d`. The current grading keys remain unchanged: several defects were in the separately supplied commentary, not the key used by the application.

| Item | Finding and correction |
| --- | --- |
| Listening Module 1, question 8 | The prompt is “Did you attend the seminar?” Attend means be present at or participate in the event. A, “I overslept,” indirectly explains missing it. Unrelated next-task background had been appended to the explanation and is removed. |
| Listening Module 1, question 9 | The old commentary chose changing clothes. The question concerns the woman, who initially plans to shop; the man mentions changing clothes. The verified key remains C, “Go shopping.” |
| Reading Module 1, cloze | The commentary's `on` and `records` do not fit the given letters/gaps. The required entries remain `ly` in `only` and `ord` in `record`. Every blank now has its own grammar/context explanation. |
| Build a Sentence, questions 4 and 5 | Question 4 is a wh-question, not a yes/no question. Question 5 retains the existing source-verified, buildable answer without the extra `the` found in the printed key/commentary but absent from the word bank. The exception remains explicit. |
| Email and Academic Discussion | Remove unsupported hard rules such as requiring two reasons, a personal anecdote or a separate conclusion, and banning all contractions. Explain the actual prompt requirements and distinguish word-count advice from automatic scoring. |
| Speaking | Give each repeat sentence its own guidance and each interview its own response requirements. Interview 1 follows the selected audio edition; the retained paper question has a separate explanation. No fixed “correct” opinion or official score is invented. |

Every choice now has an answer rationale plus separate distractor reasons. Next-task headings and background are excluded; the companion importer also stops at these boundaries on future imports. The notes were initially English-only on September 26. The September 27 update adds authored Simplified Chinese counterparts: **English UI shows English explanations; Chinese UI shows Chinese explanations**, including all distractor reasons, per-blank notes, and correction notices. Both editions are explicitly labeled as reviewed project guidance, not ETS-authored commentary. They are project-authored source-based guidance, not translations presented as official commentary. The archived companion extracts remain in the original prepared package for provenance; they are not served as the current reviewed explanation.

`shared/example1-explanations.en.json` and `shared/example1-explanations.zh-CN.json` each hold 80 matching records: 79 current screens and one retained paper Interview 1. English quotations and reference sentences retain their original wording within Chinese explanations. `backend/reviewed_explanations.py` verifies a normalized fingerprint of each question, source/audio identity and key before attaching its note. A changed or unresolved key, missing translation, or translation fingerprint mismatch withholds the rationale in both languages pending another source check. The API exposes notes only through completed review/export or explicitly authorized guided feedback, not during strict questions. Displaying a note does not modify source questions, bundle hashes, saved plans, answers, deadlines or frozen score snapshots. Updating code and restarting the service is sufficient; no example reinstall/upgrade is required.

Regression checks cover all current notes, original table keys, the reported seminar item, each known commentary defect, import boundaries, language rendering, mismatch rejection and immutable historical review/export. Local source renders and audit logs are under `tmp/qa/example1-explanations/`. This is a rationale/key audit; it is not a new certification of every audio transcription, source-image pixel or ETS scoring rule.

## Verification and local evidence

- `backend/tests/test_text_corrections.py` covers source binding, exact before matching, permitted paths, direct historical review after import, restart, idempotence, and immutable saved answers/scores.
- `tests/data/test_text_fidelity.py` verifies every installed correction and the canonical aliases, including the two user-reported examples.
- The private full import reports `textCorrections` in `generated/audit.json`; all 653 changes were applied successfully.
- Local audit files and image contact sheets are under `tmp/qa/text-fidelity-20260907/`, including before snapshots, per-group correction reports, merged counts, and scoring-impact checks. These private artifacts are not bundled with public code.

See [materials](MATERIALS.md), [testing](TESTING.md), and [acceptance](ACCEPTANCE.md) for the broader application boundaries.
