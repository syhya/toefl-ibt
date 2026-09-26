"""Loopback HTTP boundary for the personal practice application.

Handlers validate input, transact state through Storage, delegate progression to
engine, and return an allowlisted view of the current question. Original sources
and answer keys are exposed only through the appropriate review/library routes.
Changing the UI language never changes the underlying exam or scoring payload.
"""
from pathlib import Path
from collections import Counter
from urllib.parse import urlsplit
import hashlib
import json
import math
import mimetypes
import os
import re
import time
import uuid
from copy import deepcopy

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from .catalog import Catalog
from .storage import Storage
from . import engine
from . import mistakes
from .vocabulary import install_vocabulary_routes
from .explanations import explain
from .media import indexed_take
from .integrity import SourceIntegrity
from .legacy_audio import recovery_flags, recover_audio
from .practice_groups import build_practice_groups, public_group, group_session_options, group_revision, SESSION_FIELDS as GROUP_SESSION_FIELDS
from .presentation import asset_is_active, is_structured, manifest_issues, safe_stem_blocks
from .text_corrections import TextCorrections

ROOT = Path(__file__).resolve().parents[1]
ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$')
AUDIO = {'audio/webm', 'audio/ogg', 'audio/mp4', 'audio/wav', 'audio/x-wav', 'audio/mpeg', 'audio/aac'}
LOOPBACK = {'127.0.0.1', 'localhost', '::1'}


