from copy import deepcopy
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json
import hashlib
import subprocess
import uuid

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.engine import grade
from backend.media import ffmpeg_executable, probe_duration


def q(question_id, kind='choice', **extra):
    return {'id': question_id, 'contentId': f'fixture-content-{question_id}', 'type': kind, 'prompt': f'Question {question_id}', **extra}


@pytest.fixture
def env(tmp_path):
    for name in ['generated/exams', 'generated/assets', 'data', 'dist', 'scripts']:
        (tmp_path / name).mkdir(parents=True)
    (tmp_path / 'data/source.pdf').write_bytes(b'%PDF-source-with-SECRET_ANSWER')
    (tmp_path / 'data/shared.ogg').write_bytes(b'0123456789')
    (tmp_path / 'data/other.ogg').write_bytes(b'abcdefghij')
    (tmp_path / 'generated/assets/stem.jpg').write_bytes(b'FAKE_STEM_IMAGE')
    (tmp_path / 'dist/index.html').write_text('<title>React app</title>')
    (tmp_path / 'scripts/verified_fixture.json').write_text('{"engineeringFixture":true}')
    verification = {'curationSha256ByPath': {'scripts/verified_fixture.json': hashlib.sha256((tmp_path / 'scripts/verified_fixture.json').read_bytes()).hexdigest()},
                    'assetSha256ByUrl': {'/assets/stem.jpg': hashlib.sha256((tmp_path / 'generated/assets/stem.jpg').read_bytes()).hexdigest()}}
    media = {'url': '/materials/shared.ogg', 'durationSeconds': 2, 'groupId': 'shared', 'mediaType': 'audio'}
    reading = {'id': 'reading', 'modules': [
        {'id': 'r1', 'durationSeconds': 10, 'questions': [q('r1q1', answer='A', choices=[{'id': 'A', 'text': 'Option A'}, {'id': 'B', 'text': 'Option B'}], transcript='SECRET_TRANSCRIPT', explanation='SECRET_EXPLANATION', presentationSchema='structured-v1', structuredContentStatus='source-verified', stemBlocks=[{'type': 'question', 'text': 'Question r1q1'}, {'type': 'essential_visual', 'assetIndex': 0, 'alt': 'A verified fixture diagram with two labeled choices'}], assets=[{'url': '/assets/stem.jpg', 'role': 'essentialVisual', 'highResolution': True, 'alt': 'A verified fixture diagram with two labeled choices'}], source={'url': '/materials/source.pdf', 'page': 1}), q('r1q2', answer='SECRET_ANSWER')]},
        {'id': 'r2', 'durationSeconds': 8, 'questions': [q('r2q1', answer='B')]},
    ]}
    listening = {'id': 'listening', 'modules': [{'id': 'l1', 'questions': [q('l1q1', audio=media, answer='A'), q('l1q2', audio=media, answer='B'), q('l1q3', audio={**media, 'url': '/materials/other.ogg', 'groupId': 'other'}, answer='A')]}]}
    speaking = {'id': 'speaking', 'modules': [{'id': 's-repeat', 'questions': [q(f'repeat-{i}', 'listen_repeat', audio={**media, 'groupId': f'repeat-{i}'}) for i in range(7)]}, {'id': 's-interview', 'questions': [q(f'interview-{i}', 'interview', audio={**media, 'groupId': f'interview-{i}'}) for i in range(4)]}]}
    writing = {'id': 'writing', 'modules': [{'id': 'writing', 'questions': [q('build', 'build_sentence', tokens=['the', 'the', 'extra'], slots=[{'id': 'one'}, {'id': 'two'}, {'fixed': '.'}], answer='the the.'), q('email', 'email'), q('discussion', 'academic_discussion')]}]}
    exam = {'id': 'exam', 'title': 'Fixture exam', 'strictEligible': True, 'sections': [reading, listening, writing, speaking]}
    adaptive = {'id': 'adaptive', 'title': 'Branching', 'strictEligible': True, 'sections': [{'id': 'reading', 'modules': [
        {'id': 'common', 'route': 'common', 'durationSeconds': 10, 'questions': [q(f'router-{i}', answer='A') for i in range(10)]},
        {'id': 'lower', 'route': 'lower', 'durationSeconds': 8, 'questions': [q('lower-question', answer='L')]},
        {'id': 'upper', 'route': 'upper', 'durationSeconds': 8, 'questions': [q('upper-question', answer='U')]},
    ]}]}
    for item in [exam, adaptive]:
        item['verificationInputs'] = deepcopy(verification)
        (tmp_path / f"generated/exams/{item['id']}.json").write_text(json.dumps(item))
    catalog = {'stats': {'fileCount': 3}, 'materials': [{'id': 'source', 'name': 'source.pdf', 'kind': 'pdf', 'url': '/materials/source.pdf', 'path': 'source.pdf'}, {'id': 'audio', 'name': 'shared.ogg', 'kind': 'audio', 'url': '/materials/shared.ogg'}, {'id': 'other-audio', 'name': 'other.ogg', 'kind': 'audio', 'url': '/materials/other.ogg'}], 'exams': [{'id': 'exam'}, {'id': 'adaptive'}]}
    for material in catalog['materials']:
        source_file = tmp_path / 'data' / material['name']
        material['sha256'] = hashlib.sha256(source_file.read_bytes()).hexdigest()
        material['bytes'] = source_file.stat().st_size
    (tmp_path / 'generated/catalog.json').write_text(json.dumps(catalog))
    now = [1_000_000]
    app = create_app(tmp_path, clock=lambda: now[0], testing=True)
    with TestClient(app) as client:
        yield {'client': client, 'clock': now, 'root': tmp_path, 'app': app}


def start(env, **options):
    response = env['client'].post('/api/sessions', json={'examId': 'exam', 'mode': 'practice', **options})
    assert response.status_code == 200, response.text
    return response.json()


def action(env, a, name, **extra):
    body = {'action': name, 'requestId': str(uuid.uuid4()), **extra}
    if a.get('question'):
        body.setdefault('questionId', a['question']['id'])
    return env['client'].post(f"/api/sessions/{a['id']}/events", json=body)


def begin(env, a):
    response = action(env, a, 'begin')
    assert response.status_code == 200, response.text
    return response.json()


