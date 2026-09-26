# Source screenshots and current ETS Sampler interface

Baseline checked on 2026-09-05, with a separately dated live-cloze update on 2026-09-26. This record separates measurements of supplied Pack screenshots from later public-client CSS and authorized Sampler observations. Earlier bitmap estimates do not override later direct evidence. Paper Teacher/Student/Experience layouts alone do not establish computer-test UI. Observed Reading/Listening/Build pages had no clock; Email/Discussion did, so the missing clock is not generalized across the Sampler.

## Source samples and dimensions

Primary sources are the private Pack 1 and Pack 2 PDFs under the supplied `data/` tree.

| Task | Pack 1 physical page | Pack 2 physical page |
| --- | ---: | ---: |
| Complete the Words | 3 | 3 |
| Daily Life | 5 | 4 |
| Academic Passage | 13 | 11 |
| Build a Sentence | 75 | 77 |
| Email | 86 | 88 |
| Discussion | 88 | 90 |

At 96 dpi the PDF page is 1123×794 pixels. Pack 1 page 5's client occupies approximately x=48–1074 (1026 wide), toolbar y=59–111, status row y=111–139, and content below y=139. PDF margins and publisher annotations are not exam UI. Measurements below use an approximately 1024-pixel client canvas, retaining proportional content density rather than copying PDF margins.

## Shared chrome: earlier Pack measurements

- A roughly 52-pixel dark-teal top row has the source TOEFL mark and all navigation/help controls. No bottom Back/Next bar is shown.
- A roughly 28-pixel white status row shows section, gray divider, original item position, and right-aligned `00:mm:ss`, eye icon, and Hide Time above a thin dark rule.
- The content is white and excludes dashboards, thumbnails, catalog navigation, and practice statistics.
- Standard top buttons are teal/translucent teal with light borders, white text, approximately 40-pixel height, 12–15-pixel radii, and 5–7-pixel gaps. Next/Begin are white with teal text/right arrow; Back has a left arrow.
- Reading shows Volume, Help, Review, Back, Next (no Back on the first screen); Build omits Volume; Email/Discussion show Help and Next.
- Cloze uses `Questions 1–10 of n`; choices use one question position; Build uses `x of 10`; Email and Discussion use `1 of 2` and `2 of 2`. Denominators come from the source scope, not the website's base counts.

Early bitmap-only estimates used Arial/Helvetica and approximately 18px/24px body text. Later public CSS directly identified **Open Sans**, and current Sampler body text was compared at **16px/21px**. Embedded source materials can retain different fonts/sizes. Pack colors also vary: sampled Pack 1 teal was about `#014F5B`, Pack 2 about `#0B666B`; neither is a proven universal ETS design token.

## Complete the Words

The task instruction is centered near the top of the content, with large whitespace before one continuous paragraph and approximately 35–45-pixel side margins. In a 1000-pixel-wide reference image, the client begins at full-image y=57, instruction text at y=161 (client y≈104), and paragraph text at y=401 (client y≈344). A separate 96-dpi rendering gives y≈165/411, consistent after width normalization. The paragraph is not at client y=151; its position is about 43% down the visible content region. Use measured proportions and side-by-side screenshots, not a vague centering rule.

Missing letters remain inline with the original prefix. Light-gray continuous letter boxes and fine marks indicate the required count. There are no numbered bubbles, separate full-word fields, or extra answer list. Given letters must not become missing-letter input, and a prefix/input/suffix unit must wrap together.

### Live reading interaction checked on 2026-09-26

The user's open ETS Reading Part 1 page was inspected without changing answers or advancing the official session. Its paragraph uses approximately 17px Open Sans. Empty and partial fields remain expanded; editing uses `2ch Consolas, monospace`, `.2ch` letter spacing and `1.3ch` width per required letter. The gray fill is `#d3d3d3`. Independent `#696969` bottom strokes occupy `1ch` of each `1.3ch` cell at 1px thickness, so entering letters does not remove the lines. A completed field contracts to the paragraph's proportional type on blur, and expands again on focus. An incomplete field stays expanded. Tab follows the original blank order, and input accepts lowercase Latin letters only. Forced-colors mode retains a visible input edge and focus indicator.

The local component keeps one accessible input per blank during this visual transition; it does not rewrite answers on blur or use completion to bypass disabled controls. Regression checks cover keyboard re-entry, partial edits, restoration, and disabled state. Real-browser checks verify the background lines and font/width changes.

This observed online edition is not identical to the bundled PDF edition: it displays `Questions 1–10 of 17` and “than any other group activity”; the official student PDF, physical page 4, contains “than of any other group activity” and its first reading module has 20 items. All ten supplied prefixes and missing-letter lengths match. The project preserves the PDF wording, original item count, source hashes, and scoring data; it does not silently remove the extra word or three questions to imitate a different edition. The interaction match is not a claim of complete online-test equivalence.

## Daily Life and Academic Passage

Both use two columns: source on the left, original question/choices on the right. On the reference canvas, left spans roughly x=23–494, right begins around x=533, with a 38–42-pixel gap and no heavy divider. Instruction/title spans the columns.

