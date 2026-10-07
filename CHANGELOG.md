# Changelog

Changes are grouped by user-facing impact. `Unreleased` describes work in the current tree, not a published release or tag. Historical verification dates do not imply that newer code passed those same checks.

## 0.1.1 — 2026-10-07

### Changed

- Applied the existing 15:00/15:00 Reading practice profile consistently to all iBT sets. Strict iBT sessions freeze the standard server profile; guided practice honors custom settings. Older Pack preview clocks no longer override Reading settings, and saved sessions retain their original rules and deadlines.
- Updated English and Chinese timing guidance and the v9 rules contract to distinguish confirmed ETS limits from local practice presets.

### Fixed

- Requests for unavailable fixed branches now fail instead of starting only the first module as a full section. Explicit common-module guided practice remains available.
- Section totals count every cloze blank as a question item and report screen counts separately.
- The local recovered collection's Paid 1 Reading question 24 was corrected against its matching Pack source. The original truncated option, supplied key and previous proof remain in private correction evidence. Private sources and generated archives are not included in Git; genuine omissions and unresolved keys remain documented.

### Verification

- Added regression coverage for all iBT families, fixed routes, custom/strict timing, post-audio answer windows, frozen sessions, catalogue counts and the installed source correction. Full validation is recorded in [Acceptance](docs/ACCEPTANCE.md).

## [0.1.0](https://github.com/syhya/toefl-ibt/releases/tag/v0.1.0) — 2026-09-27

### Added

- Reviewed English and Simplified Chinese explanations for all 79 current Practice Test 1 screens and the retained paper Interview 1. The explanation body, distractor reasons, per-blank grammar notes, correction notices, and authorship label follow the selected interface language. Both editions are bound to the same question and answer fingerprint.

