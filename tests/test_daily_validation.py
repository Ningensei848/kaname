"""Daily may reuse only a complete, successful CI result for the running code."""
import copy
from http.client import IncompleteRead
import importlib.util
from pathlib import Path
import subprocess
from urllib.error import URLError

import pytest
import yaml

spec = importlib.util.spec_from_file_location('daily_validation', Path(__file__).resolve().parents[1] / 'scripts/daily_validation.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
SHA = 'a' * 40
ENV = dict(GITHUB_REPOSITORY='owner/repo', GITHUB_SHA=SHA, GH_TOKEN='secret-fixture',
           GITHUB_REF='refs/heads/main', GITHUB_API_URL='https://api.github.com')
RUN = dict(id=123, run_attempt=2, head_sha=SHA, head_branch='main', event='push',
           path='.github/workflows/checks.yml', repository={'full_name': 'owner/repo'},
           status='completed', conclusion='success')
JOBS = [dict(name=name, head_sha=SHA, status='completed', conclusion='success')
        for name in ('scope', 'python-checks', 'web-checks', 'test', 'web-preview')]


def evidence(runs=None, jobs=None, environment=None):
    runs = copy.deepcopy(runs if runs is not None else [RUN])
    jobs = copy.deepcopy(jobs if jobs is not None else JOBS)
    calls = []
    def fetch(path, token):
        calls.append(path)
        assert token == ENV['GH_TOKEN']
        return ({'workflow_runs': runs, 'total_count': len(runs)} if len(calls) == 1 else
                {'jobs': jobs, 'total_count': len(jobs)})
    return module.checks_evidence(environment or ENV, fetch), calls


def test_reuses_same_commit_and_current_attempt():
    value, calls = evidence()
    assert value == dict(unit_tests='checks', reason='same_main_commit_passed',
                         checks_run_id=123, checks_run_attempt=2)
    assert 'head_sha=' + SHA in calls[0] and 'event=push' in calls[0]
    assert calls[1].endswith('/runs/123/attempts/2/jobs?per_page=100')


@pytest.mark.parametrize('field,value', [
    ('head_sha', 'b'*40), ('head_branch', 'feature'), ('event', 'pull_request'),
    ('path', '.github/workflows/other.yml'), ('repository', {'full_name': 'another/repo'}),
    ('status', 'in_progress'), ('conclusion', 'failure'), ('conclusion', 'cancelled'),
    ('run_attempt', 0), ('id', '../other'),
])
def test_other_or_incomplete_ci_runs_fall_back(field, value):
    run = copy.deepcopy(RUN); run[field] = value
    result, calls = evidence(runs=[run])
    assert result['unit_tests'] == 'local' and len(calls) == 1


def test_newer_failed_run_overrides_older_success():
    newer = dict(RUN, id=124, conclusion='failure')
    assert evidence(runs=[RUN, newer])[0]['unit_tests'] == 'local'
    assert evidence(runs=[])[0]['unit_tests'] == 'local'


@pytest.mark.parametrize('field,value', [
    ('GITHUB_REF', 'refs/heads/feature'), ('GITHUB_SHA', 'main'),
    ('GH_TOKEN', ''), ('GITHUB_REPOSITORY', '../other/repo'),
    ('GITHUB_API_URL', 'https://example.org'),
])
def test_missing_context_uses_local_tests_without_network(field, value):
    result, calls = evidence(environment=dict(ENV, **{field: value}))
    assert result['unit_tests'] == 'local' and calls == []


@pytest.mark.parametrize('damage', ['missing', 'duplicate', 'failed', 'skipped', 'running', 'sha'])
def test_required_aggregate_jobs_must_be_complete(damage):
    jobs = copy.deepcopy(JOBS)
    if damage == 'missing': jobs.pop()
    elif damage == 'duplicate': jobs.append(copy.deepcopy(jobs[-1]))
    elif damage == 'running': jobs[-1]['status'] = 'in_progress'
    elif damage == 'sha': jobs[-1]['head_sha'] = 'b'*40
    else: jobs[-1]['conclusion'] = damage
    assert evidence(jobs=jobs)[0]['unit_tests'] == 'local'


@pytest.mark.parametrize('response', [{}, {'total_count': 101, 'workflow_runs': [RUN]},
                                     {'total_count': 1, 'workflow_runs': None}])
def test_malformed_or_paginated_response_falls_back(response):
    assert module.checks_evidence(ENV, lambda *_: response)['unit_tests'] == 'local'


@pytest.mark.parametrize('error', [URLError('secret-fixture'), IncompleteRead(b'secret-fixture'),
                                 TimeoutError('secret-fixture')])
def test_api_failure_does_not_log_credentials(capsys, error):
    def fail(*_): raise error
    assert module.checks_evidence(ENV, fail)['unit_tests'] == 'local'
    assert capsys.readouterr() == ('', '')


@pytest.mark.parametrize('reuse,force', [(True, False), (False, False), (True, True)])
def test_config_always_checked_and_fallback_executes_tests(monkeypatch, reuse, force):
    commands = []
    monkeypatch.setattr(module.subprocess, 'run', lambda cmd, **kw: commands.append((cmd, kw)))
    monkeypatch.setattr(module, 'checks_evidence', lambda _: {'unit_tests': 'checks' if reuse else 'local'})
    module.main(['--full-tests'] if force else [])
    assert commands[0] == ([module.sys.executable, '-m', 'techkb', 'validate-config'], {'check': True})
    assert len(commands) == (1 if reuse and not force else 2)
    if len(commands) == 2:
        assert commands[1] == ([module.sys.executable, '-m', 'pytest', '-q'], {'check': True})


def test_failed_configuration_stops_before_ci_lookup(monkeypatch):
    def fail(*_, **__): raise subprocess.CalledProcessError(1, 'validate-config')
    monkeypatch.setattr(module.subprocess, 'run', fail)
    monkeypatch.setattr(module, 'checks_evidence', lambda _: pytest.fail('config must pass first'))
    with pytest.raises(subprocess.CalledProcessError): module.main([])


def test_invalid_gcs_parallelism_stops_before_ci_lookup_or_generation(monkeypatch):
    commands = []
    monkeypatch.setenv('TECHKB_GCS_READ_WORKERS', '17')
    monkeypatch.setattr(module.subprocess, 'run', lambda command, **_: commands.append(command))
    monkeypatch.setattr(module, 'checks_evidence', lambda _: pytest.fail('invalid bounds must stop first'))
    with pytest.raises(ValueError, match='invalid read workers'):
        module.main([])
    assert commands == [[module.sys.executable, '-m', 'techkb', 'validate-config']]


def test_workflow_validation_precedes_auth_and_collection():
    workflow = yaml.safe_load((Path(__file__).resolve().parents[1] / '.github/workflows/daily.yml').read_text())
    job = workflow['jobs']['collect']
    assert job['permissions']['actions'] == 'read'
    steps = job['steps']
    validation = next(i for i, step in enumerate(steps) if step.get('run') == 'python scripts/daily_validation.py')
    auth = next(i for i, step in enumerate(steps) if step.get('uses', '').startswith('google-github-actions/auth@'))
    collection = next(i for i, step in enumerate(steps) if step.get('id') == 'collection')
    assert validation < auth < collection
    assert steps[validation]['env'] == {'GH_TOKEN': '${{ github.token }}'}