def test_active_api_has_only_current_legal_content_and_locks_originals(env):
    client = env['client']
    public = client.get('/api/catalog').json()
    assert 'path' not in public['materials'][0]
    assert client.get(public['materials'][0]['url']).status_code == 200
    assert 'sections' in client.get('/api/exams/exam').json()
    a = start(env, mode='strict', scope='reading')
    assert a['question'] is None
    a = begin(env, a)
    encoded = json.dumps(a)
    for secret in ['SECRET_ANSWER', 'SECRET_TRANSCRIPT', 'SECRET_EXPLANATION', '/materials/', 'r2q1']:
        assert secret not in encoded
    assert 'answer' not in a['question']
    assert 'source' not in a['question']
    assert client.get(public['materials'][0]['url']).status_code == 403
    assert client.get(f"/api/sessions/{a['id']}/review").status_code == 403
    assert client.get(f"/api/sessions/{a['id']}/feedback?questionId=r1q1").status_code == 403
    stem_url = a['question']['assets'][0]['url']
    assert client.get(stem_url).content == b'FAKE_STEM_IMAGE'
    assert client.get('/materials/source.pdf').status_code == 404
    assert client.get('/generated/exams/exam.json').status_code == 404
    assert action(env, a, 'pause').status_code == 409
    assert action(env, a, 'replay').status_code == 409
    done = action(env, a, 'finish').json()
    assert done['status'] == 'abandoned'
    review = client.get(f"/api/sessions/{a['id']}/review").json()
    assert 'SECRET_ANSWER' in json.dumps(review)


def test_server_deadline_survives_restart_and_rejects_boundary_and_stale_answers(env):
    a = begin(env, start(env, scope='reading'))
    old_qid = a['question']['id']
    response = action(env, a, 'answer', answer='A')
    assert response.status_code == 200
    env['clock'][0] += 10_000
    late = action(env, a, 'answer', answer='B')
    assert late.status_code == 409
    current = late.json()['session']
    assert current['question'] is None
    assert current['phase'] == 'directions' and current['deadline'] is None
    assert current['stage']['id'] == 'r2'
    env['clock'][0] += 60_000
    current = begin(env, current)
    assert current['question']['id'] == 'r2q1' and current['remainingSeconds'] == 8
    assert action(env, current, 'back').status_code == 409
    restarted = create_app(env['root'], clock=lambda: env['clock'][0], testing=True)
    with TestClient(restarted) as client:
        loaded = client.get(f"/api/sessions/{a['id']}").json()
        assert loaded['deadline'] == current['deadline']
        env['clock'][0] += 9000
        finished = client.get(f"/api/sessions/{a['id']}").json()
        assert finished['status'] == 'completed'
        review = client.get(f"/api/sessions/{a['id']}/review").json()
        assert review['answers'] == {old_qid: 'A'}
        assert review['session']['completedAt'] == current['deadline']


def test_duplicate_request_ids_cannot_double_advance_and_conflicting_reuse_is_rejected(env):
    a = begin(env, start(env, scope='reading'))
    payload = {'requestId': 'same-click', 'action': 'next', 'questionId': 'r1q1'}
    url = f"/api/sessions/{a['id']}/events"
    first = env['client'].post(url, json=payload).json()
    second = env['client'].post(url, json=payload).json()
    assert first['question']['id'] == second['question']['id'] == 'r1q2'
    assert first['revision'] == second['revision']
    assert env['client'].post(url, json={**payload, 'action': 'answer', 'answer': 'X'}).status_code == 409
    assert action(env, first, 'answer', answer='own answer', revision=1).status_code == 200


def test_shared_listening_track_only_once_and_asset_access_follows_current_question(env):
    a = begin(env, start(env, mode='strict', scope='listening'))
    assert a['phase'] == 'audio'
    assert a['deadline'] is None
    assert 'choices' not in a['question']
    url = a['question']['audio']['url']
    response = env['client'].get(url, headers={'Range': 'bytes=2-5'})
    assert response.status_code == 206 and response.content == b'2345'
    assert action(env, a, 'audio-ended').status_code == 409
    env['clock'][0] += 2000
    a = action(env, a, 'audio-ended').json()
    assert a['remainingSeconds'] == 20
    assert env['client'].get(url).status_code == 403
    a = action(env, a, 'answer', answer='A').json()
    a = action(env, a, 'next').json()
    assert a['question']['id'] == 'l1q2' and a['phase'] == 'response'
    assert action(env, a, 'back').status_code == 409
    env['clock'][0] += 20000
    a = env['client'].get(f"/api/sessions/{a['id']}").json()
    assert a['question']['id'] == 'l1q3' and a['phase'] == 'audio'
    assert a['question']['audio']['url'] != url


def test_practice_pause_freezes_only_remaining_time_and_feedback_is_visited_only(env):
    a = begin(env, start(env, scope='reading'))
    env['clock'][0] += 3000
    a = action(env, a, 'pause').json()
    assert a['phase'] == 'paused' and a['deadline'] is None
    env['clock'][0] += 60000
    a = action(env, a, 'resume').json()
    assert a['remainingSeconds'] == 7
    assert env['client'].get(f"/api/sessions/{a['id']}/feedback?questionId=r1q1").status_code == 200
    assert env['client'].get(f"/api/sessions/{a['id']}/feedback?questionId=r2q1").status_code == 403
    action(env, a, 'finish')
    score = env['client'].get(f"/api/sessions/{a['id']}/review").json()['score']
    assert score['wallSeconds'] == 63 and score['durationSeconds'] == 3


