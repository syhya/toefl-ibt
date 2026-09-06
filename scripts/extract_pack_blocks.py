#!/usr/bin/env python3
"""Recover printed Build-a-Sentence slots and spaced word blocks from PDF images.

Geometry comes from the visible underlines and word positions, never the answer
order. The answer is used only to repair missing spaces in an OCR word block.
"""
from pathlib import Path
import json
import os
import re
import statistics
import subprocess
from PIL import Image


def scan_words(image, cachebase, psm=6):
    cachebase=Path(cachebase);cachebase.parent.mkdir(parents=True,exist_ok=True)
    png=cachebase.with_suffix('.png');image.resize((image.width*3,image.height*3)).save(png)
    subprocess.run(['tesseract',str(png),str(cachebase),'-l','eng','--psm',str(psm),'tsv'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env={**os.environ,'OMP_THREAD_LIMIT':'1'})
    rows=[]
    for line in cachebase.with_suffix('.tsv').read_text().splitlines()[1:]:
        x=line.split('\t')
        if len(x)<12 or not x[11].strip():continue
        rows.append({'text':x[11], 'x':int(x[6])/3,'y':int(x[7])/3,'w':int(x[8])/3,'h':int(x[9])/3})
    png.unlink();cachebase.with_suffix('.tsv').unlink()
    return rows


def underline_boxes(image):
    grey=image.convert('L').point(lambda x:0 if x<160 else 255)
    pixels=grey.tobytes();width=image.width;groups=[]
    for y in range(int(image.height*.59),int(image.height*.82)):
        row=pixels[y*width:(y+1)*width]
        for m in re.finditer(b'\x00{65,250}',row):
            x=m.start();w=m.end()-x
            if x<image.width*.11:continue
            existing=next((g for g in groups if abs(g['x']-x)<8 and abs(g['w']-w)<15 and 0<=y-g['bottom']<3),None)
            if existing:existing['bottom']=y
            else:groups.append({'x':x,'y':y,'w':w,'bottom':y})
    groups=[g for g in groups if g['bottom']-g['y']<=4]
    if not groups:return []
    common_width=max(groups,key=lambda a:sum(abs(a['w']-b['w'])<=2 for b in groups))['w']
    return [g for g in groups if abs(g['w']-common_width)<=2]


def repair_spaces(text,answer):
    norm=lambda s:re.sub(r'[^a-z]','',s.lower())
    words=answer.replace('’',"'").split()
    target=norm(text)
    matches=[]
    for i in range(len(words)):
        for j in range(i+1,min(len(words),i+7)+1):
            candidate=' '.join(words[i:j]).strip('.,?!;:')
            if norm(candidate)==target:matches.append(candidate)
    if matches:return matches[0] if matches[0]=='I' else matches[0].lower()
    return {'tobe':'to be','alift':'a lift'}.get(text,text.replace('|','I'))


def extract(image_path,answer,cachebase):
    cachebase=Path(cachebase)
    cache=cachebase.with_suffix('.json')
    if cache.exists():
        cached=json.loads(cache.read_text())
        if cached.get('version')==3:return cached
    image=Image.open(image_path).convert('RGB');width,height=image.size
    lines=underline_boxes(image)
    if not lines:return {'tokens':[],'slots':[],'slotAuditStatus':'needs-review','warnings':['No printed underlines detected']}
    top=max(g['y'] for g in lines)+40;left=int(width*.11)
    token_words=scan_words(image.crop((left,top,int(width*.96),min(height,top+135))),str(cachebase)+'-tokens')
    if token_words:
        main_y=max(token_words,key=lambda a:sum(abs(a['y']-b['y'])<15 for b in token_words))['y']
        token_words=[w for w in token_words if abs(w['y']-main_y)<18]
    token_words.sort(key=lambda w:(round(w['y']/18),w['x']))
    groups=[]
    for w in token_words:
        w['text']=w['text'].replace('|','I')
        if not re.search(r'[A-Za-z]',w['text']):continue
        if groups:
            last=groups[-1][-1]
            same_row=abs(w['y']-last['y'])<max(w['h'],last['h'])*.65
            if same_row and w['x']-(last['x']+last['w'])<max(w['h'],last['h'])*.95:
                groups[-1].append(w);continue
        groups.append([w])
    tokens=[repair_spaces(' '.join(w['text'] for w in g),answer) for g in groups]
    min_y=min(g['y'] for g in lines);max_y=max(g['y'] for g in lines)
    response_top=max(0,min_y-40)
    fixed_words=scan_words(image.crop((0,response_top,width,max_y+12)),str(cachebase)+'-fixed')
    nodes=[{'x':g['x'],'y':g['y'],'slot':True} for g in lines]
    for w in fixed_words:
        w['text']=w['text'].replace('|','I')
        if w['text']=='l' and re.search(r'\bI\b',answer):w['text']='I'
        if not re.search('[A-Za-z]',w['text']) or '_' in w['text']:continue
        repaired=repair_spaces(w['text'],answer)
        if re.sub(r'[^a-z]','',repaired.lower()) not in re.sub(r'[^a-z]','',answer.lower()):continue
        w['text']=repaired
        w['y']+=response_top
        nearest=min(lines,key=lambda l:abs(w['y']+w['h']-l['y']))
        if abs(w['y']+w['h']-nearest['y'])>12:continue
        if nearest['y']==min_y and w['x']<width*.21:continue
        if any(abs(w['y']+w['h']-l['y'])<=12 and w['x']>=l['x']-4 and w['x']+w['w']<=l['x']+l['w']+4 for l in lines):continue
        nodes.append({'x':w['x'],'y':nearest['y'],'fixed':w['text'].replace('|','I')})
    nodes.sort(key=lambda n:(round(n['y']/12),n['x']))
    slots=[]
    for node in nodes:
        if node.get('slot'):slots.append({'id':f'slot-{len([s for s in slots if "id" in s])+1}'})
        elif slots and 'fixed' in slots[-1]:slots[-1]['fixed']+=' '+node['fixed']
        else:slots.append({'fixed':node['fixed']})
    result={'version':3,'tokens':tokens,'slots':slots,'slotAuditStatus':'geometry-ocr-needs-review','warnings':[], 'geometry':{'underlineCount':len(lines),'tokenCount':len(tokens)}}
    cache.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result
