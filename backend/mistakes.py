"""Read-only objective mistake history derived from immutable session snapshots."""
import hashlib
import json

from . import engine


TASK_LABELS = {
    'cloze': 'Complete the Words', 'complete_words': 'Complete the Words',
    'daily_life': 'Read in Daily Life', 'academic_passage': 'Read an Academic Passage',
    'listen_response': 'Listen and Choose a Response', 'choose_response': 'Listen and Choose a Response',
    'conversation': 'Listen to a Conversation', 'announcement': 'Listen to an Announcement',
    'academic_talk': 'Listen to an Academic Talk', 'build_sentence': 'Build a Sentence',
    'choice': 'Multiple Choice',
}


def question_version(question):
    """Keep key corrections distinct even when a source contentId is unchanged."""
    keys = ['contentId', 'type', 'taskType', 'prompt', 'passage', 'passageTemplate', 'context',
            'choices', 'blanks', 'tokens', 'fixedTokens', 'slots', 'stemBlocks', 'assets',
            'audio', 'directionsAudio', 'mediaSequence', 'source', 'stimulusSource',
            'answer', 'acceptedAnswers', 'subjective', 'auditStatus', 'answerConflict']
    value = {key: question[key] for key in keys if key in question}
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def has_scorable_answer(question, answer):
    if not engine.has_answer(answer):
        return False
    if question.get('type') not in ['cloze', 'complete_words']:
        return True
    # Entering only an unresolved or unkeyed blank must not make all untouched
    # verified blanks look like an attempted wrong answer.
    if not isinstance(answer, dict):
        return False
    return any(engine.has_answer(answer.get(blank['id']))
               for blank in question.get('blanks', [])
               if (blank.get('answer') is not None or blank.get('fullWord') is not None)
               and blank.get('auditStatus') != 'answer-conflict'
               and (blank.get('answerConflict') or {}).get('status') != 'needs-review')


def timestamp(session):
    for key in ['completedAt', 'updatedAt', 'startedAt']:
        value = session.get(key)
        if type(value) in [int, float]:
            return value
    return 0


def aggregate(sessions):
    """One attempt is one submitted final answer in one ended session."""
    rows = {}
    for saved in sorted(sessions, key=timestamp):
        if saved.get('status') not in ['completed', 'abandoned']:
            continue
        seen = set()
        for stage in saved.get('plan', []):
            for question in stage.get('questions', []):
                answer = saved.get('answers', {}).get(question['id'])
                if not has_scorable_answer(question, answer):
                    continue
                grade = engine.session_grade(saved, question, stage['section'])
                if not grade or grade['total'] <= 0:
                    continue
                version = question_version(question)
                key = (saved['examId'], question['id'], version)
                if key in seen:
                    continue
                seen.add(key)
                task = question.get('taskType') or question.get('type') or 'choice'
                number = question.get('number') if type(question.get('number')) is int else None
                number_end = question.get('numberEnd') if type(question.get('numberEnd')) is int else None
                label = TASK_LABELS.get(task) or TASK_LABELS.get(question.get('type')) or 'Objective question'
                suffix = f" · {number}{'–' + str(number_end) if number_end is not None else ''}" if number is not None else ''
                source = question.get('editionSource') or question.get('source') or {}
                row = rows.setdefault(key, {
                    'mistakeId': 'mistake-' + hashlib.sha256('|'.join(key).encode()).hexdigest()[:24],
                    'questionId': question['id'], 'examId': saved['examId'], 'section': stage['section'],
                    'contentId': question.get('contentId'), 'attempts': 0, 'wrongAttempts': 0,
                })
                wrong = grade['correct'] < grade['total']
                row['attempts'] += 1
                row['wrongAttempts'] += int(wrong)
                if wrong:
                    row.update(lastWrongSessionId=saved['id'], lastWrongAt=timestamp(saved))
                row.update(examTitle=saved.get('title', saved['examId']), taskType=task, number=number,
                           numberEnd=number_end, title=label + suffix, sourcePage=source.get('page'),
                           lastAttemptAt=timestamp(saved), lastSessionId=saved['id'], lastGrade=grade,
                           status='needs_review' if wrong else 'mastered',
                           _question=question, _session=saved, _version=version)
                row.update(engine.score_snapshot_metadata(saved))
    # Correct-only histories have never belonged to a mistake collection.
    return sorted((row for row in rows.values() if row['wrongAttempts']),
                  key=lambda row: (-row['lastAttemptAt'], row['mistakeId']))