@pytest.mark.parametrize('section_id', ['reading', 'writing'])
@pytest.mark.parametrize('untimed', [False, True])
def test_jump_back_and_next_register_only_visited_questions_without_restarting_time(env, section_id, untimed):
    path = env['root'] / 'generated/exams/exam.json'
    exam = json.loads(path.read_text())
    items = [q(f'navigation-{index}', answer='A', choices=[{'id': 'A', 'text': 'Option A'}]) for index in range(4)]
    if section_id == 'writing':
        items = [q(f'navigation-{index}', 'build_sentence', answer='the', tokens=['the'], slots=[{'id': 'gap'}]) for index in range(4)]
    exam['sections'] = [{'id': section_id, 'modules': [{'id': 'navigation', 'durationSeconds': 10, 'questions': items}]}]
    if untimed:
        exam.update(supplemental=True, timingPolicy='untimed')
    path.write_text(json.dumps(exam))
    catalog_path = env['root'] / 'generated/catalog.json'
    catalog_path.write_text(catalog_path.read_text() + ' ')
    a = begin(env, start(env, scope=section_id))
    deadline = a['deadline']
    assert a['stage']['timer'] == ('untimed' if untimed else 'shared')

    def feedback(question_id):
        return env['client'].get(f"/api/sessions/{a['id']}/feedback", params={'questionId': question_id})

    assert feedback('navigation-0').status_code == 200
    assert feedback('navigation-1').status_code == 403
    assert feedback('navigation-2').status_code == 403
    assert action(env, a, 'jump', index=4).status_code == 409
    for name, extra, expected in [('jump', {'index': 2}, 2), ('back', {}, 1), ('next', {}, 2), ('next', {}, 3)]:
        env['clock'][0] += 1000
        response = action(env, a, name, **extra)
        assert response.status_code == 200, response.text
        a = response.json()
        assert a['question']['id'] == f'navigation-{expected}'
        assert a['phase'] == 'response' and a['deadline'] == deadline
        submitted = action(env, a, 'answer', answer={'tokenOrder': ['0']} if section_id == 'writing' else 'A')
        assert submitted.status_code == 200, submitted.text
        a = submitted.json()
        result = feedback(f'navigation-{expected}')
        assert result.status_code == 200, result.text
        assert result.json()['grade'] == {'correct': 1, 'total': 1}
        if expected != 3:
            assert feedback('navigation-3').status_code == 403
    assert feedback('not-in-this-exam').status_code == 403


@pytest.mark.parametrize('correct,expected', [(7, 'upper-question'), (6, 'lower-question')])
def test_local_seventy_percent_adaptive_route_requires_real_branches_and_scores_only_selected(env, correct, expected):
    a = start(env, examId='adaptive', scope='reading', routeMode='adaptive')
    a = begin(env, a)
    for index in range(10):
        a = action(env, a, 'answer', answer='A' if index < correct else 'B').json()
        a = action(env, a, 'next').json()
    assert a['phase'] == 'directions' and a['question'] is None and a['deadline'] is None
    a = begin(env, a)
    assert a['question']['id'] == expected
    action(env, a, 'finish')
    review = env['client'].get(f"/api/sessions/{a['id']}/review").json()
    assert review['score']['total'] == 11
    all_ids = [q['id'] for s in review['sections'] for m in s['modules'] for q in m['questions']]
    assert ('lower-question' in all_ids) != ('upper-question' in all_ids)
    assert env['client'].post('/api/sessions', json={'examId': 'exam', 'scope': 'reading', 'routeMode': 'adaptive'}).status_code == 422


def test_eleven_speaking_windows_have_no_preparation_and_interruptions_remain_visible(env):
    a = begin(env, start(env, scope='speaking', mode='strict'))
    for index, seconds in enumerate([8, 8, 10, 10, 10, 12, 12, 45, 45, 45, 45]):
        assert a['phase'] == 'audio'
        env['clock'][0] += 2000
        a = action(env, a, 'audio-ended').json()
        assert a['phase'] == 'response' and a['remainingSeconds'] == seconds
        if index == 0:
            a = action(env, a, 'interrupt', details={'kind': 'microphone-denied'}).json()
            assert a['integrity']['interrupted'] is True
        assert action(env, a, 'next').status_code == 409
        env['clock'][0] += seconds * 1000
        a = env['client'].get(f"/api/sessions/{a['id']}").json()
    assert a['status'] == 'completed'
    assert a['integrity']['interrupted']


def test_full_strict_flow_obeys_section_order_and_separate_time_windows(env):
    path = env['root'] / 'generated/exams/exam.json'
    exam = json.loads(path.read_text())
    exam['sections'].reverse()
    path.write_text(json.dumps(exam))
    catalog_path = env['root'] / 'generated/catalog.json'
    catalog_path.write_text(catalog_path.read_text() + ' ')

    a = begin(env, start(env, mode='strict'))
    assert a['stage']['section'] == 'reading'
    env['clock'][0] += 10_000
    a = env['client'].get(f"/api/sessions/{a['id']}").json()
    assert (a['stage']['id'], a['phase'], a['deadline']) == ('r2', 'directions', None)
    a = begin(env, a)
    env['clock'][0] += 8000
    a = env['client'].get(f"/api/sessions/{a['id']}").json()
    assert (a['stage']['section'], a['phase'], a['deadline']) == ('listening', 'directions', None)
    a = begin(env, a)
    for qid in ['l1q1', 'l1q2', 'l1q3']:
        assert a['question']['id'] == qid
        if a['phase'] == 'audio':
            env['clock'][0] += 2000
            a = action(env, a, 'audio-ended').json()
        assert a['remainingSeconds'] == 20
        env['clock'][0] += 20_000
        a = env['client'].get(f"/api/sessions/{a['id']}").json()
    assert (a['stage']['section'], a['phase'], a['deadline']) == ('writing', 'directions', None)
    a = begin(env, a)
    for qid, seconds in [('build', 360), ('email', 420), ('discussion', 600)]:
        assert (a['question']['id'], a['remainingSeconds']) == (qid, seconds)
        env['clock'][0] += seconds * 1000
        a = env['client'].get(f"/api/sessions/{a['id']}").json()
        if qid in ['email', 'discussion']:
            assert a['phase'] == 'expired' and a['remainingSeconds'] == 0
            a = action(env, a, 'continue').json()
        if qid != 'discussion':
            assert a['phase'] == 'directions' and a['deadline'] is None and a['question'] is None
            a = begin(env, a)
    assert (a['stage']['section'], a['phase'], a['deadline']) == ('speaking', 'directions', None)
    a = begin(env, a)
    for seconds in [8, 8, 10, 10, 10, 12, 12, 45, 45, 45, 45]:
        assert a['phase'] == 'audio' and a['deadline'] is None
        env['clock'][0] += 2000
        a = action(env, a, 'audio-ended').json()
        assert a['phase'] == 'response' and a['remainingSeconds'] == seconds
        env['clock'][0] += seconds * 1000
        a = env['client'].get(f"/api/sessions/{a['id']}").json()
    assert a['status'] == 'completed'
    assert a['recordingIntegrity']['status'] == 'incomplete'
    assert a['integrity']['eligibleForContinuousStrict'] is False


