"""Source-ordered specialist groups built before search, filtering and paging."""
from collections import Counter
import hashlib
import json

from . import engine
from .mistakes import question_version


PUBLIC_FIELDS = ('groupId', 'examId', 'examTitle', 'section', 'moduleId', 'module', 'route', 'taskType',
                 'questionIds', 'numberStart', 'numberEnd', 'screenCount', 'itemCount', 'sourceScreenCount',
                 'unavailableCount', 'completedCount', 'status', 'hasAudio', 'audioCount', 'duplicateCount',
                 'groupContentId', 'sourcePages')
SESSION_FIELDS = ('groupId', 'groupContentId', 'moduleId', 'module', 'taskType', 'numberStart', 'numberEnd',
                  'screenCount', 'itemCount', 'sourceScreenCount', 'unavailableCount')


def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def question_content_id(question):
    """Use the same content identity as the existing individual-question API."""
    content_id = question.get('contentId') or question.get('canonicalId')
    if content_id:
        return content_id
    identity = {key: question.get(key) for key in ['type', 'prompt', 'passage', 'choices', 'tokens', 'transcript']}
    identity['blanks'] = [{key: blank.get(key) for key in ['prefix', 'length']} for blank in question.get('blanks', [])]
    if not question.get('transcript'):
        identity['media'] = [media.get('url') for media in engine.media_sequence(question)]
    # Preserve the individual endpoint's existing JSON spacing/ASCII defaults.
    return 'content-' + hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]


def _progress(sessions):
    result = {}
    for session in sessions:
        visited = set(session.get('visitedQuestions') or [])
        status = session.get('status')
        if status not in ['active', 'completed', 'abandoned']:
            continue
        for stage in session.get('plan', []):
            for question in stage.get('questions', []):
                # Merely belonging to an old selected plan does not constitute
                # having practiced this question or its current source version.
                if question['id'] not in visited or not question.get('contentId'):
                    continue
                key = (session['examId'], stage['section'], question['id'], question['contentId'], question_version(question))
                state = 'completed' if status in ['completed', 'abandoned'] else 'in_progress'
                if result.get(key) != 'completed':
                    result[key] = state
    return result


def _media(items):
    if isinstance(items, dict):
        return [items]
    return items if isinstance(items, list) else []


def _untimed_group(exam, section, module, members):
    """Match make_plan's practice-only timing classification for this subset."""
    reference_only = (module.get('referenceOnly') or section.get('referenceOnly')
                      or any(question.get('referenceOnly') or question.get('type') == 'source_page' for question in members))
    lacks_item_audio = (section['id'] in ['listening', 'speaking']
                        and any(not question.get('audio') and not question.get('mediaSequence') for question in members))
    return (exam.get('timingPolicy') == 'untimed' or section.get('timingPolicy') == 'untimed'
            or module.get('timingPolicy') == 'untimed' or reference_only or lacks_item_audio)


