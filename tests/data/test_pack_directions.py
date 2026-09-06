"""Read-only checks for source-backed directions in the private real collection."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from backend import engine
from scripts.attach_pack_directions import EXAMS, attach

ROOT = Path(__file__).resolve().parents[2]


class PackDirections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "scripts/verified_pack_directions.json"
        if not path.is_file() or not (ROOT / "generated/catalog.json").is_file():
            raise unittest.SkipTest("Private source directions are not installed")
        cls.manifest = json.loads(path.read_text())
        cls.catalog = json.loads((ROOT / "generated/catalog.json").read_text())
        cls.exams = [json.loads((ROOT / f"generated/exams/{row['id']}.json").read_text())
                     for row in cls.catalog["exams"] + cls.catalog["supplementalExams"]]

    def test_every_pack_paid_audio_module_has_its_bound_original_instructions(self):
        records = {(r["examId"], r["moduleId"]): r for r in self.manifest["modules"]}
        self.assertEqual(len(records), 33)
        for exam in self.exams:
            if exam["id"] not in EXAMS:
                continue
            self.assertIn("scripts/verified_pack_directions.json", exam["verificationInputs"]["curationSha256ByPath"])
            for section in exam["sections"]:
                if section["id"] not in {"listening", "speaking"}:
                    continue
                for module in section["modules"]:
                    record = records[(exam["id"], module["id"])]
                    self.assertEqual(module["instructions"], record["instructions"])
                    self.assertEqual(module["instructionSources"], record["sourcePages"])
                    self.assertNotIn("Answer Key", module["instructions"])
                    self.assertNotIn("BR:", module["instructions"])

    def test_attachment_is_idempotent_and_experience_is_untouched(self):
        exams = deepcopy(self.exams)
        result = attach(exams, self.catalog["materials"], ROOT)
        self.assertEqual(result["modulesAttached"], 33)
        self.assertEqual(result["questionGroupsAttached"], 13)
        self.assertEqual(exams, self.exams)
        rejected = {r["segmentId"] for r in self.manifest["excludedCandidates"]}
        self.assertIn("paid-1-mat-34301a419593-directions-1-directions", rejected)
        self.assertIn("paid-1-mat-8b523db1c6f4-directions-directions", rejected)
        self.assertFalse(rejected.intersection(self.manifest["clips"]))

    def test_pack_one_complete_directions_precede_the_first_response_clock(self):
        exam = next(e for e in self.exams if e["id"] == "pack-1")
        session = engine.new_session(exam, {"mode": "strict", "scope": "speaking"}, 1000000)
        repeat = session["plan"][0]
        interview = session["plan"][1]
        self.assertIn("art museum", repeat["instructions"])
        self.assertIn("outdoor activities", interview["instructions"])
        self.assertEqual(len(engine.media_sequence(repeat["questions"][0])), 4)
        self.assertEqual(len(engine.media_sequence(interview["questions"][0])), 3)
        now = 1000000
        engine.begin(session, now)
        for index in range(4):
            self.assertEqual(session["phase"], "audio")
            self.assertIsNone(session["deadline"])
            now = session["audioEarliestEnd"]
            engine.apply_event(session, {"action": "audio-ended", "mediaIndex": index,
                                         "questionId": engine.question(session)["id"]}, now)
        self.assertEqual(session["phase"], "response")
        self.assertEqual(session["deadline"] - now, 8000)

    def test_missing_directions_manifest_closes_only_affected_audio_scopes(self):
        exams = deepcopy(self.exams)
        with patch("scripts.attach_pack_directions.MANIFEST", "scripts/nonexistent-directions-test.json"):
            result = attach(exams, self.catalog["materials"], ROOT)
        self.assertEqual(result["status"], "manifest-not-installed")
        for before, after in zip(self.exams, exams):
            if after["id"] in EXAMS:
                self.assertFalse(after["strictEligible"])
                self.assertFalse(after["scopedEligibility"]["listening"])
                self.assertFalse(after["scopedEligibility"]["speaking"])
                self.assertEqual(after["scopedEligibility"].get("reading"), before["scopedEligibility"].get("reading"))
            else:
                self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
