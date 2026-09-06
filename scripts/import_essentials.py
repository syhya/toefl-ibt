#!/usr/bin/env python3
"""Import the user's three Essentials practice sets as untimed supplements.

No generated questions: source-image questions are authoritative when a scan
does not support exact structured transcription. Sample-response/annotation
screens are not counted as additional questions or exposed in task crops.
"""
from __future__ import annotations

import argparse
import copy
import importlib
import json
import os
import re
import subprocess
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def helpers():
    try:
        return importlib.import_module("scripts.import_materials")
    except ModuleNotFoundError:
        return importlib.import_module("import_materials")


LISTENING_PAGES = {
    1: list(range(1, 31)),
    2: [1, 2, 3, 4, 5, 7, 8, 10, 11, 13, 14, 16, 17, 18, 19, 20, 21, 22, 23, 24,
        26, 27, 29, 30, 32, 33, 35, 36, 37, 38],
    3: list(range(1, 31)),
}
SPEAKING_READ_PAGES = [1, 3, 5, 7, 9, 11]
SPEAKING_PROMPT_PAGES = {**{7 + i: [14 + i * 2, 15 + i * 2] for i in range(8)},
                         **{15 + i: [31 + i * 2, 32 + i * 2] for i in range(5)}}

# These are measured ranges in the exact supplied audio hashes, independently
# checked against the PDF question/sample sequence and an isolated local ASR pass.
# They contain the original prompt only, never either sample response.
SPEECH_SOURCES = {
    1: ("mat-d2d809e63d57", "8ad9a579039276faf498aa95c4b14b149651f09c30f5a371a6687e62da59bca2"),
    2: ("mat-b46373fccd8e", "4f438d34714dd430ce63e57e1581b3bc8fcb320b16024113b1d9277594e66d4c"),
    3: ("mat-966103cca85a", "feff11b5d1cd4bed126bb9c20fd3264bd69aadff6da6a6d7f52461042e8626e9"),
}
SPEECH_RANGES = {
    1: {7:[(342.04,344.6)],8:[(363.44,366.47)],9:[(383.62,387.24)],10:[(416,419.83)],11:[(442.86,447.13)],12:[(474.64,479.52)],13:[(503.62,508.94)],14:[(542.54,547.47)],15:[(597.52,608.99)],16:[(651.74,661.7)],17:[(746.88,755.44)],18:[(830.75,843.23)],19:[(938.4,961.46)]},
    2: {7:[(315.3,317.43)],8:[(330.9,333.49)],9:[(351.21,354.99)],10:[(375.77,380.12)],11:[(406.57,410.55)],12:[(432.57,436.83)],13:[(461.72,467.27)],15:[(519.4,533.04)],16:[(595.86,600.63)],18:[(693.91,706.2)],19:[(790.41,797.49),(811.02,812.09),(815.92,827.24)]},
    3: {7:[(381.95,385.1)],8:[(403.57,407.78)],9:[(427.44,431.53)],10:[(451.62,456.17)],11:[(480.9,485.89)],12:[(514.43,519.5)],13:[(544.2,549.94)],14:[(579.01,585.86)],15:[(632.81,649.69)],16:[(724.95,730.45)],17:[(841.82,850.85)],18:[(958.22,969.74)],19:[(1072.12,1082.42)]},
}
SPEECH_MISSING = {
    14: "原PDF第28–29页点评提及thoughts；原轨第487.04秒的Q13范例结束后，仅有静音，503.24秒直接进入采访说明，未录入Q14原声或范例。",
    17: "原PDF第35–36页点评明确是robot题；原轨684.11秒Q16手机用途范例结束后，693.91秒直接进入Q18纸书/屏幕阅读问题，未录入机器人题。",
}
LISTENING_SOURCES = {
    1: ("mat-a64fba4214fb", "1e0f2e60ec6726f35033f581b4683049a731e7d430e93a7d27dee4e2012f636f"),
    2: ("mat-89bd8bd068f2", "222f2d52e3f59c46f519a06f4042b828652e97dd980bf7b56dbb607e1911b23a"),
    3: ("mat-3ace5b868400", "ef5d91c2a21a126beeb40c5e796e01bfa977cf85ccc05733ca3cc06611f501dc"),
}
# first question, last question, measured source start, measured source end.
LISTENING_RANGES = {
    1: [[1,1,13.3,15.38],[2,2,24.21,26.37],[3,3,32.73,35.26],[4,4,44.9,47.79],[5,5,52.64,54.49],[6,7,67.86,87.88],[8,9,110.7,126.6],[10,11,142.53,176.36],[12,15,195.41,280.61],[16,16,320.38,321.96],[17,17,330.38,332.57],[18,18,339.2,342.23],[19,19,350.18,352.26],[20,20,359.17,361.49],[21,22,371.86,399.0],[23,24,430.98,462.21],[25,26,491.89,525.14],[27,30,598.12,693.93]],
    2: [[1,1,2.52,5.08],[2,2,19.65,21.09],[3,3,35.02,37.47],[4,4,52.04,54.81],[5,5,69.39,71.46],[6,7,88.29,101.93],[8,9,137.58,154.93],[10,11,198.78,228.79],[12,15,263.93,366.94],[16,16,505.07,507.74],[17,17,516.69,519.32],[18,18,558.09,560.53],[19,19,572.53,574.68],[20,20,583.87,586.16],[21,22,604.86,636.52],[23,24,663.42,680.25],[25,26,728.98,763.49],[27,30,795.73,894.32]],
    3: [[1,1,4.61,6.89],[2,2,43.17,45.0],[3,3,66.14,67.86],[4,4,91.39,94.23],[5,5,103.24,104.99],[6,7,115.26,129.18],[8,9,153.32,172.59],[10,11,190.82,217.57],[12,15,249.67,349.62],[16,16,417.78,420.05],[17,17,429.47,431.57],[18,18,449.42,451.3],[19,19,482.52,485.48],[20,20,495.52,498.31],[21,22,525.08,551.48],[23,24,588.08,626.59],[25,26,657.13,687.7],[27,30,732.43,825.31]],
}


