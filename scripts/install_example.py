#!/usr/bin/env python3
"""Install the bundled, full TOEFL iBT Practice Test 1 example without private PDF import tools."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.engine import ExamError
from backend.example_pack import install_example


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT, help='Project directory (defaults to this checkout)')
    parser.add_argument('--upgrade', action='store_true', help='Upgrade an installed lightweight v2 example; stop the server first. Saved sessions and private imports are not rewritten.')
    args = parser.parse_args()
    try:
        result = install_example(args.root, upgrade=args.upgrade)
    except (OSError, ValueError, ExamError) as error:
        parser.exit(1, f'Example installation failed / 例题安装失败: {error}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print('TOEFL iBT Practice Test 1 is ready. Refresh the app. / TOEFL iBT Practice Test 1 已就绪，请刷新网站。')


if __name__ == '__main__':
    main()
