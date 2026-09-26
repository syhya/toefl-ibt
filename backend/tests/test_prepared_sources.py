"""The small example must work offline without weakening other source gates."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.catalog import Catalog
from backend.example_pack import install_example
from backend.integrity import SourceIntegrity
from backend.prepared_sources import PROVENANCE
from backend.tests.test_api import action, begin, start

BUNDLE = Path(__file__).resolve().parents[2] / 'examples/ets-practice-test-1'


@pytest.fixture
def prepared(tmp_path):
    root = tmp_path / 'project'; root.mkdir()
    bundle = tmp_path / 'bundle'
    shutil.copytree(BUNDLE, bundle, ignore=shutil.ignore_patterns('materials'))
    assert not (bundle / 'materials').exists()
    install_example(root, bundle)
    assert not (root / 'data').exists()
    catalog = Catalog(root)
    return root, catalog, catalog.exams['student-1']


def check(prepared):
    root, catalog, exam = prepared
    return SourceIntegrity(root, catalog).check_exam(exam)


def test_prepared_assets_pass_but_do_not_claim_originals_were_reverified(prepared):
    report = check(prepared)
    assert report == {'status':'passed', 'requiresReimport':False, 'issues':[],
        'mode':'prepared-assets', 'originalSourcesVerified':False, 'optionalOriginalsMissing':13}
    materials = prepared[1].public()['materials']
    assert len(materials) == 13
    assert all(m['available'] is False and m['url'] is None for m in materials)


@pytest.mark.parametrize('mutation', ['private-exam', 'remove-proof-binding', 'alter-proof',
    'rewrite-proof-source', 'rewrite-proof-assets', 'missing-media', 'changed-media', 'wrong-original'])
def test_optional_sources_never_hide_missing_evidence_or_corrupt_assets(prepared, mutation):
    root, catalog, exam = prepared
    if mutation == 'private-exam':
        exam.pop('bundledExample')
    elif mutation == 'remove-proof-binding':
        exam['verificationInputs']['curationSha256ByPath'].pop(PROVENANCE)
    elif mutation == 'alter-proof':
        (root / PROVENANCE).write_text('{}')
    elif mutation.startswith('rewrite-proof-'):
        path = root / PROVENANCE; proof = json.loads(path.read_text())
        if mutation == 'rewrite-proof-source':
            next(iter(proof['originalSources'].values()))['sha256'] = '0' * 64
        else:
            proof['runtimeAssetSha256ByUrl'] = {}
        path.write_text(json.dumps(proof))
        exam['verificationInputs']['curationSha256ByPath'][PROVENANCE] = hashlib.sha256(path.read_bytes()).hexdigest()
    elif mutation in ['missing-media', 'changed-media']:
        q = exam['sections'][1]['modules'][0]['questions'][0]
        path = catalog.path_for(catalog.register(q['audio']['url']))
        if mutation == 'missing-media': path.unlink()
        else: path.write_bytes(b'CORRUPTED AUDIO')
    else:
        item = catalog.data['materials'][0]
        path = root / 'data' / item['path'];path.parent.mkdir(parents=True)
        path.write_bytes(b'WRONG ORIGINAL')
    assert check(prepared)['status'] == 'invalid'


def test_practice_review_and_audio_remain_available_without_original_links(prepared):
    root, catalog, exam = prepared
    clock = [1_000_000]
    app = create_app(root, clock=lambda:clock[0], testing=True)
    with TestClient(app) as client:
        env = {'root':root, 'app':app, 'client':client, 'clock':clock}
        current = begin(env, start(env, examId='student-1', mode='practice', scope='reading',
                                   questionIds=['student-1-r1-cloze']))
        assert current['integrity']['sourcesVerified'] is False
        assert current['integrity']['preparedAssetsVerified'] is True
        assert current['sourceVersionMatches'] is True
        current = action(env, current, 'answer', answer={'b1':'ght'}).json()
        current = action(env, current, 'next').json()
        review = client.get(f"/api/sessions/{current['id']}/review").json()
        q = review['sections'][0]['modules'][0]['questions'][0]
        assert review['answers'][q['id']]['b1'] == 'ght'
        assert q['explanation'] and 'url' not in q['source']
        assert 'url' not in q['explanationSource']
        # Every prepared audio/visual is present, and source omission is not a
        # playback fallback to the mismatched or unsplit original recordings.
        for section in exam['sections']:
            for module in section['modules']:
                for original in module['questions']:
                    if original.get('audio'):
                        assert catalog.path_for(catalog.register(original['audio']['url'])).is_file()
        listening = begin(env, start(env, examId='student-1', mode='practice', scope='listening',
                                    questionIds=['student-1-l1-1']))
        assert listening['phase'] == 'audio'
        audio = client.get(listening['question']['audio']['url'])
        assert audio.status_code == 200 and audio.content.startswith(b'RIFF')
        finished = action(env, listening, 'finish')
        assert finished.status_code == 200
        before = deepcopy(client.get('/api/sessions').json())
        assert install_example(root, BUNDLE)['reused'] is True
        assert client.get('/api/sessions').json() == before


def test_entire_lightweight_exam_can_be_answered_recorded_and_reviewed(prepared):
    """Protocol QA with an explicit test clock/synthetic WAV, not a real exam."""
    import io
    import wave
    root, catalog, exam = prepared
    clock = [1_000_000]
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as audio:
        audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(8000)
        audio.writeframes(b'\x00\x00' * 8000)
    synthetic_voice = buffer.getvalue()
    original = {q['id']:q for s in exam['sections'] for m in s['modules'] for q in m['questions']}
    app = create_app(root, clock=lambda:clock[0], testing=True)
    with TestClient(app) as client:
        env = {'root':root,'app':app,'client':client,'clock':clock}
        current = start(env, examId='student-1', mode='practice', scope='all')
        visited = []; takes = []
        def event(name, **extra):
            response = action(env, current, name, **extra)
            assert response.status_code == 200, (name, current.get('question', {}).get('id'), response.json().get('error'))
            return response.json()
        for _ in range(300):
            if current['status'] != 'active': break
            if current['phase'] == 'directions':
                current = event('begin'); continue
            if current['phase'] == 'audio':
                media = current['question']['audio']
                assert client.get(media['url']).status_code == 200
                clock[0] = max(clock[0], current['audioEarliestEnd']) + 1
                current = event('audio-ended', mediaIndex=current['mediaIndex']); continue
            assert current['phase'] == 'response'
            q = original[current['question']['id']]; visited.append(q['id'])
            for media in current['question'].get('practiceMediaSequence', []):
                assert client.get(media['url']).status_code == 200
            if current['stage']['section'] == 'speaking':
                take = 'qa-' + q['id']; takes.append(take)
                upload = client.post(f"/api/sessions/{current['id']}/recordings/{q['id']}",
                    params={'takeId':take,'index':0,'segmentId':take+'-0'}, content=synthetic_voice,
                    headers={'Content-Type':'audio/wav'})
                assert upload.status_code == 200, upload.text
                final = client.post(f"/api/sessions/{current['id']}/recordings/takes/{take}/finalize",
                    json={'questionId':q['id'],'segmentCount':1,'endedReason':'stopped','mimeType':'audio/wav'})
                assert final.status_code == 200, final.text
            else:
                if q['type'] == 'cloze':
                    answer = {b['id']:b.get('missingLetters') or b.get('answer') for b in q['blanks']}
                elif q['type'] == 'build_sentence':
                    answer = {'tokenOrder':[str(index) for index in q['expectedTokenOrder']]} if q.get('expectedTokenOrder') else q['answer']
                else:
                    answer = q.get('answer') or 'This is an explicit local QA writing response, not a model answer.'
                current = event('answer', answer=answer)
            current = event('next')
        assert current['status'] == 'completed'
        assert visited == list(original) and len(visited) == 79 and len(takes) == 11
        assert current['integrity']['recordingsComplete'] is True
        review = client.get(f"/api/sessions/{current['id']}/review").json()
        qs = [q for s in review['sections'] for m in s['modules'] for q in m['questions']]
        assert len(qs) == 79 and len(review['answers']) == 68
        assert sum(q['grade']['total'] for q in qs if q.get('grade')) == 84
        assert sum(q['grade']['correct'] for q in qs if q.get('grade')) == 84
        assert all(not q.get('source',{}).get('url') for q in qs)
        for take in takes:
            playback = client.get(f"/api/sessions/{current['id']}/recordings/takes/{take}")
            assert playback.status_code == 200 and len(playback.content) > 100
        assert not (root / 'data').exists()
