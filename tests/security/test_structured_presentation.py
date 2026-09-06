"""Structured stems and visual authorization use isolated generated fixtures only."""
import hashlib
import json

import pytest

from backend.presentation import asset_is_active, content_digest, safe_stem_blocks, validate_question
from backend.tests.test_api import action, begin, env, start


def install_structured(env, section='reading', status='source-verified', manifest=True, malformed=None):
    root = env['root']
    exam_path = root / 'generated/exams/exam.json'
    exam = json.loads(exam_path.read_text())
    selected = next(item for item in exam['sections'] if item['id'] == section)
    question = selected['modules'][0]['questions'][0]
    evidence_path = root / 'generated/assets/source-evidence.jpg'
    evidence_path.write_bytes(b'REVIEW_ONLY_ORIGINAL_CROP')
    question.update(
        presentationSchema='structured-v1',
        structuredContentStatus=status,
        stemBlocks=[
            {'type': 'instruction', 'text': 'Read the verified source text.'},
            {'type': 'message', 'sender': 'Source sender', 'date': 'January 2', 'paragraphs': ['First source paragraph.', 'Second source paragraph.']},
            {'type': 'dialogue', 'turns': [{'speaker': 'A', 'text': 'A source turn.'}, {'speaker': 'B', 'text': 'Another source turn.'}]},
            {'type': 'table', 'caption': 'Source table', 'headers': ['One', 'Two'], 'rows': [['A', 'B']], 'rowHeaders': True},
            {'type': 'list', 'items': ['First verified point.', 'Second verified point.'],
             'ordered': False, 'marker': 'lower-alpha'},
            {'type': 'question', 'text': 'Which source option is correct?'},
            {'type': 'form_diagram', 'highlightedPosition': 4},
            {'type': 'essential_visual', 'assetIndex': 0, 'alt': 'Necessary source diagram'},
        ],
        assets=[{'url': '/assets/stem.jpg', 'role': 'essentialVisual', 'highResolution': True,
                 'width': 1600, 'height': 1200, 'alt': 'Necessary source diagram'}],
        sourceEvidenceAssets=[{'url': '/assets/source-evidence.jpg', 'reviewOnly': True,
                               'alt': 'Original source crop', 'page': 1, 'cropBounds': [1, 2, 3, 4]}],
        stimulusSource={'materialId': 'source', 'page': 2, 'url': '/materials/source.pdf#page=2',
                        'privateNote': 'SECRET_STIMULUS_AUDIT'},
        privatePresentationEvidence='SECRET_REVIEW_METADATA',
    )
    if malformed:
        malformed(question)
    inputs = exam.setdefault('verificationInputs', {})
    inputs.setdefault('assetSha256ByUrl', {})['/assets/stem.jpg'] = hashlib.sha256((root / 'generated/assets/stem.jpg').read_bytes()).hexdigest()
    inputs['assetSha256ByUrl']['/assets/source-evidence.jpg'] = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    if manifest:
        inputs['structuredContentSha256ByQuestionId'] = {
            item['id']: content_digest(item)
            for section_item in exam['sections']
            for module in section_item['modules']
            for item in module['questions']
            if item.get('presentationSchema') == 'structured-v1'
        }
    exam_path.write_text(json.dumps(exam))
    catalog_path = root / 'generated/catalog.json'
    catalog_path.write_text(catalog_path.read_text() + ' ')
    return question


def test_structured_stem_is_whitelisted_and_original_crop_is_review_only(env):
    source = install_structured(env)
    opened = begin(env, start(env, mode='strict', scope='reading'))
    question = opened['question']
    encoded = json.dumps(question)
    assert question['presentationSchema'] == 'structured-v1'
    assert question['structuredContentStatus'] == 'source-verified'
    assert question['stemBlocks'] == source['stemBlocks']
    assert 'SECRET_REVIEW_METADATA' not in encoded
    assert 'SECRET_STIMULUS_AUDIT' not in encoded
    assert 'stimulusSource' not in question
    assert 'sourceEvidenceAssets' not in question
    assert len(question['assets']) == 1
    visual_url = question['assets'][0]['url']
    assert question['assets'][0]['role'] == 'essentialVisual'
    assert env['client'].get(visual_url).status_code == 200
    evidence_id = env['app'].state.catalog.register('/assets/source-evidence.jpg')
    assert env['client'].get(f"/api/sessions/{opened['id']}/assets/{evidence_id}").status_code == 403

    advanced = action(env, opened, 'next').json()
    assert env['client'].get(visual_url).status_code == 403
    ended = action(env, advanced, 'finish').json()
    review = env['client'].get(f"/api/sessions/{ended['id']}/review").json()
    reviewed = review['sections'][0]['modules'][0]['questions'][0]
    assert reviewed['sourceEvidenceAssets'][0]['reviewOnly'] is True
    assert reviewed['stimulusSource']['materialId'] == 'source'
    assert reviewed['stimulusSource']['page'] == 2
    assert reviewed['stimulusSource']['url'].endswith('#page=2')
    assert 'SECRET_STIMULUS_AUDIT' not in json.dumps(reviewed['stimulusSource'])
    assert env['client'].get(reviewed['stimulusSource']['url']).content == (env['root'] / 'data/source.pdf').read_bytes()
    assert env['client'].get(reviewed['sourceEvidenceAssets'][0]['url']).content == b'REVIEW_ONLY_ORIGINAL_CROP'

    evidence_path = env['root'] / 'generated/assets/source-evidence.jpg'
    evidence_path.write_bytes(b'X' * evidence_path.stat().st_size)
    assert env['client'].get(reviewed['sourceEvidenceAssets'][0]['url']).status_code == 409