Daily materials retain their source format. Pack 1 page 5 has a yellow-orange email frame, white Date/Subject cells, and serif body; it is not a global email template. Academic titles are approximately 26-pixel bold, paragraphs retain spacing, and specified highlighted terms use dark teal/white. Do not introduce answer-keyword highlighting. Choices use plain roughly 20-pixel circles and 20–25-pixel vertical spacing, without A/B badges or rounded option cards. Current Sampler ordinary prompt/choice comparison uses 16px/21px rather than the older 18px/24px estimate.

### Source-specific email frames

Semantic `message` fields alone do not capture frame color, corners, labels, typography, viewport, scrollbar, width, or signature breaks. The following source observations were checked individually:

| Source | Frame and body |
| --- | --- |
| Pack 1 p. 5 | Gold square frame, separate white Date/Subject label/value cells, serif body |
| Pack 1 p. 7 | Very pale gray-green square frame, separate white cells, small sans-serif body, no visible scrollbar |
| Pack 2 p. 4 | Dark-teal square frame, white cells, small sans-serif body, traditional arrow scrollbar |
| Pack 2 p. 6 | Mint square frame, labels on colored background/white values, independent white body, no visible scrollbar |
| Pack 3 p. 4; Pack 4 p. 6 | Pale-cyan square frame, white Subject cell, sans-serif body and scrollbar |
| Pack 3 p. 6 | Dark-teal square frame, white Subject cell, sans-serif body and scrollbar |
| Pack 5 p. 4 | Orange square frame, white Subject cell, sans-serif body and scrollbar |
| Pack 5 p. 6 | Pale-cyan rounded top/bottom, Subject divider, serif body, no visible scrollbar |
| Pack 6 p. 4 | Peach rounded frame, rounded white Subject value/body, sans-serif, no visible scrollbar |
| Pack 6 p. 6 | Gold rounded frame/darker gold edge, white Subject cell, serif, no visible scrollbar |

The original design recommendation was a finite verified theme enum with allowlisted font/width/labels/viewport, rather than arbitrary CSS in content. At that design stage `safe_stem_blocks` filtered unspecified theme fields, so any schema expansion required matching validation/projection/hash changes. Current source-specific visual selection is implemented in presentation code; this historical recommendation is not proof of a newly accepted arbitrary field. A depicted scrollbar must correspond to real scrolling with complete paragraphs, not hidden text behind decoration. Paper sources without such frames should not receive them automatically.

## Build a Sentence

The centered title and dialogue leave substantial whitespace. Two circular portraits align vertically, each beside its original dialogue/answer line. Pack 1 p. 75 portraits are approximately 92 pixels across, x≈106 from the client edge; full-page rendered y ranges are approximately 350–443 and 478–571.

The first speaker's sentence is bold. Given answer words remain ordinary text; movable tokens occupy thin black underline slots that can wrap. Sentence punctuation is fixed source content and must be checked page by page, not guessed from the answer. Available tokens are centered below, black on white without a global gray card. Preserve duplicates/distractors and use each source's own portraits.

All sixty Pack 1–6 Build pages were reviewed. Question marks appear only at Pack 1 Q2, Pack 4 Q10, Pack 5 Q3/Q9, and Pack 6 Q2; the other 55 end in periods. A mark may be inside a fixed final token or separate after the last slot; Pack 6 Q7 wraps its period to the left. `tmp/pdfs/exam-ui-reference/build-audit/all-build-source-visuals.json` records normalized bounds, question-speaker then response-speaker order, and punctuation.

## Long writing

Email uses approximately 40%/60% columns. The left panel begins immediately below the status row, with a thin pale border, rounded top corners around 16 pixels, and around 12 pixels padding. It contains scenario, bold requirements, three bullets, and the final instruction; it is not editable.

The right has Your Response, original To/Subject, then the nearly full-width editor. Its pale rounded frame contains an approximately 56-pixel light-gray toolbar: teal Cut, gray Paste/Undo/Redo, and right-aligned eye/Hide Word Count/count. The white editing area extends down the viewport. Buttons reflect available actions; source-style Paste does not authorize outside clipboard import in strict mode.

Discussion also uses 40%/60% columns:

- Left: scenario/requirements, centered professor portrait around 120–125 pixels, name, original question and paragraph breaks.
- Right: two student comments, each with a roughly 75-pixel portrait/name on the left and original comment on the right, without chat bubbles.
- Editor follows both comments. Its top follows actual content height, not a hard-coded vertical coordinate.

## Permitted claims

The observed reading/writing layouts can be described as source-based reproductions with preserved content. Visual acceptance requires comparable-width screenshots or overlays, checking that text is not truncated, reordered, or replaced. Sources differ in color, cropping, counts, clocks, and state; a bitmap does not establish exact fonts, zoom, physical display resolution, or initial time. Full production pixel/behavior parity remains unproved. Timing evidence is separately classified in [OFFICIAL_RULES.md](OFFICIAL_RULES.md).

## Public-client CSS evidence

