"""CI selection must retain affected contracts, including both rename endpoints."""
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('check_scope', Path(__file__).resolve().parents[1] / 'scripts/check_scope.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

@pytest.mark.parametrize('paths,expected', [
    (['docs/next-work.md'], ('none', 'false')),
    (['config/sources.yaml'], ('sources', 'false')),
    (['config/app.yaml'], ('app', 'true')),
    (['config/image-repairs/glucofm-2026-10-11.json'], ('images', 'false')),
    (['src/techkb/fetcher.py'], ('full', 'false')),
    (['web/package-lock.json'], ('none', 'true')),
    (['config/sources.yaml', 'web/quartz.config.ts'], ('sources', 'true')),
    (['src/techkb/publication/note.py'], ('full', 'true')),
    (['requirements.lock'], ('full', 'false')),
    (['src/techkb/normalize.py'], ('full', 'true')),
    (['.github/workflows/checks.yml'], ('full', 'true')),
    (['unknown/path'], ('full', 'true')),
    (['config/sources.yaml', 'moved/sources.yaml'], ('full', 'true')),
])
def test_contract_selection(paths, expected):
    result = module.classify(paths)
    assert (result['python'], result['web']) == expected


def test_mixed_configuration_tests_are_unioned():
    tests = module.selected_tests('app,sources')
    assert 'tests/test_extraction.py' in tests and 'tests/test_publication.py' in tests
    assert len(tests) == len(set(tests))


def test_deleted_and_renamed_paths_use_both_git_endpoints(tmp_path):
    import os
    import subprocess
    import sys
    def git(*args):
        return subprocess.check_output(['git', '-C', str(tmp_path), *args], text=True).strip()
    git('init', '-q'); git('config', 'user.email', 'fixture@example.com'); git('config', 'user.name', 'Fixture')
    (tmp_path / 'config').mkdir(); (tmp_path / 'config/sources.yaml').write_text('sources: []')
    git('add', '.'); git('commit', '-qm', 'base'); base = git('rev-parse', 'HEAD')
    (tmp_path / 'docs').mkdir(); git('mv', 'config/sources.yaml', 'docs/sources.yaml')
    git('commit', '-qam', 'rename'); head = git('rev-parse', 'HEAD')
    result = subprocess.check_output([sys.executable, str(Path(module.__file__)), '--base', base, '--head', head],
                                     cwd=tmp_path, text=True, env={**os.environ, 'GITHUB_OUTPUT': str(tmp_path / 'output')})
    assert result == 'python=sources\nweb=false\n'
    assert (tmp_path / 'output').read_text() == result
    fallback = subprocess.check_output([sys.executable, str(Path(module.__file__)), '--base', '0'*40, '--head', head],
                                       cwd=tmp_path, text=True)
    assert fallback == 'python=full\nweb=true\n'