def prepare_listening_media(materials, n):
    mid, expected_hash = LISTENING_SOURCES[n]
    source = next(m for m in materials if m["id"] == mid)
    if source["sha256"] != expected_hash:
        return {}
    audit_path = ROOT / "generated/essentials-listening-audit.json"
    audit = json.loads(audit_path.read_text()) if audit_path.exists() else {}
    old_segments = {s["groupId"]: s for s in audit.get("segments", []) if s.get("sourceSha256") == expected_hash}
    folder = ROOT / "generated/assets/media" / f"essentials-{n}"
    folder.mkdir(parents=True, exist_ok=True)
    result = {}
    with tempfile.TemporaryDirectory(prefix="toefl-essentials-listening-") as temp:
        pcm = Path(temp) / "source.wav"
        subprocess.run(["/usr/bin/afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", str(ROOT / "data" / source["path"]), str(pcm)], check=True, capture_output=True)
        with wave.open(str(pcm), "rb") as original:
            for first, last, start, end in LISTENING_RANGES[n]:
                gid = f"essentials-{n}-listening-{first}-{last}"
                original.setpos(round(start * 16000))
                contents = original.readframes(round(end * 16000) - round(start * 16000))
                target = folder / (gid + "-stimulus.wav")
                old = old_segments.get(gid, {})
                reusable = False
                if target.exists() and old.get("startSeconds") == start and old.get("endSeconds") == end:
                    try:
                        with wave.open(str(target), "rb") as check:
                            reusable = check.getframerate() == 16000 and check.getnframes() * 2 == len(contents)
                    except (wave.Error, EOFError):
                        pass
                if not reusable:
                    temporary = target.with_name(target.name + f".{os.getpid()}.tmp")
                    with wave.open(str(temporary), "wb") as output:
                        output.setnchannels(1); output.setsampwidth(2); output.setframerate(16000); output.writeframes(contents)
                    temporary.replace(target)
                audio = {"url": f"/assets/media/essentials-{n}/{target.name}", "materialId": mid,
                         "sourceUrl": source["url"], "sourceSha256": expected_hash, "scope": "group" if last > first else "item",
                         "groupId": gid, "mediaType": "audio", "durationSeconds": len(contents) / 32000,
                         "startSeconds": start, "endSeconds": end, "verified": True, "supplementalOnly": True,
                         "containsResponseWait": False}
                for number in range(first, last + 1):
                    result[number] = {"audio": audio, "transcript": old.get("text"),
                                      "mediaAudit": {"verificationMethod": old.get("verificationMethod", "source-hash-frozen-audited-audio-range"),
                                                     "sourceHashVerified": True, "automaticQuestionAudio": True}, "warnings": []}
                    if n in [2, 3] and number <= 5:
                        result[number]["sourceMismatch"] = {"type": "supplied-transcript-first-five-swapped", "incorrectTranscriptSet": n,
                                                            "matchingTranscriptSet": 3 if n == 2 else 2, "audioAndQuestionPdfSetUnchanged": True}
                        result[number]["warnings"].append("提供的2/3号听力原文PDF将前5个对答互换；此处保留与本号题本一致的本号原音，仅校验原文来源作更正。")
                    if n == 2 and number == 20:
                        result[number]["mediaAudit"]["transcriptNeedsReview"] = True
                        result[number]["warnings"].append("本题原音和原题顺序已核对；ASR对开头否定缩写识别不稳，不将ASR作为新题面。")
    return result


