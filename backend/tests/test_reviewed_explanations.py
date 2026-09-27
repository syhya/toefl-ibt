"""Bilingual rationales are checked against source/key identity, never used to score."""
from copy import deepcopy
import json
from pathlib import Path
import re

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.explanations import explain
from backend.reading_layout import project_reading_layout
from backend.reviewed_explanations import manifest
from backend.tests.test_api import action, begin, start
from backend.tests.test_prepared_sources import prepared
from scripts.attach_source_explanations import explanation_lines

ROOT = Path(__file__).resolve().parents[2]


def questions():
    exam = json.loads((ROOT / 'examples/ets-practice-test-1/exam.json').read_text())
    return {q['id']:q for s in exam['sections'] for m in s['modules'] for q in m['questions']}


def test_every_current_screen_has_a_bound_english_explanation_without_mutating_the_question():
    qs = questions()
    assert len(qs) == 79 and len(manifest()['questions']) == 80
    for q in qs.values():
        original = deepcopy(q)
        for displayed in [q, project_reading_layout(q)]:
            result = explain(displayed)
            assert result['origin'] == 'local_assistance' and result['reviewed'] is True, q['id']
            assert result['language'] == 'en' and 'Not ETS-authored' in result['label']
            english = {key:value for key,value in result.items() if key != 'translations'}
            assert not re.search('[\u3400-\u9fff]', json.dumps(english, ensure_ascii=False)), q['id']
        assert q == original
        if q['type'] == 'choice':
            assert result['text'].startswith(f"Correct answer: {q['answer']}. "), q['id']
            assert {e.split(':',1)[0] for e in result['evidence']} == {c['id'] for c in q['choices']} - {q['answer']}
        elif q['type'] == 'cloze':
            assert len(result['evidence']) == 10
            for blank, reason in zip(q['blanks'], result['evidence']):
                assert f"{blank['prefix']} + {blank['missingLetters']} = {blank['fullWord']}" in reason


def test_chinese_rationales_cover_both_editions_and_preserve_keys_blanks_and_reference_sentences():
    english, chinese = manifest(), manifest('zh-CN')
    assert chinese['questions'].keys() == english['questions'].keys()
    for qid, en in english['questions'].items():
        zh = chinese['questions'][qid]
        assert zh['fingerprint'] == en['fingerprint'], qid
        assert len(zh['evidence']) == len(en['evidence']), qid
        assert len(zh['warnings']) == len(en['warnings']), qid
        for line in [zh['text'], *zh['evidence'], *zh['warnings']]:
            assert re.search('[\u3400-\u9fff]', line), (qid, line)
        if en['text'].startswith('Reference sentence: '):
            assert zh['text'].splitlines()[0].removeprefix('参考句：') == en['text'].splitlines()[0].removeprefix('Reference sentence: ')
    for q in questions().values():
        result = explain(q)
        zh = result['translations']['zh-CN']
        assert zh['language'] == 'zh-CN' and zh['label'] == '校核解析 · 非 ETS 官方编写'
        if q['type'] == 'choice':
            assert zh['text'].startswith(f"正确答案：{q['answer']}. "), q['id']
            assert {e.split(':',1)[0] for e in zh['evidence']} == {c['id'] for c in q['choices']} - {q['answer']}
            # The referenced option remains exact in both language editions.
            assert result['text'].splitlines()[0].removeprefix('Correct answer: ') in zh['text'].splitlines()[0]
        elif q['type'] == 'cloze':
            for blank, reason in zip(q['blanks'], zh['evidence']):
                assert f"{blank['prefix']} + {blank['missingLetters']} = {blank['fullWord']}" in reason


def test_chinese_corrections_preserve_the_reviewed_meaning():
    qs = questions()
    translated = lambda qid: explain(qs[qid])['translations']['zh-CN']
    seminar = translated('student-1-l1-8')
    assert 'Did you attend the seminar?' in seminar['text']
    assert '间接回答' in seminar['text'] and '睡过头' in seminar['text']
    assert not any(word in json.dumps(seminar, ensure_ascii=False) for word in ['超市', '三文鱼', '晚餐', '戏剧'])
    shopping = translated('student-1-l1-9')
    assert shopping['text'].startswith('正确答案：C.') and '提到换衣服的是男士' in shopping['text']
    assert '特殊疑问句' in translated('student-1-w-build-4')['text']
    assert '没有 the 词块' in translated('student-1-w-build-5')['warnings'][0]
    assert '没有硬性要求至少两条理由' in ' '.join(translated('student-1-w-academic_discussion')['evidence'])
    assert '没有唯一正确' in translated('student-1-s-interview-4')['text']


