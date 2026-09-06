#!/usr/bin/env python3
"""Re-render verified essential visuals from their original PDF regions."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from urllib.parse import unquote, urlsplit


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(root: Path, materials: list[dict]) -> dict:
    try:
        from scripts.structure_questions import load
    except ModuleNotFoundError:
        from structure_questions import load
    manifest = load(root)
    by_id = {item["id"]: item for item in materials}
    specs = {}
    for record in manifest.get("questions", {}).values():
        for spec in record.get("essentialVisualCrops", []):
            old = specs.setdefault(spec["url"], spec)
            if old != spec:
                raise ValueError(f"Conflicting essential visual specification: {spec['url']}")
    if not specs:
        return {"status": "passed", "visuals": 0}
    try:
        import pymupdf
    except ModuleNotFoundError:
        import fitz as pymupdf
    rendered = 0
    for url, spec in sorted(specs.items()):
        material = by_id.get(spec.get("materialId"))
        if not material or material.get("sha256") != spec.get("sourceSha256"):
            raise ValueError(f"Changed essential visual PDF source: {url}")
        source = root / "data" / unquote(urlsplit(material["url"]).path.removeprefix("/materials/"))
        bounds = spec.get("normalizedBounds")
        if (not isinstance(bounds, list) or len(bounds) != 4 or
                not all(isinstance(value, (int, float)) for value in bounds) or
                not (0 <= bounds[0] < bounds[2] <= 1 and 0 <= bounds[1] < bounds[3] <= 1)):
            raise ValueError(f"Invalid essential visual bounds: {url}")
        target = root / "generated/assets" / url.removeprefix("/assets/")
        if target.is_file() and _digest(target) == spec.get("sha256"):
            continue
        document = pymupdf.open(source)
        page = document[spec["page"] - 1]
        rect = page.rect
        clip = pymupdf.Rect(rect.width * bounds[0], rect.height * bounds[1],
                            rect.width * bounds[2], rect.height * bounds[3])
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(spec.get("scale", 4), spec.get("scale", 4)),
                                 clip=clip, alpha=False)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".tmp.png")
        pixmap.save(temporary)
        document.close()
        if pixmap.width != spec.get("width") or pixmap.height != spec.get("height") or _digest(temporary) != spec.get("sha256"):
            temporary.unlink(missing_ok=True)
            raise ValueError(f"Essential visual render changed and requires review: {url}")
        os.replace(temporary, target)
        rendered += 1
    managed = (root / "generated/assets/structured").resolve()
    referenced = {(root / "generated/assets" / url.removeprefix("/assets/")).resolve() for url in specs}
    removed = 0
    if managed.is_dir():
        for stale in managed.rglob("*"):
            if stale.is_file() and stale.resolve() not in referenced:
                stale.unlink()
                removed += 1
    return {"status": "passed", "visuals": len(specs), "rendered": rendered,
            "removedUnreferencedDerivedFiles": removed,
            "source": "original supplied PDF; normalized verified crop; no resampling enlargement"}


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    catalog = json.loads((root / "generated/catalog.json").read_text())
    print(json.dumps(build(root, catalog["materials"]), ensure_ascii=False))
