"""Source-mutation regressions only touch the isolated pytest fixture directory."""
import hashlib
import json

import pytest

from backend.tests.test_api import env, start, begin, action


@pytest.mark.parametrize('mutation', ['same-size-pdf', 'deleted-pdf', 'changed-curation', 'deleted-curation', 'deleted-exam', 'changed-exam', 'deleted-stem'])
def test_stale_or_missing_sources_disable_new_strict_sessions_without_catalog_timestamp_changes(env, mutation):
    client, root = env['client'], env['root']
    before = next(exam for exam in client.get('/api/catalog').json()['exams'] if exam['id'] == 'exam')
    assert before['strictEligible'] is True
    if mutation == 'same-size-pdf':
        path = root / 'data/source.pdf'; path.write_bytes(b'X' * path.stat().st_size)
    elif mutation == 'deleted-pdf':
        (root / 'data/source.pdf').unlink()
    elif mutation == 'changed-curation':
        path = root / 'scripts/verified_fixture.json'; path.write_bytes(b'X' * path.stat().st_size)
    elif mutation == 'deleted-curation':
        (root / 'scripts/verified_fixture.json').unlink()
    elif mutation == 'deleted-exam':
        (root / 'generated/exams/exam.json').unlink()
    elif mutation == 'changed-exam':
        path = root / 'generated/exams/exam.json'; path.write_text(path.read_text().replace('Fixture exam', 'Changed exam', 1))
    else:
        (root / 'generated/assets/stem.jpg').unlink()
    after = next(exam for exam in client.get('/api/catalog').json()['exams'] if exam['id'] == 'exam')
    assert after['strictEligible'] is False
    assert not any(after['scopedEligibility'].values())
    assert after['runtimeVerification']['requiresReimport'] is True
    response = client.post('/api/sessions', json={'examId': 'exam', 'mode': 'strict', 'scope': 'reading'})
    assert response.status_code == 409
    assert 'reimport' in response.json()['error']


def test_old_session_media_uses_its_frozen_hash_after_a_new_import_and_can_still_exit(env):
    a = begin(env, start(env, scope='listening', mode='strict'))
    url = a['question']['audio']['url']
    assert env['client'].get(url).content == b'0123456789'
    earliest = a['audioEarliestEnd']
    # Approve a deliberately changed file in a NEW test import. The old
    # session must not adopt this new catalog hash for its previous prompt.
    changed = b'NEW_PROMPT'
    (env['root'] / 'data/shared.ogg').write_bytes(changed)
    path = env['root'] / 'generated/catalog.json'; catalog = json.loads(path.read_text())
    material = next(m for m in catalog['materials'] if m['id'] == 'audio')
    material['sha256'] = hashlib.sha256(changed).hexdigest(); material['bytes'] = len(changed)
    path.write_text(json.dumps(catalog))
    rejected = env['client'].get(url)
    assert rejected.status_code == 409 and changed not in rejected.content
    current = env['client'].get(f"/api/sessions/{a['id']}").json()
    assert current['audioEarliestEnd'] == earliest and current['deadline'] is None
    assert current['integrity']['interrupted'] is True
    assert current['sourceVersionMatches'] is False
    ended = action(env, current, 'finish')
    assert ended.status_code == 200 and ended.json()['status'] == 'abandoned'
    assert env['client'].get(f"/api/sessions/{a['id']}/review").status_code == 200
    assert env['client'].get('/api/sessions').status_code == 200


def test_same_size_stem_change_does_not_reset_deadline_or_trap_an_active_session(env):
    a = begin(env, start(env, scope='reading', mode='strict'))
    deadline = a['deadline']; url = a['question']['assets'][0]['url']
    source = env['root'] / 'generated/assets/stem.jpg'; source.write_bytes(b'Z' * source.stat().st_size)
    assert env['client'].get(url).status_code == 409
    current = env['client'].get(f"/api/sessions/{a['id']}").json()
    assert current['deadline'] == deadline
    assert current['sourceVersionMatches'] is False
    assert action(env, current, 'interrupt', reason='source-restoration').status_code == 200
    assert action(env, current, 'finish').status_code == 200
    assert env['client'].get(f"/api/sessions/{a['id']}/review").status_code == 200


def test_new_content_id_does_not_inherit_previous_completion_or_overwrite_old_answer(env):
    a = begin(env, start(env, scope='reading', questionIds=['r1q1']))
    a = action(env, a, 'answer', answer='A').json(); action(env, a, 'next')
    assert env['client'].get('/api/questions?q=r1q1').json()['items'][0]['status'] == 'completed'
    path = env['root'] / 'generated/exams/exam.json'; exam = json.loads(path.read_text())
    exam['sections'][0]['modules'][0]['questions'][0]['contentId'] = 'a-new-verified-content-version'
    path.write_text(json.dumps(exam))
    catalog = env['root'] / 'generated/catalog.json'; catalog.write_text(catalog.read_text() + ' ')
    assert env['client'].get('/api/questions?q=r1q1').json()['items'][0]['status'] == 'not_started'
    item = next(s for s in env['client'].get('/api/sessions').json()['sessions'] if s['id'] == a['id'])
    assert item['sourceVersionMatches'] is False
    review = env['client'].get(f"/api/sessions/{a['id']}/review").json()
    assert review['answers'] == {'r1q1': 'A'}