def test_recording_chunks_retry_combine_in_order_and_new_take_never_overwrites_old(env):
    a = begin(env, start(env, scope='speaking'))
    qid = a['question']['id']
    url = f"/api/sessions/{a['id']}/recordings/{qid}"
    def upload(take, index, content, segment=None):
        return env['client'].post(url, params={'takeId': take, 'index': index, 'segmentId': segment or f'{take}-{index}'}, content=content, headers={'Content-Type': 'audio/webm;codecs=opus'})
    second = upload('take-one', 1, b'BODY')
    assert second.status_code == 200
    assert env['client'].get(second.json()['url']).status_code == 409
    first = upload('take-one', 0, b'HEADER')
    assert first.status_code == 200
    assert upload('take-one', 0, b'HEADER').status_code == 200
    assert upload('take-one', 0, b'CHANGED').status_code == 409
    assert env['client'].get(first.json()['url']).content == b'HEADERBODY'
    ranged = env['client'].get(first.json()['url'], headers={'Range': 'bytes=4-8'})
    assert ranged.status_code == 206 and ranged.content == b'ERBOD'
    action(env, a, 'finish')
    newer = upload('take-two', 0, b'NEW_TAKE')
    assert newer.status_code == 200, 'late completed chunks must be accepted for visited speaking questions'
    assert env['client'].get(first.json()['url']).content == b'HEADERBODY'
    review = env['client'].get(f"/api/sessions/{a['id']}/review").json()
    assert len(review['recordings'][qid]) == 2
    unknown = env['client'].post(f"/api/sessions/{a['id']}/recordings/interview-3", params={'takeId': 'bad', 'index': 0, 'segmentId': 'bad'}, content=b'X', headers={'Content-Type': 'audio/webm'})
    assert unknown.status_code == 403


def test_sentence_token_identity_partial_answer_and_task_locking(env):
    a = begin(env, start(env, scope='writing'))
    assert action(env, a, 'answer', answer={'tokenOrder': ['0', '0']}).status_code == 422
    # Token identities must not become distinct simply by changing their
    # numeric spelling, or reuse could be mistaken for a valid word order.
    assert action(env, a, 'answer', answer={'tokenOrder': ['0', '00']}).status_code == 422
    assert action(env, a, 'answer', answer={'tokenOrder': ['²', '1']}).status_code == 422
    assert action(env, a, 'answer', answer={'tokenOrder': ['٠', '1']}).status_code == 422
    a = action(env, a, 'answer', answer={'tokenOrder': ['0', '']}).json()
    feedback = env['client'].get(f"/api/sessions/{a['id']}/feedback?questionId=build").json()
    assert feedback['grade'] == {'correct': 0, 'total': 1}
    a = action(env, a, 'answer', answer={'tokenOrder': ['0', '1']}).json()
    feedback = env['client'].get(f"/api/sessions/{a['id']}/feedback?questionId=build").json()
    assert feedback['grade'] == {'correct': 1, 'total': 1}
    a = action(env, a, 'next').json()
    assert a['phase'] == 'directions' and a['deadline'] is None
    a = begin(env, a)
    assert a['question']['id'] == 'email' and a['remainingSeconds'] == 420
    assert action(env, a, 'back').status_code == 409
    a = action(env, a, 'next').json()
    assert a['phase'] == 'directions' and a['deadline'] is None
    a = begin(env, a)
    assert a['question']['id'] == 'discussion' and a['remainingSeconds'] == 600
    assert action(env, a, 'back').status_code == 409
    action(env, a, 'finish')
    rating = env['client'].put(f"/api/sessions/{a['id']}/ratings", json={'questionId': 'email', 'value': 4, 'notes': 'Rubric self-review'})
    assert rating.status_code == 200
    assert env['client'].put(f"/api/sessions/{a['id']}/ratings", json={'questionId': 'email', 'value': 6}).status_code == 422


def test_filtered_practice_scores_only_requested_questions_and_rejects_cross_exam_ids(env):
    a = begin(env, start(env, scope='reading', questionIds=['r1q2']))
    assert a['question']['id'] == 'r1q2'
    action(env, a, 'finish')
    review = env['client'].get(f"/api/sessions/{a['id']}/review").json()
    assert review['score']['total'] == 1
    assert env['client'].post('/api/sessions', json={'examId': 'exam', 'questionIds': ['foreign-question']}).status_code == 422
    assert env['client'].post('/api/sessions', json={'examId': 'exam', 'mode': 'strict', 'questionIds': ['r1q1']}).status_code == 422


def test_local_security_rejects_host_origin_traversal_and_asset_symlink(env):
    client = env['client']
    assert client.get('/api/health', headers={'Host': 'attacker.example'}).status_code == 403
    assert client.post('/api/sessions', json={'examId': 'exam'}, headers={'Origin': 'https://attacker.example'}).status_code == 403
    for path in ['/api/library/..%2F..%2Fetc%2Fpasswd', '/materials/%2e%2e%2fsecret', '/storage/practice.sqlite3', '/generated/catalog.json']:
        assert client.get(path).status_code in [404, 422]
    a = begin(env, start(env, scope='reading'))
    stem = env['root'] / 'generated/assets/stem.jpg'
    stem.unlink()
    external = env['root'].parent / f'{uuid.uuid4()}.secret'
    external.write_text('NOT_ALLOWED')
    try:
        stem.symlink_to(external)
        response = client.get(a['question']['assets'][0]['url'])
        assert response.status_code in [403, 404]
        assert 'NOT_ALLOWED' not in response.text
    finally:
        external.unlink()


def test_conflicted_cloze_answers_never_enter_score_denominator():
    question = q('words', 'cloze', blanks=[
        {'id': 'verified', 'prefix': 'rea', 'fullWord': 'reading', 'missingLetters': 'ding'},
        {'id': 'conflicted', 'answer': 'water', 'auditStatus': 'answer-conflict'},
        {'id': 'pending', 'answer': 'the', 'answerConflict': {'status': 'needs-review'}},
    ])
    assert grade(question, {'verified': 'ding', 'conflicted': 'water', 'pending': 'the'}) == {'correct': 1, 'total': 1}
    assert grade(question, {'verified': 'reading'}) == {'correct': 1, 'total': 1}
    assert grade(question, {}) == {'correct': 0, 'total': 1}


def test_sentence_source_punctuation_difference_is_not_a_word_order_error():
    question = q('sentence', 'build_sentence', tokens=['like', 'you'], slots=[{'fixed': 'Would'}, {'id': 'one'}, {'id': 'two'}, {'fixed': 'to visit.'}], answer='Would you like to visit?')
    assert grade(question, {'tokenOrder': ['1', '0']}) == {'correct': 1, 'total': 1}
    assert grade(question, {'tokenOrder': ['0', '1']}) == {'correct': 0, 'total': 1}


