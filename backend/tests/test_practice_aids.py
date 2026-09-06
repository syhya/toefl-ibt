"""Practice aids require a genuine subset and a saved, explicit pre-start opt-in."""
import json

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.tests.test_api import env, start, begin, action


def stored(env, session_id):
    with env['app'].state.store.transaction() as db:
        return env['app'].state.store.get(db, session_id)


def modify(env, session_id, change):
    store = env['app'].state.store
    with store.transaction() as db:
        saved = store.get(db, session_id)
        change(saved)
        store.save(db, saved)


def feedback(env, current, question_id=None):
    return env['client'].get(f"/api/sessions/{current['id']}/feedback",
                              params={'questionId': question_id or current['question']['id']})


def test_default_off_blocks_feedback_and_active_review_sources_but_keeps_question_assets(env):
    current = begin(env, start(env, scope='reading'))
    assert current['allowPracticeAids'] is False
    assert stored(env, current['id'])['practiceAidsEligible'] is True
    current = action(env, current, 'answer', answer='A').json()
    asset_id = current['question']['assets'][0]['assetId']
    source_id = env['app'].state.catalog.register('/materials/source.pdf')
    before = stored(env, current['id'])
    assert feedback(env, current).status_code == 403
    for handle in [asset_id, source_id]:
        blocked = env['client'].get(f"/api/sessions/{current['id']}/review-assets/{handle}")
        assert blocked.status_code == 403 and 'SECRET_ANSWER' not in blocked.text
    assert env['client'].get(current['question']['assets'][0]['url']).status_code == 200
    assert stored(env, current['id']) == before
    action(env, current, 'finish')
    review = env['client'].get(f"/api/sessions/{current['id']}/review")
    assert review.status_code == 200 and 'SECRET_ANSWER' in review.text
    assert env['client'].get(f"/api/sessions/{current['id']}/review-assets/{source_id}").status_code == 200


def test_explicit_specialized_opt_in_allows_visited_feedback_and_review_assets(env):
    current = begin(env, start(env, scope='reading', allowPracticeAids=True))
    assert current['allowPracticeAids'] is True
    result = feedback(env, current)
    assert result.status_code == 200
    assert result.json()['question']['answer'] == 'A'
    assert result.json()['explanation']
    assert feedback(env, current, 'r2q1').status_code == 403
    source = result.json()['question']['source']['url']
    assert env['client'].get(source).status_code == 200


def listening_response(env, **options):
    current = begin(env, start(env, scope='listening', **options))
    assert env['client'].get(current['question']['audio']['url']).status_code == 200
    env['clock'][0] += 2000
    current = action(env, current, 'audio-ended').json()
    return action(env, current, 'answer', answer='A').json()


def test_default_off_disallows_direct_replay_without_changing_answers_or_deadline(env):
    current = listening_response(env)
    before = stored(env, current['id'])
    assert 'replay' not in current['allowedActions']
    assert action(env, current, 'replay', allowPracticeAids=True, practiceAidsEligible=True).status_code == 409
    assert stored(env, current['id']) == before
    assert feedback(env, current).status_code == 403
    audio_id = env['app'].state.catalog.register('/materials/shared.ogg')
    assert env['client'].get(f"/api/sessions/{current['id']}/assets/{audio_id}").status_code == 403
    assert env['client'].get(f"/api/sessions/{current['id']}/review-assets/{audio_id}").status_code == 403


def test_explicit_opt_in_keeps_existing_replay_behavior_and_saved_answers(env):
    current = listening_response(env, allowPracticeAids=True)
    assert 'replay' in current['allowedActions']
    answers = stored(env, current['id'])['answers']
    response = action(env, current, 'replay')
    assert response.status_code == 200
    replayed = response.json()
    assert replayed['phase'] == 'audio' and replayed['allowPracticeAids'] is True
    assert stored(env, current['id'])['answers'] == answers
    assert env['client'].get(replayed['question']['audio']['url']).status_code == 200


@pytest.mark.parametrize('value', [None, 0, 1, 'true', 'false', [], {}])
def test_opt_in_is_type_checked_without_creating_a_session(env, value):
    response = env['client'].post('/api/sessions', json={
        'examId': 'exam', 'mode': 'practice', 'scope': 'reading', 'allowPracticeAids': value})
    assert response.status_code == 422
    with env['app'].state.store.transaction() as db:
        assert db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 0


