"""Broken paths/anchors must fail even when no heavy CI scope is selected."""
import importlib.util
from pathlib import Path
import subprocess

import pytest

spec = importlib.util.spec_from_file_location('check_docs', Path(__file__).resolve().parents[1] / 'scripts/check_docs.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_links_include_balanced_paths_reference_style_and_images_but_not_code(tmp_path):
    (tmp_path / 'a(b).md').write_text('# 日本語と `code`\n\n## Same\n\n## Same\n<a id="explicit"></a>\n')
    (tmp_path / 'image.png').write_bytes(b'fixture')
    (tmp_path / 'space name.md').write_text('# Title\n')
    (tmp_path / 'README.md').write_text('''# Entry
[one](a(b).md#日本語と-code) [two](a(b).md#same-1)
[three][target] ![image](image.png)
[space](<space name.md#title>) [explicit](a(b).md#explicit)
[target]: a(b).md#same
`[inline](missing.md)`
~~~md
[example](missing.md)
~~~
    [indented](missing.md)
''')
    result = module.Documents(tmp_path).check(['README.md'])
    assert result['issues'] == [] and result['links'] == 6


@pytest.mark.parametrize('target,code', [
    ('deleted.md', 'missing_local_document'), ('note.md#removed', 'missing_document_anchor'),
    ('../outside.md', 'link_outside_repository'), ('note.md#L0', 'invalid_line_reference'),
    ('note.md#L3', 'invalid_line_reference'), ('note.md#L2-L1', 'invalid_line_reference'),
])
def test_missing_renamed_escaping_and_invalid_line_links_fail(tmp_path, target, code):
    (tmp_path / 'note.md').write_text('# Present\ntext\n')
    (tmp_path / 'README.md').write_text(f'[test]({target})')
    issues = module.Documents(tmp_path).check(['README.md'])['issues']
    assert len(issues) == 1 and issues[0]['code'] == code


def test_deleted_archive_is_checked_against_its_git_ref_without_network(tmp_path):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(tmp_path), *args], text=True).strip()
    git('init', '-q'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.com')
    (tmp_path / 'old.md').write_text('# Preserved\n')
    git('add', '.'); git('commit', '-qm', 'archive')
    git('branch', 'codex/archive/fixture')
    (tmp_path / 'old.md').unlink()
    prefix = 'https://github.com/owner/repo/blob/codex/archive/fixture/'
    (tmp_path / 'README.md').write_text(f'[old]({prefix}old.md#preserved)\n[broken]({prefix}missing.md)\n')
    result = module.Documents(tmp_path, 'owner/repo').check(['README.md'])
    assert result['links'] == 2
    assert len(result['issues']) == 1 and result['issues'][0]['code'] == 'missing_git_document'


def test_external_sites_are_not_fetched(tmp_path):
    (tmp_path / 'README.md').write_text('[external](https://example.invalid/file#section)')
    assert module.Documents(tmp_path).check(['README.md'])['issues'] == []
