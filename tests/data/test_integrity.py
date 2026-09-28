"""Read-only acceptance checks for the real private source collection.

Run with ``python -m unittest discover -s tests/data -v``. A public checkout
without data/generated skips these tests; no fixtures are written into the bank.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit
import wave

from backend.presentation import validate_question as validate_presentation

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_EXAMS = {*(f"experience-{n}" for n in range(1, 4)), *(f"pack-{n}" for n in range(1, 7)),
                  *(f"student-{n}" for n in range(1, 3)), *(f"teacher-{n}" for n in range(1, 3)),
                  *(f"paid-{n}" for n in range(1, 3)), *(f"essentials-{n}" for n in range(1, 4))}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def items(exam):
    for section in exam.get("sections", []):
        for module in section.get("modules", []):
            for question in module.get("questions", []):
                yield section, module, question


def units(question):
    return len(question.get("blanks", [])) if question.get("type") == "cloze" else 1


def available(question):
    return not question.get("referenceOnly") or question.get("sourcePromptAvailable") is True


def value_present(value):
    return value is not None and value != "" and value != [] and value != {}


def unresolved(item):
    return item.get("answerConflict", {}).get("status") == "needs-review" or item.get("auditStatus") == "answer-conflict"


def verified_structured_content(question):
    """Accept structured content only when the production schema accepts it."""
    return (question.get("presentationSchema") == "structured-v1"
            and question.get("structuredContentStatus") == "source-verified"
            and isinstance(question.get("stemBlocks"), list)
            and bool(question["stemBlocks"])
            and not validate_presentation(question, strict=True))


def scorable(question):
    if not available(question) or unresolved(question):
        return 0
    if question.get("type") == "cloze":
        return sum(value_present(b.get("answer")) and not unresolved(b) for b in question.get("blanks", []))
    if question.get("type") in {"email", "academic_discussion", "picture_writing", "listen_repeat", "interview", "read_aloud"}:
        return 0
    return int(value_present(question.get("answer")))


def local_url(url):
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc:
        raise ValueError("Question asset must be local")
    path = unquote(parsed.path)
    if path.startswith("/materials/"):
        base, relative = ROOT / "data", path[len("/materials/"):]
    elif path.startswith("/assets/"):
        base, relative = ROOT / "generated/assets", path[len("/assets/"):]
    else:
        raise ValueError(f"Unknown source asset URL: {path}")
    target = (base / relative).resolve()
    if not target.is_relative_to(base.resolve()):
        raise ValueError("Source asset escapes its allowed directory")
    return target


def normalize(value):
    return re.sub(r"[^a-z0-9']", "", str(value).lower().replace("’", "'"))


def reachable_sentence(question):
    """Check only that the supplied answer can use the supplied blocks/slots.

    This does not infer, select, or assert a unique correct answer.
    """
    target = normalize(question["answer"])
    tokens = [normalize(t) for t in question["tokens"]]
    slots = question["slots"]
    failed = set()

    def visit(i, position, used):
        key = i, position, used
        if key in failed:
            return False
        if i == len(slots):
            return position == len(target)
        slot = slots[i]
        fixed = slot if isinstance(slot, str) else slot.get("fixed") or slot.get("text") or ""
        if fixed:
            text = normalize(fixed)
            result = target.startswith(text, position) and visit(i + 1, position + len(text), used)
        else:
            result = any(not used & (1 << j) and text and target.startswith(text, position)
                         and visit(i + 1, position + len(text), used | (1 << j))
                         for j, text in enumerate(tokens))
        if not result:
            failed.add(key)
        return result

    return visit(0, 0, 0)


class RealDataIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        catalog_path = ROOT / "generated/catalog.json"
        if not (ROOT / "data").is_dir() or not catalog_path.is_file():
            raise unittest.SkipTest("Private data/generated collection is not installed")
        initial = read_json(catalog_path)
        private_ids = {e['id'] for e in initial.get('exams', []) + initial.get('supplementalExams', [])}
        if (initial.get('bundledExample') in [
                {'id': 'ets-practice-test-1', 'version': 1},
                {'id': 'ets-practice-test-1', 'version': 2, 'profile': 'runtime-only'},
                {'id': 'ets-practice-test-1', 'version': 3, 'profile': 'runtime-only'}]
                and private_ids == {'student-1'}
                and not (ROOT / 'scripts/verified_paper.json').is_file()):
            raise unittest.SkipTest('The official Practice Test 1 bundle is checked by test_bundled_example; the private 18-pack archive is not installed')
        if not private_ids and not initial.get('materials'):
            raise unittest.SkipTest("Portable packs are installed; the private source collection is not installed")
        if not (ROOT / 'scripts/verified_paper.json').is_file():
            raise unittest.SkipTest(
                'The legacy private curation is not installed; reconstructed snapshots '
                'are checked independently by test_recovered_collection')
        # Portable registries are validated separately. Their generated exams do
        # not become extra members of the fixed, historical source collection.
        files = [catalog_path, *sorted((ROOT / 'generated/exams' / f'{eid}.json') for eid in private_ids)]
        before = {str(p): (p.stat().st_mtime_ns, p.stat().st_size) for p in files}
        cls.catalog = read_json(catalog_path)
        cls.exams = {p.stem: read_json(p) for p in files[1:]}
        after = {str(p): (p.stat().st_mtime_ns, p.stat().st_size) for p in files}
        if before != after:
            raise unittest.SkipTest("Import snapshot changed during reading; rerun after import completes")
        cls.snapshot = before
        cls.materials = {m["id"]: m for m in cls.catalog["materials"]}
        cls.questions = {q["id"]: q for e in cls.exams.values() for _, _, q in items(e)}

    def assert_no_errors(self, errors):
        self.assertTrue(not errors, "\n".join(errors[:25]) + (f"\n... {len(errors)} total" if len(errors) > 25 else ""))

    def test_catalog_has_only_the_eighteen_source_archives(self):
        rows = self.catalog.get("exams", []) + self.catalog.get("supplementalExams", [])
        ids = [e["id"] for e in rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), EXPECTED_EXAMS)
        self.assertEqual(set(self.exams), set(ids))
        self.assertFalse(any(re.search(r"fixture|e2e|synthetic|placeholder", x, re.I) for x in ids))
        self.assertEqual(len(self.materials), len(self.catalog["materials"]))
        self.assertEqual(self.catalog["stats"]["fileCount"], len(self.materials) + len(self.catalog.get("excludedSystemFiles", [])))
        actual_files = {path.relative_to(ROOT / "data").as_posix() for path in (ROOT / "data").rglob("*")
                        if path.is_file() and path.relative_to(ROOT / "data").parts[0] != 'user-packs'
                        and not any(part.startswith(".") for part in path.relative_to(ROOT / "data").parts)}
        self.assertEqual(actual_files, {m["path"] for m in self.materials.values()},
                         "Every supplied non-hidden file must appear in the source catalog")

    def test_original_material_paths_sizes_and_hashes(self):
        errors = []
        for m in self.materials.values():
            path = (ROOT / "data" / m["path"]).resolve()
            if not path.is_relative_to((ROOT / "data").resolve()) or not path.is_file():
                errors.append(f"{m['id']}: invalid original path")
                continue
            if path.stat().st_size != m["bytes"]:
                errors.append(f"{m['id']}: original byte size changed")
            digest = hashlib.sha256()
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != m["sha256"]:
                errors.append(f"{m['id']}: original SHA-256 changed")
        self.assert_no_errors(errors)

    def test_every_question_has_a_real_original_page_and_number(self):
        errors, ids = [], []
        for eid, exam in self.exams.items():
            for section, module, q in items(exam):
                ids.append(q["id"])
                source = q.get("source", {})
                material = self.materials.get(source.get("materialId"))
                if not material or material["kind"] != "pdf":
                    errors.append(f"{q['id']}: missing original question PDF")
                    continue
                if re.search(r"参考答案|官方答案|听力原文|rubrics|lesson-plan", material["name"], re.I):
                    errors.append(f"{q['id']}: question sourced from an answer/reference-only document")
                page = source.get("page")
                if not isinstance(page, int) or not 1 <= page <= material["pages"]:
                    errors.append(f"{q['id']}: invalid original page")
                if unquote(urlsplit(source.get("url", "")).path) != "/materials/" + material["path"]:
                    errors.append(f"{q['id']}: original URL does not identify the declared material")
                if source.get("sha256") and source["sha256"] != material["sha256"]:
                    errors.append(f"{q['id']}: original source SHA mismatch")
                original_number = source.get("originalNumber")
                # The supplied PDFs themselves contain skipped/restarted and
                # occasionally unprinted numbers. Preserve those facts instead
                # of demanding that the normalized app number equal the print.
                documented_unprinted = source.get("originalNumberStatus") in {"not-printed", "unprinted"} or bool(source.get("numberingNote") or q.get("numberingNote"))
                if not isinstance(q.get("number"), int) or q["number"] < 1:
                    errors.append(f"{q['id']}: invalid normalized question number")
                if not (isinstance(original_number, int) and original_number >= 1) and not documented_unprinted:
                    errors.append(f"{q['id']}: missing original number lacks an explicit unprinted-number note")
                if not q["id"].startswith(eid + "-") or re.search(r"fixture|e2e|synthetic|placeholder", q["id"], re.I):
                    errors.append(f"{q['id']}: non-source/test question ID")
                if not any([verified_structured_content(q), q.get("assets"), q.get("passage"), q.get("passageTemplate"), q.get("audio"), q.get("tokens"),
                            q.get("sourcePromptAvailable") and len(q.get("prompt", "")) > 20]):
                    errors.append(f"{q['id']}: no real visible or audible question content")
        self.assertEqual(len(ids), len(set(ids)), "Question IDs must be unique across editions")
        self.assert_no_errors(errors)

    def test_structured_questions_match_their_frozen_source_curation(self):
        from scripts.structure_questions import load as load_structured_curation
        from backend.text_corrections import MANIFEST_PATH, read_manifest, field_value
        records = load_structured_curation(ROOT)["questions"]
        errata_path = ROOT / MANIFEST_PATH
        errata = read_manifest(errata_path)['questions'] if errata_path.is_file() else {}
        self.assertEqual(set(records), set(self.questions))
        errors, hashes = [], {}
        for eid, exam in self.exams.items():
            for _, _, q in items(exam):
                record = records[q["id"]]
                expected_text = deepcopy(record)
                # Compare against the layered provenance independently: base
                # source curation, followed by exact approved textual errata.
                for patch in errata.get(q['id'], {}).get('patches', []):
                    if patch['path'][0] not in expected_text:
                        continue
                    try:
                        before = field_value(expected_text, patch['path'])
                    except ValueError:
                        before = None
                    self.assertEqual(before, patch['before'], f"{q['id']}: stale layered curation")
                    parent = field_value(expected_text, patch['path'][:-1])
                    parent[patch['path'][-1]] = patch['after']
                source = q["source"]
                material = self.materials[source["materialId"]]
                if (record.get("examId") != eid or record.get("materialId") != material["id"] or
                        record.get("page") != source["page"] or record.get("sourceSha256") != material["sha256"] or
                        record.get("contentId") != q.get("curatedContentId") or not record.get("verificationBasis")):
                    errors.append(f"{q['id']}: structured curation lacks matching source identity/evidence")
                for field in ["stemBlocks", "prompt", "passage", "passageTemplate", "context", "choices", "transcript",
                              "tokens", "slots", "extraTokens", "fixedTokens", "interaction", "wordLimit", "recommendedWords"]:
                    if field in expected_text and expected_text[field] != q.get(field):
                        errors.append(f"{q['id']}: {field} differs from the source curation")
                if record.get("essentialVisualAssets", []) != q.get("assets", []):
                    errors.append(f"{q['id']}: active visual metadata differs from the source curation")
                for field in ["sourceEvidenceSha256", "essentialVisualSha256"]:
                    for url, expected in record.get(field, {}).items():
                        try:
                            if url not in hashes:
                                hashes[url] = hashlib.sha256(local_url(url).read_bytes()).hexdigest()
                            if hashes[url] != expected:
                                errors.append(f"{q['id']}: {field} asset differs from the frozen source curation")
                        except (ValueError, OSError) as error:
                            errors.append(f"{q['id']}/{field}: {error}")
        self.assert_no_errors(errors)

    def test_paired_teacher_audio_keeps_transcripts_out_of_active_content(self):
        from scripts.teacher_audio_presentation import finalize, safe_audio_blocks
        teachers = [self.exams[f"teacher-{n}"] for n in [1, 2]]
        questions = [q for exam in teachers for section, _, q in items(exam)
                     if section["id"] in {"listening", "speaking"}]
        if not any(q.get("mediaAudit", {}).get("officialArchiveUrl") for q in questions):
            self.skipTest("The optional paired ETS teacher audio supplement is not installed")
        self.assertEqual(len(questions), 90)
        self.assertTrue(all(safe_audio_blocks(q) for q in questions))
        self.assertTrue(all(q.get("audio", {}).get("verified") is True and not q.get("referenceOnly") for q in questions))
        self.assertTrue(all(q.get("transcript") and q["transcript"] != q["prompt"] for q in questions))
        for exam in teachers:
            self.assertIn("scripts/verified_teacher_audio.json", exam["verificationInputs"]["curationSha256ByPath"])
        # Regression: an audited recording must not promote the old text-study
        # layout, and a missing recording must not leave strict scope enabled.
        contaminated = deepcopy(teachers[0])
        first = next(q for section, _, q in items(contaminated) if section["id"] == "listening")
        first["stemBlocks"].append({"type": "paragraph", "text": first["transcript"]})
        with self.assertRaisesRegex(ValueError, "exposes source stimulus text"):
            finalize([contaminated])
        missing = deepcopy(teachers[0])
        first = next(q for section, _, q in items(missing) if section["id"] == "listening")
        first.pop("audio")
        result = finalize([missing])
        self.assertFalse(missing["strictEligible"])
        self.assertFalse(missing["scopedEligibility"]["listening"])
        self.assertFalse(first["sourcePromptAvailable"])
        self.assertEqual(result["unavailableQuestionIds"], [first["id"]])

    def test_counts_and_exclusions_match_source_items(self):
        errors = []
        for eid, exam in self.exams.items():
            qs = [q for _, _, q in items(exam)]
            count, screens = sum(map(units, qs)), len(qs)
            if exam.get("questionCount") != count or exam.get("screenCount") != screens:
                errors.append(f"{eid}: item/screen count mismatch")
            if exam.get("interactiveQuestionCount") is not None and exam["interactiveQuestionCount"] != sum(units(q) for q in qs if available(q)):
                errors.append(f"{eid}: reference-only unavailable question counted as interactive")
            if exam.get("autoScorableCount") != sum(map(scorable, qs)):
                errors.append(f"{eid}: autoScorableCount={exam.get('autoScorableCount')} actual={sum(map(scorable, qs))}")
            for _, module, _ in items(exam):
                expected = module.get("expectedItemCount")
                if expected is not None and expected != sum(units(q) for q in module["questions"]):
                    errors.append(f"{eid}/{module['id']}: expectedItemCount differs from actual source units")
            if exam.get("family") == "essentials":
                excluded = [x for s in exam["sections"] for x in s.get("excludedTasks", [])]
                if count + len(excluded) != exam["expectedSourceQuestionCount"]:
                    errors.append(f"{eid}: interactive + excluded source count mismatch")
                if exam.get("strictEligible") or not exam.get("supplemental") or exam.get("timingPolicy") != "untimed":
                    errors.append(f"{eid}: Essentials must remain an untimed supplement")
                if any(not x.get("source") or not x.get("reason") or not x.get("originalNumber") for x in excluded):
                    errors.append(f"{eid}: excluded source item lacks traceable evidence")
        self.assert_no_errors(sorted(set(errors)))

    def test_assets_and_audio_resolve_with_original_provenance(self):
        errors = []
        for exam in self.exams.values():
            for section, module, q in items(exam):
                entries = [("stem", a) for a in q.get("assets", [])]
                entries += [(field, q[field]) for field in ["audio", "cueAudio", "directionsAudio"] if q.get(field)]
                for role, a in entries:
                    url = a.get("url", "")
                    try:
                        target = local_url(url)
                        if not target.is_file():
                            raise ValueError("missing asset")
                    except (ValueError, OSError) as error:
                        errors.append(f"{q['id']}/{role}: {error}")
                        continue
                    if "/_analysis/" in url or re.search(r"fixture|e2e|placeholder", url, re.I):
                        errors.append(f"{q['id']}/{role}: private-analysis/test asset exposed as question")
                    if role == "stem":
                        continue
                    mid = a.get("materialId") or a.get("sourceMaterialId")
                    source = self.materials.get(mid)
                    if not source or source["kind"] not in {"audio", "video"}:
                        errors.append(f"{q['id']}/{role}: missing original audio/video source")
                        continue
                    if a.get("sourceSha256") and a["sourceSha256"] != source["sha256"]:
                        errors.append(f"{q['id']}/{role}: source SHA mismatch")
                    if role == "audio" and a.get("scope") == "section":
                        errors.append(f"{q['id']}: whole study track attached to every question")
                    spans = a.get("sourceIntervals") or ([a] if "startSeconds" in a else [])
                    for span in spans:
                        start, end = span.get("startSeconds"), span.get("endSeconds")
                        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or not 0 <= start < end <= source.get("durationSeconds", end) + .25:
                            errors.append(f"{q['id']}/{role}: invalid source audio interval")
                    if target.suffix.lower() == ".wav":
                        try:
                            with wave.open(str(target), "rb") as wav:
                                duration = wav.getnframes() / wav.getframerate()
                            if a.get("durationSeconds") and abs(duration - a["durationSeconds"]) > .03:
                                errors.append(f"{q['id']}/{role}: exported WAV duration mismatch")
                        except (wave.Error, EOFError):
                            errors.append(f"{q['id']}/{role}: invalid WAV")
        self.assert_no_errors(errors)

    def test_academic_discussions_have_three_source_portraits(self):
        discussions = [q for q in self.questions.values() if q.get("type") == "academic_discussion"]
        self.assertEqual(len(discussions), 18)
        urls, errors = [], []
        for q in discussions:
            dialogues = [block for block in q.get("stemBlocks", []) if block.get("type") == "dialogue"]
            if len(dialogues) != 1 or len(dialogues[0].get("turns", [])) != 3:
                errors.append(f"{q['id']}: academic discussion must contain professor plus two students")
                continue
            assets = q.get("assets", [])
            turns = dialogues[0]["turns"]
            indices = [turn.get("avatarAssetIndex") for turn in turns]
            if indices != [0, 1, 2] or len(assets) != 3:
                errors.append(f"{q['id']}: three dialogue turns are not bound to three portraits")
                continue
            for turn, asset in zip(turns, assets):
                urls.append(asset.get("url"))
                if (asset.get("role") != "essentialVisual" or asset.get("highResolution") is not True or
                        not isinstance(asset.get("width"), int) or asset["width"] < 200 or
                        not isinstance(asset.get("height"), int) or asset["height"] < 200 or
                        "portrait" not in str(asset.get("alt", "")).casefold()):
                    errors.append(f"{q['id']}/{turn.get('speaker')}: portrait metadata is incomplete")
                try:
                    if not local_url(asset.get("url", "")).is_file():
                        errors.append(f"{q['id']}/{turn.get('speaker')}: portrait file is missing")
                except (ValueError, OSError) as error:
                    errors.append(f"{q['id']}/{turn.get('speaker')}: {error}")
        self.assertEqual(len(urls), 54)
        self.assertEqual(len(set(urls)), 48)
        self.assert_no_errors(errors)

    def test_pack_builds_keep_source_portraits_and_printed_punctuation(self):
        question_marks = {(1, 2), (4, 10), (5, 3), (5, 9), (6, 2)}
        builds = [q for q in self.questions.values() if q.get("type") == "build_sentence"
                  and q["id"].startswith(("pack-", "paid-"))]
        self.assertEqual(len(builds), 80)
        urls = []
        for q in builds:
            canonical = q.get("canonicalQuestionId", q["id"])
            match = re.fullmatch(r"pack-(\d)-writing-build-(\d+)", canonical)
            self.assertIsNotNone(match, canonical)
            source_number = tuple(map(int, match.groups()))
            punctuation = "?" if source_number in question_marks else "."
            self.assertTrue(q["slots"][-1].get("fixed", "").rstrip().endswith(punctuation), q["id"])
            self.assertEqual(len(q.get("assets", [])), 2, q["id"])
            blocks = q["stemBlocks"]
            self.assertEqual([b["type"] for b in blocks], ["essential_visual", "paragraph", "essential_visual"], q["id"])
            self.assertEqual([blocks[0]["assetIndex"], blocks[2]["assetIndex"]], [0, 1])
            self.assertEqual(blocks[1]["text"], q["context"])
            for asset in q["assets"]:
                urls.append(asset["url"])
                self.assertEqual(asset["role"], "essentialVisual")
                self.assertTrue(asset["highResolution"])
                self.assertGreaterEqual(asset["width"], 200)
                self.assertGreaterEqual(asset["height"], 200)
            if q.get("canonicalQuestionId"):
                self.assertEqual(q["assets"], self.questions[canonical]["assets"])
            self.assertEqual(sum("id" in slot for slot in q["slots"]), q["blockValidation"]["slotCount"])
        self.assertEqual(len(urls), 160)
        self.assertEqual(len(set(urls)), 120)

    def test_community_post_keeps_its_original_symbol_and_comma(self):
        first = self.questions["pack-4-reading-m1-11"]
        second = self.questions["pack-4-reading-m1-12"]
        for q in [first, second]:
            self.assertEqual(len(q["assets"]), 1)
            self.assertEqual(q["assets"][0]["role"], "essentialVisual")
            self.assertTrue(q["assets"][0]["highResolution"])
            self.assertEqual([b["type"] for b in q["stemBlocks"]],
                             ["instruction", "essential_visual", "paragraph", "question"])
            self.assertEqual(q["stemBlocks"][1]["assetIndex"], 0)
            self.assertIn("language, meet", q["stemBlocks"][2]["text"])
            self.assertNotIn("language. meet", q["stemBlocks"][2]["text"])
        self.assertEqual(first["assets"], second["assets"])
        self.assertEqual(first["source"]["page"], 4)
        self.assertEqual(second["source"]["page"], 5)
        self.assertEqual(second["stimulusSource"]["page"], 4)
        self.assertEqual(second["stimulusSource"]["materialId"], first["source"]["materialId"])

    def test_section_module_and_reference_asset_links_exist(self):
        errors = []

        def walk(value, trace):
            if isinstance(value, list):
                for i, item in enumerate(value):
                    walk(item, f"{trace}/{i}")
            elif isinstance(value, dict):
                for key, child in value.items():
                    if key in {"url", "sourcePageAsset"} and isinstance(child, str) and child.startswith(("/assets/", "/materials/")):
                        try:
                            if not local_url(child).is_file():
                                errors.append(f"{trace}/{key}: missing local asset")
                            if "/_analysis/" in child:
                                errors.append(f"{trace}/{key}: analysis cache exposed as an asset")
                        except (ValueError, OSError) as error:
                            errors.append(f"{trace}/{key}: {error}")
                    walk(child, f"{trace}/{key}")

        for eid, exam in self.exams.items():
            walk(exam, eid)
        self.assert_no_errors(errors)

    def test_cloned_editions_have_per_question_source_evidence(self):
        errors = []
        for exam in self.exams.values():
            for _, _, q in items(exam):
                canonical_id = q.get("canonicalQuestionId") or q.get("source", {}).get("canonicalQuestionId")
                if not canonical_id:
                    continue
                if canonical_id not in self.questions or canonical_id == q["id"]:
                    errors.append(f"{q['id']}: invalid canonical question pointer")
                edition = q.get("editionSource")
                if not isinstance(edition, dict):
                    errors.append(f"{q['id']}: copied edition has no per-question editionSource")
                    continue
                source = self.materials.get(edition.get("materialId"))
                if not source or source["kind"] != "pdf" or not isinstance(edition.get("page"), int) or not 1 <= edition["page"] <= source["pages"]:
                    errors.append(f"{q['id']}: invalid editionSource page/material")
                elif edition.get("sha256") != source["sha256"] or unquote(urlsplit(edition.get("url", "")).path) != "/materials/" + source["path"]:
                    errors.append(f"{q['id']}: editionSource hash/URL differs from the declared original")
        self.assert_no_errors(errors)

    def test_cloze_templates_and_given_letters_are_consistent(self):
        errors = []
        for q in self.questions.values():
            if q.get("type") != "cloze":
                continue
            blanks = q.get("blanks", [])
            ids = [b["id"] for b in blanks]
            if len(ids) != len(set(ids)):
                errors.append(f"{q['id']}: duplicate blank IDs")
            if q.get("passageTemplate"):
                actual = re.findall(r"\{\{([^{}]+)\}\}", q["passageTemplate"])
                if Counter(actual) != Counter(ids):
                    errors.append(f"{q['id']}: template does not contain each blank exactly once")
            for b in blanks:
                if not value_present(b.get("answer")):
                    continue
                missing = b.get("missingLetters", b["answer"])
                full = b.get("fullWord")
                if b.get("length") and len(missing) != b["length"]:
                    errors.append(f"{q['id']}/{b['id']}: missing-letter length differs from visible slots")
                if full and normalize(b.get("prefix", "") + missing + b.get("suffix", "")) != normalize(full):
                    errors.append(f"{q['id']}/{b['id']}: prefix + missing + suffix differs from full word")
        self.assert_no_errors(errors)

    def test_native_choices_and_slots_can_accept_the_provided_answer(self):
        errors = []
        for q in self.questions.values():
            if q.get("type") == "choice" and value_present(q.get("answer")) and not unresolved(q):
                choices = [c["id"] for c in q.get("choices", [])]
                if len(choices) != len(set(choices)) or q["answer"] not in choices:
                    errors.append(f"{q['id']}: supplied answer absent from source choice IDs")
            if q.get("type") == "build_sentence" and q.get("slots") and q.get("tokens") and isinstance(q.get("answer"), str) and not unresolved(q):
                if not reachable_sentence(q):
                    errors.append(f"{q['id']}: supplied answer is not reachable with the source blocks/fixed slots")
        self.assert_no_errors(errors)

    def test_pdf_page_counts_when_pdf_reader_is_available(self):
        if importlib.util.find_spec("pypdf") is None:
            self.skipTest("pypdf is optional outside the local import environment")
        from pypdf import PdfReader
        errors = []
        for material in self.materials.values():
            if material["kind"] == "pdf" and len(PdfReader(ROOT / "data" / material["path"]).pages) != material["pages"]:
                errors.append(f"{material['id']}: actual PDF page count differs from catalog")
        self.assert_no_errors(errors)


if __name__ == "__main__":
    unittest.main()
