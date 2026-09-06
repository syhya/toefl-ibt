"""Objective results freeze on submission; late recordings and self-ratings stay live."""
from copy import deepcopy
import json

import pytest
from fastapi.testclient import TestClient

from backend import engine
from backend.app import create_app
from backend.tests.test_api import env, start, begin, action


def stored(env, session_id):
    store = env['app'].state.store
    with store.transaction() as db:
        return store.get(db, session_id)


def test_selected_multisection_snapshot_survives_restart_and_a_future_grader(env, monkeypatch):
    current = begin(env, start(env, scope='all', questionIds=['r1q1', 'email']))
    assert current['scoreSnapshotStatus'] == 'pending'
    current = action(env, current, 'answer', answer='B').json()
    writing_directions = action(env, current, 'next').json()
    assert 'scoreSnapshot' not in stored(env, current['id']), 'An intermediate Begin screen must not freeze a final result.'
    current = begin(env, writing_directions)
    current = action(env, current, 'answer', answer='A subjective response.').json()
    completed = action(env, current, 'next').json()
    frozen = deepcopy(stored(env, completed['id'])['scoreSnapshot'])
    assert frozen['engineVersion'] == engine.SCORING_ENGINE_VERSION
    assert frozen['score']['items'] == {'r1q1': {'correct': 0, 'total': 1}}
    assert frozen['score']['sections'] == {'reading': {'correct': 0, 'total': 1}, 'writing': {'correct': 0, 'total': 0}}
    assert frozen['score']['ungraded'] == 1
    assert frozen['score']['attemptedCount'] == 2
    assert completed['scoreSnapshotStatus'] == 'frozen'
    # Simulate an upgrade that would wrongly turn every old item, including
    # subjective writing, into a correct objective point.
    monkeypatch.setattr(engine, 'grade', lambda question, answer: {'correct': 1, 'total': 1})
    monkeypatch.setattr(engine, 'SCORING_ENGINE_VERSION', 'a-future-grading-engine')
    restarted = create_app(env['root'], clock=lambda: env['clock'][0], testing=True)
    with TestClient(restarted) as client:
        review = client.get(f"/api/sessions/{completed['id']}/review").json()
        exported = client.get(f"/api/sessions/{completed['id']}/export").json()
        for result in [review, exported]:
            assert result['scoreSnapshot'] == frozen
            assert result['score'] == frozen['score']
            assert result['sections'][0]['modules'][0]['questions'][0]['grade'] == {'correct': 0, 'total': 1}
            assert result['sections'][1]['modules'][0]['questions'][0]['grade'] is None
            assert result['session']['scoringEngineVersion'] == frozen['engineVersion']
        feedback = client.get(f"/api/sessions/{completed['id']}/feedback?questionId=r1q1").json()
        assert feedback['grade'] == {'correct': 0, 'total': 1}
        item = client.get('/api/mistakes').json()['items'][0]
        assert item['questionId'] == 'r1q1' and item['lastGrade'] == {'correct': 0, 'total': 1}
        assert item['scoreSnapshotStatus'] == 'frozen'
        history = client.get('/api/sessions').json()['sessions'][0]
        assert history['score']['correct'] == 0 and history['score']['total'] == 1
    assert stored(env, completed['id'])['scoreSnapshot'] == frozen


@pytest.mark.parametrize('ending', ['timeout', 'abandoned-while-paused'])
def test_snapshot_is_saved_at_every_final_transition_and_late_answers_cannot_change_it(env, ending):
    current = begin(env, start(env, scope='reading', questionIds=['r1q1']))
    current = action(env, current, 'answer', answer='A').json()
    if ending == 'timeout':
        env['clock'][0] = current['deadline'] + 1500
        rejected = action(env, current, 'answer', answer='B')
        assert rejected.status_code == 409
        ended = rejected.json()['session']
        assert ended['completedAt'] == current['deadline']
    else:
        env['clock'][0] += 2000
        paused = action(env, current, 'pause').json()
        env['clock'][0] += 60_000
        ended = action(env, paused, 'finish').json()
    frozen = deepcopy(stored(env, current['id'])['scoreSnapshot'])
    assert frozen['calculatedAt'] == env['clock'][0]
    assert frozen['score']['correct'] == frozen['score']['total'] == 1
    if ending == 'abandoned-while-paused':
        assert frozen['score']['wallSeconds'] == 62 and frozen['score']['durationSeconds'] == 2
    env['clock'][0] += 20_000
    assert action(env, ended, 'answer', questionId='r1q1', answer='B').status_code == 409
    assert action(env, ended, 'interrupt', reason='late-client-diagnostic').status_code == 200
    assert stored(env, current['id'])['scoreSnapshot'] == frozen


