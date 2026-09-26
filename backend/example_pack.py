"""Install the bundled, native TOEFL iBT Practice Test 1 without rebuilding private materials.

Unlike portable user-authored packs, this bundle retains the original exam,
media segmentation, source hashes, and timed modules. Validate in an isolated
directory first; publish the merged catalog only after every dependency exists.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
import threading

from .catalog import Catalog
from .engine import DEFAULT_TIMING, ExamError, make_plan, new_session
from .integrity import SourceIntegrity
from .presentation import validate_question
from .prepared_sources import PROFILE, LEGACY_PROFILE

_LOCK = threading.RLock()
_HASH = re.compile(r'^[0-9a-f]{64}$')
_EXAM_PATH = 'generated/exams/student-1.json'
_CATALOG_PATH = 'generated/catalog.json'


def _relative(value):
    """Accept normalized local POSIX paths, never aliases or traversal."""
    if (not isinstance(value, str) or not value or '\\' in value or '\x00' in value
            or ':' in value or PurePosixPath(value).is_absolute()
            or str(PurePosixPath(value)) != value
            or any(part in {'.', '..'} or part.startswith('.') for part in value.split('/'))):
        raise ExamError('Bundled example contains an unsafe file path.', 422)
    return value


def _safe_path(root, relative):
    path = root
    for part in _relative(relative).split('/'):
        path = path / part
        if path.is_symlink():
            raise ExamError('Bundled example paths cannot contain symbolic links.', 422)
    if not path.resolve().is_relative_to(root):
        raise ExamError('Bundled example path is outside the project folder.', 422)
    return path


def _digest(path):
    value = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def _read_json(path):
    try:
        result = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError, UnicodeError) as error:
        raise ExamError('Bundled example JSON is missing or invalid.', 422) from error
    if not isinstance(result, dict):
        raise ExamError('Bundled example JSON must contain an object.', 422)
    return result


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()


def _result(exam, reused, material_count=0, file_count=0):
    return {'id': 'student-1', 'examIds': ['student-1'], 'title': exam.get('title', 'TOEFL iBT Practice Test 1'),
            'reused': reused, 'questions': exam.get('questionCount', 0),
            'screens': exam.get('screenCount', 0), 'materials': material_count, 'files': file_count}


def _validate_existing(root):
    """Existing verified private Practice Test 1 always wins over the bundled revision."""
    try:
        catalog = Catalog(root)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ExamError('The local catalog is invalid. Restore it before installing the example.', 409) from error
    existing = catalog.exams.get('student-1')
    if existing is not None:
        if SourceIntegrity(root, catalog).check_exam(existing)['status'] != 'passed':
            raise ExamError('Existing TOEFL iBT Practice Test 1 has missing or changed sources. Reimport or restore it before installing the example.', 409)
        return _result(existing, True, len(existing.get('sourceMaterialIds', [])))
    if (root / _EXAM_PATH).exists():
        raise ExamError('An unregistered TOEFL iBT Practice Test 1 file already exists. Restore its catalog before installing the example.', 409)
    return None


def _merge_catalog(existing, bundled, replace_exam=False):
    if not isinstance(bundled.get('materials'), list) or not isinstance(bundled.get('exams'), list):
        raise ExamError('Bundled example catalog is missing materials or exams.', 422)
    if len(bundled['exams']) != 1 or bundled['exams'][0].get('id') != 'student-1':
        raise ExamError('Bundled example catalog must contain only TOEFL iBT Practice Test 1.', 422)
    result = deepcopy(existing if existing is not None else bundled)
    if existing is None:
        return result
    result.setdefault('materials', [])
    result.setdefault('exams', [])
    for material in bundled['materials']:
        if not isinstance(material, dict) or not isinstance(material.get('id'), str):
            raise ExamError('Bundled example material metadata is invalid.', 422)
        collisions = [m for m in result['materials'] if m.get('id') == material['id'] or m.get('url') == material.get('url')]
        if collisions:
            if any(m.get('id') != material['id'] or m.get('url') != material.get('url')
                   or m.get('sha256') != material.get('sha256') for m in collisions):
                raise ExamError('Bundled example conflicts with an existing source material.', 409)
            continue
        result['materials'].append(deepcopy(material))
    if replace_exam:
        result['exams'] = [deepcopy(bundled['exams'][0]) if item.get('id') == 'student-1' else item for item in result['exams']]
    else:
        result['exams'].append(deepcopy(bundled['exams'][0]))
    stats = result.setdefault('stats', {})
    # Preserve unrelated private-catalog statistics and metadata. Only these
    # aggregate counts can be recalculated from the merged public summaries.
    stats['materialFileCount'] = len(result['materials'])
    stats['fileCount'] = len(result['materials']) + len(result.get('excludedSystemFiles', []))
    for key in ['examCount', 'screenCount', 'questionCount']:
        if key == 'examCount':
            stats[key] = len(result['exams'])
        elif all(type(item.get(key)) is int for item in result['exams']):
            stats[key] = sum(item[key] for item in result['exams'])
    if all(type(item.get('strictEligible')) is bool for item in result['exams']):
        stats['strictExamCount'] = sum(item['strictEligible'] for item in result['exams'])
    result['bundledExample'] = deepcopy(bundled.get('bundledExample', {'id': 'ets-practice-test-1', 'version': 1}))
    return result


def _preflight(root, bundle, replace_exam=False):
    manifest = _read_json(_safe_path(bundle, 'manifest.json'))
    if type(manifest.get('schemaVersion')) is not int or manifest['schemaVersion'] != 1 or manifest.get('examId') != 'student-1':
        raise ExamError('Bundled example requires schemaVersion 1 and examId student-1.', 422)
    if not isinstance(manifest.get('files'), list) or not manifest['files']:
        raise ExamError('Bundled example file manifest is empty.', 422)
    entries, sources, destinations = [], set(), set()
    for record in manifest['files']:
        if (not isinstance(record, dict) or not _HASH.fullmatch(str(record.get('sha256', '')))
                or type(record.get('bytes')) is not int or record['bytes'] < 0):
            raise ExamError('Bundled example file metadata is invalid.', 422)
        source_name = _relative(record.get('path'))
        if source_name in sources:
            raise ExamError('Bundled example lists a source file more than once.', 422)
        sources.add(source_name)
        source = _safe_path(bundle, source_name)
        if not source.is_file() or source.stat().st_size != record['bytes'] or _digest(source) != record['sha256']:
            raise ExamError(f'Bundled example file is missing or changed: {source_name}', 422)
        destination_name = record.get('installPath')
        destination = None
        if destination_name is not None:
            destination_name = _relative(destination_name)
            if not (destination_name == _EXAM_PATH or destination_name.startswith(('data/', 'generated/assets/'))):
                raise ExamError('Bundled example may install only its exam and local resource files.', 422)
            if destination_name in destinations:
                raise ExamError('Bundled example lists a destination more than once.', 422)
            destinations.add(destination_name)
            destination = _safe_path(root, destination_name)
            if (destination.exists() and (not destination.is_file() or _digest(destination) != record['sha256'])
                    and not (replace_exam and destination_name == _EXAM_PATH and destination.is_file())):
                raise ExamError(f'Bundled example would overwrite an existing file: {destination_name}', 409)
        entries.append({**record, 'source': source, 'destination': destination})
    if not {'exam.json', 'catalog.json'} <= sources:
        raise ExamError('Bundled example manifest must verify exam.json and catalog.json.', 422)
    exam_entry = next(item for item in entries if item['path'] == 'exam.json')
    catalog_entry = next(item for item in entries if item['path'] == 'catalog.json')
    if exam_entry.get('installPath') != _EXAM_PATH or catalog_entry.get('installPath') is not None:
        raise ExamError('Bundled example exam or catalog destination is invalid.', 422)
    exam = _read_json(exam_entry['source'])
    if exam.get('id') != 'student-1' or type(exam.get('strictEligible')) is not bool:
        raise ExamError('Bundled example must preserve the native timed TOEFL iBT Practice Test 1 exam.', 422)
    sections = exam.get('sections', [])
    if [section.get('id') for section in sections] != ['reading', 'listening', 'writing', 'speaking']:
        raise ExamError('Bundled example must include all four ordered sections.', 422)
    for section in sections:
        questions = [q for m in section.get('modules', []) for q in m.get('questions', [])]
        if not questions or any(q.get('presentationSchema') != 'structured-v1'
                                or validate_question(q, strict=True) for q in questions):
            raise ExamError('Bundled example contains missing or unverified question content.', 422)
    # Retain all selected source questions and validate actual media. A declared
    # audio edition is allowed; missing audio may never be promoted by a flag.
    practice = make_plan(exam, {'mode': 'practice', 'scope': 'all'}, DEFAULT_TIMING)
    if sum(len(stage['questions']) for stage in practice) != sum(
            len(module.get('questions', [])) for section in sections for module in section.get('modules', [])):
        raise ExamError('Bundled example practice must retain every source question.', 422)
    scoped = exam.get('scopedEligibility', {})
    if (not isinstance(scoped, dict) or any(type(scoped.get(section)) is not bool
                                         for section in ['reading', 'listening', 'writing', 'speaking'])
            or not all(scoped.get(section) for section in ['reading', 'listening', 'writing'])):
        raise ExamError('Bundled example must preserve its verified reading, listening, and writing scopes.', 422)
    for scope in (['all'] if exam['strictEligible'] else [section for section, eligible in scoped.items() if eligible]):
        # Session validation also checks stimulus audio and rejects falsely
        # enabled strict scopes, while creating no stored session or answer.
        new_session(exam, {'mode': 'strict', 'scope': scope}, 0)
    bundled_catalog = _read_json(catalog_entry['source'])
    catalog_path = _safe_path(root, _CATALOG_PATH)
    previous_catalog = catalog_path.read_bytes() if catalog_path.exists() else None
    existing_catalog = json.loads(previous_catalog) if previous_catalog is not None else None
    merged = _merge_catalog(existing_catalog, bundled_catalog, replace_exam)
    return entries, exam, merged, previous_catalog


def _make_parents(path, root, created):
    relative = path.parent.relative_to(root)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ExamError('Bundled example paths cannot contain symbolic links.', 422)
        if not current.exists():
            current.mkdir()
            created.append(current)
        elif not current.is_dir():
            raise ExamError('Bundled example destination parent is not a directory.', 409)


def install_example(root: Path, bundle: Path | None = None, *, upgrade=False):
    """Install or reuse Practice Test 1, with validation and rollback before publication.

    ``bundle`` is an explicit test/CLI override. HTTP callers use only the
    repository's examples/ets-practice-test-1 directory, never a user-supplied URL.
    An explicit upgrade may replace a verified v2 bundled exam with v3. Private
    imports, stored sessions, old media and versioned provenance stay untouched.
    """
    with _LOCK:
        root = Path(root).resolve()
        if not root.is_dir():
            raise ExamError('The project folder does not exist.', 422)
        _safe_path(root, _CATALOG_PATH)
        _safe_path(root, _EXAM_PATH)
        reused = _validate_existing(root)
        previous_exam = None
        if reused is not None and upgrade:
            existing = Catalog(root).exams['student-1']
            if existing.get('bundledExample') == PROFILE:
                return reused
            if existing.get('bundledExample') != LEGACY_PROFILE:
                raise ExamError('Only a verified lightweight v2 example can be upgraded. Private imported exams remain unchanged.', 409)
            previous_exam = (root / _EXAM_PATH).read_bytes()
        elif reused is not None:
            return reused
        bundle = Path(bundle) if bundle is not None else _safe_path(root, 'examples/ets-practice-test-1')
        if bundle.is_symlink():
            raise ExamError('Bundled example paths cannot contain symbolic links.', 422)
        bundle = bundle.resolve()
        if not bundle.is_dir() or not (bundle / 'manifest.json').is_file():
            raise ExamError('The TOEFL iBT Practice Test 1 example is missing. Restore examples/ets-practice-test-1.', 404)
        try:
            entries, exam, merged, previous_catalog = _preflight(root, bundle, previous_exam is not None)
            if previous_exam is not None and exam.get('bundledExample') != PROFILE:
                raise ExamError('The upgrade must target the current verified example profile.', 422)
            with tempfile.TemporaryDirectory(prefix='toefl-example-') as temporary:
                stage = Path(temporary)
                for item in entries:
                    if item['destination'] is None:
                        continue
                    target = stage / item['installPath']
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(item['source'], target)
                    if _digest(target) != item['sha256']:
                        raise ExamError('Bundled example changed during validation.', 422)
                staged_catalog = stage / _CATALOG_PATH
                staged_catalog.parent.mkdir(parents=True, exist_ok=True)
                staged_catalog.write_bytes(_json_bytes(merged))
                catalog = Catalog(stage)
                report = SourceIntegrity(stage, catalog).check_exam(catalog.exams['student-1'])
                if report['status'] != 'passed':
                    raise ExamError('Bundled example failed source integrity: ' + ', '.join(item['code'] for item in report['issues']), 422)
                _publish(root, stage, entries, merged, previous_catalog, previous_exam)
        except ExamError:
            raise
        except (OSError, ValueError, TypeError, KeyError) as error:
            raise ExamError(f'Bundled example could not be installed: {error}', 422) from error
        return {**_result(exam, False, len(merged['materials']), sum(item['destination'] is not None for item in entries)),
                'upgraded': previous_exam is not None}


def _publish(root, stage, entries, merged, previous, previous_exam=None):
    """Create only absent files and replace the catalog as the final write."""
    created_files, created_dirs = [], []
    catalog_path = _safe_path(root, _CATALOG_PATH)
    if (catalog_path.read_bytes() if catalog_path.exists() else None) != previous:
        raise ExamError('The local catalog changed during example installation. Try again.', 409)
    published, temp_catalog, replaced_exam, temp_exam = False, None, False, None
    try:
        for item in entries:
            if item['destination'] is None:
                continue
            target = _safe_path(root, item['installPath'])
            if target.exists():
                if previous_exam is not None and item['installPath'] == _EXAM_PATH:
                    if target.read_bytes() != previous_exam:
                        raise ExamError('The installed example changed during upgrade.', 409)
                    with tempfile.NamedTemporaryFile(prefix='.example-', dir=target.parent, delete=False) as handle:
                        temp_exam = Path(handle.name)
                        handle.write((stage / item['installPath']).read_bytes())
                        handle.flush(); os.fsync(handle.fileno())
                    temp_exam.replace(target)
                    temp_exam, replaced_exam = None, True
                    continue
                if not target.is_file() or _digest(target) != item['sha256']:
                    raise ExamError('A local resource changed during example installation.', 409)
                continue
            _make_parents(target, root, created_dirs)
            # Exclusive creation also catches a file introduced after preflight.
            with target.open('xb') as destination:
                created_files.append(target)
                with (stage / item['installPath']).open('rb') as source:
                    shutil.copyfileobj(source, destination)
            if _digest(target) != item['sha256']:
                raise ExamError('An installed example file failed verification.', 422)
        _safe_path(root, _CATALOG_PATH)
        current = catalog_path.read_bytes() if catalog_path.exists() else None
        if current != previous:
            raise ExamError('The local catalog changed during example installation. Try again.', 409)
        _make_parents(catalog_path, root, created_dirs)
        with tempfile.NamedTemporaryFile(prefix='.catalog-', suffix='.json', dir=catalog_path.parent, delete=False) as handle:
            temp_catalog = Path(handle.name)
            handle.write(_json_bytes(merged))
            handle.flush()
            os.fsync(handle.fileno())
        temp_catalog.replace(catalog_path)
        temp_catalog = None
        published = True
        catalog = Catalog(root)
        if SourceIntegrity(root, catalog).check_exam(catalog.exams['student-1'])['status'] != 'passed':
            raise ExamError('Installed example failed source integrity.', 422)
    except Exception:
        if replaced_exam:
            (root / _EXAM_PATH).write_bytes(previous_exam)
        if temp_exam is not None:
            temp_exam.unlink(missing_ok=True)
        if published:
            if previous is None:
                catalog_path.unlink(missing_ok=True)
            else:
                catalog_path.write_bytes(previous)
        for path in reversed(created_files):
            path.unlink(missing_ok=True)
        if temp_catalog is not None:
            temp_catalog.unlink(missing_ok=True)
        for path in reversed(created_dirs):
            try:
                path.rmdir()
            except OSError:
                pass
        raise
