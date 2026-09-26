"""Server-authoritative exam state transitions; no network or browser clock."""
from copy import deepcopy
import math
import re
import unicodedata
import uuid

from .presentation import is_interactive as presentation_is_interactive, validate_question as validate_presentation

ORDER = ['reading', 'listening', 'writing', 'speaking']
RULES_VERSION = '2026-09-26-timing-scope-v6'
SCORING_ENGINE_VERSION = '2026-09-05-objective-snapshot-v1'
DEFAULT_TIMING = {'readingCommon': 690, 'readingSecond': 540, 'listeningResponse': 20, 'listeningAcademic': 30,
                  'buildSentence': 360, 'email': 420, 'academicDiscussion': 600,
                  'repeat': [8, 8, 10, 10, 10, 12, 12], 'interview': 45}
SUBJECTIVE = {'email', 'academic_discussion', 'listen_repeat', 'interview', 'read_aloud', 'picture_writing'}


class ExamError(Exception):
    def __init__(self, message, status=409):
        self.message, self.status = message, status
        super().__init__(message)


def normalize(value):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', str(value if value is not None else '')).strip().lower().replace('’', "'").replace('“', '"').replace('”', '"'))


def has_answer(value):
    if isinstance(value, dict):
        return any(has_answer(item) for item in value.values())
    if isinstance(value, list):
        return any(has_answer(item) for item in value)
    return bool(str(value if value is not None else '').strip())


def question_available(question):
    return (presentation_is_interactive(question) and question.get('sourcePromptAvailable') is not False
            and (not question.get('referenceOnly') or question.get('sourcePromptAvailable') is True))


def grade(question, answer):
    if question.get('subjective') is True or question.get('type') in SUBJECTIVE or question.get('_section') == 'speaking' or (question.get('_section') == 'writing' and question.get('type') != 'build_sentence'):
        return None
    if question.get('auditStatus') == 'answer-conflict' or (question.get('answerConflict') or {}).get('status') == 'needs-review':
        return None
    if question.get('type') in {'cloze', 'complete_words'}:
        blanks = [b for b in question.get('blanks', []) if (b.get('answer') is not None or b.get('fullWord') is not None)
                  and b.get('auditStatus') != 'answer-conflict' and (b.get('answerConflict') or {}).get('status') != 'needs-review']
        if not blanks:
            return None
        values = answer if isinstance(answer, dict) else {}
        correct = 0
        for blank in blanks:
            actual = normalize(values.get(blank['id'], ''))
            expected = normalize(blank.get('fullWord', blank.get('answer')))
            prefix = normalize(blank.get('prefix', ''))
            missing = normalize(blank.get('missingLetters', ''))
            accepted = {normalize(value) for value in blank.get('acceptedAnswers', [])}
            if actual and (actual == expected or actual in accepted or (prefix and prefix + actual == expected) or (missing and actual == missing)):
                correct += 1
        return {'correct': correct, 'total': len(blanks)}
    key = question.get('answer')
    accepted = list(key) if isinstance(key, list) else [key] if key is not None else []
    if isinstance(question.get('acceptedAnswers'), list):
        accepted.extend(question['acceptedAnswers'])
    accepted = [item for item in accepted if normalize(item)]
    if not accepted:
        return None
    if question.get('type') == 'build_sentence' and isinstance(answer, dict):
        indices = answer.get('tokenOrder', [])
        gaps = [slot for slot in question.get('slots', []) if 'fixed' not in slot]
        if not indices or any(value == '' for value in indices) or (gaps and len(indices) != len(gaps)):
            return {'correct': 0, 'total': 1}
        try:
            selected = iter(question.get('tokens', [])[int(index)] for index in indices)
            answer = ' '.join(str(slot['fixed']) if 'fixed' in slot else str(next(selected)) for slot in question['slots']) if question.get('slots') else ' '.join(selected)
            answer = re.sub(r'\s+([?.!,;:])', r'\1', answer)
        except (ValueError, IndexError, StopIteration):
            return {'correct': 0, 'total': 1}
    if isinstance(answer, list):
        answer = ' '.join(str(word) for word in answer)
    def normalized_result(value):
        text = normalize(value)
        if question.get('type') == 'build_sentence':
            text = re.sub(r'\s+([?.!,;:])', r'\1', text)
            text = re.sub(r'[.!?]+$', '', text).rstrip()
        return text
    return {'correct': int(any(normalized_result(answer) == normalized_result(item) for item in accepted)), 'total': 1}


