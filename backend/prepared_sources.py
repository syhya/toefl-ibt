"""Hash-bound provenance for the allowlisted lightweight example only.

Missing originals are a declared distribution property, never a generic
ignore-missing-source switch for private archives or user-authored packs.
"""
import json
import re

PROFILE = {'id': 'ets-practice-test-1', 'version': 3, 'profile': 'runtime-only'}
PROVENANCE = 'generated/assets/ets-practice-test-1/provenance-v3.json'
LEGACY_PROFILE = {'id': 'ets-practice-test-1', 'version': 2, 'profile': 'runtime-only'}
LEGACY_PROVENANCE = 'generated/assets/ets-practice-test-1/provenance.json'


def optional_originals(root, exam, catalog, digest):
    marker = exam.get('bundledExample')
    if exam.get('id') != 'student-1' or marker not in [PROFILE, LEGACY_PROFILE]:
        return {}
    provenance = PROVENANCE if marker == PROFILE else LEGACY_PROVENANCE
    inputs = exam.get('verificationInputs') or {}
    expected = inputs.get('curationSha256ByPath', {}).get(provenance)
    path = root / provenance
    if not expected or digest(path) != expected:
        return {}
    try:
        proof = json.loads(path.read_text())
        records = proof['originalSources']
        if (proof.get('examId') != exam['id'] or proof.get('runtimeProfile') != 'prepared-runtime-v1'
                or not isinstance(records, dict) or not records
                or set(records) != set(exam.get('sourceMaterialIds', []))
                or proof.get('contentSha256ByQuestionId') != inputs.get('structuredContentSha256ByQuestionId')
                or proof.get('runtimeAssetSha256ByUrl') != inputs.get('assetSha256ByUrl')):
            return {}
        materials = {m['id']: m for m in catalog.data.get('materials', [])}
        for material_id, record in records.items():
            actual = materials.get(material_id)
            if (not isinstance(record, dict) or not actual
                    or not re.fullmatch(r'[0-9a-f]{64}', str(record.get('sha256', '')))
                    or not isinstance(record.get('url'), str) or not record['url'].startswith('/materials/')
                    or any(record.get(key) != actual.get(key) for key in ['sha256', 'url', 'kind', 'bytes'])
                    or proof.get('sourceSha256ById', {}).get(material_id) != record.get('sha256')):
                return {}
        return records
    except (OSError, ValueError, KeyError, TypeError):
        return {}
