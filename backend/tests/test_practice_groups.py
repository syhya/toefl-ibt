"""Source grouping and group starts use isolated generated fixtures and storage."""
from copy import deepcopy
import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.tests.test_api import env, start, begin, action, q


def listing(env, **query):
    response = env['client'].get('/api/practice-groups', params=query)
    assert response.status_code == 200, response.text
    return response.json()


def group(env, module='r1', exam='exam', **query):
    return next(item for item in listing(env, **query)['items'] if item['moduleId'] == module and item['examId'] == exam)


def create_group(env, selected, **options):
    return env['client'].post('/api/sessions', json={
        'examId': selected['examId'], 'practiceGroupId': selected['groupId'],
        'expectedGroupContentId': selected['groupContentId'], **options})


def edit_exam(env, change, exam_id='exam'):
    path = env['root'] / f'generated/exams/{exam_id}.json'
    exam = json.loads(path.read_text())
    change(exam)
    path.write_text(json.dumps(exam))
    catalog = env['root'] / 'generated/catalog.json'
    catalog.write_text(catalog.read_text() + ' ')


def saved(env, session_id):
    with env['app'].state.store.transaction() as db:
        return env['app'].state.store.get(db, session_id)


def test_groups_preserve_module_members_before_search_and_pagination_without_private_content(env):
    first = group(env)
    assert first['questionIds'] == ['r1q1', 'r1q2']
    assert first['screenCount'] == first['itemCount'] == first['sourceScreenCount'] == 2
    assert first['unavailableCount'] == first['completedCount'] == 0
    assert first['status'] == 'not_started'
    matching_one = listing(env, q='Question r1q2', section='reading', pageSize=1)
    assert matching_one['total'] == 1 and matching_one['items'] == [first]
    paged = listing(env, section='reading', pageSize=1)
    assert paged['items'][0]['questionIds'] == ['r1q1', 'r1q2']
    assert listing(env, section='reading', page=2, pageSize=1)['items'][0]['questionIds'] == ['r2q1']
    encoded = json.dumps(listing(env))
    for secret in ['SECRET_ANSWER', 'SECRET_TRANSCRIPT', 'SECRET_EXPLANATION', '/materials/', '/assets/',
                   'choices', 'stemBlocks', '_searchText', '_dedupeKey']:
        assert secret not in encoded
    assert listing(env, q='SECRET_ANSWER')['total'] == 0
    assert listing(env, q='SECRET_TRANSCRIPT')['total'] == 0
    assert env['client'].get('/api/questions', params={'q': 'Question r1q2'}).json()['items'][0]['questionId'] == 'r1q2'


def test_contiguous_category_boundaries_exist_before_unavailable_members_are_removed(env):
    def replace(exam):
        exam['sections'][0]['modules'][0]['questions'] = [
            q('part-a1', taskType='daily_life', answer='A'),
            q('hidden-part', taskType='academic_passage', answer='A', sourcePromptAvailable=False),
            q('part-a2', taskType='daily_life', answer='A'),
            q('hidden-a2', taskType='daily_life', answer='A', sourcePromptAvailable=False),
        ]
    edit_exam(env, replace)
    groups = [item for item in listing(env, section='reading', taskType='daily_life')['items'] if item['examId'] == 'exam']
    assert [item['questionIds'] for item in groups] == [['part-a1'], ['part-a2']]
    assert groups[1]['sourceScreenCount'] == 2 and groups[1]['unavailableCount'] == 1
    assert groups[1]['screenCount'] == groups[1]['itemCount'] == 1
    created = create_group(env, groups[1])
    assert created.status_code == 200, created.text
    frozen = saved(env, created.json()['id'])
    assert [question['id'] for stage in frozen['plan'] for question in stage['questions']] == ['part-a2']
    assert frozen['practiceGroup']['unavailableCount'] == 1


