"""Exercise workflow admission and the side-effect boundary without credentials."""
from pathlib import Path
import re
import subprocess

import pytest
import yaml


@pytest.fixture
def workflow():
    path = Path(__file__).parents[1] / '.github/workflows/daily.yml'
    return yaml.load(path.read_text(), Loader=yaml.BaseLoader)


def selected(expression, inputs, *, success=True, ref='refs/heads/main', outcomes=None):
    # Evaluate this workflow's limited boolean expression dialect, including the
    # implicit success guard. actionlint validates the actual Actions syntax.
    text = expression.removeprefix('${{').removesuffix('}}').strip()
    if not any(function in text for function in ['success()', 'always()']):
        if not success:
            return False
    values = {
        'github.ref': ref, 'steps.gcp_auth.outcome': 'success' if success else 'failure',
        'steps.export.outputs.ready': 'true', 'steps.audit.outcome': 'success',
        'needs.collect.result': 'failure', 'needs.collect.outputs.ready': 'true',
        'needs.publish.result': 'failure', 'needs.pages.result': 'failure',
    }
    values.update(outcomes or {})
    values.update({'inputs.' + key: value for key, value in inputs.items()})
    text = re.sub(r'(?:inputs|github|steps|needs)\.[A-Za-z_.]+',
                  lambda match: repr(values[match[0]]), text)
    text = text.replace('always()', 'True').replace('success()', repr(success))
    text = text.replace('&&', ' and ').replace('||', ' or ')
    text = re.sub(r'!(?!=)', 'not ', text)
    return bool(eval(text, {'__builtins__': {}}, {}))


def inputs(**overrides):
    return dict(batch_preflight=False, publish_only=False, verification_run_id='',
                diagnostic_batch_id='', expected_success_before='',
                collection_mode='configured', max_calls='') | overrides


@pytest.mark.parametrize('success', [True, False])
def test_preflight_skips_paid_work_writes_and_publication_even_on_failure(workflow, success):
    config = inputs(batch_preflight=True)
    assert not selected(workflow['jobs']['collect']['if'], config)
    job = workflow['jobs']['batch-preflight']
    selected_steps = [step for step in job['steps']
                      if selected(step.get('if', '${{ success() }}'), config, success=success)]
    commands = '\n'.join(step.get('run', '') for step in selected_steps)
    for forbidden in ['args=(run)', 'audit-state', 'audit-run', 'batch-inspect',
                      'cost-report', 'notify', 'export-notes']:
        assert forbidden not in commands
    for step in selected_steps:
        assert 'GEMINI_API_KEY' not in step.get('env', {})
        assert 'GITHUB_TOKEN' not in step.get('env', {})
        assert step.get('uses', '') != 'actions/upload-artifact@v7'
    assert ('python scripts/batch_preflight.py' in commands) is success
    assert job['permissions'] == {'contents': 'read', 'id-token': 'write'}
    assert job['concurrency'] == workflow['jobs']['collect']['concurrency']
    for name in ['publish', 'pages', 'notify-publication']:
        assert not selected(workflow['jobs'][name]['if'], config, success=success)
    assert selected(job['if'], config)
    assert not selected(job['if'], config, ref='refs/heads/feature')


@pytest.mark.parametrize('override', [
    {'publish_only': 'true'}, {'verification_run_id': 'saved-run'},
    {'diagnostic_batch_id': 'saved-batch'}, {'expected_success_before': '0'},
    {'max_calls': '0'}, {'collection_mode': 'standard'}, {'collection_mode': 'batch'},
])
def test_preflight_conflicting_inputs_are_rejected_before_auth(workflow, override):
    steps = workflow['jobs']['batch-preflight']['steps']
    validation = next(step for step in steps if step.get('name') == 'Validate preflight inputs before authentication')
    assert steps.index(validation) < next(i for i, step in enumerate(steps) if step.get('id') == 'gcp_auth')
    config = inputs(batch_preflight=True) | override
    env = {key.upper(): str(value).lower() for key, value in config.items()}
    env['VERIFY_RUN_ID'] = env.pop('VERIFICATION_RUN_ID')
    result = subprocess.run(['/bin/bash', '-c', validation['run']], env=env, capture_output=True)
    assert result.returncode == 1


@pytest.mark.parametrize('overrides,expected', [
    ({}, ['Collect', 'Audit saved state', 'Cost and notification plan', 'Publish necessary notifications', 'Export only validated public Notes']),
    ({'publish_only': True}, ['Audit saved state', 'Export only validated public Notes']),
    ({'verification_run_id': 'saved-run'}, ['Verify saved run and state']),
    ({'diagnostic_batch_id': 'saved-batch'}, ['Inspect existing Batch without writes']),
])
def test_existing_modes_keep_operational_steps(workflow, overrides, expected):
    assert selected(workflow['jobs']['collect']['if'], inputs(**overrides))
    assert not selected(workflow['jobs']['batch-preflight']['if'], inputs(**overrides))
    operational = [step for step in workflow['jobs']['collect']['steps'] if any(
        step.get('name', '') == name for name in [
            'Collect', 'Audit saved state', 'Verify saved run and state',
            'Inspect existing Batch without writes', 'Read Batch acceptance baseline without writes',
            'Cost and notification plan', 'Publish necessary notifications', 'Export only validated public Notes'])]
    actual = [step['name'] for step in operational if selected(step['if'], inputs(**overrides))]
    assert actual == expected


@pytest.mark.parametrize('collection_mode', ['', 'configured'])
def test_preflight_valid_inputs_pass(workflow, collection_mode):
    validation = next(step for step in workflow['jobs']['batch-preflight']['steps']
                      if step.get('name') == 'Validate preflight inputs before authentication')
    env = dict(VERIFY_RUN_ID='', DIAGNOSTIC_BATCH_ID='', PUBLISH_ONLY='false',
               COLLECTION_MODE=collection_mode, MAX_CALLS='', EXPECTED_SUCCESS_BEFORE='')
    result = subprocess.run(['/bin/bash', '-c', validation['run']], env=env, capture_output=True)
    assert result.returncode == 0


@pytest.mark.parametrize('stage', ['gcp_auth', 'collection', 'audit', 'export'])
def test_storage_or_export_failure_cannot_advance_publication(workflow, stage):
    config = inputs()
    steps = workflow['jobs']['collect']['steps']
    outcomes = {f'steps.{stage}.outcome': 'failure',
                'steps.export.outputs.ready': '',
                'needs.collect.result': 'failure',
                'needs.collect.outputs.ready': '',
                'needs.publish.result': 'skipped'}
    export = next(step for step in steps if step.get('id') == 'export')
    assert not selected(export['if'], config, success=False, outcomes=outcomes)
    upload = next(step for step in steps if step.get('uses', '').startswith('actions/upload-artifact@'))
    assert not selected(upload['if'], config, success=False, outcomes=outcomes)
    for name in ['publish', 'pages']:
        assert not selected(workflow['jobs'][name]['if'], config, outcomes=outcomes)
    assert selected(workflow['jobs']['notify-publication']['if'], config, success=False, outcomes=outcomes)
    for step in steps:
        if step.get('id') in {'gcp_auth', 'collection', 'audit', 'export'}:
            assert step.get('continue-on-error', 'false') == 'false'