def test_audio_phase_hides_structured_stem_and_visual_until_response(env):
    install_structured(env, section='listening')
    root = env['root']
    extra_path = root / 'generated/assets/unreferenced.jpg'
    extra_path.write_bytes(b'UNREFERENCED_VISUAL')
    exam_path = root / 'generated/exams/exam.json'
    exam = json.loads(exam_path.read_text())
    listening = next(section for section in exam['sections'] if section['id'] == 'listening')
    question = listening['modules'][0]['questions'][0]
    question['assets'].append({'url': '/assets/unreferenced.jpg', 'role': 'essentialVisual', 'highResolution': True,
                               'alt': 'An unused source diagram that is not referenced by the stem'})
    exam['verificationInputs']['assetSha256ByUrl']['/assets/unreferenced.jpg'] = hashlib.sha256(extra_path.read_bytes()).hexdigest()
    exam['verificationInputs']['structuredContentSha256ByQuestionId'] = {
        item['id']: content_digest(item)
        for section in exam['sections'] for module in section['modules'] for item in module['questions']
        if item.get('presentationSchema') == 'structured-v1'
    }
    exam_path.write_text(json.dumps(exam))
    catalog_path = root / 'generated/catalog.json'
    catalog_path.write_text(catalog_path.read_text() + ' ')
    other_session = begin(env, start(env, mode='practice', scope='listening'))
    other_visual_url = other_session['question']['assets'][0]['url']
    assert env['client'].get(other_visual_url).status_code == 200
    opened = begin(env, start(env, mode='strict', scope='listening'))
    assert opened['phase'] == 'audio'
    for private in ['prompt', 'choices', 'transcript', 'passage', 'context']:
        assert private not in opened['question']
    assert opened['question']['stemBlocks'] == [
        {'type': 'form_diagram', 'highlightedPosition': 4}
    ]
    assert len(opened['question']['assets']) == 1
    visual_url = opened['question']['assets'][0]['url']
    assert env['client'].get(visual_url).status_code == 200
    assert env['client'].get(other_visual_url).status_code == 403
    unreferenced_id = env['app'].state.catalog.register('/assets/unreferenced.jpg')
    assert env['client'].get(f"/api/sessions/{opened['id']}/assets/{unreferenced_id}").status_code == 403
    env['clock'][0] += 2000
    response = action(env, opened, 'audio-ended').json()
    assert response['phase'] == 'response'
    assert response['question']['stemBlocks']
    assert env['client'].get(response['question']['assets'][0]['url']).status_code == 200
    response = action(env, response, 'answer', answer='A').json()
    advanced = action(env, response, 'next').json()
    assert advanced['question']['id'] == 'l1q2'
    assert env['client'].get(visual_url).status_code == 403


@pytest.mark.parametrize('status', ['needs-review', 'source-review-only'])
def test_unverified_structured_content_never_enters_an_interactive_plan(env, status):
    source = install_structured(env, status=status)
    strict = env['client'].post('/api/sessions', json={'examId': 'exam', 'mode': 'strict', 'scope': 'reading'})
    assert strict.status_code == 422
    assert 'unavailable prompts' in strict.json()['error']
    practice = begin(env, start(env, mode='practice', scope='reading'))
    assert practice['question']['id'] != source['id']
    selected = env['client'].post('/api/sessions', json={'examId': 'exam', 'mode': 'practice', 'scope': 'reading', 'questionIds': [source['id']]})
    assert selected.status_code == 422
    assert 'No interactive questions' in selected.json()['error']
    action(env, practice, 'finish')
    path = env['root'] / 'generated/exams/exam.json'
    exam = json.loads(path.read_text())
    exam['timingPolicy'] = 'untimed'
    path.write_text(json.dumps(exam))
    catalog_path = env['root'] / 'generated/catalog.json'
    catalog_path.write_text(catalog_path.read_text() + ' ')
    untimed = env['client'].post('/api/sessions', json={'examId': 'exam', 'mode': 'practice', 'scope': 'reading', 'questionIds': [source['id']]})
    assert untimed.status_code == 422
    summary = next(item for item in env['client'].get('/api/catalog').json()['exams'] if item['id'] == 'exam')
    assert summary['structuredReviewOnlyCount'] == 1
    assert summary['strictEligible'] is False
    assert next(section for section in summary['sections'] if section['id'] == 'reading')['structuredReviewOnlyCount'] == 1


