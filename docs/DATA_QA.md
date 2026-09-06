# Source-material and question-bank acceptance

English | [简体中文](DATA_QA.zh-CN.md)

Latest material review: 2026-09-05 (Asia/Shanghai). This is a dated audit of the private source collection, which is not distributed with the public repository. The first full content review used a stable 2026-09-01 00:26:22 snapshot; all eighteen archives migrated to structured content on 2026-09-02. September 5 rechecked sources/manifests, fixed cache provenance and scene alternative text, and added matching ETS teacher audio. The original 321 resources, answers, and counts were preserved except explicitly source-audited presentation corrections described below.

The final read-only catalog SHA was `19338201ba3ebfb6cf59324df45819782f92846fa7f01df8d07c933f334f7843`; all eighteen runtime source gates passed. That check did not modify sources, generated data, manifests, or user records. Earlier counts/test totals below remain historical, not current expectations for newly imported portable packs.

`tests/data` covers sources, manifests, teacher active/transcript isolation, and cache behavior using temporary plain-color PDF pages. AES PDF page counts and all eighteen Discussion portraits were checked without encryption-related skips; the PDF dependency is `pypdf[crypto]`.

## Snapshot inventory

| Scope | Count |
| --- | ---: |
| Files in catalog | 396: 393 resources, three excluded system files |
| Original PDFs | 56; 1,582 pages, 1,348 requiring OCR |
| Original audio/video | 319 / 18 |
| Effective original bytes | 843,308,067 |
| Archives | 18: fifteen iBT arrangements, three Essentials |
| Item occurrences | 1,815: iBT 1,529, Essentials 286 |
| Deduplicated questions | 1,608 based on existing source relations |
| Question screens | 1,518; each cloze blank counts as a unit but one paragraph is one screen |
| Unique essential visuals / primary question audio URLs | 469 / 607; audio excludes directions, cues, full-track references |
| Cross-edition reused screens | 161, with `editionSource` page/hash/link |
| Complete local strict archives | 14 |
| Curation files / derived hashes | 10 / 1,886 |
| Runtime source gates | 18/18; passing does not make Essentials or mismatched tasks strict-eligible |

| Archive | Units | Screens | Scoreable objective units | Local strict |
| --- | ---: | ---: | ---: | --- |
| experience-1 | 97 | 79 | 84 | Yes |
| experience-2 | 97 | 79 | 84 | Yes |
| experience-3 | 97 | 79 | 84 | Yes |
| pack-1 | 106 | 79 | 93 | Yes |
| pack-2 | 100 | 82 | 87 | Yes |
| pack-3 | 103 | 85 | 88 | Yes; two ambiguous blanks excluded from scoring |
| pack-4 | 103 | 85 | 90 | Yes |
| pack-5 | 101 | 83 | 88 | Yes |
| pack-6 | 101 | 83 | 88 | Yes |
| paid-1 | 136 | 100 | 123 | Yes; inventory contains both branches |
| paid-2 | 100 | 82 | 87 | Yes |
| student-1 | 97 | 79 | 84 | No; one speaking paper/audio mismatch |
| student-2 | 97 | 79 | 84 | Yes |
| teacher-1 | 97 | 79 | 84 | Yes, with matching ETS supplement |
| teacher-2 | 97 | 79 | 84 | Yes, with matching ETS supplement |
| essentials-1 | 96 | 96 | 74 | No; non-iBT supplement |
| essentials-2 | 94 | 94 | 74 | No; two additional missing-prompt tasks excluded |
| essentials-3 | 96 | 96 | 74 | No; non-iBT supplement |

This is source inventory, not the uniform item count of one official test. Paid 1's upper/lower stock does not all play in one session. Writing/speaking do not receive simulated official automatic scores. Only one Student 1 mismatch retained `referenceOnly`; ninety former teacher text-reference screens gained original audio with active transcripts removed. Two truly missing Essentials prompts reside in `excludedTasks` outside interactive counts.

## Automated coverage

```sh
.venv/bin/python -m unittest discover -s tests/data -v
```

The private checks verify:

