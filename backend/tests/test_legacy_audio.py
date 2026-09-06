"""Explicit legacy audio recovery only touches disposable fixture storage."""
import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.tests.test_api import env, start, begin, action


def saved(env, session_id):
    with env['app'].state.store.transaction() as db:
        return env['app'].state.store.get(db, session_id)


def change_saved(env, session_id, change):
    store = env['app'].state.store
    with store.transaction() as db:
        session = store.get(db, session_id)
        change(session)
        store.save(db, session)
    return session


def legacy(env, **options):
    current = begin(env, start(env, scope='listening', **options))
    def remove_baseline(session):
        for key in ['verificationSnapshot', 'assetManifest', 'reviewAssetManifest']:
            session.pop(key, None)
        for stage in session['plan']:
            for question in stage['questions']:
                question.pop('contentId', None)
                question.get('audio', {}).pop('sourceSha256', None)
    change_saved(env, current['id'], remove_baseline)
    return current


def recover(env, session_id, **options):
    return env['client'].post(f'/api/sessions/{session_id}/recover-audio', json={}, **options)


def edit_exam(env, change):
    path = env['root'] / 'generated/exams/exam.json'
    exam = json.loads(path.read_text())
    change(exam)
    path.write_text(json.dumps(exam))
    catalog = env['root'] / 'generated/catalog.json'
    catalog.write_text(catalog.read_text() + ' ')


def test_explicit_recovery_restores_only_current_audio_without_rewriting_history_or_progress(env):
    current = legacy(env)
    url = current['question']['audio']['url']
    before_failure = env['client'].get(url)
    assert before_failure.status_code == 409
    assert before_failure.json()['code'] == 'legacy-audio-unverified'
    loaded = env['client'].get(f"/api/sessions/{current['id']}").json()
    assert loaded['canRecoverAudio'] is True and loaded['audioRecoveryApplied'] is False
    def saved_work(session):
        session['answers']['l1q2'] = 'B'
        session['flags']['l1q2'] = True
        session['audioEarliestEnd'] = env['clock'][0] + 3000
        session['audioPlayed'] = {'previous-track': True}
    change_saved(env, current['id'], saved_work)
    store = env['app'].state.store
    with store.transaction() as db:
        db.execute('INSERT INTO ratings VALUES(?,?,?,?,?)', (current['id'], 'l1q2', 3, 'Saved notes', env['clock'][0]))
        db.execute('INSERT INTO recordings VALUES(?,?,?,?,?,?,?,?,?,?)',
                   ('saved-recording', current['id'], 'l1q2', 'saved-take', 0, 'kept.webm', 'a' * 64,
                    'audio/webm', 10, env['clock'][0]))
    before = saved(env, current['id'])
    env['clock'][0] += 500
    response = recover(env, current['id'])
    assert response.status_code == 200, response.text
    recovered = response.json()
    assert recovered['canRecoverAudio'] is False and recovered['audioRecoveryApplied'] is True
    assert recovered['sourceSnapshotStatus'] == 'legacy-unverified'
    assert recovered['integrity']['sourcesVerified'] is False
    assert recovered['integrity']['eligibleForContinuousStrict'] is False
    assert recovered['sourceVersionMatches'] is False
    after = saved(env, current['id'])
    changed = {'legacyAudioManifest', 'legacyAudioRecovery', 'events', 'revision', 'updatedAt', 'interrupted'}
    assert {key: value for key, value in after.items() if key not in changed} == {
        key: value for key, value in before.items() if key not in changed}
    assert after['events'][:-1] == before['events']
    assert after['events'][-1]['type'] == 'legacy-audio-recovered'
    assert after['revision'] == before['revision'] + 1 and after['interrupted'] is True
    assert after['legacyAudioRecovery']['verification'] == 'current-audio-only-history-unverified'
    assert set(after['legacyAudioManifest']) == {
        env['app'].state.catalog.register('/materials/shared.ogg'), env['app'].state.catalog.register('/materials/other.ogg')}
    with store.transaction() as db:
        assert db.execute('SELECT notes FROM ratings').fetchone()[0] == 'Saved notes'
        assert db.execute('SELECT relative_path FROM recordings').fetchone()[0] == 'kept.webm'
    audio = env['client'].get(url, headers={'Range': 'bytes=0-1'})
    assert audio.status_code == 206 and audio.content == b'01'
    assert audio.headers['Content-Range'] == 'bytes 0-1/10'
    other_id = env['app'].state.catalog.register('/materials/other.ogg')
    assert env['client'].get(f"/api/sessions/{current['id']}/assets/{other_id}").status_code == 403


