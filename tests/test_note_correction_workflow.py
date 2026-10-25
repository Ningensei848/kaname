from pathlib import Path
import subprocess

import pytest
import yaml

from test_daily_preflight import inputs, selected


@pytest.fixture
def workflow():
    return yaml.load((Path(__file__).parents[1] / '.github/workflows/daily.yml').read_text(), Loader=yaml.BaseLoader)


def env(config):
    result = {key.upper(): str(value).lower() if isinstance(value, bool) else str(value) for key, value in config.items()}
    result['VERIFY_RUN_ID'] = result.pop('VERIFICATION_RUN_ID')
    result['PLAN'] = result.pop('NOTE_CORRECTION_PLAN')
    return result


def test_correction_uses_existing_daily_wif_and_writer_without_paid_collection(workflow):
    job = workflow['jobs']['note-correction']
    config = inputs(note_correction_plan='config/note-corrections/' + 'a' * 64 + '.json')
    assert selected(job['if'], config)
    assert not selected(job['if'], config, ref='refs/heads/feature')
    assert not selected(workflow['jobs']['collect']['if'], config)
    assert job['concurrency'] == workflow['jobs']['collect']['concurrency']
    assert job['permissions'] == {'contents': 'read', 'id-token': 'write'}
    steps = job['steps'];guard = next(s for s in steps if s.get('name') == 'Validate reviewed plan before authentication')
    assert steps.index(guard) < next(i for i,s in enumerate(steps) if s.get('uses') == 'google-github-actions/auth@v3')
    assert 'load_plan' in guard['run'] and 'tests/test_note_corrections.py' in guard['run']
    assert all('GEMINI_API_KEY' not in s.get('env', {}) and 'GITHUB_TOKEN' not in s.get('env', {}) for s in steps)
    assert all('Collect' != s.get('name') for s in steps)
    outcomes={f'needs.{name}.result':'skipped' for name in ('collect','publish','pages')}
    assert all(not selected(workflow['jobs'][name]['if'],config,outcomes=outcomes) for name in ('publish','pages','notify-publication'))
    runner=next(s for s in steps if s.get('name') == 'Preview or apply without Gemini or article fetches')
    assert 'if [[ "$APPLY" == true ]]; then args+=(--apply); fi' in runner['run']
    assert runner['env']['PLAN'] == '${{ inputs.note_correction_plan }}'
    assert runner['env']['APPLY'] == '${{ inputs.note_correction_apply }}'


@pytest.mark.parametrize('override', [{'batch_preflight':True},{'publish_only':True},
    {'verification_run_id':'run'},{'diagnostic_batch_id':'job'}, {'expected_success_before':'0'},
    {'max_calls':'0'},{'max_output_tokens':'2048'},{'max_cost_usd':'0.20'},
    {'retry_standard_content':'a'*64},{'collection_mode':'standard'},
    {'image_repair_plan':'plan'},{'image_repair_apply':True}])
def test_correction_conflicts_fail_before_authentication(workflow, override):
    guard=next(s for s in workflow['jobs']['note-correction']['steps'] if s.get('name') == 'Validate reviewed plan before authentication')
    config=inputs(note_correction_plan='config/note-corrections/'+'a'*64+'.json') | override
    result=subprocess.run(['/bin/bash','-c',guard['run']],env=env(config),capture_output=True)
    assert result.returncode==1


@pytest.mark.parametrize('job_name',['batch-preflight','image-repair'])
def test_other_special_modes_reject_correction_inputs(workflow,job_name):
    guard=next(s for s in workflow['jobs'][job_name]['steps'] if s.get('name','').startswith('Validate'))
    config=inputs(note_correction_plan='config/note-corrections/'+'a'*64+'.json')
    values=env(config);values['NOTE_CORRECTION_PLAN']=values['PLAN']
    result=subprocess.run(['/bin/bash','-c',guard['run']],env=values,capture_output=True)
    assert result.returncode==1


def test_plan_path_guard_admits_only_committed_target(workflow):
    guard=next(s for s in workflow['jobs']['note-correction']['steps'] if s.get('name') == 'Validate reviewed plan before authentication')
    shell=guard['run'].split("python - <<'PY'",1)[0]
    plan=next(Path('config/note-corrections').glob('*.json')).as_posix()
    assert subprocess.run(['/bin/bash','-c',shell],env=env(inputs(note_correction_plan=plan)),capture_output=True).returncode==0
    for invalid in ('', '../plan.json', 'config/note-corrections/'+'f'*64+'.json'):
        assert subprocess.run(['/bin/bash','-c',shell],env=env(inputs(note_correction_plan=invalid)),capture_output=True).returncode==1
