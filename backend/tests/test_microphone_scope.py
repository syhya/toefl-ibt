"""Microphone requirements follow the actual frozen selection, not the scope label."""
from backend.tests.test_api import env, start


def test_microphone_summary_follows_selected_questions_and_survives_restoration(env):
    for options, expected in [
        ({'scope': 'all', 'questionIds': ['r1q1', 'build']}, False),
        ({'scope': 'speaking', 'questionIds': ['repeat-0']}, True),
        ({'scope': 'all', 'questionIds': ['repeat-0']}, True),
        ({'scope': 'all'}, True),
    ]:
        saved = start(env, mode='practice', **options)
        assert saved['requiresMicrophone'] is expected
        restored = env['client'].get(f"/api/sessions/{saved['id']}").json()
        assert restored['requiresMicrophone'] is expected
        summary = next(row for row in env['client'].get('/api/sessions').json()['sessions'] if row['id'] == saved['id'])
        assert summary['requiresMicrophone'] is expected
