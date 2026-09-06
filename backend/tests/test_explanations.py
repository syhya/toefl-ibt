"""Engineering-only examples plus local-source checks; never registered as practice content."""
from copy import deepcopy
from pathlib import Path
import json

import pytest

from backend.explanations import explain


def test_prefers_source_explanation_and_never_mutates_the_question():
    q = {'id': 'source-example', 'type': 'choice', 'answer': 'A', 'explanation': 'The supplied source gives this explanation.'}
    original = deepcopy(q)
    result = explain(q)
    assert result['origin'] == 'source'
    assert result['text'] == q['explanation']
    assert q == original


def test_third_party_analysis_is_labeled_and_known_analysis_conflicts_are_not_hidden():
    q = {'id': 'analysis-example', 'type': 'choice', 'answer': 'C', 'explanation': 'An accompanying guide gives B.',
         'explanationSource': {'materialId': 'analysis-book', 'page': 6, 'official': False, 'origin': 'user-supplied-analysis'},
         'source': {'materialId': 'question-book', 'page': 19},
         'explanationConflict': {'status': 'conflicts-with-original-question-key', 'resolutionEvidence': 'The source question key remains C.'}}
    result = explain(q)
    assert result['origin'] == 'source'
    assert '非 ETS 官方' in result['label']
    assert result['source']['materialId'] == 'analysis-book'
    assert result['source']['page'] == 6
    assert any('评分不因附带解析' in warning for warning in result['warnings'])
    assert q['answer'] == 'C'


def test_unresolved_or_unknown_keys_do_not_produce_correctness_claims():
    q = {'id': 'conflict-example', 'type': 'choice', 'answer': 'A', 'answerConflict': {'status': 'needs-review'}, 'explanation': 'An old source says A.'}
    assert explain(q)['origin'] == 'unavailable'
    assert explain({'type': 'choice', 'choices': [{'id': 'A', 'text': 'A candidate'}]})['origin'] == 'unavailable'
    assert explain({'type': 'email', 'answer': 'sample response'})['origin'] == 'unavailable'


def test_cloze_reconstructs_only_given_verified_letters_and_excludes_conflicted_blanks():
    q = {'id': 'cloze-example', 'type': 'cloze', 'blanks': [
        {'id': 'one', 'number': 1, 'prefix': 'rea', 'missingLetters': 'din', 'suffix': 'g', 'fullWord': 'reading', 'length': 3},
        {'id': 'two', 'number': 2, 'prefix': 'w', 'answer': 'water', 'auditStatus': 'answer-conflict'},
    ]}
    result = explain(q)
    assert result['origin'] == 'local_assistance'
    assert any('reading' in item and 'din' in item for item in result['evidence'])
    assert not any('water' in item for item in result['evidence'])
    assert result['warnings']


def test_sentence_assistance_uses_individual_token_indices_and_retains_unused_blocks():
    q = {'type': 'build_sentence', 'tokens': ['you', 'would', 'like', 'extra'],
         'slots': [{'id': 'a'}, {'id': 'b'}, {'id': 'c'}, {'fixed': 'to visit.'}], 'answer': 'Would you like to visit?'}
    result = explain(q)
    assert result['origin'] == 'local_assistance'
    assert any('would〔词块 2〕 → you〔词块 1〕 → like〔词块 3〕' in item for item in result['evidence'])
    assert any('extra〔词块 4〕' in item for item in result['evidence'])
    assert any('代词主语' in item for item in result['evidence'])


def test_choice_location_quotes_existing_text_without_inventing_a_reason():
    passage = 'Visitors borrow library books during the afternoon. The building closes at six.'
    q = {'type': 'choice', 'answer': 'A', 'choices': [{'id': 'A', 'text': 'Borrow library books'}, {'id': 'B', 'text': 'Purchase new computers'}], 'passage': passage}
    result = explain(q)
    assert result['origin'] == 'local_assistance'
    assert result['evidence'] == ['Visitors borrow library books during the afternoon.']
    assert all(quote in passage for quote in result['evidence'])
    q['passage'] = 'An unrelated source sentence.'
    missing = explain(q)
    assert missing['evidence'] == []
    assert '没有定位到可靠依据' in missing['text']


def test_actual_experience_source_spot_checks_preserve_questions_and_quote_only_imported_text():
    path = Path(__file__).resolve().parents[2] / 'generated/exams/experience-1.json'
    if not path.is_file():
        pytest.skip('Personal source materials are not bundled in a source-only checkout.')
    exam = json.loads(path.read_text())
    questions = [q for s in exam['sections'] for m in s['modules'] for q in m['questions']]
    chosen = [next(q for q in questions if q['type'] == kind) for kind in ['cloze', 'build_sentence', 'choice']]
    for q in chosen:
        before = deepcopy(q)
        explanation = explain(q)
        assert q == before
        assert explanation['origin'] in ['source', 'local_assistance', 'unavailable']
        if q['type'] == 'choice' and explanation.get('evidence'):
            source = q.get('transcript') or q.get('passage') or ''
            assert all(sentence in source for sentence in explanation['evidence'])
    assert chosen[0]['source']['page'] >= 1