def test_structured_manifest_and_visual_shape_are_enforced_without_affecting_legacy(env):
    install_structured(env, manifest=False)
    legacy_compatible = begin(env, start(env, mode='strict', scope='reading'))
    assert legacy_compatible['question']['presentationSchema'] == 'structured-v1'
    action(env, legacy_compatible, 'finish')

    install_structured(env, manifest=True, malformed=lambda question: question['stemBlocks'][0].update(answer='SECRET'))
    malformed = env['client'].post('/api/sessions', json={'examId': 'exam', 'mode': 'practice', 'scope': 'reading'})
    assert malformed.status_code == 422
    assert 'unknown-structured-block-field' in malformed.json()['error']

    install_structured(env, malformed=lambda question: question['assets'][0].update(highResolution=False))
    low_resolution = env['client'].post('/api/sessions', json={'examId': 'exam', 'mode': 'practice', 'scope': 'reading'})
    assert low_resolution.status_code == 422
    assert 'structured-asset-not-essential-high-resolution' in low_resolution.json()['error']

    install_structured(env, malformed=lambda question: question['assets'][0].update(alt='  QUESTION image! '))
    generic_asset_alt = env['client'].post('/api/sessions', json={'examId': 'exam', 'mode': 'practice', 'scope': 'reading'})
    assert generic_asset_alt.status_code == 422
    assert 'essential-visual-alt-not-semantic' in generic_asset_alt.json()['error']

    install_structured(env, malformed=lambda question: question['stemBlocks'][-1].update(alt='Original Question'))
    generic_block_alt = env['client'].post('/api/sessions', json={'examId': 'exam', 'mode': 'practice', 'scope': 'reading'})
    assert generic_block_alt.status_code == 422
    assert 'invalid-essential-visual-reference' in generic_block_alt.json()['error']

    install_structured(env, malformed=lambda question: question['stemBlocks'][3].update(rowHeaders='yes'))
    invalid_table = env['client'].post('/api/sessions', json={'examId': 'exam', 'mode': 'practice', 'scope': 'reading'})
    assert invalid_table.status_code == 422
    assert 'invalid-table-row-headers' in invalid_table.json()['error']

    install_structured(env, malformed=lambda question: question['stemBlocks'][4].update(items=[]))
    empty_list = env['client'].post('/api/sessions', json={'examId': 'exam', 'mode': 'practice', 'scope': 'reading'})
    assert empty_list.status_code == 422
    assert 'list-items-missing' in empty_list.json()['error']

    install_structured(env, malformed=lambda question: question['stemBlocks'][4].update(ordered='yes'))
    invalid_ordered = env['client'].post('/api/sessions', json={'examId': 'exam', 'mode': 'practice', 'scope': 'reading'})
    assert invalid_ordered.status_code == 422
    assert 'invalid-list-ordered' in invalid_ordered.json()['error']

    install_structured(env, malformed=lambda question: question['stemBlocks'][4].update(marker='roman'))
    invalid_marker = env['client'].post('/api/sessions', json={'examId': 'exam', 'mode': 'practice', 'scope': 'reading'})
    assert invalid_marker.status_code == 422
    assert 'invalid-list-marker' in invalid_marker.json()['error']

    install_structured(env, malformed=lambda question: question['stimulusSource'].update(page='two'))
    invalid_stimulus = env['client'].post('/api/sessions', json={'examId': 'exam', 'mode': 'practice', 'scope': 'reading'})
    assert invalid_stimulus.status_code == 422
    assert 'invalid-stimulus-source' in invalid_stimulus.json()['error']

    # A valid shape with a stale curation digest is rejected before any mode can expose it.
    source = install_structured(env)
    path = env['root'] / 'generated/exams/exam.json'
    exam = json.loads(path.read_text())
    exam['verificationInputs']['structuredContentSha256ByQuestionId'][source['id']] = '0' * 64
    path.write_text(json.dumps(exam))
    catalog = env['root'] / 'generated/catalog.json'
    catalog.write_text(catalog.read_text() + ' ')
    mismatch = env['client'].post('/api/sessions', json={'examId': 'exam', 'mode': 'practice', 'scope': 'reading'})
    assert mismatch.status_code == 409
    summary = next(item for item in env['client'].get('/api/catalog').json()['exams'] if item['id'] == 'exam')
    assert summary['runtimeVerification']['status'] == 'invalid'
    assert any(issue['code'] == 'structured-content-manifest-mismatch' for issue in summary['runtimeVerification']['issues'])