def media_sequence(question):
    result = []
    directions = question.get('_moduleDirectionsAudio')
    if directions:
        result.extend({**item, 'kind': 'directions', 'scope': 'module-directions'} for item in (directions if isinstance(directions, list) else [directions]) if isinstance(item, dict))
    if question.get('mediaSequence'):
        result.extend(question['mediaSequence'])
        return [item for item in result if isinstance(item, dict) and item.get('url')]
    directions = question.get('directionsAudio')
    if directions:
        result.extend({**item, 'kind': 'directions'} for item in (directions if isinstance(directions, list) else [directions]) if isinstance(item, dict))
    if question.get('audio'):
        result.append(question['audio'])
    return [item for item in result if isinstance(item, dict) and item.get('url')]


def media_group(media):
    return str(media.get('groupId') or media.get('url'))


def timing_config(overrides):
    timing = deepcopy(DEFAULT_TIMING)
    if overrides is not None and not isinstance(overrides, dict):
        raise ExamError('Timing settings must be an object.', 422)
    for key, value in (overrides or {}).items():
        if key not in timing:
            raise ExamError(f'Unknown timing setting: {key}', 422)
        if key == 'repeat':
            if not isinstance(value, list) or len(value) != 7 or any(type(n) not in (int, float) or not math.isfinite(n) or not 1 <= n <= 7200 for n in value):
                raise ExamError('Repeat timing requires seven positive durations.', 422)
        elif type(value) not in (int, float) or not math.isfinite(value) or not 1 <= value <= 7200:
            raise ExamError('Timing values must be between 1 and 7200 seconds.', 422)
        timing[key] = value
    return timing


