"""Strict-mode disclosure regression checks using isolated temporary fixtures only.

No requests are sent to the running 4173 app. No original/generated study
questions or user attempts are changed by these tests.
"""
import json

import pytest

from backend.tests.test_api import env, start, begin, action


@pytest.mark.parametrize('mode', ['practice', 'strict'])
def test_sentence_distractor_metadata_is_available_only_in_review(env, mode):
    path = env['root'] / 'generated/exams/exam.json'
    exam = json.loads(path.read_text())
    question = next(section for section in exam['sections'] if section['id'] == 'writing')['modules'][0]['questions'][0]
    question['extraTokens'] = ['extra']
    path.write_text(json.dumps(exam))
    catalog = env['root'] / 'generated/catalog.json'
    catalog.write_text(catalog.read_text() + ' ')

    opened = begin(env, start(env, mode=mode, scope='writing', allowPracticeAids=mode == 'practice'))
    assert opened['question']['tokens'] == ['the', 'the', 'extra']
    assert 'extraTokens' not in opened['question'], 'Identifying a distractor discloses part of the solution.'
    if mode == 'practice':
        feedback = env['client'].get(f"/api/sessions/{opened['id']}/feedback?questionId=build").json()
        assert feedback['question']['extraTokens'] == ['extra']
    action(env, opened, 'finish')
    review = env['client'].get(f"/api/sessions/{opened['id']}/review").json()
    assert review['sections'][0]['modules'][0]['questions'][0]['extraTokens'] == ['extra']


def test_other_attempt_scores_are_hidden_during_strict(env):
    practice = begin(env, start(env, mode='practice', scope='reading', questionIds=['r1q1']))
    practice = action(env, practice, 'answer', answer='A').json()
    practice = action(env, practice, 'finish').json()
    strict = begin(env, start(env, mode='strict', scope='reading'))
    history = env['client'].get('/api/sessions')
    assert history.status_code in {200, 403}
    if history.status_code == 200:
        assert all(row.get('score') is None for row in history.json()['sessions']), 'Aggregate one-question scores form an answer oracle.'
    assert env['client'].get(f"/api/sessions/{strict['id']}").json()['status'] == 'active'


def test_parallel_practice_cannot_reveal_new_question_content(env):
    begin(env, start(env, mode='strict', scope='reading'))
    response = env['client'].post('/api/sessions', json={'examId': 'exam', 'mode': 'practice', 'scope': 'reading', 'questionIds': ['r1q1']})
    if response.status_code in {403, 409}:
        return
    assert response.status_code == 200
    opened = action(env, response.json(), 'begin')
    assert opened.status_code in {403, 409}, 'A parallel practice session can expose and answer strict-session questions.'


def test_preexisting_practice_audio_cannot_bypass_strict_single_play(env):
    practice = begin(env, start(env, mode='practice', scope='listening'))
    url = practice['question']['audio']['url']
    assert env['client'].get(url).status_code == 200
    begin(env, start(env, mode='strict', scope='reading'))
    assert env['client'].get(url).status_code in {403, 409}, 'An old practice asset URL still replays the original prompt during strict mode.'


def test_preexisting_practice_cannot_fetch_or_advance_future_materials(env):
    practice = begin(env, start(env, mode='practice', scope='reading', questionIds=['r2q1']))
    begin(env, start(env, mode='strict', scope='reading'))
    response = env['client'].get(f"/api/sessions/{practice['id']}")
    assert response.status_code in {403, 409} or response.json().get('question') is None
    assert action(env, practice, 'answer', answer='B').status_code in {403, 409}


def test_validation_and_reference_surfaces_remain_locked(env):
    public = env['client'].get('/api/catalog').json()
    library = public['materials'][0]['url']
    begin(env, start(env, mode='strict', scope='reading'))
    for path in ['/api/validation', '/api/questions', library]:
        assert env['client'].get(path).status_code == 403
    for path in ['/generated/audit.json', '/generated/question-bank.json', '/generated/exams/exam.json', '/materials/source.pdf']:
        assert env['client'].get(path).status_code == 404
    for path in ['/api/catalog', '/api/exams/exam', '/api/rules']:
        response = env['client'].get(path)
        assert response.status_code == 200
        assert not any(secret in response.text for secret in ['SECRET_ANSWER', 'SECRET_EXPLANATION', 'SECRET_TRANSCRIPT'])


def test_legacy_reading_stem_or_passage_is_review_only_and_not_listed(env):
    # New sessions must never fall back to the old full-question/passage crop.
    path = env['root'] / 'generated/exams/exam.json'
    exam = json.loads(path.read_text())
    question = exam['sections'][0]['modules'][0]['questions'][0]
    question.pop('presentationSchema')
    question.pop('structuredContentStatus')
    question.pop('stemBlocks')
    question['assets'][0]['role'] = 'passage'
    path.write_text(json.dumps(exam))
    catalog = env['root'] / 'generated/catalog.json'
    catalog.write_text(catalog.read_text() + ' ')
    strict = env['client'].post('/api/sessions', json={'examId': 'exam', 'mode': 'strict', 'scope': 'reading'})
    assert strict.status_code == 422 and 'unavailable prompts' in strict.json()['error']
    opened = begin(env, start(env, mode='practice', scope='reading'))
    assert opened['question']['id'] == 'r1q2', 'A pure-text legacy question remains usable.'
    legacy_asset = env['app'].state.catalog.register('/assets/stem.jpg')
    assert env['client'].get(f"/api/sessions/{opened['id']}/assets/{legacy_asset}").status_code == 403
    assert env['client'].get('/api/questions?q=r1q1').json()['total'] == 0
    summary = next(item for item in env['client'].get('/api/catalog').json()['exams'] if item['id'] == 'exam')
    reading = next(section for section in summary['sections'] if section['id'] == 'reading')
    assert summary['legacyImageReviewOnlyCount'] == reading['legacyImageReviewOnlyCount'] == 1
    assert summary['strictEligible'] is False
    assert summary['scopedEligibility']['reading'] is False
    assert summary['scopedEligibility']['listening'] is True


def test_frozen_legacy_image_session_can_finish_and_review_without_active_image_access(env):
    opened = begin(env, start(env, mode='practice', scope='reading'))
    store = env['app'].state.store
    with store.transaction() as db:
        saved = store.get(db, opened['id'])
        frozen = saved['plan'][0]['questions'][0]
        frozen.pop('presentationSchema')
        frozen.pop('structuredContentStatus')
        frozen.pop('stemBlocks')
        frozen['assets'][0]['role'] = 'stem'
        store.save(db, saved)
    restored = env['client'].get(f"/api/sessions/{opened['id']}").json()
    assert restored['question']['id'] == 'r1q1'
    assert restored['question']['assets'] == []
    asset_id = env['app'].state.catalog.register('/assets/stem.jpg')
    assert env['client'].get(f"/api/sessions/{opened['id']}/assets/{asset_id}").status_code == 403
    ended = action(env, restored, 'finish')
    assert ended.status_code == 200
    review = env['client'].get(f"/api/sessions/{opened['id']}/review").json()
    legacy = review['sections'][0]['modules'][0]['questions'][0]
    assert legacy['assets'][0]['role'] == 'stem'
    assert env['client'].get(legacy['assets'][0]['url']).status_code == 200
