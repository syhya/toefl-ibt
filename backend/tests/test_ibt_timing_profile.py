"""The current iBT profile must survive legacy material clocks/browser presets."""
from copy import deepcopy
import json

import pytest

from backend.engine import DEFAULT_TIMING, IBT_FAMILIES, make_plan
from backend.tests.test_api import env, start, begin, action
from backend.tests.test_timing_audit import rewrite_exam


def formal_exam(env, family='pack'):
    def update(exam):
        exam['family'] = family
        for module, seconds in zip(exam['sections'][0]['modules'], (690, 540)):
            module['durationSeconds'] = seconds
    rewrite_exam(env, update)


@pytest.mark.parametrize('family', sorted(IBT_FAMILIES))
def test_all_ibt_families_use_thirty_minutes_despite_old_material_clocks(env, family):
    formal_exam(env, family)
    path = env['root'] / 'generated/exams/exam.json'
    source_before = path.read_bytes()
    current = start(env, mode='strict', scope='reading')
    assert current['stage']['seconds'] == 900
    assert current['stage']['timingBasis'] == 'local'  # Equal split is not an ETS deadline.
    current = begin(env, current)
    assert current['remainingSeconds'] == 900
    deadline = current['deadline']
    env['clock'][0] += 30_000
    current = action(env, current, 'next').json()
    current = action(env, current, 'back').json()
    assert current['deadline'] == deadline
    assert current['remainingSeconds'] == 870
    env['clock'][0] = deadline
    current = env['client'].get(f"/api/sessions/{current['id']}").json()
    assert current['phase'] == 'directions' and current['deadline'] is None
    env['clock'][0] += 60_000
    current = begin(env, current)
    assert current['remainingSeconds'] == 900
    assert path.read_bytes() == source_before


def test_strict_ibt_ignores_custom_browser_clock_values_but_freezes_actual_profile(env):
    formal_exam(env)
    custom = {**DEFAULT_TIMING, 'readingCommon': 5, 'readingSecond': 6,
              'listeningResponse': 7, 'listeningAcademic': 8, 'buildSentence': 9,
              'email': 10, 'academicDiscussion': 11, 'interview': 12,
              'repeat': [12] * 7}
    current = start(env, mode='strict', scope='all', timing=custom)
    store = env['app'].state.store
    with store.transaction() as db:
        frozen = store.get(db, current['id'])
    assert frozen['timing'] == DEFAULT_TIMING
    assert [s['seconds'] for s in frozen['plan'] if s['section'] == 'reading'] == [900, 900]
    assert [s['seconds'] for s in frozen['plan'] if s['section'] == 'writing'] == [360, 420, 600]
    listening = next(s for s in frozen['plan'] if s['section'] == 'listening')
    assert listening['responseWindows'] == [20] * 3
    speaking = [s for s in frozen['plan'] if s['section'] == 'speaking']
    assert [s['responseWindows'] for s in speaking] == [DEFAULT_TIMING['repeat'], [45] * 4]


def test_guided_ibt_honors_custom_reading_instead_of_legacy_source_override(env):
    formal_exam(env)
    current = begin(env, start(env, scope='reading', timing={'readingCommon': 1200, 'readingSecond': 600}))
    assert current['remainingSeconds'] == 1200
    env['clock'][0] = current['deadline']
    current = env['client'].get(f"/api/sessions/{current['id']}").json()
    assert current['stage']['seconds'] == 600


def test_filtered_formal_reading_retains_full_original_module_budget(env):
    formal_exam(env)
    current = start(env, scope='reading', questionIds=['r1q2'])
    assert current['stage']['partialModule'] is True
    assert current['stage']['seconds'] == 900


def test_v8_formal_session_keeps_its_frozen_source_clocks(env):
    old = start(env, scope='reading')
    store = env['app'].state.store
    with store.transaction() as db:
        saved = store.get(db, old['id'])
        saved['rulesVersion'] = '2026-09-26-balanced-reading-v8'
        saved['plan'][0]['seconds'] = 690
        saved['plan'][1]['seconds'] = 540
        store.save(db, saved)
        old_plan = deepcopy(saved['plan'])
    formal_exam(env)
    old = begin(env, old)
    assert old['remainingSeconds'] == 690
    env['clock'][0] += 10_000
    refreshed = env['client'].get(f"/api/sessions/{old['id']}").json()
    assert refreshed['remainingSeconds'] == 680
    assert refreshed['rulesVersion'] == '2026-09-26-balanced-reading-v8'
    with store.transaction() as db:
        assert store.get(db, old['id'])['plan'] == old_plan


def test_supplemental_family_does_not_acquire_ibt_timers(env):
    exam = json.loads((env['root'] / 'generated/exams/exam.json').read_text())
    exam.update(family='pack', supplemental=True, timingPolicy='untimed')
    plan = make_plan(exam, {'mode': 'practice'}, DEFAULT_TIMING)
    assert all(s['timer'] == 'untimed' for s in plan)


def test_formal_audio_still_precedes_the_entire_answer_window(env):
    formal_exam(env)
    current = begin(env, start(env, mode='strict', scope='listening', timing={'listeningResponse': 6}))
    assert current['phase'] == 'audio' and current['deadline'] is None
    env['clock'][0] += 2000
    current = action(env, current, 'audio-ended').json()
    assert current['remainingSeconds'] == 20
    assert current['deadline'] == env['clock'][0] + 20_000
    env['clock'][0] = current['deadline']
    current = env['client'].get(f"/api/sessions/{current['id']}").json()
    assert current['question']['id'] == 'l1q2'
    assert current['remainingSeconds'] == 20  # The shared original audio is not repeated.