def make_plan(exam, options, timing):
    """Freeze requested source modules into ordered, independently timed stages.

    Reading/writing share a module deadline; listening/speaking use individual
    response windows after media. Supplemental packs always remain untimed.
    Canonical section and task IDs must stay language-independent.
    """
    scope, route_mode, route = options.get('scope', 'all'), options.get('routeMode', 'fixed'), options.get('route', 'upper')
    if scope not in ['all', *ORDER] or route_mode not in ['fixed', 'adaptive'] or route not in ['upper', 'lower']:
        raise ExamError('Invalid scope or route.', 422)
    plan = []
    types = options.get('types') or options.get('questionTypes') or ([options['taskType']] if options.get('taskType') else None)
    selected_ids = options.get('questionIds')
    if (types or selected_ids) and options.get('mode', 'practice') != 'practice':
        raise ExamError('Question-type and error-review filters are only available in practice mode.', 422)
    if selected_ids is not None:
        known = {q['id'] for s in exam.get('sections', []) for m in s.get('modules', []) for q in m.get('questions', [])}
        if not isinstance(selected_ids, list) or not selected_ids or not all(isinstance(item, str) and item in known for item in selected_ids):
            raise ExamError('Selected review questions must belong to this exam.', 422)
    for section_id in ORDER:
        if scope != 'all' and scope != section_id:
            continue
        section = next((s for s in exam.get('sections', []) if s['id'] == section_id), None)
        if not section:
            continue
        modules = section.get('modules', [])
        # Select the response window by the source position, before any task or
        # error-review filter. Practising sentence 7 alone must retain window 7.
        repeat_positions = {q['id']: i for i, q in enumerate(
            q for mod in modules for q in mod.get('questions', []) if q.get('type') == 'listen_repeat')}
        adaptive = route_mode == 'adaptive' and section_id in ['reading', 'listening']
        if adaptive:
            routes = {m.get('route', 'common') for m in modules}
            if not {'common', 'upper', 'lower'}.issubset(routes):
                raise ExamError('This exam has no complete matched lower/upper branches. Choose a fixed route.', 422)
            for mod in modules:
                if not mod.get('questions'):
                    raise ExamError('Adaptive routing requires complete branch questions.', 422)
                if mod.get('route', 'common') == 'common' and any(grade(q, None) is None for q in mod['questions']):
                    raise ExamError('Adaptive routing requires verified answers for every routing question.', 422)
        created = []
        for mi, mod in enumerate(modules):
            mod_route = mod.get('route', 'common')
            if not adaptive and mod_route not in ['common', route]:
                continue
            questions = deepcopy([q for q in mod.get('questions', []) if question_available(q) and (not types or q.get('type') in types or q.get('taskType') in types)
                                  and (not selected_ids or q['id'] in selected_ids)])
            chunks = []
            if section_id == 'writing':
                for question in questions:
                    if chunks and chunks[-1][0] == question['type']:
                        chunks[-1][1].append(question)
                    else:
                        chunks.append((question['type'], [question]))
            elif (section_id in ['listening', 'speaking'] and options.get('mode', 'practice') == 'practice'
                  and not any(level.get('timingPolicy') == 'untimed' or level.get('referenceOnly') for level in [exam, section, mod])):
                # A source-study item must not remove the response timer (and
                # automatic playback) from neighbouring, fully matched items.
                for question in questions:
                    needs_study = bool(question.get('referenceOnly') or question.get('type') == 'source_page'
                                       or not (question.get('audio') or question.get('mediaSequence')))
                    if chunks and chunks[-1][0] == needs_study:
                        chunks[-1][1].append(question)
                    else:
                        chunks.append((needs_study, [question]))
            else:
                chunks = [(None, questions)]
            for chunk_index, (chunk_type, items) in enumerate(chunks):
                if not items:
                    continue
                reference_only = bool(mod.get('referenceOnly') or section.get('referenceOnly') or any(q.get('referenceOnly') or q.get('type') == 'source_page' for q in items))
                lacks_item_audio = section_id in ['listening', 'speaking'] and any(not q.get('audio') and not q.get('mediaSequence') for q in items)
                untimed = options.get('mode', 'practice') == 'practice' and (exam.get('timingPolicy') == 'untimed' or section.get('timingPolicy') == 'untimed' or mod.get('timingPolicy') == 'untimed' or reference_only or lacks_item_audio)
                practice_audio = mod.get('practiceAudio') or section.get('practiceAudio') or []
                if isinstance(practice_audio, dict):
                    practice_audio = [practice_audio]
                if mod.get('directionsAudio') and chunk_index == 0:
                    items[0]['_moduleDirectionsAudio'] = deepcopy(mod['directionsAudio'])
                for question in items:
                    question['_section'] = section_id
                    if section_id == 'speaking':
                        seconds = timing['interview'] if question['type'] == 'interview' else question.get('responseSeconds', timing['repeat'][min(repeat_positions.get(question['id'], 0), 6)])
                    else:
                        seconds = question.get('responseSeconds', timing['listeningAcademic'] if 'academic' in question.get('taskType', '').lower() else timing['listeningResponse'])
                    if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 < seconds <= 7200:
                        raise ExamError('A question has no valid verified or configured response duration.', 422)
                    if options.get('mode') == 'strict' and section_id == 'speaking' and question['type'] == 'listen_repeat' and not 8 <= seconds <= 12:
                        raise ExamError('Strict repeat response windows must remain within the verified 8–12 second range.', 422)
                    question['_responseSeconds'] = seconds
                seconds = mod.get('durationSeconds') or timing['readingCommon' if mi == 0 else 'readingSecond']
                if section_id == 'writing':
                    seconds = timing['email'] if chunk_type == 'email' else timing['academicDiscussion'] if chunk_type == 'academic_discussion' else timing['buildSentence']
                if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 < seconds <= 7200:
                    raise ExamError('A module has no valid verified or configured duration.', 422)
                timer = 'untimed' if untimed else 'shared' if section_id in ['reading', 'writing'] else 'item'
                official_seconds = {'email': 420, 'academic_discussion': 600, 'interview': 45}
                official = all(q.get('type') in official_seconds and
                               (seconds if timer == 'shared' else q['_responseSeconds']) == official_seconds[q['type']]
                               for q in items)
                timing_basis = 'untimed' if untimed else 'official' if official else 'source' if (
                    section_id == 'reading' and mod.get('durationSeconds')) else 'local'
                suffix = f'-{chunk_type}' if section_id == 'writing' else f'-part-{chunk_index + 1}' if chunk_index else ''
                created.append({'id': mod['id'] + suffix, 'section': section_id,
                                'title': mod.get('title', section_id.title()), 'route': mod_route,
                                'instructions': mod.get('instructions'), 'hasDirectionsAudio': bool(mod.get('directionsAudio')) and chunk_index == 0,
                                'timer': timer, 'timingBasis': timing_basis,
                                'responseWindows': [q['_responseSeconds'] for q in items] if timer == 'item' else [],
                                'partialModule': timer == 'shared' and len(items) < sum(
                                    section_id != 'writing' or q.get('type') == chunk_type for q in mod.get('questions', [])),
                                'practiceAudio': deepcopy(practice_audio) if untimed else [], 'referenceOnly': reference_only or lacks_item_audio,
                                'seconds': seconds, 'canBack': section_id == 'reading' or chunk_type == 'build_sentence', 'questions': items})
        if adaptive:
            common = [s for s in created if s['route'] == 'common']
            branches = {choice: [s for s in created if s['route'] == choice] for choice in ['upper', 'lower']}
            if not common or any(not branch for branch in branches.values()):
                raise ExamError('Filtering would make the adaptive branches incomplete.', 422)
            plan.extend(common)
            plan.append({'id': f'{section_id}-adaptive-pending', 'section': section_id, 'branches': branches, 'questions': []})
        else:
            plan.extend(created)
    if not plan:
        raise ExamError('No interactive questions are available for this selection.', 422)
    return plan