def test_cloze_item_counts_and_source_ranges_keep_whole_questions(env):
    def replace(exam):
        exam['sections'][0]['modules'][0]['questions'] = [
            q('cloze-one', 'cloze', taskType='cloze', number=1, numberEnd=3,
              blanks=[{'id': str(index), 'answer': 'word'} for index in range(3)]),
            q('cloze-two', 'cloze', taskType='cloze', number=4, numberEnd=5,
              blanks=[{'id': str(index), 'answer': 'word'} for index in range(2)]),
        ]
    edit_exam(env, replace)
    selected = group(env)
    assert selected['screenCount'] == 2 and selected['itemCount'] == 5
    assert (selected['numberStart'], selected['numberEnd']) == (1, 5)
    assert selected['questionIds'] == ['cloze-one', 'cloze-two']


def test_listening_bundles_a_category_and_counts_shared_stimuli_once(env):
    def categories(exam):
        module = exam['sections'][1]['modules'][0]
        for question in module['questions']:
            question['taskType'] = 'listen_response'
        # Individual group IDs do not split a source category into one-question starts.
        module['questions'][0]['audio']['groupId'] = 'individual-one'
        module['questions'][1]['audio']['groupId'] = 'individual-two'
    edit_exam(env, categories)
    selected = group(env, 'l1')
    assert selected['questionIds'] == ['l1q1', 'l1q2', 'l1q3']
    assert selected['audioCount'] == 2 and selected['hasAudio'] is True
    created = create_group(env, selected)
    assert created.status_code == 200
    assert created.json()['scope'] == 'listening' and created.json()['route'] == 'upper'
    assert created.json()['allowPracticeAids'] is False
    assert len(saved(env, created.json()['id'])['plan'][0]['questions']) == 3


def install_manual_audio(env, remove_item_audio=False):
    content = b'ISOLATED_WHOLE_MODULE_AUDIO'
    (env['root'] / 'data/whole-module.ogg').write_bytes(content)
    path = env['root'] / 'generated/catalog.json'
    catalog = json.loads(path.read_text())
    catalog['materials'].append({'id': 'whole-module-audio', 'name': 'whole-module.ogg', 'kind': 'audio',
                                'url': '/materials/whole-module.ogg', 'sha256': hashlib.sha256(content).hexdigest(),
                                'bytes': len(content)})
    path.write_text(json.dumps(catalog))
    def edit(exam):
        module = exam['sections'][1]['modules'][0]
        module['practiceAudio'] = {'url': '/materials/whole-module.ogg', 'durationSeconds': 10, 'mediaType': 'audio'}
        if remove_item_audio:
            for question in module['questions']:
                question.pop('audio', None)
    edit_exam(env, edit)
    return content


def test_timed_group_audio_count_excludes_an_unused_manual_reference_track(env):
    install_manual_audio(env)
    selected = group(env, 'l1')
    assert selected['hasAudio'] is True and selected['audioCount'] == 2
    created = create_group(env, selected)
    assert created.status_code == 200, created.text
    stage = saved(env, created.json()['id'])['plan'][0]
    assert stage['timer'] == 'item' and stage['practiceAudio'] == []


def test_untimed_group_counts_and_serves_its_sole_manual_primary_audio(env):
    content = install_manual_audio(env, remove_item_audio=True)
    selected = group(env, 'l1')
    assert selected['hasAudio'] is True and selected['audioCount'] == 1
    created = create_group(env, selected)
    assert created.status_code == 200, created.text
    opened = begin(env, created.json())
    assert opened['stage']['timer'] == 'untimed'
    assert len(opened['stage']['practiceAudio']) == 1
    assert env['client'].get(opened['stage']['practiceAudio'][0]['url']).content == content


def test_group_start_derives_lower_route_and_freezes_compact_history_metadata(env):
    selected = group(env, 'lower', 'adaptive')
    created = create_group(env, selected, scope='all', route='upper', allowPracticeAids=True)
    assert created.status_code == 200, created.text
    session = created.json()
    assert session['route'] == 'lower' and session['routeMode'] == 'fixed'
    assert session['scope'] == 'reading' and session['allowPracticeAids'] is True
    assert session['practiceGroup']['groupId'] == selected['groupId']
    assert session['practiceGroup']['groupContentId'] == selected['groupContentId']
    assert 'questionIds' not in session['practiceGroup']
    assert [question['id'] for stage in saved(env, session['id'])['plan'] for question in stage['questions']] == ['lower-question']
    app = create_app(env['root'], clock=lambda: env['clock'][0], testing=True)
    with TestClient(app) as client:
        restored = client.get(f"/api/sessions/{session['id']}").json()
        assert restored['practiceGroup'] == session['practiceGroup']
        row = next(row for row in client.get('/api/sessions').json()['sessions'] if row['id'] == session['id'])
        assert row['practiceGroup'] == session['practiceGroup']