@pytest.mark.parametrize('options', [
    {'mode': 'strict', 'scope': 'reading'},
    {'mode': 'practice', 'scope': 'all'},
    {'mode': 'practice'},
])
def test_strict_and_full_exam_requests_cannot_opt_in(env, options):
    response = env['client'].post('/api/sessions', json={
        'examId': 'exam', **options, 'allowPracticeAids': True, 'practiceAidsEligible': True})
    assert response.status_code == 422


@pytest.mark.parametrize('filter_kind', ['questionIds', 'types'])
def test_selecting_every_question_or_every_type_cannot_disguise_a_full_exam(env, filter_kind):
    exam = json.loads((env['root'] / 'generated/exams/exam.json').read_text())
    questions = [q for s in exam['sections'] for m in s['modules'] for q in m['questions']]
    selection = [q['id'] for q in questions] if filter_kind == 'questionIds' else sorted({q['type'] for q in questions})
    response = env['client'].post('/api/sessions', json={
        'examId': 'exam', 'mode': 'practice', 'scope': 'all', filter_kind: selection, 'allowPracticeAids': True})
    assert response.status_code == 422
    # The same full selection remains usable as an ordinary unassisted exam.
    current = start(env, scope='all', **{filter_kind: selection})
    assert current['allowPracticeAids'] is False
    assert stored(env, current['id'])['practiceAidsEligible'] is False


@pytest.mark.parametrize('selection', [{'questionIds': ['r1q1']}, {'taskType': 'choice'},
                                      {'types': ['build_sentence']}, {'questionTypes': ['email']}])
def test_an_actual_subset_can_opt_in_even_with_all_section_scope(env, selection):
    current = begin(env, start(env, scope='all', allowPracticeAids=True, **selection))
    assert current['allowPracticeAids'] is True
    assert stored(env, current['id'])['practiceAidsEligible'] is True
    assert feedback(env, current).status_code == 200


def test_adaptive_subset_eligibility_compares_all_pending_branches(env):
    all_ids = [f'router-{index}' for index in range(10)] + ['lower-question', 'upper-question']
    options = {'examId': 'adaptive', 'mode': 'practice', 'scope': 'all', 'routeMode': 'adaptive',
               'questionIds': all_ids, 'allowPracticeAids': True}
    assert env['client'].post('/api/sessions', json=options).status_code == 422
    subset = env['client'].post('/api/sessions', json={**options, 'questionIds': all_ids[1:]})
    assert subset.status_code == 200, subset.text
    assert subset.json()['allowPracticeAids'] is True


@pytest.mark.parametrize('missing', ['allowPracticeAids', 'practiceAidsEligible', 'both'])
def test_legacy_or_partial_permission_records_remain_off_after_restart(env, missing):
    current = listening_response(env, allowPracticeAids=True)
    def drop_marker(session):
        for key in ['allowPracticeAids', 'practiceAidsEligible'] if missing == 'both' else [missing]:
            session.pop(key, None)
    modify(env, current['id'], drop_marker)
    app = create_app(env['root'], clock=lambda: env['clock'][0], testing=True)
    with TestClient(app) as client:
        restored = client.get(f"/api/sessions/{current['id']}").json()
        assert restored['allowPracticeAids'] is False and 'replay' not in restored['allowedActions']
        assert client.get(f"/api/sessions/{current['id']}/feedback?questionId=l1q1").status_code == 403
    assert action(env, current, 'replay').status_code == 409


def test_saved_opt_in_survives_restart_and_event_payloads_cannot_enable_it(env):
    enabled = begin(env, start(env, scope='reading', allowPracticeAids=True))
    disabled = begin(env, start(env, scope='reading'))
    event = action(env, disabled, 'answer', answer='A', allowPracticeAids=True, practiceAidsEligible=True)
    assert event.status_code == 200 and event.json()['allowPracticeAids'] is False
    assert stored(env, disabled['id'])['allowPracticeAids'] is False
    app = create_app(env['root'], clock=lambda: env['clock'][0], testing=True)
    with TestClient(app) as client:
        assert client.get(f"/api/sessions/{enabled['id']}").json()['allowPracticeAids'] is True
        assert client.get(f"/api/sessions/{enabled['id']}/feedback?questionId=r1q1").status_code == 200
        assert client.get(f"/api/sessions/{disabled['id']}/feedback?questionId=r1q1").status_code == 403


