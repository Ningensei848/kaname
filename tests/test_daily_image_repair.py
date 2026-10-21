from pathlib import Path
import json
import subprocess

import pytest

from test_daily_preflight import inputs, selected, workflow


FIXTURE = Path(__file__).parent / 'fixtures/image-repair-plan.json'
PLAN = 'config/image-repairs/' + json.loads(FIXTURE.read_bytes())['note_id'] + '.json'


@pytest.fixture
def plan_workspace(tmp_path):
    plan = tmp_path / PLAN
    plan.parent.mkdir(parents=True)
    plan.write_bytes(FIXTURE.read_bytes())
    return tmp_path


@pytest.mark.parametrize('apply', [False, True])
@pytest.mark.parametrize('success', [False, True])
def test_image_repair_never_selects_collection_or_publication(workflow, apply, success):
    config = inputs(image_repair_plan=PLAN, image_repair_apply=apply)
    job = workflow['jobs']['image-repair']
    assert selected(job['if'], config)
    assert not selected(job['if'], config, ref='refs/heads/feature')
    assert not selected(workflow['jobs']['collect']['if'], config)
    assert not selected(workflow['jobs']['batch-preflight']['if'], config)
    assert job['permissions'] == {'contents': 'read', 'id-token': 'write'}
    assert job['concurrency'] == workflow['jobs']['collect']['concurrency']
    steps = [step for step in job['steps'] if selected(step.get('if', '${{ success() }}'), config, success=success)]
    commands = '\n'.join(step.get('run', '') for step in steps)
    for forbidden in ['args=(run)', 'batch-inspect', 'cost-report', 'notify', 'export-notes']:
        assert forbidden not in commands
    assert ('python scripts/repair_note_images.py' in commands) is success
    for step in steps:
        assert 'GEMINI_API_KEY' not in step.get('env', {})
        assert 'GITHUB_TOKEN' not in step.get('env', {})
    for name in ['publish', 'pages', 'notify-publication']:
        assert not selected(workflow['jobs'][name]['if'], config, success=success,
                            outcomes={'needs.collect.result': 'skipped', 'needs.publish.result': 'skipped',
                                      'needs.pages.result': 'skipped', 'needs.collect.outputs.ready': ''})


@pytest.mark.parametrize('override', [
    {'batch_preflight': True}, {'publish_only': True}, {'verification_run_id': 'saved'},
    {'diagnostic_batch_id': 'saved'}, {'expected_success_before': '0'},
    {'collection_mode': 'standard'}, {'max_calls': '0'}, {'max_output_tokens':'4096'},
    {'image_repair_plan': '../private.json'}, {'image_repair_plan': ''},
    {'image_repair_plan': 'config/image-repairs/' + 'a' * 64 + '.json'},
])
def test_conflicting_or_unreviewed_image_plans_fail_before_auth(workflow, override, plan_workspace):
    steps = workflow['jobs']['image-repair']['steps']
    validation = next(step for step in steps if step.get('name') == 'Validate image repair inputs before authentication')
    assert steps.index(validation) < next(i for i, step in enumerate(steps) if step.get('id') == 'gcp_auth')
    config = inputs(image_repair_plan=PLAN) | override
    env = {key.upper(): str(value).lower() for key, value in config.items()}
    env['VERIFY_RUN_ID'] = env.pop('VERIFICATION_RUN_ID')
    result = subprocess.run(['/bin/bash', '-c', validation['run']], env=env, capture_output=True,
                            cwd=plan_workspace)
    assert result.returncode == 1


def test_reviewed_plan_is_admitted_and_normal_schedule_keeps_collection(workflow, plan_workspace):
    validation = next(step for step in workflow['jobs']['image-repair']['steps']
                      if step.get('name') == 'Validate image repair inputs before authentication')
    config = inputs(image_repair_plan=PLAN)
    env = {key.upper(): str(value).lower() for key, value in config.items()}
    env['VERIFY_RUN_ID'] = env.pop('VERIFICATION_RUN_ID')
    result = subprocess.run(['/bin/bash', '-c', validation['run']], env=env, capture_output=True,
                            cwd=plan_workspace)
    assert result.returncode == 0
    assert selected(workflow['jobs']['collect']['if'], inputs())
    assert not selected(workflow['jobs']['image-repair']['if'], inputs())
    assert not selected(workflow['jobs']['collect']['if'], inputs(image_repair_apply=True))
