"""Catalogue item totals must not confuse one cloze screen with one answer."""
from copy import deepcopy

from backend.catalog import Catalog


def test_section_counts_include_every_cloze_blank_and_keep_screen_counts(tmp_path):
    exam = {'id': 'counts', 'sections': [
        {'id': 'reading', 'modules': [
            {'questions': [{'id': 'cloze-one', 'type': 'cloze', 'blanks': [{}, {}, {}]},
                           {'id': 'choice-one', 'type': 'choice'}]},
            {'questions': [{'id': 'cloze-two', 'type': 'cloze', 'blanks': [{}, {}]}]},
        ]},
        {'id': 'writing', 'modules': [
            {'questions': [{'id': 'build-one', 'type': 'build_sentence'},
                           {'id': 'email-one', 'type': 'email'}]},
        ]},
        {'id': 'listening', 'modules': []},
    ]}
    original = deepcopy(exam)

    summary = Catalog(tmp_path).summary(exam)
    sections = {section['id']: section for section in summary['sections']}

    assert sections['reading']['questionCount'] == 6
    assert sections['reading']['screenCount'] == 3
    assert sections['reading']['modules'] == 2
    assert sections['writing']['questionCount'] == sections['writing']['screenCount'] == 2
    assert sections['listening']['questionCount'] == sections['listening']['screenCount'] == 0
    assert summary['interactiveQuestionCount'] == 8
    assert summary['interactiveScreenCount'] == 5
    assert exam == original
