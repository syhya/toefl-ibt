"""Pack 1 pages 18, 85 and 87 require Begin before the next timed R/W stage.

These engineering fixtures contain no newly generated study questions or audio.
"""
import json

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.tests.test_api import env, start, begin, action


def assert_directions(view):
    assert view['status'] == 'active' and view['phase'] == 'directions'
    assert view['deadline'] is None and view['remainingSeconds'] is None
    assert view['question'] is None
    assert 'begin' in view['allowedActions']
    assert not set(view['allowedActions']) & {'answer', 'next', 'back', 'jump', 'flag'}


@pytest.mark.parametrize('mode', ['strict', 'practice'])
@pytest.mark.parametrize('end_reason', ['submit', 'timeout'])
def test_reading_module_two_waits_at_source_begin_screen_and_preserves_deadlines(env, mode, end_reason):
    first = begin(env, start(env, scope='reading', mode=mode))
    assert action(env, first, 'answer', answer='A').status_code == 200
    if end_reason == 'submit':
        env['clock'][0] += 3000
        last = action(env, first, 'next').json()
        waiting = action(env, last, 'next').json()
    else:
        # A delayed poll must not consume time from an unstarted second module.
        env['clock'][0] = first['deadline'] + 30_000
        waiting = env['client'].get(f"/api/sessions/{first['id']}").json()
    assert_directions(waiting)
    assert waiting['stage']['id'] == 'r2' and waiting['stage']['seconds'] == 8
    assert action(env, waiting, 'answer', questionId='r2q1', answer='B').status_code == 409
    assert action(env, waiting, 'next', questionId='r2q1').status_code == 409
    assert action(env, first, 'answer', answer='B').status_code == 409

    env['clock'][0] += 90_000
    restarted = create_app(env['root'], clock=lambda: env['clock'][0], testing=True)
    with TestClient(restarted) as client:
        restored = client.get(f"/api/sessions/{first['id']}").json()
        assert_directions(restored)
        begin_payload = {'action': 'begin', 'requestId': 'source-module-two-begin'}
        begun = client.post(f"/api/sessions/{first['id']}/events", json=begin_payload).json()
        assert begun['question']['id'] == 'r2q1'
        assert begun['deadline'] == env['clock'][0] + 8000
        assert begun['remainingSeconds'] == 8
        assert 'back' not in begun['allowedActions']
        env['clock'][0] += 2000
        retried = client.post(f"/api/sessions/{first['id']}/events", json=begin_payload).json()
        assert retried['deadline'] == begun['deadline'] and retried['remainingSeconds'] == 6
        assert client.post(f"/api/sessions/{first['id']}/events", json={'action': 'begin', 'requestId': 'invalid-restart'}).status_code == 409
        env['clock'][0] = begun['deadline']
        completed = client.get(f"/api/sessions/{first['id']}").json()
        assert completed['status'] == 'completed' and completed['completedAt'] == begun['deadline']
        assert client.get(f"/api/sessions/{first['id']}/review").json()['answers'] == {'r1q1': 'A'}


@pytest.mark.parametrize('mode', ['strict', 'practice'])
@pytest.mark.parametrize('end_reason', ['submit', 'timeout'])
def test_email_and_discussion_each_start_only_after_their_original_begin_screen(env, mode, end_reason):
    current = begin(env, start(env, scope='writing', mode=mode))
    for next_question, seconds in [('email', 420), ('discussion', 600)]:
        previous = current
        if end_reason == 'submit':
            env['clock'][0] += 3000
            waiting = action(env, current, 'next').json()
        else:
            env['clock'][0] = current['deadline'] + 30_000
            waiting = env['client'].get(f"/api/sessions/{current['id']}").json()
            if current['question']['type'] in ['email', 'academic_discussion']:
                assert waiting['phase'] == 'expired'
                waiting = action(env, waiting, 'continue').json()
        assert_directions(waiting)
        assert waiting['stage']['seconds'] == seconds
        assert action(env, previous, 'answer', answer='Late text must not enter the next task').status_code == 409
        assert action(env, waiting, 'answer', questionId=next_question, answer='The task has not started').status_code == 409
        env['clock'][0] += 120_000
        restored = env['client'].get(f"/api/sessions/{current['id']}").json()
        assert_directions(restored)
        current = begin(env, restored)
        assert current['question']['id'] == next_question and current['remainingSeconds'] == seconds
        assert current['deadline'] == env['clock'][0] + seconds * 1000
        assert action(env, current, 'back').status_code == 409
        env['clock'][0] += 1000
        refreshed = env['client'].get(f"/api/sessions/{current['id']}").json()
        assert refreshed['deadline'] == current['deadline'] and refreshed['remainingSeconds'] == seconds - 1
    action(env, current, 'finish')
    assert env['client'].get(f"/api/sessions/{current['id']}/review").json()['answers'] == {}


@pytest.mark.parametrize('section', ['listening', 'speaking'])
def test_audio_sections_still_cross_same_section_modules_without_a_preparation_screen(env, section):
    path = env['root'] / 'generated/exams/exam.json'
    exam = json.loads(path.read_text())
    selected = next(item for item in exam['sections'] if item['id'] == section)
    if section == 'listening':
        questions = selected['modules'][0]['questions']
        selected['modules'] = [
            {'id': 'listening-before', 'questions': [questions[0]]},
            {'id': 'listening-after', 'questions': [questions[-1]]},
        ]
        next_question = questions[-1]['id']
    else:
        selected['modules'][0]['questions'] = [selected['modules'][0]['questions'][0]]
        next_question = selected['modules'][1]['questions'][0]['id']
    path.write_text(json.dumps(exam))
    catalog = env['root'] / 'generated/catalog.json'
    catalog.write_text(catalog.read_text() + ' ')
    current = begin(env, start(env, scope=section, mode='strict'))
    env['clock'][0] += 2000
    current = action(env, current, 'audio-ended').json()
    env['clock'][0] = current['deadline']
    next_module = env['client'].get(f"/api/sessions/{current['id']}").json()
    assert next_module['phase'] == 'audio' and next_module['question']['id'] == next_question
    assert next_module['deadline'] is None and 'begin' not in next_module['allowedActions']
    env['clock'][0] += 2000
    response = action(env, next_module, 'audio-ended').json()
    assert response['phase'] == 'response'
    assert response['remainingSeconds'] == (45 if section == 'speaking' else 20)


def test_untimed_reference_writing_retains_its_existing_manual_flow(env):
    path = env['root'] / 'generated/exams/exam.json'
    exam = json.loads(path.read_text())
    exam['timingPolicy'] = 'untimed'
    path.write_text(json.dumps(exam))
    catalog = env['root'] / 'generated/catalog.json'
    catalog.write_text(catalog.read_text() + ' ')
    current = begin(env, start(env, scope='writing', mode='practice'))
    following = action(env, current, 'next').json()
    assert following['question']['id'] == 'email' and following['phase'] == 'response'
    assert following['stage']['timer'] == 'untimed' and following['deadline'] is None
