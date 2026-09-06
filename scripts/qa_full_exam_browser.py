#!/usr/bin/env python3
"""Complete an original four-section exam through an isolated Playwright browser.

Test-only driver. It never posts answers directly, changes clocks, skips media,
or accesses port 4173. Prepare the named headless browser with an explicitly
marked synthetic microphone, and select the original full exam in its UI first.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PW = str(Path.home() / '.codex/skills/playwright/scripts/playwright_cli.sh')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=4185)
    parser.add_argument('--browser', default='final-full-exam')
    parser.add_argument('--answers', default='tmp/qa/final-full-exam-answers.json')
    parser.add_argument('--exercise-writing-expiry', choices=['academic_discussion'],
                        help='Let the original discussion use its complete real ten-minute window, then acknowledge expiry.')
    args = parser.parse_args()
    if args.port == 4173 or not 1024 <= args.port <= 65535:
        parser.error('Use an isolated test port, never 4173.')
    base = f'http://127.0.0.1:{args.port}'
    out = ROOT / 'tmp/qa/final-full-exam-browser'
    out.mkdir(parents=True, exist_ok=True)
    expected = json.loads((ROOT / args.answers).read_text())
    report = {'status': 'running', 'startedAt': int(time.time()*1000), 'examId': expected['examId'],
              'port': args.port, 'browser': args.browser, 'headless': True,
              'clock': 'real', 'acceleratedClock': False, 'syntheticMicrophone': True,
              'navigation': 'Normal UI Next after submitting answers; speaking auto-submits at its real deadline.',
              'exerciseWritingExpiry': args.exercise_writing_expiry,
              'states': [], 'answered': [], 'submittedAnswers': {}, 'screenshots': [], 'errors': [],
              'sourceHashes': {}, 'buildHashes': {}}
    for path in [ROOT / 'generated/exams' / (expected['examId']+'.json'), ROOT / 'shared/rules.json']:
        report['sourceHashes'][str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    source_digest = report['sourceHashes']['generated/exams/'+expected['examId']+'.json']
    if expected.get('sourceExamSha256') != source_digest:
        raise RuntimeError('The prepared QA answers do not match the current original exam hash.')
    for path in [*ROOT.joinpath('backend').glob('*.py'), *ROOT.joinpath('dist/assets').glob('index-*')]:
        report['buildHashes'][str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    calls = 0

    def save():
        pending = out / 'progress.tmp'
        pending.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
        pending.replace(out / 'progress.json')

    def get(route):
        with urllib.request.urlopen(base+route, timeout=15) as response:
            if response.headers.get('X-TOEFL-QA-Preview') != 'isolated-state-real-sources':
                raise RuntimeError('Refusing a non-preview application.')
            return json.load(response)

    def ui(body):
        nonlocal calls
        calls += 1
        code = 'async(page)=>{if(!page.url().startsWith(' + json.dumps(base+'/') + '))throw new Error("Wrong QA browser origin");' + body + '}'
        proc = subprocess.run([PW, '-s='+args.browser, 'run-code', code], cwd=ROOT,
                              capture_output=True, text=True, timeout=55)
        (out/f'ui-{calls:04d}.log').write_text(proc.stdout+proc.stderr)
        if proc.returncode or '### Error' in proc.stdout:
            raise RuntimeError(f'Browser command {calls} failed: '+(proc.stdout+proc.stderr)[-1400:])
        match = re.search(r'### Result\n(.*?)(?:\n###|\Z)', proc.stdout, re.S)
        return json.loads(match[1]) if match else None

    def capture(label):
        path = f'output/playwright/full-exam-{label}.png'
        ui('await page.screenshot({path:'+json.dumps(path)+'});')
        report['screenshots'].append(path)

    try:
        sessions = get('/api/sessions')
        active = [s for s in (sessions if isinstance(sessions,list) else sessions['sessions'])
                  if s['status']=='active' and s['examId']==expected['examId']]
        if len(active)!=1:
            raise RuntimeError('Create exactly one full strict exam through the isolated browser UI first.')
        session_id = active[0]['id']
        report['sessionId'] = session_id
        initial = get('/api/sessions/'+session_id)
        if (initial.get('mode') != 'strict' or initial.get('scope') != 'all' or initial.get('filtered')
                or initial.get('isFullScope') is not True or initial.get('stageIndex') != 0
                or initial.get('phase') != 'directions'):
            raise RuntimeError('Start with a complete, unfiltered strict exam at its first Begin screen.')
        environment = ui('return await page.evaluate(()=>({synthetic:window.__TOEFL_E2E_SYNTHETIC_MICROPHONE__===true,telemetry:!!window.__fullExamQA,userAgent:navigator.userAgent}));')
        if not environment or not environment['synthetic'] or not environment['telemetry']:
            raise RuntimeError('The marked synthetic microphone and telemetry must be initialized before Begin.')
        report['browserEnvironment'] = environment
        report['headless'] = 'HeadlessChrome' in environment['userAgent']
        if not report['headless']:
            raise RuntimeError('Use the independently prepared headless QA browser.')

        def verify_saved(qid, answer):
            stop = time.monotonic()+5
            while time.monotonic() < stop:
                saved = get('/api/sessions/'+session_id)
                if saved.get('phase') != 'response' or (saved.get('question') or {}).get('id') != qid:
                    raise RuntimeError('Question changed before its complete answer was confirmed in SQLite: '+qid)
                if saved.get('answer') == answer:
                    return
                time.sleep(.1)
            raise RuntimeError('UI answer was not saved exactly as prepared: '+qid)
        last_key = None
        seen_screenshots = set()
        while time.time()*1000-report['startedAt'] < 3*60*60*1000:
            state = get('/api/sessions/'+session_id)
            if state['status'] != 'active':
                report['terminalStatus'] = state['status']
                break
            stage = state['stage']; q = state.get('question') or {}
            key = (state['stageIndex'],state['phase'],q.get('id'),state.get('mediaIndex'))
            if key != last_key:
                event = {k:state.get(k) for k in ['stageIndex','phase','questionIndex','mediaIndex','deadline','remainingSeconds','serverNow']}
                event.update({'stageId':stage['id'],'section':stage['section'],'questionId':q.get('id'),
                              'type':q.get('type'),'taskType':q.get('taskType')})
                report['states'].append(event); report['current'] = event
                print(json.dumps(event), flush=True)
                last_key = key; save()
            if state.get('integrity',{}).get('interrupted'):
                raise RuntimeError('The full exam reported an unexpected interruption.')
            label = stage['section']+'-'+str(q.get('taskType') or q.get('type') or 'directions')+'-'+state['phase']
            if label not in seen_screenshots and state['phase'] != 'audio':
                capture(label); seen_screenshots.add(label)
            if state['phase']=='directions':
                ui('await page.getByRole("button",{name:/^Begin /}).click();')
                time.sleep(.2)
                continue
            if state['phase']=='audio' or stage['section']=='speaking':
                time.sleep(1)
                continue
            if state['phase']=='expired':
                qid = q['id']
                if qid not in report['submittedAnswers'] or state.get('answer') != report['submittedAnswers'][qid]:
                    raise RuntimeError('Writing expired before the prepared answer was saved.')
                ui('if(!await page.locator("textarea.writing-editor").isDisabled())throw new Error("Expired writing is editable");'
                   'if(await page.getByRole("timer").count())throw new Error("Expired screen still has an active clock");'
                   'await page.getByRole("button",{name:"Continue",exact:true}).click();')
                report['writingExpiryAcknowledged']={'questionId':qid,'type':q['type'],'originalDeadline':state['deadline'],'observedAt':state['serverNow'],'answerUnchanged':True,'readOnly':True,'clockAccelerated':False}
                save()
                time.sleep(.2)
                continue
            if state['phase']!='response':
                raise RuntimeError('Unexpected exam phase '+state['phase'])
            qid = q['id']; entry = expected['questions'][qid]; answer = entry['answer']
            if answer is None:
                raise RuntimeError('No source-backed QA response prepared for '+qid)
            if qid not in report['answered']:
                if q['type']=='choice':
                    selector = '.answer-choice:has(input[value='+json.dumps(str(answer))+'])'
                    ui('await page.locator('+json.dumps(selector)+').click();')
                elif q['type']=='cloze':
                    answer = {b['id']: str(answer[b['id']]) for b in q['blanks']}
                    fields = []
                    for index, blank in enumerate(q['blanks']):
                        value = answer[blank['id']]
                        length = blank.get('length') or 3
                        if not re.fullmatch(r'[A-Za-z]+', value) or len(value) != length:
                            raise RuntimeError('Prepare exact missing letters, not a full word/truncated cloze response: '+qid+'/'+blank['id'])
                        label = f"Missing letters for word {blank.get('number') or index+1}"
                        if q.get('passageTemplate'):
                            label += f', {length} letters required'
                        fields.append({'label': label, 'value': value})
                    ui('for(const field of '+json.dumps(fields)+') await page.getByRole("textbox",{name:field.label,exact:true}).fill(field.value);')
                elif q['type']=='build_sentence':
                    order = [str(int(i)) for i in answer['tokenOrder']]
                    gaps = sum(isinstance(slot,dict) and not (slot.get('fixed') or slot.get('text')) for slot in q.get('slots',[]))
                    if len(order) != gaps or len(set(order)) != len(order) or any(not 0 <= int(i) < len(q['tokens']) for i in order):
                        raise RuntimeError('Invalid prepared word-bank token identity/order: '+qid)
                    answer = {'tokenOrder': order}
                    labels = [f'Use word block {int(i)+1}: {q["tokens"][int(i)]}' for i in order]
                    owner = '.sentence-slot[data-question-id='+json.dumps(qid)+']'
                    ui('const slots=page.locator('+json.dumps(owner)+');'
                       'while(await page.locator('+json.dumps(owner+'.filled')+').count())await page.locator('+json.dumps(owner+'.filled')+').first().click();'
                       'await slots.first().click();')
                    remaining_labels = labels
                    if not report.get('wordBlockDrag'):
                        partial = [''] * gaps
                        partial[0] = order[0]
                        ui('await page.getByRole("button",{name:'+json.dumps(labels[0])+',exact:true}).dragTo(page.locator('+json.dumps(owner)+').nth(0));')
                        verify_saved(qid, {'tokenOrder': partial})
                        steps = ['word-bank-to-gap-1']
                        if gaps > 1:
                            ui('await page.locator('+json.dumps(owner)+').nth(0).dragTo(page.locator('+json.dumps(owner)+').nth(1));')
                            moved = [''] * gaps; moved[1] = order[0]
                            verify_saved(qid, {'tokenOrder': moved})
                            ui('await page.locator('+json.dumps(owner)+').nth(1).dragTo(page.locator('+json.dumps(owner)+').nth(0));')
                            verify_saved(qid, {'tokenOrder': partial})
                            steps += ['filled-gap-1-to-gap-2', 'filled-gap-2-to-gap-1']
                        report['wordBlockDrag'] = {'questionId': qid, 'tokenIndex': order[0], 'verifiedSteps': steps}
                        save()
                        remaining_labels = labels[1:]
                    ui('for(const label of '+json.dumps(remaining_labels)+') await page.getByRole("button",{name:label,exact:true}).click();')
                elif q['type'] in ['email','academic_discussion']:
                    answer = str(answer).replace('\r\n','\n').replace('\r','\n')
                    ui('await page.locator("textarea.writing-editor").fill('+json.dumps(answer)+');')
                else:
                    raise RuntimeError('Unhandled original question type '+q['type'])
                verify_saved(qid, answer)
                report['submittedAnswers'][qid] = answer
                report['answered'].append(qid)
                save()
            if args.exercise_writing_expiry == q['type']:
                time.sleep(1)
                continue
            ui('await page.getByRole("button",{name:"Next",exact:true}).click();')
            if state['questionIndex']==stage['questionCount']-1 and stage['section'] in ['reading','writing']:
                if q['type'] in ['email','academic_discussion']:
                    capture(stage['section']+'-'+q['type']+'-confirmation')
                    if q['type']=='email' and not report.get('emailConfirmationRoundTrip'):
                        ui('await page.getByRole("button",{name:"Back",exact:true}).click();'
                           'if(await page.locator("textarea.writing-editor").inputValue()!=='+json.dumps(answer)+')throw new Error("Email text changed after confirmation Back");')
                        verify_saved(qid, answer)
                        ui('await page.getByRole("button",{name:"Next",exact:true}).click();')
                        report['emailConfirmationRoundTrip'] = {'questionId': qid, 'textPreserved': True, 'sqliteAnswerPreserved': True}
                        save()
                    ui('await page.getByRole("button",{name:"Continue",exact:true}).click();')
                else:
                    ui('await page.getByRole("button",{name:"Submit",exact:true}).click();')
            time.sleep(.2)
        else:
            raise RuntimeError('Full exam exceeded its three-hour driver limit.')
        if report['terminalStatus']!='completed':
            raise RuntimeError('Exam ended without completing all stages.')
        # Give the browser finalization queue time to persist the last real take.
        deadline=time.monotonic()+20
        while True:
            review=get('/api/sessions/'+session_id+'/review')
            groups=review.get('recordings',{})
            takes=[take for group in groups.values() for take in group]
            speaking = [q['id'] for section in review['sections'] if section['id']=='speaking'
                        for module in section['modules'] for q in module['questions']]
            if (len(speaking)==11 and set(groups)==set(speaking) and len(takes)==11
                    and all(len(groups[qid])==1 and groups[qid][0].get('completeSequence') for qid in speaking)
                    and review.get('recordingIntegrity',{}).get('status')=='complete'): break
            if time.monotonic()>deadline: raise RuntimeError('Final recording queue is incomplete.')
            time.sleep(1)
        (out/'review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
        final = review['session']
        questions = [(section['id'],q) for section in review['sections'] for module in section['modules'] for q in module['questions']]
        written_ids = {q['id'] for section,q in questions if section!='speaking'}
        if {section for section,q in questions} != {'reading','listening','writing','speaking'}:
            raise RuntimeError('The completed review does not contain all four original sections.')
        if written_ids != set(report['answered']) or written_ids != set(report['submittedAnswers']):
            raise RuntimeError('The driver omitted or timed past a non-speaking source question.')
        if any(review['answers'].get(qid) != answer for qid,answer in report['submittedAnswers'].items()):
            raise RuntimeError('At least one final stored answer differs from its confirmed UI submission.')
        for section, question in questions:
            entry = expected['questions'][question['id']]
            if 'expectedObjectiveGrade' in entry and question.get('grade') != entry['expectedObjectiveGrade']:
                raise RuntimeError('Frozen objective result differs from the source-audited QA expectation: '+question['id'])
        if review['score']['total'] != expected.get('expectedObjectiveTotal'):
            raise RuntimeError('The objective denominator differs from the audited original exam.')
        if any(q['type']=='build_sentence' for _,q in questions) and not report.get('wordBlockDrag'):
            raise RuntimeError('The requested real word-block drag was not verified.')
        if any(q['type']=='email' for _,q in questions) and not report.get('emailConfirmationRoundTrip'):
            raise RuntimeError('The email confirmation Back/Continue round trip was not verified.')
        if args.exercise_writing_expiry and report.get('writingExpiryAcknowledged',{}).get('type') != args.exercise_writing_expiry:
            raise RuntimeError('The requested natural writing expiry was not observed and acknowledged.')
        if (final.get('integrity',{}).get('interrupted') or final.get('scoreSnapshotStatus')!='frozen'
                or not review.get('scoreSnapshot') or any(t.get('endedReason')!='time-limit' for t in takes)):
            raise RuntimeError('Final interruption, scoring snapshot or natural recording-stop audit failed.')
        for group in ['sourceHashes','buildHashes']:
            if any(not (ROOT/path).is_file() or hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest for path,digest in report[group].items()):
                raise RuntimeError('Source or application build changed during the full-exam run.')
        report['telemetry']=ui('return await page.evaluate(()=>window.__fullExamQA);')
        report['console']=ui('return await page.evaluate(()=>({errors:window.__fullExamQA.errors}));')
        if report['console']['errors'] or any(event.get('kind')=='error' or event.get('playbackRate',1)!=1 for event in report['telemetry']['media']):
            raise RuntimeError('Browser telemetry contains a runtime/media error or nonstandard playback speed.')
        report['verifiedWrittenQuestions'] = len(written_ids)
        report['verifiedSpeakingQuestionIds'] = speaking
        capture('completed-review')
        report['completedAt']=int(time.time()*1000)
        report['wallSeconds']=(report['completedAt']-report['startedAt'])/1000
        report['recordingTakes']=len(takes)
        report['status']='completed-awaiting-audit'
        save()
        print(json.dumps({'status':report['status'],'sessionId':session_id,'wallSeconds':report['wallSeconds']}),flush=True)
    except Exception as error:
        report['status']='failed';report['errors'].append(str(error))
        try: capture('failure')
        except Exception: pass
        save();raise


if __name__=='__main__':
    main()
