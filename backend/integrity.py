"""Read-only source/version checks with stat-keyed SHA-256 caching."""
from pathlib import Path
from urllib.parse import urlsplit
import hashlib
import re
import threading

from .presentation import asset_is_active, manifest_issues
from .prepared_sources import optional_originals

HASH = re.compile(r'^[0-9a-f]{64}$')


def canonical_url(url):
    return urlsplit(url).path if isinstance(url, str) else ''


def active_urls(exam_or_plan):
    """Return only assets that may be used during a session, not answer pages."""
    urls = set()
    if isinstance(exam_or_plan, list):
        stages = [(stage.get('section'), stage) for stage in exam_or_plan]
    else:
        stages = [(section['id'], module) for section in exam_or_plan.get('sections', []) for module in section.get('modules', [])]
    def add_media(value):
        if isinstance(value, list):
            for item in value:
                add_media(item)
        elif isinstance(value, dict) and value.get('url'):
            urls.add(canonical_url(value['url']))
    for section, module in stages:
        add_media(module.get('directionsAudio'))
        add_media(module.get('practiceAudio'))
        for question in module.get('questions', []):
            for index, asset in enumerate(question.get('assets', [])):
                if asset_is_active(question, asset, index, section):
                    add_media(asset)
            for key in ['audio', 'directionsAudio', '_moduleDirectionsAudio', 'mediaSequence']:
                add_media(question.get(key))
        for branch in module.get('branches', {}).values():
            urls.update(active_urls(branch))
    return urls


def structured_review_urls(exam_or_plan):
    """Generated source crops for structured questions are review-only assets."""
    urls = set()
    if isinstance(exam_or_plan, list):
        stages = [stage for stage in exam_or_plan]
    else:
        stages = [module for section in exam_or_plan.get('sections', []) for module in section.get('modules', [])]
    for module in stages:
        for question in module.get('questions', []):
            if question.get('presentationSchema') == 'structured-v1':
                for asset in question.get('sourceEvidenceAssets', []):
                    if isinstance(asset, dict) and asset.get('url'):
                        urls.add(canonical_url(asset['url']))
        for branch in module.get('branches', {}).values():
            urls.update(structured_review_urls(branch))
    return urls


