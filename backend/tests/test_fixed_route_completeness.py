"""A missing fixed branch cannot be presented as a complete section."""
from copy import deepcopy

import pytest

from backend.engine import ExamError, new_session


def paper(section, second_route='upper'):
    def question(part):
        result = {'id': f'{section}-{part}', 'type': 'choice', 'prompt': f'{section} {part}',
                  'taskType': 'common_task' if part == 'common' else 'branch_task',
                  'answer': 'A', 'choices': [{'id': 'A', 'text': 'Answer A'}, {'id': 'B', 'text': 'Answer B'}]}
        if section == 'listening':
            result['audio'] = {'url': f'/audio/{part}.wav', 'groupId': part, 'durationSeconds': 2}
        return result

    return {'id': 'fixed-paper', 'strictEligible': True, 'sections': [{'id': section, 'modules': [
        {'id': f'{section}-m1', 'route': 'common', 'questions': [question('common')]},
        {'id': f'{section}-m2', 'route': second_route, 'questions': [question('second')]},
    ]}]}


@pytest.mark.parametrize('section', ['reading', 'listening'])
@pytest.mark.parametrize('mode', ['strict', 'practice'])
@pytest.mark.parametrize('scope', ['all', 'section'])
def test_missing_fixed_branch_cannot_drop_second_module(section, mode, scope):
    with pytest.raises(ExamError, match='selected fixed route') as error:
        new_session(paper(section), {'mode': mode, 'scope': section if scope == 'section' else scope,
                                     'routeMode': 'fixed', 'route': 'lower'}, 0)
    assert error.value.status == 422


@pytest.mark.parametrize('section', ['reading', 'listening'])
@pytest.mark.parametrize('route', ['upper', 'lower'])
def test_existing_fixed_branch_keeps_router_and_second_module(section, route):
    session = new_session(paper(section, route), {'mode': 'strict', 'scope': section, 'route': route}, 0)
    assert [q['id'] for s in session['plan'] for q in s['questions']] == [f'{section}-common', f'{section}-second']
    assert session['isFullScope'] is True


@pytest.mark.parametrize('section', ['reading', 'listening'])
@pytest.mark.parametrize('route', ['upper', 'lower'])
def test_unbranched_paper_keeps_both_common_modules(section, route):
    session = new_session(paper(section, 'common'), {'mode': 'strict', 'scope': section, 'route': route}, 0)
    assert len(session['plan']) == 2
    assert session['isFullScope'] is True


@pytest.mark.parametrize('section', ['reading', 'listening'])
@pytest.mark.parametrize('selection', ['ids', 'type'])
def test_explicit_common_only_practice_remains_available(section, selection):
    filters = {'questionIds': [f'{section}-common']} if selection == 'ids' else {'taskType': 'common_task'}
    session = new_session(paper(section), {'mode': 'practice', 'scope': section, 'route': 'lower', **filters}, 0)
    assert [q['id'] for s in session['plan'] for q in s['questions']] == [f'{section}-common']
    assert session['isFullScope'] is False


@pytest.mark.parametrize('section', ['reading', 'listening'])
@pytest.mark.parametrize('selection', ['ids', 'type'])
def test_filter_cannot_hide_a_requested_question_in_an_unavailable_branch(section, selection):
    filters = {'questionIds': [f'{section}-common', f'{section}-second']} if selection == 'ids' else {'types': ['choice']}
    with pytest.raises(ExamError, match='selected fixed route'):
        new_session(paper(section), {'mode': 'practice', 'scope': section, 'route': 'lower', **filters}, 0)


def test_filter_for_another_section_does_not_require_an_unused_branch():
    exam = paper('reading')
    exam['sections'].extend(deepcopy(paper('listening', 'lower')['sections']))
    session = new_session(exam, {'mode': 'practice', 'scope': 'all', 'route': 'lower',
                                'questionIds': ['listening-second']}, 0)
    assert [q['id'] for s in session['plan'] for q in s['questions']] == ['listening-second']


@pytest.mark.parametrize('section', ['reading', 'listening'])
def test_empty_selected_branch_cannot_pass_as_complete(section):
    exam = paper(section, 'lower')
    exam['sections'][0]['modules'][1]['questions'] = []
    with pytest.raises(ExamError, match='selected fixed route'):
        new_session(exam, {'mode': 'strict', 'scope': section, 'route': 'lower'}, 0)
