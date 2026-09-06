"""Read public metadata and keep raw study content behind opaque asset handles.

The catalog is refreshed from local files. Its summaries intentionally omit
answers and full question bodies; session endpoints project those separately.
See docs/ARCHITECTURE.md for the source-integrity and resource-pack contracts.
"""
from pathlib import Path
from urllib.parse import unquote, urlsplit
import hashlib
import json

from .presentation import has_legacy_question_image, is_interactive, is_structured, validate_question


class Catalog:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.assets = {}
        self.exams = {}
        self.exam_digests = {}
        self.data = {'materials': [], 'exams': [], 'stats': {}}
        self.stamp = None
        self.refresh()

    def refresh(self):
        path = self.root / 'generated/catalog.json'
        # Portable packs live in separate registries so rebuilding the private
        # PDF collection does not discard a newcomer's imported practice.
        pack_paths = sorted((self.root / 'generated/pack-catalogs').glob('*.json'))
        stamp = (path.stat().st_mtime_ns if path.exists() else None,
                 tuple((str(p), p.stat().st_mtime_ns) for p in pack_paths))
        if stamp == self.stamp:
            return
        data = json.loads(path.read_text()) if path.exists() else {'materials': [], 'exams': [], 'stats': {}}
        for pack_path in pack_paths:
            pack = json.loads(pack_path.read_text())
            data.setdefault('materials', []).extend(pack.get('materials', []))
            data.setdefault('exams', []).extend(pack.get('exams', []))
        if pack_paths:
            stats = data.setdefault('stats', {})
            stats['materialFileCount'] = len(data['materials'])
            stats['fileCount'] = len(data['materials']) + len(data.get('excludedSystemFiles', []))
            stats['userPackCount'] = len(pack_paths)
        exams, digests = {}, {}
        supplemental_ids = {entry['id'] for entry in data.get('supplementalExams', [])}
        for summary in [*data.get('exams', []), *data.get('supplementalExams', [])]:
            exam_path = self.root / 'generated/exams' / f"{summary['id']}.json"
            if not exam_path.resolve().is_relative_to((self.root / 'generated/exams').resolve()):
                continue
            if exam_path.is_file():
                raw = exam_path.read_bytes()
                exam = json.loads(raw)
                digests[summary['id']] = hashlib.sha256(raw).hexdigest()
                if summary['id'] in supplemental_ids or exam.get('family') == 'essentials':
                    exam.update(supplemental=True, strictEligible=False)
                exams[summary['id']] = exam
            else:
                exams[summary['id']] = {**summary, 'sections': [], 'strictEligible': False, 'scopedEligibility': {},
                    'resourcesOnly': True, '_missingGeneratedExam': True,
                    'warnings': [*summary.get('warnings', []), 'Generated exam file is missing. Reimport the original materials.']}
        self.data, self.exams, self.exam_digests, self.stamp = data, exams, digests, stamp
        for material in data.get('materials', []):
            if material.get('url'):
                self.register(material['url'], library=True)
        for exam in exams.values():
            self.register_tree(exam)

    def register_tree(self, value):
        if isinstance(value, dict):
            if isinstance(value.get('url'), str):
                self.register(value['url'])
            for child in value.values():
                self.register_tree(child)
        elif isinstance(value, list):
            for child in value:
                self.register_tree(child)

    def register(self, url, library=False):
        """Map a supported local URL to a stable handle without exposing a disk path."""
        if not isinstance(url, str):
            return None
        part = urlsplit(url).path
        if part.startswith('/materials/'):
            base, relative = self.root / 'data', unquote(part[len('/materials/'):])
        elif part.startswith('/assets/'):
            base, relative = self.root / 'generated/assets', unquote(part[len('/assets/'):])
        else:
            return None
        if not relative or '\x00' in relative or '\\' in relative or '..' in Path(relative).parts or '_analysis' in Path(relative).parts:
            return None
        target = base / relative
        if not target.resolve().is_relative_to(base.resolve()) or not base.resolve().is_relative_to(self.root):
            return None
        asset_id = 'asset-' + hashlib.sha256(part.encode()).hexdigest()[:24]
        old = self.assets.get(asset_id, {})
        self.assets[asset_id] = {'path': target, 'base': base, 'library': library or old.get('library', False)}
        return asset_id

    def path_for(self, asset_id):
        asset = self.assets.get(asset_id)
        if not asset:
            return None
        target = asset['path'].resolve()
        if not target.is_relative_to(asset['base'].resolve()) or not target.is_relative_to(self.root) or not target.is_file():
            return None
        return target

    def summary(self, exam):
        """Derive availability from the current schema, not cached imported flags."""
        keep = ['id', 'title', 'family', 'strictEligible', 'resourcesOnly', 'supplemental', 'warnings',
                'questionCount', 'screenCount', 'autoScorableCount', 'validation', 'adaptiveEligible', 'scopedEligibility', 'timingPolicy', 'sourceMaterialIds']
        result = {key: exam[key] for key in keep if key in exam}
        result['sections'] = []
        for section in exam.get('sections', []):
            questions = [q for module in section.get('modules', []) for q in module.get('questions', [])]
            structured = [q for q in questions if is_structured(q)]
            verified = [q for q in structured if not validate_question(q, strict=True)]
            blocked = [q for q in structured if validate_question(q, strict=True)]
            legacy_images = [q for q in questions if has_legacy_question_image(q)]
            result['sections'].append({'id': section['id'], 'title': section.get('title', section['id']),
                'modules': len(section.get('modules', [])), 'questionCount': len(questions),
                'structuredScreenCount': len(structured),
                'sourceVerifiedStructuredCount': len(verified),
                'structuredReviewOnlyCount': sum(q.get('structuredContentStatus') in ['needs-review', 'source-review-only'] for q in structured),
                'structuredInvalidCount': sum(bool(validate_question(q, strict=False)) for q in structured),
                'structuredBlockedCount': len(blocked),
                'legacyImageReviewOnlyCount': len(legacy_images),
                'essentialVisualCount': sum(sum(a.get('role') == 'essentialVisual' and a.get('highResolution') is True for a in q.get('assets', [])) for q in structured)})
        source_available = [q for s in exam.get('sections', []) for m in s.get('modules', []) for q in m.get('questions', [])
                            if q.get('sourcePromptAvailable') is not False and (not q.get('referenceOnly') or q.get('sourcePromptAvailable') is True)]
        available = [q for q in source_available if is_interactive(q)]
        result['interactiveScreenCount'] = len(available)
        result['interactiveQuestionCount'] = sum(len(q.get('blanks', [])) if q.get('type') == 'cloze' else 1 for q in available)
        structured = [q for q in source_available if is_structured(q)]
        result['structuredScreenCount'] = len(structured)
        result['sourceVerifiedStructuredCount'] = sum(q.get('structuredContentStatus') == 'source-verified' and not validate_question(q, strict=True) for q in structured)
        result['structuredReviewOnlyCount'] = sum(q.get('structuredContentStatus') in ['needs-review', 'source-review-only'] for q in structured)
        result['structuredInvalidCount'] = sum(bool(validate_question(q, strict=False)) for q in structured)
        result['structuredBlockedCount'] = len(structured) - result['sourceVerifiedStructuredCount']
        result['legacyImageReviewOnlyCount'] = sum(has_legacy_question_image(q) for q in source_available)
        result['essentialVisualCount'] = sum(sum(a.get('role') == 'essentialVisual' and a.get('highResolution') is True for a in q.get('assets', [])) for q in structured)
        result['structuredReady'] = bool(source_available) and all(is_structured(q) and not validate_question(q, strict=True) for q in source_available)
        blocked_sections = {section['id'] for section in result['sections']
                            if section['structuredBlockedCount'] or section['legacyImageReviewOnlyCount']}
        if blocked_sections:
            was_globally_eligible = result.get('strictEligible') is True
            result['strictEligible'] = False
            scoped = dict(result.get('scopedEligibility', {}))
            for section in result['sections']:
                scoped.setdefault(section['id'], was_globally_eligible)
            for section_id in blocked_sections:
                scoped[section_id] = False
            result['scopedEligibility'] = scoped
        return result

    def public(self):
        self.refresh()
        materials = []
        for item in self.data.get('materials', []):
            safe = {key: item[key] for key in ['id', 'name', 'kind', 'category', 'bytes', 'pages', 'durationSeconds',
                                              'supplemental', 'examIds', 'warnings', 'scanned', 'sha256'] if key in item}
            asset_id = self.register(item.get('url'), library=True)
            safe.update(assetId=asset_id, url=f'/api/library/{asset_id}' if asset_id else None)
            materials.append(safe)
        return {'schemaVersion': 2, 'generatedAt': self.data.get('generatedAt'), 'stats': self.data.get('stats', {}),
                'materials': materials, 'exams': [self.summary(exam) for exam in self.exams.values()],
                'supplementalExams': [self.summary(exam) for exam in self.exams.values() if exam.get('supplemental')]}