def practice_aids_enabled(session):
    """A saved opt-in and server-derived eligibility are both required.

    Old sessions have neither marker and remain off. Client event payloads
    cannot grant this permission after a session has started.
    """
    return (session.get('mode') == 'practice' and session.get('allowPracticeAids') is True
            and session.get('practiceAidsEligible') is True)


def _plan_question_ids(plan):
    result = set()
    for stage in plan:
        result.update((stage['section'], question['id']) for question in stage.get('questions', []))
        for branch in stage.get('branches', {}).values():
            result.update(_plan_question_ids(branch))
    return result


def new_session(exam, options, now):
    timing = timing_config(options.get('timing'))
    mode = options.get('mode', 'practice')
    if mode not in ['strict', 'practice']:
        raise ExamError('Choose strict or practice mode.', 422)
    allow_practice_aids = options.get('allowPracticeAids', False)
    if type(allow_practice_aids) is not bool:
        raise ExamError('allowPracticeAids must be a boolean.', 422)
    if exam.get('supplemental') and (mode != 'practice' or options.get('routeMode', 'fixed') != 'fixed'):
        raise ExamError('Supplementary materials use practice mode only; they are not TOEFL iBT 2026 mock exams.', 422)
    if mode == 'strict':
        timing.update(email=420, academicDiscussion=600, interview=45)
    if mode == 'strict' and not exam.get('strictEligible') and not exam.get('scopedEligibility', {}).get(options.get('scope', 'all')):
        raise ExamError('These materials have not passed strict-practice validation.', 422)
    selected_scope = options.get('scope', 'all')
    unavailable_source = any(not question_available(q) for s in exam.get('sections', [])
        if selected_scope == 'all' or s['id'] == selected_scope
        for m in s.get('modules', []) if options.get('routeMode') == 'adaptive' or m.get('route', 'common') in ['common', options.get('route', 'upper')]
        for q in m.get('questions', []))
    if mode == 'strict' and unavailable_source:
        raise ExamError('This source contains unavailable prompts; strict practice cannot silently omit them.', 422)
    plan = make_plan(exam, options, timing)
    for planned_stage in plan:
        candidates = [planned_stage] if not planned_stage.get('branches') else [
            item for branch in planned_stage['branches'].values() for item in branch
        ]
        for candidate in candidates:
            for planned_question in candidate.get('questions', []):
                presentation_issues = validate_presentation(planned_question, strict=mode == 'strict')
                if presentation_issues:
                    raise ExamError('A structured question presentation is not source-verified or valid: ' + ', '.join(presentation_issues), 422)
    filters = {key: options[key] for key in ['taskType', 'questionIds', 'types', 'questionTypes'] if options.get(key)}
    aids_eligible = mode == 'practice' and selected_scope != 'all'
    if mode == 'practice' and selected_scope == 'all' and filters:
        unfiltered_options = {key: value for key, value in options.items()
                              if key not in ['taskType', 'questionIds', 'types', 'questionTypes']}
        unfiltered_plan = make_plan(exam, unfiltered_options, timing)
        # A filter name is not proof of a subset: selecting every question or
        # every type must not turn a full exam into an assisted practice.
        aids_eligible = _plan_question_ids(plan) < _plan_question_ids(unfiltered_plan)
    if allow_practice_aids and not aids_eligible:
        raise ExamError('Replay and immediate feedback can only be enabled for specialized practice, not full exams or strict practice.', 422)
    full_scope = not filters and not unavailable_source and (options.get('scope', 'all') != 'all' or {s['section'] for s in plan} == set(ORDER))
    if mode == 'strict':
        for st in plan:
            branches = [st] if not st.get('branches') else [s for branch in st['branches'].values() for s in branch]
            for stage in branches:
                for q in stage['questions']:
                    has_stimulus = q.get('audio') or any(media.get('kind') not in ['directions', 'instructions'] for media in q.get('mediaSequence', []))
                    if stage['section'] in ['listening', 'speaking'] and not has_stimulus:
                        raise ExamError('Strict practice requires verified audio for every listening/speaking question.', 422)
                    if any(not isinstance(media.get('durationSeconds'), (int, float)) or not math.isfinite(media['durationSeconds']) or media['durationSeconds'] <= 0 for media in media_sequence(q)):
                        raise ExamError('Strict practice requires verified durations for all media segments.', 422)
                    if q.get('type') == 'source_page' or q.get('referenceOnly') or stage.get('referenceOnly'):
                        raise ExamError('Source-page placeholders cannot enter strict practice.', 422)
    return {'id': 'session-' + str(uuid.uuid4()), 'examId': exam['id'], 'title': exam.get('title', exam['id']),
            'mode': mode, 'scope': options.get('scope', 'all'), 'routeMode': options.get('routeMode', 'fixed'),
            'route': options.get('route', 'upper'), 'status': 'active', 'phase': 'directions', 'stageIndex': 0,
            'questionIndex': 0, 'deadline': None, 'mediaIndex': 0, 'audioEarliestEnd': None, 'revision': 1,
            'startedAt': now, 'updatedAt': now, 'plan': plan, 'answers': {}, 'flags': {}, 'playedGroups': [],
            'visitedSpeaking': [], 'visitedQuestions': [], 'events': [], 'interrupted': False, 'timing': timing,
            'rulesVersion': 'supplementary-untimed-v1' if exam.get('timingPolicy') == 'untimed' else RULES_VERSION,
            'scoringPolicy': {'verifiedAnswersRequiredForScoring': True, 'unresolvedAnswersExcludedFromScoring': True},
            'timingPolicy': exam.get('timingPolicy', 'configured'), 'adaptiveThreshold': .70, 'routes': {},
            'examWarnings': exam.get('warnings', []), 'pausedMilliseconds': 0, 'filters': filters,
            'isFullScope': full_scope, 'filtered': bool(filters), 'supplemental': bool(exam.get('supplemental')),
            'writingExpiryAcknowledgement': True, 'allowPracticeAids': allow_practice_aids,
            'practiceAidsEligible': aids_eligible}


