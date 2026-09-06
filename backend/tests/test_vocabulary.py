"""Vocabulary tests only use disposable databases beneath pytest's tmp_path."""
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.storage import Storage
from backend.tests.test_api import env, start, begin, action


def add(env, word='abundant', **fields):
    response = env['client'].post('/api/vocabulary', json={'word': word, **fields})
    assert response.status_code == 200, response.text
    return response.json()


def collection(env, **query):
    response = env['client'].get('/api/vocabulary', params=query)
    assert response.status_code == 200, response.text
    return response.json()


def test_vocabulary_persists_across_restart_with_source_metadata(env):
    assert collection(env) == {'items': [], 'total': 0, 'page': 1, 'pageSize': 24,
                               'summary': {'learning': 0, 'mastered': 0}}
    created = add(env, '  ＡＢＵＮＤＡＮＴ  ', meaning='丰富的', context='Water is abundant here.',
                  sourceLabel='Reading · Fixture exam', sourceQuestionId='r1q1', sourceSessionId='saved-session')
    assert created['created'] is True
    entry = created['entry']
    assert entry == {'id': entry['id'], 'word': 'abundant', 'meaning': '丰富的',
                     'context': 'Water is abundant here.', 'sourceLabel': 'Reading · Fixture exam',
                     'sourceQuestionId': 'r1q1', 'sourceSessionId': 'saved-session',
                     'status': 'learning', 'createdAt': env['clock'][0], 'updatedAt': env['clock'][0]}
    assert env['app'].state.store.path.is_relative_to(env['root'])
    restarted = create_app(env['root'], clock=lambda: env['clock'][0], testing=True)
    with TestClient(restarted) as client:
        restored = client.get('/api/vocabulary').json()
        assert restored['items'] == [entry]
        assert restored['summary'] == {'learning': 1, 'mastered': 0}


@pytest.mark.parametrize('first, duplicate, expected', [
    (' Ａｂｕｎｄａｎｔ ', 'ABUNDANT', 'abundant'),
    ('Cafe\u0301', 'CAFÉ', 'café'),
    ('Straße', 'STRASSE', 'strasse'),
    ('take\u2003part', 'TAKE  PART', 'take part'),
])
def test_normalized_duplicates_preserve_existing_notes_and_status(env, first, duplicate, expected):
    initial = add(env, first, meaning='Original meaning', context='Original context', sourceLabel='Original source')['entry']
    env['clock'][0] += 100
    response = env['client'].patch(f"/api/vocabulary/{initial['id']}", json={'status': 'mastered'})
    saved = response.json()['entry']
    env['clock'][0] += 100
    repeated = add(env, duplicate, meaning='New meaning', context='New context', sourceLabel='New source')
    assert repeated == {'entry': saved, 'created': False}
    assert saved['word'] == expected
    assert collection(env)['total'] == 1


def test_concurrent_adds_create_only_one_entry(env):
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda word: env['client'].post('/api/vocabulary', json={'word': word}),
                                  ['abundant', 'ABUNDANT', 'ＡＢＵＮＤＡＮＴ', ' Abundant ']))
    assert all(response.status_code == 200 for response in responses)
    results = [response.json() for response in responses]
    assert sum(result['created'] for result in results) == 1
    assert len({result['entry']['id'] for result in results}) == 1
    assert collection(env)['total'] == 1


def test_update_search_and_delete_survive_restart(env):
    initial = add(env, meaning='Original meaning', sourceLabel='Original source', sourceQuestionId='r1q1')['entry']
    env['clock'][0] += 500
    response = env['client'].patch(f"/api/vocabulary/{initial['id']}", json={
        'word': '  Resilient ', 'meaning': '有韧性的', 'context': 'A resilient ecosystem.', 'status': 'mastered'})
    assert response.status_code == 200, response.text
    entry = response.json()['entry']
    assert entry == {**initial, 'word': 'resilient', 'meaning': '有韧性的', 'context': 'A resilient ecosystem.',
                     'status': 'mastered', 'updatedAt': env['clock'][0]}
    assert collection(env, q='abundant')['items'] == []
    assert collection(env, q='Original meaning')['items'] == []
    assert collection(env, q='ECOSYSTEM')['items'] == [entry]
    assert collection(env, status='learning')['total'] == 0
    assert collection(env, status='mastered')['items'] == [entry]
    response = env['client'].patch(f"/api/vocabulary/{entry['id']}", json={'meaning': '', 'context': '', 'status': 'learning'})
    assert response.status_code == 200
    assert response.json()['entry']['meaning'] == response.json()['entry']['context'] == ''
    assert env['client'].delete(f"/api/vocabulary/{entry['id']}").json() == {'ok': True}
    assert env['client'].delete(f"/api/vocabulary/{entry['id']}").status_code == 404
    restarted = create_app(env['root'], clock=lambda: env['clock'][0], testing=True)
    with TestClient(restarted) as client:
        assert client.get('/api/vocabulary').json()['total'] == 0


