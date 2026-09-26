# User guide

## Start and choose a language

After [installation](../README.md), run `npm start` from the repository directory and open [http://127.0.0.1:4173](http://127.0.0.1:4173). Keep the terminal open. Stop with Control+C. macOS also has `scripts/start.command` for launching after installation.

The default application language is English. Use the header **EN / 中文** selector to change it; the browser remembers the choice for that site in local storage (`toefl-lab-language`). Application navigation, setup, feedback, and help follow your choice. Source passages, question prompts, names, answer choices, transcripts, and original audio stay in their original language so practice content is not changed by translation. Only the root project README has English and Simplified Chinese editions. Detailed guides, policies, and example notices are in English, even when application controls are in Chinese. Opening an English guide does not change the interface language.

A different browser profile or port is a different site-storage context and may use the default again. Switching interface language does not restart a session or grant extra time.

## Your first practice

1. On an empty catalog, choose **Try Practice Test 1**, or run `npm run demo`. It installs the complete Reading, Listening, Writing, and Speaking reference set, including original audio and supported curated timing.
2. Select **TOEFL iBT® Practice Test 1** or an imported archive. An existing full private catalog may label the same `student-1` archive **Official Student Sample 1**; look under **Official samples** or **All** if **Full strict tests** is selected. The current **Audio edition** supports full strict local practice. A legacy paper edition may instead show **Per-section timing**, meaning only its verified scopes are eligible. Direct R/L/W/S actions choose one section; the whole-test action uses the archive's available scope.
3. Choose an available mode and route, then start. An archive only exposes modes supported by its content.
4. Answer through the page controls and use Next when ready. The app saves accepted answers locally.
5. Complete or end the practice to open review. Check your answers, read explanations where available, and return to history later.

To add your own questions or media, open **Help & setup** and follow [Importing resources](IMPORTING.md). The prepared bundle contains TOEFL iBT® Practice Test 1, not the rest of the original private collection; see its [source notice](../examples/ets-practice-test-1/NOTICE.md). Its 97 items span 79 screens; a reading cloze screen contains multiple items. All four sections of the current audio edition support strict local practice. Interview question 1 follows the supplied original audio, not the different paper prompt. Speaking plays the prompts and then automatically records; interview windows are 45 seconds each and transcripts appear in review. The neutral interviewer illustration is a UI aid, not original examiner video. To update a lightweight v2 install, stop the service and run `npm run demo -- --upgrade`; old sessions keep their previous question version. Your own portable JSON packs are untimed guided resources; adding four sections alone does not enable strict timing.

## Practice groups in the task library

The task library follows **source test → source module/part → task-category group**. A group contains the consecutive questions of one category in that module, in source order. Different tests, modules, lower/upper branches, and later separate runs of the same category remain separate.

For example, Experience Day 1 Listening Module 1 has four entries: Listen and Choose a Response (1–8, eight questions), Conversation (9–12, four questions), Announcement (13–14, two questions), and Academic Talk (15–18, four questions). Starting an entry includes the entire group. Shared recordings and the questions attached to them retain their original playback order. A cloze screen can contain ten blanks, so the library distinguishes question items from screens.

Search and pagination operate on whole groups. A keyword matching one member keeps the complete group; combining duplicates only combines identical complete groups from different sources, without removing members. Progress is aggregated over the group's current content versions: completing one question does not complete an eight-question group. If some source screens are unavailable, the available count and an omission note are shown.

Choose a group to open preparation with its source scope and route fixed. Audio replay and instant answers still require the unchecked-by-default option below. If the imported group changes before starting, reload the library and select the current group. Previous sessions and answers remain intact. The separate mistake collection still supports individual error retries.

## Choosing a mode

| Mode or route | Use it for | Behavior |
| --- | --- | --- |
| Guided practice | Learning and revisiting tasks | Supported pause; replay and instant answers only with pre-start opt-in for specialized practice |
| Strict timing | An eligible curated archive | Server deadlines, restricted navigation, one-time media, no pause or immediate answers |
| Fixed source route | Preserve an archive's original arrangement | Does not invent missing questions or splice unrelated materials |
| Simulated adaptation | Eligible archives with verified common/upper/lower branches | Local routing from module-1 raw accuracy; default 70% upper threshold, not ETS's proprietary model |
| Untimed supplementary practice | Custom packs and Essentials | No iBT per-question time claim; supported media/recording controls are manual |

Read the concise preparation information. Detailed source warnings and verification are available outside the main answer area. A disabled strict action usually means missing/unverified content, media, a source mismatch, or a supplementary format; it is not a purchase requirement.

Before a new specialized session, select **Guided practice** and a section, task type, or selected questions. **Enable audio replay and instant answers** is unchecked by default. Check it before starting if you want **Replay audio** and **Check answer & explanation** during that session. Changing the mode or scope clears the choice. Full-test sessions and strict timing cannot enable these aids. The server enforces the saved permission; an existing session without an opt-in stays off and cannot enable it mid-session.

Starting from a test or section opens preparation; use **Continue practice** in Home or History to resume an existing attempt. Completing or ending a session still opens normal review. First prompt playback and recovery from an audio-loading failure remain available without study aids. In timed practice without aids, pause is available during the response rather than the audio phase, so pause/resume cannot restart the spoken prompt. Untimed source audio supports its initial playback and pause/resume, while repeat/seek controls require the opt-in.

## Answering each kind of task

| Task | What to do |
| --- | --- |
| Complete the Words | Type only missing letters in the inline blanks. In the timed exam presentation, letter strokes remain visible while editing; empty/partial fields use a larger monospace font, and filled fields contract to paragraph text on blur and expand again on focus. Tab follows blank order. Given letters are not editable. |
| Reading choices | Read the source material and choose one option. Use source scrolling when the material is longer than its panel. |
| Listening | Let the source play. Short-response choices may be visible but disabled during audio. Answer when enabled; strict Listening cannot go back. |
| Build a Sentence | Place given tokens into slots by click, keyboard, or supported drag/drop. Fixed words/punctuation stay supplied; repeated tokens remain separate tokens. |
| Email | Read the left-side scenario/requirements, then write in the right editor under the original To/Subject. |
| Academic Discussion | Read the professor and both students, then contribute in the editor. Source portraits appear when the imported material includes them. |
| Listen and Repeat | Listen once and speak in the recording window. In strict practice, recording starts/stops according to the source rule. |
| Interview | Listen to the original question and respond in its recording window; no new-format preparation period is added. |

Word count is a writing aid. Recommended length, including the discussion's 100-word guidance, is not a software minimum that blocks submission. Strict writing disables spelling assistance and outside clipboard import; the editor's internal Cut/Paste/Undo/Redo remain available according to their state.

The bundled sample retains the specified paper edition. Its first Reading module has 20 items; the observed online sampler showed 17 and omitted one `of` present in the paper's cloze paragraph. The ten prefixes and blank lengths agree. The input styling follows observed interaction without changing the paper text, module count, answers, or saved scores. See the [dated cloze comparison](EXAM_UI_REFERENCE.md#live-reading-interaction-checked-on-2026-09-26).

## Timers and navigation

The source-based order is Reading → Listening → Writing → Speaking. Instructions, playback, response, and recording are separate stages. Begin starts the corresponding task/module timer where the selected source has that stage. Official approximate whole-section durations are not used as four freely shared clocks.

Reading and sentence-building permit back/review within the allowed module/task. Submitted modules cannot be reopened. Listening advances forward; an unanswered manual Next prompt does not stop automatic expiry. Email and Discussion each have their own timer. Their Time Remaining confirmation keeps counting; Back returns to the same editor and Continue leaves it. Under v5 rules, natural writing expiry leaves the accepted answer read-only until Continue. Old sessions keep their frozen rule version.

The server owns deadlines. Refresh, tab backgrounding, or a client restart does not reset them. During timed work, wait for save confirmation before advancing; a request arriving after the deadline can be rejected. Read [official rules](OFFICIAL_RULES.md) for verified values and clearly marked local defaults, including the unverified six-minute Build default.

## Audio, microphone, and recovery

Use current Chrome or Edge, headphones where useful, and the preparation volume/microphone checks. Grant microphone access to the local address when you intend to practice speaking, select the correct input, and make a short recording you can hear in playback. Permission in another site does not grant permission here.

Some older Listening-only guided sessions lack audio verification records even when the audio file is present. If the app offers **Restore listening audio**, choose **Repair audio and continue**. Recovery is available only when the saved questions, reference answers, and media identity match the currently verified resources. It verifies and binds the current audio while keeping your accepted answers, question position, deadlines, and frozen rules. The recovery is recorded as an interruption and does not retroactively verify earlier playback or reset the clock. **Later** leaves the practice saved for another time.

For an audio failure, read the displayed service error or HTTP status. A verification failure (HTTP 409) needs the offered repair or source correction, not repeated Play clicks. If the questions or media have actually changed, or repair is unavailable, restore the matching verified sources or choose **Start new practice**. New practice uses the current resources rather than reopening an incompatible old session; its saved answers remain preserved. Recovery does not bypass source checks.

Recordings are segmented and uploaded to the local service. If the page shows pending uploads, keep the site and service available so retries can finish. Do not clear site data while drafts are pending. An interrupted recording can create another take while keeping the prior one. Missing segments or a missing final marker mean incomplete recording even if part of it plays.

Strict interruption/fault recovery records the event. You can continue available practice, but an interrupted run is not represented as uninterrupted strict performance. The local app cannot provide a real testing center's lockdown or proctoring. See [troubleshooting](TROUBLESHOOTING.md) for device and network symptoms.

## Review, scores, and mistakes

History opens saved sessions, original accepted answers, available source explanations, writing, and recording playback/download. Where the source has no explanation, a clearly labeled local aid may compare letters/tokens or locate imported text. It does not call an AI service or invent a semantic explanation without support.

Objective results count only reliable keys. An unresolved source-answer conflict is excluded from the denominator. Writing/speaking are saved for rubric-based 0–5 self-assessment; not yet assessed is not zero. The app does not convert raw accuracy or self-assessment into official ETS 1–6 or 120-point scores.

For Complete the Words, **Compare each blank** shows the question number, your saved input, the reconstructed word, and the full reference word together. Given letters remain visible; the missing-letter portion is emphasized. A reliably matched answer has a green **Correct** label, and a wrong answer has a red **Incorrect** label. Available accepted alternatives appear beside the reference. Choice and sentence-building comparisons also show your response against the available reference.

**Not answered**, **Not scored**, and **Answer needs review** keep neutral styling instead of a red Incorrect label. If the available answers cannot reliably explain the saved server score, the detail is labeled **Detail unavailable**. These displays do not change the stored grade. An unanswered blank can still reduce a scoreable question's result.

Use the **Needs correction** question links to jump directly to a question, or **Only incorrect questions** to show questions below full marks according to the server result. Choose **Show all answers** to restore the complete review. Unscored questions and unresolved conflicting answers are excluded from this filter; scoreable unanswered questions may be included. **Retry unmatched objective items** starts a separate practice with the eligible original questions.

New completed sessions freeze objective score snapshots. Later updates do not silently change old objective scores. A legacy record that lacked a snapshot is identified as recomputed. Late recordings and later self-assessment remain separate additions.

The mistake collection combines actually answered, scoreable objective errors from completed sessions. Retry the question, mark it mastered by a correct later response, or reopen the last wrong attempt. Past errors stay visible. If sources or keys change, old history remains and a direct retry may be unavailable until a matching resource is restored.

## Vocabulary

Open **Vocabulary** in the main navigation to keep a personal word list. There are three ways to add a word:

1. Choose **Add a word** in Vocabulary, or use the same action in a completed session's review. Enter a word or phrase; meaning, context, and source are optional.
2. In review, select an English word or short phrase from selectable passage, prompt, or answer text, then choose **Add to vocabulary**. The dialog prefills the selection, a nearby text excerpt, and the available session/question source. Expand **Show original text and question images** when you need the source passage; selection works on text, not inside an image.
3. In a Complete the Words comparison, choose **Add word** beside a reference answer. This adds the full reference word, including given letters, rather than just your missing-letter input. This action is unavailable when the reference is missing or has an unresolved conflict.

Check the prefilled text and supply your own meaning or context before saving. The app does not fetch dictionary definitions or generate translations. If saving fails, the dialog keeps your inputs so you can correct them or retry.

Search by word, meaning, context, or source, and switch between **All words**, **Learning**, and **Mastered**. Use **Edit** to update the word, meaning, context, or learning status; the original source stays read-only. **Mark mastered** and **Keep learning** move an entry between the two learning states. **Delete** asks for confirmation and removes that word and its notes; the original practice answers remain saved.

Words are normalized for case and spacing. Adding an existing word keeps its original entry, notes, source, and learning status, with a duplicate notice. Use Edit when you intend to change it. Entries are stored in the local SQLite database at `storage/practice.sqlite3` and survive page refreshes and service restarts. They are included when you back up `storage/`; there is no account or cloud synchronization.

While any strict practice session is active, review and vocabulary access are locked, including browsing, adding, editing, changing status, and deleting from another tab. Complete or end that strict session before returning to these tools.

## Backup, move, and update

There is no account or cloud sync. Keep these local directories together:

- `storage/`: SQLite session and vocabulary data, original recordings, and playback cache.
- `data/` and `generated/`: installed sources, copied portable packs/revisions, normalized exams, and registries.
- For the original private importer, its matching `scripts/verified_*.json` curation files.

Wait for pending recording uploads, stop the service, then copy the complete directories. Do not copy only a running `practice.sqlite3` while omitting its WAL. Browser-only pending uploads are not included in directory backups. A JSON session export contains answer data and recording references; download recordings separately or back up their directory.

Before an update, back up. Install dependencies if changed and run `npm run build`; restart `npm start` to serve the new backend/build. Existing sessions keep frozen source/rules. After replacing a resource pack, start a new practice for its new content. Do not delete old revision assets while keeping sessions that refer to them.
