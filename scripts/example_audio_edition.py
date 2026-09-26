"""Prepare the explicitly selected companion-audio edition of Interview 1.

The private paper import is never rewritten. Exact source/clip/reference hashes
bind this exported variant; the incompatible paper prompt stays reviewable.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

PAPER_ID = 'student-1-s-interview-1'
AUDIO_ID = PAPER_ID + '-audio'
EDITION = 'student-1-interview-audio'
OVERVIEW_URL = 'https://www.ets.org/pdfs/toefl/toefl-ibt-test-overview.pdf'
OVERVIEW_SHA = 'ce5e0eef3ea47b9964b0b1b034e96fa3b2aa0681347f17b381196cb0661249f0'
CLIP_SHA = '17f20aa9e4144e560f857a14bb8e9c6b8f2d45de977e8e0071149b86c683a729'
TRACK_SHA = '1058edbb1e4e7a65ff06bd69d097a4303a033e83d2731e2af6b24f33b4990c27'
TRANSCRIPT = "Thank you for speaking with me today. Now, I'd like you to think back to the last time you visited a city in your country, a city that you didn't live in. Why did you travel to that city? What did you like about that city?"
NOTICE = 'Interview question 1 follows the supplied original audio and differs from the paper PDF. See the version comparison in review.'


def prepare_audio_edition(exam, root, overview_pdf):
    from backend.presentation import content_digest
    reference = Path(overview_pdf)
    if not reference.is_file() or hashlib.sha256(reference.read_bytes()).hexdigest() != OVERVIEW_SHA:
        raise ValueError('The reviewed ETS Test Overview PDF is required for the audio edition export.')
    segments = json.loads((root / 'generated/media-segments.json').read_text())['segments']
    segment = next(s for s in segments if s['id'] == PAPER_ID + '-prompt')
    clip = root / 'generated' / segment['url'].lstrip('/')
    if (segment.get('sourceSha256') != TRACK_SHA or segment.get('actualSourceTranscript') != TRANSCRIPT
            or segment.get('boundaryVerified') is not True or segment.get('containsResponseWait') is not False
            or [segment.get(k) for k in ['startSeconds', 'endSeconds', 'durationSeconds']] != [12.22, 28.16, 15.94]
            or hashlib.sha256(clip.read_bytes()).hexdigest() != CLIP_SHA):
        raise ValueError('Interview audio edition source, transcript or clip changed; re-audit before export.')
    module = next(m for s in exam['sections'] if s['id'] == 'speaking' for m in s['modules'] if m['id'] == 'speaking-interview')
    paper = module['questions'][0]
    if paper['id'] != PAPER_ID:
        raise ValueError('The native paper Interview question 1 is missing.')
    q = deepcopy(paper)
    for key in ['referenceOnly', 'practiceMode', 'explanation', 'explanationSource', 'explanationAuditStatus', 'textCorrection']:
        q.pop(key, None)
    q.update(id=AUDIO_ID, prompt='Listen to the interviewer. Give a complete answer after the recording ends.',
             transcript=TRANSCRIPT, sourcePromptAvailable=True, warnings=[NOTICE],
             sourceVariant={'id':EDITION, 'notice':NOTICE, 'paperPrompt':paper['transcript'],
                            'paperPage':36, 'referenceUrl':OVERVIEW_URL, 'referencePage':19},
             source={'materialId':segment['sourceMaterialId'], 'url':segment['sourceUrl'],
                     'method':'reviewed-original-audio-edition', 'section':'speaking', 'moduleId':module['id']},
             audio={key:segment[key] for key in ['url','sourceUrl','sourceSha256','durationSeconds','startSeconds','endSeconds']},
             mediaAudit={'status':'verified-audio-edition', 'humanReviewed':False,
                         'verificationMethod':'original-ASR-transcript-compared-with-ETS-Test-Overview',
                         'paperAudioMatch':False, 'referencePdfSha256':OVERVIEW_SHA,
                         'referencePdfPage':19, 'assetSha256':CLIP_SHA})
    q['audio'].update(materialId=segment['sourceMaterialId'], segmentId=segment['id'], groupId=AUDIO_ID,
                      scope='item', mediaType='audio', verified=True, containsResponseWait=False)
    q['stemBlocks'] = [{'type':'instruction','text':q['prompt']}]
    q['contentId'] = q['curatedContentId'] = 'qcontent-' + content_digest(q)[:20]
    module['questions'][0] = q
    exam['sourceEdition'] = EDITION
    exam['warnings'] = [w for w in exam.get('warnings', []) if '采访第1题' not in w]
    exam['warnings'].append(NOTICE)
    exam['strictEligible'] = True
    exam['scopedEligibility']['speaking'] = True
    exam['validation'] = {'status':'passed', 'issues':[], 'scope':'Source-complete audio edition; timing remains disclosed local practice, not ETS calibration.'}
    inputs = exam['verificationInputs']
    inputs['assetSha256ByUrl'][segment['url']] = CLIP_SHA
    inputs['structuredContentSha256ByQuestionId'] = {
        item['id']:content_digest(item) for s in exam['sections'] for m in s['modules'] for item in m['questions']}
    return {'id':EDITION, 'questionId':AUDIO_ID, 'paperQuestionId':PAPER_ID, 'notice':NOTICE,
            'sourceTrackSha256':TRACK_SHA, 'clipSha256':CLIP_SHA, 'startSeconds':12.22, 'endSeconds':28.16,
            'referenceUrl':OVERVIEW_URL, 'referencePdfSha256':OVERVIEW_SHA, 'referencePage':19,
            'publisherNote':'The clip is from user-supplied companion audio. The transcript matches the ETS overview; this is not proof of the supplied audio publisher.'}