def test_rename_to_existing_word_is_atomic_and_missing_entries_are_404(env):
    first = add(env, 'abundant', meaning='First meaning')['entry']
    second = add(env, 'resilient', meaning='Second meaning')['entry']
    response = env['client'].patch(f"/api/vocabulary/{second['id']}",
                                   json={'word': 'ＡＢＵＮＤＡＮＴ', 'meaning': 'Must not save', 'status': 'mastered'})
    assert response.status_code == 409
    saved = {entry['id']: entry for entry in collection(env)['items']}
    assert saved == {first['id']: first, second['id']: second}
    assert env['client'].patch('/api/vocabulary/missing', json={'meaning': 'No record'}).status_code == 404
    assert env['client'].delete('/api/vocabulary/missing').status_code == 404


def test_search_filters_literal_characters_pagination_and_counts(env):
    for word, meaning, context, label in [
        ('alpha', '生态系统', 'The CAFÉ ecosystem', 'Reading'),
        ('beta', 'A second ecosystem term', 'Other context', 'Listening'),
        ('gamma', '100%_literal', 'Another context', 'Writing'),
    ]:
        env['clock'][0] += 100
        entry = add(env, word, meaning=meaning, context=context, sourceLabel=label)['entry']
        if word == 'beta':
            assert env['client'].patch(f"/api/vocabulary/{entry['id']}", json={'status': 'mastered'}).status_code == 200
    first = collection(env, pageSize=1)
    second = collection(env, page=2, pageSize=1)
    assert first['total'] == second['total'] == 3
    assert [first['items'][0]['word'], second['items'][0]['word']] == ['gamma', 'beta']
    assert collection(env, page=4, pageSize=1)['items'] == []
    assert first['summary'] == {'learning': 2, 'mastered': 1}
    filtered = collection(env, q='ECOSYSTEM', status='mastered')
    assert filtered['total'] == 1 and filtered['items'][0]['word'] == 'beta'
    assert filtered['summary'] == {'learning': 1, 'mastered': 1}
    for query in ['Cafe\u0301', '生态系统', 'Ｒｅａｄｉｎｇ']:
        assert collection(env, q=query)['items'][0]['word'] == 'alpha'
    assert collection(env, q='%_')['items'][0]['word'] == 'gamma'
    assert collection(env, q="' OR 1=1 --")['total'] == 0
    assert collection(env, status='learning')['total'] == 2


@pytest.mark.parametrize('query', [
    {'status': ''}, {'status': 'needs_review'}, {'q': 'x' * 201}, {'q': '\x00'},
    {'page': 0}, {'page': -1}, {'page': '1.0'}, {'page': '1.5'}, {'page': 'abc'},
    {'page': 1_000_001}, {'page': '9' * 100}, {'pageSize': 0}, {'pageSize': 101}, {'pageSize': 'true'},
])
def test_query_validation(env, query):
    assert env['client'].get('/api/vocabulary', params=query).status_code == 422


@pytest.mark.parametrize('payload', [
    {}, {'word': ''}, {'word': ' \t '}, {'word': None}, {'word': 12}, {'word': []},
    {'word': 'x' * 121}, {'word': '\x00invalid'}, {'word': '\ud800'},
    {'word': 'valid', 'meaning': 1}, {'word': 'valid', 'meaning': 'x' * 2001},
    {'word': 'valid', 'context': {}}, {'word': 'valid', 'context': 'x' * 4001},
    {'word': 'valid', 'sourceLabel': ['Reading']}, {'word': 'valid', 'sourceLabel': 'x' * 241},
    {'word': 'valid', 'sourceQuestionId': '../question'}, {'word': 'valid', 'sourceSessionId': 123},
    {'word': 'valid', 'sourceQuestionId': 'x' * 129}, {'word': 'valid', 'sourceSessionId': 'x' * 129},
    {'word': 'valid', 'status': 'mastered'}, {'word': 'valid', 'surprise': True},
])
def test_create_validation_does_not_write(env, payload):
    # ASCII-escaped JSON also exercises surrogate validation without relying
    # on the client library's stricter UTF-8 encoder.
    response = env['client'].post('/api/vocabulary', content=json.dumps(payload),
                                   headers={'Content-Type': 'application/json'})
    assert response.status_code == 422, response.text
    assert collection(env)['total'] == 0