class SourceIntegrity:
    def __init__(self, root, catalog):
        self.root, self.catalog = Path(root).resolve(), catalog
        self.cache = {}
        self.hash_reads = 0
        self.cache_hits = 0
        self.lock = threading.RLock()

    def digest(self, path):
        path = Path(path)
        try:
            resolved = path.resolve()
            if not resolved.is_relative_to(self.root) or not resolved.is_file():
                return None
            before = resolved.stat()
            key = (before.st_size, before.st_mtime_ns, before.st_ctime_ns, before.st_ino)
            with self.lock:
                cached = self.cache.get(str(resolved))
                if cached and cached[0] == key:
                    self.cache_hits += 1
                    return cached[1]
                value = hashlib.sha256()
                with resolved.open('rb') as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b''):
                        value.update(chunk)
                after = resolved.stat()
                if key != (after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_ino):
                    return None
                result = value.hexdigest()
                self.cache[str(resolved)] = (key, result)
                self.hash_reads += 1
                return result
        except OSError:
            return None

    def expected_for_url(self, exam, url):
        url = canonical_url(url)
        if url.startswith('/materials/'):
            material = next((m for m in self.catalog.data.get('materials', []) if canonical_url(m.get('url')) == url), None)
            return material.get('sha256') if material else None
        return (exam.get('verificationInputs') or {}).get('assetSha256ByUrl', {}).get(url)

    def check_exam(self, exam):
        issues = []
        optional = optional_originals(self.root, exam, self.catalog, self.digest)
        omitted_originals = []
        def issue(code, **detail):
            item = {'code': code, **detail}
            if item not in issues:
                issues.append(item)
        if not (self.root / 'generated/catalog.json').is_file():
            issue('catalog-missing')
        exam_path = self.root / 'generated/exams' / f"{exam['id']}.json"
        expected_exam = self.catalog.exam_digests.get(exam['id'])
        if not expected_exam or self.digest(exam_path) != expected_exam:
            issue('generated-exam-missing-or-changed')
        inputs = exam.get('verificationInputs') or {}
        curations = inputs.get('curationSha256ByPath')
        if not isinstance(curations, dict) or not curations:
            issue('verification-version-missing')
        else:
            for relative, expected in curations.items():
                if not isinstance(relative, str) or not isinstance(expected, str) or not HASH.fullmatch(expected) or self.digest(self.root / relative) != expected:
                    issue('curation-missing-or-changed', file=relative if isinstance(relative, str) else 'unknown')
        for structured_issue in manifest_issues(exam):
            issue(**structured_issue)
        materials = {m['id']: m for m in self.catalog.data.get('materials', [])}
        by_url = {canonical_url(m.get('url')): m['id'] for m in materials.values()}
        required = set(exam.get('sourceMaterialIds', []))
        def collect(value):
            if isinstance(value, dict):
                for key in ['materialId', 'sourceMaterialId', 'referenceMaterialId']:
                    if isinstance(value.get(key), str):
                        required.add(value[key])
                for key in ['url', 'sourceUrl']:
                    url = canonical_url(value.get(key))
                    if url.startswith('/materials/'):
                        if url in by_url:
                            required.add(by_url[url])
                        else:
                            issue('uncatalogued-source')
                for child in value.values():
                    collect(child)
            elif isinstance(value, list):
                for child in value:
                    collect(child)
        collect(exam.get('sections', []))
        for material_id in required:
            item = materials.get(material_id)
            if not item:
                issue('source-manifest-missing', materialId=material_id)
                continue
            expected = item.get('sha256')
            asset_id = self.catalog.register(item.get('url'), library=True)
            path = self.catalog.path_for(asset_id) if asset_id else None
            raw_path = self.catalog.assets.get(asset_id, {}).get('path')
            if (material_id in optional and path is None and raw_path is not None
                    and raw_path.resolve().is_relative_to((self.root / 'data').resolve())
                    and not raw_path.exists() and not raw_path.is_symlink()
                    and not any(p.is_symlink() for p in raw_path.parents if p.is_relative_to(self.root))):
                omitted_originals.append(material_id)
                continue
            if not path or not isinstance(expected, str) or not HASH.fullmatch(expected) or self.digest(path) != expected:
                issue('source-missing-or-changed', materialId=material_id)
        for url in active_urls(exam):
            expected = self.expected_for_url(exam, url)
            asset_id = self.catalog.register(url)
            path = self.catalog.path_for(asset_id) if asset_id else None
            if not path or not isinstance(expected, str) or not HASH.fullmatch(expected) or self.digest(path) != expected:
                issue('active-asset-missing-or-changed', assetId=asset_id)
        for url in structured_review_urls(exam):
            expected = self.expected_for_url(exam, url)
            asset_id = self.catalog.register(url)
            path = self.catalog.path_for(asset_id) if asset_id else None
            if not path or not isinstance(expected, str) or not HASH.fullmatch(expected) or self.digest(path) != expected:
                issue('structured-review-asset-missing-or-changed', assetId=asset_id)
        report = {'status': 'passed' if not issues else 'invalid', 'requiresReimport': bool(issues), 'issues': issues}
        if optional:
            report.update(mode='prepared-assets', originalSourcesVerified=not omitted_originals,
                          optionalOriginalsMissing=len(omitted_originals))
        return report

    def freeze_assets(self, session, exam):
        manifest = {}
        for url in active_urls(session['plan']):
            asset_id = self.catalog.register(url)
            if not asset_id:
                continue
            expected = self.expected_for_url(exam, url)
            path = self.catalog.path_for(asset_id)
            # Practice-only sources can lack a curation manifest; freeze their
            # actual imported asset now, never substitute it later silently.
            if not expected and path:
                expected = self.digest(path)
            if expected:
                manifest[asset_id] = {'sha256': expected, 'url': url}
        session['assetManifest'] = manifest
        review_manifest = {}
        for url in structured_review_urls(session['plan']):
            asset_id = self.catalog.register(url)
            if not asset_id:
                continue
            expected = self.expected_for_url(exam, url)
            path = self.catalog.path_for(asset_id)
            if not expected and path:
                expected = self.digest(path)
            if expected:
                review_manifest[asset_id] = {'sha256': expected, 'url': url}
        session['reviewAssetManifest'] = review_manifest
        source_urls = set()
        source_ids = set(exam.get('sourceMaterialIds', []))
        def collect(value):
            if isinstance(value, dict):
                for key in ['url', 'sourceUrl']:
                    url = canonical_url(value.get(key))
                    if url.startswith('/materials/'):
                        source_urls.add(url)
                for key in ['materialId', 'sourceMaterialId', 'referenceMaterialId']:
                    if isinstance(value.get(key), str):
                        source_ids.add(value[key])
                for child in value.values():
                    collect(child)
            elif isinstance(value, list):
                for child in value:
                    collect(child)
        collect(exam.get('sections', []))
        sources = {canonical_url(m.get('url')): m.get('sha256') for m in self.catalog.data.get('materials', [])
                   if m['id'] in source_ids or canonical_url(m.get('url')) in source_urls}
        inputs = exam.get('verificationInputs') or {}
        session['verificationSnapshot'] = {'schemaVersion': 1, 'examSha256': self.catalog.exam_digests.get(exam['id']),
            'curationSha256ByPath': dict(inputs.get('curationSha256ByPath', {})), 'sourceSha256ByUrl': sources,
            'assetSha256ByUrl': {item['url']: item['sha256'] for item in manifest.values()},
            'reviewAssetSha256ByUrl': {item['url']: item['sha256'] for item in review_manifest.values()},
            'status': self.check_exam(exam)['status']}
        if inputs.get('packDirectionsPath'):
            session['verificationSnapshot']['packDirectionsPath'] = inputs['packDirectionsPath']
        report = self.check_exam(exam)
        if report.get('mode') == 'prepared-assets':
            session['verificationSnapshot'].update(verificationMode='prepared-assets',
                originalSourcesVerified=report['originalSourcesVerified'])

    def historical_media_hash(self, session, asset_id):
        """Find only a hash already carried by the frozen question metadata."""
        def old_media(value):
            if isinstance(value, dict):
                if value.get('url') and self.catalog.register(value['url']) == asset_id:
                    expected = value.get('sourceSha256')
                    if isinstance(expected, str) and HASH.fullmatch(expected):
                        return expected
                for child in value.values():
                    found = old_media(child)
                    if found:
                        return found
            elif isinstance(value, list):
                for child in value:
                    found = old_media(child)
                    if found:
                        return found
            return None
        return old_media(session['plan'])

    def has_asset_expectation(self, session, asset_id):
        if any((session.get(key) or {}).get(asset_id) for key in ['assetManifest', 'reviewAssetManifest', 'legacyAudioManifest']):
            return True
        if any(self.catalog.register(url) == asset_id for url in
               (session.get('verificationSnapshot') or {}).get('sourceSha256ByUrl', {})):
            return True
        return self.historical_media_hash(session, asset_id) is not None

    def session_asset_matches(self, session, asset_id, path, review=False):
        frozen = session.get('assetManifest', {}).get(asset_id)
        if frozen:
            return self.digest(path) == frozen['sha256']
        frozen_review = session.get('reviewAssetManifest', {}).get(asset_id)
        if frozen_review:
            return review and self.digest(path) == frozen_review['sha256']
        for url, expected in session.get('verificationSnapshot', {}).get('sourceSha256ByUrl', {}).items():
            if self.catalog.register(url) == asset_id:
                return self.digest(path) == expected
        expected = self.historical_media_hash(session, asset_id)
        if expected:
            return self.digest(path) == expected
        recovered = (session.get('legacyAudioManifest') or {}).get(asset_id)
        if (recovered and session.get('mode') == 'practice' and not session.get('verificationSnapshot')
                and not session.get('assetManifest')):
            return self.digest(path) == recovered['sha256']
        # Never replace a missing historical expectation with the latest import
        # hash: that could serve a new prompt for an old frozen question.
        return review
