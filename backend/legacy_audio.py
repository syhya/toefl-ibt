"""Explicit, narrowly scoped audio binding for pre-snapshot listening practice.

This records what was verified now. It never creates a historical source or
scoring snapshot and never changes the session's frozen questions or progress.
"""
import hashlib
import json
import math

from . import engine
from .integrity import HASH


QUESTION_FIELDS = ('id', 'type', 'taskType', 'prompt', 'choices', 'answer', 'acceptedAnswers',
                   'transcript', 'context', 'passage', 'passageTemplate', 'blanks', 'tokens', 'slots', 'subjective')
MEDIA_FIELDS = ('url', 'durationSeconds', 'groupId', 'kind', 'scope', 'mediaType')


def _question_signature(question):
    return {**{key: question.get(key) for key in QUESTION_FIELDS},
            'media': [{key: media.get(key) for key in MEDIA_FIELDS} for media in engine.media_sequence(question)]}


def _has_conflict(question):
    return (question.get('auditStatus') == 'answer-conflict'
            or (question.get('answerConflict') or {}).get('status') == 'needs-review')


def recovery_candidate(session, catalog, integrity):
    """Return a verified current manifest only when every frozen item agrees."""
    plan = session.get('plan')
    if (session.get('mode') != 'practice' or session.get('status') != 'active'
            or session.get('verificationSnapshot') or session.get('assetManifest')
            or session.get('reviewAssetManifest') or not isinstance(plan, list) or not plan):
        return None
    if any(stage.get('section') != 'listening' or stage.get('branches')
           or stage.get('directionsAudio') or stage.get('practiceAudio') or not stage.get('questions') for stage in plan):
        return None
    exam = catalog.exams.get(session.get('examId'))
    if not exam:
        return None
    current = {}
    for section in exam.get('sections', []):
        if section.get('id') != 'listening':
            continue
        for module in section.get('modules', []):
            if module.get('branches') or module.get('directionsAudio') or module.get('practiceAudio'):
                return None
            for question in module.get('questions', []):
                if question['id'] in current:
                    return None
                current[question['id']] = question
    manifest, signatures, seen = {}, [], set()
    for stage in plan:
        for frozen in stage['questions']:
            question_id = frozen.get('id')
            question = current.get(question_id)
            if (question is None or question_id in seen or _has_conflict(frozen) or _has_conflict(question)
                    or not engine.question_available(question)):
                return None
            seen.add(question_id)
            signature = _question_signature(frozen)
            if signature != _question_signature(question):
                return None
            signatures.append(signature)
            media_items = engine.media_sequence(frozen)
            if not media_items:
                return None
            for media in media_items:
                duration = media.get('durationSeconds')
                if (isinstance(duration, bool) or not isinstance(duration, (int, float))
                        or not math.isfinite(duration) or duration <= 0):
                    return None
                url = media.get('url')
                asset_id = catalog.register(url)
                path = catalog.path_for(asset_id) if asset_id else None
                expected = integrity.expected_for_url(exam, url)
                if (not path or not isinstance(expected, str) or not HASH.fullmatch(expected)
                        or integrity.digest(path) != expected):
                    return None
                # A recovery must never supersede an actual historical hash,
                # even if another legacy clip is missing its own expectation.
                previous = integrity.historical_media_hash(session, asset_id)
                supplied_hash = media.get('sourceSha256')
                if ((previous is not None and previous != expected)
                        or (supplied_hash is not None and supplied_hash != expected)):
                    return None
                manifest[asset_id] = {'url': url, 'sha256': expected}
    if not manifest or integrity.check_exam(exam)['status'] != 'passed':
        return None
    encoded = json.dumps(signatures, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    signature_hash = hashlib.sha256(encoded.encode()).hexdigest()
    saved = session.get('legacyAudioManifest')
    audit = session.get('legacyAudioRecovery') or {}
    if saved and (saved != manifest or audit.get('schemaVersion') != 1
                  or audit.get('questionSignature') != signature_hash):
        return None
    return {'manifest': manifest, 'questionSignature': signature_hash,
            'questionIds': [question['id'] for stage in plan for question in stage['questions']],
            'examSha256': catalog.exam_digests.get(exam['id']), 'applied': bool(saved)}


def recovery_flags(session, catalog, integrity):
    candidate = recovery_candidate(session, catalog, integrity)
    return {'canRecoverAudio': bool(candidate and not candidate['applied']),
            'audioRecoveryApplied': bool(candidate and candidate['applied'])}


def recover_audio(session, catalog, integrity, now):
    candidate = recovery_candidate(session, catalog, integrity)
    if candidate is None:
        raise engine.ExamError('This session cannot safely recover legacy audio. Keep its saved answers and start a new practice with verified sources.', 409)
    if candidate['applied']:
        return False
    session['legacyAudioManifest'] = candidate['manifest']
    session['legacyAudioRecovery'] = {'schemaVersion': 1, 'recoveredAt': now,
                                    'verification': 'current-audio-only-history-unverified',
                                    'examId': session['examId'], 'examSha256': candidate['examSha256'],
                                    'questionSignature': candidate['questionSignature'],
                                    'questionIds': candidate['questionIds']}
    session['interrupted'] = True
    engine.log(session, 'legacy-audio-recovered', {'assetCount': len(candidate['manifest']),
               'historicalSourcesVerified': False}, now)
    session['revision'] += 1
    session['updatedAt'] = now
    return True