def prepare_speech_media(materials, n):
    mid, expected_hash = SPEECH_SOURCES[n]
    source = next(m for m in materials if m["id"] == mid)
    if source["sha256"] != expected_hash:
        return {}, "口语原音轨SHA-256已变化，原范围不可复用，需要重新核验。"
    cached_path = ROOT / "generated/essentials-speech-audit.json"
    cached = json.loads(cached_path.read_text()) if cached_path.exists() else {}
    transcripts = {q["questionId"]: q for q in cached.get("prompts", []) if q.get("sourceSha256") == expected_hash}
    result = {}
    folder = ROOT / "generated/assets/media" / f"essentials-{n}"
    folder.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="toefl-essentials-") as temp:
        pcm = Path(temp) / "source.wav"
        subprocess.run(["/usr/bin/afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", str(ROOT / "data" / source["path"]), str(pcm)], check=True, capture_output=True)
        with wave.open(str(pcm), "rb") as original:
            for number, spans in SPEECH_RANGES[n].items():
                qid = f"essentials-{n}-s-{number}"
                data = []
                for start, end in spans:
                    original.setpos(round(start * 16000))
                    data.append(original.readframes(round(end * 16000) - round(start * 16000)))
                contents = b"".join(data)
                target = folder / (qid + "-prompt.wav")
                spans_json = [{"startSeconds": start, "endSeconds": end} for start, end in spans]
                old = transcripts.get(qid, {})
                reusable = False
                if target.exists() and old.get("sourceIntervals") == spans_json:
                    try:
                        with wave.open(str(target), "rb") as check:
                            reusable = check.getframerate() == 16000 and check.getnframes() * 2 == len(contents)
                    except (wave.Error, EOFError):
                        pass
                if not reusable:
                    temporary = target.with_name(target.name + f".{os.getpid()}.tmp")
                    with wave.open(str(temporary), "wb") as output:
                        output.setnchannels(1); output.setsampwidth(2); output.setframerate(16000); output.writeframes(contents)
                    temporary.replace(target)
                result[number] = {"url": f"/assets/media/essentials-{n}/{target.name}", "materialId": mid,
                    "sourceUrl": source["url"], "sourceSha256": expected_hash, "scope": "item", "groupId": qid,
                    "mediaType": "audio", "durationSeconds": len(contents) / 32000,
                    "sourceIntervals": spans_json,
                    "verified": True, "supplementalOnly": True, "containsResponseWait": False,
                    "containsSampleResponses": False, "sourceRecordingPausesRemoved": len(spans) > 1,
                    "transcript": transcripts.get(qid, {}).get("transcript")}
    return result, None