def stage(a):
    return a['plan'][a['stageIndex']] if a['stageIndex'] < len(a['plan']) else None


def question(a):
    st = stage(a)
    return st['questions'][a['questionIndex']] if st and st['questions'] else None


def log(a, name, detail, now):
    a['events'].append({'type': name, 'detail': detail, 'at': now})


def current_media(a):
    items = media_sequence(question(a) or {})
    return items[a['mediaIndex']] if a.get('mediaIndex', 0) < len(items) else None


def enter_item(a, now, wall_now=None):
    st, q = stage(a), question(a)
    a['mediaIndex'] = 0
    a['audioEarliestEnd'] = None
    if q['id'] not in a['visitedQuestions']:
        a['visitedQuestions'].append(q['id'])
    if st['section'] == 'speaking' and q['id'] not in a['visitedSpeaking']:
        a['visitedSpeaking'].append(q['id'])
    if st['timer'] == 'untimed':
        a.update(phase='response', deadline=None)
        return
    if st['timer'] == 'shared':
        a['phase'] = 'response'
        return
    sequence = media_sequence(q)
    while a['mediaIndex'] < len(sequence) and media_group(sequence[a['mediaIndex']]) in a['playedGroups']:
        a['mediaIndex'] += 1
    if a['mediaIndex'] < len(sequence):
        a['phase'], a['deadline'] = 'audio', None
        duration = max(0, float(sequence[a['mediaIndex']].get('durationSeconds') or 0))
        a['audioEarliestEnd'] = (wall_now if wall_now is not None else now) + int(duration * 1000)
    else:
        a['phase'], a['deadline'] = 'response', now + int(q['_responseSeconds'] * 1000)
        if not sequence:
            log(a, 'missing-audio', q['id'], now)
            a['interrupted'] = True


def begin(a, now, wall_now=None):
    if a['status'] != 'active' or a['phase'] != 'directions':
        raise ExamError('The current stage has already begun.')
    a['questionIndex'] = 0
    if stage(a)['timer'] == 'shared':
        a['deadline'] = now + int(stage(a)['seconds'] * 1000)
    enter_item(a, now, wall_now)
    log(a, 'stage-start', stage(a)['id'], now)


