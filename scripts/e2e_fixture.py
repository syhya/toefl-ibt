#!/usr/bin/env python3
"""Isolated browser-E2E fixture with a file-controlled clock, never a production HTTP clock API."""
from copy import deepcopy
from pathlib import Path
from urllib.parse import unquote, urlsplit
import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'tmp/qa'
SANDBOX = QA / 'e2e-sandbox'
CLOCK = QA / 'e2e-clock.json'
MANIFEST = QA / 'e2e-fixture-manifest.json'
MODE = SANDBOX / 'e2e-mode.json'

FIXTURE_SCRIPT = r'''
(() => {
  window.__TOEFL_E2E_FIXTURE__ = true;
  const mark = () => {
    const banner = document.createElement('aside');
    banner.id = 'e2e-fixture-banner';
    banner.textContent = 'E2E TEST FIXTURE — PARTIAL SOURCE QUESTIONS / TEST CLOCK — NOT AN OFFICIAL EXAM';
    banner.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:2147483647;padding:7px 12px;background:#6d28d9;color:white;font:700 12px/18px system-ui;text-align:center;pointer-events:none';
    document.body.prepend(banner);
    document.body.style.paddingTop = '32px';
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mark, {once:true});
  else mark();
})();
'''

SYNTHETIC_SCRIPT = r'''
(() => {
  window.__TOEFL_E2E_FIXTURE__ = true;
  window.__TOEFL_E2E_SYNTHETIC_MICROPHONE__ = true;
  const mark = () => {
    const banner = document.createElement('aside');
    banner.id = 'e2e-synthetic-microphone-banner';
    banner.textContent = 'E2E / SYNTHETIC MICROPHONE — PARTIAL TEST FIXTURE · NO REAL MICROPHONE ACCESS';
    banner.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:2147483647;padding:7px 12px;background:#6d28d9;color:white;font:700 12px/18px system-ui;text-align:center;pointer-events:none';
    document.body.prepend(banner);
    document.body.style.paddingTop = '32px';
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mark, {once:true});
  else mark();
  const syntheticGetUserMedia = async constraints => {
    if (!constraints?.audio || constraints.video === true) throw new DOMException('This E2E fixture provides synthetic audio only.', 'NotSupportedError');
    const Context = window.AudioContext || window.webkitAudioContext;
    const context = new Context({sampleRate:48000});
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    const destination = context.createMediaStreamDestination();
    oscillator.type = 'sine';
    oscillator.frequency.value = 523.25;
    gain.gain.value = 0.15;
    oscillator.connect(gain);
    gain.connect(destination);
    oscillator.start();
    let closed = false;
    const cleanup = () => {
      if (closed) return;
      closed = true;
      try { oscillator.stop(); } catch {}
      oscillator.disconnect();
      gain.disconnect();
      void context.close();
    };
    const stream = destination.stream;
    for (const track of stream.getTracks()) {
      const stop = track.stop.bind(track);
      track.stop = () => {
        stop();
        if (stream.getTracks().every(item => item.readyState === 'ended')) cleanup();
      };
      track.addEventListener('ended', () => {
        if (stream.getTracks().every(item => item.readyState === 'ended')) cleanup();
      }, {once:true});
    }
    try { await context.resume(); }
    catch (error) { stream.getTracks().forEach(track => track.stop()); cleanup(); throw error; }
    Object.defineProperty(stream, 'toeflSyntheticFixture', {value:true});
    return stream;
  };
  const mediaDevices = navigator.mediaDevices || {};
  Object.defineProperty(mediaDevices, 'getUserMedia', {configurable:true, writable:true, value:syntheticGetUserMedia});
  if (!navigator.mediaDevices) Object.defineProperty(navigator, 'mediaDevices', {configurable:true, value:mediaDevices});
})();
'''


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    os.replace(temporary, path)


def now_ms():
    value = json.loads(CLOCK.read_text())
    return int(value['baseServerMs'] + (time.monotonic() * 1000 - value['anchorMonotonicMs']) + value['offsetMs'])


def all_urls(value):
    if isinstance(value, dict):
        for key in ['url', 'sourceUrl']:
            if isinstance(value.get(key), str):
                yield value[key]
        for child in value.values():
            yield from all_urls(child)
    elif isinstance(value, list):
        for child in value:
            yield from all_urls(child)