def source_material(materials, eid, part):
    matches = [m for m in materials if eid in m.get("examIds", []) and m["kind"] == "pdf"
               and m["name"].startswith("模拟题目") and part in m["name"]]
    if len(matches) != 1:
        raise ValueError(f"Expected one {eid} {part} question PDF, found {len(matches)}")
    return matches[0]


def read_cached(material):
    return json.loads((ROOT / "generated/extracted" / f'{material["id"]}.json').read_text())


def keys_for(materials, eid):
    material = next(m for m in materials if eid in m.get("examIds", []) and "官方答案" in m["name"])
    text = "\n".join(p["text"] for p in read_cached(material)["pages"])
    result = {"reading": {}, "listening": {}, "writing": {}}
    section = None
    for line in text.splitlines():
        heading = re.fullmatch(r"\s*(Listening|Reading|Writing)[.:]?\s*", line, re.I)
        if heading:
            section = heading[1].lower()
            continue
        if line.startswith("写作") or line.startswith("Sample Response"):
            section = None
        m = re.match(r"^\s*(\d{1,2})[.\s]+(.+?)\s*$", line)
        if m and section:
            n, answer = int(m[1]), m[2]
            if section == "writing":
                # This corrects a source-font I/l transcription, never a new item.
                answer = re.sub(r"\bl\b", "I", answer)
                answer = re.sub(r"([.])(?=I\b)", r"\1 ", answer)
            result[section][n] = answer
    for section, expected in [("reading", 30), ("listening", 30), ("writing", 14)]:
        if set(result[section]) != set(range(1, expected + 1)):
            raise ValueError(f"Incomplete {eid} {section} reference key")
    return result, material


def original_source(h, material, page, section, number):
    result = h.source(material, page["page"])
    counter = re.search(r"Question\s*(\d+)\s*of\s*(\d+)", page["text"], re.I)
    if counter and int(counter[1]) != number:
        raise ValueError(f'{material["name"]} page {page["page"]}: counter {counter[1]} != {number}')
    result.update(section=section, originalNumber=number,
                  numberVerification="visible-source-counter" if counter else "ordered-source-pages-and-neighboring-counters",
                  format="TOEFL Essentials", method="faithful-source-image")
    return result


def crop_body(h, page, name, *, speaking=False, left=.085, right=.97, bottom=None):
    # Some discussion screenshots begin content directly below the teal bar.
    # A 22% crop cut off the first student's opening line; 14% preserves it.
    top = int(page["height"] * .14)
    if bottom is None:
        bottom = page["height"] - 6
        if speaking:
            markers = [w["y"] for w in page["words"] if w["text"].lower().strip(":") in {"annotation", "sample"}
                       and w["y"] > page["height"] * .5]
        else:
            markers = [w["y"] for w in page["words"] if w["text"].lower() == "show" and w["y"] > page["height"] * .7
                       and any(v["text"].lower() == "answer" and abs(v["y"] - w["y"]) < 12
                               and 0 < v["x"] - w["x"] < 180 for v in page["words"])]
        if markers:
            bottom = min(bottom, min(markers) - 18)
    asset = h.crop(page, name, top, bottom, left=left, right=right)
    asset["sourcePageAsset"] = page["asset"]
    asset["cropBounds"] = [int(page["width"] * left), top, int(page["width"] * right), int(bottom)]
    return asset


def base_question(h, material, page, eid, section, number, kind, task_type):
    return {"id": f"{eid}-{section[0]}-{number}", "number": number, "type": kind,
            "taskType": task_type, "prompt": "", "supplemental": True,
            "source": original_source(h, material, page, section, number),
            "auditStatus": "source-image-verified", "timingPolicy": "untimed",
            "warnings": [], "sourceImageAuthoritative": True}