def select_branch(a, now):
    pending = stage(a)
    if not pending or not pending.get('branches'):
        return
    correct = total = 0
    for prior in a['plan'][:a['stageIndex']]:
        if prior['section'] == pending['section'] and prior.get('route') == 'common':
            for q in prior['questions']:
                result = grade(q, a['answers'].get(q['id']))
                if result:
                    correct += result['correct']; total += result['total']
    route = 'upper' if total and correct / total >= a['adaptiveThreshold'] else 'lower'
    a['routes'][pending['section']] = route
    a['plan'][a['stageIndex']:a['stageIndex'] + 1] = deepcopy(pending['branches'][route])
    log(a, 'adaptive-route', {'section': pending['section'], 'route': route, 'rule': 'local-70-percent'}, now)


def advance_stage(a, now, reason='submitted', wall_now=None):
    old = stage(a)
    log(a, 'stage-end', {'id': old['id'], 'reason': reason}, now)
    a['stageIndex'] += 1
    a['questionIndex'], a['deadline'], a['audioEarliestEnd'] = 0, None, None
    if a['stageIndex'] >= len(a['plan']):
        a.update(status='completed', phase='complete', completedAt=now)
        freeze_score(a, wall_now if wall_now is not None else now)
        return
    select_branch(a, now)
    a['phase'] = 'directions'
    upcoming = stage(a)
    # Pack 1 source pages 18, 85 and 87 explicitly place a Begin screen
    # before the next Reading module / Writing task. Its response deadline
    # must start at Begin, never at the preceding task's submission/timeout.
    separate_begin = upcoming['section'] in ['reading', 'writing'] and upcoming['timer'] == 'shared'
    if upcoming['section'] == old['section'] and not separate_begin:
        begin(a, now, wall_now)


def next_item(a, now, reason='submitted', wall_now=None):
    if a['questionIndex'] + 1 >= len(stage(a)['questions']):
        advance_stage(a, now, reason, wall_now)
    else:
        a['questionIndex'] += 1
        enter_item(a, now, wall_now)


def tick(a, now):
    """Catch up elapsed deadlines before accepting a user event.

    The caller supplies milliseconds from the server clock. A stale browser
    answer can therefore never extend an expired response window.
    """
    changed = False
    while a['status'] == 'active' and a['phase'] == 'response' and a['deadline'] is not None and now >= a['deadline']:
        expired = a['deadline']
        log(a, 'timeout', question(a)['id'], expired)
        if (a.get('writingExpiryAcknowledgement') is True and stage(a)['section'] == 'writing'
                and question(a)['type'] in ['email', 'academic_discussion']):
            # The accepted response is already persisted in answers. Keep its
            # original deadline and source question while the UI acknowledges
            # expiry; no editing or navigation may reopen this response.
            a['phase'] = 'expired'
        elif stage(a)['timer'] == 'shared':
            advance_stage(a, expired, 'timeout', now)
        else:
            next_item(a, expired, 'timeout', now)
        changed = True
    if changed:
        a['updatedAt'] = now
        a['revision'] += 1
    return changed