def test_empty_object_answers_do_not_mark_a_question_as_answered(env):
    a = begin(env, start(env, scope='reading'))
    a = action(env, a, 'next').json()
    a = action(env, a, 'answer', answer={'blank': ''}).json()
    assert not next(item for item in a['questionMap'] if item['questionId'] == 'r1q2')['answered']


def test_simultaneous_duplicate_clicks_across_two_application_instances_are_serialized(env):
    a = begin(env, start(env, scope='reading'))
    payload = {'action': 'next', 'questionId': 'r1q1', 'requestId': 'concurrent-duplicate'}
    def submit():
        app = create_app(env['root'], clock=lambda: env['clock'][0], testing=True)
        with TestClient(app) as client:
            response = client.post(f"/api/sessions/{a['id']}/events", json=payload)
            assert response.status_code == 200, response.text
            return response.json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        left, right = list(pool.map(lambda _: submit(), range(2)))
    assert left['question']['id'] == right['question']['id'] == 'r1q2'
    assert left['revision'] == right['revision']


def test_module_directions_and_question_audio_each_finish_once_before_response(env):
    path = env['root'] / 'generated/exams/exam.json'
    exam = json.loads(path.read_text())
    module = next(s for s in exam['sections'] if s['id'] == 'listening')['modules'][0]
    module['instructions'] = 'Listen to the task instructions first.'
    module['directionsAudio'] = {'url': '/materials/other.ogg', 'durationSeconds': 3, 'kind': 'directions', 'groupId': 'task-directions'}
    module['questions'][0]['mediaSequence'] = [
        {'url': '/materials/shared.ogg', 'durationSeconds': 2, 'kind': 'stimulus', 'groupId': 'conversation'},
        {'url': '/materials/other.ogg', 'durationSeconds': 1, 'kind': 'question', 'groupId': 'spoken-question'},
    ]
    module['questions'][0]['warnings'] = ['SECRET_ANSWER was corrected from source key.']
    path.write_text(json.dumps(exam))
    catalog_path = env['root'] / 'generated/catalog.json'
    catalog_path.write_text(catalog_path.read_text() + ' ')
    a = begin(env, start(env, scope='listening', mode='strict'))
    assert a['stage']['instructions'] == module['instructions']
    assert 'SECRET_ANSWER' not in json.dumps(a)
    for index, seconds in enumerate([3, 2, 1]):
        assert a['phase'] == 'audio' and a['mediaIndex'] == index
        assert action(env, a, 'audio-ended', mediaIndex=index + 1).status_code == 409
        env['clock'][0] += 500
        a = action(env, a, 'audio-started', mediaIndex=index).json()
        assert a['audioEarliestEnd'] == env['clock'][0] + seconds * 1000
        assert action(env, a, 'audio-ended', mediaIndex=index).status_code == 409
        env['clock'][0] += seconds * 1000
        a = action(env, a, 'audio-ended', mediaIndex=index).json()
    assert a['phase'] == 'response' and a['remainingSeconds'] == 20
    assert 'SECRET_ANSWER' not in json.dumps(a)


def test_strict_verified_writing_and_interview_times_cannot_be_overridden(env):
    a = start(env, scope='writing', mode='strict', timing={'email': 1, 'academicDiscussion': 2, 'interview': 3})
    assert a['timing']['email'] == 420
    assert a['timing']['academicDiscussion'] == 600
    assert a['timing']['interview'] == 45


@pytest.mark.parametrize('timing', [[], 'invalid', 5, {'repeat': [8, 8, 10, 10, 10, 12, float('nan')]},
                                   {'repeat': [8, 8, 10, 10, 10, 12, float('inf')]}])
def test_invalid_timing_cannot_persist_a_broken_or_locking_session(env, timing):
    response = env['client'].post('/api/sessions',
        content=json.dumps({'examId': 'exam', 'mode': 'strict', 'scope': 'reading', 'timing': timing}),
        headers={'Content-Type': 'application/json'})
    assert response.status_code == 422
    assert env['client'].get('/api/sessions').json()['sessions'] == []
    assert start(env, mode='strict', scope='reading')['status'] == 'active'


def test_matching_orphan_audio_chunk_can_be_retried_after_a_metadata_write_failure(env):
    a = begin(env, start(env, scope='speaking'))
    segment_dir = env['root'] / 'storage/segments'
    segment_dir.mkdir()
    (segment_dir / 'orphan-segment.bin').write_bytes(b'PRESERVED_AUDIO')
    response = env['client'].post(f"/api/sessions/{a['id']}/recordings/{a['question']['id']}",
        params={'takeId': 'orphan-take', 'index': 0, 'segmentId': 'orphan-segment'},
        content=b'PRESERVED_AUDIO', headers={'Content-Type': 'audio/webm'})
    assert response.status_code == 200
    assert env['client'].get(response.json()['url']).content == b'PRESERVED_AUDIO'


def test_an_active_strict_session_locks_cross_session_review_and_new_practice_feedback(env):
    old = begin(env, start(env, scope='reading'))
    old_asset = old['question']['assets'][0]['assetId']
    action(env, old, 'finish')
    fresh = begin(env, start(env, scope='reading'))
    strict = begin(env, start(env, scope='reading', mode='strict'))
    assert env['client'].get(f"/api/sessions/{old['id']}/review").status_code == 403
    assert env['client'].get(f"/api/sessions/{old['id']}/export").status_code == 403
    assert env['client'].get(f"/api/sessions/{old['id']}/review-assets/{old_asset}").status_code == 403
    assert env['client'].get(f"/api/sessions/{fresh['id']}/feedback?questionId=r1q1").status_code == 403
    assert env['client'].post('/api/sessions', json={'examId': 'exam', 'mode': 'practice', 'scope': 'reading'}).status_code == 403
    assert env['client'].get(f"/api/sessions/{fresh['id']}").status_code == 403
    assert action(env, fresh, 'answer', answer='A').status_code == 403
    assert env['client'].get(f"/api/sessions/{fresh['id']}/review").status_code == 403
    assert env['client'].get('/api/validation').status_code == 403
    history = env['client'].get('/api/sessions').json()['sessions']
    assert all('items' not in (s.get('score') or {}) for s in history)
    action(env, strict, 'finish')
    assert env['client'].get(f"/api/sessions/{old['id']}/review").status_code == 200
    assert env['client'].get(f"/api/sessions/{fresh['id']}").status_code == 200


