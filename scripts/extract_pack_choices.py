#!/usr/bin/env python3
"""Column-aware OCR for the original Pack question screenshots."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
from PIL import Image


def extract(question,section,root):
    root=Path(root);qid=question['id'];cache=root/'generated/extracted/choice-columns'/f'{qid}.json'
    source=root/'generated/assets/pages'/question['source']['materialId']/f"page-{question['source']['page']:03}.jpg"
    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest()
    if cache.exists():
        cached=json.loads(cache.read_text())
        if cached.get('version')==4 and cached.get('sourceImageSha256')==source_sha256:return cached
    im=Image.open(source).convert('RGB')
    left=.50
    crop=im.crop((int(im.width*left),int(im.height*.20),int(im.width*.958),int(im.height*.95)))
    cache.parent.mkdir(parents=True,exist_ok=True)
    tmp=cache.with_suffix('.png');crop.resize((crop.width*2,crop.height*2)).save(tmp)
    text=subprocess.check_output(['tesseract',str(tmp),'stdout','-l','eng','--psm','6'],stderr=subprocess.DEVNULL,env={**os.environ,'OMP_THREAD_LIMIT':'1'}).decode()
    tmp.unlink()
    # Radio icons have several OCR representations. Only a line-leading marker is
    # accepted, and four options are mandatory before structured fields are used.
    if qid=='pack-4-reading-m1-19':text=text.replace('Sen: provides','© It provides')
    marker=re.compile(r'(?m)^\s*[\'‘\"]?(?:\(?[©®€O0@○◯⊙C]\)?|Cc\)|\(\)|\.\)|[)»«>*]|\.|co|cD|CJ|Si)[),]?\s+')
    marks=list(marker.finditer(text))
    result={'version':4,'sourceImageSha256':source_sha256,'rawText':text,'status':'needs-review'}
    if len(marks)==4:
        before=text[:marks[0].start()].strip();lines=before.splitlines()
        starts=[i for i,line in enumerate(lines) if re.match(r'^[\s\"“‘\']*(?:What|Why|When|Who|Where|How|Which|According|The (?:word|phrase|passage|email|message|author)|It can|In the|All of|There are|Select|Click|Based)',line,re.I)]
        if starts:before=' '.join(lines[starts[0]:])
        if question.get('taskType')=='listen_response':before='Choose the best response.'
        choices=[]
        for i,m in enumerate(marks):
            body=text[m.end():marks[i+1].start() if i<3 else len(text)]
            body=re.sub(r'\s+',' ',body).strip().replace('|','I')
            body=body.replace('lusually','I usually').replace('Idon','I don')
            body=re.sub(r'\bIt(is|was|used|can|had|has|will|does|did)\b',r'It \1',body)
            body=body.replace('twas the first','It was the first').replace('Byseeing','By seeing')
            choices.append({'id':'ABCD'[i],'text':body})
        if before and all(len(c['text'])>1 for c in choices):result.update({'status':'parsed-with-source-image','prompt':before,'choices':choices})
    cache.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result