def sync_ui():
    if not (ROOT / 'dist/index.html').is_file():
        raise RuntimeError('Build the frontend with npm run build before preparing the fixture.')
    shutil.copytree(ROOT / 'dist', SANDBOX / 'dist', dirs_exist_ok=True)
    mode = json.loads(MODE.read_text()) if MODE.is_file() else {}
    index = SANDBOX / 'dist/index.html'
    html = index.read_text()
    kind = 'synthetic-mic' if mode.get('syntheticMicrophone') else 'fixture'
    script = SYNTHETIC_SCRIPT if mode.get('syntheticMicrophone') else FIXTURE_SCRIPT
    injection = f'<script data-toefl-e2e="{kind}">' + script + '</script>'
    index.write_text(html.replace('<head>', '<head>' + injection, 1))


def snapshot_backend():
    shutil.copytree(ROOT / 'backend', SANDBOX / 'backend', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('tests', '__pycache__'))
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (SANDBOX / 'backend').glob('*.py')}


def verification_inputs(source, fixture):
    """Copy verification evidence and original inputs, never rewrite old answers."""
    inputs = deepcopy(source.get('verificationInputs') or {})
    # This is a source-preserving subset; retain the original verification
    # digests only for questions actually included in this fixture.
    manifest = inputs.get('structuredContentSha256ByQuestionId')
    if isinstance(manifest, dict):
        selected_ids = {question['id'] for section in fixture['sections']
                        for module in section['modules'] for question in module['questions']}
        inputs['structuredContentSha256ByQuestionId'] = {
            question_id: digest for question_id, digest in manifest.items() if question_id in selected_ids
        }
    fixture['verificationInputs'] = inputs
    catalog = json.loads((ROOT / 'generated/catalog.json').read_text())
    source_ids = set(fixture.get('sourceMaterialIds', []))
    referenced = {urlsplit(url).path for url in all_urls(fixture) if url.startswith('/materials/')}
    materials = [m for m in catalog['materials'] if m['id'] in source_ids or urlsplit(m.get('url', '')).path in referenced]
    for material in materials:
        url = urlsplit(material['url']).path
        relative = unquote(url[len('/materials/'):])
        original = ROOT / 'data' / relative
        destination = SANDBOX / 'data' / relative
        if not original.resolve().is_relative_to((ROOT / 'data').resolve()) or not original.is_file():
            raise RuntimeError('A required original fixture source is missing.')
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            try:
                os.link(original, destination)
            except OSError:
                shutil.copy2(original, destination)
    for relative, expected in inputs.get('curationSha256ByPath', {}).items():
        original = ROOT / relative
        if not original.resolve().is_relative_to(ROOT) or not original.is_file() or hashlib.sha256(original.read_bytes()).hexdigest() != expected:
            raise RuntimeError('A required private verification input is missing or changed. Reimport before preparing the fixture.')
        destination = SANDBOX / relative; destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, destination)
    return materials


