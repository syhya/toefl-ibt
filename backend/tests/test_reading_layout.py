"""Source-bound layout fixes must not rewrite words, answers or frozen plans."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.reading_layout import layouts, normalized, project_reading_layout
from backend.tests.test_api import action, begin, start
from backend.tests.test_prepared_sources import prepared

ROOT = Path(__file__).resolve().parents[2]


def sample_question(qid):
    exam = json.loads((ROOT / 'examples/ets-practice-test-1/exam.json').read_text())
    return next(q for s in exam['sections'] for m in s['modules'] for q in m['questions'] if q['id'] == qid)


def message(q):
    return next(b for b in q['stemBlocks'] if b['type'] == 'message')


@pytest.mark.parametrize('qid', ['student-1-r2-11', 'student-1-r2-12'])
def test_workshop_email_restores_the_four_source_paragraphs_without_mutating_content(qid):
    q = sample_question(qid)
    original = deepcopy(q)
    restored = project_reading_layout(q)
    paragraphs = message(restored)['paragraphs']
    assert len(paragraphs) == 4
    assert paragraphs[0] == 'Dear Ms. Edwards,'
    assert paragraphs[1].startswith('The reservation') and paragraphs[1].endswith('apron or smock.')
    assert paragraphs[2:] == ['Best regards,', 'Laura Bennett']
    assert normalized(' '.join(paragraphs)) == normalized(' '.join(message(q)['paragraphs']))
    assert q == original
    assert project_reading_layout(restored) == restored
    assert {k:v for k,v in restored.items() if k != 'stemBlocks'} == {k:v for k,v in q.items() if k != 'stemBlocks'}


def test_long_invitation_restores_body_paragraphs_and_a_single_line_break_in_signature():
    q = project_reading_layout(sample_question('student-1-r2-13'))
    paragraphs = message(q)['paragraphs']
    assert len(paragraphs) == 6
    assert [p.split(' ')[0] for p in paragraphs] == ['Dear', "We're", 'This', 'Bring', 'For', 'Warm']
    assert paragraphs[-1] == 'Warm regards,\nJohn Parker'


@pytest.mark.parametrize('mismatch', ['id', 'materialId', 'page', 'text'])
def test_layout_cannot_apply_to_a_different_edition_or_modified_text(mismatch):
    q = sample_question('student-1-r2-11')
    if mismatch == 'id': q['id'] = 'unreviewed-question'
    elif mismatch == 'text': message(q)['paragraphs'][0] += ' Additional text.'
    else: q['source'][mismatch] = 'different-source' if mismatch == 'materialId' else 999
    before = deepcopy(q)
    assert project_reading_layout(q) == before


def test_unreviewed_message_is_not_reformatted_by_greeting_or_signoff_heuristics():
    q = {'id':'unreviewed-email', 'stemBlocks':[{'type':'message', 'paragraphs':[
        'Dear Reader, this is one intentionally continuous passage. Best regards, An Example Writer']} ]}
    assert project_reading_layout(q) is q


def test_active_and_historical_review_use_the_same_layout_without_retiming(prepared):
    root, _, _ = prepared
    clock = [1_000_000]
    app = create_app(root, clock=lambda:clock[0], testing=True)
    with TestClient(app) as client:
        env = {'root':root,'app':app,'client':client,'clock':clock}
        current = begin(env, start(env, examId='student-1', scope='reading', questionIds=['student-1-r2-12']))
        current = action(env, current, 'answer', answer='C').json()
        with app.state.store.transaction() as db:
            saved = app.state.store.get(db, current['id'])
            saved['rulesVersion'] = '2026-09-05-client-expiry-v5'
            app.state.store.save(db, saved)
            frozen = deepcopy(saved)
        assert len(message(frozen['plan'][0]['questions'][0])['paragraphs']) == 1
        refreshed = client.get(f"/api/sessions/{current['id']}").json()
        assert message(refreshed['question'])['paragraphs'][-2:] == ['Best regards,', 'Laura Bennett']
        assert refreshed['answer'] == 'C' and refreshed['deadline'] == frozen['deadline']
        with app.state.store.transaction() as db:
            assert app.state.store.get(db, current['id']) == frozen
        assert action(env, refreshed, 'finish').status_code == 200
        review = client.get(f"/api/sessions/{current['id']}/review").json()
        q = review['sections'][0]['modules'][0]['questions'][0]
        assert message(q)['paragraphs'] == message(refreshed['question'])['paragraphs']
        assert q['grade']['correct'] == 1 and review['answers'][q['id']] == 'C'
        assert not (root / 'data').exists()


def test_all_available_audited_source_layouts_preserve_text_and_unrelated_fields():
    paths = list((ROOT / 'generated/exams').glob('*.json'))
    if not paths:
        pytest.skip('Optional private source collection is not installed')
    questions = {q['id']:q for path in paths for s in json.loads(path.read_text())['sections']
                 for m in s['modules'] for q in m['questions']}
    for qid, (source, layout) in layouts().items():
        if qid not in questions: continue
        q = questions[qid]; old = deepcopy(q)
        blocks = q.get('stemBlocks', [])
        index = source['blockIndex']
        # A re-reviewed source version can have different block boundaries or
        # wording. Old character spans must then be a no-op, not a forced edit.
        if (any(q.get('source', {}).get(k) != source[k] for k in ['materialId', 'page'])
                or index >= len(blocks)
                or blocks[index].get('type') != layout.get('blockType', 'message')):
            assert project_reading_layout(q) == old, qid
            continue
        def text(item):
            block = item['stemBlocks'][source['blockIndex']]
            return ' '.join(block['paragraphs']) if block['type'] == 'message' else block['text']
        before = normalized(text(q))
        if hashlib.sha256(before.encode()).hexdigest() != layout['textSha256']:
            assert project_reading_layout(q) == old, qid
            continue
        restored = project_reading_layout(q)
        expected = before[layout['runs'][0]['start']:]
        assert normalized(text(restored)) == expected, qid
        assert q == old
        assert {k:v for k,v in restored.items() if k != 'stemBlocks'} == {k:v for k,v in q.items() if k != 'stemBlocks'}
        if layout.get('omitRepeatedInstruction'):
            assert restored['stemBlocks'][source['blockIndex']-1] == q['stemBlocks'][source['blockIndex']-1]
        expected_paragraphs = []
        for run in layout['runs']:
            part = before[run['start']:run['end']]
            if run['breakBefore'] == 'line' and expected_paragraphs:
                expected_paragraphs[-1] += '\n' + part
            else:
                expected_paragraphs.append(part)
        block = restored['stemBlocks'][index]
        actual = block['paragraphs'] if block['type'] == 'message' else block['text'].split('\n\n')
        assert actual == expected_paragraphs, qid
