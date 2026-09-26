"""Exact, source-bound transcription errata shared by import and presentation.

A correction names a question, original PDF hash/page, a text-only field path,
and its exact before/after values. There is no general spell-check or grammar
rewrite. Saved answers, option/token identities, media and score snapshots are
never changed when historical sessions are displayed with corrected text.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

MANIFEST_PATH = 'scripts/verified_text_corrections.json'
VERSION = 'source-text-2026-09-07'


def allowed_path(path):
    """Only textual leaves; IDs, input lengths, indexes and URLs stay frozen."""
    if not isinstance(path, list) or not path or not isinstance(path[0], str):
        return False
    if len(path) == 1:
        return path[0] in {'prompt', 'passage', 'context', 'passageTemplate', 'transcript',
                          'answer', 'sentencePrefix', 'terminalPunctuation'}
    if path[0] in {'tokens', 'fixedTokens', 'extraTokens'}:
        return len(path) == 2 and type(path[1]) is int and path[1] >= 0
    if path[0] in {'choices', 'slots', 'blanks'}:
        fields = {'choices': {'text'}, 'slots': {'fixed', 'text'}, 'blanks': {'prefix', 'suffix'}}
        return len(path) == 3 and type(path[1]) is int and path[1] >= 0 and path[2] in fields[path[0]]
    if path[0] != 'stemBlocks' or len(path) < 3 or type(path[1]) is not int or path[1] < 0:
        return False
    tail = path[2:]
    if len(tail) == 1:
        return tail[0] in {'text', 'sender', 'recipient', 'date', 'subject', 'caption'}
    if len(tail) == 2:
        return tail[0] in {'paragraphs', 'items', 'headers'} and type(tail[1]) is int and tail[1] >= 0
    if len(tail) == 3:
        return ((tail[0] == 'turns' and type(tail[1]) is int and tail[1] >= 0 and tail[2] in {'speaker', 'text'})
                or (tail[0] == 'rows' and all(type(i) is int and i >= 0 for i in tail[1:])))
    return False


def field_value(value, path):
    for key in path:
        if isinstance(value, list):
            if type(key) is not int or not 0 <= key < len(value):
                raise ValueError('Correction field index is outside the source question')
        elif not isinstance(value, dict) or not isinstance(key, str) or key not in value:
            raise ValueError('Correction field is missing from the source question')
        value = value[key]
    return value


def validate_record(question_id, record):
    if (not isinstance(record, dict) or not isinstance(record.get('materialId'), str)
            or type(record.get('page')) is not int or record['page'] < 1
            or not re.fullmatch(r'[0-9a-f]{64}', str(record.get('sourceSha256', '')))
            or not isinstance(record.get('patches'), list) or not record['patches']):
        raise ValueError(f'Invalid source text correction record: {question_id}')
    seen = set()
    for source in record.get('evidenceSources', []):
        if (not isinstance(source, dict) or not isinstance(source.get('materialId'), str)
                or type(source.get('page')) is not int or source['page'] < 1
                or not re.fullmatch(r'[0-9a-f]{64}', str(source.get('sourceSha256', '')))):
            raise ValueError(f'Invalid correction evidence source: {question_id}')
    for patch in record['patches']:
        metadata = (isinstance(patch, dict) and isinstance(patch.get('path'), list)
                    and len(patch['path']) == 3 and patch['path'][0] == 'stemBlocks'
                    and isinstance(patch['path'][2], str)
                    and patch['path'][2] in {'sender', 'recipient', 'date', 'subject', 'caption'})
        sentence_literal = (isinstance(patch, dict) and patch.get('path') in
                            [['sentencePrefix'], ['terminalPunctuation']])
        if (not isinstance(patch, dict) or not allowed_path(patch.get('path'))
                or not (isinstance(patch.get('before'), str) or (metadata or sentence_literal) and 'before' in patch and patch['before'] is None)
                or not isinstance(patch.get('after'), str)
                or (not patch['after'].strip() and not metadata) or patch['before'] == patch['after']
                or not isinstance(patch.get('evidence'), str) or not patch['evidence'].strip()):
            raise ValueError(f'Invalid text correction patch: {question_id}')
        if patch['path'] == ['answer'] and (record.get('questionType') != 'build_sentence'
                or patch['before'].casefold() != patch['after'].casefold()):
            raise ValueError(f'Invalid text correction patch: {question_id}; reference answers permit case-only corrections for Build a Sentence')
        if sentence_literal and record.get('questionType') != 'build_sentence':
            raise ValueError(f'Invalid text correction patch: {question_id}; sentence literals require Build a Sentence')
        if patch['path'] == ['terminalPunctuation'] and patch['after'] not in {'.', '?', '!'}:
            raise ValueError(f'Invalid text correction patch: {question_id}; terminal punctuation must be printed punctuation')
        key = tuple(patch['path'])
        if key in seen:
            raise ValueError(f'Duplicate text correction path: {question_id}')
        seen.add(key)
        if patch['path'] == ['passageTemplate'] and re.findall(r'\{\{[^{}]+\}\}', patch['before']) != re.findall(r'\{\{[^{}]+\}\}', patch['after']):
            raise ValueError(f'A text correction must preserve cloze placeholder identities: {question_id}')


def read_manifest(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('schemaVersion') != 1 or not isinstance(data.get('questions'), dict) or not isinstance(data.get('version'), str):
        raise ValueError('Invalid source text correction manifest')
    for question_id, record in data['questions'].items():
        validate_record(question_id, record)
    return data


def corrected_question(question, record, partial=False):
    """Copy text leaves only. Import requires a match; old schemas can omit fields."""
    source = question.get('source', {})
    if (source.get('materialId') != record['materialId'] or source.get('page') != record['page']
            or record.get('questionType') and record['questionType'] != question.get('type')):
        if partial:
            return question, 0
        raise ValueError(f"Correction PDF/page does not match {question['id']}")
    result = deepcopy(question)
    changed = 0
    for patch in record['patches']:
        try:
            current = field_value(result, patch['path'])
        except ValueError:
            # Only reviewed message-header metadata may be inserted. A missing
            # block or changed parent shape still cannot be repaired implicitly.
            try:
                parent = field_value(result, patch['path'][:-1]) if patch['before'] is None else None
            except ValueError:
                if partial:
                    continue
                raise
            if patch['before'] is None and isinstance(parent, dict) and patch['path'][-1] not in parent:
                current = None
            elif partial:
                continue
            else:
                raise
        if current == patch['after']:
            continue
        if current != patch['before']:
            if partial:
                continue
            raise ValueError(f"Text correction is stale: {question['id']} {patch['path']}")
        parent = field_value(result, patch['path'][:-1])
        parent[patch['path'][-1]] = patch['after']
        changed += 1
    return result, changed


def apply_import_corrections(exams, materials, root):
    """Apply the complete manifest in memory before any corrected catalog is published."""
    path = Path(root) / MANIFEST_PATH
    if not path.is_file():
        return {'status': 'not-installed', 'questions': 0, 'fields': 0}
    data = read_manifest(path)
    by_material = {m['id']: m for m in materials}
    seen, pending, count = set(), [], 0
    for exam in exams:
        for section in exam.get('sections', []):
            for module in section.get('modules', []):
                for index, question in enumerate(module.get('questions', [])):
                    record = data['questions'].get(question['id'])
                    if record is None:
                        continue
                    seen.add(question['id'])
                    for bound_source in [record, *record.get('evidenceSources', [])]:
                        material = by_material.get(bound_source['materialId'])
                        if not material or material.get('sha256') != bound_source['sourceSha256']:
                            raise ValueError(f"Text correction source PDF changed: {question['id']}")
                    corrected, changed = corrected_question(question, record)
                    corrected['textCorrection'] = {'version': data['version'], 'changedFields': len(record['patches'])}
                    pending.append((module['questions'], index, corrected))
                    count += changed
    unknown = set(data['questions']) - seen
    if unknown:
        raise ValueError('Text correction references missing questions: ' + ', '.join(sorted(unknown)))
    for questions, index, corrected in pending:
        questions[index] = corrected
    return {'status': 'passed', 'version': data['version'], 'questions': len(pending), 'fields': count}


class TextCorrections:
    """Read current signed errata without changing a frozen session plan on disk."""
    def __init__(self, root, catalog, integrity):
        self.root, self.catalog, self.integrity = Path(root), catalog, integrity
        self._digest, self._data = None, None

    def project(self, session, question):
        # A direct historical review can be the first request after reimport.
        self.catalog.refresh()
        exam = self.catalog.exams.get(session.get('examId'))
        if not exam:
            return question
        inputs = exam.get('verificationInputs') or {}
        relative = inputs.get('textCorrectionsPath', MANIFEST_PATH)
        if not isinstance(relative, str):
            return question
        expected = inputs.get('curationSha256ByPath', {}).get(relative)
        if not expected:
            return question
        path = self.root / relative
        actual = self.integrity.digest(path)
        if not actual or actual != expected:
            return question
        if actual != self._digest:
            try:
                data = read_manifest(path)
            except (OSError, ValueError, TypeError):
                return question
            self._data, self._digest = data, actual
        record = self._data['questions'].get(question.get('id'))
        if not record:
            return question
        for bound_source in [record, *record.get('evidenceSources', [])]:
            material = next((m for m in self.catalog.data.get('materials', []) if m.get('id') == bound_source['materialId']), None)
            asset_id = self.catalog.register(material.get('url')) if material else None
            source_path = self.catalog.path_for(asset_id) if asset_id else None
            if (not source_path or material.get('sha256') != bound_source['sourceSha256']
                    or self.integrity.digest(source_path) != bound_source['sourceSha256']):
                return question
        corrected, changed = corrected_question(question, record, partial=True)
        if changed:
            corrected['textCorrection'] = {'version': self._data['version'], 'changedFields': changed}
        return corrected
