"""Transcription errata repair visible text, not historical answers or scores."""
from copy import deepcopy
import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.presentation import content_digest
from backend.text_corrections import (MANIFEST_PATH, VERSION, apply_import_corrections,
                                      corrected_question, read_manifest, validate_record)
from backend.tests.test_api import env, start, begin, action

BEFORE = "'llhave to get back to you on that."
AFTER = "I’ll have to get back to you on that."


def read_exam(env):
    return json.loads((env['root'] / 'generated/exams/exam.json').read_text())


def publish(env, exam):
    (env['root'] / 'generated/exams/exam.json').write_text(json.dumps(exam))
    catalog = env['root'] / 'generated/catalog.json'
    catalog.write_text(catalog.read_text() + ' ')


def prepare_source(env):
    exam = read_exam(env)
    question = exam['sections'][0]['modules'][0]['questions'][0]
    question['source']['materialId'] = 'source'
    question['choices'][0]['text'] = BEFORE
    publish(env, exam)
    return deepcopy(question)


def manifest(env):
    digest = hashlib.sha256((env['root'] / 'data/source.pdf').read_bytes()).hexdigest()
    return {'schemaVersion': 1, 'version': VERSION, 'questions': {'r1q1': {
        'materialId': 'source', 'sourceSha256': digest, 'page': 1,
        'patches': [{'path': ['choices', 0, 'text'], 'before': BEFORE, 'after': AFTER,
                     'evidence': 'Explicit source-text regression fixture.'}],
    }}}


def install_correction(env):
    data = manifest(env)
    path = env['root'] / MANIFEST_PATH
    path.write_text(json.dumps(data))
    exam = read_exam(env)
    catalog = json.loads((env['root'] / 'generated/catalog.json').read_text())
    result = apply_import_corrections([exam], catalog['materials'], env['root'])
    exam['verificationInputs']['curationSha256ByPath'][MANIFEST_PATH] = hashlib.sha256(path.read_bytes()).hexdigest()
    exam['verificationInputs']['structuredContentSha256ByQuestionId'] = {
        q['id']: content_digest(q) for s in exam['sections'] for m in s['modules'] for q in m['questions']
        if q.get('presentationSchema') == 'structured-v1'}
    publish(env, exam)
    return result