def test_missing_legacy_snapshot_is_explicit_and_unknown_media_is_not_presented_as_frozen(env):
    a = begin(env, start(env, scope='reading'))
    store = env['app'].state.store
    with store.transaction() as db:
        legacy = store.get(db, a['id']); legacy.pop('verificationSnapshot'); legacy.pop('assetManifest')
        for st in legacy['plan']:
            for question in st['questions']:
                question.pop('contentId', None)
        store.save(db, legacy)
    loaded = env['client'].get(f"/api/sessions/{a['id']}").json()
    assert loaded['sourceSnapshotStatus'] == 'legacy-unverified'
    assert loaded['sourceVersionMatches'] is False
    assert loaded['integrity']['eligibleForContinuousStrict'] is False
    assert env['client'].get(a['question']['assets'][0]['url']).status_code == 409
    assert action(env, loaded, 'finish').status_code == 200
    assert env['client'].get(f"/api/sessions/{a['id']}/review").status_code == 200


def test_duplicate_edition_metadata_uses_that_editions_page_and_retains_canonical_page(env):
    path = env['root'] / 'generated/exams/exam.json'; exam = json.loads(path.read_text())
    item = exam['sections'][0]['modules'][0]['questions'][0]
    item['source']['page'] = 27
    item['source']['materialId'] = 'source'
    item['editionSource'] = {'page': 9, 'materialId': 'source', 'url': '/materials/source.pdf#page=9'}
    path.write_text(json.dumps(exam)); catalog = env['root'] / 'generated/catalog.json'; catalog.write_text(catalog.read_text() + ' ')
    row = env['client'].get('/api/questions?q=r1q1').json()['items'][0]
    assert row['sourcePage'] == 9 and row['canonicalSourcePage'] == 27
    assert row['sourceMaterialName'] == 'source.pdf'


def test_late_clock_gap_event_marks_completed_flow_without_changing_score_answers_or_end_time(env):
    a = begin(env, start(env, scope='reading', questionIds=['r1q1']))
    a = action(env, a, 'answer', answer='A').json(); a = action(env, a, 'next').json()
    review_before = env['client'].get(f"/api/sessions/{a['id']}/review").json()
    env['clock'][0] += 7000
    response = action(env, a, 'interrupt', reason='clock-gap')
    assert response.status_code == 200 and response.json()['integrity']['interrupted'] is True
    review_after = env['client'].get(f"/api/sessions/{a['id']}/review").json()
    assert review_before['answers'] == review_after['answers']
    assert review_before['score'] == review_after['score']
    assert review_before['session']['completedAt'] == review_after['session']['completedAt']


def test_history_does_not_advance_locked_practice_branches_as_a_status_oracle(env):
    path = env['root'] / 'generated/exams/adaptive.json'; exam = json.loads(path.read_text())
    exam['sections'][0]['modules'][1]['durationSeconds'] = 1
    path.write_text(json.dumps(exam)); catalog = env['root'] / 'generated/catalog.json'; catalog.write_text(catalog.read_text() + ' ')
    practice = begin(env, start(env, examId='adaptive', scope='reading', routeMode='adaptive'))
    strict = begin(env, start(env, scope='reading', mode='strict'))
    env['clock'][0] += 12000
    locked_history = env['client'].get('/api/sessions').json()['sessions']
    row = next(item for item in locked_history if item['id'] == practice['id'])
    assert row['status'] == 'active'
    with env['app'].state.store.transaction() as db:
        stored = env['app'].state.store.get(db, practice['id'])
        assert stored['stageIndex'] == 0 and stored['routes'] == {}
    action(env, strict, 'finish')
    resumed = env['client'].get(f"/api/sessions/{practice['id']}").json()
    assert resumed['status'] == 'active' and resumed['phase'] == 'directions'
    assert resumed['deadline'] is None and resumed['question'] is None
    with env['app'].state.store.transaction() as db:
        stored = env['app'].state.store.get(db, practice['id'])
        assert next(event['at'] for event in stored['events'] if event['type'] == 'timeout') == practice['startedAt'] + 10000, 'strict lock must not add response time to the previous practice module'
    begun = begin(env, resumed)
    assert begun['remainingSeconds'] == 1
    env['clock'][0] += 1000
    completed = env['client'].get(f"/api/sessions/{practice['id']}").json()
    assert completed['status'] == 'completed'
    assert completed['completedAt'] == begun['deadline'], 'the second module starts only after its Begin screen'


def test_scoring_policy_version_clarifies_unknown_keys_without_changing_old_sessions(env):
    a = start(env, scope='reading')
    assert a['rulesVersion'] == '2026-09-26-timing-scope-v6'
    assert a['scoringPolicy'] == {'verifiedAnswersRequiredForScoring': True, 'unresolvedAnswersExcludedFromScoring': True}
    store = env['app'].state.store
    with store.transaction() as db:
        old = store.get(db, a['id']); old['rulesVersion'] = '2026-08-31-local-v2'; old.pop('scoringPolicy', None); store.save(db, old)
    unchanged = env['client'].get(f"/api/sessions/{a['id']}").json()
    assert unchanged['rulesVersion'] == '2026-08-31-local-v2'
    assert unchanged['scoringPolicy'] is None
