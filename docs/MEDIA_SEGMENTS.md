# Local long-track segmentation and verification

Historical generation time: 2026-08-31T23:22:38+0800. Later supplements and direction changes are recorded separately in [DATA_QA.md](DATA_QA.md). This is an advanced private-source workflow, not required for portable JSON packs or the public demo.

Original `data/` files remain unchanged. Processing uses local acoustic detection, supplied transcripts, and local MLX Whisper, without sending audio to cloud inference. Initial open-source model download needs network access; subsequent processing can be offline. Automatic verification is distinct from human listening.

## Files and contracts

- `scripts/segment_media.py`: repeatable scanning, transcription, alignment, export, and verification.
- `generated/media-segments.json`: source material ID/hash, original start/end seconds, question IDs, group ID, kind, URL, confidence, verified status, and evidence.
- `generated/assets/media/<examId>/`: playback segments.
- `generated/assets/media/_analysis/`: private source-time mappings, energy analysis, and ASR caches; never active content endpoints.

## Historical processed source tracks

The table uses English source labels, not replacement filesystem paths. Original filenames and paths remain unchanged in the local `generated/catalog.json` and `generated/media-segments.json`. Counts describe that segmentation snapshot, not a fresh run or current full inventory.

| Archive | Source label | Duration | Linked groups | Automatically verified | Unmatched |
| --- | --- | ---: | ---: | ---: | ---: |
| pack-2 | Pack-2_Listening.MP3 | 1425.1s | 20 | 20 | 0 |
| pack-2 | Pack-2_Speaking.MP3 | 494.7s | 11 | 11 | 0 |
| pack-3 | Pack-3_Listening.MP3 | 1724.1s | 27 | 27 | 0 |
| pack-3 | Pack-3_Speaking.MP3 | 499.5s | 11 | 11 | 0 |
| pack-4 | Pack-4_Listening.MP3 | 1787.2s | 27 | 27 | 0 |
| pack-4 | Pack-4_Speaking.MP3 | 513.5s | 11 | 11 | 0 |
| pack-5 | Pack-5_Listening.MP3 | 1751.1s | 24 | 24 | 0 |
| pack-5 | Pack-5_Speaking.MP3 | 502.0s | 11 | 11 | 0 |
| pack-6 | Pack-6_Speaking.MP3 | 459.2s | 11 | 11 | 0 |
| pack-6 | Pack-6_listening.MP3 | 1729.4s | 24 | 24 | 0 |
| student-1 | Student-Test-01-Speaking-01-Listen and Repeat.mp3 | 59.4s | 7 | 7 | 0 |
| student-1 | Student-Test-01-Speaking-02-Interview.mp3 | 114.6s | 3 | 3 | 1 |
| student-1 | Student-Test-01-Listening-Module 01-01-Listen and Choose a Response.mp3 | 59.7s | 8 | 8 | 0 |
| student-1 | Student-Test-01-Listening-Module 01-02-Conversation 01.mp3 | 35.3s | 1 | 1 | 0 |
| student-1 | Student-Test-01-Listening-Module 01-02-Conversation 02.mp3 | 32.1s | 1 | 1 | 0 |
| student-1 | Student-Test-01-Listening-Module 01-03-Announcement.mp3 | 34.0s | 1 | 1 | 0 |
| student-1 | Student-Test-01-Listening-Module 01-04-Academic Talk.mp3 | 102.9s | 1 | 1 | 0 |
| student-1 | Student-Test-01-Listening-Module 02-01-Listen and Choose a Response.mp3 | 57.9s | 8 | 8 | 0 |
| student-1 | Student-Test-01-Listening-Module 02-02-Conversation 01.mp3 | 30.8s | 1 | 1 | 0 |
| student-1 | Student-Test-01-Listening-Module 02-03-Announcement.mp3 | 28.5s | 1 | 1 | 0 |
| student-1 | Student-Test-01-Listening-Module 02-04-Academic Talk.mp3 | 91.1s | 1 | 1 | 0 |
| student-2 | Student-Test-02-Speaking-01-Listen and Repeat.mp3 | 53.3s | 7 | 7 | 0 |
| student-2 | Student-Test-02-Speaking-02-Interview.mp3 | 114.0s | 4 | 4 | 0 |
| student-2 | Student-Test-02-Listening-Module 01-01-Listen and Choose a Response.mp3 | 58.4s | 8 | 8 | 0 |
| student-2 | Student-Test-02-Listening-Module 01-02-Conversation 01.mp3 | 24.2s | 1 | 1 | 0 |
| student-2 | Student-Test-02-Listening-Module 01-02-Conversation 02.mp3 | 26.2s | 1 | 1 | 0 |
| student-2 | Student-Test-02-Listening-Module 01-03-Announcement.mp3 | 23.9s | 1 | 1 | 0 |
| student-2 | Student-Test-02-Listening-Module 01-04-Academic Talk.mp3 | 72.4s | 1 | 1 | 0 |
| student-2 | Student-Test-02-Listening-Module 02-01-Listen and Choose a Response.mp3 | 56.7s | 8 | 8 | 0 |
| student-2 | Student-Test-02-Listening-Module 02-02-Conversation 01.mp3 | 21.1s | 1 | 1 | 0 |
| student-2 | Student-Test-02-Listening-Module 02-03-Announcement.mp3 | 18.9s | 1 | 1 | 0 |
| student-2 | Student-Test-02-Listening-Module 02-04-Academic Talk.mp3 | 81.5s | 1 | 1 | 0 |
| paid-1 | Speaking-1.m4a | 11.3s | 1 | 1 | 0 |
| paid-1 | Speaking-10.m4a | 24.6s | 1 | 1 | 0 |
| paid-1 | Speaking-11.m4a | 18.8s | 1 | 1 | 0 |
| paid-1 | Speaking-2.m4a | 15.4s | 1 | 1 | 0 |
| paid-1 | Speaking-3.m4a | 12.2s | 1 | 1 | 0 |
| paid-1 | Speaking-4.m4a | 10.7s | 1 | 1 | 0 |
| paid-1 | Speaking-5.m4a | 6.9s | 1 | 1 | 0 |
| paid-1 | Speaking-6.m4a | 5.8s | 1 | 1 | 0 |
| paid-1 | Speaking-7.m4a | 10.0s | 1 | 0 | 0 |
| paid-1 | Speaking-8.m4a | 30.8s | 1 | 1 | 0 |
| paid-1 | Speaking-9.m4a | 22.8s | 1 | 1 | 0 |
| paid-1 | Speaking-Introduction.m4a | 10.0s | 1 | 1 | 0 |
| paid-1 | Listening-M1-1.m4a | 3.4s | 1 | 1 | 0 |
| paid-1 | Listening-M1-11-12.m4a | 31.0s | 1 | 1 | 0 |
| paid-1 | Listening-M1-11-12-Title.m4a | 3.1s | 1 | 1 | 0 |
| paid-1 | Listening-M1-13-14.m4a | 13.0s | 0 | 0 | 1 |
| paid-1 | Listening-M1-13-14-Title.m4a | 6.2s | 1 | 1 | 0 |
| paid-1 | Listening-M1-15-16.m4a | 21.9s | 1 | 1 | 0 |
| paid-1 | Listening-M1-17-20(1).m4a | 82.5s | 0 | 0 | 0 |
| paid-1 | Listening-M1-17-20.m4a | 82.5s | 1 | 1 | 0 |
| paid-1 | Listening-M1-17-20-Prompt.m4a | 6.5s | 1 | 1 | 0 |
| paid-1 | Listening-M1-2.m4a | 3.8s | 1 | 1 | 0 |
| paid-1 | Listening-M1-3.m4a | 4.0s | 1 | 1 | 0 |
| paid-1 | Listening-M1-4.m4a | 3.8s | 1 | 1 | 0 |
| paid-1 | Listening-M1-5.m4a | 3.3s | 1 | 1 | 0 |
| paid-1 | Listening-M1-6.m4a | 4.2s | 1 | 1 | 0 |
| paid-1 | Listening-M1-7.m4a | 5.2s | 1 | 1 | 0 |
| paid-1 | Listening-M1-8.m4a | 4.0s | 1 | 1 | 0 |
| paid-1 | Listening-M1-9-10.m4a | 30.7s | 1 | 1 | 0 |
| paid-1 | Listening-M1-9-10-Title.m4a | 6.9s | 1 | 1 | 0 |
| paid-1 | Listening-M2-1.m4a | 5.0s | 1 | 1 | 0 |
| paid-1 | Listening-M2-10-11.m4a | 27.9s | 1 | 1 | 0 |
| paid-1 | Listening-M2-10-11-Title.m4a | 7.1s | 1 | 1 | 0 |
| paid-1 | Listening-M2-12-13.m4a | 30.7s | 1 | 1 | 0 |
| paid-1 | Listening-M2-12-13-Title.m4a | 4.6s | 1 | 1 | 0 |
| paid-1 | Listening-M2-14-15.m4a | 19.0s | 1 | 1 | 0 |
| paid-1 | Listening-M2-14-15-Title.m4a | 4.3s | 1 | 1 | 0 |
| paid-1 | Listening-M2-2.m4a | 4.2s | 1 | 1 | 0 |
| paid-1 | Listening-M2-3.m4a | 6.2s | 1 | 1 | 0 |
| paid-1 | Listening-M2-4.m4a | 2.9s | 1 | 1 | 0 |
| paid-1 | Listening-M2-5.m4a | 3.3s | 1 | 1 | 0 |
| paid-1 | Listening-M2-6.m4a | 4.8s | 1 | 1 | 0 |
| paid-1 | Listening-M2-7.m4a | 4.5s | 1 | 1 | 0 |
| paid-1 | Listening-M2-8-9.m4a | 23.0s | 1 | 1 | 0 |
| paid-1 | Listening-M2-8-9-Title.m4a | 3.6s | 1 | 1 | 0 |
| paid-1 | ListeningM2-1.m4a | 2.2s | 1 | 1 | 0 |
| paid-1 | ListeningM2-12-15.m4a | 97.4s | 1 | 1 | 0 |
| paid-1 | ListeningM2-2.m4a | 3.8s | 1 | 1 | 0 |
| paid-1 | ListeningM2-3.m4a | 3.6s | 1 | 1 | 0 |
| paid-1 | ListeningM2-4-5.m4a | 27.7s | 1 | 1 | 0 |
| paid-1 | ListeningM2-4-5-Title.m4a | 4.7s | 1 | 1 | 0 |
| paid-1 | ListeningM2-6-7.m4a | 19.0s | 1 | 1 | 0 |
| paid-1 | ListeningM2-6-7-Title.m4a | 5.5s | 1 | 1 | 0 |
| paid-1 | ListeningM2-8-11.m4a | 92.8s | 1 | 1 | 0 |
| paid-2 | Speaking-Interview-1.mp3 | 17.0s | 1 | 1 | 0 |
| paid-2 | Speaking-Interview-2.mp3 | 15.2s | 1 | 1 | 0 |
| paid-2 | Speaking-Interview-3.mp3 | 22.2s | 1 | 1 | 0 |
| paid-2 | Speaking-Interview-4.mp3 | 17.2s | 1 | 1 | 0 |
| paid-2 | Speaking-Interview-Directions.mp3 | 9.5s | 1 | 1 | 0 |
| paid-2 | Listen-and-Repeat-1.mp3 | 2.0s | 1 | 1 | 0 |
| paid-2 | Listen-and-Repeat-2.mp3 | 2.1s | 1 | 1 | 0 |
| paid-2 | Listen-and-Repeat-3.mp3 | 3.0s | 1 | 1 | 0 |
| paid-2 | Listen-and-Repeat-4.mp3 | 4.7s | 1 | 1 | 0 |
| paid-2 | Listen-and-Repeat-5.mp3 | 3.4s | 1 | 1 | 0 |
| paid-2 | Listen-and-Repeat-6.mp3 | 4.7s | 1 | 1 | 0 |
| paid-2 | Listen-and-Repeat-7.mp3 | 4.2s | 1 | 1 | 0 |
| paid-2 | Listen-and-Repeat-Directions.mp3 | 8.8s | 1 | 1 | 0 |
| paid-2 | C1.mp3 | 28.9s | 1 | 1 | 0 |
| paid-2 | C2.mp3 | 26.9s | 1 | 1 | 0 |
| paid-2 | Listen-to-an-Announcement-Directions.mp3 | 3.2s | 1 | 1 | 0 |
| paid-2 | Listen-to-a-Conversation-Directions.mp3 | 2.2s | 1 | 1 | 0 |
| paid-2 | Listening-Section-Directions.mp3 | 18.4s | 1 | 1 | 0 |
| paid-2 | Academic-Talk-with-Directions.mp3 | 99.6s | 1 | 1 | 0 |
| paid-2 | Listen-and-Choose-a-Response-Q1.mp3 | 4.3s | 1 | 1 | 0 |
| paid-2 | Listen-and-Choose-a-Response-Q2.mp3 | 4.0s | 1 | 1 | 0 |
| paid-2 | Listen-and-Choose-a-Response-Q3.mp3 | 2.7s | 1 | 1 | 0 |
| paid-2 | Listen-and-Choose-a-Response-Q4.mp3 | 1.6s | 1 | 1 | 0 |
| paid-2 | Listen-and-Choose-a-Response-Q5.mp3 | 1.9s | 1 | 1 | 0 |
| paid-2 | Listen-and-Choose-a-Response-Q6.mp3 | 2.0s | 1 | 1 | 0 |
| paid-2 | Listen-and-Choose-a-Response-Q7.mp3 | 1.7s | 1 | 1 | 0 |
| paid-2 | Listen-and-Choose-a-Response-Q8.mp3 | 2.3s | 1 | 1 | 0 |
| paid-2 | Announcement-1.mp3 | 12.9s | 1 | 1 | 0 |
| paid-2 | Announcement-2-with-Directions.mp3 | 20.2s | 1 | 1 | 0 |
| paid-2 | C1.mp3 | 25.7s | 1 | 1 | 0 |
| paid-2 | C2.mp3 | 21.7s | 1 | 1 | 0 |
| paid-2 | Academic-Talk-1.mp3 | 75.7s | 1 | 1 | 0 |
| paid-2 | Academic-Talk-2.mp3 | 126.0s | 1 | 1 | 0 |
| paid-2 | Listen-and-Choose-a-Response-Q1.mp3 | 2.4s | 1 | 1 | 0 |
| paid-2 | Listen-and-Choose-a-Response-Q2.mp3 | 2.5s | 1 | 1 | 0 |
| paid-2 | Listen-and-Choose-a-Response-Q3.mp3 | 2.3s | 1 | 1 | 0 |
| pack-1 | Pack-1_Listening.MP3 | 1108.6s | 20 | 20 | 0 |
| pack-1 | Pack-1_Speaking.MP3 | 513.4s | 11 | 11 | 0 |

