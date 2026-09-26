"""Attach the user's existing analysis PDF without treating it as an official key."""
from pathlib import Path
import json
import re
import unicodedata


def explanation_lines(span):
    """Do not attach the next question or section's heading to this rationale."""
    boundary = re.compile(
        r'^(?:What|Why|When|Who|Where|How|Which|According|The word|The new fitness center|'
        r'Woman:|M\s*an:|Topic\?|About her|Default M\s*ode|Part\s+\d+|'
        r'Passage\s*:|Conversation\s*:|Announcement\s*:|Environmental Science Class Lecture|'
        r'场景\s*[:：]|办公室空调|课堂通知|心理学播客|[一二三四五]+、|第[一二三四五]+部分)', re.I)
    kept = []
    for line_no, line in enumerate(span.splitlines()):
        if line_no and boundary.match(line.strip()):
            break
        kept.append(line)
    return kept


def attach(exams,materials,root):
    root=Path(root)
    material=next((m for m in materials if '第1套' in m['name'] and '解析' in m['name'] and m['kind']=='pdf'),None)
    exam=next((e for e in exams if e['id']=='student-1'),None)
    if not material or not exam:return {'attached':0,'conflicts':0}
    data=json.loads((root/'generated/extracted'/f"{material['id']}.json").read_text())
    pages=[unicodedata.normalize('NFKC',p['text']).replace('\x00',"'") for p in data['pages']]
    offsets=[];text=''
    for i,page in enumerate(pages):offsets.append((len(text),i+1));text+=page+'\n'
    questions={q['id']:q for s in exam['sections'] for m in s['modules'] for q in m['questions']}
    stats={'attached':0,'conflicts':0,'sourceMaterialId':material['id']}
    def page_at(position):return max((page for start,page in offsets if start<=position),default=1)
    def set_explanation(q,body,position,conflict=None):
        body='\n'.join(line for line in body.splitlines() if not re.fullmatch(r'\s*\d+[.]?\s*',line)).strip()
        q['explanationSource']={'materialId':material['id'],'page':page_at(position),'url':material['url']+f'#page={page_at(position)}','origin':'user-supplied-analysis','label':'资料附带解析','official':False}
        q['explanation']='资料附带解析（非 ETS 官方解析）\n\n'+body
        q['explanationAuditStatus']='source-attached-not-used-as-answer-key'
        if conflict:
            q['explanationConflict']=conflict
            q['explanation']='此附带解析与原题或可用词块存在差异，未用它覆盖本题评分依据。请对照原题和下方冲突说明。\n\n'+q['explanation']
            stats['conflicts']+=1
        stats['attached']+=1
    listening=re.search(r'Listening Section',text)
    writing=re.search(r'W\s*riting Section',text)
    r2=re.search(r'M\s*odule\s*2',text[:listening.start()])
    l2=re.search(r'M\s*odule\s*2',text[listening.start():writing.start()])
    l2pos=listening.start()+l2.start()
    ranges=[('r1',0,r2.start(),11,10),('r2',r2.start(),listening.start(),11,10),('l1',listening.start(),l2pos,1,18),('l2',l2pos,writing.start(),1,16)]
    for prefix,start,end,first,count in ranges:
        part=text[start:end];answers=list(re.finditer(r'正确答案[：:]\s*([A-D])[.．]?\s*',part))
        if len(answers)!=count:
            stats.setdefault('warnings',[]).append(f'{prefix}: expected {count} analysis blocks, found {len(answers)}; not automatically associated')
            continue
        for index,m in enumerate(answers):
            q=questions.get(f'student-1-{prefix}-{first+index}')
            if not q:continue
            span=part[m.start():answers[index+1].start() if index+1<len(answers) else len(part)]
            kept=explanation_lines(span)
            conflict=None
            if q.get('answer') and q['answer']!=m[1]:
                conflict={'status':'conflicts-with-original-question-key','analysisAnswer':m[1],'questionAnswer':q['answer'],'questionSource':q['source'],'analysisSourcePage':page_at(start+m.start()),'resolutionEvidence':'The original question answer key is retained; the auxiliary analysis is not an authoritative replacement.'}
                if q['id']=='student-1-l1-9':
                    conflict['resolutionEvidence']='原对话开头是女性询问是否需要超市物品；随后男性说不用换衣服。题目问女性原本准备做什么，原题答案 Go shopping 与人物指代一致。'
            set_explanation(q,'\n'.join(kept),start+m.start(),conflict)
    # Cloze commentary is block-level in the original source.
    first_notice=text.find('二、')
    if first_notice<0:first_notice=pages[0].find('What type')
    q=questions.get('student-1-r1-cloze')
    if q:set_explanation(q,text[:first_notice],0,{'status':'analysis-paragraph-simplifies-source','affectedBlankIds':['b4','b9'],'resolutionEvidence':'附带解析的 on / records 与原题补字位置及原参考键 only / record 不一致；评分仍使用原题可见字母和缺字键。'})
    q=questions.get('student-1-r2-cloze')
    if q:
        end=text.find('When is the date',r2.start())
        set_explanation(q,text[r2.start():end],r2.start())
    build_end=re.search(r'W\s*rite an Em\s*ail',text[writing.start():])
    build_end_pos=writing.start()+build_end.start()
    build=text[writing.start():build_end_pos]
    markers=list(re.finditer(r'第\s*(\d+)\s*题[：:]',build))
    for i,m in enumerate(markers):
        q=questions.get(f'student-1-w-build-{int(m[1])}')
        if not q:continue
        body=build[m.end():markers[i+1].start() if i+1<len(markers) else len(build)]
        conflict=None
        if q.get('answerConflict'):conflict={'status':'uses-reference-key-with-source-structure-conflict','resolutionEvidence':q['answerConflict'].get('reason'),'sourceReferenceAnswer':q.get('sourceReferenceAnswer')}
        set_explanation(q,body,writing.start()+m.start(),conflict)
    academic=re.search(r'Academ\s*ic Discussion',text[build_end_pos:])
    academic_pos=build_end_pos+academic.start()
    speaking=text.find('Speaking Section',academic_pos)
    q=questions.get('student-1-w-email')
    if q:set_explanation(q,text[build_end_pos:academic_pos],build_end_pos)
    q=questions.get('student-1-w-academic_discussion')
    if q:set_explanation(q,text[academic_pos:speaking],academic_pos)
    interview=text.find('Take an Interview',speaking)
    repeat_part=text[speaking:interview]
    for i in range(1,8):
        q=questions.get(f'student-1-s-listen_repeat-{i}')
        if q:set_explanation(q,repeat_part,speaking)
    markers=list(re.finditer(r'Question\s+(\d+)',text[interview:]))
    for i,m in enumerate(markers):
        q=questions.get(f'student-1-s-interview-{int(m[1])}')
        if not q:continue
        end=interview+markers[i+1].start() if i+1<len(markers) else len(text)
        set_explanation(q,text[interview+m.end():end],interview+m.start())
    return stats
