"""Mistake history uses isolated source snapshots and never writes to real attempts."""
import json

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.tests.test_api import env, start, begin, action


MISSING = object()


def attempt(env, question_id='r1q1', answer='B', scope='reading', finish='completed'):
    env['clock'][0] += 100
    opened = begin(env, start(env, mode='practice', scope=scope, questionIds=[question_id]))
    if opened['phase'] == 'audio':
        env['clock'][0] += 2000
        opened = action(env, opened, 'audio-ended').json()
    if answer is not MISSING:
        response = action(env, opened, 'answer', answer=answer)
        assert response.status_code == 200, response.text
        opened = response.json()
    if finish == 'active':
        return opened
    ended = action(env, opened, 'next' if finish == 'completed' else 'finish').json()
    assert ended['status'] == finish
    return ended


def edit_exam(env, change):
    path = env['root'] / 'generated/exams/exam.json'
    exam = json.loads(path.read_text())
    change(exam)
    path.write_text(json.dumps(exam))
    catalog = env['root'] / 'generated/catalog.json'
    catalog.write_text(catalog.read_text() + ' ')


def rows(env, **query):
    result = env['client'].get('/api/mistakes', params=query)
    assert result.status_code == 200, result.text
    return result.json()


def test_mistakes_persist_across_restarts_and_later_correct_answers_mark_mastered(env):
    assert rows(env)['summary'] == {'total': 0, 'needsReview': 0, 'mastered': 0, 'attempts': 0}
    attempt(env, answer='A')
    assert rows(env)['items'] == [], 'Correct-only questions are not mistakes.'
    first_wrong = attempt(env, answer='B')
    second_wrong = attempt(env, answer='B', finish='abandoned')
    current = rows(env)
    assert len(current['items']) == 1
    row = current['items'][0]
    assert row['questionId'] == 'r1q1' and row['examId'] == 'exam'
    assert row['attempts'] == 3 and row['wrongAttempts'] == 2
    assert row['lastGrade'] == {'correct': 0, 'total': 1}
    assert row['lastSessionId'] == second_wrong['id'] and row['available'] is True
    assert row['unavailableReason'] is None and row['status'] == 'needs_review'
    assert row['sourcePage'] == 1
    encoded = json.dumps(current)
    for private in ['SECRET_ANSWER', 'SECRET_TRANSCRIPT', 'SECRET_EXPLANATION', 'choices', 'stemBlocks', 'assets']:
        assert private not in encoded
    assert 'answer' not in row and 'answers' not in row and 'prompt' not in row
    assert row['title'] == 'Multiple Choice'
    fixed = attempt(env, answer='A')
    assert rows(env)['items'] == []
    mastered = rows(env, status='mastered')['items'][0]
    assert mastered['mistakeId'] == row['mistakeId']
    assert mastered['attempts'] == 4 and mastered['wrongAttempts'] == 2
    assert mastered['lastGrade'] == {'correct': 1, 'total': 1}
    assert mastered['lastSessionId'] == fixed['id'] and mastered['status'] == 'mastered'
    assert mastered['lastWrongSessionId'] == second_wrong['id']
    assert mastered['lastWrongAt'] == second_wrong['completedAt']
    assert rows(env)['summary'] == {'total': 1, 'needsReview': 0, 'mastered': 1, 'attempts': 4}
    # A delayed diagnostic on an older ended attempt is not a newer answer.
    env['clock'][0] += 10000
    assert action(env, first_wrong, 'interrupt', reason='late-connection-log').status_code == 200
    assert rows(env, status='all')['items'][0]['lastSessionId'] == fixed['id']
    restarted = create_app(env['root'], clock=lambda: env['clock'][0], testing=True)
    with TestClient(restarted) as client:
        restored = client.get('/api/mistakes?status=all').json()
        assert restored['items'][0] == mastered
    wrong_again = attempt(env, answer='B')
    reopened = rows(env)['items'][0]
    assert reopened['status'] == 'needs_review' and reopened['lastSessionId'] == wrong_again['id']
    assert reopened['attempts'] == 5 and reopened['wrongAttempts'] == 3


def test_active_blank_ungraded_and_conflicted_answers_do_not_become_mistakes(env):
    active = attempt(env, answer='B', finish='active')
    assert rows(env)['items'] == []
    # Keep this active practice outside the ended-history collection.
    attempt(env, question_id='r1q2', answer='')
    attempt(env, question_id='r1q2', answer=MISSING)
    attempt(env, question_id='email', answer='An essay is subjective.', scope='writing')
    edit_exam(env, lambda exam: exam['sections'][0]['modules'][1]['questions'][0].pop('answer'))
    attempt(env, question_id='r2q1', answer='No verified key')
    edit_exam(env, lambda exam: exam['sections'][0]['modules'][0]['questions'][1].update(
        auditStatus='answer-conflict', answerConflict={'status': 'needs-review'}))
    attempt(env, question_id='r1q2', answer='Not a resolved answer')
    assert rows(env)['summary']['total'] == 0
    assert env['client'].get(f"/api/sessions/{active['id']}").json()['status'] == 'active'


