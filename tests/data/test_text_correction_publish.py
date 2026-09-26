"""Reject stale source errata without replacing the published question archive.

The real collection-import entry point, bank builder, Essentials publisher and
correction validator run here. Only PDF/OCR/audio preparation is substituted;
all source and published files are disposable fixtures under ``tmp_path``.
"""
from copy import deepcopy
import hashlib
import json
import sys

import pytest

from backend.text_corrections import MANIFEST_PATH, VERSION


@pytest.mark.parametrize('target_exam', ['pack-1', 'essentials-3'])
def test_stale_correction_preserves_all_published_archive_metadata(tmp_path, monkeypatch, target_exam):
    from scripts import import_materials as importer
    from scripts import import_essentials as essentials
    from scripts import attach_source_explanations, structure_questions, extract_structured_visuals
    from scripts import attach_teacher_audio, teacher_audio_presentation, attach_pack_directions

    for key, relative in {'ROOT': '.', 'DATA': 'data', 'OUT': 'generated',
                          'ASSETS': 'generated/assets', 'CACHE': 'generated/extracted'}.items():
        path = tmp_path / relative
        path.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(importer, key, path)
    monkeypatch.setattr(essentials, 'ROOT', tmp_path)
    monkeypatch.setattr(sys, 'argv', ['import_materials.py', '--jobs', '1'])
    (tmp_path / 'scripts').mkdir()
    for name in ['cloze', 'choices', 'paid', 'paper', 'editions', 'blocks',
                 'structured_content', 'structured_essentials', 'teacher_audio', 'pack_directions']:
        (tmp_path / 'scripts' / f'verified_{name}.json').write_text('{}')

    exam_ids = [f'{family}-{number}' for family, count in [
        ('experience', 3), ('pack', 6), ('student', 2), ('teacher', 2), ('paid', 2), ('essentials', 3)
    ] for number in range(1, count + 1)]
    materials = []
    for eid in exam_ids:
        content = ('source fixture for ' + eid).encode()
        source_path = tmp_path / 'data' / f'{eid}.pdf'
        source_path.write_bytes(content)
        materials.append({'id': f'source-{eid}', 'category': eid.rsplit('-', 1)[0],
                          'examIds': [eid], 'kind': 'pdf', 'scanned': True,
                          'name': f'2026-{eid}.pdf', 'path': source_path.name,
                          'url': f'/materials/{source_path.name}', 'bytes': len(content),
                          'sha256': hashlib.sha256(content).hexdigest()})
    by_exam = {m['examIds'][0]: m for m in materials}
    prepared, built = [], []

    def prepare_pdf(material, jobs=1):
        prepared.append(material['id'])
        return [{'page': 1, 'text': 'Current fixture wording.'}]

    def section(eid, sid):
        question = {'id': f'{eid}-{sid}-q1', 'number': 1, 'type': 'choice',
                    'taskType': 'academic_passage', 'prompt': 'Current fixture wording.',
                    'choices': [{'id': 'A', 'text': 'First fixture option.'},
                                {'id': 'B', 'text': 'Second fixture option.'}],
                    'answer': 'A', 'assets': [], 'presentationSchema': 'structured-v1',
                    'stemBlocks': [{'type': 'question', 'text': 'Current fixture wording.'}],
                    'source': {'materialId': by_exam[eid]['id'], 'page': 1}}
        return {'id': sid, 'modules': [{'id': f'{sid}-module', 'expectedItemCount': 1,
                                       'questions': [question]}],
                'matchedAudioQuestionCount': 0, 'interactiveQuestionCount': 1}

    def source_exam(number, material, pages, all_materials, *, config=None, exam_id=None):
        eid = exam_id or material['examIds'][0]
        built.append(eid)
        return {'id': eid, 'title': eid, 'family': eid.rsplit('-', 1)[0],
                'warnings': [], 'strictEligible': False, 'sections': [section(eid, 'reading')]}

    monkeypatch.setattr(importer, 'inventory', lambda: deepcopy(materials))
    monkeypatch.setattr(importer, 'prepare_pdf', prepare_pdf)
    monkeypatch.setattr(importer, 'experience_exam', source_exam)
    monkeypatch.setattr(importer, 'pack_exam', source_exam)
    monkeypatch.setattr(importer, 'paid_exam', lambda n, base, items: source_exam(
        n, by_exam[f'paid-{n}'], [], items))
    monkeypatch.setattr(importer, 'enrich_questions', lambda *args: None)

    # Keep the real Essentials orchestration, including its publish flag. Stub
    # its section parsers instead of replacing the function that writes files.
    monkeypatch.setattr(essentials, 'keys_for', lambda items, eid: (
        {sid: {} for sid in ['reading', 'listening', 'writing']}, by_exam[eid]))
    monkeypatch.setattr(essentials, 'source_material', lambda items, eid, label: by_exam[eid])
    for sid in ['reading', 'listening', 'writing', 'speaking']:
        monkeypatch.setattr(essentials, f'build_{sid}',
                            lambda helpers, eid, *args, sid=sid: section(eid, sid))
    for module, name in [(attach_source_explanations, 'attach'), (structure_questions, 'apply'),
                         (extract_structured_visuals, 'build'), (attach_teacher_audio, 'attach'),
                         (teacher_audio_presentation, 'finalize'), (attach_pack_directions, 'attach')]:
        monkeypatch.setattr(module, name, lambda *args: {})

    generated = tmp_path / 'generated'
    published_paths = [*(generated / 'exams' / f'{eid}.json' for eid in exam_ids),
                       *(generated / name for name in ['catalog.json', 'question-bank.json',
                                                       'deduplication.json', 'audit.json'])]
    for path in published_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'publishedBeforeImport': path.name}) + '\n')
    before = {path.relative_to(generated): path.read_bytes() for path in published_paths}

    material = by_exam[target_exam]
    correction = {'schemaVersion': 1, 'version': VERSION, 'questions': {
        f'{target_exam}-reading-q1': {
            'materialId': material['id'], 'sourceSha256': material['sha256'], 'page': 1,
            'patches': [{'path': ['prompt'], 'before': 'An obsolete extraction that no longer matches.',
                         'after': 'Reviewed fixture wording.',
                         'evidence': 'Synthetic stale-field fixture bound to the exact source bytes.'}],
        },
    }}
    (tmp_path / MANIFEST_PATH).write_text(json.dumps(correction))

    with pytest.raises(ValueError, match=f'Text correction is stale: {target_exam}-reading-q1'):
        importer.main()

    # Ensure the real entry point traversed every collection before rejecting,
    # rather than passing because it exited before the former early writes.
    assert set(built) == set(exam_ids) - {'essentials-1', 'essentials-2', 'essentials-3'}
    assert set(prepared) == {m['id'] for m in materials}
    after = {path.relative_to(generated): path.read_bytes()
             for path in generated.glob('*.json')}
    after.update({path.relative_to(generated): path.read_bytes()
                  for path in (generated / 'exams').glob('*.json')})
    assert after == before