def apply_event(a, payload, now):
    action = payload.get('action')
    if action == 'interrupt':
        a['interrupted'] = True
        log(a, 'interrupted', payload.get('details', payload.get('detail', payload.get('reason', 'client interruption'))), now)
        a['revision'] += 1
        a['updatedAt'] = now
        return
    if a['status'] != 'active':
        raise ExamError('This session has ended.')
    q, st = question(a), stage(a)
    if a['phase'] == 'expired' and action not in ['continue', 'finish']:
        raise ExamError('The writing response time has ended. Select Continue to leave this question.')
    if action in ['answer', 'next', 'back', 'jump', 'continue', 'audio-ended', 'audio-started', 'flag', 'replay', 'skip-audio']:
        if not payload.get('questionId') or payload['questionId'] != q['id']:
            raise ExamError('The displayed question is no longer current. Your expired answer was not submitted.')
    if action == 'begin':
        begin(a, now)
    elif action == 'continue':
        if a['phase'] != 'expired':
            raise ExamError('Continue is only available after the writing response time has ended.')
        advance_stage(a, now, 'timeout')
    elif action == 'answer':
        if a['phase'] != 'response':
            raise ExamError('Answers are accepted only during the response window.')
        answer = payload.get('answer', payload.get('value'))
        if not isinstance(answer, (str, dict, list, int, float)) and answer is not None:
            raise ExamError('Invalid answer format.', 422)
        if q.get('choices') and answer is not None and answer not in [c['id'] for c in q['choices']]:
            raise ExamError('Choose one of the current question options.', 422)
        if q.get('blanks') and answer is not None:
            if not isinstance(answer, dict) or not set(answer).issubset({b['id'] for b in q['blanks']}):
                raise ExamError('Unknown cloze blank.', 422)
        if q.get('type') == 'build_sentence' and isinstance(answer, dict):
            indices = answer.get('tokenOrder')
            tokens = q.get('tokens', [])
            if not isinstance(indices, list) or any(not isinstance(index, str) or (index != '' and (not index.isascii() or not index.isdigit() or index != str(int(index)) or not 0 <= int(index) < len(tokens))) for index in indices):
                raise ExamError('Invalid sentence token index.', 422)
            selected = [index for index in indices if index != '']
            if len(set(selected)) != len(selected):
                raise ExamError('Each individual word-bank token can be used only once.', 422)
            gaps = sum('fixed' not in slot for slot in q.get('slots', []))
            if gaps and len(indices) != gaps:
                raise ExamError('Provide one token position per sentence gap.', 422)
        a['answers'][q['id']] = answer
    elif action in ['next', 'back', 'jump']:
        if a['phase'] != 'response':
            raise ExamError('Navigation is unavailable in this phase.')
        if action == 'next':
            if st['section'] == 'speaking' and a['mode'] == 'strict':
                raise ExamError('Speaking responses submit automatically when the recording window ends.')
            if st['section'] == 'listening' and st['timer'] != 'untimed' and not has_answer(a['answers'].get(q['id'])):
                raise ExamError('You must answer this question before selecting Next.')
            next_item(a, now)
        else:
            if not st['canBack']:
                raise ExamError('You cannot return to an earlier question in this task.')
            index = a['questionIndex'] - 1 if action == 'back' else payload.get('index')
            if type(index) is not int or not 0 <= index < len(st['questions']):
                raise ExamError('You can only navigate inside the current module.')
            a['questionIndex'] = index
            current_id = question(a)['id']
            if current_id not in a['visitedQuestions']:
                a['visitedQuestions'].append(current_id)
    elif action == 'flag':
        if a['phase'] != 'response' or not st['canBack']:
            raise ExamError('This question cannot be flagged now.')
        a['flags'][q['id']] = not a['flags'].get(q['id'], False)
    elif action in ['audio-ended', 'skip-audio']:
        if a['phase'] != 'audio':
            raise ExamError('No prompt is currently playing.')
        if action == 'skip-audio' and a['mode'] != 'practice':
            raise ExamError('Strict practice does not allow skipping a prompt.')
        sequence = media_sequence(q)
        if len(sequence) > 1 and payload.get('mediaIndex') != a['mediaIndex']:
            raise ExamError('This ended event belongs to a different media segment.')
        if action != 'skip-audio' and now + 250 < (a.get('audioEarliestEnd') or 0):
            raise ExamError('The current media segment has not finished its playback window.')
        a['playedGroups'].append(media_group(current_media(a)))
        a['mediaIndex'] += 1
        while a['mediaIndex'] < len(sequence) and media_group(sequence[a['mediaIndex']]) in a['playedGroups']:
            a['mediaIndex'] += 1
        if a['mediaIndex'] < len(sequence):
            a['audioEarliestEnd'] = now + int(float(current_media(a).get('durationSeconds') or 0) * 1000)
        else:
            a.update(phase='response', deadline=now + int(q['_responseSeconds'] * 1000), audioEarliestEnd=None)
        log(a, action, q['id'], now)
    elif action == 'audio-started':
        if a['phase'] != 'audio':
            raise ExamError('No current audio segment.')
        if len(media_sequence(q)) > 1 and payload.get('mediaIndex') != a['mediaIndex']:
            raise ExamError('This playing event belongs to a different media segment.')
        # This event may report loading latency, but cannot shorten the floor.
        floor = now + int(float(current_media(a).get('durationSeconds') or 0) * 1000)
        a['audioEarliestEnd'] = max(a.get('audioEarliestEnd') or 0, floor)
    elif action == 'pause':
        if a['mode'] != 'practice' or a['phase'] == 'paused':
            raise ExamError('Pause is only available in practice mode.')
        if a['phase'] == 'audio' and not practice_aids_enabled(a):
            raise ExamError('Pausing audio requires practice aids enabled before starting.')
        a['pausedState'] = {'phase': a['phase'], 'pausedAt': now, 'remaining': max(0, a['deadline'] - now) if a['deadline'] else None,
                            'audioRemaining': max(0, a['audioEarliestEnd'] - now) if a['audioEarliestEnd'] else None}
        a.update(phase='paused', deadline=None, audioEarliestEnd=None)
        log(a, 'paused', q['id'], now)
    elif action == 'resume':
        if a['phase'] == 'paused':
            prior = a.pop('pausedState')
            a['pausedMilliseconds'] += now - prior['pausedAt']
            a['phase'] = prior['phase']
            a['deadline'] = now + prior['remaining'] if prior['remaining'] is not None else None
            a['audioEarliestEnd'] = now + prior['audioRemaining'] if prior['audioRemaining'] is not None else None
        else:
            a['interrupted'] = True
        log(a, 'resumed', q['id'], now)
    elif action == 'replay':
        if not practice_aids_enabled(a):
            raise ExamError('Replay, immediate feedback and review resources were not enabled for this practice session.')
        if a['mode'] != 'practice' or not media_sequence(q):
            raise ExamError('Replay is only available in practice mode.')
        if st['timer'] == 'untimed':
            raise ExamError('Use the manual reference-audio player for untimed practice.')
        a['playedGroups'] = [g for g in a['playedGroups'] if g not in {media_group(m) for m in media_sequence(q)}]
        enter_item(a, now)
        log(a, 'practice-replay', q['id'], now)
    elif action == 'finish':
        if a.get('pausedState'):
            a['pausedMilliseconds'] += now - a['pausedState']['pausedAt']
        a.update(status='abandoned', phase='complete', deadline=None, completedAt=now)
        a['interrupted'] = True
        log(a, 'finished-early', payload.get('reason', 'Ended by user'), now)
        freeze_score(a, now)
    else:
        raise ExamError('Unknown session action.', 422)
    a['revision'] += 1
    a['updatedAt'] = now


