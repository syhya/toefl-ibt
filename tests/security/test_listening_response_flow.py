"""Official short-response preview and Must Answer must not weaken phase controls."""
import json

import pytest

from backend.tests.test_api import env, start, begin, action


def configure(env, task='listen_response', directions=False, cue_kind=None, untimed=False):
    path = env['root'] / 'generated/exams/exam.json'
    exam = json.loads(path.read_text())
    if untimed:
        exam['timingPolicy'] = 'untimed'
    module = next(section for section in exam['sections'] if section['id'] == 'listening')['modules'][0]
    question = module['questions'][0]
    question.update(taskType=task, number=11, transcript='SECRET_SPOKEN_TRANSCRIPT', prompt='Choose the best response.',
                    answer='A', choices=[{'id': 'A', 'text': 'First source option', 'correct': True, 'explanation': 'SECRET_OPTION_METADATA'},
                                         {'id': 'B', 'text': 'Second source option'}])
    if directions:
        module['directionsAudio'] = {'url': '/materials/other.ogg', 'durationSeconds': 2, 'groupId': 'module-directions'}
    if cue_kind:
        question['mediaSequence'] = [
            {'url': '/materials/other.ogg', 'durationSeconds': 2, 'groupId': 'instruction-cue', 'kind': cue_kind},
            {**question['audio'], 'kind': 'stimulus'},
        ]
    path.write_text(json.dumps(exam))
    catalog = env['root'] / 'generated/catalog.json'
    catalog.write_text(catalog.read_text() + ' ')


@pytest.mark.parametrize('mode', ['strict', 'practice'])
def test_short_listening_previews_only_source_choices_and_number_after_instructions(env, mode):
    configure(env, directions=True)
    current = begin(env, start(env, mode=mode, scope='listening'))
    assert current['question']['audio']['kind'] == 'directions'
    assert 'number' not in current['question'] and 'choices' not in current['question']
    env['clock'][0] += 2000
    current = action(env, current, 'audio-ended', mediaIndex=0).json()
    preview = current['question']
    assert current['phase'] == 'audio' and current['deadline'] is None
    assert preview['number'] == 11 and 'numberEnd' not in preview
    assert preview['choices'] == [{'id': 'A', 'text': 'First source option'}, {'id': 'B', 'text': 'Second source option'}]
    for hidden in ['prompt', 'transcript', 'answer', 'passage', 'context']:
        assert hidden not in preview
    assert 'SECRET_' not in json.dumps(preview)
    assert 'answer' not in current['allowedActions'] and 'next' not in current['allowedActions']
    rejected = action(env, current, 'answer', answer='A')
    assert rejected.status_code == 409 and rejected.json()['session']['answer'] is None
    env['clock'][0] += 2000
    response = action(env, current, 'audio-ended', mediaIndex=1).json()
    assert response['phase'] == 'response' and response['remainingSeconds'] == 20
    assert response['question']['choices'] == preview['choices']
    assert 'transcript' not in response['question'] and 'answer' not in response['question']


@pytest.mark.parametrize('task', ['conversation', 'announcement', 'academic_talk'])
def test_other_listening_audio_does_not_preview_choices_or_question_numbers(env, task):
    configure(env, task=task)
    current = begin(env, start(env, mode='strict', scope='listening'))
    assert current['phase'] == 'audio' and current['deadline'] is None
    assert 'choices' not in current['question'] and 'number' not in current['question']
    assert 'prompt' not in current['question'] and 'transcript' not in current['question']


@pytest.mark.parametrize('kind', ['directions', 'instructions'])
def test_a_short_task_instruction_segment_never_uses_the_option_preview(env, kind):
    configure(env, cue_kind=kind)
    current = begin(env, start(env, mode='strict', scope='listening'))
    assert current['question']['audio']['kind'] == kind
    assert 'choices' not in current['question'] and 'number' not in current['question']


@pytest.mark.parametrize('mode', ['strict', 'practice'])
def test_manual_timed_listening_next_requires_an_answer_without_resetting_the_clock(env, mode):
    configure(env)
    current = begin(env, start(env, mode=mode, scope='listening'))
    env['clock'][0] += 2000
    current = action(env, current, 'audio-ended').json()
    deadline = current['deadline']
    env['clock'][0] += 1000
    denied = action(env, current, 'next')
    assert denied.status_code == 409 and 'must answer' in denied.json()['error']
    assert denied.json()['session']['question']['id'] == 'l1q1'
    assert denied.json()['session']['deadline'] == deadline
    current = action(env, current, 'answer', answer='A').json()
    current = action(env, current, 'answer', answer=None).json()
    assert action(env, current, 'next').status_code == 409, 'Clearing an answer cannot satisfy Must Answer.'
    current = action(env, current, 'answer', answer='A').json()
    following = action(env, current, 'next').json()
    assert following['question']['id'] == 'l1q2' and following['remainingSeconds'] == 20
    assert following['deadline'] == env['clock'][0] + 20000


@pytest.mark.parametrize('mode', ['strict', 'practice'])
def test_empty_listening_response_still_auto_submits_at_timeout_without_becoming_a_mistake(env, mode):
    configure(env)
    current = begin(env, start(env, mode=mode, scope='listening', **({'questionIds': ['l1q1']} if mode == 'practice' else {})))
    env['clock'][0] += 2000
    current = action(env, current, 'audio-ended').json()
    env['clock'][0] = current['deadline']
    following = env['client'].get(f"/api/sessions/{current['id']}").json()
    if mode == 'strict':
        assert following['question']['id'] == 'l1q2' and following['phase'] == 'response'
        following = action(env, following, 'finish').json()
    else:
        assert following['status'] == 'completed'
        assert following['scoreSnapshotStatus'] == 'frozen'
    review = env['client'].get(f"/api/sessions/{current['id']}/review").json()
    assert review['answers'] == {}
    assert review['score']['items']['l1q1'] == {'correct': 0, 'total': 1}
    assert env['client'].get('/api/mistakes').json()['items'] == []


def test_untimed_listening_and_reading_keep_their_existing_empty_next_behavior(env):
    reading = begin(env, start(env, mode='strict', scope='reading'))
    assert reading['stage']['timer'] == 'shared'
    next_reading = action(env, reading, 'next').json()
    assert next_reading['question']['id'] == 'r1q2'
    assert next_reading['deadline'] == reading['deadline']
    action(env, next_reading, 'finish')
    configure(env, untimed=True)
    listening = begin(env, start(env, mode='practice', scope='listening'))
    assert listening['stage']['timer'] == 'untimed'
    following = action(env, listening, 'next').json()
    assert following['question']['id'] == 'l1q2' and following['deadline'] is None
