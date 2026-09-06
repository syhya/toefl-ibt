#!/usr/bin/env python3
"""TEST ONLY: real-catalog UI preview with isolated SQLite/recording storage.

Reads this project's unchanged data/, generated/, shared/ and dist/. All writable
application state is redirected to tmp/qa/full-catalog-preview/storage/. Does not
enable testing mode, replace the clock, synthesize questions, or bypass source
SHA checks. Never use this entry point as the user's normal 4173 launcher.
"""
from pathlib import Path
import argparse
import importlib
import json
import os
import re
import sys
from unittest.mock import patch

sys.dont_write_bytecode = True
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def preview_app(tag=None):
    from backend.storage import Storage

    qa_parent = (PROJECT_ROOT / 'tmp/qa').resolve()
    if tag is not None and not re.fullmatch(r'[a-z0-9_-]{1,32}', tag):
        raise ValueError('Use a short lowercase QA state tag.')
    qa_root = PROJECT_ROOT / 'tmp/qa' / ('full-catalog-preview' + ('-' + tag if tag else ''))
    if qa_root.is_symlink() or not qa_root.resolve().is_relative_to(qa_parent):
        raise RuntimeError('The preview state directory must stay inside tmp/qa.')
    for name in ['data', 'generated', 'dist']:
        if not (PROJECT_ROOT / name).is_dir():
            raise RuntimeError(f'Real source directory is missing: {name}')
    qa_root.mkdir(parents=True, exist_ok=True)
    isolated = Storage(qa_root)
    module = importlib.import_module('backend.app')

    def isolated_storage(source_root):
        if Path(source_root).resolve() != PROJECT_ROOT:
            raise RuntimeError('Unexpected source root supplied to the preview factory.')
        return isolated

    # create_app captures this concrete store in its handlers. The temporary
    # factory substitution is restored before serving requests. Production
    # processes are separate and unaffected by this process-local substitution.
    with patch.object(module, 'Storage', isolated_storage):
        app = module.create_app(PROJECT_ROOT, testing=False)
    assert app.state.store is isolated
    assert isolated.path.resolve().is_relative_to(qa_root.resolve())
    assert app.state.catalog.root == PROJECT_ROOT
    app.state.qa_preview = True

    @app.middleware('http')
    async def mark_preview(request, call_next):
        response = await call_next(request)
        response.headers['X-TOEFL-QA-Preview'] = 'isolated-state-real-sources'
        return response

    return app, qa_root, isolated.path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=4177)
    parser.add_argument('--tag', help='Optional isolated state name; existing QA and user records are retained.')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535 or args.port == 4173:
        parser.error('Choose a valid preview port other than the user service port 4173.')
    app, qa_root, database = preview_app(args.tag)
    info = {'testOnly': True, 'pid': os.getpid(), 'port': args.port,
            'url': f'http://127.0.0.1:{args.port}', 'sourceRoot': str(PROJECT_ROOT),
            'stateRoot': str(qa_root), 'database': str(database),
            'testingMode': False, 'clock': 'real', 'sourceHashGate': 'unchanged production logic'}
    (qa_root / 'preview-info.json').write_text(json.dumps(info, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(info, ensure_ascii=False), flush=True)
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=args.port, log_level='warning', access_log=False)


if __name__ == '__main__':
    main()