1. The expected eighteen source archives, unique question IDs, and no E2E/synthetic/placeholder archive inserted into the private bank.
2. All 393 effective files' path, size, SHA and disk/catalog agreement, and reread PDF page counts.
3. Original PDF/page/printed numbering for each question; 92 screens without printed numbers have explicit differences rather than invented printed IDs.
4. Item/screen/interactive/scoreable/module counts and Essentials interactive-plus-excluded totals.
5. Question/direction/cue asset existence, source hashes, intervals, WAV decodability and duration; direct originals are covered by original-file hashes.
6. Nested section/module/reference links, excluding private `_analysis` or test-fixture paths from question assets.
7. Canonical and `editionSource` resolution for 161 reused screens.
8. One cloze placeholder per blank and consistency of given letters, missing letters, suffix, and full word.
9. Choice keys in original option IDs and reference Build sentences constructible from original tokens/fixed positions, without inferring a unique new answer.
10. Essentials remains supplementary, non-strict, untimed, with absent prompts excluded.
11. All 1,518 structures match private source identities, display fields, old crops, and necessary-visual hashes; not merely a verified label.
12. Ninety teacher active listening/speaking blocks allow original instructions/questions only. Reintroducing transcripts to an in-memory copy fails the gate; absent media disables its strict scope.
13. Temporary plain-color PDFs cover source-changed rerender, same-source cache reuse, unbound legacy cache rejection, and Pack column cache invalidation by page-image hash.
14. Thirty-three Pack/Paid directions match manifests, reattachment is repeatable, missing manifests close affected strict scopes, and answer time begins after directions/stimulus.

Public checkouts without private inputs skip the source checks and do not inject fake questions to make them pass. If import is changing the snapshot, wait for completion and rerun.

## Content and crop review

Thirteen Pack cloze passages/130 blanks were checked against images, reference keys, given letters, and gray widths: 128 have usable keys, two remain conflicting. Paid lower-branch crops were sampled including original answer pages; active crops did not expose complete answer PDFs, and reused questions kept canonical/source-edition evidence.

All 359 Essentials question-PDF pages were processed into structure without inventing prompts/options. Original True/False/Not stated labels remain. Fifty-five speaking crops were scanned for sample/annotation leakage, with writing/picture/speaking areas visually sampled and boundaries corrected. Fifty-four listening segments cover ninety questions; 37 recoverable speaking prompts came from explicit original track regions. Ninety-one audio assets passed PCM/duration checks, with longest internal quiet gap 3.98 seconds; model responses and long waits were excluded.

Prompt/passage/template/choice/token scans found no suspicious answer-key, sample-response, annotation, or test-marker leakage in the final snapshot. These scans aid but do not replace semantic image/audio review.

## Source issues and handling

| Issue | Handling |
| --- | --- |
| Two Pack 3 cloze keys conflict with letters/context | Preserve candidates/evidence, keep null answers out of scoring, retain timed source tasks |
| Another Pack 3 inflection and Pack 1 ending differ from printed key | Source widths/images/parallel edition support an explicit correction; original key retained |
| Student 1 Interview Q1 is a different paper/audio prompt | Preserve mismatch and reference scope; no generated replacement; no complete strict archive |
| Two teacher directories originally lacked audio | Add 72 matching original ETS MP3s on 2026-09-05 without overwrite/new questions; gate active transcripts before strict eligibility |
| Paid 1 M1 Q13–14 audio is another announcement | Retain mismatch; use disclosed verified canonical Pack source override |
| Some Paid choice keys conflict with question/audio | Preserve edition/parallel/audio evidence; validate provided corrections, not infer a new unique key |
| Pack 1 Repeat Q6 paper omits an opening audio word | Keep the complete single stimulus and traceable difference |
| Essentials 2/3 first five transcript references swapped | Correct reference links only; preserve question/audio and `sourceMismatch` |
| Essentials 2 Speaking Q14/Q17 prompts unrecoverable | Use neighboring numbering, example boundaries, silence, and ASR evidence to exclude tasks; do not derive prompts from examples |
| Missing/skipped/restarted printed numbers | Keep printed facts separate from application order |

Verification establishes traceability, structural/count consistency, accessible assets, and handling of known gaps. Local ASR/acoustic/source alignment is not word-by-word human listening: `humanReviewed` remains distinct. It cannot guarantee every OCR glyph or second of audio. Calibration, equating, proprietary routing, and official scores are outside this audit. See [rules](OFFICIAL_RULES.md) and [media methodology](MEDIA_SEGMENTS.md).

