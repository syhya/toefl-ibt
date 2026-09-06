"""Source-cache regressions use isolated color pages, never exam questions."""
from contextlib import ExitStack
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(importlib.util.find_spec("fitz") and importlib.util.find_spec("PIL"),
                     "Local PDF import dependencies are not installed")
class SourceCacheIntegrity(unittest.TestCase):
    def setUp(self):
        from scripts import import_materials
        self.importer = import_materials
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        for key, path in {"ROOT": self.root, "DATA": self.root / "data",
                          "OUT": self.root / "generated", "ASSETS": self.root / "generated/assets",
                          "CACHE": self.root / "generated/extracted"}.items():
            self.stack.enter_context(patch.object(self.importer, key, path))
            path.mkdir(parents=True, exist_ok=True)
        self.ocr = self.stack.enter_context(patch.object(self.importer.subprocess, "run", side_effect=self.fake_ocr))

    def fake_ocr(self, command, **kwargs):
        # Record the pixels sent to OCR without inventing textual test questions.
        self.assertEqual(command[0], "tesseract")
        digest = hashlib.sha256(Path(command[1]).read_bytes()).hexdigest()
        base = Path(command[2])
        base.with_suffix(".txt").write_text(digest)
        base.with_suffix(".tsv").write_text("level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n")

    def color_pdf(self, color):
        import fitz
        path = self.root / "data/source.pdf"
        with fitz.open() as document:
            page = document.new_page(width=80, height=100)
            page.draw_rect(page.rect, color=color, fill=color)
            document.save(path)
        return {"id": "cache-regression", "path": "source.pdf", "name": "source.pdf",
                "category": "pack", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    def test_changed_pdf_renders_new_pixels_before_new_ocr_hash_is_recorded(self):
        first = self.importer.prepare_pdf(self.color_pdf((1, 0, 0)), jobs=1)
        second_source = self.color_pdf((0, 0, 1))
        second = self.importer.prepare_pdf(second_source, jobs=1)
        self.assertNotEqual(first[0]["text"], second[0]["text"])
        cache = json.loads((self.root / "generated/extracted/cache-regression.json").read_text())
        self.assertEqual(cache["sha256"], second_source["sha256"])
        self.assertEqual(self.ocr.call_count, 2)

    def test_same_verified_source_reuses_ocr(self):
        source = self.color_pdf((1, 0, 0))
        first = self.importer.prepare_pdf(source, jobs=1)
        self.assertEqual(self.importer.prepare_pdf(source, jobs=1), first)
        self.assertEqual(self.ocr.call_count, 1)

    def test_unbound_legacy_page_and_existing_image_are_not_relabelled(self):
        from PIL import Image
        source = self.color_pdf((0, 0, 1))
        legacy = self.root / "tmp/pdfs" / hashlib.sha1(b"data/source.pdf").hexdigest()[:8]
        legacy.mkdir(parents=True)
        page_dir = self.root / "generated/assets/pages/cache-regression"
        page_dir.mkdir(parents=True)
        for path in [legacy / "p-01.jpg", page_dir / "page-001.jpg"]:
            Image.new("RGB", (80, 100), (255, 0, 0)).save(path)
        (legacy / "p-01.txt").write_text("unbound cache")
        (legacy / "p-01.tsv").write_text("")
        self.importer.prepare_pdf(source, jobs=1)
        with Image.open(page_dir / "page-001.jpg") as image:
            red, _, blue = image.getpixel((20, 20))
        self.assertGreater(blue, red)
        self.assertEqual(self.ocr.call_count, 1)

    def test_pack_columns_invalidate_same_question_cache_when_page_pixels_change(self):
        from PIL import Image
        from scripts.extract_pack_choices import extract
        page = self.root / "generated/assets/pages/cache-regression/page-001.jpg"
        page.parent.mkdir(parents=True)
        question = {"id": "cache-regression", "source": {"materialId": "cache-regression", "page": 1}}
        with patch("scripts.extract_pack_choices.subprocess.check_output", return_value=b"") as ocr:
            Image.new("RGB", (80, 100), (255, 0, 0)).save(page)
            first = extract(question, "reading", self.root)
            self.assertEqual(extract(question, "reading", self.root), first)
            self.assertEqual(ocr.call_count, 1)
            Image.new("RGB", (80, 100), (0, 0, 255)).save(page)
            second = extract(question, "reading", self.root)
        self.assertNotEqual(first["sourceImageSha256"], second["sourceImageSha256"])
        self.assertEqual(ocr.call_count, 2)

    def test_pack_columns_reject_legacy_cache_without_pixel_provenance(self):
        from PIL import Image
        from scripts.extract_pack_choices import extract
        page = self.root / "generated/assets/pages/cache-regression/page-001.jpg"
        page.parent.mkdir(parents=True)
        Image.new("RGB", (80, 100), (0, 0, 255)).save(page)
        cache = self.root / "generated/extracted/choice-columns/cache-regression.json"
        cache.parent.mkdir(parents=True)
        cache.write_text(json.dumps({"version": 3, "status": "parsed-with-source-image", "rawText": "unbound cache"}))
        question = {"id": "cache-regression", "source": {"materialId": "cache-regression", "page": 1}}
        with patch("scripts.extract_pack_choices.subprocess.check_output", return_value=b"") as ocr:
            result = extract(question, "reading", self.root)
        self.assertEqual(ocr.call_count, 1)
        self.assertEqual(result["version"], 4)
        self.assertEqual(result["sourceImageSha256"], hashlib.sha256(page.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