def test_question_library_paginates_metadata_without_answers_and_tracks_progress(env):
    client = env['client']
    result = client.get('/api/questions?section=reading&pageSize=2').json()
    assert result['total'] > 2 and len(result['items']) == 2
    assert result['taskCounts']['choice'] > 0
    for item in result['items']:
        assert item['status'] == 'not_started'
        assert item['contentId'] and item['duplicateCount'] >= 1
        for private in ['prompt', 'answer', 'passage', 'transcript', 'assets', 'audio', 'source']:
            assert private not in item
    assert 'SECRET_ANSWER' not in json.dumps(result)
    assert '/materials/' not in json.dumps(result)
    assert client.get('/api/questions?section=reading&q=r1q2').json()['total'] == 1
    assert client.get('/api/questions?taskType=email').json()['total'] == 1
    a = begin(env, start(env, scope='reading', questionIds=['r1q1']))
    progress = client.get('/api/questions?section=reading&q=r1q1').json()['items'][0]
    assert progress['status'] == 'in_progress'
    action(env, a, 'next')
    progress = client.get('/api/questions?section=reading&q=r1q1').json()['items'][0]
    assert progress['status'] == 'completed'
    strict = begin(env, start(env, scope='reading', mode='strict'))
    assert client.get('/api/questions').status_code == 403
    action(env, strict, 'finish')
    assert client.get('/api/questions?pageSize=10000').status_code == 422


def test_section_completion_distinguishes_filtered_work_and_conservatively_migrates_old_records(env):
    full = start(env, scope='reading')
    partial = start(env, scope='reading', questionIds=['r1q1'])
    writing_task = start(env, scope='writing', taskType='build_sentence')
    assert full['isFullScope'] is True and full['filtered'] is False
    assert partial['isFullScope'] is False and partial['filters']['questionIds'] == ['r1q1']
    assert writing_task['isFullScope'] is False
    store = env['app'].state.store
    with store.transaction() as db:
        for session_id in [full['id'], partial['id']]:
            legacy = store.get(db, session_id)
            for key in ['filters', 'filtered', 'isFullScope']:
                legacy.pop(key, None)
            store.save(db, legacy)
    by_id = {item['id']: item for item in env['client'].get('/api/sessions').json()['sessions']}
    assert by_id[full['id']]['isFullScope'] is True
    assert by_id[partial['id']]['isFullScope'] is False
    assert env['client'].post('/api/sessions', json={'examId': 'exam', 'questionIds': []}).status_code == 422


def test_supplementary_exams_are_registered_safely_and_can_only_use_practice_mode(env):
    supplemental = {'id': 'essentials-test', 'title': 'Supplementary Essentials fixture', 'family': 'essentials',
                    'supplemental': True, 'strictEligible': True, 'sections': [{'id': 'reading', 'modules': [
                        {'id': 'essentials-reading', 'durationSeconds': 20, 'questions': [q('essentials-question', answer='A')]}
                    ]}]}
    (env['root'] / 'generated/exams/essentials-test.json').write_text(json.dumps(supplemental))
    catalog_path = env['root'] / 'generated/catalog.json'
    catalog = json.loads(catalog_path.read_text())
    catalog['supplementalExams'] = [{'id': 'essentials-test', 'associatedMaterials': [{'url': '/materials/source.pdf'}]}]
    catalog_path.write_text(json.dumps(catalog))
    public = env['client'].get('/api/catalog').json()
    added = next(item for item in public['exams'] if item['id'] == 'essentials-test')
    assert added['supplemental'] is True and added['strictEligible'] is False
    assert '/materials/' not in json.dumps(public)
    assert env['client'].post('/api/sessions', json={'examId': 'essentials-test', 'mode': 'strict'}).status_code == 422
    assert env['client'].post('/api/sessions', json={'examId': 'essentials-test', 'mode': 'practice', 'routeMode': 'adaptive'}).status_code == 422
    result = env['client'].post('/api/sessions', json={'examId': 'essentials-test', 'mode': 'practice', 'scope': 'reading'})
    assert result.status_code == 200
    assert result.json()['supplemental'] is True


def test_source_key_correction_evidence_is_released_only_in_review(env):
    path = env['root'] / 'generated/exams/exam.json'
    exam = json.loads(path.read_text())
    first = exam['sections'][0]['modules'][0]['questions'][0]
    first.update(sourceReferenceAnswer='ORIGINAL_SOURCE_KEY', answerConflict={'status': 'resolved', 'provided': 'ORIGINAL_SOURCE_KEY'},
                 resolutionEvidence='SOURCE_IMAGE_CHECK', answerEvidence={'kind': 'manual-source-verification'}, auditStatus='verified-correction')
    path.write_text(json.dumps(exam))
    catalog_path = env['root'] / 'generated/catalog.json'
    catalog_path.write_text(catalog_path.read_text() + ' ')
    a = begin(env, start(env, scope='reading', mode='strict'))
    assert 'ORIGINAL_SOURCE_KEY' not in json.dumps(a)
    assert 'SOURCE_IMAGE_CHECK' not in json.dumps(a)
    assert 'auditStatus' not in a['question']
    action(env, a, 'finish')
    review = env['client'].get(f"/api/sessions/{a['id']}/review").json()
    first_review = review['sections'][0]['modules'][0]['questions'][0]
    assert first_review['sourceReferenceAnswer'] == 'ORIGINAL_SOURCE_KEY'
    assert first_review['resolutionEvidence'] == 'SOURCE_IMAGE_CHECK'
    assert first_review['auditStatus'] == 'verified-correction'


