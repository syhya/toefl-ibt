"""Upgrade only the explicitly selected example; keep old plans and media usable."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.catalog import Catalog
from backend.engine import ExamError
from backend.example_pack import install_example
from backend.integrity import SourceIntegrity
from backend.prepared_sources import LEGACY_PROFILE, LEGACY_PROVENANCE, PROFILE
from backend.presentation import content_digest
from backend.tests.test_api import action, begin, start
from backend.tests.test_example_pack import file_record, snapshot, write_json

BUNDLE = Path(__file__).resolve().parents[2] / 'examples/ets-practice-test-1'


@pytest.fixture
def legacy_example(tmp_path):
    bundle = tmp_path / 'legacy-bundle'
    shutil.copytree(BUNDLE, bundle, ignore=shutil.ignore_patterns('materials'))
    exam = json.loads((bundle / 'exam.json').read_text())
    interview = exam['sections'][-1]['modules'][-1]
    q = interview['questions'][0]
    original = q.pop('sourceVariant')['paperPrompt']
    removed_url = q.pop('audio')['url']
    q.update(id='student-1-s-interview-1', prompt=original, transcript=original,
             source=deepcopy(interview['questions'][1]['source']),
             referenceOnly=True, practiceMode='text-only-source-study',
             stemBlocks=[{'type':'instruction','text':original}])
    q['contentId'] = 'qcontent-' + content_digest(q)[:20]
    exam.update(bundledExample=LEGACY_PROFILE, strictEligible=False)
    exam.pop('sourceEdition')
    exam['scopedEligibility']['speaking'] = False
    inputs = exam['verificationInputs']
    inputs['assetSha256ByUrl'].pop(removed_url)
    inputs['structuredContentSha256ByQuestionId'] = {item['id']:content_digest(item)
        for s in exam['sections'] for m in s['modules'] for item in m['questions']}
    proof = json.loads((bundle / 'provenance.json').read_text())
    proof.pop('audioEdition')
    proof['contentSha256ByQuestionId'] = inputs['structuredContentSha256ByQuestionId']
    proof['runtimeAssetSha256ByUrl'] = inputs['assetSha256ByUrl']
    write_json(bundle / 'provenance.json', proof)
    inputs['textCorrectionsPath'] = 'generated/assets/ets-practice-test-1/text-corrections.json'
    inputs['curationSha256ByPath'] = {
        LEGACY_PROVENANCE:hashlib.sha256((bundle / 'provenance.json').read_bytes()).hexdigest(),
        inputs['textCorrectionsPath']:hashlib.sha256((bundle / 'text-corrections.json').read_bytes()).hexdigest()}
    write_json(bundle / 'exam.json', exam)
    catalog = json.loads((bundle / 'catalog.json').read_text())
    catalog.update(bundledExample=LEGACY_PROFILE, exams=[{k:v for k,v in exam.items() if k != 'sections'}])
    write_json(bundle / 'catalog.json', catalog)
    manifest = json.loads((bundle / 'manifest.json').read_text())
    files = []
    for record in manifest['files']:
        if record['path'] == removed_url.lstrip('/'): continue
        destination = record.get('installPath')
        if record['path'] == 'provenance.json': destination = LEGACY_PROVENANCE
        if record['path'] == 'text-corrections.json': destination = inputs['textCorrectionsPath']
        files.append(file_record(bundle, record['path'], destination))
    manifest['files'] = files
    write_json(bundle / 'manifest.json', manifest)
    root = tmp_path / 'project'; root.mkdir()
    install_example(root, bundle)
    return root


def test_upgrade_preserves_old_source_study_and_audio_and_enables_new_interview(legacy_example):
    root = legacy_example
    clock = [1_000_000]
    app = create_app(root, clock=lambda:clock[0], testing=True)
    with TestClient(app) as client:
        env = {'root':root,'app':app,'client':client,'clock':clock}
        old_paper = begin(env, start(env, examId='student-1', scope='speaking', questionIds=['student-1-s-interview-1']))
        old_audio = begin(env, start(env, examId='student-1', scope='speaking', questionIds=['student-1-s-interview-2']))
        audio_url = old_audio['question']['audio']['url']
        original_bytes = client.get(audio_url).content
        with app.state.store.transaction() as db:
            old_rows = {s['id']: deepcopy(s) for s in app.state.store.all(db)}
        assert install_example(root, BUNDLE)['reused'] is True
        result = install_example(root, BUNDLE, upgrade=True)
        assert result['upgraded'] is True
        assert (root / LEGACY_PROVENANCE).exists()
        with app.state.store.transaction() as db:
            assert {s['id']:s for s in app.state.store.all(db)} == old_rows
        old = client.get(f"/api/sessions/{old_paper['id']}").json()
        assert old['stage']['timer'] == 'untimed' and old['deadline'] is None
        assert 'currently live' in old['question']['prompt']
        assert client.get(audio_url).content == original_bytes
        new = begin(env, start(env, examId='student-1', scope='speaking', taskType='interview'))
        assert new['question']['id'] == 'student-1-s-interview-1-audio'
        assert new['phase'] == 'audio' and new['deadline'] is None
        assert 'sourceVariant' not in new['question'] and 'transcript' not in new['question']
        assert client.get(new['question']['audio']['url']).status_code == 200
        clock[0] = new['audioEarliestEnd'] + 1
        recording = action(env, new, 'audio-ended').json()
        assert recording['phase'] == 'response' and recording['remainingSeconds'] == 45
        assert 'last time you visited' not in json.dumps(recording['question'])
        clock[0] = recording['deadline']
        next_q = client.get(f"/api/sessions/{new['id']}").json()
        assert next_q['question']['id'] == 'student-1-s-interview-2' and next_q['phase'] == 'audio'
        assert action(env, next_q, 'finish').status_code == 200
        reviewed = client.get(f"/api/sessions/{new['id']}/review").json()['sections'][0]['modules'][0]['questions'][0]
        assert 'last time you visited' in reviewed['transcript']
        assert 'currently live' in reviewed['sourceVariant']['paperPrompt']
        assert 'explanationSource' not in reviewed
    assert install_example(root, BUNDLE, upgrade=True)['reused'] is True
    assert Catalog(root).exams['student-1']['bundledExample'] == PROFILE
    assert Catalog(root).data['stats']['strictExamCount'] == 1


def test_failed_upgrade_restores_metadata_and_removes_only_new_files(legacy_example, monkeypatch):
    root = legacy_example
    before = snapshot(root)
    original = SourceIntegrity.check_exam
    def reject_new(integrity, exam):
        if integrity.root == root and exam.get('bundledExample') == PROFILE:
            return {'status':'failed','issues':[{'code':'explicit-post-publish-test'}]}
        return original(integrity, exam)
    monkeypatch.setattr(SourceIntegrity, 'check_exam', reject_new)
    with pytest.raises(ExamError, match='Installed example failed'):
        install_example(root, BUNDLE, upgrade=True)
    assert snapshot(root) == before
