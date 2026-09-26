"""Native example installation is isolated from user data and private resources."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from backend.catalog import Catalog
from backend.engine import DEFAULT_TIMING, ExamError, make_plan, new_session
from backend.example_pack import install_example
from backend.integrity import SourceIntegrity
from backend.presentation import content_digest

PROJECT = Path(__file__).resolve().parents[2]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def file_record(bundle, path, destination):
    source = bundle / path
    return {'path': path, 'installPath': destination, 'bytes': source.stat().st_size,
            'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}


@pytest.fixture
def example(tmp_path):
    """Small transport fixture; real Practice Test 1 is independently tested below."""
    root, bundle = tmp_path / 'project', tmp_path / 'bundle'
    root.mkdir()
    bundle.mkdir()
    (bundle / 'source.pdf').write_bytes(b'fixture source PDF bytes')
    (bundle / 'voice.wav').write_bytes(b'fixture segmented audio bytes')
    write_json(bundle / 'provenance.json', {'examId': 'student-1', 'verified': True})
    source_sha = hashlib.sha256((bundle / 'source.pdf').read_bytes()).hexdigest()
    voice_sha = hashlib.sha256((bundle / 'voice.wav').read_bytes()).hexdigest()
    provenance_sha = hashlib.sha256((bundle / 'provenance.json').read_bytes()).hexdigest()
    sections = []
    for section, kind in [('reading', 'choice'), ('listening', 'choice'), ('writing', 'email'), ('speaking', 'interview')]:
        question = {'id': f'student-1-{section}-1', 'type': kind, 'taskType': kind,
                    'prompt': 'Fixture transport question.', 'presentationSchema': 'structured-v1',
                    'structuredContentStatus': 'source-verified', 'assets': [],
                    'stemBlocks': [{'type': 'question', 'text': 'Fixture transport question.'}],
                    'source': {'materialId': 'pack-source', 'url': '/materials/ets-practice-test-1/source.pdf#page=1', 'page': 1}}
        if kind == 'choice':
            question.update(choices=[{'id': 'A', 'text': 'A source choice.'}, {'id': 'B', 'text': 'Another source choice.'}], answer='A')
        if section == 'listening':
            question['audio'] = {'url': '/assets/ets-practice-test-1/voice.wav', 'durationSeconds': 2,
                                 'materialId': 'pack-source', 'verified': True, 'scope': 'item'}
        sections.append({'id': section, 'title': section.title(), 'modules': [
            {'id': f'{section}-m1', 'title': section.title(), 'durationSeconds': 690,
             'expectedItemCount': 1, 'questions': [question]}]})
    exam = {'schemaVersion': 1, 'id': 'student-1', 'title': 'TOEFL iBT Practice Test 1', 'family': 'student',
            'strictEligible': False,
            'scopedEligibility': {'reading': True, 'listening': True, 'writing': True, 'speaking': False},
            'sourceMaterialIds': ['pack-source'], 'sections': sections,
            'questionCount': 4, 'screenCount': 4, 'verificationInputs': {
                'curationSha256ByPath': {'generated/assets/ets-practice-test-1/provenance.json': provenance_sha},
                'assetSha256ByUrl': {'/assets/ets-practice-test-1/voice.wav': voice_sha},
                'structuredContentSha256ByQuestionId': {q['id']: content_digest(q) for s in sections for m in s['modules'] for q in m['questions']}}}
    write_json(bundle / 'exam.json', exam)
    write_json(bundle / 'catalog.json', {'schemaVersion': 2, 'generatedAt': 'fixture',
        'bundledExample': {'id': 'ets-practice-test-1', 'version': 1}, 'stats': {'fileCount': 1},
        'materials': [{'id': 'pack-source', 'name': 'source.pdf', 'kind': 'pdf',
                      'url': '/materials/ets-practice-test-1/source.pdf', 'sha256': source_sha, 'bytes': 24}],
        'exams': [{k: exam[k] for k in ['id', 'title', 'family', 'questionCount', 'screenCount']}]})
    destinations = {'exam.json': 'generated/exams/student-1.json', 'catalog.json': None,
                    'provenance.json': 'generated/assets/ets-practice-test-1/provenance.json',
                    'source.pdf': 'data/ets-practice-test-1/source.pdf', 'voice.wav': 'generated/assets/ets-practice-test-1/voice.wav'}
    write_json(bundle / 'manifest.json', {'schemaVersion': 1, 'examId': 'student-1',
        'files': [file_record(bundle, path, destination) for path, destination in destinations.items()]})
    return root, bundle


def change_manifest(bundle, mutation):
    path = bundle / 'manifest.json'
    manifest = json.loads(path.read_text())
    mutation(manifest)
    write_json(path, manifest)


def change_exam(bundle, mutation):
    """Sign transport edits so a test reaches semantic rather than hash checks."""
    path = bundle / 'exam.json'
    exam = json.loads(path.read_text())
    mutation(exam)
    exam['verificationInputs']['structuredContentSha256ByQuestionId'] = {
        q['id']: content_digest(q) for section in exam['sections']
        for module in section['modules'] for q in module['questions']}
    write_json(path, exam)
    change_manifest(bundle, lambda manifest: manifest['files'].__setitem__(
        next(i for i, record in enumerate(manifest['files']) if record['path'] == 'exam.json'),
        file_record(bundle, 'exam.json', 'generated/exams/student-1.json')))


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_native_install_validates_sources_and_keeps_timed_modules(example):
    root, bundle = example
    result = install_example(root, bundle)
    assert result['examIds'] == ['student-1'] and result['reused'] is False
    catalog = Catalog(root)
    exam = catalog.exams['student-1']
    assert SourceIntegrity(root, catalog).check_exam(exam)['status'] == 'passed'
    plan = make_plan(exam, {'scope': 'all', 'mode': 'practice'}, DEFAULT_TIMING)
    assert [stage['section'] for stage in plan] == ['reading', 'listening', 'writing', 'speaking']
    assert [stage['timer'] for stage in plan] == ['shared', 'item', 'shared', 'untimed']
    assert plan[0]['seconds'] == 690 and plan[2]['seconds'] == 420
    assert exam['strictEligible'] is False
    for scope in ['reading', 'listening', 'writing']:
        assert new_session(exam, {'scope': scope, 'mode': 'strict'}, 0)['mode'] == 'strict'
    for scope in ['all', 'speaking']:
        with pytest.raises(ExamError, match='not passed strict-practice'):
            new_session(exam, {'scope': scope, 'mode': 'strict'}, 0)
    assert catalog.data['bundledExample'] == {'id': 'ets-practice-test-1', 'version': 1}


@pytest.mark.parametrize('scope', ['all', 'speaking'])
def test_missing_interview_audio_cannot_be_promoted_to_strict_eligibility(example, scope):
    root, bundle = example
    if scope == 'all':
        change_exam(bundle, lambda exam: exam.update(strictEligible=True))
    else:
        change_exam(bundle, lambda exam: exam['scopedEligibility'].update(speaking=True))
    with pytest.raises(ExamError, match='verified audio'):
        install_example(root, bundle)
    assert snapshot(root) == {}


def test_practice_cannot_silently_omit_an_unavailable_source_question(example):
    root, bundle = example
    change_exam(bundle, lambda exam: exam['sections'][-1]['modules'][0]['questions'][0].update(sourcePromptAvailable=False))
    with pytest.raises(ExamError, match='retain every source question'):
        install_example(root, bundle)
    assert snapshot(root) == {}


def test_unstructured_questions_are_not_accepted_as_verified_native_content(example):
    root, bundle = example
    change_exam(bundle, lambda exam: exam['sections'][0]['modules'][0]['questions'][0].pop('presentationSchema'))
    with pytest.raises(ExamError, match='unverified question content'):
        install_example(root, bundle)
    assert snapshot(root) == {}


def test_existing_valid_native_pack_is_reused_even_if_bundled_revision_changes(example):
    root, bundle = example
    install_example(root, bundle)
    (root / 'storage').mkdir()
    (root / 'storage/practice.sqlite3').write_bytes(b'unchanged session and answer bytes')
    before = snapshot(root)
    (bundle / 'source.pdf').write_bytes(b'changed new bundled edition')
    assert install_example(root, bundle)['reused'] is True
    assert snapshot(root) == before


def test_explicit_upgrade_does_not_replace_a_private_source_import(example):
    root, bundle = example
    install_example(root, bundle)
    before = snapshot(root)
    with pytest.raises(ExamError, match='Private imported exams remain unchanged'):
        install_example(root, bundle, upgrade=True)
    assert snapshot(root) == before


def test_merge_preserves_other_exams_materials_settings_and_session_bytes(example):
    root, bundle = example
    original = {'schemaVersion': 2, 'generatedAt': 'private import', 'custom': {'keep': True},
                'stats': {'scannedPages': 999}, 'materials': [{'id': 'private-source', 'url': '/materials/private.pdf'}],
                'exams': [{'id': 'pack-1', 'title': 'TPO Pack 1'}]}
    write_json(root / 'generated/catalog.json', original)
    write_json(root / 'generated/exams/pack-1.json', {'id': 'pack-1', 'sections': []})
    write_json(root / 'storage/settings.json', {'language': 'zh-CN'})
    (root / 'storage/practice.sqlite3').write_bytes(b'existing frozen sessions')
    before = snapshot(root)
    install_example(root, bundle)
    catalog = json.loads((root / 'generated/catalog.json').read_text())
    assert catalog['custom'] == original['custom'] and catalog['stats']['scannedPages'] == 999
    assert catalog['exams'][0] == original['exams'][0]
    assert catalog['materials'][0] == original['materials'][0]
    assert {e['id'] for e in catalog['exams']} == {'pack-1', 'student-1'}
    assert all((root / path).read_bytes() == value for path, value in before.items() if path != 'generated/catalog.json')


@pytest.mark.parametrize('field,value', [
    ('path', '../source.pdf'), ('path', '/etc/passwd'), ('path', 'sub/../source.pdf'),
    ('installPath', '../../outside.pdf'), ('installPath', 'backend/app.py'),
    ('installPath', 'generated/catalog.json'), ('installPath', 'generated/exams/private.json'),
    ('installPath', 'data/../backend/app.py'), ('installPath', 'data\\source.pdf'),
])
def test_untrusted_manifest_cannot_escape_or_overwrite_code(example, field, value):
    root, bundle = example
    change_manifest(bundle, lambda m: m['files'][2].update({field: value}))
    with pytest.raises(ExamError):
        install_example(root, bundle)
    assert snapshot(root) == {}


@pytest.mark.parametrize('kind', ['source', 'destination', 'bundle-parent'])
def test_symlinked_paths_are_rejected_without_touching_target(example, tmp_path, kind):
    root, bundle = example
    outside = tmp_path / 'outside'
    outside.mkdir()
    if kind == 'source':
        data = (bundle / 'source.pdf').read_bytes()
        (outside / 'source.pdf').write_bytes(data)
        (bundle / 'source.pdf').unlink()
        (bundle / 'source.pdf').symlink_to(outside / 'source.pdf')
    elif kind == 'destination':
        (root / 'data').symlink_to(outside, target_is_directory=True)
    else:
        (outside / 'ets-practice-test-1').symlink_to(bundle, target_is_directory=True)
        (root / 'examples').symlink_to(outside, target_is_directory=True)
    before = snapshot(outside)
    with pytest.raises(ExamError, match='symbolic'):
        install_example(root, None if kind == 'bundle-parent' else bundle)
    assert snapshot(outside) == before
    assert not (root / 'generated/catalog.json').exists()


@pytest.mark.parametrize('mutation', ['missing-file', 'changed-bytes', 'duplicate-source', 'duplicate-destination', 'missing-dependency'])
def test_corrupted_or_incomplete_bundle_never_publishes_catalog(example, mutation):
    root, bundle = example
    if mutation == 'missing-file':
        (bundle / 'voice.wav').unlink()
    elif mutation == 'changed-bytes':
        (bundle / 'source.pdf').write_bytes(b'x' * (bundle / 'source.pdf').stat().st_size)
    elif mutation == 'duplicate-source':
        change_manifest(bundle, lambda m: m['files'].append(deepcopy(m['files'][0])))
    elif mutation == 'duplicate-destination':
        change_manifest(bundle, lambda m: m['files'][3].update(installPath=m['files'][4]['installPath']))
    else:
        change_manifest(bundle, lambda m: m['files'].pop())
    with pytest.raises(ExamError):
        install_example(root, bundle)
    assert snapshot(root) == {}


def test_differing_existing_asset_is_preserved_and_blocks_install(example):
    root, bundle = example
    (root / 'data/ets-practice-test-1').mkdir(parents=True)
    (root / 'data/ets-practice-test-1/source.pdf').write_bytes(b'existing user file')
    before = snapshot(root)
    with pytest.raises(ExamError, match='overwrite'):
        install_example(root, bundle)
    assert snapshot(root) == before


def test_invalid_existing_pack_is_not_silently_replaced(example):
    root, bundle = example
    install_example(root, bundle)
    (root / 'data/ets-practice-test-1/source.pdf').write_bytes(b'damaged private source')
    before = snapshot(root)
    with pytest.raises(ExamError, match='Existing TOEFL iBT Practice Test 1'):
        install_example(root, bundle)
    assert snapshot(root) == before


def test_failed_file_copy_rolls_back_new_files_and_keeps_original_catalog(example, monkeypatch):
    root, bundle = example
    write_json(root / 'generated/catalog.json', {'materials': [], 'exams': [], 'note': 'preserve'})
    before = snapshot(root)
    def interrupted_copy(source, target, *args):
        target.write(b'partial write')
        raise OSError('simulated disk failure')
    monkeypatch.setattr('backend.example_pack.shutil.copyfileobj', interrupted_copy)
    with pytest.raises(ExamError, match='simulated disk failure'):
        install_example(root, bundle)
    assert snapshot(root) == before


def test_post_publish_integrity_failure_restores_original_catalog(example, monkeypatch):
    root, bundle = example
    write_json(root / 'generated/catalog.json', {'materials': [], 'exams': [], 'note': 'preserve'})
    before = snapshot(root)
    check = SourceIntegrity.check_exam
    def fail_installed(integrity, exam):
        if integrity.root == root:
            return {'status': 'invalid', 'issues': [{'code': 'simulated-final-check'}]}
        return check(integrity, exam)
    monkeypatch.setattr(SourceIntegrity, 'check_exam', fail_installed)
    with pytest.raises(ExamError, match='Installed example'):
        install_example(root, bundle)
    assert snapshot(root) == before


def test_catalog_change_during_staging_is_not_overwritten(example, monkeypatch):
    root, bundle = example
    original = {'materials': [], 'exams': [], 'note': 'before'}
    write_json(root / 'generated/catalog.json', original)
    check = SourceIntegrity.check_exam
    def concurrent_change(integrity, exam):
        result = check(integrity, exam)
        if integrity.root != root:
            write_json(root / 'generated/catalog.json', {**original, 'note': 'concurrent import'})
        return result
    monkeypatch.setattr(SourceIntegrity, 'check_exam', concurrent_change)
    with pytest.raises(ExamError, match='catalog changed'):
        install_example(root, bundle)
    assert json.loads((root / 'generated/catalog.json').read_text())['note'] == 'concurrent import'
    assert not (root / 'generated/exams/student-1.json').exists()


def test_real_bundled_pack_is_complete_and_native_on_a_clean_install(tmp_path):
    result = install_example(tmp_path, PROJECT / 'examples/ets-practice-test-1')
    assert result['questions'] == 97 and result['screens'] == 79 and result['materials'] == 13
    catalog = Catalog(tmp_path)
    exam = catalog.exams['student-1']
    summary = catalog.summary(exam)
    assert summary['strictEligible'] is True and summary['structuredReady'] is True
    assert summary['scopedEligibility'] == {'reading': True, 'listening': True, 'writing': True, 'speaking': True}
    assert SourceIntegrity(tmp_path, catalog).check_exam(exam)['status'] == 'passed'
    questions = [q for section in exam['sections'] for module in section['modules'] for q in module['questions']]
    assert len({q['taskType'] for q in questions}) == 12
    assert len(questions) == 79
    assert sum(len(q['blanks']) if q['type'] == 'cloze' else 1 for q in questions) == 97
    plan = make_plan(exam, {'mode': 'practice', 'scope': 'all'}, DEFAULT_TIMING)
    assert len(plan) == 9
    assert [stage['seconds'] for stage in plan if stage['section'] == 'writing'] == [360, 420, 600]
    assert [q['_responseSeconds'] for stage in plan for q in stage['questions'] if q['type'] == 'listen_repeat'] == [8, 8, 10, 10, 10, 12, 12]
    assert sum('textCorrection' in q for q in questions) == 39
    assert all(stage['timer'] != 'untimed' for stage in plan)
    interview = next(stage for stage in plan if stage['id'] == 'speaking-interview')
    assert interview['timer'] == 'item' and len(interview['questions']) == 4
    assert interview['responseWindows'] == [45, 45, 45, 45]
    assert interview['questions'][0]['id'] == 'student-1-s-interview-1-audio'
    assert interview['questions'][0]['audio']['verified'] is True
    assert interview['questions'][0]['mediaAudit']['paperAudioMatch'] is False
    for scope in ['reading', 'listening', 'writing', 'speaking', 'all']:
        strict_session = new_session(exam, {'mode': 'strict', 'scope': scope}, 0)
        assert strict_session['mode'] == 'strict'
        assert all(stage['section'] == scope or scope == 'all' for stage in strict_session['plan'])
    assert all(item['url'].startswith(('/materials/', '/assets/')) for item in catalog.data['materials'])