def test_abandoning_before_adaptive_routing_does_not_score_unselected_branches(env):
    current = begin(env, start(env, examId='adaptive', scope='reading', routeMode='adaptive'))
    current = action(env, current, 'answer', answer='A').json()
    ended = action(env, current, 'finish').json()
    score = stored(env, ended['id'])['scoreSnapshot']['score']
    assert score['correct'] == 1 and score['total'] == 10
    assert set(score['items']) == {f'router-{index}' for index in range(10)}
    assert 'lower-question' not in score['items'] and 'upper-question' not in score['items']


def test_late_recordings_and_self_ratings_update_review_without_mutating_objective_snapshot(env):
    current = begin(env, start(env, scope='speaking', questionIds=['repeat-0']))
    env['clock'][0] += 2000
    current = action(env, current, 'audio-ended').json()
    env['clock'][0] = current['deadline']
    completed = env['client'].get(f"/api/sessions/{current['id']}").json()
    frozen = deepcopy(stored(env, current['id'])['scoreSnapshot'])
    assert frozen['score']['items'] == {} and frozen['score']['total'] == 0
    assert frozen['score']['ungraded'] == 1 and frozen['score']['attemptedCount'] == 0
    assert completed['recordingIntegrity']['status'] == 'incomplete'
    assert 'recordingIntegrity' not in frozen and 'ratings' not in frozen
    base = f"/api/sessions/{current['id']}"
    uploaded = env['client'].post(f'{base}/recordings/repeat-0',
        params={'takeId': 'late-take', 'segmentId': 'late-segment', 'index': 0},
        content=b'ISOLATED_LATE_RECORDING_FIXTURE', headers={'Content-Type': 'audio/webm'})
    assert uploaded.status_code == 200
    assert env['client'].post(f'{base}/recordings/takes/late-take/finalize', json={
        'questionId': 'repeat-0', 'segmentCount': 1, 'endedReason': 'time-limit', 'mimeType': 'audio/webm'}).status_code == 200
    assert env['client'].put(f'{base}/ratings', json={'questionId': 'repeat-0', 'value': 0, 'notes': 'A real saved zero self-rating.'}).status_code == 200
    review = env['client'].get(f'{base}/review').json()
    assert review['recordingIntegrity']['status'] == 'complete'
    assert review['score']['attemptedCount'] == 1
    assert review['ratings']['repeat-0']['value'] == 0
    assert review['scoreSnapshot']['score']['attemptedCount'] == 0
    assert review['sections'][0]['modules'][0]['questions'][0]['grade'] is None
    assert env['client'].put(f'{base}/ratings', json={'questionId': 'repeat-0', 'value': 4}).status_code == 200
    assert env['client'].get(f'{base}/export').json()['ratings']['repeat-0']['value'] == 4
    assert stored(env, current['id'])['scoreSnapshot'] == frozen


def test_legacy_results_remain_explicitly_recomputed_without_backfilling_historical_data(env, monkeypatch):
    current = begin(env, start(env, scope='reading', questionIds=['r1q1']))
    current = action(env, current, 'answer', answer='B').json()
    ended = action(env, current, 'next').json()
    store = env['app'].state.store
    with store.transaction() as db:
        legacy = store.get(db, ended['id'])
        legacy.pop('scoreSnapshot')
        store.save(db, legacy)
        original = db.execute('SELECT body FROM sessions WHERE id=?', (ended['id'],)).fetchone()['body']
    monkeypatch.setattr(engine, 'grade', lambda question, answer: {'correct': 1, 'total': 1})
    result = env['client'].get(f"/api/sessions/{ended['id']}/review").json()
    assert result['scoreSnapshot'] is None
    assert result['session']['scoreSnapshotStatus'] == 'legacy-recomputed'
    assert result['score']['correct'] == 1 and result['sections'][0]['modules'][0]['questions'][0]['grade']['correct'] == 1
    assert 'Legacy session' in result['score']['notice']
    env['client'].get(f"/api/sessions/{ended['id']}/export")
    env['client'].get('/api/sessions')
    env['client'].get('/api/mistakes?status=all')
    with store.transaction() as db:
        assert db.execute('SELECT body FROM sessions WHERE id=?', (ended['id'],)).fetchone()['body'] == original
