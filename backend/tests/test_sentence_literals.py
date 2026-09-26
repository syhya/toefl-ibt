from copy import deepcopy

from backend.engine import grade, session_grade


def sentence():
    return {'id': 'fixed-literal-fixture', 'type': 'build_sentence',
            'structuredContentStatus': 'source-verified',
            'tokens': ['the cafe', 'visited', 'he', 'the park'],
            'slots': [{'fixed':'Yes. She said'}, {'id':'a'}, {'id':'b'}, {'id':'c'}, {'fixed':'.'}],
            'expectedTokenOrder': [2, 1, 0], 'answer': 'Yes, she said he visited the cafe.'}


def test_correct_tokens_are_not_penalized_for_uneditable_source_punctuation():
    q = sentence(); before = deepcopy(q)
    assert grade(q, {'tokenOrder':['2','1','0']}) == {'correct':1,'total':1}
    assert grade(q, {'tokenOrder':['2','1','3']}) == {'correct':0,'total':1}
    assert grade(q, {'tokenOrder':['1','2','0']}) == {'correct':0,'total':1}
    assert q == before


def test_inconsistent_or_unverified_expected_order_cannot_override_the_key():
    q = sentence(); q['expectedTokenOrder'] = [2, 1, 3]
    assert grade(q, {'tokenOrder':['2','1','3']}) == {'correct':0,'total':1}
    q = sentence(); q.pop('structuredContentStatus')
    assert grade(q, {'tokenOrder':['2','1','0']}) == {'correct':0,'total':1}


def test_existing_score_snapshot_is_not_regraded_by_the_literal_fix():
    q = sentence()
    saved = {'answers':{q['id']:{'tokenOrder':['2','1','0']}},
             'scoreSnapshot':{'score':{'items':{q['id']:{'correct':0,'total':1}}}}}
    before = deepcopy(saved)
    assert session_grade(saved, q) == {'correct':0,'total':1}
    assert saved == before
