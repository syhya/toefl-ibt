"""Private source errata must survive every subsequent material import."""
import json
from pathlib import Path

import pytest

from backend.text_corrections import MANIFEST_PATH, field_value, read_manifest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(not (ROOT / MANIFEST_PATH).is_file(), reason='Private source text errata are not installed')
def test_all_source_verified_text_corrections_are_installed_and_clones_agree():
    data = read_manifest(ROOT / MANIFEST_PATH)
    catalog = json.loads((ROOT / 'generated/catalog.json').read_text())
    materials = {m['id']:m for m in catalog['materials']}
    questions = {q['id']:q for path in (ROOT / 'generated/exams').glob('*.json')
                 for s in json.loads(path.read_text()).get('sections',[])
                 for m in s.get('modules',[]) for q in m.get('questions',[])}
    for qid, record in data['questions'].items():
        q = questions[qid]
        assert q['source']['materialId'] == record['materialId']
        assert q['source']['page'] == record['page']
        assert materials[record['materialId']]['sha256'] == record['sourceSha256']
        for patch in record['patches']:
            assert field_value(q,patch['path']) == patch['after'], f"{qid}: {patch['path']}"
        assert q['textCorrection']['version'] == data['version']
    for q in questions.values():
        canonical = q.get('canonicalQuestionId') or q.get('source',{}).get('canonicalQuestionId')
        if canonical not in data['questions']:
            continue
        for patch in data['questions'][canonical]['patches']:
            assert field_value(q,patch['path']) == field_value(questions[canonical],patch['path']), f"{q['id']} alias drift"
    # The user's two reports are explicit regressions, not a general spell rule.
    assert questions['pack-1-listening-m1-6']['choices'][3]['text'].replace('’', "'") == "I'll have to get back to you on that."
    assert questions['pack-1-listening-m1-7']['choices'][3]['text'].replace('’', "'") == "It's a nice room."
