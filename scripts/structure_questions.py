#!/usr/bin/env python3
"""Apply locally verified, answer-free structured stem presentations.

The curation file is deliberately separate from OCR/import code. A question is
never promoted from an image to an active structured presentation unless its
exact question id, source file hash, page, and answer-free display blocks are
present in scripts/verified_structured_content.json. Original crops remain as
review-only evidence. Missing or stale records leave the legacy question alone
and are reported to the caller; they are never filled from an answer key.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path


SCHEMA = "structured-v1"
CURATION_NAME = "verified_structured_content.json"
CURATION_FRAGMENTS = ["verified_structured_essentials.json"]
CONTENT_ID = re.compile(r"^qcontent-[0-9a-f]{20}$")
STATUSES = {"source-verified", "needs-review", "source-review-only"}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(root: Path) -> dict:
    path = root / "scripts" / CURATION_NAME
    if not path.is_file():
        return {"schemaVersion": 1, "questions": {}}
    value = json.loads(path.read_text())
    if value.get("schemaVersion") != 1 or not isinstance(value.get("questions"), dict):
        raise ValueError(f"Invalid {CURATION_NAME}")
    merged = copy.deepcopy(value)
    for name in CURATION_FRAGMENTS:
        fragment_path = root / "scripts" / name
        if not fragment_path.is_file():
            continue
        fragment = json.loads(fragment_path.read_text())
        if fragment.get("schemaVersion") != 1 or not isinstance(fragment.get("questions"), dict):
            raise ValueError(f"Invalid {name}")
        overlap = set(merged["questions"]) & set(fragment["questions"])
        if overlap:
            raise ValueError(f"Conflicting structured curation question ids in {name}: {sorted(overlap)[:3]}")
        merged["questions"].update(copy.deepcopy(fragment["questions"]))
        merged.setdefault("scope", []).extend(x for x in fragment.get("scope", []) if x not in merged.get("scope", []))
        merged.setdefault("fragmentAudit", {})[name] = copy.deepcopy(fragment.get("audit", {}))
    return merged


def apply(exams: list[dict], materials: list[dict], root: Path) -> dict:
    curation = load(root)
    records = curation["questions"]
    rebuildable_visuals = {spec.get("url"): spec for item in records.values()
                           for spec in item.get("essentialVisualCrops", [])
                           if isinstance(spec, dict) and isinstance(spec.get("url"), str)}
    material_by_id = {item["id"]: item for item in materials}
    assets_root = root / "generated" / "assets"
    applied, stale, missing_assets = [], [], []
    seen = set()
    for exam in exams:
        for section in exam.get("sections", []):
            for module in section.get("modules", []):
                for question in module.get("questions", []):
                    record = records.get(question.get("id"))
                    if not record:
                        continue
                    seen.add(question["id"])
                    source = question.get("source", {})
                    material = material_by_id.get(source.get("materialId"))
                    if (not material or record.get("examId") != exam["id"] or
                            record.get("materialId") != source.get("materialId") or
                            record.get("page") != source.get("page") or
                            record.get("sourceSha256") != material.get("sha256") or
                            not CONTENT_ID.fullmatch(str(record.get("contentId", ""))) or
                            not CONTENT_ID.fullmatch(str(record.get("sourceContentId", record.get("contentId", "")))) or
                            question.get("contentId") not in {record.get("sourceContentId", record.get("contentId")),
                                                              record.get("contentId"),
                                                              *record.get("previousContentIds", [])}):
                        stale.append(question["id"])
                        continue
                    status = record.get("structuredContentStatus", "source-verified")
                    if (status not in STATUSES or
                            ("supplemental" in record and bool(record["supplemental"]) != bool(exam.get("supplemental"))) or
                            ("timingPolicy" in record and record["timingPolicy"] != exam.get("timingPolicy"))):
                        stale.append(question["id"])
                        continue
                    expected_assets = record.get("sourceEvidenceSha256", {})
                    visual_assets = record.get("essentialVisualAssets", [])
                    expected_visuals = record.get("essentialVisualSha256", {})
                    visual_urls = {asset.get("url") for asset in visual_assets if isinstance(asset, dict)}
                    if (visual_urls != set(expected_visuals) or
                            not visual_urls.issubset(rebuildable_visuals) or
                            any(asset.get("alt") != rebuildable_visuals[asset.get("url")].get("alt") or
                                asset.get("width") != rebuildable_visuals[asset.get("url")].get("width") or
                                asset.get("height") != rebuildable_visuals[asset.get("url")].get("height")
                                for asset in visual_assets)):
                        missing_assets.append(question["id"])
                        continue
                    original_assets = copy.deepcopy([asset for asset in question.get("assets", [])
                                                     if asset.get("role") != "essentialVisual"])
                    bad_asset = False
                    for asset in original_assets:
                        url = asset.get("url", "")
                        path = assets_root / url.removeprefix("/assets/")
                        if not path.is_file() or expected_assets.get(url) != _sha(path):
                            missing_assets.append(question["id"])
                            bad_asset = True
                    for url, expected in expected_visuals.items():
                        path = assets_root / url.removeprefix("/assets/")
                        if not path.is_file() or _sha(path) != expected:
                            missing_assets.append(question["id"])
                            bad_asset = True
                    if bad_asset:
                        continue
                    for key in ["prompt", "passage", "passageTemplate", "context", "choices", "transcript",
                                "tokens", "slots", "extraTokens", "fixedTokens", "interaction",
                                "wordLimit", "recommendedWords"]:
                        if key in record:
                            question[key] = copy.deepcopy(record[key])
                    if record.get("additionalWarnings"):
                        question["warnings"] = list(dict.fromkeys([*question.get("warnings", []), *record["additionalWarnings"]]))
                    if record.get("stimulusSource"):
                        stimulus = record["stimulusSource"]
                        stimulus_material = material_by_id.get(stimulus.get("materialId"))
                        expected_url = (stimulus_material.get("url") + f"#page={stimulus.get('page')}") if stimulus_material else None
                        if (not stimulus_material or stimulus.get("sourceSha256") != stimulus_material.get("sha256") or
                                stimulus.get("url") != expected_url or type(stimulus.get("page")) is not int or stimulus["page"] < 1):
                            stale.append(question["id"])
                            continue
                        question["stimulusSource"] = {key: stimulus[key] for key in ["materialId", "page", "url"]}
                    question["presentationSchema"] = SCHEMA
                    question["structuredContentStatus"] = status
                    question["stemBlocks"] = copy.deepcopy(record["stemBlocks"])
                    question["curatedContentId"] = record["contentId"]
                    evidence = copy.deepcopy(question.get("sourceEvidenceAssets", []))
                    for asset in original_assets:
                        evidence.append({**asset, "role": "sourceEvidence", "reviewOnly": True,
                                         "page": source.get("page")})
                    question["sourceEvidenceAssets"] = evidence
                    # Full-question crops never remain active. Only separately
                    # verified essential visuals may be restored here.
                    question["assets"] = copy.deepcopy(record.get("essentialVisualAssets", []))
                    applied.append(question["id"])
    unknown = sorted(set(records) - seen)
    if stale or missing_assets or unknown:
        raise ValueError({"staleStructuredRecords": stale,
                          "missingStructuredEvidenceAssets": missing_assets,
                          "unknownStructuredQuestionIds": unknown})
    return {"schemaVersion": 1,
            "curationFiles": [f"scripts/{CURATION_NAME}", *[f"scripts/{name}" for name in CURATION_FRAGMENTS]],
            "recordCount": len(records), "appliedCount": len(applied),
            "appliedQuestionIds": applied, "status": "passed"}