@pytest.mark.parametrize('extra', [{'questionIds': []}, {'taskType': 'choice'}, {'types': ['choice']},
                                  {'questionTypes': ['choice']}, {'mode': 'strict'}, {'routeMode': 'adaptive'},
                                  {'scope': 'listening'}])
def test_group_start_rejects_conflicting_scope_mode_or_member_filters(env, extra):
    assert create_group(env, group(env), **extra).status_code == 422


def test_stale_group_revision_and_removed_members_are_rejected(env):
    before = group(env)
    edit_exam(env, lambda exam: exam['sections'][0]['modules'][0]['questions'][1].update(contentId='new-content-version'))
    after = group(env)
    assert after['groupId'] == before['groupId'] and after['groupContentId'] != before['groupContentId']
    assert create_group(env, before).status_code == 409
    assert create_group(env, after).status_code == 200
    edit_exam(env, lambda exam: exam['sections'][0]['modules'][0]['questions'][1].update(sourcePromptAvailable=False))
    assert create_group(env, after).status_code == 409
    assert group(env)['unavailableCount'] == 1


def test_answer_correction_with_unchanged_content_id_invalidates_start_and_progress(env):
    before = group(env)
    current = begin(env, start(env, scope='reading', questionIds=['r1q1']))
    action(env, current, 'answer', answer='A')
    action(env, current, 'next')
    assert group(env)['completedCount'] == 1
    edit_exam(env, lambda exam: exam['sections'][0]['modules'][0]['questions'][0].update(answer='B'))
    after = group(env)
    assert after['groupId'] == before['groupId'] and after['groupContentId'] != before['groupContentId']
    assert after['completedCount'] == 0 and after['status'] == 'not_started'
    assert create_group(env, before).status_code == 409


def test_changed_module_route_invalidates_old_group_revision_before_any_session_is_saved(env):
    before = group(env, 'upper', 'adaptive')
    assert before['route'] == 'upper'
    edit_exam(env, lambda exam: exam['sections'][0]['modules'][2].update(route='lower'), exam_id='adaptive')
    after = group(env, 'upper', 'adaptive')
    assert after['groupId'] == before['groupId'] and after['questionIds'] == before['questionIds']
    assert after['groupContentId'] != before['groupContentId'] and after['route'] == 'lower'
    assert create_group(env, before).status_code == 409
    with env['app'].state.store.transaction() as db:
        assert db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 0
    created = create_group(env, after)
    assert created.status_code == 200 and created.json()['route'] == 'lower'
    frozen = saved(env, created.json()['id'])
    assert frozen['plan'][0]['route'] == 'lower'
    assert [question['id'] for stage in frozen['plan'] for question in stage['questions']] == after['questionIds']


def test_added_module_directions_audio_invalidates_old_group_and_new_revision_freezes_it(env):
    before = group(env, 'l1')
    directions = {'url': '/materials/shared.ogg', 'durationSeconds': 2, 'mediaType': 'audio', 'kind': 'directions'}
    edit_exam(env, lambda exam: exam['sections'][1]['modules'][0].update(directionsAudio=directions))
    after = group(env, 'l1')
    assert after['groupId'] == before['groupId'] and after['questionIds'] == before['questionIds']
    assert after['groupContentId'] != before['groupContentId']
    assert create_group(env, before).status_code == 409
    with env['app'].state.store.transaction() as db:
        assert db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 0
    created = create_group(env, after)
    assert created.status_code == 200, created.text
    frozen = saved(env, created.json()['id'])
    assert frozen['plan'][0]['questions'][0]['_moduleDirectionsAudio'] == directions
    opened = begin(env, created.json())
    assert opened['question']['audio']['kind'] == 'directions'
    assert env['client'].get(opened['question']['audio']['url']).status_code == 200