def calculate_score(a):
    """Calculate raw objective results; use score() when reading saved history."""
    by_section = {}
    items = {}
    correct = total = ungraded = 0
    for st in a['plan']:
        for q in st.get('questions', []):
            result = grade({**q, '_section': st['section']}, a['answers'].get(q['id']))
            part = by_section.setdefault(st['section'], {'correct': 0, 'total': 0})
            if result:
                items[q['id']] = result
                correct += result['correct']; total += result['total']
                part['correct'] += result['correct']; part['total'] += result['total']
            else:
                ungraded += 1
    wall_seconds = max(0, ((a.get('completedAt') or a['updatedAt']) - a['startedAt']) / 1000)
    return {'correct': correct, 'total': total, 'accuracy': correct / total if total else None,
            'ungraded': ungraded, 'sections': by_section, 'items': items,
            'attemptedCount': sum(has_answer(value) for value in a['answers'].values()),
            'elapsedSeconds': wall_seconds, 'wallSeconds': wall_seconds,
            'durationSeconds': max(0, wall_seconds - a.get('pausedMilliseconds', 0) / 1000),
            'notice': 'Raw practice results only. Not an ETS score or a calibrated 1–6 / 120 score.'}


def frozen_score(a):
    snapshot = a.get('scoreSnapshot')
    return snapshot['score'] if isinstance(snapshot, dict) and isinstance(snapshot.get('score'), dict) else None


def freeze_score(a, now):
    """Store objective results once so later imports cannot rewrite history."""
    """Persist once at the active-to-ended transition, never on a history read."""
    if a['status'] not in ['completed', 'abandoned'] or frozen_score(a) is not None:
        return
    a['scoreSnapshot'] = {'schemaVersion': 1, 'calculatedAt': now,
                          'engineVersion': SCORING_ENGINE_VERSION, 'score': calculate_score(a)}


def score_snapshot_metadata(a):
    snapshot = a.get('scoreSnapshot')
    if frozen_score(a) is not None:
        return {'scoreSnapshotStatus': 'frozen', 'scoreSnapshotCalculatedAt': snapshot.get('calculatedAt'),
                'scoringEngineVersion': snapshot.get('engineVersion')}
    return {'scoreSnapshotStatus': 'pending' if a.get('status') == 'active' else 'legacy-recomputed',
            'scoreSnapshotCalculatedAt': None, 'scoringEngineVersion': SCORING_ENGINE_VERSION}


def score(a):
    saved = frozen_score(a)
    if saved is not None:
        # Recording arrival may augment the response's attemptedCount. Callers
        # must never mutate the original objective result saved at submission.
        return deepcopy(saved)
    result = calculate_score(a)
    if a.get('status') != 'active':
        result['notice'] += ' Legacy session: no objective score snapshot was saved; this result is recalculated using the current grading engine.'
    return result


def session_grade(a, q, section=None):
    saved = frozen_score(a)
    if saved is not None:
        # A missing key means ungraded at submission; a future grader must not
        # silently turn that historical question into an objective result.
        return deepcopy(saved.get('items', {}).get(q['id']))
    original = {**q, '_section': section} if section is not None else q
    return grade(original, a['answers'].get(q['id']))
