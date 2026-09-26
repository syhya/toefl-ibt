# Importing your own resources

**Start with the bundled TOEFL iBT® Practice Test 1; use portable JSON packs to add your own content.** The curated Practice Test 1 installer preserves the full reference exam and its verified media. The portable importer accepts a separate authoring schema and creates untimed supplementary resources. The historical PDF/OCR importer is specialized for the original full private collection and requires its exact directory layout and private curation manifests. Adding an arbitrary PDF to `data/` does not automatically create an interactive exam.

## Install the complete TOEFL iBT® Practice Test 1

After installation, run:

```sh
npm run demo
npm start
```

Or choose **Try Practice Test 1** on an empty homepage or in **Help & setup**. The complete package at [`examples/ets-practice-test-1/`](../examples/ets-practice-test-1/README.md) contains 97 question items across 79 screens: Reading 40 items/22 screens, Listening 34/34, Writing 12/12, and Speaking 11/11. Its prepared questions, extracted explanations, audio clips, portraits, and review evidence are included; the original PDFs and full MP3 tracks are optional and omitted. Corrected structured text and the original module/task arrangement are retained. The current v3 audio edition supports strict local practice in all sections. Interview question 1 deliberately follows the original companion audio rather than the different paper prompt; setup and review disclose this edition difference.

This is the default newcomer dataset. No OCR or private collection is needed. Installation validates the bundled files before registering Practice Test 1. An existing `student-1` in your full local collection is reused, so this action does not duplicate it or replace personal records. Repeating installation is safe. To upgrade an installed lightweight v2 example, stop the service, run `npm run demo -- --upgrade`, and restart. The explicit upgrade preserves saved sessions and old media/provenance; private full-source imports are not overwritten. The package uses `manifest.json` and internal `exam.json`; these are not portable JSON input files and must not be passed to `import:pack`. Source attribution and third-party rights are documented in the package [notice](../examples/ets-practice-test-1/NOTICE.md).

Keep every tracked example file: 53 prepared assets and four metadata JSON files, plus the manifest and notices. The runtime payload is approximately 18.3 MB. The 13 originals listed in `optionalOriginals` are provenance references, not required downloads; the local `materials/` folder is ignored by Git. Prepared-content/media hashes remain mandatory. Only the allowlisted `runtime-only` example profile permits absent originals, and it requires a matching provenance record. Private archives and portable packs do not inherit this exception.

Reusing an existing verified `student-1` is intentionally a no-op, not an upgrade command. If the installed sources are changed or missing, restore that installation's matching files/catalog before retrying; replacing only the example directory does not repair an already damaged local exam. There is no `--replace` option for the native example. The `--replace` workflow below applies only to custom portable packs.

## Refresh the bundled example (maintainers only)

The exporter requires the verified original curated `student-1` exam and private source/errata inputs; it is not part of a new user's installation and cannot export from an already installed example snapshot. Supply an unmodified copy of the documented ETS PDF; its bytes must match the source question paper:

```sh
.venv/bin/python scripts/export_example.py --official-pdf /path/to/toefl-ibt-full-length-practice-test-1.pdf --overview-pdf /path/to/toefl-ibt-test-overview.pdf
```

The exporter derives the native example and resource hashes from those verified inputs. `MATERIAL_FILENAMES` defines the public English names, while original source URLs/installation paths stay unchanged. It rejects unresolved dependencies and stale extra files instead of publishing them. Review the resulting complete package and test a clean install before distribution; do not run the full private importer merely to start the sample.

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

The executable validation is [`backend/packs.py`](../backend/packs.py). The [minimal JSON above](#minimal-complete-pack) is the starting point for your own text-only content; the default installed reference set is TOEFL iBT® Practice Test 1. Do not copy generated exam files as input: they contain internal fields that are intentionally rejected.

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

Use `stemBlocks` for separate paragraphs, instructions, titles, messages, dialogue, lists, tables, highlighted sentences, form diagrams, and visuals. The bundled TOEFL iBT® Practice Test 1 shows the complete source discussion with a professor, two students, and their portraits. To add your own authorized portraits, put images in `assets` and add each zero-based `avatarAssetIndex` to the corresponding dialogue turn. Keep names and comments in original order. The schema is validated by [`backend/presentation.py`](../backend/presentation.py); HTML/scripts are not a supported content format. Plain JSON is sufficient for most packs.

## Installed files and backup

The curated TOEFL iBT® Practice Test 1 installer registers `generated/exams/student-1.json` in `generated/catalog.json`, with prepared media/provenance under `generated/assets/`; original `data/` files are optional for this allowlisted profile. It preserves an existing verified Practice Test 1; it does not overwrite a changed local archive. Portable custom packs use the separate revisioned paths below:

```text
data/user-packs/<id>/<revision>/   Copied manifest and local assets
generated/pack-catalogs/<id>.json  Portable-pack registry
generated/exams/user-<id>.json    Current normalized exam
storage/                         Existing answers and recordings
```

The runtime combines pack registries with any private base catalog. Back up `data/`, `generated/`, and `storage/` together to retain resources and history. Import does not upload files to a remote service. For storage consistency and pending recording drafts, see [the user guide](USER_GUIDE.md).

## Original private PDF/OCR collection

This advanced importer supports the original known directory, not arbitrary PDFs. It requires legally obtained source files and their matching private `scripts/verified_*.json` records, which are not distributed in the public repository. Use the bundled TOEFL iBT® Practice Test 1 for a complete starting set, or portable packs for new custom content.

```sh
.venv/bin/python -m pip install -r requirements-import.txt
tesseract --list-langs
.venv/bin/python scripts/import_materials.py --jobs 4
```

Tesseract and `eng` language data are external prerequisites for OCR. `--ocr-all` expands scanned-page extraction, but extraction alone does not mark content source-verified. Preserve original filenames/directories and back up before reimport. Do not rerun full OCR on every launch; generated content is reused.

The pipeline validates source SHA, pages, content identity, curated choices/blanks, structured blocks, and media/visual provenance. Missing manifests or mismatches close affected strict scopes instead of inventing content. Rebuild interface assets if needed with `.venv/bin/python scripts/extract_exam_ui.py`; verify the installed teacher supplement offline with `.venv/bin/python scripts/attach_teacher_audio.py`. See [materials](MATERIALS.md), [source-data audit](DATA_QA.md), and [media segmentation](MEDIA_SEGMENTS.md) for the dated private collection methodology.
