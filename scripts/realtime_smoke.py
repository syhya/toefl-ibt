#!/usr/bin/env python3
"""Real-wall-clock HTTP flow verification. No browser or microphone is tested.

Uses an isolated SQLite database and a frozen source/backend snapshot. Original
materials are hard-linked read-only inputs, never edited. The report contains
only timings, opaque IDs and hashes, not question text or user responses.
"""
from pathlib import Path
from urllib.parse import unquote, urlsplit
import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid

import httpx

ROOT = Path(__file__).resolve().parents[1]


def iso():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exam', default='experience-1')
    parser.add_argument('--port', type=int, default=4175)
    parser.add_argument('--max-seconds', type=int, default=10800)
    parser.add_argument('--report', type=Path, default=ROOT / 'tmp/qa/realtime-report.json')
    args = parser.parse_args()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    report = {'schemaVersion': 1, 'status': 'preparing', 'examId': args.exam, 'startedAt': iso(),
              'verification': 'real-wall-clock-server-http-flow', 'clockAccelerated': False,
              'browserTested': False, 'microphoneTested': False,
              'limitations': ['No browser rendering, audio listening, or real microphone recording is verified by this run.',
                             'Answers remain empty to verify automatic timeout progression.'],
              'codeHashes': {}, 'stageTransitions': [], 'mediaReads': [], 'assetReads': [], 'errors': []}
    report['snapshotMode'] = {'backend': 'copied files', 'exam': 'copied JSON',
                              'originalData': 'hard links; never modified by this tool', 'generatedAssets': 'copied files'}
    process = None
    started = time.monotonic()
    temporary = Path(tempfile.mkdtemp(prefix='realtime-', dir=args.report.parent))

    def checkpoint():
        report['updatedAt'] = iso()
        report['elapsedWallSeconds'] = round(time.monotonic() - started, 3)
        temp_report = args.report.with_suffix('.tmp')
        temp_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        os.replace(temp_report, args.report)

    def remaining_budget():
        if time.monotonic() - started > args.max_seconds:
            raise TimeoutError('Finite verification time budget exceeded.')

    def interrupt(signum, frame):
        raise KeyboardInterrupt(f'Interrupted by signal {signum}')

    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    try:
        exam_path = ROOT / 'generated/exams' / f'{args.exam}.json'
        if not exam_path.resolve().is_relative_to((ROOT / 'generated/exams').resolve()):
            raise ValueError('Invalid exam identifier.')
        exam = json.loads(exam_path.read_text())
        report['examSha256'] = sha(exam_path)
        for source in (ROOT / 'backend').glob('*.py'):
            report['codeHashes'][source.name] = sha(source)
        shutil.copytree(ROOT / 'backend', temporary / 'backend', ignore=shutil.ignore_patterns('__pycache__', 'tests'))
        (temporary / 'generated/exams').mkdir(parents=True)
        shutil.copy2(exam_path, temporary / 'generated/exams' / exam_path.name)
        original_catalog = json.loads((ROOT / 'generated/catalog.json').read_text())
        required_urls = set(all_urls(exam))
        source_ids = set(exam.get('sourceMaterialIds', []))
        required_urls.update(m['url'] for m in original_catalog.get('materials', []) if m['id'] in source_ids)
        material_paths = {urlsplit(url).path for url in required_urls if url.startswith('/materials/')}
        materials = [m for m in original_catalog.get('materials', []) if urlsplit(m.get('url', '')).path in material_paths]
        (temporary / 'generated/catalog.json').write_text(json.dumps({'exams': [{'id': args.exam}], 'materials': materials, 'stats': {'fileCount': len(materials)}}))
        for url in required_urls:
            uri = urlsplit(url).path
            if uri.startswith('/materials/'):
                directory, relative = 'data', unquote(uri[len('/materials/'):])
            elif uri.startswith('/assets/'):
                directory, relative = 'generated/assets', unquote(uri[len('/assets/'):])
            else:
                continue
            source = ROOT / directory / relative
            if not source.resolve().is_relative_to((ROOT / directory).resolve()) or not source.is_file():
                raise FileNotFoundError('An explicitly referenced exam asset is missing or outside the allowed input tree.')
            target = temporary / directory / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                if directory != 'data':
                    shutil.copy2(source, target)
                else:
                    try:
                        os.link(source, target)
                    except OSError:
                        shutil.copy2(source, target)
        for relative, expected in (exam.get('verificationInputs') or {}).get('curationSha256ByPath', {}).items():
            source = ROOT / relative
            if not source.resolve().is_relative_to(ROOT) or not source.is_file() or sha(source) != expected:
                raise RuntimeError('Verification inputs changed; reimport before the real-time validation run.')
            destination = temporary / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        report['status'] = 'starting'
        checkpoint()
        log_path = args.report.parent / 'realtime-server.log'
        with log_path.open('w') as log:
            process = subprocess.Popen([sys.executable, '-m', 'backend', '--port', str(args.port)], cwd=temporary,
                                       stdout=log, stderr=log, env={**os.environ, 'PYTHONUNBUFFERED': '1'})
        base = f'http://127.0.0.1:{args.port}'
        with httpx.Client(base_url=base, timeout=25) as client:
            for _ in range(100):
                remaining_budget()
                if process.poll() is not None:
                    raise RuntimeError('The isolated backend could not start; check realtime-server.log.')
                try:
                    if client.get('/api/health').status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(.1)
            else:
                raise RuntimeError('The isolated backend did not become ready.')

            def request(method, path, body=None):
                response = client.request(method, path, json=body) if body is not None else client.request(method, path)
                if response.status_code >= 400:
                    data = response.json()
                    raise RuntimeError(f"HTTP {response.status_code}: {data.get('error', 'request failed')}")
                return response.json()

            state = request('POST', '/api/sessions', {'examId': args.exam, 'mode': 'strict', 'scope': 'all', 'routeMode': 'fixed', 'route': 'upper'})
            report['sessionId'] = state['id']
            report['port'] = args.port
            report['timing'] = state['timing']
            report['rulesVersion'] = state['rulesVersion']
            report['status'] = 'running'
            print(f"Real-time backend verification started: {state['id']} at {base}", flush=True)

            def event(action, **extra):
                return request('POST', f"/api/sessions/{state['id']}/events", {'action': action, 'requestId': str(uuid.uuid4()), **extra})

            state = event('interrupt', reason='backend-only-verification-no-browser-or-microphone')
            previous_stage = None
            checked_assets = set()
            while state['status'] == 'active':
                remaining_budget()
                st = state['stage']
                if st['id'] != previous_stage:
                    report['stageTransitions'].append({'stageId': st['id'], 'section': st['section'], 'at': iso(),
                        'serverNow': state['serverNow'], 'timer': st['timer'], 'seconds': st['seconds'], 'questionCount': st['questionCount']})
                    previous_stage = st['id']
                    print(f"{iso()} {st['section']} / {st['id']}", flush=True)
                    checkpoint()
                if state['phase'] == 'directions':
                    state = event('begin')
                    continue
                question = state.get('question') or {}
                for asset in question.get('assets', []):
                    if asset['assetId'] in checked_assets:
                        continue
                    response = client.get(asset['url'])
                    response.raise_for_status()
                    report['assetReads'].append({'assetId': asset['assetId'], 'bytes': len(response.content),
                                                'sha256': hashlib.sha256(response.content).hexdigest()})
                    checked_assets.add(asset['assetId'])
                if state['phase'] == 'audio':
                    media = question.get('audio')
                    if not media:
                        raise RuntimeError('The current audio phase has no authorized media.')
                    read_started = time.monotonic()
                    digest, count = hashlib.sha256(), 0
                    with client.stream('GET', media['url']) as response:
                        response.raise_for_status()
                        for chunk in response.iter_bytes():
                            count += len(chunk)
                            digest.update(chunk)
                    state = event('audio-started', questionId=question['id'], mediaIndex=state.get('mediaIndex', 0))
                    floor = state['audioEarliestEnd']
                    entry = {'questionId': question['id'], 'mediaIndex': state.get('mediaIndex', 0), 'assetId': media['assetId'],
                             'durationSeconds': media.get('durationSeconds'), 'bytes': count, 'sha256': digest.hexdigest(),
                             'readSeconds': round(time.monotonic() - read_started, 3), 'startedAt': iso()}
                    report['mediaReads'].append(entry)
                    checkpoint()
                    while int(time.time() * 1000) < floor + 75:
                        remaining_budget()
                        time.sleep(min(1, max(.01, (floor + 75 - time.time() * 1000) / 1000)))
                    state = event('audio-ended', questionId=question['id'], mediaIndex=state.get('mediaIndex', 0))
                    entry['endedAt'] = iso()
                    checkpoint()
                    continue
                if state['phase'] != 'response' or state['deadline'] is None:
                    raise RuntimeError('Unexpected non-timed state in strict flow.')
                report['current'] = {'stageId': st['id'], 'section': st['section'], 'phase': state['phase'],
                                     'questionId': question.get('id'), 'deadline': state['deadline'], 'remainingSeconds': state['remainingSeconds']}
                checkpoint()
                time.sleep(min(5, max(.05, (state['deadline'] - state['serverNow']) / 1000 + .075)))
                state = request('GET', f"/api/sessions/{state['id']}")

            review = request('GET', f"/api/sessions/{state['id']}/review")
            report['status'] = 'passed'
            report['completedAt'] = iso()
            report['serverCompletedAt'] = state['completedAt']
            report['finalRevision'] = state['revision']
            report['timeoutCount'] = sum(event['type'] == 'timeout' for event in review['events'])
            report['stageEndCount'] = sum(event['type'] == 'stage-end' for event in review['events'])
            report['scoreMetadata'] = {key: review['score'].get(key) for key in ['total', 'attemptedCount', 'durationSeconds', 'wallSeconds']}
            report.pop('current', None)
            print(f"Real-time backend verification passed. Report: {args.report}", flush=True)
    except BaseException as error:
        report['status'] = 'interrupted' if isinstance(error, KeyboardInterrupt) else 'failed'
        report['errors'].append({'type': type(error).__name__, 'message': str(error), 'at': iso()})
        print(f"Real-time verification {report['status']}: {error}", file=sys.stderr, flush=True)
    finally:
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=5)
        checkpoint()
        shutil.rmtree(temporary, ignore_errors=True)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