## Verification method and limits

1. Measure 16 kHz mono PCM energy at a -38 dB threshold, treating quiet intervals over 1.45 seconds separately. Quiet audio is not itself proof of an official response window.
2. Compress long silence only for ASR and retain compressed-to-original time mapping. Playback uses exports from original intervals, never the compressed transcription track.
3. Align supplied text with local ASR word order, then snap boundaries to measurable silence. Automatic verification requires similarity at least 0.94, reliable bounds, and no internal quiet interval of four seconds or more.
4. Where Pack interviews have no verbatim source transcript, first match all seven repeat tasks, then identify exactly four prompts each followed by at least thirty seconds of response wait and map the verified order. Label this `ordered-acoustic-structure-cross-check`, not human listening.
5. `verified` means the described traceable automatic checks passed. `humanReviewed` is separate and defaults false. Weak matches or uncertain bounds remain `needs-review` and cannot enter strict playback.
6. `sources[].excludedWaits` records excluded silence, including trailing silence. It is neither stimulus playback nor extra preparation; versioned response rules own the window.
7. Directions candidates are separate. Without enough evidence they do not become a prompt; missing spoken questions are not generated.
8. `cue` is an original recording tone, identified by narrow-band short-time spectrum and position after repeat prompts. `sourceDelayAfterPromptSeconds` describes the source gap, not an official preparation allowance. Cue and stimulus are separate and the player must not duplicate the cue.

