# Changelog

English | [简体中文](CHANGELOG.zh-CN.md)

Changes are grouped by user-facing impact. `Unreleased` describes work in the current tree, not a published release or tag. Historical verification dates do not imply that newer code passed those same checks.

## Unreleased

### Added

- A bilingual [Vocabulary](docs/USER_GUIDE.md#vocabulary) page with manual entry, search, learning/mastered filters, editing, confirmed deletion, and local SQLite persistence. Duplicate additions preserve the existing entry and source.
- Review shortcuts to collect selected words with context and source, or save a Complete the Words reference as a full word. Meanings and notes are entered manually.
- Incorrect-question jump links and clearer question markers alongside the review filter.
- GPT-6 Astra development attribution and the project's purpose of exploring the model's current capabilities and limits.
- English and Simplified Chinese application language selection and paired documentation.
- Public newcomer workflow, demonstration content, and portable resource import guidance.
- Installation, usage, architecture, contribution, troubleshooting, and security documentation.
- Open-source issue/PR templates and a clean-checkout CI workflow.

### Changed

- The task library now organizes source tests into module/part and category groups. Each entry starts the full ordered group, with item/screen counts and aggregate progress; search, pagination, and deduplication preserve group membership. Group selection retains its original branch and rejects stale content at start.

- Audio replay and instant answers now require an unchecked-by-default preparation option in specialized guided practice. Strict and full-test sessions cannot enable it; old sessions without explicit consent remain off. Session API checks enforce the same rule, while first playback, audio recovery, and review after finishing remain available.
- Test/section start actions open preparation so the study-aid choice is visible; explicit Continue actions resume saved sessions.

- Review now compares each Complete the Words blank with its full reference word and accepted alternatives. Correct and incorrect answers have text labels and distinct colors; unanswered, unscored, conflicting, or unverifiable details remain neutral.
- Choice and sentence-building review presents the response and available reference together. The comparison explains saved server results without changing frozen scores.
- Vocabulary reads and changes follow the existing strict-session review lock, including requests from another tab.

### Fixed

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
