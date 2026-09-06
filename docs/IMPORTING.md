# Importing your own resources

English | [简体中文](IMPORTING.zh-CN.md)

There are two supported workflows. **Portable JSON packs are the recommended path for a new user.** The historical PDF/OCR importer is specialized for the original private collection and requires its exact directory layout and private curation manifests. Adding an arbitrary PDF to `data/` does not automatically create an interactive exam.

## Try the bundled demonstration

After installation, run:

```sh
npm run demo
npm start
```

Or open the empty application's **Try the demo** action. The pack at [`examples/demo/pack.json`](../examples/demo/pack.json) has four original demonstration screens: a reading choice, a missing-letter paragraph, an email, and a discussion. It is short, text-only, untimed, and not an official question set. It can be installed alongside an existing private collection without replacing it. Installing identical content again is idempotent.

## Import text-only JSON in the website

Open **Help & setup**, choose a UTF-8 `.json` pack, and import it. The website's JSON import supports text-only packs. If a pack references any local file—an image, audio, video, or source PDF—use the command-line workflow below so the importer can read its containing directory. Finish an active strict session before importing through the application.

The displayed title is the exact string you supply. Application language switching does not translate your questions or custom title; a title may itself contain both languages if useful.

## Import a folder with media

Create a folder like this outside the repository, or in a local ignored location:

```text
my-practice/
  pack.json
  audio/prompt.mp3
  images/map.png
  source.pdf
```

From the repository root:

```sh
npm run import:pack -- "/absolute/path/to/my-practice/pack.json"
```

The importer validates the manifest and referenced files, copies them to a revisioned local resource directory, and registers the new archive. Refresh the site and choose the imported title under supplemental/all resources. No original resource folder needs to remain mounted for normal use after import. The source question collection and `storage/` answers are not overwritten.

For a changed pack using the same ID:

```sh
npm run import:pack -- "/absolute/path/to/my-practice/pack.json" --replace
```

A different pack with an existing ID is rejected without `--replace`; identical content is unchanged. Replacement publishes a new revision with distinct source/media paths. Existing sessions retain their frozen content; begin a new practice to use the new revision. Keep revision files while historical records refer to them.

## Minimal complete pack

Save this as `pack.json`; the content below is an original example, not a TOEFL source question:

```json
{
  "schemaVersion": 1,
  "id": "my-first-pack",
  "title": "My first reading practice",
  "sections": [
    {
      "id": "reading",
      "questions": [
        {
          "id": "opening-hours",
          "type": "choice",
          "taskType": "daily_life",
          "passage": "The community center opens at 10 a.m. on Sundays.",
          "prompt": "When does the center open on Sunday?",
          "choices": [
            {"id": "A", "text": "At 9 a.m."},
            {"id": "B", "text": "At 10 a.m."}
          ],
          "answer": "B"
        }
      ]
    }
  ]
}
```

`title` must be a string, not a translation object. JSON uses double quotes and cannot contain comments or trailing commas. The importer converts simple passage text into structured display blocks automatically.

## Manifest contract

The executable validation is [`backend/packs.py`](../backend/packs.py); [`examples/demo/pack.json`](../examples/demo/pack.json) is a working text-only example. Do not copy generated exam files as input: they contain internal fields that are intentionally rejected.

| Field | Requirement |
| --- | --- |
| `schemaVersion` | Number `1` |
| `id` | 1–48 lowercase letters/digits/hyphens/underscores; starts with a letter or digit; stable across revisions |
| `title` | Nonblank string, at most 200 characters |
| `sections` | 1–4 unique sections; each has `id` and 1–200 `questions` |
| Section `id` | `reading`, `listening`, `writing`, or `speaking` |
| Question `id` | Same identifier format; unique across the whole pack |
| Question `type` | Compatible with its section; see below |
| Question `prompt` | Nonblank string |
| `taskType` | Optional task classification, such as `daily_life` or `academic_passage` |
| `source` | Optional `{ "file": "source.pdf", "page": 1 }`; physical PDF page, starting at 1 |

Supported section/type combinations:

| Section | Types |
| --- | --- |
| Reading | `choice`, `cloze` |
| Listening | `choice` |
| Writing | `build_sentence`, `email`, `academic_discussion`, `picture_writing` |
| Speaking | `listen_repeat`, `interview`, `read_aloud` |

Listening and speaking imports currently require a local audio/video file for every question, including `read_aloud`. Packs are supplemental, guided, and untimed regardless of type; importing media does not grant full strict or official-source status.

Question fields accepted by version 1 are `id`, `type`, `taskType`, `prompt`, `passage`, `passageTemplate`, `context`, `choices`, `answer`, `blanks`, `tokens`, `slots`, `extraTokens`, `fixedTokens`, `recommendedWords`, `wordLimit`, `interaction`, `stemBlocks`, `assets`, `audio`, `source`, and `transcript`. Unknown fields are rejected. Do not add `strictEligible`, `expectedTokenOrder`, deadlines, generated URLs, or arbitrary CSS to a portable question.

