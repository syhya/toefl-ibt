#!/usr/bin/env python3
"""Verify and attach the paired ETS teacher audio without creating question text.

The default command is a read-only, offline verification. --install copies only
the 72 manifest-bound original MP3s into the existing teacher material folder;
it never overwrites a different file. Archives and source PDFs are SHA-256 bound.

Importer integration: call attach(exams, materials, root) AFTER the existing
source/structured-text curation has been validated, but BEFORE runtime hashes.
This function intentionally leaves referenceOnly, prompts, transcripts, blocks,
and strict eligibility unchanged. A separately verified presentation migration
must remove reference-mode stimulus text before enabling timed availability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = Path('scripts/verified_teacher_audio.json')
DEFAULT_CACHE = Path('tmp/qa/official-audio-verification')


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def text_digest(value):
    return digest_bytes(str(value).encode('utf-8'))


def read_manifest(root=ROOT, manifest_path=None):
    path = Path(manifest_path) if manifest_path else root / DEFAULT_MANIFEST
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('schemaVersion') != 1 or len(data.get('archives', [])) != 2:
        raise ValueError('Unsupported or incomplete teacher audio manifest')
    return data


def contained(base, relative):
    relative = PurePosixPath(relative)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Unsafe manifest path')
    resolved = (base / str(relative)).resolve()
    if not resolved.is_relative_to(base.resolve()):
        raise ValueError('Manifest path escapes its source directory')
    return resolved


def source_checks(root, archive):
    pdf = contained(root / 'data', archive['sourcePdfPath'])
    if not pdf.is_file() or digest_bytes(pdf.read_bytes()) != archive['sourcePdfSha256']:
        raise ValueError(f"Source teacher PDF missing or changed: {archive['examId']}")
    records = archive['audioFiles']
    if len(records) != 36 or sum(len(r.get('questionIds', [])) for r in records) != 45:
        raise ValueError(f"Unexpected teacher audio coverage: {archive['examId']}")
    qids = [qid for record in records for qid in record.get('questionIds', [])]
    if len(qids) != len(set(qids)):
        raise ValueError('Duplicate teacher audio question mapping')


def playback_asset(root, record, rebuild=False):
    """Verify or rebuild a measured original-audio tail trim; never invent silence."""
    segment = record.get('playbackSegment')
    if segment is None:
        return None
    if (segment.get('sourceSha256') != record['sha256'] or
            segment.get('startSeconds') != 0 or segment.get('sampleRate') != 16000 or
            not 0 < segment.get('frameCount', 0) < record['durationSeconds'] * 16000 or
            segment.get('durationSeconds') != segment['frameCount'] / 16000 or
            segment.get('endSeconds') != segment['durationSeconds'] or
            not str(segment.get('url', '')).startswith('/assets/media/')):
        raise ValueError('Invalid teacher source-audio segment provenance')
    destination = contained(root / 'generated/assets', segment['url'].removeprefix('/assets/'))
    if destination.is_file():
        if digest_bytes(destination.read_bytes()) != segment['sha256']:
            raise ValueError(f'Teacher playback asset changed: {destination}')
        return destination
    if not rebuild:
        return None
    source = contained(root / 'data', record['dataPath'])
    if digest_bytes(source.read_bytes()) != record['sha256']:
        raise ValueError(f'Teacher source audio changed: {source}')
    # Reuse the existing isolated decoder and PCM writer. No ASR, model download,
    # network request, source overwrite, time stretch or speech synthesis occurs.
    runtime = next((p for p in [root / '.venv-media/bin/python', ROOT / '.venv-media/bin/python'] if p.is_file()), Path(sys.executable))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='teacher-audio-') as directory:
        temporary = Path(directory) / 'clip.wav'
        code = ('import sys; from pathlib import Path; '
                'from scripts.segment_media import decode,save_wav; '
                'save_wav(Path(sys.argv[2]),decode(Path(sys.argv[1]))[:int(sys.argv[3])])')
        subprocess.run([str(runtime), '-c', code, str(source), str(temporary), str(segment['frameCount'])],
                       cwd=ROOT, check=True, capture_output=True)
        contents = temporary.read_bytes()
        if digest_bytes(contents) != segment['sha256']:
            raise ValueError('Rebuilt teacher audio differs from the measured PCM clip')
        with destination.open('xb') as output:
            output.write(contents)
    return destination


def verify(root=ROOT, manifest_path=None, cache_dir=None, install=False):
    """Return a complete offline plan; optionally install originals after validation."""
    root = Path(root)
    cache = Path(cache_dir) if cache_dir else root / DEFAULT_CACHE
    manifest = read_manifest(root, manifest_path)
    plans = []
    for archive in manifest['archives']:
        source_checks(root, archive)
        installed = [contained(root / 'data', r['dataPath']) for r in archive['audioFiles']]
        need_archive = not all(p.is_file() for p in installed)
        archive_path = cache / archive['cacheFile']
        payloads = {}
        if need_archive:
            blob = archive_path.read_bytes()
            if len(blob) != archive['bytes'] or digest_bytes(blob) != archive['sha256']:
                raise ValueError(f"Official archive missing, incomplete, or changed: {archive_path}")
            with zipfile.ZipFile(archive_path) as zipped:
                if zipped.testzip() is not None:
                    raise ValueError('Official teacher audio archive CRC failed')
                actual = {name for name in zipped.namelist() if not name.endswith('/')}
                expected = {r['archiveMember'] for r in archive['audioFiles']}
                if actual != expected:
                    raise ValueError('Official archive member inventory differs from manifest')
                for record in archive['audioFiles']:
                    payloads[record['archiveMember']] = zipped.read(record['archiveMember'])
        for record, destination in zip(archive['audioFiles'], installed):
            contents = destination.read_bytes() if destination.exists() else payloads[record['archiveMember']]
            if len(contents) != record['bytes'] or digest_bytes(contents) != record['sha256']:
                raise ValueError(f'Original audio missing or changed: {destination}')
            plans.append({'examId': archive['examId'], 'record': record,
                          'destination': destination, 'contents': contents,
                          'alreadyInstalled': destination.is_file()})
    # Validate every source and target before making any additions.
    if install:
        for plan in plans:
            if plan['alreadyInstalled']:
                continue
            destination = plan['destination']
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('xb') as output:
                output.write(plan['contents'])
    clips = [p['record'] for p in plans if p['record'].get('playbackSegment')]
    available_clips = sum(playback_asset(root, record, rebuild=install) is not None for record in clips)
    return {'schemaVersion': 1, 'status': 'verified-offline' if available_clips == len(clips) else 'sources-verified-playback-assets-missing',
            'installed': install, 'audioFileCount': len(plans),
            'alreadyInstalledCount': sum(p['alreadyInstalled'] for p in plans),
            'newlyInstalledCount': sum(not p['alreadyInstalled'] for p in plans) if install else 0,
            'mappedQuestionCount': sum(len(p['record'].get('questionIds', [])) for p in plans),
            'playbackAssetCount': available_clips, 'expectedPlaybackAssetCount': len(clips),
            'questionTextModified': False, 'networkUsed': False}


def attach(exams, materials, root=ROOT, manifest_path=None):
    """Attach verified original files only; caller owns presentation and eligibility."""
    root = Path(root)
    manifest_path = Path(manifest_path) if manifest_path else root / DEFAULT_MANIFEST
    if not manifest_path.is_file():
        return {'status': 'manifest-not-installed', 'attachedQuestionCount': 0}
    manifest = read_manifest(root, manifest_path)
    by_path = {m['path']: m for m in materials}
    by_exam = {e['id']: e for e in exams}
    planned = []
    skipped = []
    errata_cache = {}

    def corrected_transcript_matches(exam, question, anchor, archive):
        """Accept only an exact signed OCR correction of this original anchor.

        The normal importer attaches audio before text errata. A subsequent
        offline/idempotence check may instead read the corrected catalog.
        Neither path allows arbitrary transcript edits or changes audio mapping.
        """
        from backend.text_corrections import MANIFEST_PATH, read_manifest as read_errata
        expected = (exam.get('verificationInputs') or {}).get('curationSha256ByPath', {}).get(MANIFEST_PATH)
        path = root / MANIFEST_PATH
        if not expected or not path.is_file() or digest_bytes(path.read_bytes()) != expected:
            return False
        if expected not in errata_cache:
            errata_cache[expected] = read_errata(path)['questions']
        correction = errata_cache[expected].get(question['id'])
        if not correction or (correction['materialId'], correction['page'], correction['sourceSha256']) != (
                archive['sourcePdfMaterialId'], anchor['page'], archive['sourcePdfSha256']):
            return False
        return any(patch['path'] == ['transcript'] and text_digest(patch['before']) == anchor['transcriptSha256']
                   and patch['after'] == question.get('transcript') for patch in correction['patches'])
    for archive in manifest['archives']:
        exam = by_exam.get(archive['examId'])
        if exam is None:
            continue
        records = archive['audioFiles']
        if not any(r['dataPath'] in by_path for r in records):
            skipped.append(archive['examId'])
            continue
        source_checks(root, archive)
        questions = {q['id']: q for s in exam['sections'] for m in s['modules'] for q in m['questions']}
        for record in records:
            material = by_path.get(record['dataPath'])
            if not material or material.get('sha256') != record['sha256']:
                raise ValueError(f"Teacher audio inventory missing or changed: {record['dataPath']}")
            actual = contained(root / 'data', record['dataPath'])
            if not actual.is_file() or digest_bytes(actual.read_bytes()) != record['sha256']:
                raise ValueError(f'Installed teacher audio missing or changed: {actual}')
            if record.get('mappingStatus') != 'verified-official-paired-source':
                continue
            for anchor in record.get('questionAnchors', []):
                question = questions.get(anchor['questionId'])
                if question is None or question.get('source', {}).get('materialId') != archive['sourcePdfMaterialId']:
                    raise ValueError(f"Teacher question/source identity changed: {anchor['questionId']}")
                if question.get('source', {}).get('page') != anchor['page']:
                    raise ValueError(f"Teacher question source page changed: {anchor['questionId']}")
                if (text_digest(question.get('transcript', '')) != anchor['transcriptSha256']
                        and not corrected_transcript_matches(exam, question, anchor, archive)):
                    raise ValueError(f"Teacher source transcript changed: {anchor['questionId']}")
            planned.append((exam, questions, archive, record, material))
    # The full mapping and playable files are validated before touching a question.
    for _, _, _, record, _ in planned:
        playback_asset(root, record, rebuild=True)
    attached = 0
    for exam, questions, archive, record, material in planned:
        qids = record.get('questionIds', [])
        group = record['groupId']
        media = {'url': material['url'], 'materialId': material['id'],
                 'sourceUrl': material['url'], 'sourceSha256': material['sha256'],
                 'durationSeconds': record['durationSeconds'], 'mediaType': 'audio',
                 'scope': 'group' if len(qids) > 1 else 'item', 'groupId': group,
                 'verified': True, 'containsResponseWait': False}
        segment = record.get('playbackSegment')
        if segment:
            media.update({key: segment[key] for key in ['url', 'durationSeconds', 'startSeconds', 'endSeconds']})
            media.update({'segmentId': group + '-tail-trim', 'assetSha256': segment['sha256']})
        audit = {'verificationMethod': 'official-paired-archive-filenames-and-local-audio-content-audit',
                 'humanReviewed': False, 'exactTranscriptVerified': record['exactTranscriptVerified'],
                 'officialArchiveUrl': archive['url'], 'officialArchiveSha256': archive['sha256'],
                 'archiveMember': record['archiveMember'],
                 'asrComparison': record.get('asrComparison'),
                 'playbackBoundary': record.get('playbackSegment'),
                 'evidence': ['ETS teacher resource page pairs this archive with this teacher PDF.',
                              'Exact set/module/item-or-range filenames and all 68 stimulus contents checked.',
                              'Original PDF and individual audio SHA-256 are verified before attachment.',
                              'ASR differences are review evidence; ASR never replaces the original question or transcript.']}
        for qid in qids:
            question = questions[qid]
            question['audio'] = dict(media)
            question['mediaAudit'] = dict(audit)
            attached += 1
        target = record.get('directionsForQuestionId')
        if target:
            questions[target]['directionsAudio'] = {**media, 'scope': 'directions'}
        if material['id'] not in exam['sourceMaterialIds']:
            exam['sourceMaterialIds'].append(material['id'])
        associated = exam.setdefault('associatedMaterials', [])
        if not any(m['id'] == material['id'] for m in associated):
            associated.append({k: material[k] for k in ['id', 'name', 'url', 'kind']})
        # Keep manifest in the runtime curation list so changed/missing mappings
        # invalidate an existing strict attempt just like changed source media.
        if manifest_path.is_relative_to(root):
            exam.setdefault('verificationInputs', {}).setdefault('curationSha256ByPath', {})[
                manifest_path.relative_to(root).as_posix()] = digest_bytes(manifest_path.read_bytes())
    return {'status': 'attached-original-audio' if attached else 'not-installed',
            'attachedQuestionCount': attached, 'audioFileCount': len(planned),
            'skippedExamIds': skipped, 'questionTextModified': False,
            'presentationMigrationRequired': bool(attached), 'strictEligibilityChanged': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--cache-dir', type=Path)
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = verify(ROOT, args.manifest, args.cache_dir, args.install)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