- A bilingual [Vocabulary](docs/USER_GUIDE.md#vocabulary) page with manual entry, search, learning/mastered filters, editing, confirmed deletion, and local SQLite persistence. Duplicate additions preserve the existing entry and source.
- Review shortcuts to collect selected words with context and source, or save a Complete the Words reference as a full word. Meanings and notes are entered manually.
- Incorrect-question jump links and clearer question markers alongside the review filter.
- GPT-6 Astra development attribution and the project's purpose of exploring the model's current capabilities and limits.
- English and Simplified Chinese application language selection, a bilingual root README, and English-only detailed documentation.
- A complete TOEFL iBT® Practice Test 1 reference set for the newcomer workflow, derived from the ETS-hosted question paper and separately supplied companion audio/explanations, with corrected structured questions, prepared media, and portraits. Source attribution and third-party rights are documented in the example notice.
- Installation, usage, architecture, contribution, troubleshooting, and security documentation.
- Open-source issue/PR templates and a clean-checkout CI workflow.

### Changed

- Initial public release as `v0.1.0`, with package version `0.1.0`.

- The default Practice Test 1 package is now the disclosed original-audio edition (v3): all four Interview prompts play before automatic 45-second recording windows. Question 1 differs from the paper PDF; review preserves that comparison and excludes the incompatible paper sample answer. The 57-file runtime payload is about 18.3 MB. Explicit lightweight v2 upgrades keep saved sessions and old assets intact.

- Reading defaults to the user-selected balanced 30-minute practice profile (15:00 + 15:00), replacing the earlier 21:00/09:00 allocation and original 20:30 total. The equal split matches this paper's two 20-item modules; it is not claimed as verified official module timing. Unchanged legacy browser presets upgrade; custom settings, source-specific clocks, and existing session deadlines remain intact.

- Re-audited Practice Test 1 timing against ETS sources. Start pages identify official limits, source settings, local presets and untimed study; shared-budget subsets explicitly retain the full task/module time. Filtered repeat tasks preserve durations by original position. New audio-edition sessions use matched Interview prompts with 45-second response windows; legacy paper sessions retain their original timing and eligibility.

- All 13 optional local original files for the sample use lowercase English filenames. Manifest mappings and the exporter preserve unchanged bytes, source IDs, and original installation paths; private data and saved-session references are not renamed.
- README, package inventory, import/recovery instructions, and documentation policy now reflect the current example and distinguish it from dated private-collection audits. The default runtime payload is approximately 18.3 MB; 13 original PDFs/full tracks are optional and excluded from Git. Missing originals do not disable prepared practice, but corrupt/missing runtime assets still fail verification.

- Only the root README retains English and Simplified Chinese editions. Other Markdown documents are English-only. The in-app reader serves English guides without changing the chosen interface language, and legacy localized documentation endpoints remain compatible.

- `npm run demo` and the newcomer action now install **TOEFL iBT® Practice Test 1** (`student-1`, 97 items, 79 screens). The current audio edition supports eligible strict practice in all four sections and the full test. Legacy paper-edition sessions retain their original restrictions. Existing verified Student Sample 1 is reused without replacing personal records. The former synthetic pack remains a test fixture; TPO Pack 1 is no longer the default example.

- The task library now organizes source tests into module/part and category groups. Each entry starts the full ordered group, with item/screen counts and aggregate progress; search, pagination, and deduplication preserve group membership. Group selection retains its original branch and rejects stale content at start.

- Audio replay and instant answers now require an unchecked-by-default preparation option in specialized guided practice. Strict and full-test sessions cannot enable it; old sessions without explicit consent remain off. Session API checks enforce the same rule, while first playback, audio recovery, and review after finishing remain available.
- Test/section start actions open preparation so the study-aid choice is visible; explicit Continue actions resume saved sessions.

- Review now compares each Complete the Words blank with its full reference word and accepted alternatives. Correct and incorrect answers have text labels and distinct colors; unanswered, unscored, conflicting, or unverifiable details remain neutral.
- Choice and sentence-building review presents the response and available reference together. The comparison explains saved server results without changing frozen scores.
- Vocabulary reads and changes follow the existing strict-session review lock, including requests from another tab.

### Fixed

- Source-attribution CI checks follow the concise root READMEs to the source notice and verify its official PDF URL and recorded SHA-256.

- Sentence-builder selection and drag state reset on question changes, preventing a prior question's gap index from misplacing or rejecting the next answer.
- A verified sentence token order can be graded with its printed fixed literals when only those literals' punctuation differs from the answer key; word identity/order remain exact and saved score snapshots are not rewritten.
- Speaking now shows a neutral interviewer/speaker illustration when no original visual exists, hides transcripts during timed responses, and avoids duplicate text in older study sessions.

- Restored source-reviewed reading paragraph and signature breaks in 23 emails and two academic passages (73 associated screens), including Practice Test 1's workshop email. Active practice and review share a hash-bound display projection; saved questions, answers, timing and scores are untouched. Existing explicit newlines survive rendering, and source signatures intentionally printed on one line remain unchanged.

- Complete the Words now retains per-letter strokes while typing and uses the observed expanded monospace editor, completed-answer collapse on blur, and re-entry on focus. Partially filled answers remain expanded. Source wording and counts remain those of the supplied PDF, including the documented online-edition differences.

- Eligible older Listening-only guided sessions can use **Repair audio and continue** when audio verification records are missing. Recovery requires matching questions, reference answers, and currently verified media; it preserves answers, progress, deadlines, and frozen rules, and records the repair as an interruption without claiming historical verification.
- Audio failures now show the service error or HTTP status. Verification failures offer eligible recovery instead of a repeated playback retry; actual source changes still require matching resources or new practice.
- **Start new practice** no longer reopens an active session whose source version does not match.

### Existing local application capabilities

- Source-based structured reading, listening, writing, and speaking practice.
- Server-owned deadlines, frozen session rules, strict navigation, and writing expiry acknowledgement.
- Local answers, segmented recording, playback, review, self-assessment, and cross-session mistakes.
- Frozen objective score snapshots and source/asset integrity checks.

## Development verification — 2026-09-05 to 2026-09-06

The private collection and the v5 local examination flow underwent the dated checks in [ACCEPTANCE.md](docs/ACCEPTANCE.md). These records include full browser practice, original media, explicit synthetic-microphone recording, service restart persistence, and source-data auditing. They are historical evidence for the tested revisions; they are not a release announcement, real-microphone certification, or proof of complete ETS production parity.