def install_bundled_correction(env):
    """Publish the same fixture under an exam-signed runtime path, with no private manifest."""
    relative = 'generated/assets/example/text-corrections.json'
    path = env['root'] / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    data = manifest(env)
    path.write_text(json.dumps(data))
    exam = read_exam(env)
    module = exam['sections'][0]['modules'][0]
    corrected, changed = corrected_question(module['questions'][0], data['questions']['r1q1'])
    assert changed == 1
    corrected['textCorrection'] = {'version': VERSION, 'changedFields': changed}
    module['questions'][0] = corrected
    inputs = exam['verificationInputs']
    inputs['textCorrectionsPath'] = relative
    inputs['curationSha256ByPath'][relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    inputs['structuredContentSha256ByQuestionId'] = {
        q['id']: content_digest(q) for section in exam['sections'] for mod in section['modules'] for q in mod['questions']
        if q.get('presentationSchema') == 'structured-v1'}
    publish(env, exam)
    assert not (env['root'] / MANIFEST_PATH).exists()
    return relative


def stored(env, session_id):
    store = env['app'].state.store
    with store.transaction() as db:
        return deepcopy(store.get(db, session_id))


def test_old_active_and_completed_sessions_show_source_corrections_without_changing_answers_or_scores(env):
    original = prepare_source(env)
    active = begin(env, start(env, scope='reading', questionIds=['r1q1']))
    active = action(env, active, 'answer', answer='A').json()
    deadline = active['deadline']
    before_session = stored(env, active['id'])
    completed = begin(env, start(env, scope='reading', questionIds=['r1q1']))
    completed = action(env, completed, 'answer', answer='A').json()
    completed = action(env, completed, 'next').json()
    frozen = stored(env, completed['id'])
    assert install_correction(env) == {'status':'passed', 'version':VERSION, 'questions':1, 'fields':1}
    loaded = env['client'].get(f"/api/sessions/{active['id']}").json()
    assert loaded['question']['choices'][0]['text'] == AFTER
    assert loaded['question']['choices'][0]['id'] == 'A'
    assert loaded['question']['textCorrection'] == {'version':VERSION, 'changedFields':1}
    assert loaded['answer'] == 'A' and loaded['deadline'] == deadline
    assert 'answer' not in loaded['question'] and 'sourceSha256' not in json.dumps(loaded['question'])
    current = stored(env, active['id'])
    for key in ['answers', 'deadline', 'plan']:
        assert current[key] == before_session[key]
    assert current['plan'][0]['questions'][0]['choices'] == original['choices']
    for endpoint in ['review', 'export', 'feedback?questionId=r1q1']:
        response = env['client'].get(f"/api/sessions/{completed['id']}/{endpoint}")
        assert response.status_code == 200
        payload = response.json()
        q = payload['question'] if endpoint.startswith('feedback') else payload['sections'][0]['modules'][0]['questions'][0]
        assert q['choices'][0]['text'] == AFTER
        assert q['grade'] == {'correct': 1, 'total': 1} if 'grade' in q else payload['grade'] == {'correct':1,'total':1}
        if not endpoint.startswith('feedback'):
            assert payload['answers'] == frozen['answers']
            assert payload['scoreSnapshot'] == frozen['scoreSnapshot']
    after = stored(env, completed['id'])
    assert after['answers'] == frozen['answers'] and after['scoreSnapshot'] == frozen['scoreSnapshot']
    assert after['plan'] == frozen['plan']
    with TestClient(create_app(env['root'], clock=lambda:env['clock'][0], testing=True)) as client:
        review = client.get(f"/api/sessions/{completed['id']}/review").json()
        assert review['sections'][0]['modules'][0]['questions'][0]['choices'][0]['text'] == AFTER
        assert review['scoreSnapshot'] == frozen['scoreSnapshot']


def test_new_sessions_use_corrected_catalog_and_import_is_idempotent(env):
    prepare_source(env)
    install_correction(env)
    opened = begin(env, start(env, scope='reading', questionIds=['r1q1']))
    assert opened['question']['choices'][0]['text'] == AFTER
    exam = read_exam(env)
    result = apply_import_corrections([exam], json.loads((env['root'] / 'generated/catalog.json').read_text())['materials'], env['root'])
    assert result['fields'] == 0


@pytest.mark.parametrize('changed', ['manifest', 'pdf'])
def test_old_session_does_not_apply_unsigned_or_changed_source_errata(env, changed):
    prepare_source(env)
    opened = begin(env, start(env, scope='reading', questionIds=['r1q1']))
    install_correction(env)
    path = env['root'] / (MANIFEST_PATH if changed == 'manifest' else 'data/source.pdf')
    path.write_bytes(path.read_bytes() + b'changed')
    loaded = env['client'].get(f"/api/sessions/{opened['id']}").json()
    assert loaded['question']['choices'][0]['text'] == BEFORE
    assert loaded['deadline'] == opened['deadline']


def test_stale_or_wrong_page_field_corrections_never_rewrite_other_content(env):
    original = prepare_source(env)
    record = manifest(env)['questions']['r1q1']
    wrong = deepcopy(record); wrong['page'] = 2
    assert corrected_question(original, wrong, partial=True) == (original, 0)
    with pytest.raises(ValueError, match='PDF/page'):
        corrected_question(original, wrong)
    other = deepcopy(original); other['choices'][0]['text'] = 'A genuinely different source option.'
    assert corrected_question(other, record, partial=True) == (other, 0)
    with pytest.raises(ValueError, match='stale'):
        corrected_question(other, record)


@pytest.mark.parametrize('path', [['answer'], ['choices',0,'id'], ['audio','url'], ['blanks',0,'length'], ['source','page'], ['slots',0,'id']])
def test_manifest_cannot_change_answers_identifiers_media_or_input_lengths(env, path):
    record = manifest(env)['questions']['r1q1']
    record['patches'][0]['path'] = path
    with pytest.raises(ValueError, match='Invalid text correction patch'):
        validate_record('r1q1', record)


def test_cloze_corrections_preserve_the_same_placeholder_ids(env):
    record = manifest(env)['questions']['r1q1']
    record['patches'][0].update(path=['passageTemplate'], before='Some {{b1}}.', after='Some {{b2}}.')
    with pytest.raises(ValueError, match='placeholder identities'):
        validate_record('r1q1', record)


def test_invalid_record_cannot_partially_mutate_an_import(env):
    original = prepare_source(env)
    data = manifest(env)
    data['questions']['missing-question'] = deepcopy(data['questions']['r1q1'])
    (env['root'] / MANIFEST_PATH).write_text(json.dumps(data))
    exam = read_exam(env); before = deepcopy(exam)
    materials = json.loads((env['root'] / 'generated/catalog.json').read_text())['materials']
    with pytest.raises(ValueError, match='missing questions'):
        apply_import_corrections([exam], materials, env['root'])
    assert exam == before


@pytest.mark.parametrize('endpoint', ['review', 'export', 'feedback?questionId=r1q1'])
def test_first_request_after_reimport_can_be_a_direct_historical_review(env, endpoint):
    prepare_source(env)
    current = begin(env, start(env, scope='reading', questionIds=['r1q1']))
    current = action(env, current, 'answer', answer='A').json()
    ended = action(env, current, 'next').json()
    install_correction(env)
    payload = env['client'].get(f"/api/sessions/{ended['id']}/{endpoint}").json()
    q = payload['question'] if endpoint.startswith('feedback') else payload['sections'][0]['modules'][0]['questions'][0]
    assert q['choices'][0]['text'] == AFTER


def test_case_only_reference_corrections_and_printed_sentence_literals_keep_token_identity(env):
    record = manifest(env)['questions']['r1q1']
    record['questionType'] = 'build_sentence'
    record['patches'] = [
        {'path':['answer'], 'before':'i can help', 'after':'I can help', 'evidence':'Printed source case.'},
        {'path':['sentencePrefix'], 'before':None, 'after':'Thanks.', 'evidence':'Printed fixed preface.'},
        {'path':['terminalPunctuation'], 'before':None, 'after':'.', 'evidence':'Printed final period.'},
    ]
    validate_record('build', record)
    q = {'id':'build','type':'build_sentence','source':{'materialId':'source','page':1},
         'tokens':['I','can','help'],'slots':[{'id':'g1'},{'id':'g2'},{'id':'g3'}],'answer':'i can help'}
    corrected, changed = corrected_question(q, record)
    assert changed == 3 and corrected['answer'] == 'I can help'
    assert corrected['slots'] == q['slots'] and corrected['tokens'] == q['tokens']
    assert q['answer'] == 'i can help' and 'sentencePrefix' not in q
    record['patches'][0]['after'] = 'I cannot help'
    with pytest.raises(ValueError, match='case-only'):
        validate_record('build', record)


def test_source_bound_message_header_insertions_are_guarded_in_old_layouts(env):
    record = manifest(env)['questions']['r1q1']
    record['patches'] = [{'path':['stemBlocks',0,'subject'], 'before':None, 'after':'Library update', 'evidence':'Printed header.'}]
    validate_record('q', record)
    q = {'id':'q','source':{'materialId':'source','page':1}, 'stemBlocks':[{'type':'message','paragraphs':['Original paragraph.']}]}
    corrected, changed = corrected_question(q, record)
    assert changed == 1 and corrected['stemBlocks'][0]['subject'] == 'Library update'
    assert corrected_question(corrected, record)[1] == 0
    q['stemBlocks'] = []
    assert corrected_question(q, record, partial=True) == (q,0)


def test_historical_projection_uses_signed_bundled_errata_without_private_manifest(env):
    prepare_source(env)
    current = begin(env, start(env, scope='reading', questionIds=['r1q1']))
    current = action(env, current, 'answer', answer='A').json()
    current = action(env, current, 'next').json()
    original = stored(env, current['id'])
    relative = install_bundled_correction(env)
    assert relative != MANIFEST_PATH
    response = env['client'].get(f"/api/sessions/{current['id']}/review")
    assert response.status_code == 200, response.text
    review = response.json()
    question = review['sections'][0]['modules'][0]['questions'][0]
    assert question['choices'][0]['text'] == AFTER
    assert question['choices'][0]['id'] == 'A'
    assert question['grade'] == {'correct': 1, 'total': 1}
    assert review['answers'] == original['answers']
    assert review['scoreSnapshot'] == original['scoreSnapshot']
    after = stored(env, current['id'])
    for key in ['plan', 'answers', 'deadline', 'scoreSnapshot']:
        assert after[key] == original[key]
    with TestClient(create_app(env['root'], clock=lambda: env['clock'][0], testing=True)) as restarted:
        review = restarted.get(f"/api/sessions/{current['id']}/review").json()
        assert review['sections'][0]['modules'][0]['questions'][0]['choices'][0]['text'] == AFTER


@pytest.mark.parametrize('invalid', ['unsigned', 'changed', 'relative-escape', 'absolute-escape', 'symlink-escape'])
def test_bundled_errata_projection_rejects_unsigned_changed_or_outside_paths(env, invalid):
    prepare_source(env)
    current = begin(env, start(env, scope='reading', questionIds=['r1q1']))
    original = stored(env, current['id'])
    relative = install_bundled_correction(env)
    path = env['root'] / relative
    exam = read_exam(env)
    inputs = exam['verificationInputs']
    if invalid == 'unsigned':
        del inputs['curationSha256ByPath'][relative]
    elif invalid == 'changed':
        path.write_bytes(path.read_bytes() + b' ')
    else:
        outside = env['root'].parent / f"{env['root'].name}-outside-corrections.json"
        outside.write_bytes(path.read_bytes())
        if invalid == 'relative-escape':
            destination = '../' + outside.name
        elif invalid == 'absolute-escape':
            destination = str(outside)
        else:
            link = env['root'] / 'generated/assets/linked-corrections.json'
            link.symlink_to(outside)
            destination = str(link.relative_to(env['root']))
        inputs['textCorrectionsPath'] = destination
        inputs['curationSha256ByPath'][destination] = hashlib.sha256(outside.read_bytes()).hexdigest()
    publish(env, exam)
    response = env['client'].get(f"/api/sessions/{current['id']}")
    assert response.status_code == 200, response.text
    assert response.json()['question']['choices'][0]['text'] == BEFORE
    after = stored(env, current['id'])
    for key in ['plan', 'answers', 'deadline']:
        assert after[key] == original[key]