def source_choices(count=4):
    # These are response labels, not invented replacement option text. The exact
    # original choices remain visible in the source image immediately above.
    return [{"id": letter, "text": ""} for letter in "ABCD"[:count]]


def build_reading(h, eid, material, pages, keys, answer_material):
    if len(pages) != 30:
        raise ValueError(f"Unexpected {eid} reading page count")
    questions = []
    for n, page in enumerate(pages, 1):
        task = "vocabulary" if n <= 5 or 16 <= n <= 20 else "true_false_not_stated" if 12 <= n <= 15 else "read_a_text"
        q = base_question(h, material, page, eid, "reading", n, "choice", "essentials_" + task)
        q["assets"] = [crop_body(h, page, q["id"])]
        q["sourceImageContainsQuestionAndChoices"] = True
        if task == "true_false_not_stated":
            q["choices"] = [{"id": v, "text": v} for v in ["True", "False", "Not stated"]]
            q["answer"] = next(v for v in ["True", "False", "Not stated"] if v.lower() == keys[n].lower())
        else:
            q["choices"], q["answer"] = source_choices(), keys[n]
        q["answerSource"] = {"materialId": answer_material["id"], "originalNumber": n, "section": "Reading"}
        q["audit"] = {"questionAndOptions": "unaltered-source-raster", "answer": "provided-separate-reference-key",
                      "optionOrder": "left-to-right" if task == "vocabulary" else "top-to-bottom",
                      "structuredOptionText": False, "syntheticContent": False}
        questions.append(q)
    return {"id": "reading", "title": "Essentials · 阅读补充练习", "taskTypes": sorted({q["taskType"] for q in questions}),
            "modules": [{"id": "essentials-reading", "title": "Essentials Reading · untimed",
                         "timingPolicy": "untimed", "expectedItemCount": 30, "questions": questions}]}


def raw_audio(materials, eid, part):
    selected = [m for m in materials if eid in m.get("examIds", []) and m["kind"] == "audio" and part in m["name"]]
    if len(selected) != 1:
        return None
    m = selected[0]
    return {"url": m["url"], "materialId": m["id"], "durationSeconds": m.get("durationSeconds"),
            "scope": "section", "mediaType": "audio", "manualOnly": True, "allowSeeking": True,
            "warning": "整段原始学习音轨，可能含范例回答。仅手动定位/播放，不作为逐题自动考试音频。"}


def build_listening(h, eid, n, material, pages, keys, answer_material, materials):
    questions = []
    media = prepare_listening_media(materials, n)
    for number, page_number in enumerate(LISTENING_PAGES[n], 1):
        page = pages[page_number - 1]
        task = "listen_and_reply" if number <= 5 or 16 <= number <= 20 else "listen_to_a_text"
        q = base_question(h, material, page, eid, "listening", number, "choice", "essentials_" + task)
        q.update(assets=[crop_body(h, page, q["id"])], choices=source_choices(), answer=keys[number],
                 sourceImageContainsQuestionAndChoices=True,
                 answerSource={"materialId": answer_material["id"], "section": "Listening", "originalNumber": number},
                 mediaAudit={"status": "section-study-track-only", "automaticQuestionAudio": False},
                 warnings=["题干/选项来自原图；原音轨请用手动播放器定位，未核验逐题音频边界。"],
                 audit={"questionAndOptions": "unaltered-source-raster", "answer": "provided-separate-reference-key", "syntheticContent": False})
        if number in media:
            q.update(copy.deepcopy(media[number]))
            q["sourcePromptAvailable"] = True
            q["transcriptStatus"] = "source-reference/local-ASR review aid; original audio is authoritative"
            if not q.get("transcript"):
                q.pop("transcript", None)
        questions.append(q)
    audio = raw_audio(materials, eid, "听力")
    module = {"id": "essentials-listening", "title": "Essentials Listening · untimed study",
              "timingPolicy": "untimed", "expectedItemCount": 30, "questions": questions}
    if audio and len(media) != 30:
        module["practiceAudio"] = audio
    transcript = next((m for m in materials if eid in m.get("examIds", []) and "听力原文" in m["name"]), None)
    refs = ([{"materialId": transcript["id"], "url": transcript["url"], "role": "transcript", "reviewOnly": True}] if transcript else [])
    if audio:
        refs.append({"materialId": audio["materialId"], "url": audio["url"], "role": "whole-study-audio", "manualOnly": True, "reviewOnly": True})
    return {"id": "listening", "title": "Essentials · 听力补充练习", "taskTypes": ["essentials_listen_and_reply", "essentials_listen_to_a_text"],
            "practiceAudio": audio if len(media) != 30 else None, "modules": [module],
            "referenceMaterials": refs, "matchedAudioQuestionCount": len(media)}