## Running the advanced tool

The MLX workflow below is for a compatible Apple Silicon/macOS environment with `uv`; it is not a cross-platform runtime prerequisite.

```sh
# Keep optional media tooling isolated from the application and system packages.
uv venv --python 3.12 .venv-media
uv pip install --python .venv-media/bin/python mlx-whisper imageio-ffmpeg rapidfuzz
HF_HUB_DISABLE_XET=1 .venv-media/bin/python scripts/segment_media.py all
.venv-media/bin/python scripts/segment_media.py validate
```

The tool prefers the `imageio_ffmpeg` binary. On macOS, CoreAudio decoding can produce standard WAV while installation is unavailable, without repairing global Homebrew FFmpeg. If Numba/LLVM is unavailable, the same DTW operation has a slower pure-Python fallback.

## Integration

Only `verified=true` stimulus/prompt segments map to questions. Questions with the same `groupId` share one playback before separate answers. Retain source track, interval, and verification state for tracing. Do not change `needs-review` to verified merely to enable a mock.

## Recorded source differences

- `student-1-s-interview-1-prompt`, source 12.22–28.16 seconds, `verified=false`: the paper asks about the size of the current residence; audio asks about a recent visit to another city. Preserve the versions for review and do not claim a match. The 2026-09-05 official ZIP recheck still found this difference.
- `pack-1-speaking-listen_repeat-6-prompt`, source 153.38–156.96 seconds, `verified=true`: the original audio has an introductory word missing from the paper transcript. Preserve the complete single original sentence and disclose the omission rather than cutting off its beginning.
- `mat-237f97573298`: the supplied M1-13–14 track duplicates the hiking announcement for M1-15–16. Use matching canonical auction audio only with a disclosed, verified source override; retain the original mismatch.

Full source-question/transcript excerpts are not reproduced here; private source evidence remains local. See [independent official verification](ets-2026-verification.md) and [materials](MATERIALS.md).
