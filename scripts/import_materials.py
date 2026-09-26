#!/usr/bin/env python3
"""Import local TOEFL materials without uploading them to a service.

The catalogue always inventories every non-hidden file. Interactive questions are
derived from the supplied PDFs; OCR is cached and source page/crops are retained.
Run: python scripts/import_materials.py [--ocr-all] [--jobs 6]
Optional regeneration dependencies: pymupdf, pypdf, Pillow, mutagen, tesseract.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime
import concurrent.futures
import hashlib
import json
import logging
import mimetypes
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DATA = ROOT / "data"
OUT = ROOT / "generated"
ASSETS = OUT / "assets"
CACHE = OUT / "extracted"
# This instruction is printed on all 13 original Pack cloze source pages.
PACK_CLOZE_INSTRUCTION = "Fill in the missing letters in the paragraph."
logging.getLogger("pypdf").setLevel(logging.ERROR)


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean(text):
    lines = text.replace("\x0c", "").splitlines()
    lines = [line for line in lines if not re.search(r"TOEFL\s*i?BT.*(?:Experience|Practice)|^TOEFLiBT|^Reading Section|^Listening Section|^Writing Section|^Speaking Section", line, re.I)]
    text = "\n".join(lines).strip()
    text = re.sub(r"(?<!\w)\|(?!\w)", "I", text)
    text = re.sub(r"\{([A-D])\)", r"(\1)", text)
    text = text.replace("(0)", "(D)")
    text = re.sub(r"(?m)^(\d{1,2}),\s+", r"\1. ", text)
    text = text.replace("2.1 wish", "2. I wish")
    text=text.replace('Read anotice.','Read a notice.').replace('Read anemail.','Read an email.')
    for a,b in {"Whatis":"What is", "Whatwill":"What will", "Whywasan":"Why was an", "Whenis":"When is", "Itis ":"It is ", "Aphone":"A phone", "Agame":"A game", "Acomputer":"A computer", "Goto arestaurant":"Go to a restaurant", "I'mplanning":"I'm planning", "I'mgoing":"I'm going", "I'mthinking":"I'm thinking", "I'mattending":"I'm attending", "I'mmoving":"I'm moving", "Ihadagreat":"I had a great"}.items(): text=text.replace(a,b)
    return re.sub(r"\n{3,}", "\n\n", text)


def paragraph(text):
    return re.sub(r"(?<!\n)\n(?!\n)", " ", clean(text)).strip()


def material_id(path):
    return "mat-" + hashlib.sha1(path.relative_to(DATA).as_posix().encode()).hexdigest()[:12]


def material_url(path):
    return "/materials/" + quote(path.relative_to(DATA).as_posix(), safe="/")


def family(path):
    text = str(path)
    if "Essentials" in text: return "essentials"
    if "00. TPO" in text: return "pack"
    if "01. 官方学生" in text: return "student"
    if "02. 官方教师" in text: return "teacher"
    if "03. 官方体验" in text: return "experience"
    if "04. 付费" in text: return "paid"
    return "reference"


def exam_ids(path):
    s = str(path); f = family(path)
    if f == "pack":
        m=re.search(r"2026新托福Pack-(\d)",s); return ["pack-"+m[1]] if m else []
    if f == "experience":
        m=re.search(r"(?:Pracitce Test |Practice Test )(\d)",s); return ["experience-"+m[1]] if m else []
    if f == "student":
        # Parent collection title says “第1套有解析”; never let that override file/set 02.
        local=path.name+" "+path.parent.name
        m=re.search(r"第(\d)套|样题0(\d)",local); return ["student-"+next(v for v in m.groups() if v)] if m else []
    if f == "teacher":
        m=re.search(r"test-(\d)",s); return ["teacher-"+m[1]] if m else []
    if f == "paid":
        m=re.search(r"Test\s*(\d)",s); return ["paid-"+m[1]] if m else []
    if f == "essentials":
        m=re.search(r"官方模拟题目(\d)",s); return ["essentials-"+m[1]] if m else []
    return []


def inventory():
    """Inventory the fixed PDF collection; portable packs have their own registry."""
    from pypdf import PdfReader
    try:
        from mutagen import File as AudioFile
    except ImportError:
        AudioFile = None
    materials=[]
    for p in sorted(DATA.rglob("*")):
        if not p.is_file() or p.relative_to(DATA).parts[0] == 'user-packs' or any(part.startswith(".") for part in p.relative_to(DATA).parts): continue
        suffix=p.suffix.lower()
        kind = "pdf" if suffix == ".pdf" else "video" if suffix == ".mp4" else "audio" if suffix in {".mp3", ".m4a", ".ogg", ".wav"} else "file"
        item={"id":material_id(p),"path":p.relative_to(DATA).as_posix(),"url":material_url(p),"name":p.name,"category":family(p),"kind":kind,"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"supplemental":family(p) in {"essentials", "reference"},"examIds":exam_ids(p),"warnings":[]}
        if kind=="pdf":
            try:
                reader=PdfReader(p)
                item["pages"]=len(reader.pages)
                texts=[x.extract_text() or "" for x in reader.pages]
                item["textCharacters"]=sum(map(len,texts))
                item["scanned"]=item["textCharacters"] < len(texts)*150
                item["extraction"]="ocr-required" if item["scanned"] else "text"
                if not item["scanned"]:
                    dump(CACHE / f"{item['id']}.json", {"materialId":item["id"],"sha256":item["sha256"],"method":"pdf-text","pages":[{"page":i+1,"text":t} for i,t in enumerate(texts)]})
            except Exception as e: item["warnings"].append("PDF extraction failed: "+str(e))
        elif AudioFile:
            try:
                audio=AudioFile(p)
                if audio is not None: item["durationSeconds"]=round(audio.info.length,3)
            except Exception as e: item["warnings"].append("Duration unavailable: "+str(e))
        materials.append(item)
    return materials


def prepare_pdf(material, jobs=6):
    """Create reproducible local OCR and faithful full-page JPEGs, with caching."""
    import fitz
    target=CACHE / f"{material['id']}.json"
    ocr_mode=6 if material["category"] in {"student","teacher","paid"} else 3
    engine='vision' if material['category']=='reference' and re.search(r'[\u4e00-\u9fff]',material['name']) and sys.platform=='darwin' and shutil.which('swiftc') else 'tesseract'
    vision_binary=OUT/'tools/ocr-vision'
    asset_dir=ASSETS / "pages" / material["id"]
    asset_dir.mkdir(parents=True,exist_ok=True)
    same_source_images = False
    if target.exists():
        old=json.loads(target.read_text())
        same_source_images = (old.get("sha256") == material["sha256"] and
                              old.get("method") in {"tesseract-ocr", "local-vision-ocr"})
        if same_source_images and old.get('engine','tesseract')==engine and old.get("ocrMode",3)==ocr_mode and all((ASSETS/p["asset"].removeprefix("/assets/")).exists() for p in old["pages"]):
            return old["pages"]
    if engine=='vision' and not vision_binary.exists():
        vision_binary.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(['swiftc',str(ROOT/'scripts/ocr_vision.swift'),'-o',str(vision_binary)],check=True,capture_output=True)
    with fitz.open(DATA/material["path"]) as pdf:
        page_count = len(pdf)
    def page_job(i):
        dest=asset_dir / f"page-{i+1:03}.jpg"
        tempbase=asset_dir/f"page-{i+1:03}"
        # A filename alone is not provenance. Re-render when the source hash is
        # missing or changed; unbound tmp/pdfs legacy caches are never reused.
        if not same_source_images or not dest.exists():
            # Separate fitz document per worker avoids sharing mutable page state.
            with fitz.open(DATA/material["path"]) as doc:
                pix=doc[i].get_pixmap(matrix=fitz.Matrix(1.8,1.8))
                pix.save(dest, jpg_quality=88)
        if engine=='vision':
            words=json.loads(subprocess.check_output([str(vision_binary),str(dest)]))
            text='\n'.join(w['text'] for w in words)
        else:
            subprocess.run(["tesseract",str(dest),str(tempbase),"-l","eng","--psm",str(ocr_mode),"txt","tsv"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env={**os.environ,"OMP_THREAD_LIMIT":"1"})
            text=tempbase.with_suffix(".txt").read_text()
            words=parse_tsv(tempbase.with_suffix(".tsv").read_text())
            tempbase.with_suffix(".txt").unlink();tempbase.with_suffix(".tsv").unlink()
        from PIL import Image
        with Image.open(dest) as page_image:
            w,h=page_image.size
        return {"page":i+1,"text":text,"asset":"/assets/"+dest.relative_to(ASSETS).as_posix(),"width":w,"height":h,"words":words}
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool: pages=list(pool.map(page_job,range(page_count)))
    dump(target,{"materialId":material["id"],"sha256":material["sha256"],"method":"local-vision-ocr" if engine=='vision' else 'tesseract-ocr','engine':engine,"ocrMode":ocr_mode,"pages":pages})
    print(f"OCR {material['name']}: {len(pages)} pages",flush=True)
    return pages


def parse_tsv(text):
    rows=[]
    for line in text.splitlines()[1:]:
        fields=line.split("\t")
        if len(fields)<12 or not fields[11].strip():continue
        rows.append({"text":fields[11],"x":int(fields[6]),"y":int(fields[7]),"w":int(fields[8]),"h":int(fields[9]),"confidence":float(fields[10])})
    return rows


def crop(page, name, top, bottom, left=.09, right=.91):
    from PIL import Image
    source=ASSETS / page["asset"].removeprefix("/assets/")
    image=Image.open(source)
    box=(int(image.width*left),int(top),int(image.width*right),int(bottom))
    dest=ASSETS/"stems"/(name+".jpg"); dest.parent.mkdir(parents=True,exist_ok=True)
    image.crop(box).save(dest,quality=92)
    return {"url":"/assets/"+dest.relative_to(ASSETS).as_posix(),"alt":"Original question from the supplied PDF","role":"stem"}


def find_y(page, phrase, default):
    for word in page["words"]:
        if re.fullmatch(phrase,word["text"],re.I): return word["y"]
    return int(page["height"]*default)


def phrase_y(page,phrase,default=.1):
    norm=lambda s:re.sub(r'[^a-z0-9]','',s.lower())
    needle=[norm(t) for t in phrase.split() if norm(t)]
    words=[w for w in page['words'] if norm(w['text'])]
    for i in range(len(words)-len(needle)+1):
        if [norm(w['text']) for w in words[i:i+len(needle)]]==needle:return words[i]['y']
    return page['height']*default


def source(material,page):
    return {"materialId":material["id"],"page":page,"url":material["url"]+f"#page={page}","method":"ocr-with-source"}


def mc_questions(text, start, end):
    result=[]
    matches=list(re.finditer(r"(?m)^\s*(\d{1,2})[.)]\s+",text))
    for i,m in enumerate(matches):
        n=int(m[1])
        if not start<=n<=end:continue
        body=text[m.end():matches[i+1].start() if i+1<len(matches) else len(text)]
        opts=list(re.finditer(r"\(([A-D])\)\s*",body))
        if [o[1] for o in opts[:4]] != list("ABCD"):continue
        choices=[]
        for j,opt in enumerate(opts[:4]):
            choice=body[opt.end():opts[j+1].start() if j<3 else len(body)]
            choice=re.split(r"\n\s*Listen to |\n\s*Read an? ",choice)[0]
            choices.append({"id":opt[1],"text":paragraph(choice)})
        result.append({"number":n,"type":"choice","prompt":paragraph(body[:opts[0].start()]),"choices":choices})
    return result


_CURATION_FILE = ROOT / 'scripts/verified_paper.json'
_CURATION = json.loads(_CURATION_FILE.read_text()) if _CURATION_FILE.exists() else {}

EXPERIENCE = {1: {'r': [[4, 5, 6, 7], [9, 10, 11, 12]],
     'rak': [13, 14],
     'l': [[17, 18, 19, 20, 21, 22], [24, 25, 26, 27, 28]],
     'lak': [29, 30],
     'w': [32, 33, 34, 35, 36],
     's': [38, 39]},
 2: {'r': [[4, 5, 6, 7], [9, 10, 11, 12]],
     'rak': [13, 14],
     'l': [[17, 18, 19, 20, 21, 22, 23], [25, 26, 27, 28, 29]],
     'lak': [30, 31],
     'w': [33, 34, 35, 36, 37],
     's': [39, 40]},
 3: {'r': [[4, 5, 6, 7], [9, 10, 11, 12]],
     'rak': [13, 14],
     'l': [[17, 18, 19, 20, 21], [23, 24, 25, 26, 27]],
     'lak': [28, 29],
     'w': [31, 32, 33, 34, 35],
     's': [37, 38]}}
for _n, _cfg in EXPERIENCE.items():
    _cfg.update(_CURATION.get('experiences', {}).get(str(_n), {}))

# Transcribed from the supplied answer-key pages; not model-generated answers.
BUILD_ANSWERS = {n: _CURATION.get('experiences', {}).get(str(n), {}).get('wa', []) for n in (1, 2, 3)}

# These answers are transcribed from the four supplied official PDF answer keys.
PAPER = {('student', 1): {'r': [[4, 5, 6, 7, 8], [10, 11, 12, 13]],
                  'rg': [[([4], 11, 12), ([5, 6], 13, 15), ([7, 8], 16, 20)],
                         [([10], 11, 12), ([11], 13, 15), ([12, 13], 16, 20)]],
                  'rak': [14, 15],
                  'l': [[18, 19, 20, 21], [23, 24, 25]],
                  'lak': [26, 27],
                  'w': [29, 30, 31, 32, 33],
                  's': [35, 36]},
 ('student', 2): {'r': [[4, 5, 6, 7], [9, 10, 11, 12]],
                  'rg': [[([4, 5], 11, 12), ([5, 6], 13, 15), ([6, 7], 16, 20)],
                         [([9, 10], 11, 12), ([10, 11], 13, 15), ([11, 12], 16, 20)]],
                  'rak': [13, 14],
                  'l': [[17, 18, 19, 20], [22, 23, 24, 25]],
                  'lak': [26, 27],
                  'w': [29, 30, 31, 32, 33],
                  's': [35, 36]},
 ('teacher', 1): {'r': [[4, 5, 6, 7], [9, 10, 11, 12]],
                  'rak': [13, 14],
                  'l': [[17, 18, 19, 20], [22, 23, 24, 25]],
                  'lak': [26, 27],
                  'w': [29, 30, 31, 32, 33],
                  's': [35, 36]},
 ('teacher', 2): {'r': [[4, 5, 6, 7], [9, 10, 11, 12]],
                  'rak': [13, 14],
                  'l': [[17, 18, 19, 20], [22, 23, 24, 25]],
                  'lak': [26, 27],
                  'w': [29, 30, 31, 32, 33],
                  's': [35, 36]}}
for (_family, _n), _cfg in PAPER.items():
    _cfg.update(_CURATION.get('papers', {}).get(f'{_family}-{_n}', {}))

# '_' is one movable word/phrase position. Literal strings are already printed in
# the source sentence. Verified against every Experience Day Build-a-Sentence crop.
EXPERIENCE_SLOTS = {int(n): slots for n, slots in _CURATION.get('experienceSlots', {}).items()}

PACK_PREFIXES = {tuple(map(int, key.split('-'))): value for key, value in _CURATION.get('packPrefixes', {}).items()}


def lookup_audio(materials, examid, name):
    matches=[m for m in materials if examid in m["examIds"] and m["name"]==name]
    if len(matches)!=1: return None
    m=matches[0]
    return {"url":m["url"],"materialId":m["id"],"sourceSha256":m['sha256'],"durationSeconds":m.get("durationSeconds"),"mediaType":m["kind"]}


def experience_exam(n, material, pages, materials, config=None, exam_id=None):
    eid=exam_id or f"experience-{n}"; cfg=config or EXPERIENCE[n];fam=eid.rsplit('-',1)[0]
    title={"experience":"体验日官方练习","student":"官方学生版样题","teacher":"官方教师版样题"}[fam]+f" {n}"
    exam={"schemaVersion":1,"id":eid,"title":title,"family":fam,"sourceMaterialIds":[m["id"] for m in materials if eid in m["examIds"]],"strictEligible":False,"warnings":["固定纸版练习路径；ETS 自适应算法与正式评分不可本地复制。","扫描题经过本地 OCR；补字题与组句题保留原页裁图。"],"sections":[]}
    def pg(i):return pages[i-1]
    # The scan's '13' is misread as '18'; verified against the source image.
    if fam=="experience" and n==2:
        pages=[dict(p) for p in pages]
        pages[9]["text"]=pages[9]["text"].replace("18. What is this advertisement", "13. What is this advertisement")
    if fam=="student" and n==2:
        pages=[dict(p) for p in pages]
        pages[5]["text"]=pages[5]["text"].replace("TT. In which", "17. In which")
        pages[9]["text"]=pages[9]["text"].replace("18. Whatis indicated", "13. Whatis indicated")
        for i in [23,24]:
            pages[i]["text"]=re.sub(r"(?m)^(1[3-7])[.]",lambda m:str(int(m[1])-1)+".",pages[i]["text"])
        exam["warnings"].append("原题 Listening Module 2 的题号在11后跳到13；本地顺序号12–16对应原纸版13–17，答案按题目顺序对齐。")
    if fam=="teacher" and n==1:
        pages=[dict(p) for p in pages]
        for i in [8,9,10,11]:pages[i]["text"]=re.sub(r"(?m)^(\d{1,2})[.]",lambda m:str(int(m[1])+10)+".",pages[i]["text"])
        pages[18]["text"]=pages[18]["text"].replace("18. Whois the intended", "13. Whois the intended")
        exam["warnings"].append("原题 Reading Module 2 的选择题印为1–10；本地顺序号11–20按答案表对齐，并保留原题号。")
    if fam=="teacher" and n==2:
        pages=[dict(p) for p in pages]
        for i in [18,19]:pages[i]["text"]=re.sub(r"(?m)^(1[1-7])[.]",lambda m:str(int(m[1])+1)+".",pages[i]["text"])
        pages[18]["text"]=pages[18]["text"].replace("What do the speakers imply", "11. What do the speakers imply")
        exam["warnings"].append("原题 Listening Module 1 第二段会话首题未编号，后续印刷题号落后一位；本地11–18按答案表顺序对齐，保留原始编号。")
    # Original pages define three reading passage groups per module.
    reading={"id":"reading","title":"Reading","modules":[]}
    for mod,nums in enumerate(cfg["r"],1):
        questions=[];texts=[clean(pg(i)["text"]) for i in nums]
        answer=cfg.get("ra",[[],[]])[mod-1]
        prefixes=cfg.get("prefixes",[[],[]])[mod-1]
        p=pg(nums[0]);read_y=find_y(p,r"Read",.38)
        cloze={"id":f"{eid}-r{mod}-cloze","number":1,"numberEnd":10,"type":"cloze","prompt":"Fill in the missing letters. Enter only the missing letters for each numbered word, in reading order.","blanks":[{"id":f"b{i+1}","number":i+1,"prefix":prefixes[i] if i<len(prefixes) else "","answer":answer[i] if i<len(answer) else None,"length":len(answer[i]) if i<len(answer) else None} for i in range(10)],"assets":[crop(p,f"{eid}-r{mod}-cloze",find_y(p,r"Fill",.1)-6,read_y-8)],"source":source(material,nums[0]),"warnings":[]}
        if len(answer)>=10:cloze["answer"]={f"b{i+1}":answer[i] for i in range(10)}
        questions.append(cloze)
        groups=[(a,b,c) for a,b,c in cfg["rg"][mod-1]] if cfg.get("rg") else [([nums[0]],11,12),([nums[1]],13,15),(nums[2:],16,20)]
        for pnums,start,end in groups:
            text="\n\n".join(clean(pg(i)["text"]) for i in pnums)
            before=re.split(rf"(?m)^\s*{start}[.]\s*",text,maxsplit=1)[0]
            if start in {11,13}:
                headings=list(re.finditer(r'(?m)^Read\s+.+$',before))
                if headings:before=before[headings[-1].start():]
            else:
                headings=list(re.finditer(r'(?m)^[A-Z][A-Za-z-]*(?: (?:[A-Z][A-Za-z-]*|of|the|and|in|on|for|to|a))*\s*$',before))
                if headings:before=before[headings[-1].start():]
            passage=paragraph(before)
            passage_asset=None
            if start==16 and fam in {'student','teacher'}:
                # PSM 6 recovers numbering reliably but does not preserve paragraph
                # gaps. Retain the original passage layout for paragraph questions.
                first_page=pg(pnums[0]);title=before.splitlines()[0].strip()
                original_start=6 if fam=='teacher' and n==1 and mod==2 else 16
                top=phrase_y(first_page,title,.12)-6;bottom=find_y(first_page,rf'{original_start}\.',.83)-10
                if bottom>top:
                    passage_asset=crop(first_page,f'{eid}-r{mod}-academic-passage',top,bottom,left=.08,right=.94)
                    passage_asset['role']='passage';passage_asset['alt']='Original academic passage with its paragraph boundaries preserved'
            for q in mc_questions(text,start,end):
                q.update({"id":f"{eid}-r{mod}-{q['number']}","passage":passage,"source":source(material,next((i for i in pnums if re.search(rf"(?m)^\s*{q['number']}[.]",clean(pg(i)["text"]))),pnums[0])),"warnings":[]})
                if q["number"]<=len(answer):q["answer"]=answer[q["number"]-1]
                if passage_asset:
                    q['passageText']=q['passage'];q['passage']='';q['assets']=[passage_asset];q['passageLayout']='original-paragraph-image'
                if fam=="teacher" and n==1 and mod==2:q["source"]["originalNumber"]=q["number"]-10
                questions.append(q)
        reading["modules"].append({"id":f"reading-m{mod}","title":f"Reading · Module {mod}","route":"common","questions":questions,"expectedItemCount":20})
    exam["sections"].append(reading)
    listening={"id":"listening","title":"Listening","modules":[]}
    for mod,nums in enumerate(cfg["l"],1):
        text="\n\n".join(clean(pg(i)["text"]) for i in nums)
        questions=mc_questions(text,1,18 if mod==1 else 16)
        answer=cfg.get("la",[[],[]])[mod-1]
        for q in questions:
            number=q["number"]
            if number<=8:
                q["transcript"]=q["prompt"]
                q["prompt"]="Choose the best response."
                name=f"Listening{mod}_Listen_Response_Question{number}.ogg";group=f"l{mod}-q{number}";scope="item"
                q["taskType"]="listen_response"
            else:
                if number<=10:rng="9-10";typ="Conversation"
                elif number<=12 and mod==1:rng="11-12";typ="Conversation"
                elif number<=14 and mod==1:rng="13-14";typ="Announcement"
                elif number<=12 and mod==2:rng="11-12";typ="Announcement"
                else:rng="15-18" if mod==1 else "13-16";typ="Academic_Talk"
                name=f"Listening{mod}_{typ}_Questions_{rng}.ogg";group=f"l{mod}-{typ}-{rng}";scope="group"
                direction=lookup_audio(materials,eid,f"Listening{mod}_{typ}_Directions_{rng}.ogg")
                if number==int(rng.split('-')[0]) and direction:q["directionsAudio"]={**direction,"scope":"directions","groupId":group+"-directions"}
                first=int(rng.split('-')[0]);start=re.search(rf"(?m)^\s*{first}[.]\s*",text)
                prefix=text[:start.start()] if start else ""
                split=re.split(r"\n\s*(?=Listen to )",prefix)
                q["transcript"]=paragraph(split[-1])
                q["taskType"]=typ.lower()
            audio=lookup_audio(materials,eid,name)
            q.update({"id":f"{eid}-l{mod}-{number}","source":source(material,next((i for i in nums if re.search(rf"(?m)^\s*{number}[.]",clean(pg(i)["text"]))),nums[0])),"warnings":[]})
            if audio:q["audio"]={**audio,"groupId":group,"scope":scope}
            else:q["warnings"].append("Missing or ambiguous audio mapping")
            if number<=len(answer):q["answer"]=answer[number-1]
            if fam=="student" and n==2 and mod==2 and number>=12:q["source"]["originalNumber"]=number+1
            if fam=="teacher" and n==2 and mod==1 and number>=11:q["source"]["originalNumber"]=None if number==11 else number-1
        listening["modules"].append({"id":f"listening-m{mod}","title":f"Listening · Module {mod}","route":"common","questions":questions,"expectedItemCount":18 if mod==1 else 16})
    exam["sections"].append(listening)
    writing={"id":"writing","title":"Writing","modules":[]}
    builds=[]
    answer_text=clean(pg(cfg["w"][4])["text"])
    answer_lines=cfg.get("wa",BUILD_ANSWERS[n])
    for page_num in cfg["w"][:2]:
        page=pg(page_num);text=clean(page["text"])
        items=list(re.finditer(r"(?m)^\s*(\d{1,2})[.]\s+",text))
        for idx,m in enumerate(items):
            number=int(m[1]);body=text[m.end():items[idx+1].start() if idx+1<len(items) else len(text)]
            y=find_y(page,rf"{number}\..*",.14);nextnum=int(items[idx+1][1]) if idx+1<len(items) else None
            bottom=find_y(page,rf"{nextnum}\..*",.86)-12 if nextnum else find_y(page,r"TOEFL.*",.93)-15
            tokens=[]
            for line in body.splitlines():
                if "/" in line:tokens.extend(t.strip() for t in line.split("/") if t.strip())
            q={"id":f"{eid}-w-build-{number}","number":number,"type":"build_sentence","prompt":"Make an appropriate sentence using the words and phrases in the original question. Keep any words already supplied in the sentence.","tokens":tokens,"assets":[crop(page,f"{eid}-build-{number}",y-7,bottom)],"source":source(material,page_num),"warnings":[]}
            if fam=="experience" and n in EXPERIENCE_SLOTS:
                layout=EXPERIENCE_SLOTS[n][number-1]
                q["slots"]=[{"id":f"slot-{i+1}"} if token=='_' else {"fixed":token} for i,token in enumerate(layout)]
                q["slotAuditStatus"]="verified-source-image"
                if n==3 and number==7:q["tokens"]=["would","to know","how","I","you","happen","can get"]
                if n==3 and number==1:
                    q["contextPrefix"]="Thanks."
                    q["tokens"]=["you want","of it","me","you","to send","do","a copy"]
            if number<=len(answer_lines):q["answer"]=re.sub(r"^\d+[.\s]+","",answer_lines[number-1])
            builds.append(q)
    writing["modules"].append({"id":"writing-build","title":"Build a Sentence","questions":builds,"expectedItemCount":10})
    for kind,ind,number in [("email",2,11),("academic_discussion",3,12)]:
        pnum=cfg["w"][ind]; page=pg(pnum);text=clean(page["text"])
        q={"id":f"{eid}-w-{kind}","number":number,"type":kind,"prompt":text,"source":source(material,pnum),"warnings":["Use the original page to verify any OCR spelling or names."],"assets":[crop(page,f"{eid}-{kind}",page["height"]*.10,page["height"]*.88)]}
        writing["modules"].append({"id":"writing-email" if kind=="email" else "writing-discussion","title":"Write an Email" if kind=="email" else "Academic Discussion","questions":[q],"expectedItemCount":1})
    exam["sections"].append(writing)
    speaking={"id":"speaking","title":"Speaking","modules":[]}
    for kind,pnum,label,role,expected in [("listen_repeat",cfg["s"][0],"Listen and Repeat","Trainer",7),("interview",cfg["s"][1],"Take an Interview","Interviewer",4)]:
        text=clean(pg(pnum)["text"]); parts=re.split(rf"\b{role}:\s*",text)
        questions=[]
        for i in range(expected):
            name=f"Speaking_Listen_Repeat_{i+1}.ogg" if kind=="listen_repeat" else f"Speaking_Interview_{i+1}.mp4"
            audio=lookup_audio(materials,eid,name)
            q={"id":f"{eid}-s-{kind}-{i+1}","number":i+1 if kind=="listen_repeat" else i+8,"type":kind,"prompt":"Listen carefully. Repeat what you heard once." if kind=="listen_repeat" else "Listen to the interviewer. Give a complete answer after the recording ends.","context":paragraph(parts[0]),"transcript":paragraph(parts[i+1]) if i+1<len(parts) else "","source":source(material,pnum),"warnings":[]}
            if audio:q["audio"]={**audio,"groupId":f"s-{kind}-{i+1}","scope":"item"}
            else:q["warnings"].append("Missing or ambiguous audio mapping")
            questions.append(q)
        direction_name="Speaking_Listen_Repeat_Directions.ogg" if kind=="listen_repeat" else "Speaking_Interview_Directions.ogg"
        direction=lookup_audio(materials,eid,direction_name)
        speaking["modules"].append({"id":f"speaking-{kind}","title":label,"instructions":paragraph(parts[0]),"directionsAudio":direction,"questions":questions,"expectedItemCount":expected})
    exam["sections"].append(speaking)
    return finalize_exam(exam)


def finalize_exam(exam):
    exam["questionCount"]=sum(len(q.get("blanks",[])) if q["type"]=="cloze" else 1 for s in exam["sections"] for m in s["modules"] for q in m["questions"])
    exam["screenCount"]=sum(len(m["questions"]) for s in exam["sections"] for m in s["modules"])
    exam["autoScorableCount"]=sum(sum(b.get('answer') is not None and b.get('autoScorable',True) for b in q.get('blanks',[])) if q['type']=='cloze' else 1 if q['type'] in {'choice','build_sentence'} and q.get('answer') is not None else 0 for s in exam['sections'] for m in s['modules'] for q in m['questions'] if q.get('sourcePromptAvailable',True))
    expected_objective=sum(len(q['blanks']) if q['type']=='cloze' else 1 for s in exam['sections'] for m in s['modules'] for q in m['questions'] if q['type'] in {'choice','cloze','build_sentence'} and q.get('sourcePromptAvailable',True))
    exam['unscoredCount']=max(0,expected_objective-exam['autoScorableCount']);exam['autoScoringComplete']=exam['unscoredCount']==0
    return exam


def parse_pack_answers(material):
    cached=json.loads((CACHE/f"{material['id']}.json").read_text())
    text="\n".join(p["text"] for p in cached["pages"])
    section="reading";module=1;answers={};last=None
    for line in text.splitlines():
        line=line.strip()
        sect=re.search(r"\b(Reading|Listening|Writing|Speaking)\b",line,re.I)
        if sect:
            section=sect[1].lower();module=1;last=None
        mod=re.search(r"module\s*([12])",line,re.I)
        if mod:module=int(mod[1]);last=None
        match=re.match(r"^(\d{1,2})[.\s]+(.+)",line)
        key=f"{section}-m{module}"
        if match:
            number=int(match[1]); answers.setdefault(key,{})[number]=match[2].strip();last=(key,number)
        elif last and line and not re.search(r"Build a sentence|Listen and repeat|Pack\s*\d",line,re.I) and not (sect or mod):
            answers[last[0]][last[1]]+=" "+line
    return answers


def pack_exam(n, material, pages, materials):
    eid=f"pack-{n}"
    related=[m for m in materials if eid in m["examIds"]]
    key_material=next(m for m in related if "参考答案" in m["name"])
    answers=parse_pack_answers(key_material)
    exam={"schemaVersion":1,"id":eid,"title":f"TPO Pack {n}","family":"pack","sourceMaterialIds":[m["id"] for m in related],"strictEligible":False,"warnings":["听力和口语只有整段音轨，未核验逐题切分；不支持完整严格模考。可交互练习阅读/写作，整段音轨请在资料库学习。","使用原题截图；补字答案来自参考答案的完整单词，按完整词输入。","练习截图和参考答案为用户提供资料，题量与公开基本版可能不同。"],"sections":[{"id":s,"title":s.title(),"modules":[]} for s in ["reading","listening","writing","speaking"]]}
    section_map={s["id"]:s for s in exam["sections"]}
    for sid in ["listening","speaking"]:
        audio=next((m for m in related if m["kind"]=="audio" and sid in m["name"].lower()),None)
        if audio:section_map[sid]["practiceAudio"]={"url":audio["url"],"materialId":audio["id"],"durationSeconds":audio.get("durationSeconds"),"scope":"section","warning":"整段学习音轨，不能自动逐题同步。"}
    current="reading";module=1;modules={};prev_numbers={};timings={};listen_type="listen_response"
    for page in pages:
        text=page["text"]
        if n==3 and page["page"] in {18,20}:
            # Source-image review confirms these headers, which OCR omitted.
            text=f"Reading | Question {13 if page['page']==18 else 15} of 15\n"+text
        sect=re.search(r"\b(Reading|Listening|Writing|Speaking)\b",text[:500])
        if sect:
            new=sect[1].lower()
            if new!=current:current=new;module=1
        mod=re.search(r"\bModule\s*([12])\b",text)
        if mod and not re.search(r"Question[s]?\s+\d",text):
            module=int(mod[1])
            if current=="reading":
                time=re.search(r"\b00:(\d{2}):(\d{2})\b",text)
                if time:timings[f"reading-m{module}"]={"durationSeconds":int(time[1])*60+int(time[2]),"timingSource":source(material,page["page"]),"timingNote":"该资料模块开始说明页显示的时限；不是对所有正式试卷的保证。"}
        if current=="listening" and "Listen to " in text:
            listen_type="academic_talk" if "talk " in text or "podcast" in text else "announcement" if "announcement" in text else "conversation"
        if current=="listening" and "Module 2" in text:listen_type="listen_response"
        qmatch=re.search(r"Question[s]?\s*\|?\s*(\d{1,2})(?:\s*[-–]\s*(\d{1,2}))?\s+of\s+(\d{1,2})",text,re.I)
        if not qmatch:
            # Two Pack-6 speaking headers were damaged in OCR; surrounding question pages are contiguous.
            if current=="speaking" and re.search(r"Question\s*(?:\d*)\s*of 11|Listen and repeat only once",text) and "speaking" in prev_numbers and prev_numbers["speaking"]<7:
                number=prev_numbers["speaking"]+1;end=None;total=11
            else:continue
        else:number=int(qmatch[1]);end=int(qmatch[2]) if qmatch[2] else None;total=int(qmatch[3])
        prev_numbers[current]=number
        if current=="writing":
            mid="writing-build" if total==10 else "writing-email" if number==1 else "writing-discussion"
            kind="build_sentence" if total==10 else "email" if number==1 else "academic_discussion"
        elif current=="speaking":mid="speaking-listen_repeat" if number<=7 else "speaking-interview";kind="listen_repeat" if number<=7 else "interview"
        else:mid=f"{current}-m{module}";kind="cloze" if end else "choice"
        if mid not in modules:
            title=mid.replace("-"," · ").replace("_"," ").title()
            expected=total if current in {'reading','listening'} else 10 if kind=='build_sentence' else 7 if kind=='listen_repeat' else 4 if kind=='interview' else 1
            modules[mid]={"id":mid,"title":title,"route":"common","questions":[],"expectedItemCount":expected,**timings.get(mid,{})}
            section_map[current]["modules"].append(modules[mid])
        q={"id":f"{eid}-{mid}-{number}","number":number,"type":kind,"source":source(material,page["page"]),"warnings":[]}
        q["assets"]=[crop(page,q["id"],page["height"]*.18,page["height"]*.97,left=.044,right=.957)]
        answer=answers.get(f"{current}-m{module}",{}).get(number)
        if kind=="cloze":
            q.update({"numberEnd":end,"answerMode":"missing_letters","prompt":PACK_CLOZE_INSTRUCTION,"blanks":[{"id":f"b{i}","number":i,"prefix":"","answer":answers.get(mid,{}).get(i)} for i in range(number,end+1)]})
            prefixes=PACK_PREFIXES.get((n,module,number),['']*len(q['blanks']))
            for i,blank in enumerate(q["blanks"]):
                blank["prefix"]=prefixes[i]
                blank["fullWord"]=blank["answer"]
                blank["sourceReferenceAnswer"]=blank["answer"]
                blank["missingLetters"]=blank["answer"][len(prefixes[i]):] if blank["answer"] else None
                blank["answer"]=blank["missingLetters"]
                blank["length"]=len(blank["missingLetters"]) if blank["missingLetters"] else None
                blank["acceptedAnswers"]=[blank["missingLetters"],blank["fullWord"]]
                blank["auditStatus"]="verified-prefix-source-image"
                if n==1 and module==1 and blank['number']==16:
                    blank.update({'fullWord':'roles','missingLetters':'les','answer':'les','length':3,'acceptedAnswers':['les','roles'],'answerConflict':{'provided':'role','resolvedAnswer':'roles','status':'resolved-from-source','reason':'The source shows ro___, and the sentence has play essential roles without a singular article; the parallel paid-source key also gives roles.'}})
                if n==3 and module==1 and blank["number"] in {1,3}:
                    corrected={1:"These",3:"organisms"}[blank["number"]]
                    blank["answerConflict"]={"provided":blank["fullWord"],"contextualCorrection":corrected,"status":"needs-review","reason":"The visible prefix/blank count and the plural noun phrase conflict with the provided reference key."}
                    blank["answer"]=None;blank["acceptedAnswers"]=[];blank["auditStatus"]="answer-conflict"
                if n==3 and module==2 and blank["number"]==1:
                    blank["answerConflict"]={"provided":"reshapes","contextualAlternative":"reshaped","status":"needs-review","reason":"The rest of the Industrial Revolution paragraph is narrated in the past tense."}
                    blank["answer"]=None;blank["acceptedAnswers"]=[];blank["auditStatus"]="answer-conflict"
            q["answerMode"]="missing_letters"
            q["prompt"]=PACK_CLOZE_INSTRUCTION
            q["answer"]={b["id"]:b["answer"] for b in q["blanks"] if b.get("answer")}
        elif kind=="choice":
            q.update({"prompt":f"Answer question {number} shown in the original image.","choices":[{"id":c,"text":f"Option {c} · 见原题第 {i+1} 个选项"} for i,c in enumerate("ABCD")]})
            if answer and re.fullmatch(r"[ABCD]",answer):q["answer"]=answer
            elif answer:
                q["type"]="short_answer";q.pop("choices");q["prompt"]="Copy the sentence you select from the original passage. This item requires self-review."
                q["referenceAnswer"]=answer;q["warnings"].append("原参考答案按句子位置描述，未转为不可靠的自动判分选项。")
            if current=="listening":
                q["taskType"]=listen_type
                q["warnings"].append("只有整段听力音轨，尚无经核验的逐题播放范围。")
        elif kind=="build_sentence":
            q["prompt"]="Make an appropriate sentence using the words and fixed fragments in the original question."
            if answer:q["answer"]=answer
        elif kind in {"email","academic_discussion"}:q["prompt"]="Read the original task and write your response."
        else:
            q["prompt"]="Listen and repeat once." if kind=="listen_repeat" else "Answer the interviewer."
            q["warnings"].append("只有整段口语音轨，尚无经核验的逐题播放范围。")
            if kind=="listen_repeat" and answer:q["transcript"]=answer
            q["responseSeconds"]=[8,8,10,10,10,12,12][number-1] if number<=7 else 45
            q["timingSource"]=source(material,page["page"])
            q["timingNote"]="与该资料整组截图中的初始作答倒计时一致。"
        if any(x["number"]==number for x in modules[mid]["questions"]):
            exam["warnings"].append(f"Duplicate question image at page {page['page']} omitted.")
        else:modules[mid]["questions"].append(q)
    return finalize_exam(exam)


def resource_exam(eid, materials, supplemental=False):
    fam,n=eid.rsplit("-",1)
    related=[m for m in materials if eid in m["examIds"]]
    titles={"student":"官方学生版样题","teacher":"官方教师版样题","paid":"付费练习题","essentials":"TOEFL Essentials 母题"}
    reasons={"student":"扫描题含任务组音轨；尚未完成题目和逐题音频边界校验，当前提供完整原始资料。","teacher":"官方资料未提供音频；当前提供题目、原文与答案原始 PDF。","paid":"扫描 PDF 部分题目直接附有答案；为避免模考时泄露答案，尚未开放未经完整校验的交互题。","essentials":"TOEFL Essentials 不是 TOEFL iBT 2026；仅作补充资料，不进入 iBT 模考。"}
    return {"schemaVersion":1,"id":eid,"title":f"{titles[fam]} {n}","family":fam,"resourcesOnly":True,"supplemental":supplemental,"strictEligible":False,"sourceMaterialIds":[m["id"] for m in related],"associatedMaterials":[{k:m[k] for k in ["id","name","url","kind"]} for m in related],"warnings":[reasons[fam]],"sections":[],"questionCount":0,"screenCount":0,"autoScorableCount":0}


def paid_mc(text,start,end):
    text=clean(text)
    text=re.sub(r'(?m)^(\d{1,2})[.]([A-Za-z])',r'\1. \2',text)
    text=re.sub(r'(?m)^Cc[.]\s*','C. ',text)
    text=re.sub(r"(?m)^\s*[‘'\"]?([ABCD])[.,]\s*_?\s*",lambda m:'('+m[1]+') ',text)
    text=re.sub(r'(?m)^\s*\d{1,2}\s*$','',text)
    return mc_questions(text,start,end)


def paid_exam(n,base,materials):
    eid=f'paid-{n}';exam=copy.deepcopy(base)
    edition=[m for m in materials if eid in m['examIds']]
    primary=next(m for m in edition if m['kind']=='pdf' and ('lower level 题目' in m['name'] if n==1 else '题目' in m['name']))
    upper=next((m for m in edition if m['kind']=='pdf' and '阅读&听力M2' in m['name']),primary)
    exam.update({'id':eid,'title':f'补充套题 {n}'+(' · lower / upper 双分支' if n==1 else ' · upper 路径'),'family':'paid','strictEligible':False,'primaryEditionMaterialIds':[m['id'] for m in edition],'sourceMaterialIds':list(dict.fromkeys(base['sourceMaterialIds']+[m['id'] for m in edition])),'warnings':['本资料与对应 Pack 存在重复题，保留原套编排并共享题库内容身份。','本资料参考答案存在冲突，已核对的修正及依据仅在复盘和资料校验中显示。'],'supportsAdaptive':n==1})
    for section in exam['sections']:
        for module in section['modules']:
            original_mid=module['id']
            if section['id'] in {'reading','listening'}:
                route='upper' if original_mid.endswith('m2') else 'common'
                module['route']=route
                if route=='upper':module['id']=original_mid+'-upper';module['title']+=' · Upper'
            for q in module['questions']:
                original=q['id'];q['canonicalQuestionId']=original;q['deduplicatedFrom']=original
                if section['id']=='reading':
                    branch='2-upper' if module['route']=='upper' else '1';q['id']=f'{eid}-r{branch}-'+('cloze-' if q['type']=='cloze' else '')+str(q['number'])
                elif section['id']=='listening':
                    branch='2-upper' if module['route']=='upper' else '1';q['id']=f'{eid}-l{branch}-{q["number"]}'
                elif q['type']=='build_sentence':q['id']=f'{eid}-w-build-{q["number"]}'
                elif section['id']=='writing':q['id']=f'{eid}-w-{q["type"]}'
                else:q['id']=f'{eid}-s-{q["type"]}-{q["number"] if q["type"]=="listen_repeat" else q["number"]-7}'
                q['source']['editionMaterialId']=(upper if module.get('route')=='upper' else primary)['id']
                q['source']['canonicalQuestionId']=original
                q['auditStatus']='equivalent-source-edition'
    if n==1:
        curated_path=ROOT/'scripts/verified_paid.json'
        if curated_path.exists():
            curated=json.loads(curated_path.read_text())
            exam['sections'][0]['modules'].append(copy.deepcopy(curated['lowerReading']))
            exam['sections'][1]['modules'].append(copy.deepcopy(curated['lowerListening']))
            exam['formQuestionCounts']={'lower':base['questionCount'],'upper':base['questionCount']}
        else:
            exam['supportsAdaptive']=False
            exam['unavailableBranches']=['lower']
            exam['warnings'].append('缺少本地分支题面校验文件，lower分支暂不可开始；原文件仍在资料库。')
    return finalize_exam(exam)


def normalize_words(text):
    return re.findall(r"[a-z]+(?:'[a-z]+)?",text.lower().replace('’',"'"))


def solve_word_blocks(question):
    """A validation oracle: consume the source slots/tokens to reproduce the key."""
    if not question.get("answer") or not question.get("slots"):return None
    target=normalize_words(question["answer"]);tokens=[normalize_words(t) for t in question.get("tokens",[])]
    def rec(si,ai,used):
        if si==len(question["slots"]):return [] if ai==len(target) else None
        slot=question["slots"][si]
        if "fixed" in slot:
            val=normalize_words(slot["fixed"])
            return rec(si+1,ai+len(val),used) if target[ai:ai+len(val)]==val else None
        for i,val in enumerate(tokens):
            if val and i not in used and target[ai:ai+len(val)]==val:
                tail=rec(si+1,ai+len(val),used|{i})
                if tail is not None:return [i]+tail
        return None
    return rec(0,0,set())


def enrich_questions(exams,materials):
    byid={m['id']:m for m in materials};cache={}
    required_files=['verified_paper.json','verified_blocks.json','verified_cloze.json','verified_paid.json','verified_choices.json','verified_editions.json','verified_structured_content.json','verified_structured_essentials.json']
    missing_verification=[name for name in required_files if not (ROOT/'scripts'/name).is_file()]
    changed_sources=[mid for mid,sha in _CURATION.get('sourceSha256ById',{}).items() if mid not in byid or byid[mid]['sha256']!=sha]
    overrides=json.loads((ROOT/'scripts/verified_blocks.json').read_text()) if (ROOT/'scripts/verified_blocks.json').exists() else {}
    cloze_file=ROOT/'scripts/verified_cloze.json'
    cloze_overrides={v['questionId']:v for v in json.loads(cloze_file.read_text()).get('questions',[])} if cloze_file.exists() else {}
    choice_path=ROOT/'scripts/verified_choices.json'
    choice_overrides=json.loads(choice_path.read_text()).get('questions',{}) if choice_path.exists() else {}
    edition_path=ROOT/'scripts/verified_editions.json'
    edition_data=json.loads(edition_path.read_text()) if edition_path.exists() else {}
    edition_overrides={v['questionId']:v for v in edition_data.get('questions',[])}
    source_key_records={v['questionId']:v for v in edition_data.get('sourceAnswerKeys',[])}
    media_path=OUT/'media-segments.json'
    segment_map={}
    if media_path.exists():
        for segment in json.loads(media_path.read_text()).get('segments',[]):
            for qid in segment.get('questionIds',[]):segment_map.setdefault(qid,[]).append(segment)
    for exam in exams:
        exam['associatedMaterials']=[{k:byid[mid][k] for k in ['id','name','url','kind']} for mid in exam['sourceMaterialIds'] if mid in byid]
        for section in exam['sections']:
            task_types=set()
            for module in section['modules']:
                for q in module['questions']:
                    q['source'].setdefault('originalNumber',q['number'])
                    q['source'].update({'moduleId':module['id'],'section':section['id']})
                    if q['source'].get('originalNumber') is None:q['source'].update({'originalNumberStatus':'not-printed','numberingNote':'原页未印此题独立编号；number为原题出现顺序的本地导航序号。'})
                    if exam['family'] in {'experience','student','teacher'} and (section['id']=='speaking' or q['type'] in {'email','academic_discussion'}):
                        q['source'].update({'originalNumber':None,'originalNumberStatus':'not-printed','numberingNote':'原纸版此任务未印独立题号，保留原顺序；本地number仅用于导航。'})
                    if q['id'] in edition_overrides:
                        record=edition_overrides[q['id']];q['editionSource']=copy.deepcopy(record['editionSource']);q['editionSource']['url']=byid[q['editionSource']['materialId']]['url']+f"#page={q['editionSource']['page']}";q['editionAudit']={k:v for k,v in record.items() if k not in {'questionId','canonicalSource','editionSource'}}
                    q.setdefault('auditStatus','parsed-with-source')
                    cloze_override=cloze_overrides.get(q['id']) or cloze_overrides.get(q.get('canonicalQuestionId',''))
                    if q['type']=='cloze' and cloze_override:
                        q['blanks']=copy.deepcopy(cloze_override['blanks']);q['passageTemplate']=cloze_override['passageTemplate'];q['clozeAudit']=copy.deepcopy(cloze_override.get('audit',{}))
                        q['answer']={b['id']:b['answer'] for b in q['blanks'] if b.get('answer') is not None}
                    choice_file=CACHE/'choice-columns'/f"{q.get('canonicalQuestionId',q['id'])}.json"
                    if q['type']=='choice' and (exam['family']=='pack' or q.get('canonicalQuestionId','').startswith('pack-')):
                        try:from scripts.extract_pack_choices import extract as extract_columns
                        except ModuleNotFoundError:from extract_pack_choices import extract as extract_columns
                        source_question=copy.deepcopy(q);source_question['id']=q.get('canonicalQuestionId',q['id']);extract_columns(source_question,section['id'],ROOT)
                    if q['type']=='choice' and choice_file.exists():
                        parsed=json.loads(choice_file.read_text())
                        if parsed.get('status')=='parsed-with-source-image':
                            q['prompt']=parsed['prompt'];q['choices']=parsed['choices'];q['choiceAuditStatus']='ocr-with-original-question-image'
                        else:q['choiceAuditStatus']='needs-review'
                    corrected_choice=choice_overrides.get(q.get('canonicalQuestionId',q['id']))
                    if corrected_choice:q.update({k:copy.deepcopy(v) for k,v in corrected_choice.items() if k!='evidence'})
                    if q.get('canonicalQuestionId',q['id'])=='pack-2-reading-m2-15':
                        special=_CURATION.get('specialQuestions',{}).get('pack-2-reading-m2-15')
                        if special:
                            q.update(copy.deepcopy(special))
                            q['warnings']=[w for w in q['warnings'] if '自动判分选项' not in w]
                        else:q['auditStatus']='missing-source-verification'
                    if q['type']=='choice' and section['id']=='reading' and not q.get('taskType'):
                        if exam['family']=='pack' or q.get('canonicalQuestionId','').startswith('pack-'):
                            mid=q['source']['materialId']
                            if mid not in cache:cache[mid]=json.loads((CACHE/f'{mid}.json').read_text())['pages']
                            txt=cache[mid][q['source']['page']-1]['text']
                            q['taskType']='daily_life' if re.search(r'Read\s+(?:an?\s+)?(?:email|e-mail|notice|text|social|advertisement)',txt,re.I) else 'academic_passage'
                        else:q['taskType']='daily_life' if q['number']<=15 else 'academic_passage'
                    else:q.setdefault('taskType',q['type'])
                    task_types.add(q['taskType'])
                    if q['type']=='cloze':
                        q['answerMode']='missing_letters'
                        for blank in q['blanks']:
                            blank.setdefault('givenLetters',blank.get('prefix',''))
                            blank.setdefault('missingLetters',blank.get('answer'))
                            blank.setdefault('fullWord',(blank.get('prefix','')+(blank.get('missingLetters') or '')) or None)
                            blank.setdefault('acceptedAnswers',[blank.get('missingLetters'),blank.get('fullWord')])
                            blank.setdefault('auditStatus','verified-prefix-source-image')
                            if blank.get('answerConflict',{}).get('status')=='needs-review':
                                blank.update({'answer':None,'fullWord':None,'missingLetters':None,'acceptedAnswers':[]})
                    block_override=overrides.get(q['id']) or overrides.get(q.get('canonicalQuestionId',''))
                    if block_override:
                        q.update({k:v for k,v in block_override.items() if k!='evidence'})
                    candidates=segment_map.get(q['id'],[])
                    good=[seg for seg in candidates if seg.get('verified') and seg.get('kind') in {'stimulus','prompt'} and not seg.get('containsResponseWait')]
                    if not good and q.get('canonicalQuestionId'):
                        canonical=segment_map.get(q['canonicalQuestionId'],[])
                        good=[seg for seg in canonical if seg.get('verified') and seg.get('kind') in {'stimulus','prompt'} and not seg.get('containsResponseWait')]
                        if len(good)==1:q['sourceOverride']={'kind':'equivalent-verified-audio','canonicalQuestionId':q['canonicalQuestionId'],'reason':'The matching Pack edition supplies a verified stimulus for this duplicate item.'}
                    if len(good)==1:
                        seg=good[0]
                        q['audio']={'url':seg['url'],'materialId':seg['sourceMaterialId'],'sourceUrl':seg['sourceUrl'],'sourceSha256':seg.get('sourceSha256'),'segmentId':seg['id'],'groupId':seg['groupId'],'scope':'group' if len(seg['questionIds'])>1 else 'item','durationSeconds':seg['durationSeconds'],'mediaType':'audio','startSeconds':seg['startSeconds'],'endSeconds':seg['endSeconds'],'verified':True,'containsResponseWait':False}
                        q['mediaAudit']={k:seg[k] for k in ['verificationMethod','humanReviewed','confidence','evidence'] if k in seg}
                        q['transcript']=seg.get('actualSourceTranscript') or seg.get('actualTranscript') or seg.get('text') or q.get('transcript','')
                        if seg.get('referenceMismatch'):
                            q['sourceVariants']={'referenceText':seg.get('referenceText'),'actualSourceTranscript':q['transcript'],'status':'audio-source-variant','segmentId':seg['id']}
                            q['warnings'].append('原声音轨与纸版转写存在措辞差异；完整原文与来源见复盘。')
                        q['warnings']=[w for w in q['warnings'] if not re.search(r'只有整段|Missing or ambiguous',w)]
                        cues=[c for c in candidates+segment_map.get(q.get('canonicalQuestionId',''),[]) if c.get('verified') and c.get('kind')=='cue' and c.get('groupId')==seg['groupId']]
                        if cues:
                            cue=cues[0];q['cueAudio']={k:cue[k] for k in ['url','durationSeconds','sourceMaterialId','sourceUrl','startSeconds','endSeconds','verified'] if k in cue};q['cueAudio'].update({'segmentId':cue['id'],'groupId':cue['groupId'],'scope':'cue'})
                            q['sourceDelayAfterPromptSeconds']=cue.get('sourceDelayAfterPromptSeconds',0)
                    elif candidates:
                        q['mediaAudit']={'status':'needs-review','candidates':[{'segmentId':s['id'],'warnings':s.get('warnings',[]),'text':s.get('text')} for s in candidates]}
                    q['sourcePromptAvailable']=True
                    if section['id'] in {'listening','speaking'} and not q.get('audio'):
                        if exam['family'] in {'teacher','student'} and q.get('transcript'):
                            original_prompt=q['prompt'];q['referenceOnly']=True;q['practiceMode']='text-only-source-study'
                            q['prompt']=q['transcript'] if section['id']=='speaking' or q.get('taskType')=='listen_response' else q['transcript']+'\n\n'+original_prompt
                            q['warnings'].append('本题没有与题本文字完全匹配的已核验原音；仅作不限时原文专项学习。')
                        else:
                            q['referenceOnly']=True;q['sourcePromptAvailable']=False
                            q['warnings'].append('当前缺少可对应到此题的完整刺激材料；保留在资料校验中，不作为可开始的练习题。')
                    if q['type']=='build_sentence' and q.get('slots'):
                        order=solve_word_blocks(q)
                        q['blockValidation']={'status':'passed' if order is not None else 'failed','slotCount':sum('id' in s for s in q['slots']),'tokenCount':len(q.get('tokens',[]))}
                        if order is not None:q['expectedTokenOrder']=order
                        else:q['warnings'].append('原题词块/固定词与参考答案尚未完全对齐，待审核。')
                    if q.get('answerConflict'):
                        conflict=q['answerConflict'];q.setdefault('sourceReferenceAnswer',conflict.get('provided'))
                        q['resolutionEvidence']={'kind':conflict.get('status'),'source':q['source'],'audioMaterialId':conflict.get('evidenceAudioMaterialId'),'summary':conflict.get('reason')}
                        q['answerOrigin']='source-reconciled' if str(conflict.get('status','')).startswith('resolved') else 'unresolved-source-conflict'
                    else:q.setdefault('answerOrigin','source-reference')
                    if q['id'] in source_key_records:
                        supplied=source_key_records[q['id']];q['editionReferenceAnswer']=supplied['answer'];q['editionAnswerSource']={k:v for k,v in supplied.items() if k!='questionId'}
                        if q.get('answer') is not None and supplied['answer']!=q['answer']:
                            q['answerConflict']={'provided':supplied['answer'],'resolvedAnswer':q['answer'],'status':'resolved-from-matching-original-sources','sourceAnswerPage':supplied['page'],'sourceAnswerMaterialId':supplied['materialId'],'reason':'The supplemental keyed letter disagrees with the matching complete original question. The retained answer is cross-checked against the original passage or the original recorded stimulus, with both sources preserved.'}
                            q['sourceReferenceAnswer']=supplied['answer'];q['answerOrigin']='source-reconciled';q['resolutionEvidence']={'source':q['source'],'editionSource':q.get('editionSource'),'audioMaterialId':q.get('audio',{}).get('materialId'),'transcript':q.get('transcript'),'canonicalQuestionId':q.get('canonicalQuestionId'),'summary':q['answerConflict']['reason']}
            section['taskTypes']=sorted(task_types)
        exam['scopedEligibility']={s['id']:exam['family']=='experience' for s in exam['sections']}
        if exam['family'] in {'student','teacher'}:
            exam['scopedEligibility']['reading']=sum(len(q.get('blanks',[])) if q['type']=='cloze' else 1 for m in exam['sections'][0]['modules'] for q in m['questions'])==40
        if exam['family'] in {'pack','paid'}:
            reading=next(s for s in exam['sections'] if s['id']=='reading')
            exam['scopedEligibility']['reading']=all((q['type']!='choice' or q.get('choiceAuditStatus') in {'ocr-with-original-question-image','verified-source-paragraph-sentences'} or (q['id'].startswith('paid-1-r2-lower') and bool(q.get('choices')))) and (q['type']!='cloze' or all(b.get('prefixVerified') or str(b.get('auditStatus','')).startswith('verified') for b in q['blanks'])) for m in reading['modules'] for q in m['questions'])
        writing=next((s for s in exam['sections'] if s['id']=='writing'),None)
        if writing:
            builds=[q for m in writing['modules'] for q in m['questions'] if q['type']=='build_sentence']
            exam['scopedEligibility']['writing']=len(builds)==10 and all(q.get('blockValidation',{}).get('status')=='passed' and q.get('slotAuditStatus')=='verified-source-image' for q in builds)
        for sid in ['listening','speaking']:
            sec=next((s for s in exam['sections'] if s['id']==sid),None)
            if sec and exam['family'] in {'student','pack','paid'}:
                qs=[q for m in sec['modules'] for q in m['questions']]
                exam['scopedEligibility'][sid]=bool(qs) and all(q.get('audio',{}).get('verified') for q in qs)
        exam['verificationInputs']={'missingFiles':missing_verification,'changedSourceMaterialIds':changed_sources,'sourceHashStatus':'passed' if _CURATION and not changed_sources else 'unverified'}
        if missing_verification or changed_sources or not _CURATION:
            exam['scopedEligibility']={key:False for key in exam['scopedEligibility']}
            exam['strictEligible']=False
            exam['warnings'].append('缺少题库人工校验文件或原资料内容已改变，严格资格已关闭。恢复本地校验文件后重新导入，或重新核对源资料。')
        exam['interactiveQuestionCount']=sum((len(q['blanks']) if q['type']=='cloze' else 1) for s in exam['sections'] for m in s['modules'] for q in m['questions'] if q.get('sourcePromptAvailable'))


def audit_import(materials,exams):
    from urllib.parse import unquote
    by_id={m["id"]:m for m in materials};failures=[];checked_assets=set();checked_audio=set();checks=[]
    for exam in exams:
        issues=[];ids=set();objective=0;audio_count=0;module_checks=[]
        for section in exam["sections"]:
            for module in section["modules"]:
                item_count=0
                for q in module["questions"]:
                    if q["id"] in ids:issues.append("duplicate question id "+q["id"])
                    ids.add(q["id"])
                    item_count+=len(q["blanks"]) if q["type"]=="cloze" else 1
                    if q["type"] in {"choice","cloze","build_sentence"}:
                        objective+=len(q["blanks"]) if q["type"]=="cloze" else 1
                    if q["type"]=='build_sentence' and q.get('blockValidation',{}).get('status')=='failed':issues.append('word-block alignment failed '+q['id'])
                    if q["type"]=="choice" and (len(q.get("choices",[]))<2 if exam.get('supplemental') else len(q.get("choices",[]))!=4):issues.append("choice count "+q["id"])
                    if q["type"]=="cloze" and set(q.get("answer",{}))!={b['id'] for b in q['blanks'] if b.get('answer') is not None}:issues.append("cloze answer mapping differs from known source answers "+q["id"])
                    if q["source"]["materialId"] not in by_id:issues.append("unknown source "+q["id"])
                    if q.get('presentationSchema'):
                        from backend.presentation import validate_question
                        issues.extend(f"{code} {q['id']}" for code in validate_question(q,strict=True))
                        contaminated=next((block.get('text','') for block in q.get('stemBlocks',[]) if block.get('type')=='question' and re.match(r'^\s*\d+\s+(?:email|notice|passage|chat|article)\s*[.:]?(?:\s|$)',block.get('text',''),re.I)),None)
                        if contaminated is not None:issues.append('source page-header fragment in structured question '+q['id'])
                        displayed_questions=[block.get('text') for block in q.get('stemBlocks',[]) if block.get('type')=='question']
                        if displayed_questions and displayed_questions!=[q.get('prompt')]:issues.append('structured question block differs from prompt '+q['id'])
                    for asset in q.get("assets",[]):
                        checked_assets.add(asset["url"])
                        p=ASSETS/asset["url"].removeprefix("/assets/")
                        if not p.is_file() or not p.stat().st_size:issues.append("missing asset "+asset["url"])
                    for asset in q.get('sourceEvidenceAssets',[]):
                        checked_assets.add(asset['url'])
                        p=ASSETS/asset['url'].removeprefix('/assets/')
                        if not p.is_file() or not p.stat().st_size:issues.append('missing source evidence asset '+asset['url'])
                    audio=q.get("audio")
                    if audio:
                        audio_count+=1;checked_audio.add(audio["url"])
                        p=ASSETS/unquote(audio['url'].removeprefix('/assets/')) if audio['url'].startswith('/assets/') else DATA/unquote(audio["url"].removeprefix("/materials/"))
                        if not p.is_file() or not p.stat().st_size:issues.append("missing audio "+audio["url"])
                        if audio["materialId"] not in by_id or by_id[audio["materialId"]]["url"]!=audio.get('sourceUrl',audio["url"]):issues.append("mismatched audio material "+q["id"])
                    elif section["id"] in {"listening","speaking"} and q['type']!='read_aloud':issues.append("no verified item audio "+q["id"])
                if module.get("expectedItemCount") and item_count!=module["expectedItemCount"]:issues.append(f"{module['id']} count {item_count} != {module['expectedItemCount']}")
                module_checks.append({'moduleId':module['id'],'route':module.get('route','common'),'expectedItems':module.get('expectedItemCount',item_count),'actualItems':item_count,'screens':len(module['questions']),'blankUnits':sum(len(q.get('blanks',[])) for q in module['questions'])})
        if exam["family"]=="experience":
            if exam["questionCount"]!=97:issues.append("Expected 97 source items")
            if audio_count!=45:issues.append("Expected audio mapping on 34 Listening + 11 Speaking items")
            if objective!=84:issues.append("Expected 84 objective source answers")
            if not all(exam.get('scopedEligibility',{}).values()):issues.append('one or more section scopes did not pass validation')
            exam["strictEligible"]=not issues
            exam["validation"]={"status":"passed" if not issues else "failed","expectedItems":97,"verifiedAudioItems":audio_count,"objectiveAnswers":objective,"answerKeyVerification":"reading/listening/build keys transcribed and visually checked against supplied answer-key pages","audioMappingVerification":"exact set/module/item-or-question-range filenames; source durations read locally","scope":"local timed simulation; not an ETS-certified replica"}
            if issues:failures.extend([exam["id"]+": "+i for i in issues])
        else:
            exam['strictEligible']=not exam.get('supplemental') and bool(exam.get('scopedEligibility')) and all(exam.get('scopedEligibility',{}).values()) and not issues
            exam["validation"]={"status":"passed-local-timed-materials" if exam['strictEligible'] else "resources-only" if exam.get("resourcesOnly") else "guided-practice-only","issues":issues,"scope":"source material/timing eligibility is separate from complete automatic scoring"}
        checks.append({"examId":exam["id"],"resourcesOnly":exam.get("resourcesOnly",False),"strictEligible":exam["strictEligible"],"scopedEligibility":exam.get('scopedEligibility',{}),"questionCount":exam["questionCount"],"screenCount":exam["screenCount"],"autoScorableCount":exam["autoScorableCount"],'unscoredCount':exam.get('unscoredCount',0),'autoScoringComplete':exam.get('autoScoringComplete',False),"audioMappedItems":audio_count,'modules':module_checks,"issues":issues})
    disk_files={p.relative_to(DATA).as_posix() for p in DATA.rglob("*") if p.is_file() and p.relative_to(DATA).parts[0] != 'user-packs' and not any(x.startswith(".") for x in p.relative_to(DATA).parts)}
    inventory_files={m["path"] for m in materials}
    if disk_files!=inventory_files:failures.append("catalogue coverage differs from filesystem")
    report={"schemaVersion":1,"status":"passed" if not failures else "failed","cataloguedFileCount":len(materials),"filesystemFileCount":len(disk_files),"allNonHiddenFilesCatalogued":disk_files==inventory_files,"assetUrlsVerified":len(checked_assets),"audioUrlsVerified":len(checked_audio),"ibtCollectionCount":sum(not e.get('supplemental') for e in exams),"essentialsCollectionCount":sum(bool(e.get('supplemental')) for e in exams),"strictLocalSimulationCount":sum(e["strictEligible"] for e in exams),"guidedPracticeCount":sum(not e["strictEligible"] and not e.get("resourcesOnly") and not e.get('supplemental') for e in exams),"resourcesOnlyCount":sum(bool(e.get("resourcesOnly")) for e in exams),"failures":failures,"exams":checks}
    return report


def question_bank(exams, publish=True):
    """Deduplicate content, preserving every exam occurrence and source edition."""
    registry={};by_question={};source_cache={};conflicts=[]
    for exam in exams:
        for section in exam['sections']:
            for module in section['modules']:
                for q in module['questions']:
                    canonical=q.get('canonicalQuestionId')
                    if canonical and canonical in by_question:content_id=by_question[canonical]
                    elif q.get('curatedContentId'):content_id=q['curatedContentId']
                    else:
                        if q.get('presentationSchema')=='structured-v1':
                            display_keys=['prompt','passage','passageTemplate','context','choices','tokens','slots','stemBlocks']
                            if section['id'] in {'listening','speaking'}:display_keys.append('transcript')
                            body=json.dumps({k:q.get(k) for k in display_keys},ensure_ascii=False,sort_keys=True)
                        elif q.get('choices') and all(c['text'].startswith('Option ') for c in q['choices']) or exam['family']=='pack' or q['type']=='cloze' or q.get('sourceImageAuthoritative'):
                            mid=q['source']['materialId']
                            if mid not in source_cache:source_cache[mid]=json.loads((CACHE/f'{mid}.json').read_text())['pages']
                            raw=source_cache[mid][q['source']['page']-1]['text']
                            raw='\n'.join(line for line in raw.splitlines() if not re.search(r'toefl|RADA|DIME|Volume|Hide Time|Help @|Review|^Reading\s*\||^Listening\s*\||^Speaking\s*\||^Writing\s*\|',line,re.I))
                            body=raw
                            if section['id'] in {'listening','speaking'}:body+=' '+q.get('transcript','')
                            if q.get('sourceImageAuthoritative'):
                                body+=' '+','.join(hashlib.sha256((ASSETS/a['url'].removeprefix('/assets/')).read_bytes()).hexdigest() for a in q.get('assets',[]))
                        else:
                            body=' '.join([q.get('passageTemplate',''),q.get('passage',''),q.get('prompt',''),q.get('transcript','') if section['id'] in {'listening','speaking'} else '']+[c['text'] for c in q.get('choices',[])]+q.get('tokens',[]))
                            if q['type']=='cloze':body+=' '+json.dumps([(b.get('prefix'),b.get('suffix'),b.get('length')) for b in q['blanks']])
                        normalized=' '.join(normalize_words(body))
                        content_id='qcontent-'+hashlib.sha256((q['taskType']+'|'+normalized).encode()).hexdigest()[:20]
                    q['contentId']=content_id;by_question[q['id']]=content_id
                    instance={'questionId':q['id'],'examId':exam['id'],'section':section['id'],'moduleId':module['id'],'route':module.get('route','common'),'number':q['number'],'numberEnd':q.get('numberEnd'),'source':q['source']}
                    if content_id not in registry:registry[content_id]={'id':content_id,'taskType':q['taskType'],'canonicalQuestionId':q['id'],'question':q,'instances':[]}
                    registry[content_id]['instances'].append(instance)
                    if q.get('answerConflict'):conflicts.append({'questionId':q['id'],'contentId':content_id,'source':q['source'],'conflict':q['answerConflict']})
                    for blank in q.get('blanks',[]):
                        if blank.get('answerConflict'):conflicts.append({'questionId':q['id'],'blankId':blank['id'],'contentId':content_id,'source':q['source'],'conflict':blank['answerConflict']})
    units=lambda q:len(q['blanks']) if q['type']=='cloze' else 1
    stats={'questionOccurrences':len(by_question),'uniqueQuestionScreens':len(registry),'duplicateOccurrences':len(by_question)-len(registry),'itemOccurrences':sum(units(q) for e in exams for s in e['sections'] for m in s['modules'] for q in m['questions']),'uniqueItems':sum(units(v['question']) for v in registry.values()),'contentGroupsWithDuplicates':sum(len(v['instances'])>1 for v in registry.values()),'answerConflictOccurrences':len(conflicts),'unresolvedAnswerConflictOccurrences':sum(c['conflict'].get('status')=='needs-review' for c in conflicts)}
    if publish:
        dump(OUT/'question-bank.json',{'schemaVersion':1,'stats':stats,'questions':list(registry.values())})
        dump(OUT/'deduplication.json',{'schemaVersion':1,'method':'normalized content hash plus manually verified equivalent Pack/paid edition aliases','stats':stats,'duplicates':[{'contentId':v['id'],'canonicalQuestionId':v['canonicalQuestionId'],'instances':v['instances']} for v in registry.values() if len(v['instances'])>1],'answerConflicts':conflicts})
    return stats


def runtime_verification_manifests(exams):
    """Freeze verification-file and referenced derived-asset hashes for runtime gates.

    This only adds exam-level metadata. No question, answer, timing, or source
    file is rewritten by this function.
    """
    from urllib.parse import unquote, urlsplit
    names=['verified_paper.json','verified_blocks.json','verified_cloze.json','verified_paid.json','verified_choices.json','verified_editions.json','verified_structured_content.json','verified_structured_essentials.json','verified_text_corrections.json']
    curation={f'scripts/{name}':hashlib.sha256((ROOT/'scripts'/name).read_bytes()).hexdigest() for name in names if (ROOT/'scripts'/name).is_file()}
    curation_files = set(curation)
    asset_cache={}
    def urls(value):
        if isinstance(value,dict):
            candidate=value.get('url')
            if isinstance(candidate,str) and candidate.startswith('/assets/'):yield candidate
            for child in value.values():yield from urls(child)
        elif isinstance(value,list):
            for child in value:yield from urls(child)
    for exam in exams:
        expected={}
        for url in sorted(set(urls(exam.get('sections',[])))):
            if url not in asset_cache:
                relative=unquote(urlsplit(url).path.removeprefix('/assets/'))
                path=(ASSETS/relative).resolve()
                if not path.is_relative_to(ASSETS.resolve()) or not path.is_file():continue
                asset_cache[url]=hashlib.sha256(path.read_bytes()).hexdigest()
            if url in asset_cache:expected[url]=asset_cache[url]
        inputs=exam.setdefault('verificationInputs',{})
        inputs['curationSha256ByPath']=dict(curation)
        teacher_manifest = ROOT / 'scripts/verified_teacher_audio.json'
        if exam.get('id') in {'teacher-1', 'teacher-2'} and teacher_manifest.is_file() and any(
                q.get('mediaAudit', {}).get('officialArchiveUrl')
                for section in exam.get('sections', []) for module in section.get('modules', []) for q in module.get('questions', [])):
            inputs['curationSha256ByPath']['scripts/verified_teacher_audio.json'] = hashlib.sha256(teacher_manifest.read_bytes()).hexdigest()
            curation_files.add('scripts/verified_teacher_audio.json')
        pack_directions_manifest = ROOT / 'scripts/verified_pack_directions.json'
        if pack_directions_manifest.is_file() and any(
                module.get('directionsAudit', {}).get('manifest') == 'scripts/verified_pack_directions.json'
                for section in exam.get('sections', []) for module in section.get('modules', [])):
            inputs['curationSha256ByPath']['scripts/verified_pack_directions.json'] = hashlib.sha256(pack_directions_manifest.read_bytes()).hexdigest()
            curation_files.add('scripts/verified_pack_directions.json')
        inputs['assetSha256ByUrl']=expected
        from backend.presentation import content_digest
        inputs['structuredContentSha256ByQuestionId']={q['id']:content_digest(q) for section in exam.get('sections',[]) for module in section.get('modules',[]) for q in module.get('questions',[]) if q.get('presentationSchema')=='structured-v1'}
    return {'curationFiles':len(curation_files),'derivedAssets':len(asset_cache)}


def exam_summary(exam):
    return {k:v for k,v in exam.items() if k!="sections"} | {"sections":[{"id":s["id"],"title":s["title"],"taskTypes":s.get("taskTypes",[]),"modules":len(s["modules"]),"questionCount":sum(len(q.get("blanks",[])) if q["type"]=="cloze" else 1 for m in s["modules"] for q in m["questions"])} for s in exam["sections"]]}


def reconcile_final_warnings(exams):
    """Replace import-phase notices with final evidence, without touching questions.

    Call only after media enrichment and capability/scoring audit. Exact obsolete
    messages are removed; unrelated source, numbering and verification warnings
    survive. The public warnings contain counts/status, never reference answers.
    """
    obsolete={
        '组音轨正在按逐题边界校验；未完成校验前仅开放引导练习。',
        '听力和口语只有整段音轨，未核验逐题切分；不支持完整严格模考。可交互练习阅读/写作，整段音轨请在资料库学习。',
        '使用原题截图；补字答案来自参考答案的完整单词，按完整词输入。',
        '整段学习音轨仅手动播放；未核验的口语原声题保留为参考，不计入交互题数。',
        '扫描题经过本地 OCR；补字题与组句题保留原页裁图。',
        '扫描题以真实裁图为准；选择题按原图选项顺序输入，不用生成文字替代无法核实的扫描内容。',
    }
    completed_media='原始整轨已通过本地ASR、原文与声学边界自动交叉校验，播放切片不包含原录音作答等待；并非ETS认证切片。'
    changed=[]
    for exam in exams:
        before=list(exam.get('warnings',[]))
        warnings=[w for w in before if w not in obsolete]
        questions=[q for section in exam.get('sections',[]) for module in section.get('modules',[]) for q in module.get('questions',[])]
        media_questions=[q for section in exam.get('sections',[]) if section['id'] in {'listening','speaking'} for module in section.get('modules',[]) for q in module.get('questions',[]) if q['type']!='read_aloud']
        missing_media=[q for q in media_questions if not q.get('audio',{}).get('verified')]
        if exam.get('family')=='pack':
            warnings.append('缺字题已按原图给定字母和空格长度结构化；只输入缺失字母，原图可复核。无法确定唯一答案的空不计入核分。')
        if exam.get('family') in {'student','pack'}:
            if media_questions and not missing_media:
                warnings.append(completed_media)
            elif exam.get('id')=='student-1' and {q['id'] for q in missing_media}=={'student-1-s-interview-1'}:
                warnings.append('除采访第1题纸面与原音版本不符外，其余听说原音已完成核验；该题仅供不限时原文学习，完整严格模考与口语严格专项不可用。阅读、听力和写作的严格计时资格以当前资料完整性检查为准。')
            elif missing_media:
                warnings.append(f'听说任务中仍有{len(missing_media)}道题缺少与题面匹配且核验通过的原音；相关范围不能用于严格计时，仅按原资料可用程度提供不限时学习。')
        if exam.get('family')=='essentials':
            if media_questions and not missing_media:
                warnings.append('已核验的听力题与口语原声提示提供分题或题组音频；完整学习音轨另作手动参考。所有任务采用不限时补充练习，朗读题直接使用原纸面文字。')
            else:
                warnings.append('已核验题目提供对应原声片段；尚未核验的整段学习音轨仅作手动参考。所有任务采用不限时补充练习，朗读题直接使用原纸面文字。')
            excluded=[item for section in exam.get('sections',[]) for item in section.get('excludedTasks',[])]
            if excluded:
                warnings.append(f'原资料缺少{len(excluded)}道口语题的可核验原声提示，已保留出处并列入排除项，不计入交互题数，也不生成替代问题。')
        if exam.get('unscoredCount',0):
            warnings.append(f"本套有{exam['unscoredCount']}个客观题计分单元无法从原资料确定唯一答案，已排除自动判分；答案争议与题面、音频的计时资格分别核验。")
        overridden=sum(bool(q.get('sourceOverride')) for q in questions)
        if overridden:
            warnings.append(f'本套{overridden}道题采用所给资料另一版本中已核验的同题原声；对应关系和源音差异保留在复盘中，不使用合成音频。')
        if any(q.get('sourceVariants') for q in questions):
                warnings.append('部分原声与所给纸版转写存在措辞差异，保留完整原声；两种来源的差异在复盘中说明。')
        if exam.get('family') in {'experience','student','teacher'}:
            warnings.append('扫描题面已按原页核对并结构化；原裁图仅在复盘中作为来源证据。')
        if exam.get('family')=='essentials':
            warnings.append('题面已按原PDF逐页核对并结构化；原整题图仅供复盘核对，题意所需照片和场景使用原PDF高清裁图。')
        exam['warnings']=list(dict.fromkeys(warnings))
        if before!=exam['warnings']:changed.append(exam['id'])
    return {'schemaVersion':1,'status':'reconciled-after-media-and-capability-audit','changedExamIds':changed,'questionsModified':False,'referenceAnswersInPublicNotices':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ocr-all",action="store_true",help="OCR all scanned iBT question PDFs, retaining original page assets")
    parser.add_argument("--jobs",type=int,default=6)
    args=parser.parse_args()
    # This importer knows one private collection layout. Fail before modifying
    # generated outputs when invoked from a public checkout or partial backup.
    required_manifests = ['cloze', 'choices', 'paid', 'paper', 'editions', 'blocks',
                          'structured_content', 'structured_essentials', 'teacher_audio', 'pack_directions', 'text_corrections']
    missing = [name for name in required_manifests if not (ROOT / 'scripts' / f'verified_{name}.json').is_file()]
    if not DATA.is_dir() or missing:
        parser.error('The private PDF collection and matching verified_*.json files are required. '
                     'New users: run npm run demo or npm run import:pack -- /path/to/pack.json. '
                     '需要原始私有 PDF 资料及校对清单；新用户请使用演示或通用资源包。')
    OUT.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True)
    materials=inventory(); exams=[]
    for n in [1,2,3]:
        m=next(m for m in materials if m["category"]=="experience" and m["kind"]=="pdf" and f"experience-{n}" in m["examIds"])
        pages=prepare_pdf(m,args.jobs)
        exam=experience_exam(n,m,pages,materials)
        exams.append(exam)
    if args.ocr_all:
        for m in materials:
            if m["kind"]=="pdf" and m.get("scanned"): prepare_pdf(m,args.jobs)
    for n in range(1,7):
        m=next(m for m in materials if m["category"]=="pack" and m["kind"]=="pdf" and m["name"].startswith("2026") and f"pack-{n}" in m["examIds"])
        pages=prepare_pdf(m,args.jobs)
        exam=pack_exam(n,m,pages,materials)
        exams.append(exam)
    for fam in ["student","teacher"]:
        for n in [1,2]:
            m=next(m for m in materials if m["category"]==fam and m["kind"]=="pdf" and m.get("scanned") and f"{fam}-{n}" in m["examIds"])
            pages=prepare_pdf(m,args.jobs)
            exam=experience_exam(n,m,pages,materials,config=PAPER[(fam,n)],exam_id=f"{fam}-{n}")
            if fam=="teacher":exam["warnings"].append("官方教师资料没有音频：听力、口语仅用于阅读原文和专项练习，不可完整严格模考。")
            exams.append(exam)
    for n in [1,2]:
        for material in materials:
            if material['kind']=='pdf' and f'paid-{n}' in material['examIds']:prepare_pdf(material,args.jobs)
        exams.append(paid_exam(n,next(e for e in exams if e['id']==f'pack-{n}'),materials))
    try:
        from scripts.import_essentials import build_essentials
        from scripts.attach_source_explanations import attach as attach_explanations
        from scripts.structure_questions import apply as apply_structured_presentations
        from scripts.extract_structured_visuals import build as build_structured_visuals
        from scripts.attach_teacher_audio import attach as attach_teacher_audio
        from scripts.teacher_audio_presentation import finalize as finalize_teacher_audio
        from scripts.attach_pack_directions import attach as attach_pack_directions
    except ModuleNotFoundError:
        from import_essentials import build_essentials
        from attach_source_explanations import attach as attach_explanations
        from structure_questions import apply as apply_structured_presentations
        from extract_structured_visuals import build as build_structured_visuals
        from attach_teacher_audio import attach as attach_teacher_audio
        from teacher_audio_presentation import finalize as finalize_teacher_audio
        from attach_pack_directions import attach as attach_pack_directions
    supplemental=build_essentials(materials,jobs=args.jobs,publish=False)
    enrich_questions(exams,materials)
    explanation_stats=attach_explanations(exams,materials,ROOT)
    for exam in exams+supplemental:finalize_exam(exam)
    # Establish the source-content identity before applying separately curated
    # presentation blocks. The curation record must match this identity, so a
    # changed PDF/OCR/question cannot silently inherit an older structured stem.
    question_bank(exams+supplemental,publish=False)
    structured_visual_stats=build_structured_visuals(ROOT,materials)
    structured_stats=apply_structured_presentations(exams+supplemental,materials,ROOT)
    teacher_audio_stats=attach_teacher_audio(exams,materials,ROOT)
    teacher_audio_stats['presentation']=finalize_teacher_audio(exams)
    pack_directions_stats=attach_pack_directions(exams,materials,ROOT)
    for exam in exams:finalize_exam(exam)
    from backend.text_corrections import apply_import_corrections
    text_correction_stats=apply_import_corrections(exams+supplemental,materials,ROOT)
    runtime_hash_stats=runtime_verification_manifests(exams+supplemental)
    bank_stats=question_bank(exams+supplemental)
    audit=audit_import(materials,exams+supplemental)
    audit['warningFinalization']=reconcile_final_warnings(exams+supplemental)
    audit['sourceExplanations']=explanation_stats
    audit['runtimeVerificationHashes']=runtime_hash_stats
    audit['structuredPresentations']=structured_stats
    audit['structuredVisuals']=structured_visual_stats
    audit['teacherAudio']=teacher_audio_stats
    audit['packDirections']=pack_directions_stats
    audit['textCorrections']=text_correction_stats
    for material in materials:
        cached=CACHE/f"{material['id']}.json"
        if material['kind']=='pdf' and cached.exists():
            extraction=json.loads(cached.read_text())
            material['extraction']=extraction['method'];material['extractedPageCount']=len(extraction['pages']);material['extractedTextCharacters']=sum(len(p.get('text','')) for p in extraction['pages'])
    audit['extraction']={'pdfFilesExtracted':sum(bool(m.get('extractedPageCount')) for m in materials),'pdfPagesExtracted':sum(m.get('extractedPageCount',0) for m in materials),'ocrPagesExtracted':sum(m.get('extractedPageCount',0) for m in materials if m.get('extraction','').endswith('ocr'))}
    for exam in exams+supplemental:dump(OUT/"exams"/f"{exam['id']}.json",exam)
    dump(OUT/"audit.json",audit)
    excluded=[{'path':p.relative_to(DATA).as_posix(),'bytes':p.stat().st_size,'reason':'hidden operating-system metadata; inventoried but not imported as study content'} for p in sorted(DATA.rglob('*')) if p.is_file() and p.relative_to(DATA).parts[0] != 'user-packs' and any(part.startswith('.') for part in p.relative_to(DATA).parts)]
    audit.update({'allFileCount':len(materials)+len(excluded),'excludedSystemFileCount':len(excluded),'pdfPageCount':sum(m.get('pages',0) for m in materials),'scannedPageCount':sum(m.get('pages',0) for m in materials if m.get('scanned')),'questionBank':bank_stats})
    dump(OUT/"audit.json",audit)
    catalog={"schemaVersion":1,"generatedAt":datetime.now().astimezone().isoformat(timespec="seconds"),"sourceRoot":"data","stats":{"fileCount":len(materials)+len(excluded),"materialFileCount":len(materials),"excludedSystemFileCount":len(excluded),"pdfCount":sum(m["kind"]=="pdf" for m in materials),"pdfPageCount":sum(m.get('pages',0) for m in materials),"scannedPageCount":sum(m.get('pages',0) for m in materials if m.get('scanned')),"audioCount":sum(m["kind"]=="audio" for m in materials),"videoCount":sum(m["kind"]=="video" for m in materials),"totalBytes":sum(m["bytes"] for m in materials),"ibtExamCount":len(exams),"supplementalExamCount":len(supplemental),"interactiveExamCount":sum(not e.get("resourcesOnly") for e in exams),"strictExamCount":sum(e["strictEligible"] for e in exams),"questionCount":sum(e["questionCount"] for e in exams+supplemental),"ibtQuestionCount":sum(e["questionCount"] for e in exams),"supplementalQuestionCount":sum(e["questionCount"] for e in supplemental),"uniqueQuestionCount":bank_stats['uniqueItems']},"materials":materials,"excludedSystemFiles":excluded,"exams":[exam_summary(e) for e in exams],"supplementalExams":[exam_summary(e) for e in supplemental]}
    dump(OUT/"catalog.json",catalog)
    try:
        from scripts.extract_exam_ui import build as build_exam_ui
    except ModuleNotFoundError:
        from extract_exam_ui import build as build_exam_ui
    build_exam_ui(ROOT, materials)
    print(json.dumps(catalog["stats"],ensure_ascii=False),flush=True)


if __name__=="__main__":main()
