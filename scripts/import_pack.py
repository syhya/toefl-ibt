#!/usr/bin/env python3
"""Validate and import a portable resource pack; paths are relative to its JSON file."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.engine import ExamError
from backend.packs import import_pack


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path, help='Path to pack.json')
    parser.add_argument('--replace', action='store_true', help='Publish a new revision of an existing pack')
    args = parser.parse_args()
    try:
        path=args.manifest.resolve()
        manifest=json.loads(path.read_text(encoding='utf-8'))
        result=import_pack(ROOT, manifest, path.parent, replace=args.replace)
    except (OSError, ValueError, ExamError) as error:
        parser.exit(1, f'Import failed / 导入失败: {error}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print('Resource pack ready. Refresh the app. / 资源包已就绪，请刷新网站。')

if __name__ == '__main__':
    main()