def test_missing_item_audio_uses_untimed_reference_practice_instead_of_fake_twenty_second_flow(env):
    path = env['root'] / 'generated/exams/exam.json'
    exam = json.loads(path.read_text())
    listening = next(s for s in exam['sections'] if s['id'] == 'listening')
    listening['practiceAudio'] = {'url': '/materials/shared.ogg', 'durationSeconds': 2, 'mediaType': 'audio'}
    for mod in listening['modules']:
        for item in mod['questions']:
            item.pop('audio', None)
            item['referenceOnly'] = True
            item['sourcePromptAvailable'] = True
    path.write_text(json.dumps(exam))
    catalog = env['root'] / 'generated/catalog.json'; catalog.write_text(catalog.read_text() + ' ')
    a = begin(env, start(env, scope='listening'))
    assert a['stage']['timer'] == 'untimed'
    assert a['phase'] == 'response' and a['deadline'] is None
    assert 'audio' not in a['question']
    assert len(a['stage']['practiceAudio']) == 1
    audio = a['stage']['practiceAudio'][0]
    assert env['client'].get(audio['url']).content == b'0123456789'
    env['clock'][0] += 600_000
    unchanged = env['client'].get(f"/api/sessions/{a['id']}").json()
    assert unchanged['question']['id'] == a['question']['id']
    assert unchanged['deadline'] is None
    assert action(env, unchanged, 'next').json()['question']['id'] == 'l1q2'
    assert env['client'].post('/api/sessions', json={'examId': 'exam', 'mode': 'strict', 'scope': 'listening'}).status_code == 422


def test_untimed_speaking_requires_manual_next_and_never_auto_submits(env):
    path = env['root'] / 'generated/exams/exam.json'
    exam = json.loads(path.read_text()); exam.update(supplemental=True, timingPolicy='untimed')
    path.write_text(json.dumps(exam))
    catalog = env['root'] / 'generated/catalog.json'; catalog.write_text(catalog.read_text() + ' ')
    a = begin(env, start(env, scope='speaking'))
    assert a['stage']['timer'] == 'untimed' and a['phase'] == 'response'
    assert 'next' in a['allowedActions']
    assert a['rulesVersion'] == 'supplementary-untimed-v1'
    env['clock'][0] += 3600_000
    assert env['client'].get(f"/api/sessions/{a['id']}").json()['question']['id'] == a['question']['id']
    assert action(env, a, 'next').json()['question']['id'] == 'repeat-1'


def test_unavailable_reference_prompt_is_not_exposed_as_an_interactive_question(env):
    path = env['root'] / 'generated/exams/exam.json'
    exam = json.loads(path.read_text())
    unavailable = exam['sections'][0]['modules'][0]['questions'][0]
    unavailable.update(referenceOnly=True, sourcePromptAvailable=False)
    path.write_text(json.dumps(exam))
    catalog = env['root'] / 'generated/catalog.json'; catalog.write_text(catalog.read_text() + ' ')
    assert env['client'].get('/api/questions?section=reading&q=r1q1').json()['total'] == 0
    a = begin(env, start(env, scope='reading'))
    assert a['question']['id'] == 'r1q2'
    assert env['client'].post('/api/sessions', json={'examId': 'exam', 'mode': 'practice', 'questionIds': ['r1q1']}).status_code == 422


def test_recording_completion_requires_final_metadata_and_preserves_original_interruptions(env):
    a = begin(env, start(env, scope='speaking', questionIds=['repeat-0']))
    qid = a['question']['id']
    base = f"/api/sessions/{a['id']}/recordings"
    def upload(index, text):
        return env['client'].post(f'{base}/{qid}', params={'takeId': 'final-test', 'index': index, 'segmentId': f'final-part-{index}'}, content=text, headers={'Content-Type': 'audio/webm'})
    assert upload(0, b'HEADER').status_code == 200
    env['clock'][0] += 2000
    a = action(env, a, 'audio-ended').json()
    a = action(env, a, 'interrupt', reason='storage-recovery-test').json()
    env['clock'][0] += 8000
    a = env['client'].get(f"/api/sessions/{a['id']}").json()
    assert a['status'] == 'completed'
    integrity = a['recordingIntegrity']
    assert integrity['status'] == 'incomplete'
    assert integrity['missingQuestionIds'] == [qid]
    assert integrity['incompleteTakes'][0]['reason'] == 'not_finalized'
    final = {'questionId': qid, 'segmentCount': 2, 'endedReason': 'time-limit', 'mimeType': 'audio/webm;codecs=opus'}
    response = env['client'].post(f'{base}/takes/final-test/finalize', json=final)
    assert response.status_code == 200
    assert response.json()['take']['missingIndices'] == [1]
    assert response.json()['take']['completeSequence'] is False
    assert env['client'].post(f'{base}/takes/final-test/finalize', json=final).status_code == 200
    assert env['client'].post(f'{base}/takes/final-test/finalize', json={**final, 'segmentCount': 3}).status_code == 409
    assert upload(1, b'FINAL').status_code == 200
    assert upload(2, b'EXTRA').status_code == 409
    review = env['client'].get(f"/api/sessions/{a['id']}/review").json()
    assert review['recordingIntegrity']['status'] == 'complete'
    assert review['recordingIntegrity']['recordedQuestionIds'] == [qid]
    assert review['session']['integrity']['interrupted'] is True
    assert review['recordings'][qid][0]['expectedSegmentCount'] == 2


def test_finalization_can_arrive_before_chunks_and_zero_chunk_takes_remain_empty(env):
    a = begin(env, start(env, scope='speaking', questionIds=['repeat-0']))
    qid = a['question']['id']
    route = f"/api/sessions/{a['id']}/recordings/takes/empty-take/finalize"
    final = {'questionId': qid, 'segmentCount': 0, 'endedReason': 'user-stop', 'mimeType': 'audio/webm'}
    response = env['client'].post(route, json=final)
    assert response.status_code == 200
    assert response.json()['take']['state'] == 'empty'
    assert response.json()['take']['completeSequence'] is False
    assert env['client'].post(route, json=final).status_code == 200
    final_first = {'questionId': qid, 'segmentCount': 1, 'endedReason': 'time-limit', 'mimeType': 'audio/webm'}
    response = env['client'].post(route.replace('empty-take', 'arrives-first'), json=final_first)
    assert response.status_code == 200
    assert response.json()['take']['missingIndices'] == [0]
    result = env['client'].post(f"/api/sessions/{a['id']}/recordings/{qid}", params={'takeId': 'arrives-first', 'index': 0, 'segmentId': 'late-chunk'}, content=b'LATE_AUDIO', headers={'Content-Type': 'audio/webm'})
    assert result.status_code == 200
    current = env['client'].get(f"/api/sessions/{a['id']}").json()
    assert qid in current['recordingIntegrity']['recordedQuestionIds']
    assert current['recordingIntegrity']['incompleteTakes'][0]['reason'] == 'empty'