def build_writing(h, eid, material, pages, keys, answer_material):
    if len(pages) != 17:
        raise ValueError(f"Unexpected {eid} writing page count")
    building = []
    for n in range(1, 15):
        page = pages[n - 1]
        q = base_question(h, material, page, eid, "writing", n, "build_sentence", "essentials_build_sentence")
        q.update(assets=[crop_body(h, page, q["id"])], answer=keys[n],
                 inputMode="complete-sentence-transcription", answerSource={"materialId": answer_material["id"], "section": "Writing", "originalNumber": n},
                 warnings=["原词块与固定文字完整保留在题图。此补充题使用整句输入，不宣称已核验拖放词槽。"],
                 audit={"question": "unaltered-source-raster", "answer": "provided-separate-reference-key", "fixedSlotInteractionVerified": False, "syntheticContent": False})
        building.append(q)
    modules = [{"id": "essentials-build-sentence", "title": "Essentials · Build a Sentence",
                "timingPolicy": "untimed", "expectedItemCount": 14, "questions": building}]
    for number, kind, title in [(1, "email", "Write an Email"), (2, "picture_writing", "Describe a Photo"), (3, "academic_discussion", "Academic Discussion")]:
        page = pages[13 + number]
        q = base_question(h, material, page, eid, "writing", number, kind, "essentials_" + kind)
        q["id"] = f"{eid}-w-{kind}-{number}"
        # Email/photo tasks have source material only on the left. The right
        # pane is an empty editor; discussion has legitimate student posts there.
        right = .565 if kind == "picture_writing" else .47 if kind == "email" else .97
        q["assets"] = [crop_body(h, page, q["id"], right=right)]
        q["audit"] = {"question": "unaltered-source-raster", "sampleAnswersExcluded": True, "syntheticContent": False}
        modules.append({"id": "essentials-" + kind, "title": "Essentials · " + title,
                        "timingPolicy": "untimed", "expectedItemCount": 1, "questions": [q]})
    return {"id": "writing", "title": "Essentials · 写作补充练习", "taskTypes": ["essentials_build_sentence", "essentials_email", "essentials_picture_writing", "essentials_academic_discussion"], "modules": modules}


