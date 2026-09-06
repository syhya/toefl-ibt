# User guide

English | [简体中文](USER_GUIDE.zh-CN.md)

## Start and choose a language

After [installation](../README.md), run `npm start` from the repository directory and open [http://127.0.0.1:4173](http://127.0.0.1:4173). Keep the terminal open. Stop with Control+C. macOS also has `scripts/start.command` for launching after installation.

The default application language is English. Use the header **EN / 中文** selector to change it; the browser remembers the choice for that site in local storage (`toefl-lab-language`). Application navigation, setup, feedback, and help follow your choice. Source passages, question prompts, names, answer choices, transcripts, and original audio stay in their original language so practice content is not changed by translation. Every documentation page has an English/简体中文 link near its title.

A different browser profile or port is a different site-storage context and may use the default again. Switching interface language does not restart a session or grant extra time.

## Your first practice

1. On an empty catalog, choose **Try the demo**. It installs four short original reading/writing screens, with no audio or time limit. You can also run `npm run demo`.
2. Select the demo or an imported archive. Direct R/L/W/S actions choose one section; the whole-test action uses the archive's available scope.
3. Choose an available mode and route, then start. An archive only exposes modes supported by its content.
4. Answer through the page controls and use Next when ready. The app saves accepted answers locally.
5. Complete or end the practice to open review. Check your answers, read explanations where available, and return to history later.

To add your own questions or media, open **Help & setup** and follow [Importing resources](IMPORTING.md). Public code does not include the original private 18-archive collection. A resource pack is untimed guided practice; it is not a full official mock simply because it includes four sections.

## Choosing a mode

| Mode or route | Use it for | Behavior |
| --- | --- | --- |
| Guided practice | Learning and revisiting tasks | Pause/replay/review tools where supported |
| Strict timing | An eligible curated archive | Server deadlines, restricted navigation, one-time media, no pause or immediate answers |
| Fixed source route | Preserve an archive's original arrangement | Does not invent missing questions or splice unrelated materials |
| Simulated adaptation | Eligible archives with verified common/upper/lower branches | Local routing from module-1 raw accuracy; default 70% upper threshold, not ETS's proprietary model |
| Untimed supplementary practice | Custom packs and Essentials | No iBT per-question time claim; supported media/recording controls are manual |

Read the concise preparation information. Detailed source warnings and verification are available outside the main answer area. A disabled strict action usually means missing/unverified content, media, a source mismatch, or a supplementary format; it is not a purchase requirement.

## Answering each kind of task

| Task | What to do |
| --- | --- |
| Complete the Words | Type only missing letters in the inline blanks. Given letters remain visible. The blank width/letter markers show the required count; Tab moves between inputs. |
| Reading choices | Read the source material and choose one option. Use source scrolling when the material is longer than its panel. |
| Listening | Let the source play. Short-response choices may be visible but disabled during audio. Answer when enabled; strict Listening cannot go back. |
| Build a Sentence | Place given tokens into slots by click, keyboard, or supported drag/drop. Fixed words/punctuation stay supplied; repeated tokens remain separate tokens. |
| Email | Read the left-side scenario/requirements, then write in the right editor under the original To/Subject. |
| Academic Discussion | Read the professor and both students, then contribute in the editor. Source portraits appear when the imported material includes them. |
| Listen and Repeat | Listen once and speak in the recording window. In strict practice, recording starts/stops according to the source rule. |
| Interview | Listen to the original question and respond in its recording window; no new-format preparation period is added. |

Word count is a writing aid. Recommended length, including the discussion's 100-word guidance, is not a software minimum that blocks submission. Strict writing disables spelling assistance and outside clipboard import; the editor's internal Cut/Paste/Undo/Redo remain available according to their state.

## Timers and navigation

The source-based order is Reading → Listening → Writing → Speaking. Instructions, playback, response, and recording are separate stages. Begin starts the corresponding task/module timer where the selected source has that stage. Official approximate whole-section durations are not used as four freely shared clocks.

Reading and sentence-building permit back/review within the allowed module/task. Submitted modules cannot be reopened. Listening advances forward; an unanswered manual Next prompt does not stop automatic expiry. Email and Discussion each have their own timer. Their Time Remaining confirmation keeps counting; Back returns to the same editor and Continue leaves it. Under v5 rules, natural writing expiry leaves the accepted answer read-only until Continue. Old sessions keep their frozen rule version.

The server owns deadlines. Refresh, tab backgrounding, or a client restart does not reset them. During timed work, wait for save confirmation before advancing; a request arriving after the deadline can be rejected. Read [official rules](OFFICIAL_RULES.md) for verified values and clearly marked local defaults, including the unverified six-minute Build default.

## Audio, microphone, and recovery

Use current Chrome or Edge, headphones where useful, and the preparation volume/microphone checks. Grant microphone access to the local address when you intend to practice speaking, select the correct input, and make a short recording you can hear in playback. Permission in another site does not grant permission here.

Recordings are segmented and uploaded to the local service. If the page shows pending uploads, keep the site and service available so retries can finish. Do not clear site data while drafts are pending. An interrupted recording can create another take while keeping the prior one. Missing segments or a missing final marker mean incomplete recording even if part of it plays.

Strict interruption/fault recovery records the event. You can continue available practice, but an interrupted run is not represented as uninterrupted strict performance. The local app cannot provide a real testing center's lockdown or proctoring. See [troubleshooting](TROUBLESHOOTING.md) for device and network symptoms.

## Review, scores, and mistakes

History opens saved sessions, original accepted answers, available source explanations, writing, and recording playback/download. Where the source has no explanation, a clearly labeled local aid may compare letters/tokens or locate imported text. It does not call an AI service or invent a semantic explanation without support.

Objective results count only reliable keys. An unresolved source-answer conflict is excluded from the denominator. Writing/speaking are saved for rubric-based 0–5 self-assessment; not yet assessed is not zero. The app does not convert raw accuracy or self-assessment into official ETS 1–6 or 120-point scores.

New completed sessions freeze objective score snapshots. Later updates do not silently change old objective scores. A legacy record that lacked a snapshot is identified as recomputed. Late recordings and later self-assessment remain separate additions.

The mistake collection combines actually answered, scoreable objective errors from completed sessions. Retry the question, mark it mastered by a correct later response, or reopen the last wrong attempt. Past errors stay visible. If sources or keys change, old history remains and a direct retry may be unavailable until a matching resource is restored.

## Backup, move, and update

There is no account or cloud sync. Keep these local directories together:

- `storage/`: SQLite, original recordings, and playback cache.
- `data/` and `generated/`: installed sources, copied portable packs/revisions, normalized exams, and registries.
- For the original private importer, its matching `scripts/verified_*.json` curation files.

Wait for pending recording uploads, stop the service, then copy the complete directories. Do not copy only a running `practice.sqlite3` while omitting its WAL. Browser-only pending uploads are not included in directory backups. A JSON session export contains answer data and recording references; download recordings separately or back up their directory.

Before an update, back up. Install dependencies if changed and run `npm run build`; restart `npm start` to serve the new backend/build. Existing sessions keep frozen source/rules. After replacing a resource pack, start a new practice for its new content. Do not delete old revision assets while keeping sessions that refer to them.
