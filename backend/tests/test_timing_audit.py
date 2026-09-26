"""Timing regression checks: source positions, mixed media, and frozen sessions."""
import json
from copy import deepcopy
from pathlib import Path

import pytest

from backend.engine import DEFAULT_TIMING, make_plan
from backend.tests.test_api import env, start, begin, action


def rewrite_exam(env, update):
    path = env['root'] / 'generated/exams/exam.json'
    exam = json.loads(path.read_text())
    update(exam)
    path.write_text(json.dumps(exam))
    catalog = env['root'] / 'generated/catalog.json'
    catalog.write_text(catalog.read_text() + ' ')


@pytest.mark.parametrize('index,expected', [(0, 8), (2, 10), (5, 12), (6, 12)])
def test_repeat_subset_keeps_original_response_window_after_audio(env, index, expected):
    current = start(env, scope='speaking', questionIds=[f'repeat-{index}'])
    assert current['stage']['responseWindows'] == [expected]
    assert current['stage']['timingBasis'] == 'local'
    env['clock'][0] += 60_000  # Directions consume no response time.
    current = begin(env, current)
    assert current['phase'] == 'audio' and current['deadline'] is None
    env['clock'][0] += 2000
    response = action(env, current, 'audio-ended').json()
    assert response['remainingSeconds'] == expected
    assert response['deadline'] == env['clock'][0] + expected * 1000
    env['clock'][0] = response['deadline']
    assert env['client'].get(f"/api/sessions/{current['id']}").json()['status'] == 'completed'


def test_repeat_filter_preserves_custom_sequence_and_explicit_source_window(env):
    def update(exam):
        repeat = exam['sections'][3]['modules'][0]['questions']
        repeat[0].update(referenceOnly=True)  # Unavailable items still occupy their source position.
        repeat[6]['responseSeconds'] = 11
    rewrite_exam(env, update)
    current = start(env, scope='speaking', questionIds=['repeat-5', 'repeat-6'],
                    timing={'repeat': [8, 9, 9, 10, 10, 11, 12]})
    assert current['stage']['responseWindows'] == [11, 11]


def test_unmatched_interview_does_not_untime_matched_following_questions(env):
    def update(exam):
        q = exam['sections'][3]['modules'][1]['questions'][0]
        q.pop('audio')
        q.update(referenceOnly=True, sourcePromptAvailable=True)
    rewrite_exam(env, update)
    current = begin(env, start(env, scope='speaking', taskType='interview'))
    assert current['stage']['timer'] == 'untimed' and current['deadline'] is None
    assert current['stage']['questionCount'] == 1
    env['clock'][0] += 120_000
    current = action(env, current, 'next').json()
    assert current['question']['id'] == 'interview-1'
    assert current['phase'] == 'audio' and current['deadline'] is None
    assert current['stage']['timer'] == 'item'
    assert current['stage']['timingBasis'] == 'official'
    assert current['stage']['responseWindows'] == [45, 45, 45]
    env['clock'][0] += 2000
    current = action(env, current, 'audio-ended').json()
    assert current['remainingSeconds'] == 45
    env['clock'][0] = current['deadline']
    current = env['client'].get(f"/api/sessions/{current['id']}").json()
    assert current['question']['id'] == 'interview-2' and current['phase'] == 'audio'
    assert env['client'].post('/api/sessions', json={
        'examId': 'exam', 'mode': 'strict', 'scope': 'speaking',
    }).status_code == 422


def test_shared_subset_reports_full_budget_without_restarting_on_navigation(env):
    selected = start(env, scope='reading', questionIds=['r1q2'])
    assert selected['stage']['partialModule'] is True
    assert selected['stage']['seconds'] == 10
    assert selected['stage']['timingBasis'] == 'source'
    current = begin(env, start(env, scope='reading'))
    deadline = current['deadline']
    env['clock'][0] += 3000
    current = action(env, current, 'next').json()
    current = action(env, current, 'back').json()
    assert current['deadline'] == deadline and current['remainingSeconds'] == 7


def test_old_frozen_untimed_plan_is_not_rebuilt_or_relabelled(env):
    saved = start(env, scope='speaking', taskType='interview')
    store = env['app'].state.store
    with store.transaction() as db:
        old = store.get(db, saved['id'])
        old['rulesVersion'] = '2026-09-05-client-expiry-v5'
        old['plan'][0]['timer'] = 'untimed'
        for key in ['timingBasis', 'responseWindows', 'partialModule']:
            old['plan'][0].pop(key)
        frozen = deepcopy(old['plan'])
        store.save(db, old)
    current = begin(env, saved)
    env['clock'][0] += 120_000
    current = env['client'].get(f"/api/sessions/{saved['id']}").json()
    assert current['rulesVersion'] == '2026-09-05-client-expiry-v5'
    assert current['deadline'] is None and 'timingBasis' not in current['stage']
    with store.transaction() as db:
        assert store.get(db, saved['id'])['plan'] == frozen


def test_bundled_sample_timing_evidence_and_windows():
    path = Path(__file__).resolve().parents[2] / 'examples/ets-practice-test-1/exam.json'
    exam = json.loads(path.read_text())
    plan = make_plan(exam, {'mode': 'practice', 'scope': 'all'}, DEFAULT_TIMING)
    reading = [s for s in plan if s['section'] == 'reading']
    assert [(s['seconds'], s['timingBasis']) for s in reading] == [(690, 'local'), (540, 'local')]
    listening = [s for s in plan if s['section'] == 'listening']
    assert [s['responseWindows'] for s in listening] == [[20] * 14 + [30] * 4, [20] * 12 + [30] * 4]
    assert all(s['timingBasis'] == 'local' for s in listening)
    writing = [s for s in plan if s['section'] == 'writing']
    assert [(s['seconds'], s['timingBasis']) for s in writing] == [(360, 'local'), (420, 'official'), (600, 'official')]
    assert [s['timer'] for s in plan if s['section'] == 'speaking'] == ['item', 'untimed', 'item']
    repeat = next(s for s in plan if s['id'] == 'speaking-listen_repeat')
    selected = make_plan(exam, {'mode': 'practice', 'questionIds': [repeat['questions'][-1]['id']]}, DEFAULT_TIMING)
    assert selected[0]['responseWindows'] == [12]
