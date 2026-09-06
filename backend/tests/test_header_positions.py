"""Positions describe selected source questions without changing their numbers or timing."""
import json

from backend.tests.test_api import env, start, begin, action, q


def test_filtered_positions_count_cloze_blanks_and_preserve_original_question_numbers(env):
    path = env['root'] / 'generated/exams/exam.json'
    exam = json.loads(path.read_text())
    reading = next(section for section in exam['sections'] if section['id'] == 'reading')
    reading['modules'][0]['questions'].insert(0, q('source-cloze', 'cloze', number=11, numberEnd=13,
        blanks=[{'id': f'blank-{index}', 'number': 11 + index, 'answer': 'word'} for index in range(3)]))
    reading['modules'][0]['questions'][-1]['number'] = 24
    path.write_text(json.dumps(exam))
    catalog = env['root'] / 'generated/catalog.json'
    catalog.write_text(catalog.read_text() + ' ')

    one = begin(env, start(env, scope='reading', questionIds=['r1q2']))
    assert one['filtered'] is True
    assert one['question']['number'] == 24
    assert one['stage']['itemCount'] == one['stage']['currentQuestionUnitStart'] == 1
    action(env, one, 'finish')

    grouped = begin(env, start(env, scope='reading', questionIds=['source-cloze', 'r1q2']))
    assert grouped['stage']['questionCount'] == 2
    assert grouped['stage']['itemCount'] == 4
    assert grouped['stage']['currentQuestionUnitStart'] == 1
    assert grouped['question']['number'] == 11 and grouped['question']['numberEnd'] == 13
    later = action(env, grouped, 'next').json()
    assert later['stage']['currentQuestionUnitStart'] == 4
    assert later['question']['number'] == 24
    assert later['deadline'] == grouped['deadline']
    earlier = action(env, later, 'back').json()
    assert earlier['stage']['currentQuestionUnitStart'] == 1
    assert earlier['deadline'] == grouped['deadline']