def test_stimulus_source_page_change_invalidates_the_structured_manifest(env):
    source = install_structured(env)
    path = env['root'] / 'generated/exams/exam.json'
    exam = json.loads(path.read_text())
    question = next(q for section in exam['sections'] for module in section['modules'] for q in module['questions'] if q['id'] == source['id'])
    question['stimulusSource']['page'] = 3
    question['stimulusSource']['url'] = '/materials/source.pdf#page=3'
    path.write_text(json.dumps(exam))
    catalog = env['root'] / 'generated/catalog.json'
    catalog.write_text(catalog.read_text() + ' ')
    response = env['client'].post('/api/sessions', json={'examId': 'exam', 'mode': 'practice', 'scope': 'reading'})
    assert response.status_code == 409
    assert 'verification manifest' in response.json()['error']


def test_catalog_reports_only_structured_coverage_counts(env):
    install_structured(env)
    summary = next(item for item in env['client'].get('/api/catalog').json()['exams'] if item['id'] == 'exam')
    reading = next(section for section in summary['sections'] if section['id'] == 'reading')
    assert summary['structuredScreenCount'] == 1
    assert summary['sourceVerifiedStructuredCount'] == 1
    assert summary['essentialVisualCount'] == 1
    assert summary['structuredReady'] is False
    assert reading['structuredScreenCount'] == 1
    assert 'stemBlocks' not in json.dumps(summary)


def test_highlighted_source_sentence_is_validated_and_safely_projected():
    question = {
        'presentationSchema': 'structured-v1',
        'structuredContentStatus': 'source-verified',
        'stemBlocks': [
            {'type': 'highlighted_sentence', 'text': 'The source-highlighted sentence.'},
            {'type': 'form_diagram', 'highlightedPosition': 4},
        ],
        'assets': [],
    }
    assert validate_question(question, strict=True) == []
    assert safe_stem_blocks(question['stemBlocks']) == question['stemBlocks']
    question['stemBlocks'][0]['answer'] = 'SECRET'
    assert validate_question(question, strict=True) == ['unknown-structured-block-field']
    assert safe_stem_blocks(question['stemBlocks']) == [
        {'type': 'highlighted_sentence', 'text': 'The source-highlighted sentence.'},
        {'type': 'form_diagram', 'highlightedPosition': 4},
    ]
    question['stemBlocks'][0].pop('answer')
    question['stemBlocks'][1]['highlightedPosition'] = 9
    assert validate_question(question, strict=True) == [
        'invalid-form-diagram-position'
    ]


def test_dialogue_avatar_is_safely_projected_and_authorizes_only_its_high_resolution_asset():
    question = {
        'presentationSchema': 'structured-v1',
        'structuredContentStatus': 'source-verified',
        'stemBlocks': [{
            'type': 'dialogue',
            'turns': [{
                'speaker': 'Dr. Gupta',
                'text': 'Which viewpoint do you agree with?',
                'avatarAssetIndex': 0,
                'privateCropNote': 'SECRET',
            }],
        }],
        'assets': [{
            'url': '/assets/professor.png',
            'role': 'essentialVisual',
            'highResolution': True,
            'alt': 'Portrait of Dr. Gupta, the professor in the discussion',
        }],
    }
    assert validate_question(question, strict=True) == ['invalid-dialogue-turn']
    projected = safe_stem_blocks(question['stemBlocks'])
    assert projected == [{
        'type': 'dialogue',
        'turns': [{
            'speaker': 'Dr. Gupta',
            'text': 'Which viewpoint do you agree with?',
            'avatarAssetIndex': 0,
        }],
    }]
    question['stemBlocks'][0]['turns'][0].pop('privateCropNote')
    assert validate_question(question, strict=True) == []
    assert asset_is_active(question, question['assets'][0], 0, 'writing') is True
    question['stemBlocks'][0]['turns'][0]['avatarAssetIndex'] = 1
    assert validate_question(question, strict=True) == ['invalid-dialogue-turn']
    assert asset_is_active(question, question['assets'][0], 0, 'writing') is False