def valid_id(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise engine.ExamError('Invalid identifier.', 422)
    return value


async def read_body(request, limit=2 * 1024 * 1024):
    length = request.headers.get('content-length')
    if length and int(length) > limit:
        raise engine.ExamError('The upload is too large.', 413)
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise engine.ExamError('The upload is too large.', 413)
        chunks.append(chunk)
    return b''.join(chunks)


async def read_json(request):
    if request.headers.get('content-type', '').split(';')[0].strip() != 'application/json':
        raise engine.ExamError('Use application/json.', 415)
    try:
        # Python's decoder otherwise accepts NaN and Infinity, which JSON does
        # not support and which would make a persisted session unrenderable.
        def reject_constant(value):
            raise ValueError('Non-finite JSON number: ' + value)
        body = json.loads(await read_body(request), parse_constant=reject_constant)
    except (ValueError, UnicodeError):
        raise engine.ExamError('Invalid JSON.', 422)
    if not isinstance(body, dict):
        raise engine.ExamError('A JSON object is required.', 422)
    return body


def create_app(root_dir=ROOT, clock=None, testing=False):
    root = Path(root_dir).resolve()
    clock = clock or (lambda: int(time.time() * 1000))
    catalog, store = Catalog(root), Storage(root)
    source_integrity = SourceIntegrity(root, catalog)
    text_corrections = TextCorrections(root, catalog, source_integrity)
    app = FastAPI(title='TOEFL Local Lab', docs_url='/api/docs' if testing else None, redoc_url=None,
                  openapi_url='/api/openapi.json' if testing else None)
    app.state.store, app.state.catalog, app.state.clock = store, catalog, clock
    app.state.source_integrity = source_integrity
    directions_cache = {}

    def verified_direction_text(a, media):
        """Only expose the original PDF instruction paired with this signed clip."""
        if media.get('kind') != 'directions' or not media.get('segmentId'):
            return None
        snapshot = a.get('verificationSnapshot') or {}
        relative = snapshot.get('packDirectionsPath', 'scripts/verified_pack_directions.json')
        if not isinstance(relative, str):
            return None
        expected = snapshot.get('curationSha256ByPath', {}).get(relative)
        if not expected:
            return None
        path = (root / relative).resolve()
        if source_integrity.digest(path) != expected:
            return None
        if expected not in directions_cache:
            content = path.read_bytes()
            if hashlib.sha256(content).hexdigest() != expected:
                return None
            directions_cache[expected] = json.loads(content).get('clips', {})
        clip = directions_cache[expected].get(media['segmentId'], {})
        if clip.get('verified') is not True or clip.get('url') != media.get('url'):
            return None
        text = clip.get('sourceText')
        return text if isinstance(text, str) else None

    @app.middleware('http')
    async def local_guard(request, call_next):
        try:
            host = urlsplit('http://' + request.headers.get('host', '')).hostname
            if host not in LOOPBACK and not (testing and host == 'testserver'):
                return JSONResponse({'error': 'Local access only.'}, status_code=403)
            origin = request.headers.get('origin')
            if request.method not in ['GET', 'HEAD']:
                parsed = urlsplit(origin) if origin else None
                if request.headers.get('sec-fetch-site') == 'cross-site' or (parsed and (parsed.hostname not in LOOPBACK or parsed.scheme != 'http')):
                    return JSONResponse({'error': 'Cross-origin writes are not allowed.'}, status_code=403)
            response = await call_next(request)
        except engine.ExamError as error:
            response = JSONResponse({'error': error.message}, status_code=error.status)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Cache-Control'] = 'no-store' if request.url.path.startswith('/api/') else 'no-cache'
        return response

    @app.exception_handler(engine.ExamError)
    async def exam_error(request, error):
        return JSONResponse({'error': error.message}, status_code=error.status)

    @app.exception_handler(Exception)
    async def internal_error(request, error):
        return JSONResponse({'error': 'The local server could not complete this request. Existing saved data was not discarded.'}, status_code=500)

    def get_session(db, session_id):
        a = store.get(db, valid_id(session_id))
        if a is None:
            raise engine.ExamError('Session not found.', 404)
        return a

    def reject_during_strict(db):
        if any(a['status'] == 'active' and a['mode'] == 'strict' for a in store.all(db)):
            raise engine.ExamError('Review, feedback and reference resources are locked while strict practice is active.', 403)

    install_vocabulary_routes(app, store, clock, read_json, reject_during_strict)

    def exclusive_session_guard(db, a):
        if any(item['status'] == 'active' and item['mode'] == 'strict' and item['id'] != a['id'] for item in store.all(db)):
            raise engine.ExamError('Another strict session is active. Other sessions and their media are locked until it ends.', 403)

    def asset_url(a, url, review=False):
        asset_id = catalog.register(url)
        if not asset_id:
            return None
        if review and urlsplit(url).path.startswith('/materials/') and not catalog.path_for(asset_id):
            return None
        route = 'review-assets' if review else 'assets'
        fragment = urlsplit(url).fragment if isinstance(url, str) else ''
        suffix = '#' + fragment if re.fullmatch(r'page=\d+', fragment) else ''
        return {'assetId': asset_id, 'url': f"/api/sessions/{a['id']}/{route}/{asset_id}{suffix}"}

    def safe_question(a, q, review=False):
        """Project only the material allowed in this phase and remap media URLs.

        Keep this explicit allowlist when adding fields: returning the importer
        dictionary wholesale would expose answers, transcripts and audit data.
        """
        if not q:
            return None
        # A source-backed transcription correction updates display only. The
        # stored plan still supplies grading, answer IDs, deadlines and media.
        q = text_corrections.project(a, q)
        keys = ['id', 'type', 'taskType', 'number', 'numberEnd', 'prompt', 'passage', 'passageTemplate', 'context', 'tokens',
                'fixedTokens', 'slots', 'wordLimit', 'recommendedWords', 'warnings', 'verificationStatus',
                'interaction', 'sourceImageContainsQuestionAndChoices', 'referenceOnly', 'sourcePromptAvailable', 'practiceMode', 'subjective',
                'presentationSchema', 'structuredContentStatus', 'textCorrection', 'sentencePrefix', 'terminalPunctuation']
        if review:
            keys += ['answer', 'transcript', 'explanation', 'explanations', 'answerStatus', 'rubric',
                     'sourceReferenceAnswer', 'answerConflict', 'resolutionEvidence', 'answerEvidence', 'auditStatus',
                     'acceptedAnswers', 'sourceAnswerVariants', 'explanationConflict', 'extraTokens']
        result = {key: q[key] for key in keys if key in q}
        if is_structured(q):
            result['stemBlocks'] = safe_stem_blocks(q.get('stemBlocks'))
        if not review and result.get('warnings'):
            result['warnings'] = ['This question has a material-verification note. Details are available in review.']
        if q.get('choices'):
            result['choices'] = [{key: choice[key] for key in ['id', 'text'] if key in choice} for choice in q['choices']]
        if q.get('blanks'):
            fields = ['id', 'prefix', 'suffix', 'length', 'number', 'missingLength'] + (['answer', 'fullWord', 'missingLetters', 'auditStatus', 'answerConflict', 'sourceReferenceAnswer', 'acceptedAnswers', 'resolutionEvidence', 'answerEvidence'] if review else [])
            result['blanks'] = [{key: blank[key] for key in fields if key in blank} for blank in q['blanks']]
        if not review and a['phase'] == 'audio':
            result = {key: q[key] for key in ['id', 'type', 'taskType', 'presentationSchema', 'structuredContentStatus'] if key in q}
            media_item = engine.current_media(a) or {}
            if (engine.stage(a)['section'] == 'listening' and q.get('taskType') == 'listen_response'
                    and media_item.get('kind') not in ['directions', 'instructions']):
                # The official short-response screen previews its disabled
                # choices during the spoken prompt, but never its transcript.
                result.update({key: q[key] for key in ['number', 'numberEnd'] if key in q})
                if q.get('choices'):
                    result['choices'] = [{key: choice[key] for key in ['id', 'text'] if key in choice} for choice in q['choices']]
            audio_blocks = [block for block in safe_stem_blocks(q.get('stemBlocks'))
                            if block.get('type') == 'form_diagram']
            if audio_blocks:
                result['stemBlocks'] = audio_blocks
        if not review and engine.stage(a)['section'] in ['listening', 'speaking']:
            result.pop('passage', None)
        result['assets'] = []
        current_stage = engine.stage(a) if not review else None
        for index, asset in enumerate(q.get('assets', [])):
            if not review and not asset_is_active(q, asset, index, current_stage['section'] if current_stage else None):
                continue
            mapped = asset_url(a, asset.get('url'), review)
            if mapped:
                safe_asset = {**mapped, 'role': asset.get('role', 'stem'), 'alt': asset.get('alt', 'Question image')}
                if is_structured(q):
                    safe_asset.update({key: asset[key] for key in ['highResolution', 'width', 'height', 'choiceId'] if key in asset})
                result['assets'].append(safe_asset)
        media = engine.media_sequence(q)
        if review:
            result['sourceEvidenceAssets'] = []
            for evidence in q.get('sourceEvidenceAssets', []):
                mapped = asset_url(a, evidence.get('url'), True)
                if mapped:
                    result['sourceEvidenceAssets'].append({**mapped, **{key: evidence[key] for key in ['alt', 'reviewOnly', 'page', 'cropBounds'] if key in evidence}})
            stimulus_source = q.get('stimulusSource')
            if isinstance(stimulus_source, dict):
                safe_source = {key: stimulus_source[key] for key in ['materialId', 'page'] if key in stimulus_source}
                if stimulus_source.get('url'):
                    safe_source.update(asset_url(a, stimulus_source['url'], True) or {})
                if safe_source:
                    result['stimulusSource'] = safe_source
            result['mediaSequence'] = [{**{key: m[key] for key in ['durationSeconds', 'mediaType', 'kind'] if key in m},
                                        **(asset_url(a, m.get('url'), True) or {})} for m in media]
            source = q.get('source', {})
            result['source'] = {key: source[key] for key in ['page', 'materialId', 'number'] if key in source}
            if source.get('url'):
                result['source'].update(asset_url(a, source['url'], True) or {})
        elif a['phase'] == 'audio':
            media_item = engine.current_media(a)
            if media_item:
                result['audio'] = {**{key: media_item[key] for key in ['durationSeconds', 'mediaType', 'kind', 'scope'] if key in media_item},
                                   **(asset_url(a, media_item.get('url')) or {}), 'mediaIndex': a['mediaIndex']}
                instruction_text = verified_direction_text(a, media_item)
                if instruction_text:
                    result['audio']['instructions'] = instruction_text
        if not review and a['mode'] == 'practice' and engine.stage(a)['timer'] == 'untimed':
            result['practiceMediaSequence'] = [{**{key: item[key] for key in ['durationSeconds', 'mediaType', 'kind', 'title'] if key in item},
                                               **(asset_url(a, item.get('url')) or {})} for item in media]
            if (engine.practice_aids_enabled(a) and q.get('displayTranscriptDuringPractice') is True
                    and isinstance(q.get('transcript'), str)):
                result['transcript'] = q['transcript']
                result['displayTranscriptDuringPractice'] = True
                result['transcriptLabel'] = '原文研读 · 不冒充有原音的听力考试'
        result['mediaCount'] = len(media)
        if review:
            result['explanation'] = explain(q)
            if q.get('explanationSource'):
                explanation_source = q['explanationSource']
                mapped = {key: explanation_source[key] for key in ['page', 'materialId', 'label', 'origin', 'official'] if key in explanation_source}
                if explanation_source.get('url'):
                    mapped.update(asset_url(a, explanation_source['url'], True) or {})
                result['explanationSource'] = mapped
                if result['explanation']['origin'] == 'source':
                    result['explanation']['source'] = mapped
        return result

    def recordings(db, a):
        grouped = {}
        rows = db.execute('SELECT * FROM recordings WHERE session_id=? ORDER BY created_at,chunk_index', (a['id'],)).fetchall()
        takes = {}
        for row in rows:
            take = takes.setdefault(row['take_id'], {'takeId': row['take_id'], 'questionId': row['question_id'],
                    'url': f"/api/sessions/{a['id']}/recordings/takes/{row['take_id']}", 'mimeType': row['mime_type'],
                    'size': 0, 'segments': [], 'createdAt': row['created_at']})
            take['size'] += row['size']
            take['segments'].append({'id': row['id'], 'index': row['chunk_index'], 'size': row['size']})
        finals = {row['take_id']: row for row in db.execute('SELECT * FROM recording_takes WHERE session_id=?', (a['id'],))}
        for take_id, row in finals.items():
            takes.setdefault(take_id, {'takeId': take_id, 'questionId': row['question_id'],
                'url': f"/api/sessions/{a['id']}/recordings/takes/{take_id}", 'mimeType': row['mime_type'],
                'size': 0, 'segments': [], 'createdAt': row['finalized_at']})
        for take in takes.values():
            take['segments'].sort(key=lambda item: item['index'])
            indices = [s['index'] for s in take['segments']]
            final = finals.get(take['takeId'])
            take['finalized'] = final is not None
            take['expectedSegmentCount'] = final['expected_count'] if final else None
            take['endedReason'] = final['ended_reason'] if final else None
            take['contiguous'] = indices == list(range(len(indices)))
            take['missingIndices'] = sorted(set(range(final['expected_count'])) - set(indices)) if final else []
            take['completeSequence'] = bool(final and final['expected_count'] > 0 and indices == list(range(final['expected_count'])))
            take['state'] = 'complete' if take['completeSequence'] else 'not_finalized' if not final else 'empty' if final['expected_count'] == 0 else 'missing_segments'
            grouped.setdefault(take['questionId'], []).append(take)
        return grouped

    def recording_integrity(a, grouped):
        expected = [q['id'] for st in a['plan'] if st['section'] == 'speaking' for q in st.get('questions', [])] if a['status'] == 'completed' else list(a['visitedSpeaking'])
        recorded = [qid for qid in expected if any(take['completeSequence'] for take in grouped.get(qid, []))]
        incomplete = [{'takeId': take['takeId'], 'questionId': qid, 'reason': take['state'],
                       'expectedSegmentCount': take['expectedSegmentCount'], 'receivedSegmentCount': len(take['segments']),
                       'missingIndices': take['missingIndices']}
                      for qid, takes in grouped.items() for take in takes if not take['completeSequence']]
        missing = [qid for qid in expected if qid not in recorded]
        complete = not missing and not incomplete
        return {'status': 'complete' if complete else 'pending' if a['status'] == 'active' else 'incomplete',
                'expectedQuestionIds': expected, 'recordedQuestionIds': recorded, 'missingQuestionIds': missing,
                'incompleteTakes': incomplete}

    def summary(a, validations=None):
        result = {key: a.get(key) for key in ['id', 'examId', 'title', 'mode', 'scope', 'routeMode', 'route', 'status',
                                           'startedAt', 'updatedAt', 'completedAt', 'interrupted', 'rulesVersion', 'filters', 'filtered', 'supplemental', 'timingPolicy']}
        result['requiresMicrophone'] = any(part.get('section') == 'speaking' and bool(part.get('questions')) for part in a.get('plan', []))
        result['writingExpiryAcknowledgement'] = a.get('writingExpiryAcknowledgement') is True
        result['allowPracticeAids'] = engine.practice_aids_enabled(a)
        if isinstance(a.get('practiceGroup'), dict):
            result['practiceGroup'] = {key: a['practiceGroup'][key] for key in GROUP_SESSION_FIELDS if key in a['practiceGroup']}
        result.update(engine.score_snapshot_metadata(a))
        full = a.get('isFullScope')
        if full is None:
            # Older sessions did not identify filtered practice. Compare their
            # frozen selected plan to the actual source scope; never assume full.
            full = False
            exam = catalog.exams.get(a['examId'])
            if exam and not a.get('filters'):
                try:
                    expected = []
                    scope = a.get('scope', 'all')
                    for sec in exam.get('sections', []):
                        if scope != 'all' and sec['id'] != scope:
                            continue
                        selected_route = a.get('routes', {}).get(sec['id'], a.get('route', 'upper'))
                        expected.extend(engine.make_plan(exam, {'scope': sec['id'], 'route': selected_route}, a['timing']))
                    actual_ids = [q['id'] for st in a['plan'] for q in st.get('questions', [])]
                    expected_ids = [q['id'] for st in expected for q in st.get('questions', [])]
                    complete_sections = scope != 'all' or {st['section'] for st in expected} == set(engine.ORDER)
                    full = bool(expected_ids) and complete_sections and len(actual_ids) == len(expected_ids) and set(actual_ids) == set(expected_ids)
                except (engine.ExamError, KeyError, TypeError):
                    pass
        result['isFullScope'] = full is True
        snapshot = a.get('verificationSnapshot')
        result['sourceSnapshotStatus'] = 'verified' if snapshot and snapshot.get('status') == 'passed' else 'unverified' if snapshot else 'legacy-unverified'
        if result['filtered'] is None:
            result['filtered'] = not result['isFullScope']
        current_exam = catalog.exams.get(a['examId'])
        current_questions = {q['id']: q for s in current_exam.get('sections', []) for m in s.get('modules', []) for q in m.get('questions', [])} if current_exam else {}
        previous_questions = [q for st in a['plan'] for q in st.get('questions', [])]
        result['sourceVersionMatches'] = bool(previous_questions) and all(q.get('contentId') and current_questions.get(q['id'], {}).get('contentId') == q['contentId'] for q in previous_questions)
        if result['sourceVersionMatches'] and snapshot:
            current_inputs = current_exam.get('verificationInputs') or {}
            if snapshot.get('curationSha256ByPath') != current_inputs.get('curationSha256ByPath'):
                result['sourceVersionMatches'] = False
            for url, expected in snapshot.get('sourceSha256ByUrl', {}).items():
                if source_integrity.expected_for_url(current_exam, url) != expected:
                    result['sourceVersionMatches'] = False
                    break
            for url, expected in snapshot.get('assetSha256ByUrl', {}).items():
                current_expected = source_integrity.expected_for_url(current_exam, url)
                if current_expected is not None and current_expected != expected:
                    result['sourceVersionMatches'] = False
                    break
            for url, expected in snapshot.get('reviewAssetSha256ByUrl', {}).items():
                current_expected = source_integrity.expected_for_url(current_exam, url)
                if current_expected is not None and current_expected != expected:
                    result['sourceVersionMatches'] = False
                    break
        if result['sourceVersionMatches']:
            if validations is not None and a['examId'] in validations:
                runtime = validations[a['examId']]
            else:
                runtime = source_integrity.check_exam(current_exam)
                if validations is not None:
                    validations[a['examId']] = runtime
            result['sourceVersionMatches'] = runtime['status'] == 'passed'
            result['runtimeSourceStatus'] = runtime['status']
        else:
            result['runtimeSourceStatus'] = 'content-version-unverified'
        result.update(recovery_flags(a, catalog, source_integrity))
        return result

    def session_view(db, a, now):
        st, q = engine.stage(a), engine.question(a)
        active = a['status'] == 'active'
        allowed = []
        if active:
            allowed += ['interrupt', 'finish']
            if a['phase'] == 'directions':
                allowed.append('begin')
            elif a['phase'] == 'response':
                allowed += ['answer']
                if st['section'] != 'speaking' or a['mode'] == 'practice':
                    allowed.append('next')
                if st['canBack']:
                    allowed += ['jump', 'flag']
                    if a['questionIndex'] > 0:
                        allowed.append('back')
            elif a['phase'] == 'audio':
                allowed += ['audio-ended', 'audio-started']
            elif a['phase'] == 'expired':
                allowed.append('continue')
            if a['mode'] == 'practice' and a['phase'] != 'expired':
                if a['phase'] != 'audio' or engine.practice_aids_enabled(a):
                    allowed.append('resume' if a['phase'] == 'paused' else 'pause')
                if engine.practice_aids_enabled(a) and q and engine.media_sequence(q) and a['phase'] == 'response' and st['timer'] != 'untimed':
                    allowed.append('replay')
        safe_stage = {key: st[key] for key in ['id', 'section', 'title', 'timer', 'seconds', 'canBack', 'route', 'instructions', 'hasDirectionsAudio', 'referenceOnly'] if key in st} if st else None
        if safe_stage:
            safe_stage['questionCount'] = len(st['questions'])
            safe_stage['itemCount'] = sum(len(item.get('blanks', [])) if item.get('type') == 'cloze' else 1 for item in st['questions'])
            safe_stage['currentQuestionUnitStart'] = 1 + sum(len(item.get('blanks', [])) if item.get('type') == 'cloze' else 1 for item in st['questions'][:a['questionIndex']])
            safe_stage['sectionItemCount'] = sum(len(item.get('blanks', [])) if item.get('type') == 'cloze' else 1 for part in a['plan'] if part['section'] == st['section'] for item in part['questions'])
            safe_stage['sectionQuestionOffset'] = sum(len(part['questions']) for part in a['plan'][:a['stageIndex']] if part['section'] == st['section'])
            safe_stage['practiceAudio'] = [{**{key: media[key] for key in ['durationSeconds', 'mediaType', 'title'] if key in media},
                                           **(asset_url(a, media.get('url')) or {})} for media in st.get('practiceAudio', [])] if a['mode'] == 'practice' else []
        all_recordings = recordings(db, a)
        recording_status = recording_integrity(a, all_recordings)
        qid = q['id'] if q else None
        return {**summary(a), 'serverNow': now, 'deadline': a['deadline'], 'revision': a['revision'], 'phase': a['phase'],
                'stageIndex': a['stageIndex'], 'questionIndex': a['questionIndex'], 'stage': safe_stage,
                'remainingSeconds': max(0, math.ceil((a['deadline'] - now) / 1000)) if a['deadline'] is not None else None,
                'audioEarliestEnd': a.get('audioEarliestEnd'), 'mediaIndex': a.get('mediaIndex', 0),
                'question': safe_question(a, q) if active and a['phase'] != 'directions' else None,
                'answer': a['answers'].get(qid) if active else None, 'flags': a['flags'],
                'recordingSegments': all_recordings.get(qid, []), 'recordingIntegrity': recording_status, 'allowedActions': allowed,
                'questionMap': [{'index': index, 'questionId': item['id'], 'answered': engine.has_answer(a['answers'].get(item['id'])),
                                  'flagged': bool(a['flags'].get(item['id']))} for index, item in enumerate(st['questions'])] if st and st.get('canBack') else [],
                'integrity': {'interrupted': a['interrupted'], 'recordingsComplete': recording_status['status'] == 'complete',
                              'sourcesVerified': (a.get('verificationSnapshot') or {}).get('status') == 'passed' and (a.get('verificationSnapshot') or {}).get('originalSourcesVerified', True),
                              'preparedAssetsVerified': (a.get('verificationSnapshot') or {}).get('status') == 'passed' and (a.get('verificationSnapshot') or {}).get('verificationMode') == 'prepared-assets',
                              'eligibleForContinuousStrict': a['mode'] == 'strict' and a['status'] == 'completed' and not a['interrupted'] and recording_status['status'] == 'complete' and (a.get('verificationSnapshot') or {}).get('status') == 'passed',
                              'events': [event for event in a['events'] if event['type'] in ['interrupted', 'resumed', 'missing-audio', 'recording-error', 'clock-gap', 'source-changed', 'legacy-audio-unverified', 'legacy-audio-recovered']]},
                'progress': {'stageIndex': a['stageIndex'], 'totalStages': len(a['plan']), 'questionIndex': a['questionIndex'],
                             'totalQuestions': sum(len(s.get('questions', [])) for s in a['plan'])},
                'timing': a['timing'], 'routes': a['routes'], 'rulesVersion': a['rulesVersion'], 'scoringPolicy': a.get('scoringPolicy'),
                'warnings': a['examWarnings'], 'notice': 'Local simulation; selected timing and adaptive defaults are not ETS calibration.'}

    def review_view(db, a):
        reject_during_strict(db)
        if a['status'] == 'active':
            raise engine.ExamError('Review is available only after the session ends.', 403)
        sections = []
        for section_id in engine.ORDER:
            modules = []
            for st in a['plan']:
                if st['section'] != section_id or not st.get('questions'):
                    continue
                questions = []
                for q in st['questions']:
                    safe = safe_question(a, q, review=True)
                    safe['grade'] = engine.session_grade(a, q, section_id)
                    questions.append(safe)
                modules.append({'id': st['id'], 'title': st['title'], 'questions': questions})
            if modules:
                sections.append({'id': section_id, 'title': section_id.title(), 'modules': modules})
        ratings = {row['question_id']: {'value': row['value'], 'notes': row['notes'], 'updatedAt': row['updated_at']}
                   for row in db.execute('SELECT * FROM ratings WHERE session_id=?', (a['id'],))}
        saved_recordings = recordings(db, a)
        score = engine.score(a)
        score['attemptedCount'] += sum(not engine.has_answer(a['answers'].get(qid)) and any(take['size'] > 0 for take in takes) for qid, takes in saved_recordings.items())
        return {'session': session_view(db, a, clock()), 'exam': {'id': a['examId'], 'title': a['title'], 'sections': sections},
                'sections': sections, 'answers': a['answers'], 'recordings': saved_recordings, 'score': score,
                'ratings': ratings, 'events': a['events'], 'recordingIntegrity': recording_integrity(a, saved_recordings),
                'scoreSnapshot': deepcopy(a.get('scoreSnapshot'))}

    @app.get('/api/health')
    def health():
        return {'ok': True, 'storage': 'sqlite', 'serverNow': clock(), 'rulesVersion': engine.RULES_VERSION}

    @app.get('/api/documentation/{locale}/{document}')
    def documentation(locale: str, document: str):
        """Serve public Markdown from an explicit map, never client-selected paths."""
        public_docs = [
            'USER_GUIDE', 'IMPORTING', 'TROUBLESHOOTING', 'ARCHITECTURE',
            'TESTING', 'MATERIALS', 'OFFICIAL_RULES', 'DATA_QA', 'ACCEPTANCE',
            'DESIGN_REFERENCES', 'EXAM_UI_REFERENCE', 'GOAL_COMPLETION_AUDIT',
            'MEDIA_SEGMENTS', 'ets-2026-verification', 'PROJECT_HISTORY',
            'STRICT_MODE_SECURITY_REVIEW', 'TEXT_FIDELITY',
        ]
        paths = {name: root / 'docs' / name for name in public_docs}
        paths['DOCUMENTATION_INDEX'] = root / 'docs' / 'README'
        paths['BUNDLED_ETS_PRACTICE_TEST_1'] = root / 'examples/ets-practice-test-1/README'
        paths['BUNDLED_ETS_PRACTICE_TEST_1_NOTICE'] = root / 'examples/ets-practice-test-1/NOTICE'
        for name in ['README', 'CONTRIBUTING', 'SECURITY', 'CODE_OF_CONDUCT', 'CHANGELOG']:
            paths[name] = root / name
        if locale not in ['en', 'zh-CN'] or document not in paths:
            raise engine.ExamError('Documentation not found.', 404)
        # Preserve old localized endpoints as aliases without maintaining
        # translated copies. Only the project README follows the UI language.
        content_locale = locale if document == 'README' else 'en'
        suffix = '.zh-CN.md' if content_locale == 'zh-CN' else '.md'
        path = Path(str(paths[document]) + suffix)
        # Do not follow symlinks even when an allowlisted filename was replaced locally.
        if (not path.is_file() or path.is_symlink()
                or any(parent.is_symlink() for parent in path.parents if parent.is_relative_to(root))
                or not path.resolve().is_relative_to(root.resolve())):
            raise engine.ExamError('Documentation not found.', 404)
        return FileResponse(path, media_type='text/plain; charset=utf-8',
                            headers={'Content-Language': content_locale})

    @app.get('/api/catalog')
    def get_catalog():
        catalog.refresh()
        result = catalog.public()
        for summary_item in result['exams']:
            full = catalog.exams[summary_item['id']]
            runtime = source_integrity.check_exam(full)
            summary_item['runtimeVerification'] = runtime
            if runtime['status'] != 'passed':
                summary_item['strictEligible'] = False
                summary_item['scopedEligibility'] = {section: False for section in engine.ORDER}
                summary_item.setdefault('warnings', []).append('Source files or verification inputs changed/missing. Stop the service and reimport before strict practice.')
            eligible = {}
            for sec in full.get('sections', []):
                routes = {mod.get('route', 'common') for mod in sec.get('modules', [])}
                eligible[sec['id']] = {'common', 'upper', 'lower'}.issubset(routes)
                public_section = next(s for s in summary_item['sections'] if s['id'] == sec['id'])
                public_section['taskTypes'] = sorted({q.get('taskType', q.get('type')) for m in sec.get('modules', []) for q in m.get('questions', []) if q.get('taskType') or q.get('type')})
                public_section['adaptiveEligible'] = eligible[sec['id']]
            summary_item['adaptiveEligibility'] = eligible
            summary_item['adaptiveEligible'] = eligible.get('reading', False) and eligible.get('listening', False)
        return result

    @app.post('/api/resource-packs')
    async def import_resource_pack(request: Request):
        """The browser accepts text-only JSON; local media packs use the CLI."""
        from .packs import import_pack
        payload = await read_json(request)
        with store.transaction() as db:
            if any(a['status'] == 'active' and a['mode'] == 'strict' for a in store.all(db)):
                raise engine.ExamError('Finish the active strict session before importing resources.', 409)
            result = import_pack(root, payload)
        catalog.refresh()
        return result

    @app.post('/api/resource-packs/demo')
    async def import_demo(request: Request):
        from .example_pack import install_example
        # Install the signed native exam, retaining its clocks, media and provenance.
        # No client-selected filesystem path is accepted by this endpoint.
        with store.transaction() as db:
            if any(a['status'] == 'active' and a['mode'] == 'strict' for a in store.all(db)):
                raise engine.ExamError('Finish the active strict session before importing resources.', 409)
            result = install_example(root)
        catalog.refresh()
        return result

    @app.get('/api/exams/{exam_id}')
    def exam_info(exam_id: str):
        return next((exam for exam in get_catalog()['exams'] if exam['id'] == valid_id(exam_id)), None) or JSONResponse({'error': 'Exam not found.'}, status_code=404)

    @app.get('/api/rules')
    def rules():
        path = root / 'shared/rules.json'
        return json.loads(path.read_text()) if path.is_file() else {'version': engine.RULES_VERSION, 'defaults': engine.DEFAULT_TIMING,
                'notice': 'Local practice configuration. No ETS calibration or official score conversion.'}

    @app.get('/api/validation')
    def validation():
        with store.transaction() as db:
            reject_during_strict(db)
        path = root / 'generated/audit.json'
        audit = json.loads(path.read_text()) if path.is_file() else {}
        # The audit may include source paths for local review, but it never serves
        # arbitrary files or question answer keys through this public endpoint.
        return {'schemaVersion': 1, 'summary': audit.get('summary', {}), 'coverage': catalog.data.get('stats', {}),
                'exams': [{'id': e['id'], 'title': e.get('title'), 'validation': e.get('validation', {}), 'warnings': e.get('warnings', [])} for e in catalog.exams.values()],
                'warnings': audit.get('warnings', []), 'fileCount': len(catalog.data.get('materials', []))}

    @app.get('/api/practice-groups')
    def practice_groups(section: str = '', taskType: str = '', q: str = '', page: int = 1, pageSize: int = 24, deduplicate: bool = False):
        if section and section not in ['all', *engine.ORDER]:
            raise engine.ExamError('Invalid question section.', 422)
        if not 1 <= pageSize <= 100 or page < 1 or len(q) > 200:
            raise engine.ExamError('Use a positive page, pageSize 1–100 and a short search query.', 422)
        catalog.refresh()
        with store.transaction() as db:
            reject_during_strict(db)
            groups = build_practice_groups(catalog, store.all(db))
            query = q.strip().casefold()
            filtered = [group for group in groups if (section in ['', 'all'] or group['section'] == section)
                        and (not query or query in group['_searchText'])]
            task_counts = dict(Counter(group['taskType'] for group in filtered))
            if taskType and taskType != 'all':
                filtered = [group for group in filtered if group['taskType'] == taskType]
            if deduplicate:
                unique = {}
                for group in filtered:
                    unique.setdefault(group['_dedupeKey'], group)
                filtered = list(unique.values())
            return {'items': [public_group(group) for group in filtered[(page - 1) * pageSize:page * pageSize]],
                    'total': len(filtered), 'page': page, 'pageSize': pageSize,
                    'taskCounts': task_counts, 'deduplicate': deduplicate}

    @app.get('/api/questions')
    def question_library(section: str = '', taskType: str = '', q: str = '', page: int = 1, pageSize: int = 24, deduplicate: bool = False):
        if section and section not in ['all', *engine.ORDER]:
            raise engine.ExamError('Invalid question section.', 422)
        if not 1 <= pageSize <= 100 or page < 1 or len(q) > 200:
            raise engine.ExamError('Use a positive page, pageSize 1–100 and a short search query.', 422)
        with store.transaction() as db:
            reject_during_strict(db)
            history_items = store.all(db)
        catalog.refresh()
        progress = {}
        for saved in history_items:
            for st in saved['plan']:
                for item in st.get('questions', []):
                    if not item.get('contentId'):
                        continue
                    key = (saved['examId'], item['id'], item['contentId'])
                    if key in progress:
                        continue
                    if saved['status'] == 'completed' or (saved['status'] == 'abandoned' and item['id'] in saved['visitedQuestions']):
                        progress[key] = 'completed'
                    elif saved['status'] == 'active' and item['id'] in saved['visitedQuestions']:
                        progress[key] = 'in_progress'
        rows = []
        names = {material['id']: material.get('name') for material in catalog.data.get('materials', [])}
        for exam in catalog.exams.values():
            for sec in exam.get('sections', []):
                for mod in sec.get('modules', []):
                    for item in mod.get('questions', []):
                        if not engine.question_available(item):
                            continue
                        supplied_title = next((item[key] for key in ['passageTitle', 'topic', 'title'] if isinstance(item.get(key), str) and item[key].strip()), None)
                        number = item.get('number')
                        title = supplied_title[:100] if supplied_title else f"{mod.get('title', mod['id'])} · {number if number is not None else item['id']}"
                        content_id = item.get('contentId') or item.get('canonicalId')
                        if not content_id:
                            identity = {key: item.get(key) for key in ['type', 'prompt', 'passage', 'choices', 'tokens', 'transcript']}
                            identity['blanks'] = [{key: blank.get(key) for key in ['prefix', 'length']} for blank in item.get('blanks', [])]
                            if not item.get('transcript'):
                                identity['media'] = [m.get('url') for m in engine.media_sequence(item)]
                            content_id = 'content-' + hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]
                        task = item.get('taskType') or item.get('type')
                        canonical_source = item.get('source') or {}
                        edition_source = item.get('editionSource') or canonical_source
                        row = {'questionId': item['id'], 'examId': exam['id'], 'examTitle': exam.get('title', exam['id']),
                               'section': sec['id'], 'module': mod.get('title', mod['id']), 'moduleId': mod['id'], 'title': title,
                               'taskType': task, 'number': number, 'sourcePage': edition_source.get('page'),
                               'sourceMaterialId': edition_source.get('materialId'), 'sourceMaterialName': names.get(edition_source.get('materialId')),
                               'canonicalSourcePage': canonical_source.get('page'), 'canonicalSourceMaterialId': canonical_source.get('materialId'),
                               'canonicalSourceMaterialName': names.get(canonical_source.get('materialId')),
                               'auditStatus': item.get('auditStatus') or item.get('verificationStatus') or ('verified' if exam.get('strictEligible') else 'needs-review'),
                               'hasAudio': bool(item.get('audio') or item.get('mediaSequence')),
                               'status': progress.get((exam['id'], item['id'], content_id), 'not_started'), 'contentId': content_id}
                        searchable = ' '.join(str(value) for value in [title, exam.get('title', ''), item.get('prompt', ''), item.get('passage', ''), task]).lower()
                        rows.append((row, searchable))
        duplicates = Counter(row['contentId'] for row, _ in rows)
        filtered = [row for row, search in rows if (not section or section == 'all' or row['section'] == section) and (not q or q.lower() in search)]
        task_counts = dict(Counter(row['taskType'] for row in filtered))
        if taskType and taskType != 'all':
            filtered = [row for row in filtered if row['taskType'] == taskType]
        if deduplicate:
            unique = {}
            for row in filtered:
                unique.setdefault(row['contentId'], row)
            filtered = list(unique.values())
        for row in filtered:
            row['duplicateCount'] = duplicates[row['contentId']]
        return {'items': filtered[(page - 1) * pageSize:page * pageSize], 'total': len(filtered), 'page': page,
                'pageSize': pageSize, 'taskCounts': task_counts, 'deduplicate': deduplicate}

    @app.get('/api/mistakes')
    def mistake_collection(section: str = 'all', status: str = 'needs_review', q: str = '', page: int = 1, pageSize: int = 24):
        if section not in ['', 'all', *engine.ORDER] or status not in ['all', 'needs_review', 'mastered']:
            raise engine.ExamError('Choose a valid mistake section and review status.', 422)
        if not 1 <= pageSize <= 100 or page < 1 or len(q) > 200:
            raise engine.ExamError('Use a positive page, pageSize 1–100 and a short search query.', 422)
        with store.transaction() as db:
            reject_during_strict(db)
            # Creation order makes equal completion timestamps deterministic;
            # a later interruption event must not make an old answer "latest".
            saved_sessions = [json.loads(row['body']) for row in db.execute('SELECT body FROM sessions ORDER BY rowid')]
            catalog.refresh()
            rows = mistakes.aggregate(saved_sessions)
            query = q.strip().casefold()
            rows = [row for row in rows if (section in ['', 'all'] or row['section'] == section)
                    and (not query or query in ' '.join(str(row.get(key) or '') for key in
                         ['title', 'examTitle', 'questionId', 'taskType', 'number', 'sourcePage']).casefold())]
            counts = {'total': len(rows), 'needsReview': sum(row['status'] == 'needs_review' for row in rows),
                      'mastered': sum(row['status'] == 'mastered' for row in rows),
                      'attempts': sum(row['attempts'] for row in rows)}
            filtered = [row for row in rows if status == 'all' or row['status'] == status]
            items, runtime_by_exam = [], {}
            for row in filtered[(page - 1) * pageSize:page * pageSize]:
                exam = catalog.exams.get(row['examId'])
                current = next((question for sec in exam.get('sections', []) for module in sec.get('modules', [])
                                for question in module.get('questions', []) if question['id'] == row['questionId']), None) if exam else None
                reason = None
                if not current:
                    reason = 'source_missing'
                elif row['_version'] != mistakes.question_version(current):
                    reason = 'source_changed'
                elif not engine.question_available(current) or not row['_session'].get('verificationSnapshot'):
                    reason = 'source_unverified'
                else:
                    snapshot = row['_session']['verificationSnapshot']
                    inputs = exam.get('verificationInputs') or {}
                    if snapshot.get('curationSha256ByPath') != inputs.get('curationSha256ByPath') or any(
                        source_integrity.expected_for_url(exam, url) != expected
                        for mapping in ['sourceSha256ByUrl', 'assetSha256ByUrl', 'reviewAssetSha256ByUrl']
                        for url, expected in snapshot.get(mapping, {}).items()
                    ):
                        reason = 'source_changed'
                    else:
                        runtime = runtime_by_exam.setdefault(row['examId'], None)
                        if runtime is None:
                            runtime = runtime_by_exam[row['examId']] = source_integrity.check_exam(exam)
                        if runtime['status'] != 'passed':
                            reason = 'source_unverified'
                items.append({**{key: value for key, value in row.items() if not key.startswith('_')},
                              'available': reason is None, 'unavailableReason': reason})
            return {'schemaVersion': 1, 'items': items, 'summary': counts, 'total': len(filtered),
                    'page': page, 'pageSize': pageSize, 'section': section or 'all', 'status': status, 'q': q,
                    'notice': 'Objective practice mistakes from submitted answers in ended sessions. Grades use each saved source snapshot; this is not an ETS score.'}

    @app.get('/api/sessions')
    def history():
        catalog.refresh()
        with store.transaction() as db:
            sessions = store.all(db)
            exclusive_ids = {a['id'] for a in sessions if a['status'] == 'active' and a['mode'] == 'strict'}
            for a in sessions:
                if exclusive_ids and a['id'] not in exclusive_ids:
                    continue
                if engine.tick(a, clock()):
                    store.save(db, a)
            if any(a['status'] == 'active' and a['mode'] == 'strict' for a in sessions):
                keys = ['id', 'examId', 'title', 'mode', 'scope', 'status', 'startedAt', 'updatedAt', 'completedAt', 'isFullScope', 'filtered', 'interrupted', 'sourceVersionMatches']
                validations = {}
                summaries = [summary(a, validations) for a in sessions]
                return {'sessions': [{key: item.get(key) for key in keys} for item in summaries]}
            validations = {}
            return {'sessions': [{**summary(a, validations), 'score': {key: value for key, value in engine.score(a).items() if key not in ['items', 'sections']} if a['status'] != 'active' else None} for a in sessions]}

    @app.post('/api/sessions')
    async def create_session(request: Request):
        payload = await read_json(request)
        with store.transaction() as db:
            if any(s['status'] == 'active' and s['mode'] == 'strict' for s in store.all(db)):
                raise engine.ExamError('A strict session is active. New sessions are locked until it ends.', 403)
        catalog.refresh()
        exam = catalog.exams.get(valid_id(payload.get('examId')))
        if not exam:
            raise engine.ExamError('Exam not found.', 404)
        if manifest_issues(exam):
            raise engine.ExamError('The structured-content verification manifest does not match this generated exam. Reimport the source materials.', 409)
        practice_group = None
        if 'practiceGroupId' in payload:
            valid_id(payload['practiceGroupId'])
            if 'expectedGroupContentId' in payload:
                valid_id(payload['expectedGroupContentId'])
            payload, practice_group = group_session_options(catalog, exam, payload)
        elif 'expectedGroupContentId' in payload:
            raise engine.ExamError('A group content expectation requires a practice group.', 422)
        a = engine.new_session(exam, payload, clock())
        if practice_group is not None:
            planned_questions = [question for stage in a['plan'] for question in stage.get('questions', [])]
            planned_ids = [question['id'] for question in planned_questions]
            if (planned_ids != payload['questionIds'] or any(stage.get('branches') for stage in a['plan'])
                    or group_revision(practice_group['groupId'], planned_questions, catalog.exam_digests.get(exam['id'])) != practice_group['groupContentId']):
                raise engine.ExamError('The selected practice group could not be frozen in its complete source order. Refresh the practice library.', 409)
            a['practiceGroup'] = practice_group
        if payload.get('mode') == 'strict':
            runtime = source_integrity.check_exam(exam)
            if runtime['status'] != 'passed':
                raise engine.ExamError('Source files or verification versions changed/missing. Stop the service and reimport before starting strict practice.', 409)
        catalog.register_tree(a['plan'])
        source_integrity.freeze_assets(a, exam)
        if a['mode'] == 'strict':
            for st in a['plan']:
                candidates = [st] if not st.get('branches') else [s for branch in st['branches'].values() for s in branch]
                for candidate in candidates:
                    for q in candidate['questions']:
                        for media in engine.media_sequence(q):
                            asset_id = catalog.register(media.get('url'))
                            if not asset_id or not catalog.path_for(asset_id):
                                raise engine.ExamError('A required prompt file is missing. Strict practice cannot begin.', 422)
        with store.transaction() as db:
            if any(s['status'] == 'active' and s['mode'] == 'strict' for s in store.all(db)):
                raise engine.ExamError('A strict session is already active. New sessions are locked until it ends.', 403)
            store.save(db, a)
            return session_view(db, a, clock())

    @app.get('/api/sessions/{session_id}')
    def get_session_view(session_id: str):
        catalog.refresh()
        with store.transaction() as db:
            a = get_session(db, session_id)
            exclusive_session_guard(db, a)
            if engine.tick(a, clock()):
                store.save(db, a)
            return session_view(db, a, clock())

    @app.post('/api/sessions/{session_id}/recover-audio')
    async def recover_session_audio(session_id: str, request: Request):
        payload = await read_json(request)
        if payload:
            raise engine.ExamError('Audio recovery expects an empty JSON object.', 422)
        catalog.refresh()
        with store.transaction() as db:
            a = get_session(db, session_id)
            reject_during_strict(db)
            now = clock()
            # Recovery never ticks, rewinds or submits a question. The next
            # normal event retains the original authoritative deadline checks.
            if recover_audio(a, catalog, source_integrity, now):
                store.save(db, a)
            return session_view(db, a, now)

    @app.post('/api/sessions/{session_id}/events')
    async def session_event(session_id: str, request: Request):
        payload = await read_json(request)
        request_id = valid_id(payload.get('requestId'))
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        error = None
        with store.transaction() as db:
            a = get_session(db, session_id)
            exclusive_session_guard(db, a)
            now = clock()
            engine.tick(a, now)
            previous = db.execute('SELECT payload_hash FROM requests WHERE session_id=? AND request_id=?', (session_id, request_id)).fetchone()
            if previous:
                if previous['payload_hash'] != fingerprint:
                    error = engine.ExamError('This requestId was already used for a different action.')
            else:
                try:
                    engine.apply_event(a, payload, now)
                    db.execute('INSERT INTO requests(session_id,request_id,payload_hash) VALUES(?,?,?)', (session_id, request_id, fingerprint))
                except engine.ExamError as exc:
                    error = exc
            store.save(db, a)
            view = session_view(db, a, now)
        if error:
            return JSONResponse({'error': error.message, 'session': view}, status_code=error.status)
        return view

    @app.get('/api/sessions/{session_id}/review')
    def review(session_id: str):
        with store.transaction() as db:
            a = get_session(db, session_id)
            if engine.tick(a, clock()):
                store.save(db, a)
            return review_view(db, a)

    @app.get('/api/sessions/{session_id}/feedback')
    def feedback(session_id: str, questionId: str):
        with store.transaction() as db:
            reject_during_strict(db)
            a = get_session(db, session_id)
            if a['status'] == 'active' and not engine.practice_aids_enabled(a):
                raise engine.ExamError('Replay, immediate feedback and review resources were not enabled for this practice session.', 403)
            if a['mode'] != 'practice' or questionId not in a['visitedQuestions']:
                raise engine.ExamError('Immediate feedback is only available for visited practice questions.', 403)
            q = next(q for st in a['plan'] for q in st.get('questions', []) if q['id'] == questionId)
            rating = db.execute('SELECT value,notes FROM ratings WHERE session_id=? AND question_id=?', (a['id'], questionId)).fetchone()
            reviewed_question = safe_question(a, q, review=True)
            return {'question': reviewed_question, 'answer': a['answers'].get(questionId),
                    'grade': engine.session_grade(a, q), 'recordings': recordings(db, a).get(questionId, []),
                    'rating': dict(rating) if rating else None, 'explanation': reviewed_question['explanation']}

    @app.get('/api/sessions/{session_id}/export')
    def export(session_id: str):
        with store.transaction() as db:
            a = get_session(db, session_id)
            result = review_view(db, a)
            result['exportedAt'] = clock()
            result['notice'] = 'JSON export. Download grouped recording takes separately. This is not an ETS score.'
            return JSONResponse(result, headers={'Content-Disposition': f'attachment; filename="{session_id}.json"'})

    @app.put('/api/sessions/{session_id}/ratings')
    async def self_rating(session_id: str, request: Request):
        payload = await read_json(request)
        qid, value = valid_id(payload.get('questionId')), payload.get('value')
        if type(value) is not int or not 0 <= value <= 5 or not isinstance(payload.get('notes', ''), str) or len(payload.get('notes', '')) > 10000:
            raise engine.ExamError('Use an integer rubric rating from 0 to 5 and short notes.', 422)
        with store.transaction() as db:
            a = get_session(db, session_id)
            exclusive_session_guard(db, a)
            if a['status'] == 'active' and a['mode'] != 'practice':
                raise engine.ExamError('Strict-session self-rating is available after completion.', 403)
            q = next((q for st in a['plan'] for q in st.get('questions', []) if q['id'] == qid), None)
            if not q or (q.get('type') not in engine.SUBJECTIVE and q.get('subjective') is not True) or (a['status'] == 'active' and qid not in a['visitedQuestions']):
                raise engine.ExamError('Only a visited writing or speaking response can receive a rubric self-rating.', 422)
            now = clock()
            db.execute('INSERT INTO ratings VALUES(?,?,?,?,?) ON CONFLICT(session_id,question_id) '
                       'DO UPDATE SET value=excluded.value,notes=excluded.notes,updated_at=excluded.updated_at',
                       (session_id, qid, value, payload.get('notes', ''), now))
            return {'questionId': qid, 'value': value, 'notes': payload.get('notes', ''), 'updatedAt': now}

    @app.get('/api/library/{asset_id}')
    def library(asset_id: str):
        catalog.refresh()
        with store.transaction() as db:
            if any(a['status'] == 'active' and a['mode'] == 'strict' for a in store.all(db)):
                raise engine.ExamError('The original-material library is locked while strict practice is active.', 403)
        asset = catalog.assets.get(valid_id(asset_id))
        if not asset or not asset['library']:
            raise engine.ExamError('Library asset not found.', 404)
        path = catalog.path_for(asset_id)
        if not path:
            raise engine.ExamError('Asset not found.', 404)
        media_type = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
        if media_type in ['text/html', 'image/svg+xml', 'text/javascript', 'application/javascript']:
            media_type = 'application/octet-stream'
        return FileResponse(path, media_type=media_type)

    def question_asset_ids(q, review=False, section=None):
        urls = [asset.get('url') for index, asset in enumerate(q.get('assets', []))
                if review or asset_is_active(q, asset, index, section)]
        if review:
            urls += [asset.get('url') for asset in q.get('sourceEvidenceAssets', [])]
            if isinstance(q.get('stimulusSource'), dict):
                urls.append(q['stimulusSource'].get('url'))
        urls += [m.get('url') for m in engine.media_sequence(q)] if review else []
        if review and q.get('source', {}).get('url'):
            urls.append(q['source']['url'])
        if review and (q.get('explanationSource') or {}).get('url'):
            urls.append(q['explanationSource']['url'])
        return {catalog.register(url) for url in urls}

    def serve_session_asset(session_id, asset_id, review=False):
        catalog.refresh()
        with store.transaction() as db:
            a = get_session(db, session_id)
            exclusive_session_guard(db, a)
            if engine.tick(a, clock()):
                store.save(db, a)
            if review:
                reject_during_strict(db)
                if a['status'] == 'active' and a['mode'] != 'practice':
                    raise engine.ExamError('Review assets are locked until this session ends.', 403)
                if a['status'] == 'active' and not engine.practice_aids_enabled(a):
                    raise engine.ExamError('Replay, immediate feedback and review resources were not enabled for this practice session.', 403)
                allowed = set()
                for st in a['plan']:
                    allowed.update(catalog.register(media.get('url')) for media in st.get('practiceAudio', []))
                    for q in st.get('questions', []):
                        if a['status'] != 'active' or q['id'] in a['visitedQuestions']:
                            allowed.update(question_asset_ids(q, review=True))
            else:
                if a['status'] != 'active' or a['phase'] in ['directions', 'paused']:
                    raise engine.ExamError('No question asset is authorized in this phase.', 403)
                q = engine.question(a)
                allowed = question_asset_ids(q, section=engine.stage(a)['section'])
                manual_assets = {catalog.register(media.get('url')) for media in engine.stage(a).get('practiceAudio', [])}
                if a['mode'] == 'practice' and engine.stage(a)['timer'] == 'untimed':
                    manual_assets.update(catalog.register(media.get('url')) for media in engine.media_sequence(q))
                if a['mode'] == 'practice' and asset_id in manual_assets:
                    reject_during_strict(db)
                    allowed.update(manual_assets)
                if a['phase'] == 'audio':
                    allowed.add(catalog.register(engine.current_media(a).get('url')))
            if valid_id(asset_id) not in allowed:
                raise engine.ExamError('This asset does not belong to the currently allowed question.', 403)
            if review and catalog.assets.get(asset_id, {}).get('library') and any(s['status'] == 'active' and s['mode'] == 'strict' for s in store.all(db)):
                raise engine.ExamError('Original source files are locked while strict practice is active.', 403)
            path = catalog.path_for(asset_id)
            if not path:
                raise engine.ExamError('Asset not found.', 404)
            if not source_integrity.session_asset_matches(a, asset_id, path, review=review):
                legacy_audio = (not a.get('verificationSnapshot') and not a.get('assetManifest')
                                and not source_integrity.has_asset_expectation(a, asset_id)
                                and any(catalog.register(media.get('url')) == asset_id
                                        for stage in a['plan'] for question in stage.get('questions', [])
                                        for media in engine.media_sequence(question)))
                a['interrupted'] = True
                engine.log(a, 'legacy-audio-unverified' if legacy_audio else 'source-changed', {'assetId': asset_id}, clock())
                a['revision'] += 1
                a['updatedAt'] = clock()
                store.save(db, a)
                if legacy_audio:
                    return JSONResponse({'code': 'legacy-audio-unverified', 'error': 'This older session has no saved audio verification. Recover verified audio to continue without changing your saved answers or progress.'}, status_code=409)
                return JSONResponse({'code': 'source-changed', 'error': 'This media/source asset no longer matches the session snapshot. The original answers and deadline are preserved; restore the source or start a reimported practice.'}, status_code=409)
            mime = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
            if mime in ['text/html', 'image/svg+xml', 'text/javascript', 'application/javascript']:
                mime = 'application/octet-stream'
            return FileResponse(path, media_type=mime)

    @app.get('/api/sessions/{session_id}/assets/{asset_id}')
    def session_asset(session_id: str, asset_id: str):
        return serve_session_asset(session_id, asset_id)

    @app.get('/api/sessions/{session_id}/review-assets/{asset_id}')
    def review_asset(session_id: str, asset_id: str):
        return serve_session_asset(session_id, asset_id, review=True)

    @app.post('/api/sessions/{session_id}/recordings/{question_id}')
    async def save_segment(session_id: str, question_id: str, request: Request, segmentId: str, takeId: str, index: int):
        segment_id, take_id, qid = valid_id(segmentId), valid_id(takeId), valid_id(question_id)
        if not 0 <= index < 10000:
            raise engine.ExamError('Invalid recording segment index.', 422)
        mime = request.headers.get('content-type', '').split(';')[0].strip().lower()
        if mime not in AUDIO:
            raise engine.ExamError('Use a supported audio Content-Type.', 415)
        body = await read_body(request, 8 * 1024 * 1024)
        if not body:
            raise engine.ExamError('The recording segment is empty.', 422)
        digest = hashlib.sha256(body).hexdigest()
        with store.transaction() as db:
            a = get_session(db, session_id)
            if qid not in a['visitedSpeaking']:
                raise engine.ExamError('Recording uploads are limited to speaking questions already visited in this session.', 403)
            finalized = db.execute('SELECT * FROM recording_takes WHERE session_id=? AND take_id=?', (session_id, take_id)).fetchone()
            if finalized and (finalized['question_id'] != qid or index >= finalized['expected_count'] or (finalized['mime_type'] and finalized['mime_type'] != mime)):
                raise engine.ExamError('This segment is outside the finalized take definition.')
            existing = db.execute('SELECT * FROM recordings WHERE id=? OR (session_id=? AND take_id=? AND chunk_index=?)',
                                  (segment_id, session_id, take_id, index)).fetchone()
            if existing:
                if any([existing['id'] != segment_id, existing['session_id'] != session_id, existing['question_id'] != qid,
                        existing['take_id'] != take_id, existing['sha256'] != digest, existing['mime_type'] != mime]):
                    raise engine.ExamError('This recording segment identity already contains different data.')
            else:
                prior = db.execute('SELECT question_id,mime_type FROM recordings WHERE session_id=? AND take_id=? LIMIT 1', (session_id, take_id)).fetchone()
                if prior and (prior['question_id'] != qid or prior['mime_type'] != mime):
                    raise engine.ExamError('A take must use one question and one audio format.')
                directory = store.directory / 'segments'
                directory.mkdir(mode=0o700, exist_ok=True)
                if directory.is_symlink() or not directory.resolve().is_relative_to(store.directory.resolve()):
                    raise engine.ExamError('Recording storage is not accessible.', 403)
                filename = directory / f'{segment_id}.bin'
                if filename.is_symlink() or (filename.exists() and hashlib.sha256(filename.read_bytes()).hexdigest() != digest):
                    raise engine.ExamError('This recording segment filename already contains different data.')
                temp = directory / f'.{uuid.uuid4()}.tmp'
                try:
                    with temp.open('xb') as output:
                        output.write(body)
                        output.flush()
                        os.fsync(output.fileno())
                    # An identical orphan file can remain after a database/full-disk
                    # failure. Adopt it on retry; never overwrite different bytes.
                    if not filename.exists():
                        os.replace(temp, filename)
                    db.execute('INSERT INTO recordings VALUES(?,?,?,?,?,?,?,?,?,?)',
                               (segment_id, session_id, qid, take_id, index, f'segments/{segment_id}.bin', digest, mime, len(body), clock()))
                finally:
                    temp.unlink(missing_ok=True)
            url = f'/api/sessions/{session_id}/recordings/takes/{take_id}'
            return {'id': segment_id, 'takeId': take_id, 'index': index, 'questionId': qid,
                    'url': url, 'recordingUrl': url, 'mimeType': mime, 'size': len(body)}

    @app.post('/api/sessions/{session_id}/recordings/takes/{take_id}/finalize')
    async def finalize_take(session_id: str, take_id: str, request: Request):
        take_id = valid_id(take_id)
        payload = await read_json(request)
        qid, count = valid_id(payload.get('questionId')), payload.get('segmentCount')
        reason = payload.get('endedReason', 'stopped')
        mime = payload.get('mimeType')
        if mime is not None:
            if not isinstance(mime, str):
                raise engine.ExamError('Invalid audio MIME type.', 422)
            mime = mime.split(';')[0].strip().lower()
            if mime not in AUDIO:
                raise engine.ExamError('Use a supported audio MIME type.', 415)
        if type(count) is not int or not 0 <= count <= 10000 or not isinstance(reason, str) or not reason or len(reason) > 80:
            raise engine.ExamError('Use a valid expected segment count and a short recording end reason.', 422)
        with store.transaction() as db:
            a = get_session(db, session_id)
            if qid not in a['visitedSpeaking']:
                raise engine.ExamError('Only an already visited speaking question can finalize a recording.', 403)
            now = clock()
            engine.tick(a, now)
            prior = db.execute('SELECT * FROM recording_takes WHERE session_id=? AND take_id=?', (session_id, take_id)).fetchone()
            if prior:
                if prior['question_id'] != qid or prior['expected_count'] != count or prior['ended_reason'] != reason or (mime and prior['mime_type'] and mime != prior['mime_type']):
                    raise engine.ExamError('This take was already finalized with different metadata.')
            else:
                parts = db.execute('SELECT question_id,mime_type,chunk_index FROM recordings WHERE session_id=? AND take_id=?', (session_id, take_id)).fetchall()
                if any(part['question_id'] != qid or part['chunk_index'] >= count or (mime and mime != part['mime_type']) for part in parts):
                    raise engine.ExamError('Final metadata does not match the already saved recording chunks.')
                mime = mime or (parts[0]['mime_type'] if parts else None)
                db.execute('INSERT INTO recording_takes VALUES(?,?,?,?,?,?,?)', (session_id, take_id, qid, count, reason, mime, now))
                engine.log(a, 'recording-finalized', {'questionId': qid, 'takeId': take_id, 'segmentCount': count, 'endedReason': reason}, now)
                if reason in ['error', 'interrupted', 'microphone-error', 'stream-ended'] or (a['mode'] == 'strict' and reason == 'stopped-early'):
                    a['interrupted'] = True
                    engine.log(a, 'recording-error', {'questionId': qid, 'takeId': take_id, 'endedReason': reason}, now)
                a['revision'] += 1
                a['updatedAt'] = now
            store.save(db, a)
            groups = recordings(db, a)
            take = next(take for take in groups[qid] if take['takeId'] == take_id)
            return {'take': take, 'recordingIntegrity': recording_integrity(a, groups)}

    @app.get('/api/sessions/{session_id}/recordings/takes/{take_id}')
    def play_take(session_id: str, take_id: str, request: Request):
        with store.transaction() as db:
            reject_during_strict(db)
            a = get_session(db, session_id)
            if a['status'] == 'active' and a['mode'] == 'strict':
                raise engine.ExamError('Recording playback is locked during strict practice.', 403)
            rows = db.execute('SELECT * FROM recordings WHERE session_id=? AND take_id=? ORDER BY chunk_index',
                              (session_id, valid_id(take_id))).fetchall()
            final = db.execute('SELECT * FROM recording_takes WHERE session_id=? AND take_id=?', (session_id, take_id)).fetchone()
            if not rows:
                raise engine.ExamError('Recording not found.', 404)
            if [row['chunk_index'] for row in rows] != list(range(len(rows))):
                raise engine.ExamError('Some recording chunks have not arrived yet. Retry pending uploads before playback.')
            paths = []
            for row in rows:
                path = (store.directory / row['relative_path']).resolve()
                if not path.is_relative_to(store.directory.resolve()) or not path.is_file():
                    raise engine.ExamError('A recording chunk is unavailable.', 404)
                paths.append((path, row['size']))
        indexed = indexed_take(store.directory, take_id, rows, final)
        extension = {'audio/webm': '.webm', 'audio/mp4': '.m4a', 'audio/ogg': '.ogg', 'audio/wav': '.wav', 'audio/x-wav': '.wav', 'audio/mpeg': '.mp3', 'audio/aac': '.aac'}.get(rows[0]['mime_type'], '.audio')
        if indexed:
            return FileResponse(indexed['path'], media_type=rows[0]['mime_type'],
                headers={'X-Recording-Container': 'lossless-remux', 'X-Recording-Duration': str(indexed['durationSeconds']),
                         'Content-Disposition': f'inline; filename="{take_id}{extension}"'})
        total = sum(size for _, size in paths)
        start, end, status = 0, total - 1, 200
        headers = {'Accept-Ranges': 'bytes', 'X-Recording-Container': 'raw-unverified',
                   'Content-Disposition': f'inline; filename="{take_id}{extension}"'}
        range_header = request.headers.get('range')
        if range_header:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', range_header)
            if not match or (not match[1] and not match[2]):
                return JSONResponse({'error': 'Invalid byte range.'}, status_code=416, headers={'Content-Range': f'bytes */{total}'})
            if not match[1]:
                suffix = int(match[2]); start = max(0, total - suffix)
                if suffix == 0:
                    start = total
            else:
                start = int(match[1]); end = min(total - 1, int(match[2])) if match[2] else total - 1
            if start >= total or end < start:
                return JSONResponse({'error': 'Unsatisfiable byte range.'}, status_code=416, headers={'Content-Range': f'bytes */{total}'})
            status = 206
            headers['Content-Range'] = f'bytes {start}-{end}/{total}'
        headers['Content-Length'] = str(end - start + 1)

        def stream():
            offset = 0
            for path, size in paths:
                local_start, local_end = max(0, start - offset), min(size - 1, end - offset)
                if local_start <= local_end:
                    with path.open('rb') as source:
                        source.seek(local_start)
                        remaining = local_end - local_start + 1
                        while remaining:
                            chunk = source.read(min(65536, remaining))
                            if not chunk:
                                break
                            remaining -= len(chunk)
                            yield chunk
                offset += size
                if offset > end:
                    break
        return StreamingResponse(stream(), status_code=status, media_type=rows[0]['mime_type'], headers=headers)

    @app.get('/{resource:path}')
    def frontend(resource: str):
        if resource.startswith(('api/', 'materials/', 'generated/', 'storage/')):
            raise engine.ExamError('Resource not found.', 404)
        base = root / 'dist'
        target = (base / (resource or 'index.html')).resolve()
        if not target.is_relative_to(base.resolve()) or not base.resolve().is_relative_to(root):
            raise engine.ExamError('Resource not found.', 404)
        if target.is_file():
            return FileResponse(target)
        index = base / 'index.html'
        if resource and '.' not in Path(resource).name and index.is_file():
            return FileResponse(index)
        raise engine.ExamError('The frontend is not built. Run npm run build, or use the Vite development server.', 404)

    return app