def test_recovery_is_idempotent_and_persists_after_restart(env):
    current = legacy(env)
    assert recover(env, current['id']).status_code == 200
    first = saved(env, current['id'])
    env['clock'][0] += 1000
    assert recover(env, current['id']).status_code == 200
    assert saved(env, current['id']) == first
    app = create_app(env['root'], clock=lambda: env['clock'][0], testing=True)
    with TestClient(app) as client:
        restored = client.get(f"/api/sessions/{current['id']}").json()
        assert restored['audioRecoveryApplied'] is True and restored['canRecoverAudio'] is False
        assert restored['sourceSnapshotStatus'] == 'legacy-unverified'
        assert client.get(current['question']['audio']['url']).content == b'0123456789'
        assert client.post(f"/api/sessions/{current['id']}/recover-audio", json={}).status_code == 200
    assert saved(env, current['id']) == first


def test_recovery_does_not_tick_an_expired_response_deadline(env):
    current = legacy(env)
    def expire_without_tick(session):
        session['phase'] = 'response'
        session['deadline'] = env['clock'][0] - 1
        session['answers']['l1q1'] = 'A'
    before = change_saved(env, current['id'], expire_without_tick)
    response = recover(env, current['id'])
    assert response.status_code == 200
    after = saved(env, current['id'])
    for field in ['phase', 'deadline', 'answers', 'stageIndex', 'questionIndex', 'mediaIndex', 'audioEarliestEnd', 'plan']:
        assert after.get(field) == before.get(field)


@pytest.mark.parametrize('scope', ['reading', 'speaking', 'all'])
def test_recovery_rejects_plans_outside_listening(env, scope):
    current = begin(env, start(env, scope=scope))
    change_saved(env, current['id'], lambda session: [session.pop(key, None) for key in
                                                    ['verificationSnapshot', 'assetManifest', 'reviewAssetManifest']])
    assert recover(env, current['id']).status_code == 409
    assert 'legacyAudioManifest' not in saved(env, current['id'])


def test_recovery_rejects_strict_completed_and_another_active_strict_session(env):
    practice = legacy(env)
    strict = legacy(env, mode='strict')
    assert recover(env, strict['id']).status_code == 403
    assert recover(env, practice['id']).status_code == 403
    action(env, strict, 'finish')
    action(env, practice, 'finish')
    before = saved(env, practice['id'])
    assert recover(env, practice['id']).status_code == 409
    assert saved(env, practice['id']) == before


@pytest.mark.parametrize('header', [{'Origin': 'https://attacker.example'}, {'Sec-Fetch-Site': 'cross-site'},
                                  {'Host': 'attacker.example'}])
def test_recovery_inherits_loopback_and_cross_origin_protection(env, header):
    current = legacy(env)
    before = saved(env, current['id'])
    assert recover(env, current['id'], headers=header).status_code == 403
    assert saved(env, current['id']) == before


@pytest.mark.parametrize('field,value', [
    ('prompt', 'Different spoken question'), ('answer', 'Different answer'),
    ('transcript', 'Changed source words'), ('context', 'New context'), ('passage', 'New passage'),
    ('type', 'short_answer'), ('taskType', 'announcement'),
    ('choices', [{'id': 'A', 'text': 'Changed choice'}]),
    ('audio', {'url': '/materials/other.ogg', 'durationSeconds': 2, 'groupId': 'shared', 'mediaType': 'audio'}),
])
def test_recovery_rejects_substantive_question_changes(env, field, value):
    current = legacy(env)
    edit_exam(env, lambda exam: exam['sections'][1]['modules'][0]['questions'][0].update({field: value}))
    before = saved(env, current['id'])
    assert recover(env, current['id']).status_code == 409
    assert saved(env, current['id']) == before
    view = env['client'].get(f"/api/sessions/{current['id']}").json()
    assert view['canRecoverAudio'] is False and view['audioRecoveryApplied'] is False