def test_progress_never_marks_unvisited_planned_members_complete(env):
    current = start(env, scope='reading')
    assert group(env)['status'] == 'not_started'
    current = begin(env, current)
    assert group(env)['status'] == 'in_progress' and group(env)['completedCount'] == 0
    current = action(env, current, 'answer', answer='A').json()
    # A shared timeout can finish a module while its remaining question was never visited.
    env['clock'][0] += 10_000
    current = env['client'].get(f"/api/sessions/{current['id']}").json()
    action(env, current, 'finish')
    partial = group(env)
    assert partial['completedCount'] == 1 and partial['status'] == 'in_progress'
    second = begin(env, start(env, scope='reading', questionIds=['r1q2']))
    action(env, second, 'answer', answer='An attempted response')
    action(env, second, 'next')
    assert group(env)['completedCount'] == 2 and group(env)['status'] == 'completed'
    # Starting another attempt must not erase the completed current-version history.
    begin(env, start(env, scope='reading'))
    assert group(env)['status'] == 'completed'


def clone_exam(env, reverse=False):
    original = json.loads((env['root'] / 'generated/exams/exam.json').read_text())
    clone = deepcopy(original)
    clone.update(id='clone', title='Second source edition')
    for section in clone['sections']:
        for module in section['modules']:
            for question in module['questions']:
                question['id'] = 'clone-' + question['id']
    if reverse:
        clone['sections'][0]['modules'][0]['questions'].reverse()
    (env['root'] / 'generated/exams/clone.json').write_text(json.dumps(clone))
    path = env['root'] / 'generated/catalog.json'
    catalog = json.loads(path.read_text())
    catalog['exams'].append({'id': 'clone'})
    path.write_text(json.dumps(catalog))


@pytest.mark.parametrize('reverse', [False, True])
def test_deduplication_uses_whole_ordered_content_sequences_and_retains_source_members(env, reverse):
    clone_exam(env, reverse)
    first = group(env)
    duplicate = group(env, exam='clone')
    assert first['groupId'] != duplicate['groupId']
    assert first['groupContentId'] != duplicate['groupContentId'], 'Start revisions are source-bound even when content duplicates.'
    assert first['duplicateCount'] == (1 if reverse else 2)
    deduped = listing(env, section='reading', deduplicate=True)['items']
    r1 = [item for item in deduped if item['moduleId'] == 'r1']
    assert len(r1) == (2 if reverse else 1)
    assert r1[0]['examId'] == 'exam' and r1[0]['questionIds'] == ['r1q1', 'r1q2']
    if reverse:
        assert r1[1]['questionIds'] == ['clone-r1q2', 'clone-r1q1']
    else:
        searched = listing(env, q='Second source edition', deduplicate=True)['items']
        assert all(item['examId'] == 'clone' for item in searched)


def test_server_rejects_a_plan_that_omits_an_advertised_member(env, monkeypatch):
    from backend import engine
    selected = group(env)
    original = engine.new_session
    def incomplete(*args, **kwargs):
        result = original(*args, **kwargs)
        result['plan'][0]['questions'].pop()
        return result
    monkeypatch.setattr(engine, 'new_session', incomplete)
    assert create_group(env, selected).status_code == 409
    with env['app'].state.store.transaction() as db:
        assert db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 0


@pytest.mark.parametrize('query', [{'section': 'bad'}, {'page': 0}, {'pageSize': 101}, {'q': 'a' * 201}])
def test_group_query_validation(env, query):
    assert env['client'].get('/api/practice-groups', params=query).status_code == 422


def test_groups_and_group_starts_obey_strict_isolation_and_request_validation(env):
    selected = group(env)
    cross_origin = env['client'].post('/api/sessions', json={
        'examId': 'exam', 'practiceGroupId': selected['groupId']}, headers={'Origin': 'https://example.invalid'})
    assert cross_origin.status_code == 403
    assert env['client'].post('/api/sessions', json={'examId': 'exam', 'expectedGroupContentId': selected['groupContentId']}).status_code == 422
    assert env['client'].post('/api/sessions', json={'examId': 'exam', 'practiceGroupId': selected['groupId'], 'expectedGroupContentId': None}).status_code == 422
    begin(env, start(env, scope='reading', mode='strict'))
    response = env['client'].get('/api/practice-groups')
    assert response.status_code == 403 and 'items' not in response.json()
    assert create_group(env, selected).status_code == 403