def build_practice_groups(catalog, sessions=(), exam_id=None):
    progress = _progress(sessions)
    groups = []
    for exam in catalog.exams.values():
        if exam_id is not None and exam['id'] != exam_id:
            continue
        for section in exam.get('sections', []):
            for module in section.get('modules', []):
                runs = []
                for question in module.get('questions', []):
                    task = question.get('taskType') or question.get('type') or 'unknown'
                    if runs and runs[-1][0] == task:
                        runs[-1][1].append(question)
                    else:
                        runs.append((task, [question]))
                for task, source_members in runs:
                    members = [question for question in source_members if engine.question_available(question)]
                    if not members:
                        continue
                    ids = [question['id'] for question in members]
                    contents = [question_content_id(question) for question in members]
                    states = [progress.get((exam['id'], section['id'], question['id'], content, question_version(question)), 'not_started')
                              for question, content in zip(members, contents)]
                    complete = states.count('completed')
                    audio_urls = set()
                    for question in members:
                        for media in engine.media_sequence(question):
                            if media.get('url') and media.get('kind') not in ['directions', 'instructions']:
                                audio_urls.add(media['url'])
                    if _untimed_group(exam, section, module, members):
                        for media in _media(module.get('practiceAudio') or section.get('practiceAudio')):
                            if media.get('url') and media.get('kind') not in ['directions', 'instructions']:
                                audio_urls.add(media['url'])
                    source_pages = []
                    for question in members:
                        source = question.get('editionSource') or question.get('source') or {}
                        page = source.get('page')
                        if type(page) is int and page not in source_pages:
                            source_pages.append(page)
                    start = members[0].get('number')
                    end = members[-1].get('numberEnd') or members[-1].get('number')
                    group_id = 'practice-group-' + _hash([exam['id'], section['id'], module['id'], task, source_members[0]['id']])[:24]
                    group = {
                        'groupId': group_id,
                        'examId': exam['id'], 'examTitle': exam.get('title', exam['id']),
                        'section': section['id'], 'moduleId': module['id'], 'module': module.get('title', module['id']),
                        'route': module.get('route') or 'common', 'taskType': task, 'questionIds': ids,
                        'screenCount': len(members), 'sourceScreenCount': len(source_members),
                        'unavailableCount': len(source_members) - len(members),
                        'itemCount': sum(max(1, len(question.get('blanks') or []))
                                         if question.get('type') in ['cloze', 'complete_words'] else 1 for question in members),
                        'completedCount': complete,
                        'status': 'completed' if complete == len(members) else 'in_progress' if any(state != 'not_started' for state in states) else 'not_started',
                        'hasAudio': bool(audio_urls), 'audioCount': len(audio_urls),
                        'groupContentId': group_revision(group_id, members, catalog.exam_digests.get(exam['id'])),
                        '_dedupeKey': _hash({'taskType': task, 'contentIds': contents}),
                    }
                    if type(start) is int:
                        group['numberStart'] = start
                    if type(end) is int:
                        group['numberEnd'] = end
                    if source_pages:
                        group['sourcePages'] = source_pages
                    group['_searchText'] = ' '.join(str(value or '') for value in [
                        exam.get('title'), exam['id'], module.get('title'), module['id'], task,
                        *[question.get(key) for question in members for key in
                          ['id', 'number', 'numberEnd', 'title', 'passageTitle', 'topic', 'prompt', 'passage', 'passageText', 'passageTemplate']],
                    ]).casefold()
                    groups.append(group)
    duplicates = Counter(group['_dedupeKey'] for group in groups)
    for group in groups:
        group['duplicateCount'] = duplicates[group['_dedupeKey']]
    return groups


def group_revision(group_id, questions, exam_digest):
    # Content IDs identify duplicates, whereas corrected keys/source metadata
    # need a distinct revision even when that duplicate identity is retained.
    # Bind the imported exam too: module routes, instructions and shared audio
    # can change without modifying any individual member's question metadata.
    return 'group-content-' + _hash({'groupId': group_id, 'examSha256': exam_digest,
                                    'questions': [[question['id'], question_version(question)] for question in questions]})


def public_group(group):
    return {key: group[key] for key in PUBLIC_FIELDS if key in group}


def group_session_options(catalog, exam, payload):
    if payload.get('mode', 'practice') != 'practice' or payload.get('routeMode', 'fixed') != 'fixed':
        raise engine.ExamError('Practice groups require practice mode and a fixed source route.', 422)
    if any(key in payload for key in ['questionIds', 'taskType', 'types', 'questionTypes']):
        raise engine.ExamError('Choose a practice group or individual question filters, not both.', 422)
    group = next((group for group in build_practice_groups(catalog, exam_id=exam['id'])
                  if group['groupId'] == payload['practiceGroupId']), None)
    if group is None:
        raise engine.ExamError('This practice group is no longer available for this source exam. Refresh the practice library.', 409)
    if payload.get('scope', 'all') not in ['all', group['section']]:
        raise engine.ExamError('The selected practice group belongs to a different section.', 422)
    expected = payload.get('expectedGroupContentId')
    if expected is not None and expected != group['groupContentId']:
        raise engine.ExamError('This practice group changed after it was listed. Refresh the practice library before starting.', 409)
    options = {**payload, 'mode': 'practice', 'scope': group['section'], 'routeMode': 'fixed',
               'route': group['route'] if group['route'] in ['upper', 'lower'] else 'upper',
               'questionIds': group['questionIds']}
    return options, {key: group[key] for key in SESSION_FIELDS if key in group}
