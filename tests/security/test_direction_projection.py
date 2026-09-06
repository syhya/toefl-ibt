"""Instruction projection uses only frozen, verified PDF text; never ASR/answers."""
import hashlib
import json

import pytest

from backend.tests.test_api import env, start, begin, action


PDF_INSTRUCTION = 'Original PDF instruction.\nThe original paragraph break is retained.'
NEXT_PDF_INSTRUCTION = 'Original PDF task-specific instruction.'


def install_directions(env, mutation=None):
    root = env['root']
    path = root / 'scripts/verified_pack_directions.json'
    clips = {
        'module-cue': {'verified': True, 'url': '/materials/other.ogg', 'sourceText': PDF_INSTRUCTION,
                       'asrText': 'SECRET_ASR_WORDING', 'transcript': 'SECRET_TRANSCRIPT', 'audit': 'SECRET_AUDIT'},
        'question-cue': {'verified': True, 'url': '/materials/other.ogg', 'sourceText': NEXT_PDF_INSTRUCTION},
        'stimulus-cue': {'verified': True, 'url': '/materials/shared.ogg', 'sourceText': 'SECRET_STIMULUS_TEXT'},
    }
    if mutation == 'unverified-clip':
        clips['module-cue']['verified'] = False
    elif mutation == 'wrong-url':
        clips['module-cue']['url'] = '/materials/shared.ogg'
    elif mutation == 'not-text':
        clips['module-cue']['sourceText'] = {'answer': 'SECRET_OBJECT'}
    raw = json.dumps({'schemaVersion': 1, 'clips': clips}).encode()
    path.write_bytes(raw)
    exam_path = root / 'generated/exams/exam.json'
    exam = json.loads(exam_path.read_text())
    if mutation != 'unbound-file':
        exam['verificationInputs']['curationSha256ByPath']['scripts/verified_pack_directions.json'] = hashlib.sha256(raw).hexdigest()
    module = next(section for section in exam['sections'] if section['id'] == 'listening')['modules'][0]
    module['instructions'] = 'The source module introduction.'
    module['directionsAudio'] = {'url': '/materials/other.ogg', 'durationSeconds': 3,
                                 'segmentId': 'module-cue', 'groupId': 'module-cue',
                                 'instructions': 'SECRET_INLINE_INSTRUCTIONS'}
    if mutation == 'missing-segment-id':
        module['directionsAudio'].pop('segmentId')
    module['questions'][0].update(transcript='SECRET_QUESTION_TRANSCRIPT', answer='SECRET_ANSWER',
        mediaSequence=[
            {'url': '/materials/other.ogg', 'durationSeconds': 1, 'segmentId': 'question-cue', 'groupId': 'question-cue', 'kind': 'directions'},
            {'url': '/materials/shared.ogg', 'durationSeconds': 2, 'segmentId': 'stimulus-cue', 'groupId': 'stimulus-cue', 'kind': 'stimulus'},
            {'url': '/materials/shared.ogg', 'durationSeconds': 1, 'groupId': 'spoken-question', 'kind': 'question'},
        ])
    exam_path.write_text(json.dumps(exam))
    catalog = root / 'generated/catalog.json'
    catalog.write_text(catalog.read_text() + ' ')
    if mutation == 'changed-file':
        path.write_text(path.read_text() + ' ')
    elif mutation == 'missing-file':
        path.unlink()
    elif mutation == 'external-symlink':
        target = root.parent / f'{root.name}-external-directions.json'
        target.write_bytes(raw)
        path.unlink()
        path.symlink_to(target)
    return path


def test_only_verified_pdf_text_is_projected_for_the_current_instruction_segment(env):
    install_directions(env)
    initial = start(env, mode='strict', scope='listening')
    assert initial['phase'] == 'directions' and initial['deadline'] is None and initial['question'] is None
    current = begin(env, initial)
    assert current['phase'] == 'audio' and current['deadline'] is None
    assert current['question']['audio']['kind'] == 'directions'
    assert current['question']['audio']['scope'] == 'module-directions'
    assert current['question']['audio']['instructions'] == PDF_INSTRUCTION
    assert action(env, current, 'answer', answer='A').status_code == 409
    assert action(env, current, 'audio-ended', mediaIndex=0).status_code == 409
    for index, seconds in enumerate([3, 1, 2, 1]):
        encoded = json.dumps(current)
        for forbidden in ['SECRET_ASR_WORDING', 'SECRET_TRANSCRIPT', 'SECRET_AUDIT', 'SECRET_INLINE_INSTRUCTIONS',
                          'SECRET_QUESTION_TRANSCRIPT', 'SECRET_STIMULUS_TEXT', 'SECRET_ANSWER']:
            assert forbidden not in encoded
        assert current['deadline'] is None and current['remainingSeconds'] is None
        assert 'prompt' not in current['question'] and 'transcript' not in current['question']
        env['clock'][0] += seconds * 1000
        current = action(env, current, 'audio-ended', mediaIndex=index).json()
        if index == 0:
            assert current['question']['audio']['instructions'] == NEXT_PDF_INSTRUCTION
            assert 'scope' not in current['question']['audio']
        elif index in [1, 2]:
            assert 'instructions' not in current['question']['audio']
    assert current['phase'] == 'response' and current['remainingSeconds'] == 20
    assert current['deadline'] == env['clock'][0] + 20_000
    assert 'audio' not in current['question'] and 'transcript' not in current['question'] and 'answer' not in current['question']
    assert PDF_INSTRUCTION not in json.dumps(current['question'])
    assert 'SECRET_QUESTION_TRANSCRIPT' not in json.dumps(current)


@pytest.mark.parametrize('mutation', ['unbound-file', 'unverified-clip', 'wrong-url', 'not-text',
                                      'missing-segment-id', 'changed-file', 'missing-file', 'external-symlink'])
def test_unverified_instruction_text_never_falls_back_to_inline_or_asr_text(env, mutation):
    path = install_directions(env, mutation)
    try:
        # Guided practice can open references with an invalid runtime manifest;
        # that must not promote unverified text into the trusted audio caption.
        current = begin(env, start(env, mode='practice', scope='listening'))
        assert current['phase'] == 'audio' and current['deadline'] is None
        assert current['question']['audio']['kind'] == 'directions'
        assert 'instructions' not in current['question']['audio']
        assert 'SECRET_INLINE_INSTRUCTIONS' not in json.dumps(current)
        assert 'SECRET_ASR_WORDING' not in json.dumps(current)
    finally:
        if mutation == 'external-symlink':
            path.resolve().unlink(missing_ok=True)


def test_a_changed_curation_file_cannot_replace_the_cached_original_pdf_text(env):
    path = install_directions(env)
    current = begin(env, start(env, mode='strict', scope='listening'))
    assert current['question']['audio']['instructions'] == PDF_INSTRUCTION
    changed = json.loads(path.read_text())
    changed['clips']['module-cue']['sourceText'] = 'REPLACED_INSTRUCTION_TEXT'
    path.write_text(json.dumps(changed))
    restored = env['client'].get(f"/api/sessions/{current['id']}").json()
    assert restored['question']['audio']['instructions'] == PDF_INSTRUCTION
    assert 'REPLACED_INSTRUCTION_TEXT' not in json.dumps(restored)
    assert restored['sourceVersionMatches'] is False
    assert restored['deadline'] is None and restored['audioEarliestEnd'] == current['audioEarliestEnd']