def test_reference_keys_match_the_manually_reviewed_original_pdf_tables():
    qs = questions()
    for module, first, keys in [
        ('r1', 11, 'DCBCBBABDA'), ('r2', 11, 'CCACDDBCBC'),
        ('l1', 1, 'ACBBDDDACBBDADCBBA'), ('l2', 1, 'BADBABCBBBACBCDA'),
    ]:
        for number, key in enumerate(keys, first):
            assert qs[f'student-1-{module}-{number}']['answer'] == key, (module, number)
    for module, pieces in [('r1', ['ght','at','ple','ly','sic','ever','s','om','ord','cing']),
                           ('r2', ['s','to','ions','th','les','ts','rt','lved','itive','ch'])]:
        assert [b['missingLetters'] for b in qs[f'student-1-{module}-cloze']['blanks']] == pieces


def test_seminar_explanation_teaches_the_indirect_negative_reply_without_next_task_leakage():
    result = explain(questions()['student-1-l1-8'])
    text = json.dumps(result)
    assert 'Did you attend the seminar?' in text
    assert 'past event' in text and 'indirect answer' in text and 'missed it' in text
    assert not any(word in text.lower() for word in ['supermarket', 'salmon', 'dinner', 'theater'])


def test_known_companion_errors_are_corrected_without_changing_keys_or_inventing_rules():
    qs = questions()
    ninth = explain(qs['student-1-l1-9'])
    assert ninth['text'].startswith('Correct answer: C.') and 'man who mentions changing clothes' in ninth['text']
    fifth = explain(qs['student-1-w-build-5'])
    assert fifth['text'].splitlines()[0] == 'Reference sentence: Do you know how much tickets will cost?'
    assert 'word bank' in fifth['warnings'][0]
    assert 'wh-question, not a yes/no question' in explain(qs['student-1-w-build-4'])['text']
    discussion = explain(qs['student-1-w-academic_discussion'])
    assert any('does not impose an at-least-two-reasons rule' in e for e in discussion['evidence'])
    assert 'There is no single correct' in explain(qs['student-1-s-interview-4'])['text']


@pytest.mark.parametrize('field', ['answer', 'transcript', 'source', 'choices', 'audio', 'conflict'])
def test_changed_context_or_key_withholds_the_reviewed_rationale_in_english(field):
    q = deepcopy(questions()['student-1-l1-8'])
    if field == 'answer': q['answer'] = 'B'
    elif field == 'transcript': q['transcript'] = 'Did you enjoy the seminar?'
    elif field == 'source': q['source']['page'] += 1
    elif field == 'choices': q['choices'][0]['text'] = 'Different reply.'
    elif field == 'audio': q['audio']['segmentId'] = 'different-question'
    else: q['answerConflict'] = {'status':'needs-review'}
    result = explain(q)
    assert result['origin'] == 'unavailable' and result['language'] == 'en'
    assert 'Correct answer:' not in result['text']
    translated = result['translations']['zh-CN']
    assert translated['language'] == 'zh-CN' and '暂不展示' in translated['text']
    assert '正确答案：' not in translated['text'] and translated['evidence'] == []


def test_mismatched_translation_is_withheld_and_returned_translations_are_independent(monkeypatch):
    from backend import reviewed_explanations
    q = questions()['student-1-l1-8']
    result = explain(q)
    result['translations']['zh-CN']['evidence'].clear()
    assert len(explain(q)['translations']['zh-CN']['evidence']) == 3
    original = manifest
    changed = deepcopy(manifest('zh-CN'))
    changed['questions'][q['id']]['fingerprint'] = 'different-version'
    monkeypatch.setattr(reviewed_explanations, 'manifest', lambda language='en': changed if language == 'zh-CN' else original())
    result = explain(q)
    assert result['origin'] == 'unavailable'
    assert not result['translations']['zh-CN']['evidence']