On 2026-09-05, the user-provided [public ETS client entry](https://ibt2-toefl-pt.ets.org/ibt2tcweb/themes/toeflCompat/index.html) returned HTTP 200 without registration identifiers. Only explicitly referenced CSS/fonts were read: no cookies, forms, question/registration APIs, or new question downloads. Static verification and later interactive observation are separate.

- `toolbarToefl.css` and `toefl_enky.css` define default Open Sans; toolbar CSS imports it directly. Embedded content can override that default.
- Toolbar heights are 50/30 pixels; major buttons are 40 pixels high, radius 12, horizontal padding 24, font 13px/700. Section labels are 15px; question/time labels 13px/600 with 26px line height.
- Compatibility CSS specifies 1024-pixel container width, 686-pixel content, and 2-pixel divider. Adding 50/30 gives 768 pixels, matching the observed 4:3 canvas. Width is direct CSS evidence; total height is a structural inference supported by observation. Outer background is `#b4b4b4`. That September 5 static review did not establish an overall scaling algorithm or input-enlargement rule; the later live-cloze section records direct focus/blur observations without claiming a universal client rule.
- Static CSS contains both purple brand variables and teal compatibility rules. The later actual session was teal; that does not establish every theme. CSS and remaining clocks do not establish initial task duration.

Local read-only copies, explicit resource links, responses, and font hashes are under `tmp/qa/ets-client-static/`, without private registration parameters. Open Sans normal Latin/Latin-ext variable WOFF2 (weights 300–800) was obtained via the client's referenced Google Fonts CSS, stored under `public/fonts/`, and accompanied by copyright/OFL 1.1. Toolbar rules alone do not establish content/editor typography.

## Student notice cross-check

The authorized Sampler showed the same Dance cloze and Municipal Charter notice as local Student 1, in a teal/gray 4:3 canvas. The original PDF physical p. 4 was checked (SHA-256 `33e37aac4324d36a01af7ac0eb67b06aa438dfdf4fc96e31f4bdb72d9b8d9a2d`): centered bold title/subtitle and double thin white/gray frame matched existing `student-1-r1-11` and `student-1-r1-12`. No same-text Experience/Paid question was found among eighteen archives, so the style maps only to those IDs.

Normalized to 1024 pixels, the notice is roughly 356×168, about 70% of the left half. Two square gray borders are about 8 pixels apart; body side inset about 22; title roughly 14px bold centered, subtitle 11px bold centered, body 11px sans-serif, no scrollbar. `reference-material-layout.ts` selects `double-gray-notice` for those two IDs. The original continuous instruction retains title/subtitle/body; visual metadata does not author or replace text.

## Observed Listening states

The same authorized session provided these observations; its `Question 1 of 9` is a Sampler count only.

| State | Actual controls/content |
| --- | --- |
| Short-response playback | Volume only; question position, brief instruction, original portrait and visible disabled choices |
| Playback complete | Next appears and choices enable |
| Unanswered Next | Must Answer dialog with Return to Question; manual navigation validation, not extra time |
| Conversation playback | Volume, listening title, centered original people; no position/prompt/choices |
| Conversation response | Position, source people left, prompt/choices right; playback title removed |
| Academic Talk playback | Volume, source scene/title; no position/choices; only this playback state was observed |

No countdown was visible in those Sampler Listening pages. This does not remove source-supported local timers or establish official initial values. The local short-response disabled-choice exception and unanswered-Next check follow observation, while server expiry still advances automatically. Unseen states are not inferred from adjacent tasks.

## Observed Writing states and expiry

Build showed no clock. Unanswered Next moved directly to Email without an observed intermediate Begin; this differs from some PDF Begin pages and must stay a separate observation.

Email was `Question 1 of 2`, with Next/Hide Time and a first visible **06:56 remaining**. It was an existing Student 1 task, not imported online content. Layout was approximately 40%/60%, ordinary body 16px/21px, bold To/Subject around 16px, and the source toolbar described above.

Email Next opened a full-canvas **Time Remaining** confirmation, not a small modal. Back/Continue replaced navigation while question position and clock remained; first observed confirmation time was **05:50**. Back resumed the same editor; Continue left permanently. No time was paused or added.

Continue led directly to Discussion `Question 2 of 2`, first visible **09:34 remaining**, with 40%/60% layout, 16px/21px ordinary body, approximately 75-pixel students and 126-pixel professor. The initial session observation stopped here without microphone recording. Local build `index-DyFdUP0-.js` implemented that writing comparison and persistent-editor Back/Continue behavior; the identifier is historical, not a current build promise.

Later, Discussion had naturally expired. The source retained the question, removed its clock, and displayed **Writing Time Expired** with Continue, then Speaking instructions with two task types, eleven questions, Volume, and Begin. Speaking Begin was not clicked and no human recording was made by the assistant.

New local sessions freeze `writingExpiryAcknowledgement`: Email/Discussion expiry retains accepted answers read-only; the server rejects edits and Continue advances. Old sessions keep their frozen policy. Unsaved post-deadline browser drafts are not displayed as accepted answers. Speaking instructions use the observed/CSS-supported 50-pixel top bar. This observation does not establish unseen Reading, Listening, or Build expiry dialogs.
