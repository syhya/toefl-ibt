# Independent ETS 2026 verification

Checked on 2026-09-05 for TOEFL iBT from 2026-01-21. This dated review used ETS pages and PDFs and compared `OFFICIAL_RULES.md` with `shared/rules.json`. A separate source check then supplemented existing teacher questions with matching ETS audio; no new questions were authored or added. The bilingual documentation update does not imply a new live verification.

## Sequence and countdowns

The order is Reading → Listening → Writing → Speaking. Reading/Listening use two adaptive stages; Writing/Speaking are linear. The published base counts are 50/47/12/11 and approximate times 30/29/23/8 minutes, excluding directions and subject to adaptation. These do not justify four fixed section-wide clocks. [ETS structure](https://www.ets.org/toefl/test-takers/ibt/about/content.html), [Teacher FAQ, pp. 2–4](https://www.ets.org/content/dam/ets-org/pdfs/toefl/teacher-faq.pdf).

| Task | Verification | Primary source |
| --- | --- | --- |
| Reading | Module clock, within-module Next/Back, no return to module 1 | [Teacher Test 1, physical pp. 3, 7](https://www.ets.org/content/dam/ets-org/pdfs/toefl/toefl-ibt-teachers-resources-practice-test-1.pdf) |
| Listening | Per-question clock, forward-only, stimulus once | [Teacher Test 1, pp. 15, 20](https://www.ets.org/content/dam/ets-org/pdfs/toefl/toefl-ibt-teachers-resources-practice-test-1.pdf), [Specifications, p. 12](https://www.eu.ets.org/pdfs/toefl/toefl-enki-test-specifications-2026.pdf) |
| Build a Sentence | Ten token-moving questions; task clock; initial 6:00/6:50 not verified | [Specifications, p. 6](https://www.eu.ets.org/pdfs/toefl/toefl-enki-test-specifications-2026.pdf), [Teacher Test 1, p. 27](https://www.ets.org/content/dam/ets-org/pdfs/toefl/toefl-ibt-teachers-resources-practice-test-1.pdf) |
| Email | Seven minutes including reading/writing | [Writing lessons, p. 7](https://www.ets.org/content/dam/ets-org/pdfs/toefl/toefl-ibt-lesson-plan-writing.pdf) |
| Discussion | Ten minutes; at least 100 words recommended; word count, no spell-check | [Writing lessons, pp. 4, 7](https://www.ets.org/content/dam/ets-org/pdfs/toefl/toefl-ibt-lesson-plan-writing.pdf) |
| Repeat | Seven sentences, no preparation, one repeat, maximum 8–12-second windows | [Teacher Test 1, p. 33](https://www.ets.org/content/dam/ets-org/pdfs/toefl/toefl-ibt-teachers-resources-practice-test-1.pdf), [Overview, p. 17](https://www.ets.org/pdfs/toefl/toefl-ibt-test-at-a-glance.pdf) |
| Interview | Four questions, no preparation, 45 seconds each | [Teacher Test 1, p. 34](https://www.ets.org/content/dam/ets-org/pdfs/toefl/toefl-ibt-teachers-resources-practice-test-1.pdf), [Overview, p. 18](https://www.ets.org/pdfs/toefl/toefl-ibt-test-overview.pdf) |

Blueprint estimates are Reading router 18–21 minutes / second module 9, and Listening router 18 / lower 7 / upper 11. They carry estimated/pre-release qualifications and do not establish every archive's exact timer. [Specifications, pp. 2–3](https://www.eu.ets.org/pdfs/toefl/toefl-enki-test-specifications-2026.pdf).

## Implementation conclusions

- Existing sequence, navigation, and Email/Discussion/Interview times agree with the checked official sources.
- Initial Reading module times, Listening 20/30-second defaults, and Repeat 8/8/10/10/10/12/12 remain source-material observations, not universal official values.
- Build's 360 seconds remains a local default. Subtracting 7 and 10 from an approximate 23-minute writing overview does not prove an exact six-minute limit.
- Listening needs both per-question timing and no return; a 29-minute section clock does not satisfy those rules.
- Classroom preparation exercises are not new-format speaking test preparation time. [Speaking lesson plan, p. 3](https://www.ets.org/content/dam/ets-org/pdfs/toefl/toefl-ibt-lesson-plan-speaking.pdf).
- Raw key-comparison results may be reported; official Reading/Listening scores involve difficulty, IRT, equating, and conversion. [Teacher FAQ, pp. 4–5](https://www.ets.org/content/dam/ets-org/pdfs/toefl/teacher-faq.pdf).

## Evidence boundary

Public ETS documentation does not expose a complete production state machine, all timing allocations, calibration parameters, or routing thresholds. The early [Sample 1](https://www.ets.org/toefl/test-takers/ibt/prepare/sample-test-jan-2026-1.html) visit only reached a form; later the user's authorized Sampler showed Reading, Listening, Build, long writing, and Email's Time Remaining confirmation. First visible 06:56/09:34 values were remaining times. [Detailed interface observations](EXAM_UI_REFERENCE.md) retain that scope; Build's absent clock still does not establish an initial limit.

The [teacher resource page](https://www.ets.org/toefl/teachers-advisors-agents/ibt/teaching/preparing-students.html) supplied matching PDF/audio links. Existing questions remain sourced from the user's PDFs; speech recognition did not generate or rewrite questions.

## Teacher audio supplement

[Test 1 audio ZIP](https://www.ets.org/content/dam/ets-org/pdfs/toefl/teacher-practice-test-1-audio-file.zip) was 6,812,272 bytes; [Test 2](https://www.ets.org/content/dam/ets-org/pdfs/toefl/teacher-practice-test-2-audio-file.zip) was 6,728,221 bytes. Complete downloads and ZIP CRC checks passed. Each contained 36 MP3 files: 23 stimuli covering 34 listening questions, 11 speaking stimuli, and two speaking directions. Page pairing, archive, module, file numbering, subject, and order matched the existing teacher collection rather than the Experience archives.

Private `scripts/verified_teacher_audio.json` binds source PDFs, physical pages, original transcripts, and audio hashes. `scripts/attach_teacher_audio.py` verifies offline by default; explicit installation adds original MP3s without overwriting files. ASR was used for comparison only. Machine differences for 18 segments remain review evidence, not confirmed transcript errors or a claim of word-by-word human listening. Active timed tasks hide full stimuli text; review retains original transcripts.

## Student 1 remains a version mismatch

The [current Student Test 1 audio ZIP](https://www.ets.org/content/dam/ets-org/pdfs/toefl/student-practice-test-1-audio-files.zip) was re-downloaded on 2026-09-05: 22,617,951 bytes, CRC passed. `Speaking/Interview/Speaking_Interview_Question1.mp4` still asks about a recent visit to another city, while the user's PDF asks about the size of the current city of residence. This is a substantive question mismatch.

The paper question remains available only within its supported reference scope; no replacement prompt or synthetic audio was inserted and the archive is not presented as a complete strict mock. The downloaded ZIP remains only in `tmp/qa/official-audio-verification/`, with `student-1-interview-1-check.json` recording hashes and comparison.
