"""Browser fixtures retain the selected source digests without inventing new ones."""
from copy import deepcopy
import json

from scripts import e2e_fixture


def test_subset_fixture_retains_only_original_digests_for_included_questions(tmp_path, monkeypatch):
    (tmp_path / 'generated').mkdir()
    (tmp_path / 'generated/catalog.json').write_text(json.dumps({'materials': []}))
    monkeypatch.setattr(e2e_fixture, 'ROOT', tmp_path)
    monkeypatch.setattr(e2e_fixture, 'SANDBOX', tmp_path / 'fixture')
    source = {'verificationInputs': {'structuredContentSha256ByQuestionId': {
        'included-question': '1' * 64, 'not-in-fixture': '2' * 64,
    }}}
    original = deepcopy(source)
    fixture = {'sections': [{'id': 'speaking', 'modules': [{'questions': [{'id': 'included-question'}]}]}]}

    assert e2e_fixture.verification_inputs(source, fixture) == []
    assert fixture['verificationInputs']['structuredContentSha256ByQuestionId'] == {'included-question': '1' * 64}
    assert source == original