def test_partial_cloze_stays_one_original_question_and_unresolved_blanks_are_excluded(env):
    def add_cloze(exam):
        exam['sections'][0]['modules'][0]['questions'].append({
            'id': 'cloze-source', 'contentId': 'cloze-content', 'type': 'cloze', 'taskType': 'cloze',
            'number': 11, 'numberEnd': 13, 'prompt': 'Isolated cloze fixture',
            'blanks': [
                {'id': 'one', 'answer': 'one'}, {'id': 'two', 'answer': 'two'},
                {'id': 'conflicted', 'answer': 'SECRET_CONFLICT', 'answerConflict': {'status': 'needs-review'}},
            ],
        })
    edit_exam(env, add_cloze)
    attempt(env, question_id='cloze-source', answer={})
    attempt(env, question_id='cloze-source', answer={'conflicted': 'Only the unresolved blank was attempted'})
    assert rows(env)['items'] == []
    saved = attempt(env, question_id='cloze-source', answer={'one': 'one', 'two': 'wrong', 'conflicted': 'irrelevant'})
    item = rows(env)['items'][0]
    assert item['questionId'] == 'cloze-source' and item['title'] == 'Complete the Words · 11–13'
    assert item['lastGrade'] == {'correct': 1, 'total': 2}
    assert item['wrongAttempts'] == item['attempts'] == 1
    assert item['lastSessionId'] == saved['id']
    assert 'SECRET_CONFLICT' not in json.dumps(item) and 'blanks' not in item
    attempt(env, question_id='cloze-source', answer={'one': 'one', 'two': 'two', 'conflicted': 'unresolved'})
    assert rows(env, status='mastered')['items'][0]['lastGrade'] == {'correct': 2, 'total': 2}


def test_source_changes_keep_the_old_mistake_and_never_substitute_a_new_version(env):
    old = attempt(env, answer='B')
    original = rows(env)['items'][0]
    edit_exam(env, lambda exam: exam['sections'][0]['modules'][0]['questions'][0].update(
        contentId='new-question-version', prompt='A different verified source question.', answer='B'))
    attempt(env, answer='B')
    historical = rows(env)['items'][0]
    assert historical['mistakeId'] == original['mistakeId']
    assert historical['lastSessionId'] == old['id'] and historical['status'] == 'needs_review'
    assert historical['attempts'] == 1 and historical['lastGrade'] == {'correct': 0, 'total': 1}
    assert historical['available'] is False and historical['unavailableReason'] == 'source_changed'
    attempt(env, answer='A')
    both = rows(env, status='all')['items']
    assert len(both) == 2 and len({item['mistakeId'] for item in both}) == 2
    assert {item['available'] for item in both} == {True, False}
    edit_exam(env, lambda exam: exam['sections'][0]['modules'][0]['questions'].pop(0))
    assert all(not item['available'] and item['unavailableReason'] == 'source_missing' for item in rows(env, status='all')['items'])


def test_answer_key_correction_does_not_regrade_an_old_snapshot_or_hide_missing_sources(env):
    attempt(env, answer='B')
    edit_exam(env, lambda exam: exam['sections'][0]['modules'][0]['questions'][0].update(answer='B'))
    old = rows(env)['items'][0]
    assert old['lastGrade'] == {'correct': 0, 'total': 1}, 'Use the frozen original key, never the latest key.'
    assert old['available'] is False and old['unavailableReason'] == 'source_changed'
    edit_exam(env, lambda exam: exam['sections'][0]['modules'][0]['questions'][0].update(answer='A'))
    assert rows(env)['items'][0]['available'] is True
    (env['root'] / 'data/source.pdf').unlink()
    assert rows(env)['items'][0]['available'] is False


def test_mistake_filters_pagination_and_summary_do_not_return_other_question_content(env):
    attempt(env, question_id='r1q1', answer='B')
    attempt(env, question_id='r1q2', answer='wrong')
    attempt(env, question_id='build', answer={'tokenOrder': ['0', '2']}, scope='writing')
    attempt(env, question_id='r1q1', answer='A')
    result = rows(env, status='all', page=1, pageSize=1)
    assert result['total'] == 3 and len(result['items']) == 1
    assert result['summary'] == {'total': 3, 'needsReview': 2, 'mastered': 1, 'attempts': 4}
    assert rows(env, status='all', page=2, pageSize=1)['items'][0]['mistakeId'] != result['items'][0]['mistakeId']
    writing = rows(env, section='writing', q='Build a Sentence')
    assert len(writing['items']) == 1 and writing['items'][0]['questionId'] == 'build'
    assert writing['summary']['attempts'] == 1
    assert rows(env, section='speaking')['items'] == []
    assert rows(env, q='SECRET_ANSWER')['total'] == 0, 'Search only public metadata, not private solution text.'


@pytest.mark.parametrize('query', [{'section': 'invalid'}, {'status': 'wrong'}, {'page': 0}, {'pageSize': 101}, {'q': 'x' * 201}])
def test_mistake_query_validation(env, query):
    assert env['client'].get('/api/mistakes', params=query).status_code == 422


def test_strict_session_locks_all_mistake_views_and_read_only_queries_do_not_tick_sessions(env):
    attempt(env, answer='B')
    strict = begin(env, start(env, mode='strict', scope='reading'))
    store = env['app'].state.store
    with store.transaction() as db:
        before = list(db.execute('SELECT body FROM sessions ORDER BY rowid'))
        bodies = [row['body'] for row in before]
    env['clock'][0] += 100_000
    for query in [{}, {'status': 'all'}, {'section': 'reading', 'q': 'r1q1'}, {'pageSize': 1, 'page': 2}]:
        response = env['client'].get('/api/mistakes', params=query)
        assert response.status_code == 403
        assert 'items' not in response.json()
    with store.transaction() as db:
        assert [row['body'] for row in db.execute('SELECT body FROM sessions ORDER BY rowid')] == bodies
    action(env, strict, 'finish')
    assert rows(env)['total'] == 1
