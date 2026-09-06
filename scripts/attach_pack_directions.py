"""Attach source-verified Pack/Paid directions without inventing spoken text."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import wave

MANIFEST = "scripts/verified_pack_directions.json"
EXAMS = {*(f"pack-{n}" for n in range(1, 7)), "paid-1", "paid-2"}


def attach(exams, materials, root):
    root = Path(root)
    path = root / MANIFEST
    affected = [exam for exam in exams if exam.get("id") in EXAMS]
    if not path.is_file():
        for exam in affected:
            exam["strictEligible"] = False
            exam.setdefault("scopedEligibility", {}).update(listening=False, speaking=False)
            note = "缺少听说原说明的来源校核文件；相关严格范围已关闭，不能以通用说明代替未核对的原资料。"
            if note not in exam.setdefault("warnings", []):
                exam["warnings"].append(note)
        return {"status": "manifest-not-installed", "modulesAttached": 0, "questionGroupsAttached": 0}
    manifest = json.loads(path.read_text())
    if manifest.get("schemaVersion") != 1 or not isinstance(manifest.get("clips"), dict):
        raise ValueError("Invalid original-directions source manifest")
    by_material = {m["id"]: m for m in materials}
    hashes = {}

    def digest(target):
        target = target.resolve()
        if not target.is_relative_to(root.resolve()) or not target.is_file():
            raise ValueError("Missing or invalid original-directions source file")
        if target not in hashes:
            hashes[target] = hashlib.sha256(target.read_bytes()).hexdigest()
        return hashes[target]

    def check_pdf(source):
        m = by_material.get(source.get("materialId"))
        if (not m or m["kind"] != "pdf" or m["sha256"] != source.get("sha256") or
                digest(root / "data" / m["path"]) != source.get("sha256") or
                type(source.get("page")) is not int or not 1 <= source["page"] <= m["pages"] or
                source.get("url") != m["url"] + f"#page={source['page']}"):
            raise ValueError("Original directions PDF/page changed or is missing")

    def media(clip_id, owner):
        record = manifest["clips"][clip_id]
        m = by_material.get(record.get("sourceMaterialId"))
        if (record.get("verified") is not True or record.get("containsResponseWait") is not False or
                not m or m["kind"] not in {"audio", "video"} or
                record["sourceSha256"] != m["sha256"] or digest(root / "data" / m["path"]) != m["sha256"]):
            raise ValueError(f"Original directions audio source changed: {clip_id}")
        for source in record["pdfEvidence"]:
            check_pdf(source)
        url = record["url"]
        if not url.startswith("/assets/"):
            raise ValueError("Directions must use a verified local original-source clip")
        target = root / "generated/assets" / url.removeprefix("/assets/")
        if digest(target) != record["assetSha256"]:
            raise ValueError(f"Directions clip is missing or changed: {clip_id}")
        with wave.open(str(target), "rb") as wav:
            duration = wav.getnframes() / wav.getframerate()
        if (abs(duration - record["durationSeconds"]) > .03 or
                abs(duration - (record["endSeconds"] - record["startSeconds"])) > .03 or
                not 0 <= record["startSeconds"] < record["endSeconds"] <= m["durationSeconds"] + .03):
            raise ValueError(f"Directions clip interval or duration changed: {clip_id}")
        return {"url": url, "materialId": m["id"], "sourceUrl": m["url"],
                "sourceSha256": m["sha256"], "startSeconds": record["startSeconds"],
                "endSeconds": record["endSeconds"], "durationSeconds": duration,
                "mediaType": "audio", "kind": "directions", "scope": "directions",
                "groupId": f"source-directions-{owner}-{clip_id}", "verified": True,
                "containsResponseWait": False, "segmentId": clip_id}

    operations = []
    groups = []
    for exam in affected:
        modules = {m["id"]: m for s in exam["sections"] if s["id"] in {"listening", "speaking"} for m in s["modules"]}
        records = [r for r in manifest["modules"] if r["examId"] == exam["id"]]
        if {r["moduleId"] for r in records} != set(modules):
            raise ValueError(f"Directions coverage differs from source modules: {exam['id']}")
        for record in records:
            if not record.get("instructions") or not record.get("sourcePages"):
                raise ValueError("Source directions cannot be empty")
            for source in record["sourcePages"]:
                check_pdf(source)
            audio = [media(cid, f"{exam['id']}-{record['moduleId']}") for cid in record.get("clipIds", [])]
            operations.append((exam, modules[record["moduleId"]], record, audio))
        questions = {q["id"]: q for m in modules.values() for q in m["questions"]}
        for record in manifest.get("questionGroups", []):
            if record["examId"] != exam["id"]:
                continue
            q = questions.get(record["firstQuestionId"])
            if not q or q.get("audio", {}).get("groupId") != record["stimulusGroupId"]:
                raise ValueError("Directions question group no longer matches its original stimulus")
            audio = [media(cid, record["firstQuestionId"]) for cid in record["clipIds"]]
            groups.append((exam, q, record, audio))
    # All original documents, audio intervals and targets pass before mutation.
    for exam, module, record, audio in operations:
        module["instructions"] = record["instructions"]
        module["instructionSources"] = copy.deepcopy(record["sourcePages"])
        module["directionsAudit"] = {"manifest": MANIFEST, "moduleId": module["id"],
                                    "method": "original-PDF-text-and-separately-verified-original-audio",
                                    "sourceNotes": record.get("sourceNotes", [])}
        if audio:
            module["directionsAudio"] = audio
    for exam, q, record, audio in groups:
        q["directionsAudio"] = audio[0] if len(audio) == 1 else audio
        q["directionsAudit"] = {"manifest": MANIFEST, "sourceGroupEvidence": record["evidence"],
                                "humanReviewed": False}
    for exam in affected:
        exam.setdefault("verificationInputs", {}).setdefault("curationSha256ByPath", {})[MANIFEST] = digest(path)
    return {"status": "attached-source-directions", "modulesAttached": len(operations),
            "modulesWithAudio": sum(bool(row[3]) for row in operations),
            "questionGroupsAttached": len(groups), "clipCount": len(manifest["clips"]),
            "questionContentChanged": False, "syntheticAudioUsed": False}
