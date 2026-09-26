"""Public help routes return only allowlisted Markdown, without question-data access."""
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app


def test_only_root_readme_is_bilingual_and_old_localized_doc_routes_return_english(tmp_path):
    docs = tmp_path / 'docs'
    docs.mkdir()
    english = '# User guide\n\n```sh\nnpm run import:pack -- "my pack.json"\n```\n'
    chinese = '# 项目介绍\n\n保留 `npm start` 命令。\n'
    (docs / 'USER_GUIDE.md').write_text(english)
    # A stale translated copy must not override the English-only policy.
    (docs / 'USER_GUIDE.zh-CN.md').write_text('STALE TRANSLATION')
    (tmp_path / 'README.zh-CN.md').write_text(chinese)
    (tmp_path / 'README.md').write_text('# Public project overview\n')
    (docs / 'README.md').write_text('# Documentation index\n')
    bundled = tmp_path / 'examples/ets-practice-test-1'
    bundled.mkdir(parents=True)
    for name in ['README', 'NOTICE']:
        (bundled / f'{name}.md').write_text(f'# TOEFL iBT Practice Test 1 {name}\n')
    with TestClient(create_app(tmp_path, testing=True)) as client:
        for language in ['en', 'zh-CN']:
            response = client.get(f'/api/documentation/{language}/USER_GUIDE')
            assert response.status_code == 200
            assert response.text == english
            assert response.headers['content-language'] == 'en'
            assert response.headers['content-type'].startswith('text/plain')
        assert client.get('/api/documentation/en/README').text == '# Public project overview\n'
        translated_readme = client.get('/api/documentation/zh-CN/README')
        assert translated_readme.text == chinese
        assert translated_readme.headers['content-language'] == 'zh-CN'
        assert client.get('/api/documentation/en/DOCUMENTATION_INDEX').text == '# Documentation index\n'
        for doc_id, name in [('BUNDLED_ETS_PRACTICE_TEST_1', 'README'), ('BUNDLED_ETS_PRACTICE_TEST_1_NOTICE', 'NOTICE')]:
            for language in ['en', 'zh-CN']:
                response = client.get(f'/api/documentation/{language}/{doc_id}')
                assert response.status_code == 200
                assert response.text == f'# TOEFL iBT Practice Test 1 {name}\n'
                assert response.headers['content-language'] == 'en'


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


def test_bundled_documents_do_not_follow_intermediate_symlinks(tmp_path):
    hidden = tmp_path / 'storage'
    (hidden / 'ets-practice-test-1').mkdir(parents=True)
    (hidden / 'ets-practice-test-1/NOTICE.md').write_text('PRIVATE CONTENT')
    (tmp_path / 'examples').symlink_to(hidden, target_is_directory=True)
    with TestClient(create_app(tmp_path, testing=True)) as client:
        response = client.get('/api/documentation/en/BUNDLED_ETS_PRACTICE_TEST_1_NOTICE')
        assert response.status_code == 404
        assert 'PRIVATE CONTENT' not in response.text