def prepare(reset=False, synthetic_mic=False):
    if SANDBOX.exists() and not (SANDBOX / '.e2e-owned').is_file():
        raise RuntimeError('Refusing to replace a directory without this fixture’s ownership marker.')
    if reset and SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    if SANDBOX.exists() and MANIFEST.exists():
        atomic_json(MODE, {'syntheticMicrophone': synthetic_mic})
        sync_ui()
        if (ROOT / 'shared').is_dir():
            shutil.copytree(ROOT / 'shared', SANDBOX / 'shared', dirs_exist_ok=True)
        manifest = json.loads(MANIFEST.read_text())
        source_path = ROOT / 'generated/exams/experience-1.json'
        source = json.loads(source_path.read_text())
        fixture_path = SANDBOX / 'generated/exams/e2e-fixture.json'
        fixture = json.loads(fixture_path.read_text())
        materials = verification_inputs(source, fixture)
        atomic_json(fixture_path, fixture)
        fixture_catalog = json.loads((SANDBOX / 'generated/catalog.json').read_text())
        fixture_catalog['materials'] = materials
        atomic_json(SANDBOX / 'generated/catalog.json', fixture_catalog)
        manifest['syntheticMicrophone'] = synthetic_mic
        manifest['codeHashes'] = snapshot_backend()
        manifest['backendSnapshotPath'] = str(SANDBOX / 'backend')
        manifest['verificationMetadataSourceSha256'] = hashlib.sha256(source_path.read_bytes()).hexdigest()
        atomic_json(MANIFEST, manifest)
        return manifest
    SANDBOX.mkdir(parents=True, exist_ok=True)
    (SANDBOX / '.e2e-owned').write_text('Temporary local browser test fixture; not user practice data.\n')
    atomic_json(MODE, {'syntheticMicrophone': synthetic_mic})
    source_path = ROOT / 'generated/exams/experience-1.json'
    source = json.loads(source_path.read_text())
    sections = {s['id']: s for s in source['sections']}
    reading = [q for m in sections['reading']['modules'] for q in m['questions']]
    cloze = next(q for q in reading if q['type'] == 'cloze')
    choices = [q for q in reading if q['type'] == 'choice']
    daily = next((q for q in choices if q.get('taskType') == 'daily_life'), choices[0])
    academic = next((q for q in reversed(choices) if q.get('taskType') == 'academic_passage' and q['id'] != daily['id']), choices[-1])
    listening = [q for m in sections['listening']['modules'] for q in m['questions']]
    by_type = {kind: [q for q in listening if q.get('taskType') == kind] for kind in ['listen_response', 'conversation', 'announcement', 'academic_talk']}
    if any(not values for values in by_type.values()):
        raise RuntimeError('The source exam must contain all four verified listening task types.')
    writing = [q for m in sections['writing']['modules'] for q in m['questions']]
    fixture_sections = [
        {'id': 'reading', 'title': 'Reading fixture', 'modules': [
            {'id': 'fixture-reading-router', 'title': 'Fixture router · one real screen', 'route': 'common', 'durationSeconds': 690, 'questions': [deepcopy(cloze)]},
            {'id': 'fixture-reading-upper', 'title': 'Fixture upper · one real screen', 'route': 'upper', 'durationSeconds': 540, 'questions': [deepcopy(daily)]},
            {'id': 'fixture-reading-lower', 'title': 'Fixture lower · one real screen', 'route': 'lower', 'durationSeconds': 540, 'questions': [deepcopy(academic)]},
        ]},
        {'id': 'listening', 'title': 'Listening fixture', 'modules': [
            {'id': 'fixture-listening-router', 'title': 'Fixture listening router', 'route': 'common', 'questions': deepcopy([by_type['listen_response'][0], by_type['conversation'][0]])},
            {'id': 'fixture-listening-upper', 'title': 'Fixture listening upper', 'route': 'upper', 'questions': deepcopy([by_type['announcement'][-1], by_type['academic_talk'][-1]])},
            {'id': 'fixture-listening-lower', 'title': 'Fixture listening lower', 'route': 'lower', 'questions': deepcopy([by_type['announcement'][0], by_type['academic_talk'][0]])},
        ]},
        {'id': 'writing', 'title': 'Writing fixture', 'modules': [
            {'id': f'fixture-{kind}', 'title': f'Fixture {kind}', 'questions': [deepcopy(next(q for q in writing if q['type'] == kind))]}
            for kind in ['build_sentence', 'email', 'academic_discussion']
        ]},
        deepcopy(sections['speaking']),
    ]
    for mod in fixture_sections[-1]['modules']:
        mod['id'] = 'fixture-' + mod['id']
        mod['title'] = 'Fixture ' + mod.get('title', mod['id'])
    first_listen_source = sections['listening']['modules'][0]
    for key in ['instructions', 'directionsAudio']:
        if key in first_listen_source:
            fixture_sections[1]['modules'][0][key] = deepcopy(first_listen_source[key])
    fixture = {'id': 'e2e-fixture', 'title': 'E2E verification fixture · NOT a complete official exam', 'family': 'experience',
               'strictEligible': True, 'adaptiveEligible': True, 'sourceMaterialIds': source.get('sourceMaterialIds', []),
               'warnings': ['仅用于自动化验收：每条阅读路径只有两屏真实来源题，不是完整 TOEFL 试卷。',
                            '该隔离测试服务器使用文件可推进时钟，不代表真实时长或真实麦克风验收。'],
               'validation': {'status': 'test-fixture', 'sourceExamId': source['id'], 'partialFixture': True},
               'sections': fixture_sections}
    all_questions = [q for s in fixture_sections for m in s['modules'] for q in m['questions']]
    fixture['screenCount'] = len(all_questions)
    fixture['questionCount'] = sum(len(q.get('blanks', [])) if q['type'] == 'cloze' else 1 for q in all_questions)
    (SANDBOX / 'generated/exams').mkdir(parents=True)
    materials = verification_inputs(source, fixture)
    atomic_json(SANDBOX / 'generated/exams/e2e-fixture.json', fixture)
    catalog = json.loads((ROOT / 'generated/catalog.json').read_text())
    urls = set(all_urls(fixture))
    original_paths = {urlsplit(url).path for url in urls if url.startswith('/materials/')}
    atomic_json(SANDBOX / 'generated/catalog.json', {'schemaVersion': 2, 'exams': [{'id': 'e2e-fixture'}], 'materials': materials,
        'stats': {'fileCount': len(materials), 'ibtExamCount': 0, 'testFixtureCount': 1}, 'supplementalExams': []})
    for url in urls:
        path = urlsplit(url).path
        if path.startswith('/materials/'):
            directory, relative = 'data', unquote(path[len('/materials/'):])
        elif path.startswith('/assets/'):
            directory, relative = 'generated/assets', unquote(path[len('/assets/'):])
        else:
            continue
        original = ROOT / directory / relative
        if not original.resolve().is_relative_to((ROOT / directory).resolve()) or not original.is_file():
            raise RuntimeError('A referenced source asset is missing or outside the allowed input directory.')
        destination = SANDBOX / directory / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            continue
        # Immutable data inputs may be hard-linked. Generated assets are copied
        # so subsequent OCR/media processing cannot change the fixture in place.
        if directory == 'data':
            try:
                os.link(original, destination)
            except OSError:
                shutil.copy2(original, destination)
        else:
            shutil.copy2(original, destination)
    if (ROOT / 'shared').is_dir():
        shutil.copytree(ROOT / 'shared', SANDBOX / 'shared', dirs_exist_ok=True)
    sync_ui()
    clock = {'baseServerMs': int(time.time() * 1000), 'anchorMonotonicMs': int(time.monotonic() * 1000), 'offsetMs': 0}
    atomic_json(CLOCK, clock)
    manifest = {'id': 'e2e-fixture', 'sandbox': str(SANDBOX), 'clockFile': str(CLOCK), 'productionDataModified': False,
                'sourceExamId': source['id'], 'sourceSha256': hashlib.sha256(source_path.read_bytes()).hexdigest(),
                'partialFixture': True, 'realDurationVerified': False, 'realMicrophoneVerified': False,
                'syntheticMicrophone': synthetic_mic,
                'codeHashes': snapshot_backend(), 'backendSnapshotPath': str(SANDBOX / 'backend'),
                'modules': [{'section': s['id'], 'id': m['id'], 'route': m.get('route', 'common'), 'questionIds': [q['id'] for q in m['questions']]} for s in fixture_sections for m in s['modules']],
                'readingRouterAnswer': {b['id']: b.get('missingLetters') or b.get('answer') for b in cloze.get('blanks', [])},
                'listeningRouterAnswers': {q['id']: q.get('answer') for q in fixture_sections[1]['modules'][0]['questions']},
                'notice': 'Test-only local manifest. Answer fixtures are never served by the production API. Not a complete official exam.'}
    atomic_json(MANIFEST, manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    serve = sub.add_parser('serve')
    serve.add_argument('--port', type=int, default=4176)
    serve.add_argument('--reset', action='store_true')
    serve.add_argument('--synthetic-mic', action='store_true', help='TEST ONLY: inject an explicitly labeled oscillator stream instead of any real microphone request')
    setup = sub.add_parser('prepare')
    setup.add_argument('--reset', action='store_true')
    setup.add_argument('--synthetic-mic', action='store_true')
    advance = sub.add_parser('advance')
    advance.add_argument('seconds', type=float)
    sub.add_parser('status')
    sub.add_parser('sync-ui')
    args = parser.parse_args()
    if args.command in ['serve', 'prepare']:
        manifest = prepare(args.reset, args.synthetic_mic)
        print(json.dumps({'fixture': manifest['id'], 'clockFile': str(CLOCK), 'manifest': str(MANIFEST)}, ensure_ascii=False), flush=True)
        if args.command == 'serve':
            if not 1 <= args.port <= 65535:
                parser.error('Choose a local port from 1 to 65535.')
            sys.path.insert(0, str(SANDBOX))
            import uvicorn
            from backend.app import create_app
            print(f'Isolated E2E fixture: http://127.0.0.1:{args.port}', flush=True)
            uvicorn.run(create_app(SANDBOX, clock=now_ms), host='127.0.0.1', port=args.port, log_level='warning')
    elif args.command == 'advance':
        if not math.isfinite(args.seconds) or not 0 <= args.seconds <= 86400:
            parser.error('Advance must be between 0 and 86400 seconds.')
        clock = json.loads(CLOCK.read_text())
        clock['offsetMs'] += int(args.seconds * 1000)
        atomic_json(CLOCK, clock)
        print(json.dumps({'advancedSeconds': args.seconds, 'offsetSeconds': clock['offsetMs'] / 1000, 'serverNow': now_ms()}))
    elif args.command == 'sync-ui':
        sync_ui()
        print('The latest built frontend was copied into the isolated fixture.')
    else:
        print(json.dumps({'clock': json.loads(CLOCK.read_text()), 'serverNow': now_ms(), 'manifest': str(MANIFEST)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