## Historical migration batches: 2026-09-02

**Status metadata.** After capability auditing, stale development messages were replaced with actual media/availability limits. Teacher missing-audio warnings were accurate then and later resolved on September 5. Eighteen Essentials read-aloud tasks were correctly recognized as not needing a model stimulus in that private workflow. Only top-level descriptions/validation/catalog metadata changed; all eighteen normalized `sections` hashes and six curation/asset expectations stayed unchanged. Sixteen data/strict-isolation checks and eighteen runtime gates passed; the 4177 preview read the result without touching 4173. Evidence: `tmp/qa/final-warnings-metadata-audit.json`.

**Cloze instructions.** All 33 iBT cloze passages were checked. Thirteen Pack sources and five reused occurrences still said full words were accepted despite missing-letter-only inputs. Eighteen prompts were replaced with the exact source instruction; thirteen canonical instructions updated without changing content IDs. Only prompts changed; templates, letters, full words, keys/conflicts, scoring, and times stayed equal. Sixteen checks/eighteen gates passed. Evidence: `tmp/qa/cloze-instruction-audit.json`.

**First structured batch.** Experience 1/2/3 and Student 2's 316 screens gained source-bound structure. Sixty-six text screenshots moved to review, with no essential visual needed in this batch. It restored eight cloze templates, forty Build dialogue contexts, Student 2 messages/articles, and eight long-writing tasks, without deriving text from answers. Pre-import identity/hash checks rejected changed sources. Sixteen data/isolation checks, sixty backend checks, build, and isolated active/review checks passed. Evidence: `tmp/qa/structured-first-batch-audit.json`.

**All structured screens.** All eighteen archives / 1,518 screens became structured and source-verified, zero structural errors or active legacy full-question images. Review retained 1,084 crop references. At that snapshot, 580 essential-visual occurrences reused 348 source crops (iBT 449/229, Essentials 131/119), including Discussion 54/48. All were scale-4 crops with bounds/source/output hashes/dimensions and no question/answer/control leakage. Eight Essentials form diagrams became DOM; shared clean crops retained provenance. All 42 Essentials Build tasks remained fillable, including three with four slots and one extra token. Teacher text-reference tasks still existed then, before September 5 audio migration.

The repeatable import yielded 1,815 occurrences / 1,518 screens / 1,608 unique questions, twelve then-strict archives, eight curation files, and 1,718 derived hashes. Portrait checks covered eighteen tasks, `[0,1,2]`, dimensions, and semantic alternatives; eleven data checks passed. Isolated API checks covered form diagrams with original sound and current-only visual/audio access. Evidence: `tmp/qa/final-structured-materials-audit.json` and batch `structured-*-audit.json` files.

## September 5: source cache and scene text

All originals and 1,518 manifests were reread; sixteen directly rendered screens sampled all twelve iBT task types and supplementary types. A verified label means a source-bound local record, not universal human approval of every glyph/second.

Two cache defects were fixed: changed PDFs could reuse same-name old page images, and Pack column OCR depended only on question/cache version. Both now require matching actual source/page-image hashes; unbound caches cannot become current. Five regressions used temporary solid-color PDFs without re-OCRing real questions.

Pack 1 Repeat's scene alternative text incorrectly said airport. Seven pages 92–98 and Paid 1 p. 22 directly showed the art museum. Only 77 `alt` fields across fourteen occurrences and their relevant digests changed; images/audio/text/keys/timing/identity/eligibility stayed equal. Evidence: `tmp/qa/museum-alt-20260905/audit.json`.

## September 5: teacher audio supplement