def test_supplementary_subjective_tasks_never_receive_string_match_scores():
    assert grade({'type': 'read_aloud', 'answer': 'Original read-aloud text'}, 'Original read-aloud text') is None
    assert grade({'type': 'picture_writing', 'answer': 'Sample description'}, 'Sample description') is None
    assert grade({'type': 'future-subjective-type', 'subjective': True, 'answer': 'Example'}, 'Example') is None


def test_sentence_scoring_accepts_only_explicit_source_variants():
    question = {'type': 'build_sentence', 'tokens': ['alpha', 'beta', 'gamma'],
                'slots': [{'id': 'one'}, {'id': 'two'}, {'id': 'three'}], 'answer': 'alpha beta gamma.',
                'acceptedAnswers': ['beta alpha gamma?'], 'sourceAnswerVariants': [{'source': 'engineering-test-fixture', 'answer': 'beta alpha gamma?'}]}
    assert grade(question, {'tokenOrder': ['0', '1', '2']}) == {'correct': 1, 'total': 1}
    assert grade(question, {'tokenOrder': ['1', '0', '2']}) == {'correct': 1, 'total': 1}
    assert grade(question, 'BETA  ALPHA GAMMA.') == {'correct': 1, 'total': 1}
    assert grade(question, {'tokenOrder': ['2', '1', '0']}) == {'correct': 0, 'total': 1}


def test_finalized_streaming_webm_gets_lossless_duration_index_and_range_without_changing_segments(env):
    executable = ffmpeg_executable()
    tone = subprocess.run([executable, '-nostdin', '-hide_banner', '-loglevel', 'error', '-f', 'lavfi',
        '-i', 'sine=frequency=523.25:sample_rate=48000:duration=0.35', '-c:a', 'libopus', '-f', 'webm', 'pipe:1'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout
    # A pipe is deliberately nonseekable and does not contain a finalized
    # WebM Duration header, like MediaRecorder's streaming chunks.
    raw_path = env['root'] / 'streaming-test.webm'; raw_path.write_bytes(tone)
    assert probe_duration(raw_path, executable) is None
    a = begin(env, start(env, scope='speaking', questionIds=['repeat-0']))
    qid = a['question']['id']; route = f"/api/sessions/{a['id']}/recordings"
    cut = len(tone) // 3
    chunks = [tone[:cut], tone[cut:cut*2], tone[cut*2:]]
    for index in [1, 0, 2]:
        response = env['client'].post(f'{route}/{qid}', params={'takeId': 'real-codec-test', 'index': index, 'segmentId': f'codec-{index}'}, content=chunks[index], headers={'Content-Type': 'audio/webm'})
        assert response.status_code == 200
    url = response.json()['url']
    raw = env['client'].get(url)
    assert raw.content == tone and raw.headers['x-recording-container'] == 'raw-unverified'
    final = env['client'].post(f'{route}/takes/real-codec-test/finalize', json={'questionId': qid, 'segmentCount': 3, 'endedReason': 'user-stop', 'mimeType': 'audio/webm'})
    assert final.status_code == 200
    originals = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (env['root'] / 'storage/segments').glob('codec-*.bin')}
    indexed = env['client'].get(url)
    assert indexed.status_code == 200
    assert indexed.headers['x-recording-container'] == 'lossless-remux'
    assert .3 <= float(indexed.headers['x-recording-duration']) <= .5
    playback = env['root'] / 'indexed-test.webm'; playback.write_bytes(indexed.content)
    assert .3 <= probe_duration(playback, executable) <= .5
    decoded = subprocess.run([executable, '-nostdin', '-hide_banner', '-loglevel', 'error', '-i', str(playback), '-f', 'null', '-'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert decoded.returncode == 0
    def packets(path):
        return subprocess.run([executable, '-nostdin', '-hide_banner', '-loglevel', 'error', '-i', str(path), '-map', '0:a:0', '-c', 'copy', '-f', 'data', 'pipe:1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout
    assert packets(raw_path) == packets(playback), 'remux must preserve compressed audio packets without re-encoding'
    ranged = env['client'].get(url, headers={'Range': 'bytes=0-15'})
    assert ranged.status_code == 206 and ranged.content == indexed.content[:16]
    assert originals == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (env['root'] / 'storage/segments').glob('codec-*.bin')}


def test_invalid_finalized_audio_falls_back_to_raw_without_claiming_playback_validation(env):
    a = begin(env, start(env, scope='speaking', questionIds=['repeat-0']))
    qid = a['question']['id']; route = f"/api/sessions/{a['id']}/recordings"
    response = env['client'].post(f'{route}/{qid}', params={'takeId': 'invalid-codec', 'index': 0, 'segmentId': 'invalid-codec-0'}, content=b'NOT_AN_AUDIO_CONTAINER', headers={'Content-Type': 'audio/webm'})
    env['client'].post(f'{route}/takes/invalid-codec/finalize', json={'questionId': qid, 'segmentCount': 1, 'endedReason': 'user-stop', 'mimeType': 'audio/webm'})
    played = env['client'].get(response.json()['url'])
    assert played.status_code == 200 and played.content == b'NOT_AN_AUDIO_CONTAINER'
    assert played.headers['x-recording-container'] == 'raw-unverified'
    assert 'x-recording-duration' not in played.headers


def test_untimed_practice_exposes_only_current_clean_clips_and_explicit_text_study(env):
    path = env['root'] / 'generated/exams/exam.json'
    exam = json.loads(path.read_text()); exam.update(supplemental=True, timingPolicy='untimed')
    listening = next(s for s in exam['sections'] if s['id'] == 'listening')
    first = listening['modules'][0]['questions'][0]
    first.update(transcript='Supplied paper transcript for text study.', displayTranscriptDuringPractice=True)
    path.write_text(json.dumps(exam)); catalog = env['root'] / 'generated/catalog.json'; catalog.write_text(catalog.read_text() + ' ')
    a = begin(env, start(env, scope='listening'))
    assert a['stage']['timer'] == 'untimed'
    assert a['stage']['practiceAudio'] == []
    assert len(a['question']['practiceMediaSequence']) == 1
    assert a['question']['transcript'] == first['transcript']
    assert a['question']['displayTranscriptDuringPractice'] is True
    clip = a['question']['practiceMediaSequence'][0]
    assert env['client'].get(clip['url']).status_code == 200
    a = action(env, a, 'next').json()
    assert 'transcript' not in a['question'], 'text-study transcript needs an explicit source flag'
