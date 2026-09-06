#!/usr/bin/env python3
"""Local-only source-audio segmentation, ASR alignment, and traceable exports.

Use the project-isolated .venv-media, never the broken system FFmpeg. Source
files are read-only. ASR runs on this Mac with MLX; no inference API is called.
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
from functools import lru_cache
import json
import re
import subprocess
import sys
import tempfile
import time
import types
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "generated/assets/media"
CACHE = OUT / "_analysis"
SAMPLE_RATE = 16000
DEFAULT_MODEL = "mlx-community/whisper-tiny.en-mlx-q4"


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


@lru_cache(maxsize=1)
def decode(path):
    import numpy as np
    try:
        binary = ffmpeg()
    except ImportError:
        # macOS ships a working CoreAudio decoder independently of Homebrew.
        # This lets energy analysis run before the optional ASR install finishes.
        with tempfile.TemporaryDirectory(prefix="toefl-media-") as directory:
            output = Path(directory) / "audio.wav"
            subprocess.run(["/usr/bin/afconvert", "-f", "WAVE", "-d", f"LEI16@{SAMPLE_RATE}",
                            "-c", "1", str(path), str(output)], check=True, capture_output=True)
            with wave.open(str(output), "rb") as source:
                return np.frombuffer(source.readframes(source.getnframes()), dtype="<i2").astype("float32") / 32768
    command = [binary, "-hide_banner", "-loglevel", "error", "-i", str(path),
               "-f", "f32le", "-ac", "1", "-ar", str(SAMPLE_RATE), "pipe:1"]
    result = subprocess.run(command, check=True, capture_output=True)
    return np.frombuffer(result.stdout, dtype="<f4").copy()


def save_wav(path, audio):
    import numpy as np
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())


def material_exam(m):
    # Some earlier catalogs included the parent phrase '第1套有解析'. Do not
    # infer a student's form number from that descriptive parent directory.
    student = re.search(r"托福样题0?([12])", m["name"])
    if student:
        return f"student-{student.group(1)}"
    return next((e for e in m.get("examIds", []) if e.startswith(("pack-", "paid-"))), None)


def source_materials(exam=None):
    catalog = read_json(ROOT / "generated/catalog.json")
    selected = []
    for m in catalog["materials"]:
        if m["kind"] not in ("audio", "video"):
            continue
        eid = material_exam(m)
        if eid and (not exam or eid in exam):
            selected.append({**m, "resolvedExamId": eid})
    return selected


def speech_regions(audio, threshold_db=-38, gap_seconds=1.45):
    """Measured energy regions; >=1.45 s gaps are never retained in a prompt.

    This is a boundary detector, not a claim that every region contains speech.
    Beeps and noise are retained for later classification instead of discarded.
    """
    import numpy as np
    frame = 160
    padded = np.pad(audio, (0, (-len(audio)) % frame))
    rms = np.sqrt(np.mean(padded.reshape(-1, frame) ** 2, axis=1))
    active = np.flatnonzero(rms > 10 ** (threshold_db / 20))
    if not len(active):
        return []
    parts = np.split(active, np.flatnonzero(np.diff(active) > gap_seconds * 100) + 1)
    regions = []
    for p in parts:
        begin, end = p[0] / 100, (p[-1] + 1) / 100
        if end - begin < .055:
            continue
        regions.append({"start": round(max(0, begin - .10), 3),
                        "end": round(min(len(audio) / SAMPLE_RATE, end + .14), 3),
                        "activeFrames": len(p)})
    return regions


def prepare(m):
    import numpy as np
    folder = CACHE / m["id"]
    metadata_path = folder / "energy.json"
    if metadata_path.exists():
        cached = read_json(metadata_path)
        if cached.get("sha256") == m["sha256"]:
            return cached
    audio = decode(ROOT / "data" / m["path"])
    regions = speech_regions(audio)
    compressed = []
    cursor = 0
    for region in regions:
        clip = audio[round(region["start"] * SAMPLE_RATE):round(region["end"] * SAMPLE_RATE)]
        region["compressedStart"] = cursor / SAMPLE_RATE
        region["compressedEnd"] = (cursor + len(clip)) / SAMPLE_RATE
        compressed.extend([clip, np.zeros(round(.4 * SAMPLE_RATE), dtype="float32")])
        cursor += len(clip) + round(.4 * SAMPLE_RATE)
    assembled = np.concatenate(compressed) if compressed else audio
    folder.mkdir(parents=True, exist_ok=True)
    save_wav(folder / "compressed.wav", assembled)
    metadata = {"materialId": m["id"], "examId": m["resolvedExamId"],
                "sha256": m["sha256"], "sourcePath": m["path"],
                "durationSeconds": len(audio) / SAMPLE_RATE,
                "compressedSeconds": len(assembled) / SAMPLE_RATE,
                "sampleRate": SAMPLE_RATE, "thresholdDb": -38,
                "splitGapSeconds": 1.45, "regions": regions}
    write_json(metadata_path, metadata)
    return metadata


def source_time(compressed_time, regions, end=False):
    for r in regions:
        if r["compressedStart"] <= compressed_time <= r["compressedEnd"]:
            return r["start"] + compressed_time - r["compressedStart"]
    previous = [r for r in regions if r["compressedEnd"] < compressed_time]
    following = [r for r in regions if r["compressedStart"] > compressed_time]
    if end and previous:
        return previous[-1]["end"]
    if following:
        return following[0]["start"]
    return regions[-1]["end"]


def transcribe(m, model):
    # Numba is an optional speed-up for the existing NumPy DTW implementation.
    # When LLVM wheels are unavailable, execute exactly those Python functions
    # without JIT compilation; this changes speed, not the alignment algorithm.
    try:
        import numba  # noqa: F401
    except ImportError:
        fallback = types.ModuleType("numba")
        fallback.jit = lambda *args, **kwargs: (args[0] if args and callable(args[0]) else lambda function: function)
        sys.modules["numba"] = fallback
    import mlx_whisper
    metadata = prepare(m)
    folder = CACHE / m["id"]
    path = folder / "asr.json"
    if path.exists():
        result = read_json(path)
        if result.get("sha256") == m["sha256"] and result.get("model") == model:
            return result
    audio = decode(folder / "compressed.wav")
    started = time.time()
    result = mlx_whisper.transcribe(audio, path_or_hf_repo=model, language="en",
        word_timestamps=True, temperature=0, condition_on_previous_text=False,
        no_speech_threshold=.6, verbose=False)
    words = []
    for segment in result.get("segments", []):
        for w in segment.get("words", []):
            words.append({"word": w["word"], "start": round(source_time(w["start"], metadata["regions"]), 3),
                          "end": round(source_time(w["end"], metadata["regions"], True), 3),
                          "probability": w.get("probability"),
                          "compressedStart": w["start"], "compressedEnd": w["end"]})
    output = {"materialId": m["id"], "sha256": m["sha256"], "model": model,
              "method": "local-mlx-whisper-on-measured-speech-regions",
              "elapsedSeconds": round(time.time() - started, 2),
              "text": result.get("text", ""), "words": words,
              "segments": result.get("segments", [])}
    write_json(path, output)
    print(f'ASR {m["resolvedExamId"]} {m["name"]}: {output["elapsedSeconds"]}s / {len(words)} words', flush=True)
    return output


def normalize(text):
    return " ".join(re.findall(r"[a-z0-9]+(?:'[a-z]+)?", str(text).lower().replace("’", "'")))


def load_exam(eid):
    path = ROOT / "generated/exams" / (eid + ".json")
    return read_json(path) if path.exists() else None


def questions_for(exam, section, module=None):
    if not exam:
        return []
    return [q for s in exam["sections"] if s["id"] == section
            for m in s["modules"] if not module or m["id"] == module
            for q in m["questions"]]


def expected_pack_listening(eid):
    """Pair the separate supplied listening transcript with source question IDs."""
    catalog = read_json(ROOT / "generated/catalog.json")
    material = next((m for m in catalog["materials"] if eid in m.get("examIds", [])
                     and m["kind"] == "pdf" and "听力原文" in m["name"]), None)
    if not material:
        return []
    path = ROOT / "generated/extracted" / (material["id"] + ".json")
    if not path.exists():
        return []
    text = "\n".join(p["text"] for p in read_json(path)["pages"])
    headings = list(re.finditer(r"(?im)^\s*(?:(?:Pack\s*\d+\s*)?Module\s*(\d)|"
                                r"(Conversation|Announcement|Lecture)\s*(\d+)[^\n]*|"
                                r"(\d+)\.\s*)(.*)$", text))
    exam = load_exam(eid)
    results, module, counters = [], 1, {}
    for i, heading in enumerate(headings):
        if heading[1]:
            module = int(heading[1])
            continue
        mid = f"listening-m{module}"
        qs = questions_for(exam, "listening", mid)
        if heading[4]:
            number = int(heading[4])
            q = next((q for q in qs if q.get("number") == number), None)
            if q:
                results.append({"examId": eid, "section": "listening", "moduleId": mid,
                    "questionIds": [q["id"]], "groupId": f"{eid}-{mid}-response-{number}",
                    "kind": "stimulus", "text": heading[5].strip(),
                    "referenceMaterialId": material["id"], "taskType": "listen_response"})
            continue
        typ = {"conversation": "conversation", "announcement": "announcement", "lecture": "academic_talk"}[heading[2].lower()]
        size = 4 if typ == "academic_talk" else 2
        offset = counters.get((module, typ), 0)
        members = [q for q in qs if q.get("taskType") == typ][offset:offset + size]
        counters[(module, typ)] = offset + size
        if not members:
            continue
        begin = heading.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        body = text[begin:end].strip()
        results.append({"examId": eid, "section": "listening", "moduleId": mid,
            "questionIds": [q["id"] for q in members],
            "groupId": f'{eid}-{mid}-{typ}-{heading[3]}', "kind": "stimulus",
            "text": body, "referenceMaterialId": material["id"], "taskType": typ})
    return results


def expected_for(m):
    eid = m["resolvedExamId"]
    exam = load_exam(eid)
    name = m["name"].lower()
    if eid.startswith("paid-"):
        return expected_paid(m)
    if eid.startswith("pack-") and "listening" in name:
        return expected_pack_listening(eid)
    if "speaking" in name or "口语" in name:
        qs = questions_for(exam, "speaking")
        if eid.startswith("pack-"):
            # Imported interview transcripts may themselves come from this ASR
            # manifest. Never treat that feedback as independent source proof.
            qs = [q for q in qs if q["type"] == "listen_repeat"]
        if "listen and repeat" in name:
            qs = [q for q in qs if q["type"] == "listen_repeat"]
        elif "interview" in name:
            qs = [q for q in qs if q["type"] == "interview"]
        return [{"examId": eid, "section": "speaking",
                 "moduleId": "speaking-" + q["type"], "questionIds": [q["id"]],
                 "groupId": q["id"], "kind": "prompt", "text": q["transcript"],
                 "taskType": q["type"], "referenceMaterialId": q.get("source", {}).get("materialId")}
                for q in qs if q.get("transcript")]
    module_match = re.search(r"module\s*0?(\d)", name)
    if not module_match:
        return []
    mid = f"listening-m{module_match[1]}"
    qs = questions_for(exam, "listening", mid)
    if "choose a response" in name:
        groups = [[q] for q in qs if q.get("taskType") == "listen_response"]
    else:
        typ = "conversation" if "conversation" in name else "announcement" if "announcement" in name else "academic_talk"
        matching = [q for q in qs if q.get("taskType") == typ]
        if typ == "conversation":
            number = int(re.search(r"conversation\s*0?(\d)", name)[1])
            matching = matching[(number - 1) * 2:number * 2]
        groups = [matching] if matching else []
    return [{"examId": eid, "section": "listening", "moduleId": mid,
             "questionIds": [q["id"] for q in group],
             "groupId": f'{eid}-{mid}-{group[0]["number"]}', "kind": "stimulus",
             "text": group[0].get("transcript", ""), "taskType": group[0].get("taskType"),
             "referenceMaterialId": group[0].get("source", {}).get("materialId")}
            for group in groups if group[0].get("transcript")]


def expected_paid(m):
    eid, name, path = m["resolvedExamId"], m["name"], m["path"]
    number = int(eid[-1])
    if "(1)" in name:
        catalog = read_json(ROOT / "generated/catalog.json")
        if any(x["id"] != m["id"] and x.get("sha256") == m["sha256"] for x in catalog["materials"]):
            return []
    section = "listening" if "听力" in path else "speaking"
    title = any(word in name for word in ["标题", "说明", "介绍", "开始"]) or "题目.m4a" in name
    route, module, nums, typ = "common", 1, [], None
    if section == "speaking":
        digits = re.search(r"(?:口语|跟读|面试题目)(\d+)", name)
        if number == 1:
            n = int(digits[1]) if digits else 0
            typ = "listen_repeat" if n <= 7 else "interview"
            nums = [n] if n else []
        else:
            typ = "interview" if "面试" in name else "listen_repeat"
            n = int(re.search(r"(\d+)", name)[1]) if re.search(r"\d", name) else 0
            nums = [n if typ == "listen_repeat" else n + 7] if n else []
        mid = "speaking-" + typ
        qids = [f'{eid}-s-{typ}-{n if typ == "listen_repeat" else n - 7}' for n in nums]
    else:
        mod_match = re.search(r"M([12])", path, re.I)
        module = int(mod_match[1]) if mod_match else 1
        route = "lower" if module == 2 and "lower" in path.lower() else "upper" if module == 2 else "common"
        mid = f"listening-m{module}" + ("-" + route if module == 2 else "")
        if number == 1:
            match = re.search(r"M[12]-(\d+)(?:-(\d+))?", name, re.I)
            if match:
                nums = list(range(int(match[1]), int(match[2] or match[1]) + 1))
        else:
            response = re.search(r"对答-Q(\d+)", name)
            conv = re.search(r"^C(\d+)", name)
            announcement = re.search(r"通知类(\d+)", name)
            academic = re.search(r"学术讲座(\d*)", name)
            if response:
                nums, typ = [int(response[1])], "listen_response"
            elif conv:
                first = (9 if module == 1 else 4) + (int(conv[1]) - 1) * 2
                nums, typ = [first, first + 1], "conversation"
            elif announcement:
                first = 13 + (int(announcement[1]) - 1) * 2
                nums, typ = [first, first + 1], "announcement"
                title = False  # The word 说明 here means intro is included in the stimulus file.
            elif academic:
                first = 17 if module == 1 else 8 + (int(academic[1] or 1) - 1) * 4
                nums, typ = list(range(first, first + 4)), "academic_talk"
                title = False
        qids = [f'{eid}-l{module}{"-" + route if module == 2 else ""}-{n}' for n in nums]
    if title or not nums:
        return [{"examId": eid, "section": section, "moduleId": mid,
                 "questionIds": qids, "groupId": f'{eid}-{m["id"]}-directions', "kind": "directions",
                 "taskType": typ, "text": "", "explicitFileRange": True}]
    text, reference_id = "", None
    if section == "listening" and not (number == 1 and route == "lower"):
        targets = expected_pack_listening(f"pack-{number}")
        for item in targets:
            if item["moduleId"] == f"listening-m{module}" and any(qid.endswith("-" + str(nums[0])) for qid in item["questionIds"]):
                text, reference_id, typ = item["text"], item["referenceMaterialId"], item["taskType"]
                break
    elif section == "speaking":
        source = read_json(ROOT / "generated/media-segments.json")
        target_qid = f'pack-{number}-speaking-{typ}-{nums[0]}'
        target = next((s for s in source.get("segments", []) if target_qid in s["questionIds"] and s["kind"] == "prompt"), None)
        if target:
            text = target.get("actualSourceTranscript") or target["text"]
            reference_id = target["sourceMaterialId"]
    return [{"examId": eid, "section": section, "moduleId": mid, "questionIds": qids,
             "groupId": f'{eid}-{mid}-{nums[0]}', "kind": "prompt" if section == "speaking" else "stimulus",
             "taskType": typ, "text": text, "referenceMaterialId": reference_id,
             "explicitFileRange": not bool(text), "rangeFromFilename": nums}]


def explicit_file_candidate(item, meta, asr):
    if not meta["regions"] or not asr.get("text", "").strip():
        return None
    first, last = meta["regions"][0], meta["regions"][-1]
    gap = max([0] + [b["start"] - a["end"] for a, b in zip(meta["regions"], meta["regions"][1:])])
    return {**item, "text": asr["text"].strip(), "matchedText": normalize(asr["text"]),
            "startSeconds": first["start"], "endSeconds": last["end"], "confidence": .95,
            "verified": gap < 4, "boundaryVerified": True, "maximumInternalGapSeconds": round(gap, 3),
            "humanReviewed": False, "verificationMethod": "explicit-source-file-question-range-and-measured-boundaries",
            "evidence": ["source-filename-explicitly-identifies-question-range", "local-ASR-auditable-transcript", "measured-energy-boundaries"],
            "warnings": ["ASR text is a local aid, not an official transcript; answer-key corrections need separate review."]}


def match_expected(expected, asr, meta, minimum_start=0):
    from rapidfuzz import fuzz
    # Speaker labels are present only in printed transcripts, never in speech.
    target = re.sub(r"(?i)\b(?:man|woman|trainer|interviewer|professor|narrator)\s*:", "", expected["text"])
    target = normalize(target)
    # Short lines can recur in module 2. Search the next plausible acoustic
    # neighborhood instead of jumping to an equally matching later occurrence.
    upper_time = minimum_start + 180 if len(target.split()) <= 22 else float("inf")
    candidates = [(i, w) for i, w in enumerate(asr["words"])
                  if w["end"] >= minimum_start and w["start"] <= upper_time]
    token_words, starts, sentence = [], [], ""
    for index, word in candidates:
        token = normalize(word["word"])
        if not token:
            continue
        if sentence:
            sentence += " "
        starts.append(len(sentence))
        sentence += token
        token_words.append((index, word))
    if not sentence or len(target) < 7:
        return None
    match = fuzz.partial_ratio_alignment(target, sentence)
    if not match:
        return None
    match_start = match.dest_start
    while match_start < len(sentence) and sentence[match_start].isspace():
        match_start += 1
    first = max(0, bisect.bisect_right(starts, match_start) - 1)
    last = max(first, bisect.bisect_left(starts, match.dest_end) - 1)
    # Fuzzy character windows can include the last word of the preceding item.
    # Exact multi-word edge anchors are stronger evidence than that window.
    target_tokens = target.split()
    tokens = [normalize(w["word"]) for _, w in token_words]
    edge_length = min(3, len(target_tokens))
    for offset in range(first, min(first + 7, last - edge_length + 2)):
        if tokens[offset:offset + edge_length] == target_tokens[:edge_length]:
            first = offset
            break
    for offset in range(last, max(first + edge_length - 2, last - 7), -1):
        if tokens[offset - edge_length + 1:offset + 1] == target_tokens[-edge_length:]:
            last = offset
            break
    selected = token_words[first:last + 1]
    if not selected:
        return None
    start, end = selected[0][1]["start"], selected[-1][1]["end"]
    matched_text = sentence[starts[first]:starts[last] + len(normalize(selected[-1][1]["word"]))]
    score = fuzz.ratio(target, matched_text) / 100
    # Zero-duration words at compressed joins occasionally drift to the next
    # recording. Neighbor words and a measured long gap identify that artifact.
    if len(selected) >= 3:
        last_word = selected[-1][1]
        previous_end = selected[-2][1]["end"]
        if last_word["end"] - last_word["start"] < .025 and last_word["start"] - previous_end > 4:
            end = previous_end
        first_word = selected[0][1]
        next_start = selected[1][1]["start"]
        if first_word["end"] - first_word["start"] < .025 and next_start - first_word["end"] > 4:
            start = next_start
    # Snap only when the word boundary is close to a measured acoustic boundary.
    # Large expansions are not guessed (they could contain another prompt).
    start_region = next((r for r in meta["regions"] if r["start"] - .3 <= start <= r["end"] + .3), None)
    end_region = next((r for r in meta["regions"] if r["start"] - .3 <= end <= r["end"] + .3), None)
    if expected.get("taskType") == "listen_repeat" and start_region and end_region and end_region["end"] - end_region["start"] < .7:
        # A final zero-duration word can be aligned to the following beep. A
        # beep is not part of the utterance; export it separately as a cue.
        spoken = [r for r in meta["regions"] if start_region["start"] <= r["start"] < end_region["start"] and r["end"] - r["start"] >= .8]
        if spoken:
            end_region = spoken[-1]
            end = end_region["end"]
    boundary_verified = False
    if start_region and end_region:
        start_gap = start - start_region["start"]
        end_gap = end_region["end"] - end
        region_text_match = 0
        if start_region is end_region:
            region_text_match = fuzz.ratio(target, normalize(region_words(start_region, asr))) / 100
        if (-.3 <= start_gap < 1.0 and -.3 <= end_gap < 1.0) or region_text_match >= .94:
            start, end = start_region["start"], end_region["end"]
            boundary_verified = True
        else:
            start = max(start_region["start"], start - .10)
            end = min(end_region["end"], end + .15)
    bad_spans = [r for r in meta["regions"] if r["start"] > start and r["end"] < end]
    max_gap = max([0] + [b["start"] - a["end"] for a, b in zip(meta["regions"], meta["regions"][1:])
                         if a["end"] >= start and b["start"] <= end])
    return {**expected, "startSeconds": round(start, 3), "endSeconds": round(end, 3),
            "confidence": round(score, 4), "matchedText": matched_text,
            "boundaryVerified": boundary_verified, "maximumInternalGapSeconds": round(max_gap, 3),
            "verified": bool(score >= .94 and boundary_verified and end > start and max_gap < 4.0),
            "evidence": ["supplied-reference-text", "local-ASR-word-alignment", "measured-energy-boundaries"],
            "verificationMethod": "automated-cross-check", "humanReviewed": False}


def refine_word_times(asr, metadata):
    """Do not map a boundary word across an excised 45-second quiet interval.

    Whisper can timestamp a first word partly in the artificial 0.4s connector.
    Select the retained speech region with the largest word overlap and clamp to
    that region instead of mapping its two endpoints to different source clips.
    """
    for word in asr["words"]:
        start, end = word.get("compressedStart"), word.get("compressedEnd")
        if start is None:
            continue
        overlaps = [(max(0, min(end, r["compressedEnd"]) - max(start, r["compressedStart"])), r)
                    for r in metadata["regions"]]
        overlap, region = max(overlaps, key=lambda item: item[0])
        if overlap <= 0:
            continue
        word["start"] = round(region["start"] + max(0, start - region["compressedStart"]), 3)
        word["end"] = round(region["start"] + min(region["end"] - region["start"], end - region["compressedStart"]), 3)
    return asr


def export_clip(m, segment):
    folder = OUT / m["resolvedExamId"]
    folder.mkdir(parents=True, exist_ok=True)
    sid = f'{segment["groupId"]}-{segment["kind"]}'
    path = folder / (sid + ".mp3")
    duration = segment["endSeconds"] - segment["startSeconds"]
    try:
        binary = ffmpeg()
    except ImportError:
        binary = None
    if binary:
        command = [binary, "-hide_banner", "-loglevel", "error", "-y",
                   "-ss", str(segment["startSeconds"]), "-i", str(ROOT / "data" / m["path"]),
                   "-t", str(duration), "-map", "0:a:0", "-ac", "1", "-ar", "24000",
                   "-codec:a", "libmp3lame", "-b:a", "64k", str(path)]
        subprocess.run(command, check=True, capture_output=True)
    else:
        path = path.with_suffix(".wav")
        audio = decode(ROOT / "data" / m["path"])
        save_wav(path, audio[round(segment["startSeconds"] * SAMPLE_RATE):round(segment["endSeconds"] * SAMPLE_RATE)])
    return {**segment, "id": sid, "sourceMaterialId": m["id"], "sourceUrl": m["url"],
            "sourceSha256": m["sha256"], "url": "/assets/media/" + m["resolvedExamId"] + "/" + path.name,
            "durationSeconds": round(duration, 3), "status": "verified" if segment["verified"] else "needs-review",
            "containsResponseWait": False,
            "warnings": segment.get("warnings", [] if segment["verified"] else ["Text match or exact boundary needs review before strict use."])}


def region_words(region, asr):
    words = [w["word"] for w in asr["words"]
             if w["start"] >= region["start"] - .25 and w["end"] <= region["end"] + .25]
    return "".join(words).strip()


def complete_repeat_utterance(candidate, metadata, asr):
    """Keep source utterances intact when a printed key omits a short prefix."""
    if candidate.get("taskType") != "listen_repeat" or candidate["verified"] or candidate["confidence"] < .97:
        return candidate
    region = next((r for r in metadata["regions"] if r["start"] <= candidate["startSeconds"] and r["end"] >= candidate["endSeconds"]), None)
    if not region:
        return candidate
    actual = region_words(region, asr)
    expected_words, actual_words = normalize(candidate["text"]).split(), normalize(actual).split()
    offset = next((i for i in range(max(0, len(actual_words) - len(expected_words)) + 1)
                   if actual_words[i:i + len(expected_words)] == expected_words), None)
    if offset is None or not 0 < len(actual_words) - len(expected_words) <= 3 or len(expected_words) < 6:
        return candidate
    return {**candidate, "startSeconds": region["start"], "endSeconds": region["end"],
            "verified": True, "boundaryVerified": True, "referenceMismatch": True,
            "referenceText": candidate["text"], "actualSourceTranscript": actual,
            "verificationMethod": "complete-measured-utterance-with-reference-prefix-discrepancy",
            "evidence": candidate["evidence"] + ["complete-single-acoustic-utterance", "reference-body-exactly-contained-in-ASR"],
            "warnings": ["Printed reference omits words found in the source audio; retain the complete utterance and disclose the difference."]}


def known_content_variant(m, meta, asr, expected, matched, unmatched):
    if m["resolvedExamId"] != "student-1" or "interview" not in m["name"].lower() or not unmatched:
        return []
    first = next((e for e in expected if e["questionIds"] == ["student-1-s-interview-1"]), None)
    next_item = next((s for s in matched if s["questionIds"] == ["student-1-s-interview-2"]), None)
    if not first or not next_item:
        return []
    prefix = " ".join(normalize(first["text"]).split()[:6])
    regions = [r for r in meta["regions"] if r["end"] < next_item["startSeconds"]]
    index = next((i for i, r in enumerate(regions) if prefix in normalize(region_words(r, asr))), None)
    if index is None:
        return []
    chosen = regions[index:]
    text = " ".join(region_words(r, asr) for r in chosen)
    return [export_clip(m, {**first, "startSeconds": chosen[0]["start"], "endSeconds": chosen[-1]["end"],
        "confidence": .92, "verified": False, "boundaryVerified": True,
        "maximumInternalGapSeconds": max([0] + [b["start"] - a["end"] for a, b in zip(chosen, chosen[1:])]),
        "referenceMismatch": True, "referenceText": first["text"], "actualSourceTranscript": text,
        "matchedText": normalize(text), "verificationMethod": "ordered-source-variant-not-matching-printed-question",
        "humanReviewed": False, "evidence": ["matching-spoken-greeting", "bounded-by-next-reference-matched-interview-question", "different-question-content"],
        "warnings": ["Source audio asks about the last city visited, but the supplied paper asks whether the person lives in a city/town/village. Do not label this an exact paper/audio match."]})]


def repeat_cues(m, meta, matched):
    import numpy as np
    repeats = [s for s in matched if s.get("taskType") == "listen_repeat"]
    if not repeats:
        return []
    audio = decode(ROOT / "data" / m["path"])
    result = []
    for item in repeats:
        region = next((r for r in meta["regions"] if item["endSeconds"] < r["start"] < item["endSeconds"] + 6 and r["end"] - r["start"] < .7), None)
        if not region:
            continue
        samples = audio[round(region["start"] * SAMPLE_RATE):round(region["end"] * SAMPLE_RATE)]
        spectrum = abs(np.fft.rfft(samples)) ** 2
        peak = int(spectrum.argmax())
        concentration = float(spectrum[max(0, peak - 3):peak + 4].sum() / max(float(spectrum.sum()), 1e-12))
        frequency = peak * SAMPLE_RATE / len(samples)
        if concentration < .60 or not 480 <= frequency <= 1200:
            continue
        result.append(export_clip(m, {"examId": m["resolvedExamId"], "section": "speaking", "moduleId": "speaking-listen_repeat",
            "questionIds": item["questionIds"], "groupId": item["groupId"], "kind": "cue", "text": "Recording cue tone",
            "startSeconds": region["start"], "endSeconds": region["end"], "confidence": round(concentration, 4),
            "verified": True, "boundaryVerified": True, "maximumInternalGapSeconds": 0, "humanReviewed": False,
            "sourceDelayAfterPromptSeconds": round(region["start"] - item["endSeconds"], 3),
            "verificationMethod": "measured-short-narrow-band-tone-after-repeat-prompt",
            "evidence": ["measured-energy-boundaries", "spectral-tone-concentration", "position-after-matched-repeat-utterance"]}))
    return result


def pack_interviews(m, meta, asr, matched):
    """The four prompts have measured >30s answer gaps on supplied Pack tracks.

    This checks both the known item count and all four ordered acoustic windows;
    no arbitrary division of a track into four equal lengths is permitted.
    """
    if not m["resolvedExamId"].startswith("pack-") or "speaking" not in m["name"].lower():
        return []
    repeats = [s for s in matched if s.get("taskType") == "listen_repeat"]
    if len(repeats) != 7:
        return []
    lower = max(s["endSeconds"] for s in repeats)
    candidates = []
    for i, region in enumerate(meta["regions"]):
        next_start = meta["regions"][i + 1]["start"] if i + 1 < len(meta["regions"]) else meta["durationSeconds"]
        gap = next_start - region["end"]
        text = region_words(region, asr)
        if region["start"] > lower and region["end"] - region["start"] >= 4 and gap >= 30 and len(normalize(text).split()) >= 8:
            candidates.append((region, gap, text))
    questions = [q for q in questions_for(load_exam(m["resolvedExamId"]), "speaking") if q["type"] == "interview"]
    if len(candidates) != 4 or len(questions) != 4:
        return []
    output = []
    for q, (region, gap, text) in zip(questions, candidates):
        output.append(export_clip(m, {"examId": m["resolvedExamId"], "section": "speaking",
            "moduleId": "speaking-interview", "questionIds": [q["id"]], "groupId": q["id"],
            "kind": "prompt", "taskType": "interview", "text": text, "matchedText": normalize(text),
            "startSeconds": region["start"], "endSeconds": region["end"], "confidence": .92,
            "verified": True, "boundaryVerified": True, "maximumInternalGapSeconds": 1.45,
            "followingSourceWaitSeconds": round(gap, 3), "humanReviewed": False,
            "verificationMethod": "ordered-acoustic-structure-cross-check",
            "evidence": ["seven-reference-matched-repeat-prompts-before-interview",
                         "exactly-four-ordered-spoken-prompts-with-30s-plus-following-waits",
                         "four-question-source-layout", "measured-energy-boundaries", "local-ASR"]}))
    return output


def additional_regions(m, meta, asr, matched):
    result = []
    for index, region in enumerate(meta["regions"]):
        if any(s["startSeconds"] <= region["start"] + .5 and s["endSeconds"] >= region["end"] - .5 for s in matched):
            continue
        text = region_words(region, asr)
        normal = normalize(text)
        if len(normal) < 12:
            continue
        if not re.search(r"\b(section|clock|you will|you are|you have volunteered|repeat only|no time for preparation|next|back|interview)\b", normal):
            continue
        sid = f'{m["resolvedExamId"]}-{m["id"]}-directions-{index + 1}'
        result.append(export_clip(m, {"examId": m["resolvedExamId"],
            "section": "speaking" if "speaking" in m["name"].lower() or "口语" in m["name"] else "listening",
            "moduleId": None, "questionIds": [], "groupId": sid, "kind": "directions",
            "text": text, "matchedText": normal, "startSeconds": region["start"], "endSeconds": region["end"],
            "confidence": .8, "verified": False, "boundaryVerified": True,
            "maximumInternalGapSeconds": 1.45, "humanReviewed": False,
            "verificationMethod": "local-ASR-directive-detection-needs-review",
            "evidence": ["local-ASR", "measured-energy-boundaries"]}))
    return result


def build(materials):
    old_path = ROOT / "generated/media-segments.json"
    old = read_json(old_path) if old_path.exists() else {}
    ids = {m["id"] for m in materials}
    segments = [s for s in old.get("segments", []) if s.get("sourceMaterialId") not in ids]
    audits = [s for s in old.get("sources", []) if s.get("materialId") not in ids]
    for m in materials:
        meta = prepare(m)
        asr_path = CACHE / m["id"] / "asr.json"
        if not asr_path.exists():
            audits.append({"materialId": m["id"], "examId": m["resolvedExamId"], "status": "needs-asr"})
            continue
        asr = refine_word_times(read_json(asr_path), meta)
        expected = expected_for(m)
        cursor, matched, unmatched = 0, [], []
        for item in expected:
            if m["resolvedExamId"].startswith("paid-") and item.get("taskType") == "announcement" and not normalize(asr["text"]).startswith("listen"):
                item = {**item, "text": re.sub(r"(?i)^listen to an announcement (?:at a university (?:event|club meeting)|in a classroom|on the school radio)[.\s]*", "", item["text"]),
                        "sourceTitleOmitted": True}
            candidate = explicit_file_candidate(item, meta, asr) if item.get("explicitFileRange") else match_expected(item, asr, meta, cursor)
            if candidate and candidate["confidence"] >= .72 and candidate["endSeconds"] > candidate["startSeconds"]:
                candidate = complete_repeat_utterance(candidate, meta, asr)
                cursor = candidate["endSeconds"] - .1
                matched.append(export_clip(m, candidate))
            else:
                unmatched.append({"groupId": item["groupId"], "questionIds": item["questionIds"],
                                  "text": item["text"], "reason": "reference-text-not-reliably-aligned"})
        interview_segments = pack_interviews(m, meta, asr, matched)
        matched.extend(interview_segments)
        variants = known_content_variant(m, meta, asr, expected, matched, unmatched)
        cues = repeat_cues(m, meta, matched)
        extras = additional_regions(m, meta, asr, matched)
        segments.extend(matched + variants + cues + extras)
        waits = [{"startSeconds": round(a["end"], 3), "endSeconds": round(b["start"], 3),
                  "durationSeconds": round(b["start"] - a["end"], 3), "kind": "measured-silent-gap"}
                 for a, b in zip(meta["regions"], meta["regions"][1:]) if b["start"] - a["end"] > 4]
        if meta["regions"] and meta["durationSeconds"] - meta["regions"][-1]["end"] > 4:
            waits.append({"startSeconds": meta["regions"][-1]["end"], "endSeconds": round(meta["durationSeconds"], 3),
                          "durationSeconds": round(meta["durationSeconds"] - meta["regions"][-1]["end"], 3), "kind": "measured-trailing-silence"})
        audits.append({"materialId": m["id"], "examId": m["resolvedExamId"], "sourcePath": m["path"],
                       "sha256": m["sha256"], "durationSeconds": meta["durationSeconds"],
                       "expectedGroups": len(expected) + len(interview_segments), "matchedGroups": len(matched),
                       "verifiedGroups": sum(s["verified"] for s in matched),
                       "unmatched": unmatched, "excludedWaits": waits,
                       "sourceMismatch": {"expected": "charity auction", "recognized": "hiking trip",
                           "wrongSourceMaterialId": m["id"], "correctCanonicalGroupId": "pack-1-listening-m1-announcement-1",
                           "note": "The supplied M1-13-14 audio duplicates the hiking announcement for M1-15-16; use the verified canonical auction audio only with a disclosed source override."}
                           if m["id"] == "mat-237f97573298" and unmatched and "hiking" in normalize(asr["text"]) else None,
                       "sourceRegions": [{"startSeconds": r["start"], "endSeconds": r["end"],
                           "recognizedText": region_words(r, asr), "segmentIds": [s["id"] for s in matched + variants + cues + extras
                           if s["startSeconds"] <= r["start"] + .5 and s["endSeconds"] >= r["end"] - .5]}
                           for r in meta["regions"]],
                       "asrModel": asr["model"], "status": "reviewed-by-alignment"})
        print(f'ALIGN {m["name"]}: {len(matched)}/{len(expected)} matched; {sum(s["verified"] for s in matched)} verified', flush=True)
    write_json(old_path, {"schemaVersion": 1, "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "method": "local-ASR + supplied transcript + measured audio energy boundaries",
               "warning": "Only verified segments may enter strict playback; excludedWaits are source silence, never replayed as response time.",
               "segments": segments, "sources": audits})
    write_report(read_json(old_path))


def write_report(data):
    lines = ["# 本地长音轨切分与核验", "", f'生成时间：{data["generatedAt"]}', "",
        "原始 data 文件保持不变。切分只使用本机声学检测、源资料原文和本机 MLX Whisper；不向云端推理服务发送音频。首次下载开源模型后可离线重新处理。",
        "", "## 文件与接口", "",
        "- `scripts/segment_media.py`：可重复执行的扫描、转写、对齐、导出与校验工具。",
        "- `generated/media-segments.json`：每段包含 sourceMaterialId、原音轨 SHA-256、startSeconds/endSeconds、questionIds、groupId、kind、url、confidence、verified 和证据。",
        "- `generated/assets/media/<examId>/`：供本地播放器使用的分段音频。",
        "- `generated/assets/media/_analysis/`：保留原时间映射、能量检测与 ASR 缓存，均为本地私有中间文件。",
        "", "## 已完成的源轨", "",
        "| 套题 | 源文件 | 原时长 | 已关联组 | 自动核验组 | 未匹配组 |",
        "| --- | --- | ---: | ---: | ---: | ---: |"]
    for source in data["sources"]:
        lines.append(f'| {source["examId"]} | {Path(source.get("sourcePath", source["materialId"])).name} | {source.get("durationSeconds", 0):.1f}s | {source.get("matchedGroups", 0)} | {source.get("verifiedGroups", 0)} | {len(source.get("unmatched", []))} |')
    lines.extend(["", "## 核验方法与限制", "",
        "1. 用 16 kHz 单声道 PCM 测量能量边界。阈值为 -38 dB；超过 1.45 秒的安静区间分开处理。该测量只证明带声与安静，不把每个安静区间直接宣称为官方答题时间。",
        "2. 仅为 ASR 压缩长静音，并保存压缩时刻到原时刻的映射。播放器使用从原时间区间导出的片段，绝不播放这个压缩转写轨。",
        "3. 已给原文与本地 ASR 的词序对齐后，再将边界吸附到可测量的安静区间。文本相似度至少 0.94、边界可靠且片段内部无 4 秒以上长静音时，标为自动核验通过。",
        "4. Pack 采访原页没有逐字转写时，必须先匹配前面全部 7 个复述题，再找到恰好 4 段、均伴随 30 秒以上作答等待的采访提示，按已核对的四题顺序关联。此类证据另标 ordered-acoustic-structure-cross-check，不冒充人工听校。",
        "5. verified 表示通过上述可追溯的自动核验；humanReviewed 单独标识人工听校，默认 false。低匹配或边界不确定的段落为 needs-review，不能进入严格播放。",
        "6. sources[].excludedWaits 列出被排除的安静区间（包括末尾静音）。这些区间不作为题目音频播放，也不能再当作准备时间；作答窗口由版本化考试规则单独计时。",
        "7. 说明候选段独立保存为 directions；没有充分证据的说明不会自动混入题干。源轨没有独立朗读问题时，不凭空生成问题音频。",
        "8. cue 段是原轨中的录音提示音，按短时窄带频谱及其位于复述题后的顺序核对；sourceDelayAfterPromptSeconds 仅记录原录音中的间隔，不自动等同于正式准备时间。提示音与正文是独立资产，播放器不应额外再播放第二遍提示音。",
        "", "## 运行", "", "```sh",
        "# 使用项目专属虚拟环境；不要修补系统 Homebrew FFmpeg。",
        "uv venv --python 3.12 .venv-media",
        "uv pip install --python .venv-media/bin/python mlx-whisper imageio-ffmpeg rapidfuzz",
        "HF_HUB_DISABLE_XET=1 .venv-media/bin/python scripts/segment_media.py all",
        ".venv-media/bin/python scripts/segment_media.py validate",
        "```", "",
        "工具优先使用 imageio_ffmpeg 自带二进制。macOS 安装尚未完成时可用系统自带 CoreAudio 解码，输出标准 WAV，不调用损坏的 Homebrew FFmpeg。Numba/LLVM 缺失时使用同一 DTW 函数的纯 Python 实现，计算更慢但不改变算法。",
        "", "## 接入规则", "",
        "只将 verified=true 且 kind 为 stimulus/prompt 的段落映射至题目。questionIds 共享同一个 groupId 时只播放一次，然后按题号分别答题。保留源轨、时间区间与核验状态以供校验页面追踪；不得把 needs-review 直接改为已核验以开放模考。",
        ""])
    mismatches = [s for s in data["segments"] if s.get("referenceMismatch")]
    if mismatches:
        lines.extend(["## 来源差异", ""])
        for s in mismatches:
            lines.extend([f'- **{s["id"]}**：源区间 {s["startSeconds"]:.2f}–{s["endSeconds"]:.2f} 秒，verified={str(s["verified"]).lower()}。',
                          f'  纸面参考：{s.get("referenceText", s.get("text", ""))}',
                          f'  音频识别：{s.get("actualSourceTranscript", "")}',
                          f'  处理：{"完整保留单一原声句子，并披露纸面漏词。" if s["verified"] else "作为不同音频版本保留供核对；不宣称与纸面题完全匹配。"}', ""])
    for source in data["sources"]:
        if source.get("sourceMismatch"):
            lines.extend([f'- **{source["materialId"]}**：{source["sourceMismatch"]["note"]}', ""])
    path = ROOT / "docs/MEDIA_SEGMENTS.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text("\n".join(lines))


def validate():
    data = read_json(ROOT / "generated/media-segments.json")
    seen, errors = set(), []
    sources = {s["materialId"]: s for s in data["sources"]}
    for s in data["segments"]:
        if s["id"] in seen:
            errors.append(f'duplicate id: {s["id"]}')
        seen.add(s["id"])
        if not 0 <= s["startSeconds"] < s["endSeconds"] <= sources[s["sourceMaterialId"]]["durationSeconds"] + .1:
            errors.append(f'invalid source boundaries: {s["id"]}')
        if not (ROOT / "generated" / s["url"].lstrip("/")).is_file():
            errors.append(f'missing output: {s["id"]}')
        if s["verified"] and not (s["boundaryVerified"] and s.get("maximumInternalGapSeconds", 0) < 4):
            errors.append(f'verified segment includes unverified boundaries or wait: {s["id"]}')
    if errors:
        raise SystemExit("\n".join(errors))
    print(f'Validated {len(data["segments"])} segments; {sum(s["verified"] for s in data["segments"])} verified.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["scan", "transcribe", "build", "all", "validate"])
    parser.add_argument("--exam", action="append", help="e.g. pack-1; repeat for more forms")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()
    if args.phase == "validate":
        validate()
        return
    materials = source_materials(args.exam)
    print(f"Selected {len(materials)} source tracks", flush=True)
    for m in materials:
        meta = prepare(m)
        print(f'{m["resolvedExamId"]} {m["name"]}: {meta["durationSeconds"]:.1f}s -> {meta["compressedSeconds"]:.1f}s, {len(meta["regions"])} measured regions', flush=True)
        if args.phase in ("transcribe", "all"):
            transcribe(m, args.model)
    if args.phase in ("transcribe", "all") and any(m["resolvedExamId"].startswith("paid-") for m in materials):
        rows = []
        for m in source_materials():
            path = CACHE / m["id"] / "asr.json"
            if m["resolvedExamId"].startswith("paid-") and path.exists():
                data = read_json(path)
                rows.append({"materialId": m["id"], "examId": m["resolvedExamId"], "name": m["name"],
                             "path": m["path"], "sourceSha256": m["sha256"], "text": data["text"],
                             "words": data["words"], "method": data["method"], "model": data["model"]})
        write_json(ROOT / "generated/paid-audio-transcripts.json", {"schemaVersion": 1, "sources": rows,
                   "notice": "Local ASR for source cross-check only; never expose transcripts during a timed listening/speaking attempt."})
    if args.phase in ("build", "all"):
        build(materials)


if __name__ == "__main__":
    main()
