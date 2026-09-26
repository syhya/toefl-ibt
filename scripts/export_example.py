"""Prepare the complete official student Practice Test 1 from verified local data.

The downloaded ETS PDF must match the supplied question PDF byte for byte.
This command never changes the private question bank or personal sessions.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.catalog import Catalog
from backend.integrity import SourceIntegrity
from backend.presentation import content_digest
from backend.prepared_sources import PROFILE, PROVENANCE
from scripts.example_audio_edition import prepare_audio_edition

EXAM_ID = 'student-1'
BUNDLE_ID = 'ets-practice-test-1'
SOURCE_URL = 'https://www.in.ets.org/content/dam/ets-india/pdfs/toefl/toefl-ibt-full-length-practice-test-1.pdf'
SOURCE_MATERIAL_ID = 'mat-3e0bfa577216'

# Public bundle names are independent of the original private archive layout.
# Keep installed paths/source URLs stable so existing sessions remain valid.
MATERIAL_FILENAMES = {
    'mat-3e0bfa577216': 'toefl-ibt-practice-test-1.pdf',
    'mat-e076415a17d6': 'practice-test-1-companion-explanations.pdf',
    'mat-4bd232d56357': 'practice-test-1-speaking-listen-and-repeat.mp3',
    'mat-0851ff6f24bd': 'practice-test-1-speaking-interview.mp3',
    'mat-3da881e3980a': 'practice-test-1-listening-module-1-listen-and-choose-a-response.mp3',
    'mat-6da99819f979': 'practice-test-1-listening-module-1-conversation-1.mp3',
    'mat-d2c9cf02ac26': 'practice-test-1-listening-module-1-conversation-2.mp3',
    'mat-238127e7064b': 'practice-test-1-listening-module-1-announcement.mp3',
    'mat-576ebde803ab': 'practice-test-1-listening-module-1-academic-talk.mp3',
    'mat-b3b341c1f4ff': 'practice-test-1-listening-module-2-listen-and-choose-a-response.mp3',
    'mat-480b6e281380': 'practice-test-1-listening-module-2-conversation-1.mp3',
    'mat-ae5c697b096e': 'practice-test-1-listening-module-2-announcement.mp3',
    'mat-89a0d7636674': 'practice-test-1-listening-module-2-academic-talk.mp3',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def export(root=ROOT, official_pdf=None, overview_pdf=None):
    catalog = Catalog(root)
    exam = deepcopy(catalog.exams[EXAM_ID])
    result = SourceIntegrity(root, catalog).check_exam(exam)
    if result['status'] != 'passed':
        raise ValueError(f'Practice Test 1 must pass source verification before export: {result}')
    if exam.get('bundledExample'):
        raise ValueError('Export requires the original curated collection, not an installed example')
    official_pdf = Path(official_pdf) if official_pdf else root / f'tmp/qa/{BUNDLE_ID}/official-source.pdf'
    original_pdf = next(m for m in catalog.data['materials'] if m['id'] == SOURCE_MATERIAL_ID)
    if not official_pdf.is_file() or sha(official_pdf) != original_pdf['sha256']:
        raise ValueError('Download the linked ETS PDF and supply --official-pdf; it must match the local question PDF exactly')
    bundle = root / 'examples' / BUNDLE_ID
    original_exam_sha = sha(root / f'generated/exams/{EXAM_ID}.json')
    original_curations = deepcopy(exam['verificationInputs']['curationSha256ByPath'])
    edition = prepare_audio_edition(exam, root, overview_pdf or root / 'tmp/qa/example1-timing/ets-overview.pdf')
    original_curations['scripts/example_audio_edition.py'] = sha(root / 'scripts/example_audio_edition.py')
    questions = [q for s in exam['sections'] for m in s['modules'] for q in m['questions']]
    required_ids = set(exam['sourceMaterialIds'])
    urls = set()

    def collect(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {'materialId', 'sourceMaterialId', 'referenceMaterialId'} and isinstance(child, str):
                    required_ids.add(child)
                collect(key)
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
        elif isinstance(value, str) and value.startswith(('/assets/', '/materials/')):
            urls.add(urlsplit(value).path)

    errata = json.loads((root / 'scripts/verified_text_corrections.json').read_text())
    errata['questions'] = {k: v for k, v in errata['questions'].items() if k in {q['id'] for q in questions}}
    collect(exam)
    collect(errata)
    materials = [deepcopy(m) for m in catalog.data['materials'] if m['id'] in required_ids]
    if {m['id'] for m in materials} != required_ids:
        raise ValueError('Practice Test 1 has an unresolved material dependency')
    for material in materials:
        if material.get('examIds') != [EXAM_ID]:
            raise ValueError('A dependency belongs to another source set; review before bundling')
        if material['id'] not in MATERIAL_FILENAMES:
            raise ValueError(f"Assign an English bundle filename for material {material['id']}")
        material['name'] = MATERIAL_FILENAMES[material['id']]
        urls.add(urlsplit(material['url']).path)
    files = []

    def entry(path, install_path):
        files.append({'path': path.relative_to(bundle).as_posix(), 'installPath': install_path,
                      'sha256': sha(path), 'bytes': path.stat().st_size})

    by_url = {urlsplit(m['url']).path: m for m in materials}
    asset_hashes = {}
    original_sources = {}
    planned = []
    for url in sorted(urls):
        if url.startswith('/assets/'):
            relative = unquote(url[len('/assets/'):])
            source = root / 'generated/assets' / relative
            destination = bundle / 'assets' / relative
            install = 'generated/assets/' + relative
            asset_hashes[url] = sha(source)
        else:
            material = by_url[url]
            original_sources[material['id']] = {
                **{key: material[key] for key in ['name', 'kind', 'bytes', 'sha256', 'url']},
                'bundlePath': 'materials/' + MATERIAL_FILENAMES[material['id']],
                'installPath': 'data/' + material['path'],
            }
            continue
        planned.append((source, destination, install))
    planned_names = [destination.relative_to(bundle).as_posix() for _, destination, _ in planned]
    if len(planned_names) != len(set(planned_names)):
        raise ValueError('Source basenames collide; assign distinct bundled paths')
    allowed = set(planned_names) | {'manifest.json', 'exam.json', 'catalog.json', 'provenance.json',
        'text-corrections.json', 'README.md', 'NOTICE.md'}
    # Optional originals may stay in the maintainer's ignored local directory.
    allowed.update(record['bundlePath'] for record in original_sources.values())
    extras = {p.relative_to(bundle).as_posix() for p in bundle.rglob('*') if p.is_file()} - allowed
    if extras:
        raise ValueError(f'Unexpected/stale files in the example bundle; review before publishing: {sorted(extras)}')
    for source, destination, install in planned:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        entry(destination, install)

    provenance = {'schemaVersion': 1, 'examId': EXAM_ID, 'sourceExamSha256': original_exam_sha,
        'runtimeProfile': 'prepared-runtime-v1', 'originalSources': original_sources,
        'runtimeAssetSha256ByUrl': asset_hashes,
        'sourceCurationSha256ByPath': original_curations,
        'scope': 'Practice Test 1 with the explicitly disclosed original-audio version of Interview question 1. No synthetic speech or authored replacement prompt.',
        'audioEdition': edition,
        'officialPdf': {'title': 'TOEFL iBT® Practice Test 1', 'url': SOURCE_URL, 'materialId': SOURCE_MATERIAL_ID,
            'sha256': original_pdf['sha256'], 'bytes': original_pdf['bytes'], 'pages': original_pdf['pages'],
            'verifiedAt': datetime.now(timezone.utc).date().isoformat(), 'downloadMatchesLocalBytes': True},
        'supplementalSources': {'audio': 'Local user-supplied MP3 files; the linked PDF does not establish their publisher.',
            'explanations': 'Local user-supplied analysis PDF; not ETS official explanations.'},
        'questionIds': [q['id'] for q in questions],
        'contentSha256ByQuestionId': {q['id']: content_digest(q) for q in questions},
        'sourceSha256ById': {m['id']: m['sha256'] for m in materials},
        'textCorrectionScreens': len(errata['questions']),
        'textCorrectionFields': sum(len(r['patches']) for r in errata['questions'].values())}
    for name, data in [('provenance', provenance), ('text-corrections', errata)]:
        path = bundle / f'{name}.json'
        write_json(path, data)
        entry(path, PROVENANCE if name == 'provenance' else f'generated/assets/{BUNDLE_ID}/{name}-v3.json')
    inputs = exam['verificationInputs']
    inputs['curationSha256ByPath'] = {f['installPath']: f['sha256'] for f in files if f['path'] in
        {'provenance.json', 'text-corrections.json'}}
    inputs.update(assetSha256ByUrl=asset_hashes, textCorrectionsPath=f'generated/assets/{BUNDLE_ID}/text-corrections-v3.json')
    exam['bundledExample'] = deepcopy(PROFILE)
    exam['warnings'].append('Lightweight example: prepared questions and assets are verified; original PDFs and full audio tracks are optional and not included.')
    exam['title'] = 'TOEFL iBT® Practice Test 1 · Audio edition'
    write_json(bundle / 'exam.json', exam)
    entry(bundle / 'exam.json', f'generated/exams/{EXAM_ID}.json')
    stats = {'fileCount': len(materials), 'materialFileCount': len(materials), 'excludedSystemFileCount': 0,
        'pdfCount': sum(m['kind'] == 'pdf' for m in materials), 'pdfPageCount': sum(m.get('pages', 0) for m in materials),
        'audioCount': sum(m['kind'] == 'audio' for m in materials), 'videoCount': 0,
        'totalBytes': sum(m['bytes'] for m in materials), 'ibtExamCount': 1, 'supplementalExamCount': 0,
        'interactiveExamCount': 1, 'strictExamCount': int(exam['strictEligible']), 'questionCount': exam['questionCount'],
        'ibtQuestionCount': exam['questionCount'], 'supplementalQuestionCount': 0, 'uniqueQuestionCount': exam['questionCount']}
    data = {'schemaVersion': 2, 'generatedAt': datetime.now(timezone.utc).isoformat(),
        'sourceRoot': 'data', 'bundledExample': exam['bundledExample'], 'stats': stats,
        'materials': materials, 'excludedSystemFiles': [], 'exams': [{k: v for k, v in exam.items() if k != 'sections'}],
        'supplementalExams': []}
    write_json(bundle / 'catalog.json', data)
    entry(bundle / 'catalog.json', None)
    manifest = {'schemaVersion': 1, 'examId': EXAM_ID, 'title': exam['title'],
        'profile': 'runtime-only', 'optionalOriginals': original_sources,
        'questionCount': exam['questionCount'], 'screenCount': exam['screenCount'],
        'sourceUrl': SOURCE_URL, 'files': sorted(files, key=lambda f: f['path'])}
    write_json(bundle / 'manifest.json', manifest)
    print(json.dumps({'files': len(files), 'bytes': sum(f['bytes'] for f in files),
        'items': exam['questionCount'], 'screens': exam['screenCount']}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--official-pdf', type=Path, help='Unmodified PDF downloaded from the documented ETS URL')
    parser.add_argument('--overview-pdf', type=Path, help='Reviewed ETS Test Overview PDF for the Interview audio edition')
    args = parser.parse_args()
    export(official_pdf=args.official_pdf, overview_pdf=args.overview_pdf)