@pytest.mark.parametrize('patch', [
    {}, {'word': False}, {'word': ''}, {'word': 'x' * 121}, {'meaning': None},
    {'context': []}, {'status': 'all'}, {'status': 1}, {'status': {}},
    {'sourceLabel': 'Changed source'}, {'createdAt': 42}, {'updatedAt': 42},
])
def test_update_validation_preserves_entry(env, patch):
    entry = add(env)['entry']
    response = env['client'].patch(f"/api/vocabulary/{entry['id']}", json=patch)
    assert response.status_code == 422, response.text
    assert collection(env)['items'] == [entry]


def test_json_boundary_and_invalid_identifiers(env):
    for body in ['[]', 'null', '{"word": NaN}', '{']:
        assert env['client'].post('/api/vocabulary', content=body,
                                  headers={'Content-Type': 'application/json'}).status_code == 422
    assert env['client'].post('/api/vocabulary', content='{"word":"valid"}').status_code == 415
    for method, payload in [('PATCH', {'meaning': 'valid'}), ('DELETE', None)]:
        response = env['client'].request(method, '/api/vocabulary/invalid!', json=payload)
        assert response.status_code == 422


def test_strict_guard_locks_every_route_without_ticking_sessions_or_mutating_entries(env):
    entry = add(env, meaning='Saved meaning')['entry']
    strict = begin(env, start(env, mode='strict', scope='reading'))
    store = env['app'].state.store
    with store.transaction() as db:
        before_sessions = [row['body'] for row in db.execute('SELECT body FROM sessions ORDER BY rowid')]
        before_entries = [dict(row) for row in db.execute('SELECT * FROM vocabulary')]
    env['clock'][0] += 100_000
    for method, url, payload in [
        ('GET', '/api/vocabulary', None),
        ('GET', '/api/vocabulary?q=saved&status=learning&page=2&pageSize=1', None),
        ('POST', '/api/vocabulary', {'word': 'new'}),
        ('POST', '/api/vocabulary', {'word': 'abundant'}),
        ('PATCH', f"/api/vocabulary/{entry['id']}", {'meaning': 'Changed'}),
        ('DELETE', f"/api/vocabulary/{entry['id']}", None),
        ('DELETE', '/api/vocabulary/missing', None),
    ]:
        response = env['client'].request(method, url, json=payload)
        assert response.status_code == 403, response.text
        assert set(response.json()) == {'error'}
    with store.transaction() as db:
        assert [row['body'] for row in db.execute('SELECT body FROM sessions ORDER BY rowid')] == before_sessions
        assert [dict(row) for row in db.execute('SELECT * FROM vocabulary')] == before_entries
    action(env, strict, 'finish')
    assert collection(env)['items'] == [entry]


def test_vocabulary_inherits_loopback_and_cross_origin_guards(env):
    entry = add(env)['entry']
    assert env['client'].get('/api/vocabulary', headers={'Host': 'attacker.example'}).status_code == 403
    for method, url, payload in [('POST', '/api/vocabulary', {'word': 'new'}),
                                 ('PATCH', f"/api/vocabulary/{entry['id']}", {'status': 'mastered'}),
                                 ('DELETE', f"/api/vocabulary/{entry['id']}", None)]:
        response = env['client'].request(method, url, json=payload, headers={'Origin': 'https://attacker.example'})
        assert response.status_code == 403
    assert collection(env)['items'] == [entry]


def test_existing_database_migration_is_additive_and_repeatable(tmp_path):
    directory = tmp_path / 'storage'
    directory.mkdir()
    session = {'id': 'old-session', 'startedAt': 100, 'updatedAt': 200, 'preserved': ['original', 'data']}
    with sqlite3.connect(directory / 'practice.sqlite3') as db:
        db.execute('CREATE TABLE sessions (id TEXT PRIMARY KEY, body TEXT NOT NULL, '
                   'created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)')
        db.execute('INSERT INTO sessions VALUES (?,?,?,?)', (session['id'], json.dumps(session), 100, 200))
    for _ in range(2):
        store = Storage(tmp_path)
        with store.transaction() as db:
            assert store.get(db, session['id']) == session
            assert db.execute('SELECT COUNT(*) FROM vocabulary').fetchone()[0] == 0
            row = db.execute('SELECT created_at,updated_at FROM sessions WHERE id=?', (session['id'],)).fetchone()
            assert tuple(row) == (100, 200)