### Choices, blanks, and sentence building

Choice questions need 2–8 choices with unique `id` and nonempty `text`. An optional `answer` must equal a choice ID; omit it when no reliable key is available. Missing keys are not guessed.

For cloze, use a `passageTemplate` with one `{{blank-id}}` per blank. Keep given letters in the template. Each blank needs a unique `id` and integer `length` from 1 to 30; `prefix`, `suffix`, `number`, and an optional missing-letter `answer` describe the input. The answer length must match the missing-letter count. For example:

```json
{
  "id": "garden",
  "type": "cloze",
  "prompt": "Enter only the missing letters.",
  "passageTemplate": "Volunteers wa{{b1}} the plants.",
  "blanks": [{"id": "b1", "number": 1, "prefix": "wa", "length": 3, "answer": "ter"}]
}
```

Build questions require nonempty string `tokens` and `slots`. A slot is `{ "id": "s1" }` for a movable token or `{ "fixed": "." }` for supplied text. Preserve duplicate tokens, distractors, fixed words, and punctuation; an `answer` can provide the reference sentence for review/scoring. Keep answer-bearing data out of `prompt` and `stemBlocks`.

### Audio, images, and original PDFs

```json
{
  "audio": {"file": "audio/prompt.mp3"},
  "assets": [{"file": "images/map.png", "alt": "Map showing the entrance and reading room"}],
  "source": {"file": "source.pdf", "page": 1}
}
```

These are optional question fields, except media is required for Listening/Speaking. Audio duration is probed from the file; a supplied guessed duration is not the authority. Images must decode and have a specific descriptive `alt`. Without custom `stemBlocks`, images follow the source text. With custom blocks, reference each image using an `essential_visual` block or dialogue avatar index.

File paths are relative to `pack.json`. Absolute paths, parent traversal (`..`), hidden path components, backslashes, and paths outside the pack are rejected. Supported extensions: `.pdf`, `.txt`, `.json`, `.png`, `.jpg`, `.jpeg`, `.webp`, `.mp3`, `.wav`, `.ogg`, `.m4a`, `.mp4`, `.webm`. Audio/image validation still applies; renaming an unsupported file does not convert it. Keep JSON below 2 MiB, each referenced file below 100 MiB, and referenced files together below 200 MiB.

A source PDF is provenance/reference, not an automatic OCR-to-question conversion. Source hashes make imported bytes traceable; they do not establish official authorship, correct answers, or copyright permission. You are responsible for the content you import or redistribute.

### Advanced structured layout

Use `stemBlocks` for separate paragraphs, instructions, titles, messages, dialogue, lists, tables, highlighted sentences, form diagrams, and visuals. The demo's discussion shows a professor and two student turns. To add your own authorized portraits, put images in `assets` and add each zero-based `avatarAssetIndex` to the corresponding dialogue turn. Keep names and comments in original order. The schema is validated by [`backend/presentation.py`](../backend/presentation.py); HTML/scripts are not a supported content format. Plain JSON is sufficient for most packs.

## Installed files and backup

```text
data/user-packs/<id>/<revision>/   Copied manifest and local assets
generated/pack-catalogs/<id>.json  Portable-pack registry
generated/exams/user-<id>.json    Current normalized exam
storage/                         Existing answers and recordings
```

The runtime combines pack registries with any private base catalog. Back up `data/`, `generated/`, and `storage/` together to retain resources and history. Import does not upload files to a remote service. For storage consistency and pending recording drafts, see [the user guide](USER_GUIDE.md).

## Original private PDF/OCR collection

This advanced importer supports the original known directory, not arbitrary PDFs. It requires legally obtained source files and their matching private `scripts/verified_*.json` records, which are not distributed in the public repository. New users should use portable packs instead.

```sh
.venv/bin/python -m pip install -r requirements-import.txt
tesseract --list-langs
.venv/bin/python scripts/import_materials.py --jobs 4
```

Tesseract and `eng` language data are external prerequisites for OCR. `--ocr-all` expands scanned-page extraction, but extraction alone does not mark content source-verified. Preserve original filenames/directories and back up before reimport. Do not rerun full OCR on every launch; generated content is reused.

The pipeline validates source SHA, pages, content identity, curated choices/blanks, structured blocks, and media/visual provenance. Missing manifests or mismatches close affected strict scopes instead of inventing content. Rebuild interface assets if needed with `.venv/bin/python scripts/extract_exam_ui.py`; verify the installed teacher supplement offline with `.venv/bin/python scripts/attach_teacher_audio.py`. See [materials](MATERIALS.md), [source-data audit](DATA_QA.md), and [media segmentation](MEDIA_SEGMENTS.md) for the dated private collection methodology.
