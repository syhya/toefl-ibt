"""Read-only timing and source-preservation checks for every installed archive."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from backend.engine import DEFAULT_TIMING, make_plan, uses_ibt_timing

ROOT = Path(__file__).resolve().parents[2]
PATHS = sorted((ROOT / 'generated/exams').glob('*.json'))


@pytest.mark.parametrize('path', PATHS, ids=lambda p: p.stem)
def test_all_installed_routes_preserve_questions_and_apply_current_timing(path):
    exam = json.loads(path.read_text())
    before = deepcopy(exam)
    if not uses_ibt_timing(exam) and not exam.get('supplemental'):
        pytest.skip('A custom non-iBT source has its own timing contract')
    routes = {'upper'} | {m['route'] for s in exam['sections'] for m in s['modules']
                          if m.get('route') in {'upper', 'lower'}}
    for route in sorted(routes):
        plan = make_plan(exam, {'mode': 'practice', 'route': route}, DEFAULT_TIMING)
        if exam.get('supplemental'):
            assert all(s['timer'] == 'untimed' for s in plan)
        else:
            reading = [s for s in plan if s['section'] == 'reading']
            assert [s['seconds'] for s in reading] == [900, 900]
            writing = [s for s in plan if s['section'] == 'writing']
            assert [s['seconds'] for s in writing] == [360, 420, 600]
            assert all(s['timingBasis'] == 'local' for s in reading)
            for stage in plan:
                if stage['timer'] == 'item':
                    for q in stage['questions']:
                        if q['type'] == 'interview':
                            assert q['_responseSeconds'] == 45
                        elif q['type'] == 'listen_repeat':
                            assert 8 <= q['_responseSeconds'] <= 12
                        elif stage['section'] == 'listening':
                            assert q['_responseSeconds'] == (30 if 'academic' in q.get('taskType', '') else 20)
    assert exam == before, 'Building timed routes must not rewrite source content, media, or keys'
