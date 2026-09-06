"""Enable paired teacher recordings only after source-safe display curation."""
from __future__ import annotations

import re

from backend.presentation import validate_question

TEACHER_IDS = {"teacher-1", "teacher-2"}
SOURCE_INSTRUCTIONS = {
    "listen_response": "Choose the best response.",
    "listen_repeat": "Listen to the speaker and repeat what she says. Repeat only once.",
    "interview": "Please answer the interviewer's questions.",
}
OBSOLETE_WARNINGS = {
    "官方教师资料没有音频：听力、口语仅用于阅读原文和专项练习，不可完整严格模考。",
    "本题没有与题本文字完全匹配的已核验原音；仅作不限时原文专项学习。",
    "Missing or ambiguous audio mapping",
}


def normalized(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def safe_audio_blocks(question):
    """Only existing printed questions or source-printed directions may remain.

    These three instructions were visually checked on both teacher PDFs.
    Never turn a transcript into an on-screen question, including during the
    response phase after the recording has finished.
    """
    kind = question.get("taskType")
    blocks = question.get("stemBlocks", [])
    if kind in SOURCE_INSTRUCTIONS:
        expected = SOURCE_INSTRUCTIONS[kind]
        return (question.get("prompt") == expected and
                blocks == [{"type": "instruction", "text": expected}])
    return (kind in {"conversation", "announcement", "academic_talk"} and
            bool(question.get("prompt")) and
            blocks == [{"type": "question", "text": question["prompt"]}] and
            normalized(question["prompt"]) != normalized(question.get("transcript", "")))


def finalize(exams):
    """Promote scopes from audited media and curated displays, never by family."""
    enabled, unavailable = [], []
    for exam in exams:
        if exam.get("id") not in TEACHER_IDS:
            continue
        scopes = exam.setdefault("scopedEligibility", {})
        input_checks = exam.get("verificationInputs", {})
        source_inputs_pass = (input_checks.get("sourceHashStatus") == "passed" and
                              not input_checks.get("missingFiles") and
                              not input_checks.get("changedSourceMaterialIds"))
        for section in exam.get("sections", []):
            if section.get("id") not in {"listening", "speaking"}:
                continue
            questions = [q for module in section["modules"] for q in module["questions"]]
            for q in questions:
                audited_audio = (q.get("audio", {}).get("verified") is True and
                                 q.get("audio", {}).get("containsResponseWait") is False and
                                 q.get("mediaAudit", {}).get("verificationMethod") ==
                                 "official-paired-archive-filenames-and-local-audio-content-audit")
                if audited_audio:
                    if validate_question(q, strict=True) or not safe_audio_blocks(q):
                        raise ValueError(f"Teacher audio presentation still exposes source stimulus text: {q['id']}")
                    q.pop("referenceOnly", None)
                    q.pop("practiceMode", None)
                    q["sourcePromptAvailable"] = True
                    q["warnings"] = [w for w in q.get("warnings", []) if w not in OBSOLETE_WARNINGS]
                    enabled.append(q["id"])
                else:
                    q["referenceOnly"] = True
                    # A curated audio presentation has no visible transcript.
                    # Missing original recordings cannot become answerable items.
                    if safe_audio_blocks(q):
                        q["sourcePromptAvailable"] = False
                    unavailable.append(q["id"])
            scopes[section["id"]] = source_inputs_pass and bool(questions) and all(q["id"] in enabled for q in questions)
        if all(scopes.get(s) for s in ["listening", "speaking"]):
            exam["warnings"] = [w for w in exam.get("warnings", []) if w not in OBSOLETE_WARNINGS]
            note = "教师版已补充 ETS 当前公开配套原声：按官方套号、模块和题号关联并核验文件摘要；自动语音比对仅供复盘校核，不替换原题或宣称逐字人工听校。"
            if note not in exam["warnings"]:
                exam["warnings"].append(note)
        exam["interactiveQuestionCount"] = sum(
            len(q["blanks"]) if q["type"] == "cloze" else 1
            for section in exam["sections"] for module in section["modules"] for q in module["questions"]
            if q.get("sourcePromptAvailable"))
        if not scopes or not all(scopes.values()):
            exam["strictEligible"] = False
    return {"enabledQuestionCount": len(enabled), "unavailableQuestionIds": unavailable,
            "activeTranscriptsPermitted": False}