The [ETS teacher resource page](https://www.ets.org/toefl/teachers-advisors-agents/ibt/teaching/preparing-students.html) linked matching [Test 1](https://www.ets.org/content/dam/ets-org/pdfs/toefl/teacher-practice-test-1-audio-file.zip) and [Test 2](https://www.ets.org/content/dam/ets-org/pdfs/toefl/teacher-practice-test-2-audio-file.zip) ZIPs. Together they supplied 72 MP3s / 13,624,909 bytes: per archive, 23 listening stimuli for 34 questions, eleven speaking stimuli, and two directions. No original file was overwritten and no item was added.

Manifests bind package CRC/SHA, each file, source PDF/pages/numbering, and transcript hashes. Sixty-eight stimuli underwent local ASR comparison; differences remain evidence, not rewritten transcripts/keys. `humanReviewed: false` and `exactTranscriptVerified: false` preserve the actual boundary. Three tracks with trailing waits use explicit source-interval WAV exports while full MP3s remain.

The ninety existing teacher tasks were replayed through isolated state/API checks: active text did not leak stimuli, review retained all ninety transcripts, fourteen repeats used 8/8/10/10/10/12/12 and eight interviews 45 seconds via the isolated clock. This did not touch real user storage or the 4173 session. Evidence: `tmp/qa/teacher-audio-migration-20260905/`.

## September 5: portraits, punctuation, and social icon

All sixty Pack Build pages were rendered/reviewed; twenty Paid reuse screens share their sources. Eighty screens retain 160 portrait references / 120 scale-4 crops, in the original speaker order; paper sources without portraits gained none. Five specified questions ended in question marks and 55 in periods. Missing fixed punctuation was restored for 48 canonical plus fifteen Paid occurrences (63), preserving token order, extras, slot count, fixed words, reference answers, scoring, and times. Display identities changed normally; pre-import `sourceContentId` and unrelated hashes stayed unchanged.

That batch had 468 visuals, nine curation files, and 1,841 derived hashes, with counts/strict eligibility unchanged. Re-parsing 679 Pack/Paid screens from existing extraction and replaying all 1,518 manifests reproduced active content. Twenty-three data checks passed. Evidence: `tmp/qa/build-source-visuals-20260905/audit.json`.

Pack 4 Daily Q11–12's source social-post icon was restored from p. 4 as one 184×184 scale-4 asset, with p. 5's cross-page source retained. One OCR period was corrected to the original comma; all other text/keys were equal. Final visual count became 469 files / 742 references in 626 screens, with nine manifests / 1,842 hashes at that batch. Twenty-four data checks/eighteen gates passed. Evidence: `tmp/qa/daily-source-visuals-20260905/audit.json`.

## September 5: original listening/speaking directions

Thirty-three modules in eight Pack/Paid archives had omitted source general rules/scenarios and existing audio directions. Source-checked text/pages/audio were restored without neighboring essays, keys, or premature question content. Paid canonical directions retained their independently checked edition scenarios.

Among 53 old direction candidates, sixteen were already verified and 37 had acoustic-only evidence; these historical states were not bulk rewritten. Forty-four passed source/ASR/interval review and independent PCM byte comparison, including 29 earlier Pack candidates. Original endings, bounds, WAV frames, and hashes remain recorded; `humanReviewed: false` and ASR differences remain honest.

Excluded candidates were a misclassified complete Paid lecture, a duplicate title already in a replaced stimulus, and one Paid interview-direction WAV without stable independently reproduced source-interval PCM. The latter kept paper scenario text, without substitute/synthetic audio. Unrelated Student candidates were unchanged. Two Paid 2 filename-number associations were corrected to module-level scenario placement with history retained.

Thirty-three modules retain text; 22 have audio; thirteen listening groups play a distinct title only at group start. Pack 1 Repeat's first sequence is section directions → repeat rules → museum scenario → stimulus; Interview uses rules → outdoor scenario → question. Original question/choice/key/stimulus/count/identity/response-time fields remained unchanged; unrelated ten archive files were byte-identical.

Final gates passed for eighteen archives with ten curation files / 1,886 hashes, unchanged 469 visual files. Isolated time replay covered seventeen scopes (including two Paid branches), 439 response screens, and all 44 directions, proving no answer clock started early. Re-parsed 679 source screens plus all structured records/directions matched current data without new OCR. Twenty-eight data tests passed. Evidence: `tmp/qa/pack-directions-audit-20260905/`. Restored playback data does not itself prove every current production instruction-screen transition.

## Scores and mistake-data boundary

A read-only implementation/test-scope review confirmed completion-only objective snapshots, explicit legacy recomputation, independent late recording/self-assessment, and mistake aggregation restricted to actually answered reliable objective units. Changed text/media/keys produce new versions rather than silently replacing historical errors. Current source gates were rerun; documentation closeout did not itself rerun all UI/application tests. Current-version check counts and actual browser/device evidence belong in [ACCEPTANCE.md](ACCEPTANCE.md), not inherited historic totals such as 111 or 177.