@pytest.mark.parametrize('primary', ['question', 'stage'])
def test_default_off_untimed_practice_keeps_its_primary_audio_but_hides_optional_transcript(env, primary):
    path = env['root'] / 'generated/exams/exam.json'
    exam = json.loads(path.read_text())
    exam.update(supplemental=True, timingPolicy='untimed')
    module = exam['sections'][1]['modules'][0]
    first = module['questions'][0]
    first.update(transcript='Optional answer-like transcript.', displayTranscriptDuringPractice=True,
                 prompt='Required source prompt remains available.')
    if primary == 'stage':
        module['practiceAudio'] = first['audio']
        for question in module['questions']:
            question.pop('audio', None)
    path.write_text(json.dumps(exam))
    catalog = env['root'] / 'generated/catalog.json'
    catalog.write_text(catalog.read_text() + ' ')
    current = begin(env, start(env, scope='listening'))
    assert current['allowPracticeAids'] is False and current['stage']['timer'] == 'untimed'
    assert 'transcript' not in current['question'] and 'displayTranscriptDuringPractice' not in current['question']
    assert current['question']['prompt'] == 'Required source prompt remains available.'
    clips = current['question']['practiceMediaSequence'] if primary == 'question' else current['stage']['practiceAudio']
    assert len(clips) == 1
    assert env['client'].get(clips[0]['url'], headers={'Range': 'bytes=0-1'}).status_code == 206
    assert feedback(env, current).status_code == 403


def test_required_reading_passage_remains_visible_without_optional_transcript_preview(env):
    path = env['root'] / 'generated/exams/exam.json'
    exam = json.loads(path.read_text())
    exam.update(supplemental=True, timingPolicy='untimed')
    question = exam['sections'][0]['modules'][0]['questions'][0]
    question.update(passage='Required reading passage.', transcript='Optional transcript preview.',
                    displayTranscriptDuringPractice=True)
    path.write_text(json.dumps(exam))
    catalog = env['root'] / 'generated/catalog.json'
    catalog.write_text(catalog.read_text() + ' ')
    current = begin(env, start(env, scope='reading'))
    assert current['question']['passage'] == 'Required reading passage.'
    assert 'transcript' not in current['question']


def test_opt_in_does_not_bypass_another_active_strict_session(env):
    practice = begin(env, start(env, scope='reading', allowPracticeAids=True))
    source_id = env['app'].state.catalog.register('/materials/source.pdf')
    begin(env, start(env, mode='strict', scope='listening'))
    assert feedback(env, practice).status_code == 403
    assert env['client'].get(f"/api/sessions/{practice['id']}/review-assets/{source_id}").status_code == 403


def test_audio_pause_is_hidden_and_rejected_without_aids_without_mutating_session(env):
    current = begin(env, start(env, scope='listening'))
    assert current['phase'] == 'audio' and 'pause' not in current['allowedActions']
    before = stored(env, current['id'])
    response = action(env, current, 'pause')
    assert response.status_code == 409
    assert response.json()['error'] == 'Pausing audio requires practice aids enabled before starting.'
    assert stored(env, current['id']) == before
    assert env['client'].get(current['question']['audio']['url']).status_code == 200


def test_response_pause_remains_available_without_aids(env):
    current = listening_response(env)
    assert 'pause' in current['allowedActions']
    answers = stored(env, current['id'])['answers']
    response = action(env, current, 'pause')
    assert response.status_code == 200 and response.json()['phase'] == 'paused'
    resumed = action(env, response.json(), 'resume')
    assert resumed.status_code == 200 and resumed.json()['phase'] == 'response'
    assert stored(env, current['id'])['answers'] == answers


def test_opted_in_audio_pause_preserves_existing_behavior(env):
    current = begin(env, start(env, scope='listening', allowPracticeAids=True))
    assert 'pause' in current['allowedActions']
    paused = action(env, current, 'pause')
    assert paused.status_code == 200 and paused.json()['phase'] == 'paused'
    env['clock'][0] += 1000
    resumed = action(env, paused.json(), 'resume')
    assert resumed.status_code == 200 and resumed.json()['phase'] == 'audio'
    assert 'pause' in resumed.json()['allowedActions']


def test_pre_policy_paused_audio_can_resume_once_but_cannot_pause_again(env):
    current = begin(env, start(env, scope='listening', allowPracticeAids=True))
    paused = action(env, current, 'pause').json()
    modify(env, current['id'], lambda session: [session.pop(key, None) for key in
                                               ['allowPracticeAids', 'practiceAidsEligible']])
    view = env['client'].get(f"/api/sessions/{current['id']}").json()
    assert view['allowPracticeAids'] is False and 'resume' in view['allowedActions']
    resumed = action(env, paused, 'resume')
    assert resumed.status_code == 200 and resumed.json()['phase'] == 'audio'
    assert 'pause' not in resumed.json()['allowedActions']
    before = stored(env, current['id'])
    assert action(env, resumed.json(), 'pause').status_code == 409
    assert stored(env, current['id']) == before