def build_speaking(h, eid, n, material, pages, materials):
    if len(pages) != 40:
        raise ValueError(f"Unexpected {eid} speaking page count")
    questions = []
    for number, page_number in enumerate(SPEAKING_READ_PAGES, 1):
        page = pages[page_number - 1]
        q = base_question(h, material, page, eid, "speaking", number, "read_aloud", "essentials_read_aloud")
        q.update(assets=[crop_body(h, page, q["id"], speaking=True)], prompt="Read the words aloud.",
                 recordingMode="manual", sourcePromptAvailable=True, audit={"question": "unaltered-source-raster", "duplicateSampleScreenPages": [page_number, page_number + 1],
                                                "sampleResponsesAndAnnotationsExcluded": True, "syntheticContent": False})
        questions.append(q)
    media, source_problem = prepare_speech_media(materials, n)
    modules = [{"id": "essentials-read-aloud", "title": "Essentials · Read Aloud",
                "timingPolicy": "untimed", "expectedItemCount": 6, "questions": questions}]
    for kind, numbers, title in [("listen_repeat", range(7, 15), "Listen and Repeat"), ("interview", range(15, 20), "Virtual Interview")]:
        items = []
        for number in numbers:
            if number not in media:
                continue
            page_number = SPEAKING_PROMPT_PAGES[number][0]
            page = pages[page_number - 1]
            q = base_question(h, material, page, eid, "speaking", number, kind, "essentials_" + kind)
            clip = copy.deepcopy(media[number]); transcript = clip.pop("transcript", None)
            q.update(assets=[crop_body(h, page, q["id"], speaking=True)], audio=clip,
                     prompt="Listen and repeat only once." if kind == "listen_repeat" else "Please answer the interviewer's question.",
                     recordingMode="manual", sourcePromptAvailable=True,
                     audit={"question": "original-source-audio-with-screenshot-counter", "duplicateSampleScreenPages": SPEAKING_PROMPT_PAGES[number],
                            "sampleResponsesAndAnnotationsExcluded": True, "isolatedClipAsrChecked": True, "syntheticContent": False},
                     mediaAudit={"verificationMethod": "source-sequence-PDF-annotation-and-measured-boundary-cross-check", "sourceHashVerified": True,
                                 "sourceRecordingPausesRemoved": clip["sourceRecordingPausesRemoved"]})
            if transcript:
                q["transcript"] = transcript
                q["transcriptStatus"] = "local-ASR-review-aid; original audio is authoritative"
            if clip["sourceRecordingPausesRemoved"]:
                q["warnings"].append("原学习录音在问题中途暂停；仅删除可测量的静音，原语音片段逐字保留。此题仍为不计时补充练习。")
            items.append(q)
        if items:
            modules.append({"id": "essentials-" + kind, "title": "Essentials · " + title,
                            "timingPolicy": "untimed", "expectedItemCount": len(items),
                            "expectedSourceItemCount": 8 if kind == "listen_repeat" else 5,
                            "missingSourceNumbers": [number for number in numbers if number not in media], "questions": items})
    excluded = [{"originalNumber": number, "source": h.source(material, pair[0]), "physicalPages": pair,
                 "sourceTaskType": "Listen and Repeat" if number <= 14 else "Virtual Interview",
                 "reason": source_problem or SPEECH_MISSING.get(number, "原音轨未提供可核验的问题声源；不创建替代题。"),
                 "status": "reference-only-source-prompt-missing", "sourcePromptAvailable": False}
                for number, pair in SPEAKING_PROMPT_PAGES.items() if number not in media]
    audio = raw_audio(materials, eid, "口语")
    refs = [{"materialId": material["id"], "url": material["url"], "role": "question-and-sample-reference", "reviewOnly": True}]
    if audio:
        refs.append({"materialId": audio["materialId"], "url": audio["url"], "role": "whole-study-audio", "manualOnly": True})
    return {"id": "speaking", "title": "Essentials · 口语补充练习", "taskTypes": ["essentials_read_aloud", "essentials_listen_repeat", "essentials_interview"],
            "expectedSourceQuestionCount": 19, "interactiveQuestionCount": 6 + len(media),
            "referenceMaterials": refs, "excludedTasks": excluded,
            "modules": modules}


def validate_exam(exam):
    ids = []
    for section in exam["sections"]:
        for module in section["modules"]:
            if len(module["questions"]) != module["expectedItemCount"]:
                raise ValueError(f"Question count mismatch in {module['id']}")
            for q in module["questions"]:
                ids.append(q["id"])
                for asset in q["assets"]:
                    if not (ROOT / "generated" / asset["url"].lstrip("/")).is_file():
                        raise ValueError(f"Missing source crop for {q['id']}")
                if q["type"] == "choice" and q.get("answer") not in {c["id"] for c in q["choices"]}:
                    raise ValueError(f"Answer/choice mismatch in {q['id']}")
                if q.get("audio", {}).get("scope") == "section":
                    raise ValueError("A whole-track audio must never be attached to each question")
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate Essentials question IDs in {exam['id']}")
    if exam["strictEligible"] or exam["timingPolicy"] != "untimed":
        raise ValueError("Essentials must never inherit iBT strict timing")