@pytest.mark.parametrize('field,value', [('durationSeconds', 3), ('groupId', 'different-group')])
def test_recovery_rejects_changed_media_identity(env, field, value):
    current = legacy(env)
    edit_exam(env, lambda exam: exam['sections'][1]['modules'][0]['questions'][0]['audio'].update({field: value}))
    assert recover(env, current['id']).status_code == 409


@pytest.mark.parametrize('mutation', ['branch', 'missing-question', 'missing-file', 'changed-file', 'changed-curation'])
def test_recovery_rejects_incomplete_plan_or_invalid_current_sources(env, mutation):
    current = legacy(env)
    if mutation == 'branch':
        change_saved(env, current['id'], lambda session: session['plan'][0].update(branches={'upper': []}))
    elif mutation == 'missing-question':
        edit_exam(env, lambda exam: exam['sections'][1]['modules'][0]['questions'].pop())
    elif mutation == 'missing-file':
        (env['root'] / 'data/other.ogg').unlink()
    elif mutation == 'changed-file':
        (env['root'] / 'data/other.ogg').write_bytes(b'CHANGED AUDIO')
    else:
        (env['root'] / 'scripts/verified_fixture.json').write_text('{}')
    before = saved(env, current['id'])
    assert recover(env, current['id']).status_code == 409
    assert saved(env, current['id']) == before


@pytest.mark.parametrize('expectation', ['snapshot', 'manifest', 'media-hash'])
def test_known_expectations_cannot_be_rebound_or_overridden(env, expectation):
    current = legacy(env)
    asset_id = current['question']['audio']['assetId']
    def known_mismatch(session):
        if expectation == 'snapshot':
            session['verificationSnapshot'] = {'sourceSha256ByUrl': {'/materials/shared.ogg': '0' * 64}}
        elif expectation == 'manifest':
            session['assetManifest'] = {asset_id: {'url': '/materials/shared.ogg', 'sha256': '0' * 64}}
        else:
            session['plan'][0]['questions'][0]['audio']['sourceSha256'] = '0' * 64
    change_saved(env, current['id'], known_mismatch)
    assert recover(env, current['id']).status_code == 409
    response = env['client'].get(current['question']['audio']['url'])
    assert response.status_code == 409 and response.json()['code'] == 'source-changed'
    # A separately bound hash must never supersede the old known mismatch.
    change_saved(env, current['id'], lambda session: session.update(legacyAudioManifest={
        asset_id: {'url': '/materials/shared.ogg', 'sha256': hashlib.sha256(b'0123456789').hexdigest()}}))
    response = env['client'].get(current['question']['audio']['url'])
    assert response.status_code == 409 and response.json()['code'] == 'source-changed'


def test_recovery_remains_bound_to_the_original_recovered_bytes_after_reimport(env):
    current = legacy(env)
    assert recover(env, current['id']).status_code == 200
    recovered = saved(env, current['id'])
    content = b'Newly imported audio'
    (env['root'] / 'data/shared.ogg').write_bytes(content)
    catalog_path = env['root'] / 'generated/catalog.json'
    catalog = json.loads(catalog_path.read_text())
    next(item for item in catalog['materials'] if item['id'] == 'audio').update(
        sha256=hashlib.sha256(content).hexdigest(), bytes=len(content))
    catalog_path.write_text(json.dumps(catalog))
    assert recover(env, current['id']).status_code == 409
    view = env['client'].get(f"/api/sessions/{current['id']}").json()
    assert view['canRecoverAudio'] is False and view['audioRecoveryApplied'] is False
    response = env['client'].get(current['question']['audio']['url'])
    assert response.status_code == 409 and response.json()['code'] == 'source-changed'
    assert saved(env, current['id'])['legacyAudioManifest'] == recovered['legacyAudioManifest']


def test_recovery_requires_an_empty_json_body(env):
    current = legacy(env)
    route = f"/api/sessions/{current['id']}/recover-audio"
    for value in [{'force': True}, [], None]:
        assert env['client'].post(route, content=json.dumps(value),
                                   headers={'Content-Type': 'application/json'}).status_code == 422
    assert env['client'].post(route, content='{}').status_code == 415
