"""Public help routes return only allowlisted Markdown, without question-data access."""
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app


def test_allowlisted_document_pairs_preserve_markdown_and_code(tmp_path):
    docs = tmp_path / 'docs'
    docs.mkdir()
    english = '# User guide\n\n```sh\nnpm run import:pack -- "my pack.json"\n```\n'
    chinese = '# 使用指南\n\n保留 `npm start` 命令。\n'
    (docs / 'USER_GUIDE.md').write_text(english)
    (docs / 'USER_GUIDE.zh-CN.md').write_text(chinese)
    (tmp_path / 'README.md').write_text('# Public project overview\n')
    (docs / 'README.md').write_text('# Documentation index\n')
    with TestClient(create_app(tmp_path, testing=True)) as client:
        for language, expected in [('en', english), ('zh-CN', chinese)]:
            response = client.get(f'/api/documentation/{language}/USER_GUIDE')
            assert response.status_code == 200
            assert response.text == expected
            assert response.headers['content-type'].startswith('text/plain')
        assert client.get('/api/documentation/en/README').text == '# Public project overview\n'
        assert client.get('/api/documentation/en/DOCUMENTATION_INDEX').text == '# Documentation index\n'


def test_unknown_documents_traversal_and_symlinks_cannot_expose_private_files(tmp_path):
    docs = tmp_path / 'docs'
    docs.mkdir()
    private = tmp_path / 'private.md'
    private.write_text('PRIVATE CONTENT')
    (docs / 'USER_GUIDE.md').symlink_to(private)
    with TestClient(create_app(tmp_path, testing=True)) as client:
        for path in [
            '/api/documentation/en/USER_GUIDE',
            '/api/documentation/en/private',
            '/api/documentation/en/../private.md',
            '/api/documentation/en/%2e%2e%2fprivate.md',
            '/api/documentation/fr/README',
            '/api/documentation/en/DOES_NOT_EXIST',
        ]:
            response = client.get(path)
            assert response.status_code == 404, path
            assert 'PRIVATE CONTENT' not in response.text
