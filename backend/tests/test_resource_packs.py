"""Public-pack onboarding uses temporary roots, never the private material collection."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import wave

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.app import create_app
from backend.catalog import Catalog
from backend.engine import ExamError, grade, media_sequence
from backend.integrity import SourceIntegrity
from backend.packs import import_pack
from backend.tests.test_api import action, begin, env, start

PROJECT = Path(__file__).resolve().parents[2]


def pack():
    """Small original fixture; no imported commercial question is needed."""
    return {'schemaVersion': 1, 'id': 'my-pack', 'title': 'A local authored pack', 'sections': [
        {'id': 'reading', 'questions': [{'id': 'notice', 'type': 'choice', 'prompt': 'When does it open?',
          'passage': 'The library opens at nine.', 'choices': [{'id': 'A', 'text': 'Nine'}, {'id': 'B', 'text': 'Ten'}], 'answer': 'A'}]}
    ]}


@pytest.fixture
def clean(tmp_path):
    root = tmp_path / 'project'
    root.mkdir()
    app = create_app(root, clock=lambda: 1_000_000, testing=True)
    with TestClient(app) as client:
        yield {'root': root, 'app': app, 'client': client}


def imported(clean, manifest=None):
    response = clean['client'].post('/api/resource-packs', json=manifest or pack())
    assert response.status_code == 200, response.text
    return response.json()


def checked_action(clean, current, name, **extra):
    response = action(clean, current, name, **extra)
    assert response.status_code == 200, response.text
    return response.json()


def test_custom_portable_pack_walkthrough_saves_and_grades_all_four_screens(clean):
    root, client = clean['root'], clean['client']
    assert client.get('/api/catalog').json()['exams'] == []
    manifest = json.loads((PROJECT / 'tests/fixtures/portable-pack.json').read_text())
    response = client.post('/api/resource-packs', json=manifest)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['questions'] == 4
    public = client.get('/api/catalog').json()
    assert len(public['exams']) == 1
    entry = public['exams'][0]
    assert entry['structuredReady'] is True
    assert entry['strictEligible'] is False
    assert entry['interactiveQuestionCount'] == 5
    strict = client.post('/api/sessions', json={'examId': result['id'], 'mode': 'strict'})
    assert strict.status_code == 422
    current = start(clean, examId=result['id'], mode='practice', scope='all')
    answers = {
        'library-notice': 'B', 'garden-words': {'b1': 'ter', 'b2': 'bors'},
        'volunteer-email': 'Dear coordinator, I can volunteer on Saturday.',
        'community-discussion': 'I support the library because it offers year-round activities.',
    }
    visited = []
    while current['status'] == 'active':
        assert current['deadline'] is None
        if current['phase'] == 'directions':
            current = checked_action(clean, current, 'begin')
            continue
        assert current['stage']['timer'] == 'untimed'
        qid = current['question']['id']
        short_id = qid.removeprefix('user-welcome-demo-')
        visited.append(short_id)
        current = checked_action(clean, current, 'answer', answer=answers[short_id])
        assert current['answer'] == answers[short_id]
        current = checked_action(clean, current, 'next')
    assert visited == list(answers)
    assert current['status'] == 'completed'
    review = client.get(f"/api/sessions/{current['id']}/review").json()
    questions = [q for section in review['sections'] for mod in section['modules'] for q in mod['questions']]
    assert len(questions) == 4
    assert questions[0]['grade'] == {'correct': 1, 'total': 1}
    assert questions[1]['grade'] == {'correct': 2, 'total': 2}
    assert questions[2]['grade'] is None and questions[3]['grade'] is None
    for q in questions:
        assert review['answers'][q['id']] == answers[q['id'].removeprefix('user-welcome-demo-')]
    exam = clean['app'].state.catalog.exams[result['id']]
    assert clean['app'].state.source_integrity.check_exam(exam)['status'] == 'passed'


def test_bundled_demo_installs_official_sample_and_preserves_its_scoped_timing(clean):
    root, client = clean['root'], clean['client']
    shutil.copytree(PROJECT / 'examples/ets-practice-test-1', root / 'examples/ets-practice-test-1')
    response = client.post('/api/resource-packs/demo', json={'path': '/ignored/client/path'})
    assert response.status_code == 200, response.text
    assert response.json()['id'] == 'student-1'
    assert response.json()['questions'] == 97
    assert response.json()['screens'] == 79
    entries = client.get('/api/catalog').json()['exams']
    assert [entry['id'] for entry in entries] == ['student-1']
    entry = entries[0]
    assert entry['strictEligible'] is False
    assert entry['scopedEligibility'] == {'reading': True, 'listening': True, 'writing': True, 'speaking': False}
    assert entry['runtimeVerification']['status'] == 'passed'
    assert entry['interactiveQuestionCount'] == 97
    assert entry['interactiveScreenCount'] == 79
    assert [(section['id'], section['questionCount']) for section in entry['sections']] == [
        ('reading', 22), ('listening', 34), ('writing', 12), ('speaking', 11)]
    exam = clean['app'].state.catalog.exams['student-1']
    questions = {q['id']: q for section in exam['sections'] for module in section['modules'] for q in module['questions']}
    for question in questions.values():
        if question['id'].startswith(('student-1-l', 'student-1-s')) and question['id'] != 'student-1-s-interview-1':
            assert question['audio']['verified'] is True
            url = question['audio']['url']
            catalog = clean['app'].state.catalog
            assert catalog.path_for(catalog.register(url)).is_file()
    # A known paper/audio version conflict must not be promoted into a strict exam.
    assert not questions['student-1-s-interview-1'].get('audio')
    for scope in ['all', 'speaking']:
        rejected = client.post('/api/sessions', json={'examId': 'student-1', 'mode': 'strict', 'scope': scope})
        assert rejected.status_code == 422, rejected.text
    for scope in ['listening', 'writing']:
        scoped = start(clean, examId='student-1', mode='strict', scope=scope)
        assert scoped['stage']['section'] == scope
        checked_action(clean, scoped, 'finish')
    current = start(clean, examId='student-1', mode='strict', scope='reading')
    assert current['phase'] == 'directions'
    assert current['stage']['seconds'] == 690
    assert current['deadline'] is None
    current = begin(clean, current)
    assert current['phase'] == 'response'
    assert current['question']['id'] == 'student-1-r1-cloze'
    assert current['remainingSeconds'] == 690
    assert current['deadline'] == current['serverNow'] + 690_000
    current = checked_action(clean, current, 'finish')
    saved = client.get('/api/sessions').json()['sessions']
    assert any(item['id'] == current['id'] for item in saved)
    repeated = client.post('/api/resource-packs/demo')
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()['reused'] is True
    assert client.get('/api/sessions').json()['sessions'] == saved
    assert [item['id'] for item in client.get('/api/catalog').json()['exams']] == ['student-1']


def test_frozen_alternate_listening_directions_path_rejects_changed_hash(env):
    # This compatibility behavior is independent of the default example; keep
    # testing it without bundling an unrelated Pack 1 instruction recording.
    from tests.security.test_direction_projection import install_directions, PDF_INSTRUCTION

    root, client = env['root'], env['client']
    original = install_directions(env)
    relative = 'generated/assets/example-directions/pack-directions.json'
    path = root / relative
    path.parent.mkdir(parents=True)
    original.rename(path)
    exam_path = root / 'generated/exams/exam.json'
    exam = json.loads(exam_path.read_text())
    inputs = exam['verificationInputs']
    inputs['packDirectionsPath'] = relative
    inputs['curationSha256ByPath'][relative] = inputs['curationSha256ByPath'].pop('scripts/verified_pack_directions.json')
    exam_path.write_text(json.dumps(exam))
    catalog_path = root / 'generated/catalog.json'
    catalog_path.write_text(catalog_path.read_text() + ' ')
    current = start(env, mode='strict', scope='listening')
    store = env['app'].state.store
    with store.transaction() as db:
        frozen = deepcopy(store.get(db, current['id']))
    snapshot = frozen['verificationSnapshot']
    assert snapshot['packDirectionsPath'] == relative
    original_manifest = path.read_bytes()
    assert hashlib.sha256(original_manifest).hexdigest() == snapshot['curationSha256ByPath'][relative]
    first = media_sequence(frozen['plan'][0]['questions'][0])[0]
    assert first['kind'] == 'directions'
    current = begin(env, current)
    assert current['phase'] == 'audio'
    assert current['question']['audio']['instructions'] == PDF_INSTRUCTION
    assert client.get(current['question']['audio']['url']).status_code == 200
    path.write_bytes(original_manifest + b' ')
    rejected = client.get(f"/api/sessions/{current['id']}")
    assert rejected.status_code == 200, rejected.text
    assert 'instructions' not in rejected.json()['question']['audio']
    path.write_bytes(original_manifest)
    restored = client.get(f"/api/sessions/{current['id']}").json()
    assert restored['question']['audio']['instructions'] == PDF_INSTRUCTION
    assert restored['question']['audio']['url'] == current['question']['audio']['url']
    assert restored['deadline'] == current['deadline']


def media_pack(folder):
    folder.mkdir(parents=True)
    Image.new('RGB', (64, 64), 'navy').save(folder / 'map image.png')
    (folder / 'source.PDF').write_bytes(b'%PDF-1.4\nOriginal source fixture.\n%%EOF')
    with wave.open(str(folder / 'prompt.wav'), 'wb') as audio:
        audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(8000)
        audio.writeframes(b'\x00\x00' * 8000)
    manifest = pack()
    manifest['sections'][0]['questions'][0].update(
        assets=[{'file': 'map image.png', 'alt': 'A navy campus map with the library marked'}],
        source={'file': 'source.PDF', 'page': 1},
    )
    manifest['sections'].extend([
        {'id': 'listening', 'questions': [{'id': 'listen', 'type': 'choice', 'prompt': 'Choose a reply.',
         'choices': [{'id': 'A', 'text': 'Thanks.'}, {'id': 'B', 'text': 'Tomorrow.'}], 'answer': 'A', 'audio': {'file': 'prompt.wav'}}]},
        {'id': 'speaking', 'questions': [{'id': 'repeat', 'type': 'listen_repeat', 'prompt': 'Repeat the sentence.', 'audio': {'file': 'prompt.wav'}}]},
    ])
    return manifest


def test_cli_resolves_relative_media_and_retains_prior_revision_files(clean, tmp_path, monkeypatch):
    folder = tmp_path / 'portable'
    manifest = media_pack(folder)
    path = folder / 'pack.json'
    path.write_text(json.dumps(manifest))
    spec = importlib.util.spec_from_file_location('isolated_import_pack', PROJECT / 'scripts/import_pack.py')
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(cli, 'ROOT', clean['root'])
    monkeypatch.setattr(sys, 'argv', ['import_pack.py', str(path)])
    cli.main()
    catalog = clean['app'].state.catalog
    catalog.refresh()
    exam = catalog.exams['user-my-pack']
    original = exam['sections'][0]['modules'][0]['questions'][0]
    original_url = original['assets'][0]['url']
    assert 'map%20image.png' in original_url
    mapped = catalog.path_for(catalog.register(original_url))
    assert mapped.read_bytes() == (folder / 'map image.png').read_bytes()
    assert original['source']['page'] == 1
    source = next(m for m in catalog.data['materials'] if m['id'] == original['source']['materialId'])
    assert source['kind'] == 'pdf'
    assert source['sha256'] == hashlib.sha256((folder / 'source.PDF').read_bytes()).hexdigest()
    assert SourceIntegrity(clean['root'], catalog).check_exam(exam)['status'] == 'passed'
    listening = exam['sections'][1]['modules'][0]['questions'][0]['audio']
    assert listening['mediaType'] == 'audio' and listening['durationSeconds'] == pytest.approx(1)
    current = begin(clean, start(clean, examId='user-my-pack', mode='practice', scope='reading'))
    frozen_asset = current['question']['assets'][0]['url']
    assert clean['client'].get(frozen_asset).content == mapped.read_bytes()
    old_bytes = mapped.read_bytes()
    assert import_pack(clean['root'], manifest, folder)['unchanged'] is True
    Image.new('RGB', (64, 64), 'green').save(folder / 'map image.png')
    with pytest.raises(ExamError) as conflict:
        import_pack(clean['root'], manifest, folder)
    assert conflict.value.status == 409
    monkeypatch.setattr(sys, 'argv', ['import_pack.py', str(path), '--replace'])
    cli.main()
    catalog.refresh()
    changed = catalog.exams['user-my-pack']['sections'][0]['modules'][0]['questions'][0]['assets'][0]['url']
    assert changed != original_url
    assert mapped.read_bytes() == old_bytes
    assert clean['client'].get(frozen_asset).content == old_bytes
    assert len(list((clean['root'] / 'data/user-packs/my-pack').iterdir())) == 2
    # Restarting the API also recovers the frozen old media URL from session state.
    with TestClient(create_app(clean['root'], testing=True)) as restarted:
        assert restarted.get(frozen_asset).content == old_bytes


def test_registry_merge_keeps_existing_collection_and_is_idempotent(env):
    catalog_path = env['root'] / 'generated/catalog.json'
    collection = catalog_path.read_bytes()
    result = imported(env)
    assert result['unchanged'] is False
    imported_again = imported(env)
    assert imported_again['unchanged'] is True
    assert catalog_path.read_bytes() == collection
    entries = env['client'].get('/api/catalog').json()['exams']
    assert sorted(e['id'] for e in entries) == ['adaptive', 'exam', 'user-my-pack']


def test_browser_import_waits_until_strict_session_ends(env):
    current = begin(env, start(env, mode='strict', scope='reading'))
    for endpoint, payload in [('/api/resource-packs', pack()), ('/api/resource-packs/demo', None)]:
        response = env['client'].post(endpoint, json=payload) if payload else env['client'].post(endpoint)
        assert response.status_code == 409
        assert 'Finish the active strict session' in response.json()['error']
    assert not (env['root'] / 'generated/pack-catalogs').exists()
    checked_action(env, current, 'finish')
    assert imported(env)['id'] == 'user-my-pack'


@pytest.mark.parametrize('payload', ['{', '[]', '{"schemaVersion":NaN}', '{"schemaVersion":Infinity}'])
def test_invalid_json_is_rejected_without_catalog_writes(clean, payload):
    response = clean['client'].post('/api/resource-packs', content=payload, headers={'content-type': 'application/json'})
    assert response.status_code == 422
    assert not (clean['root'] / 'generated').exists()


@pytest.mark.parametrize('mutate', [
    lambda p: p.update(schemaVersion=True),
    lambda p: p.update(id='../escape'),
    lambda p: p.update(id='UPPER'),
    lambda p: p.update(id='x' * 49),
    lambda p: p['sections'][0].update(id=[]),
    lambda p: p['sections'][0]['questions'][0].update(type=[]),
    lambda p: p['sections'][0]['questions'][0].update(id='unsafe/id'),
    lambda p: p['sections'][0]['questions'][0].update(assets=None),
    lambda p: p['sections'][0]['questions'][0].update(taskType={}),
    lambda p: p['sections'][0]['questions'][0].update(source=[]),
    lambda p: p['sections'][0]['questions'][0].update(choices=[{'id': '', 'text': 'A'}, {'id': 'B', 'text': 'B'}]),
    lambda p: p['sections'][0]['questions'][0].update(answer='unknown'),
    lambda p: p['sections'][0]['questions'][0].update(recommendedWords='100'),
    lambda p: p['sections'][0]['questions'][0].update(stemBlocks=[{'type': []}]),
    lambda p: p['sections'][0]['questions'][0].update(stemBlocks=[{'type': 'list', 'marker': [], 'items': ['one']}]),
    lambda p: p['sections'][0]['questions'][0].update(unknown='field'),
    lambda p: p['sections'][0]['questions'].append(deepcopy(p['sections'][0]['questions'][0])),
])
def test_invalid_question_shapes_return_422_without_partial_import(clean, mutate):
    manifest = pack(); mutate(manifest)
    response = clean['client'].post('/api/resource-packs', json=manifest)
    assert response.status_code == 422, response.text
    assert not (clean['root'] / 'generated').exists()
    assert not (clean['root'] / 'data').exists()


@pytest.mark.parametrize('relative', ['../outside.png', '/tmp/outside.png', 'https://example.com/image.png', 'folder\\image.png', '.hidden.png', 'folder/./image.png', 'pack.json'])
def test_import_rejects_unsafe_file_paths(clean, tmp_path, relative):
    folder = tmp_path / 'media'; folder.mkdir()
    manifest = pack(); manifest['sections'][0]['questions'][0]['assets'] = [{'file': relative, 'alt': 'A library map'}]
    with pytest.raises(ExamError) as error:
        import_pack(clean['root'], manifest, folder)
    assert error.value.status == 422
    assert not (clean['root'] / 'generated').exists()


@pytest.mark.parametrize('intermediate', [False, True])
def test_import_rejects_source_symlinks_even_inside_the_pack(clean, tmp_path, intermediate):
    folder = tmp_path / 'media'; folder.mkdir()
    real = folder / 'real'; real.mkdir()
    Image.new('RGB', (32, 32), 'navy').save(real / 'image.png')
    if intermediate:
        (folder / 'linked').symlink_to(real, target_is_directory=True)
        name = 'linked/image.png'
    else:
        (folder / 'linked.png').symlink_to(real / 'image.png')
        name = 'linked.png'
    manifest = pack(); manifest['sections'][0]['questions'][0]['assets'] = [{'file': name, 'alt': 'The library entrance'}]
    with pytest.raises(ExamError) as error:
        import_pack(clean['root'], manifest, folder)
    assert error.value.status == 422


def test_import_rejects_destination_parent_symlink_before_copying_anything(clean, tmp_path):
    outside = tmp_path / 'outside'; outside.mkdir()
    (clean['root'] / 'generated').symlink_to(outside, target_is_directory=True)
    with pytest.raises(ExamError) as error:
        import_pack(clean['root'], pack())
    assert error.value.status == 422
    assert list(outside.iterdir()) == []
    assert not (clean['root'] / 'data').exists()


def test_browser_cannot_import_media_references_or_remote_urls(clean):
    for audio in [{'file': 'prompt.wav'}, {'url': 'https://example.com/prompt.mp3'}]:
        manifest = pack(); manifest['sections'][0]['questions'][0]['audio'] = audio
        response = clean['client'].post('/api/resource-packs', json=manifest)
        assert response.status_code == 422


def test_sentence_slot_validation_matches_grading_and_cloze_metadata_is_typed(clean):
    manifest = {'schemaVersion': 1, 'id': 'sentence', 'title': 'Sentence practice', 'sections': [{'id': 'writing', 'questions': [{
        'id': 'build', 'type': 'build_sentence', 'prompt': 'Make a sentence.', 'tokens': ['the', 'library'],
        'slots': [{'fixed': 'Visit'}, {'id': 'first'}, {'id': 'second'}, {'fixed': '.'}], 'answer': 'Visit the library.'}]}]}
    assert imported(clean, manifest)['questions'] == 1
    q = clean['app'].state.catalog.exams['user-sentence']['sections'][0]['modules'][0]['questions'][0]
    assert grade(q, {'tokenOrder': ['0', '1']}) == {'correct': 1, 'total': 1}
    for slots in [[[]], [{'id': []}], [{'fixed': ''}], [{'id': 'one'}, {'id': 'one'}], [{'id': 'one'}, {'id': 'two'}, {'id': 'three'}]]:
        bad = deepcopy(manifest); bad['id'] = 'bad-slots'; bad['sections'][0]['questions'][0]['slots'] = slots
        response = clean['client'].post('/api/resource-packs', json=bad)
        assert response.status_code == 422
    cloze = pack(); cloze['sections'][0]['questions'] = [{'id': 'blank', 'type': 'cloze', 'prompt': 'Fill letters.', 'passageTemplate': 'wa{{x}}', 'blanks': [{'id': 'x', 'length': 3, 'answer': 'ter', 'prefix': []}]}]
    assert clean['client'].post('/api/resource-packs', json=cloze).status_code == 422
