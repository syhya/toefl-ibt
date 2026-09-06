"""Observed writing expiry acknowledgement, without reopening response time."""
import pytest
import json
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.engine import RULES_VERSION
from backend.tests.test_api import env, start, begin, action


def test_runtime_rule_version_matches_the_published_rule_document():
    published = json.loads((Path(__file__).resolve().parents[2] / 'shared/rules.json').read_text())
    assert RULES_VERSION == published['rulesVersion']


def writing_at(env, qid, mode='strict'):
    current = begin(env, start(env, scope='writing', mode=mode))
    while current['question']['id'] != qid:
        current = begin(env, action(env, current, 'next').json())
    return current


@pytest.mark.parametrize('mode', ['strict', 'practice'])
@pytest.mark.parametrize('qid', ['email', 'discussion'])
def test_deadline_preserves_readonly_question_and_rejects_every_edit(env, mode, qid):
    a = writing_at(env, qid, mode)
    a = action(env, a, 'answer', answer='Saved before the deadline.').json()
    deadline = a['deadline']
    env['clock'][0] = deadline
    late = action(env, a, 'answer', answer='Too late')
    assert late.status_code == 409
    frozen = late.json()['session']
    assert frozen['phase'] == 'expired' and frozen['status'] == 'active'
    assert frozen['question']['id'] == qid
    assert frozen['answer'] == 'Saved before the deadline.'
    assert frozen['deadline'] == deadline and frozen['remainingSeconds'] == 0
    assert set(frozen['allowedActions']) == {'continue', 'finish', 'interrupt'}
    for name in ['answer', 'next', 'back', 'jump', 'begin', 'pause', 'resume', 'replay', 'flag']:
        assert action(env, frozen, name, answer='Still too late', index=0).status_code == 409
    env['clock'][0] += 60_000
    current = env['client'].get(f"/api/sessions/{a['id']}").json()
    assert current['phase'] == 'expired' and current['answer'] == frozen['answer']
    assert current['deadline'] == deadline


def test_continue_advances_once_and_next_task_gets_its_full_begin_window(env):
    a = writing_at(env, 'email')
    env['clock'][0] = a['deadline'] + 300_000
    frozen = env['client'].get(f"/api/sessions/{a['id']}").json()
    assert frozen['phase'] == 'expired'
    payload = {'action': 'continue', 'questionId': 'email', 'requestId': 'one-expiry-acknowledgement'}
    route = f"/api/sessions/{a['id']}/events"
    waiting = env['client'].post(route, json=payload).json()
    assert waiting['phase'] == 'directions' and waiting['question'] is None
    assert waiting['deadline'] is None
    duplicate = env['client'].post(route, json=payload).json()
    assert duplicate['stageIndex'] == waiting['stageIndex'] and duplicate['phase'] == 'directions'
    assert action(env, waiting, 'continue', questionId='email').status_code == 409
    env['clock'][0] += 90_000
    next_task = begin(env, waiting)
    assert next_task['question']['id'] == 'discussion'
    assert next_task['deadline'] == env['clock'][0] + 600_000


def test_restore_keeps_expired_state_and_final_score_freezes_after_continue(env):
    a = begin(env, start(env, scope='writing', questionIds=['discussion']))
    a = action(env, a, 'answer', answer='Retained response.').json()
    env['clock'][0] = a['deadline']
    env['client'].get(f"/api/sessions/{a['id']}")
    env['clock'][0] += 30_000
    with TestClient(create_app(env['root'], clock=lambda: env['clock'][0], testing=True)) as client:
        restored = client.get(f"/api/sessions/{a['id']}").json()
        assert restored['phase'] == 'expired' and restored['answer'] == 'Retained response.'
        assert restored['scoreSnapshotStatus'] == 'pending'
        ended = client.post(f"/api/sessions/{a['id']}/events", json={
            'action': 'continue', 'questionId': 'discussion', 'requestId': 'finish-after-restore',
        }).json()
        assert ended['status'] == 'completed' and ended['scoreSnapshotStatus'] == 'frozen'
        review = client.get(f"/api/sessions/{a['id']}/review").json()
        assert review['answers'] == {'discussion': 'Retained response.'}


def test_legacy_frozen_sessions_keep_their_previous_timeout_flow(env):
    a = begin(env, start(env, scope='writing', questionIds=['email', 'discussion']))
    store = env['app'].state.store
    with store.transaction() as db:
        legacy = store.get(db, a['id'])
        legacy.pop('writingExpiryAcknowledgement')
        legacy['rulesVersion'] = '2026-09-05-source-flow-v4'
        store.save(db, legacy)
    env['clock'][0] = a['deadline']
    waiting = env['client'].get(f"/api/sessions/{a['id']}").json()
    assert waiting['phase'] == 'directions' and waiting['question'] is None
    assert not waiting['writingExpiryAcknowledgement']
