"""Official Practice Test 1 fidelity checks run in every checkout, without the private bank."""
import hashlib
import json
from pathlib import Path

from backend.engine import DEFAULT_TIMING, make_plan
from backend.presentation import content_digest, validate_question
from backend.text_corrections import field_value, read_manifest

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / 'examples/ets-practice-test-1'


def read(name):
    return json.loads((BUNDLE / name).read_text())


def test_complete_native_practice_test_one_keeps_all_source_tasks_and_clocks():
    exam = read('exam.json')
    assert exam['id'] == 'student-1'
    assert exam['strictEligible'] is True
    assert [s['id'] for s in exam['sections']] == ['reading', 'listening', 'writing', 'speaking']
    questions = [q for s in exam['sections'] for m in s['modules'] for q in m['questions']]
    assert len(questions) == exam['screenCount'] == 79
    assert sum(len(q['blanks']) if q['type'] == 'cloze' else 1 for q in questions) == exam['questionCount'] == 97
    assert len({q['taskType'] for q in questions}) == 12
    assert all(q['id'].startswith('student-1-') and not validate_question(q, strict=True) for q in questions)
    modules = {m['id']: m for s in exam['sections'] for m in s['modules']}
    assert len(modules) == 9
    plan = make_plan(exam, {'mode': 'practice', 'scope': 'all'}, DEFAULT_TIMING)
    assert [stage['seconds'] for stage in plan if stage['timer'] == 'shared'] == [900, 900, 360, 420, 600]
    assert [q['_responseSeconds'] for stage in plan if stage['section'] == 'speaking' for q in stage['questions'] if q['type'] == 'listen_repeat'] == [8, 8, 10, 10, 10, 12, 12]
    assert [q['_responseSeconds'] for stage in plan if stage['section'] == 'speaking' for q in stage['questions'] if q['type'] == 'interview'] == [45] * 4


def test_bundle_carries_corrected_text_and_original_source_evidence():
    exam = read('exam.json')
    provenance = read('provenance.json')
    errata = read_manifest(BUNDLE / 'text-corrections.json')
    questions = {q['id']: q for s in exam['sections'] for m in s['modules'] for q in m['questions']}
    assert set(provenance['questionIds']) == set(questions)
    for qid, q in questions.items():
        assert content_digest(q) == provenance['contentSha256ByQuestionId'][qid]
        if qid != 'student-1-s-interview-1-audio':
            assert q['source']['materialId'] == 'mat-3e0bfa577216' and 1 <= q['source']['page'] <= 36, qid
    assert len(errata['questions']) == provenance['textCorrectionScreens'] == 39
    assert sum(len(r['patches']) for r in errata['questions'].values()) == provenance['textCorrectionFields'] == 71
    for qid, record in errata['questions'].items():
        q = questions[qid]
        assert q['source']['materialId'] == record['materialId']
        assert q['source']['page'] == record['page']
        assert record['sourceSha256'] == provenance['sourceSha256ById'][record['materialId']]
        for patch in record['patches']:
            assert field_value(q, patch['path']) == patch['after']
    interview = questions['student-1-s-interview-1-audio']
    assert not interview.get('referenceOnly')
    assert interview['audio']['verified'] is True
    assert interview['mediaAudit']['paperAudioMatch'] is False
    assert 'last time you visited a city' in interview['transcript']
    assert 'currently live' in interview['sourceVariant']['paperPrompt']
    assert 'explanationSource' not in interview
    assert exam['scopedEligibility'] == {'reading': True, 'listening': True, 'writing': True, 'speaking': True}


def test_practice_test_one_bundle_hashes_do_not_depend_on_private_manifests():
    manifest = read('manifest.json')
    installed = {}
    for entry in manifest['files']:
        raw = (BUNDLE / entry['path']).read_bytes()
        assert len(raw) == entry['bytes']
        assert hashlib.sha256(raw).hexdigest() == entry['sha256'], entry['path']
        if entry['installPath']:
            assert entry['installPath'] not in installed
            installed[entry['installPath']] = entry['sha256']
    inputs = read('exam.json')['verificationInputs']
    assert inputs['curationSha256ByPath']
    for path, digest in inputs['curationSha256ByPath'].items():
        assert not path.startswith('scripts/')
        assert installed[path] == digest
    catalog = read('catalog.json')
    assert len(catalog['materials']) == 13
    assert {e['id'] for e in catalog['exams']} == {'student-1'}
    assert catalog['supplementalExams'] == []


def test_recorded_official_pdf_identity_and_readme_attribution():
    url = 'https://www.in.ets.org/content/dam/ets-india/pdfs/toefl/toefl-ibt-full-length-practice-test-1.pdf'
    expected = '33e37aac4324d36a01af7ac0eb67b06aa438dfdf4fc96e31f4bdb72d9b8d9a2d'
    provenance = read('provenance.json')['officialPdf']
    assert provenance['url'] == url and provenance['sha256'] == expected
    assert provenance['pages'] == 36 and provenance['downloadMatchesLocalBytes'] is True
    catalog = read('catalog.json')
    pdf = next(m for m in catalog['materials'] if m['id'] == provenance['materialId'])
    manifest = read('manifest.json')
    original = manifest['optionalOriginals'][pdf['id']]
    assert original['sha256'] == expected
    assert original['installPath'] == 'data/' + pdf['path']
    assert not any(f['path'].startswith('materials/') for f in manifest['files'])
    # An optional local original can verify the historical fingerprint, but a
    # public checkout must not require that file or a fresh network download.
    source = BUNDLE / original['bundlePath']
    if source.is_file():
        assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
    # The concise project READMEs delegate source details to the linked notice.
    # Keep that attribution path intact and verify the notice's source identity.
    notice_path = 'examples/ets-practice-test-1/NOTICE.md'
    for language in ['', '.zh-CN']:
        assert f']({notice_path})' in (ROOT / ('README' + language + '.md')).read_text()
    notice = (ROOT / notice_path).read_text()
    assert f']({url})' in notice
    assert expected in notice
    # No source data from the superseded TPO example belongs in the new bundle.
    assert not (ROOT / 'examples/tpo-pack-1').exists()
    assert all('student-1' in f['path'] or not f['path'].startswith('assets/') for f in read('manifest.json')['files'])