@pytest.mark.parametrize('heading', ['Part 2: Conversation', '场景:买菜', 'Passage: A new passage',
                                  'The new fitness center is intended for which group?',
                                  '办公室空调维修对话', 'Environmental Science Class Lecture'])
def test_companion_import_stops_at_the_next_task_boundary(heading):
    body = '正确答案:A. I overslept.\n→ Explains missing the event.\n' + heading + '\nNEXT TASK BODY'
    assert explanation_lines(body) == ['正确答案:A. I overslept.', '→ Explains missing the event.']


def test_review_projects_bilingual_notes_onto_saved_sessions_without_rewriting_answers_or_scores(prepared):
    root, _, _ = prepared
    clock = [1_000_000]
    app = create_app(root, clock=lambda:clock[0], testing=True)
    with TestClient(app) as client:
        env = {'root':root, 'app':app, 'client':client, 'clock':clock}
        current = begin(env, start(env, examId='student-1', scope='listening', questionIds=['student-1-l1-8']))
        assert 'explanation' not in current['question']
        assert 'translations' not in json.dumps(current)
        assert client.get(f"/api/sessions/{current['id']}/feedback?questionId=student-1-l1-8").status_code == 403
        clock[0] = current['audioEarliestEnd'] + 1
        current = action(env, current, 'audio-ended').json()
        current = action(env, current, 'answer', answer='A').json()
        assert action(env, current, 'finish').status_code == 200
        with app.state.store.transaction() as db:
            old = deepcopy(app.state.store.get(db, current['id']))
        for endpoint in ['review','export']:
            result = client.get(f"/api/sessions/{current['id']}/{endpoint}").json()
            q = result['sections'][0]['modules'][0]['questions'][0]
            assert q['explanation']['language'] == 'en' and q['explanation']['reviewed']
            assert q['explanation']['translations']['zh-CN']['text'].startswith('正确答案：A. I overslept.')
            assert 'explanationSource' not in q
            assert q['grade'] == {'correct':1,'total':1}
            assert result['answers'] == old['answers'] and result['scoreSnapshot'] == old['scoreSnapshot']
        with app.state.store.transaction() as db:
            assert app.state.store.get(db, current['id']) == old


@pytest.mark.parametrize('mode, allow_aids', [('practice', True), ('practice', False), ('strict', False)])
def test_bilingual_feedback_respects_practice_consent_and_strict_boundaries(prepared, mode, allow_aids):
    root, _, _ = prepared
    clock = [1_000_000]
    app = create_app(root, clock=lambda:clock[0], testing=True)
    with TestClient(app) as client:
        env = {'root':root, 'app':app, 'client':client, 'clock':clock}
        selection = {'questionIds':['student-1-r1-11']} if mode == 'practice' else {}
        current = begin(env, start(env, examId='student-1', mode=mode, scope='reading',
                                   allowPracticeAids=allow_aids, **selection))
        assert 'explanation' not in current['question']
        assert 'translations' not in json.dumps(current)
        response = client.get(f"/api/sessions/{current['id']}/feedback?questionId=student-1-r1-11")
        assert response.status_code == (200 if allow_aids else 403)
        if allow_aids:
            explanation = response.json()['question']['explanation']
            assert explanation['text'].startswith('Correct answer: D.')
            assert explanation['translations']['zh-CN']['text'].startswith('正确答案：D.')


def test_retained_paper_interview_guide_is_not_replaced_with_audio_edition_guidance():
    path = ROOT / 'generated/exams/student-1.json'
    if not path.exists(): pytest.skip('The retained private paper edition is optional')
    paper = json.loads(path.read_text())
    q = next((q for s in paper['sections'] for m in s['modules'] for q in m['questions'] if q['id']=='student-1-s-interview-1'),None)
    if q is None: pytest.skip('This installation uses the audio edition')
    result = explain(q)
    assert result['language'] == 'en' and result['origin'] == 'local_assistance'
    assert 'currently live' in result['text']