def build_essentials(materials, jobs=6):
    h = helpers()
    exams = []
    for n in [1, 2, 3]:
        eid = f"essentials-{n}"
        resources = [m for m in materials if eid in m.get("examIds", [])]
        keys, answer_material = keys_for(materials, eid)
        question_materials = {s: source_material(materials, eid, cn) for s, cn in [("reading", "阅读"), ("listening", "听力"), ("writing", "写作"), ("speaking", "口语")]}
        pages = {s: h.prepare_pdf(m, jobs=jobs) for s, m in question_materials.items()}
        exam = {"schemaVersion": 1, "id": eid, "title": f"TOEFL Essentials 补充练习 {n}",
                "family": "essentials", "supplemental": True, "resourcesOnly": False,
                "strictEligible": False, "timingPolicy": "untimed", "testFormat": "TOEFL Essentials",
                "sourceMaterialIds": [m["id"] for m in resources],
                "associatedMaterials": [{"id": m["id"], "name": m["name"], "url": m["url"], "kind": m["kind"]} for m in resources],
                "warnings": ["Essentials 是独立的补充材料，不是 2026 iBT 模考；不使用 iBT 题量、分流、计时或分数。",
                             "扫描题以真实裁图为准；选择题按原图选项顺序输入，不用生成文字替代无法核实的扫描内容。",
                             "整段学习音轨仅手动播放；未核验的口语原声题保留为参考，不计入交互题数。"],
                "sections": []}
        exam["sections"] = [build_reading(h, eid, question_materials["reading"], pages["reading"], keys["reading"], answer_material),
                            build_listening(h, eid, n, question_materials["listening"], pages["listening"], keys["listening"], answer_material, materials),
                            build_writing(h, eid, question_materials["writing"], pages["writing"], keys["writing"], answer_material),
                            build_speaking(h, eid, n, question_materials["speaking"], pages["speaking"], materials)]
        h.finalize_exam(exam)
        speaking_count = exam["sections"][-1]["interactiveQuestionCount"]
        excluded_count = 19 - speaking_count
        exam.update(interactiveQuestionCount=exam["screenCount"], expectedSourceQuestionCount=96, referenceOnlyQuestionCount=excluded_count)
        exam["audit"] = {"expected": {"reading": 30, "listening": 30, "writing": 17, "speaking": 19, "total": 96},
                         "interactive": {"reading": 30, "listening": 30, "writing": 17, "speaking": speaking_count, "total": exam["screenCount"]},
                         "excludedAsReferenceOnly": excluded_count, "sourceQuestionPdfPages": sum(len(p) for p in pages.values()),
                         "sampleScreensDeduplicated": True, "parseWarnings": (["原轨未录入2道口语题；保留来源证据但不生成替代题。"] if excluded_count else []),
                         "noSyntheticQuestions": True}
        if n in [2, 3]:
            mismatch = "提供的2/3号听力原文PDF前5个对答文本互换。已由各自题本选项、各自原音与另一原文文本交叉核验；不交换音轨或题本、不改写问题。"
            exam["warnings"].append(mismatch)
            exam["audit"]["sourceMismatches"] = [{"section": "listening", "originalNumbers": [1, 2, 3, 4, 5], "description": mismatch}]
        exam["audit"]["verifiedListeningAudioQuestions"] = exam["sections"][1]["matchedAudioQuestionCount"]
        exam["audit"]["verifiedSpeakingPromptAudioQuestions"] = speaking_count - 6
        validate_exam(exam)
        h.dump(ROOT / "generated/exams" / f"{eid}.json", exam)
        exams.append(exam)
        print(f"Essentials {n}: {exam['screenCount']} interactive source items; {excluded_count} reference-only speaking prompts", flush=True)
    return exams


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=6)
    args = parser.parse_args()
    catalog = json.loads((ROOT / "generated/catalog.json").read_text())
    build_essentials(catalog["materials"], jobs=args.jobs)
