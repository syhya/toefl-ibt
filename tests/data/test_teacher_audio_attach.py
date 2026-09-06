"""Fail-closed media provenance checks using existing private source fixtures."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts import attach_teacher_audio as teacher_audio

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / 'scripts/verified_teacher_audio.json'


@unittest.skipUnless(MANIFEST.is_file(), 'Private teacher audio audit is not installed')
class TeacherAudioProvenance(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.manifest = json.loads(MANIFEST.read_text())
        (self.root / 'scripts').mkdir()
        (self.root / 'scripts/verified_teacher_audio.json').write_text(MANIFEST.read_text())
        self.materials = []
        self.exams = []
        for archive in self.manifest['archives']:
            self.copy_source(archive['sourcePdfPath'])
            self.exams.append(json.loads((ROOT / 'generated/exams' / f"{archive['examId']}.json").read_text()))
            for index, record in enumerate(archive['audioFiles']):
                self.copy_source(record['dataPath'])
                self.materials.append({'id': f"{archive['examId']}-audio-{index}",
                                       'name': Path(record['dataPath']).name,
                                       'path': record['dataPath'], 'sha256': record['sha256'],
                                       'url': '/materials/' + record['dataPath'], 'kind': 'audio'})

    def copy_source(self, relative):
        target = self.root / 'data' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'data' / relative, target)

    def test_attachment_preserves_question_text_and_does_not_open_strict_mode(self):
        before = copy.deepcopy(self.exams)
        result = teacher_audio.attach(self.exams, self.materials, self.root)
        self.assertEqual(result['attachedQuestionCount'], 90)
        self.assertFalse(result['strictEligibilityChanged'])
        for old, new in zip(before, self.exams):
            self.assertEqual(old['strictEligible'], new['strictEligible'])
            for old_s, new_s in zip(old['sections'], new['sections']):
                for old_m, new_m in zip(old_s['modules'], new_s['modules']):
                    for old_q, new_q in zip(old_m['questions'], new_m['questions']):
                        for key in ['prompt', 'transcript', 'stemBlocks', 'referenceOnly', 'answer']:
                            self.assertEqual(old_q.get(key), new_q.get(key))

    def test_changed_audio_fails_before_any_question_is_mutated(self):
        before = copy.deepcopy(self.exams)
        changed = self.root / 'data' / self.manifest['archives'][-1]['audioFiles'][-1]['dataPath']
        changed.write_bytes(b'changed fixture bytes')
        with self.assertRaisesRegex(ValueError, 'missing or changed'):
            teacher_audio.attach(self.exams, self.materials, self.root)
        self.assertEqual(before, self.exams)

    def test_changed_source_transcript_fails_before_any_question_is_mutated(self):
        qid = self.manifest['archives'][-1]['audioFiles'][0]['questionIds'][0]
        question = next(q for exam in self.exams for section in exam['sections']
                        for module in section['modules'] for q in module['questions'] if q['id'] == qid)
        question['transcript'] += '\n'
        before = copy.deepcopy(self.exams)
        with self.assertRaisesRegex(ValueError, 'transcript changed'):
            teacher_audio.attach(self.exams, self.materials, self.root)
        self.assertEqual(before, self.exams)

    def test_installed_originals_verify_without_the_download_cache(self):
        result = teacher_audio.verify(self.root, cache_dir=self.root / 'absent-download-cache')
        self.assertEqual(result['alreadyInstalledCount'], 72)
        self.assertEqual(result['mappedQuestionCount'], 90)


if __name__ == '__main__':
    unittest.main()
