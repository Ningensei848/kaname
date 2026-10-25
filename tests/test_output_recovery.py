"""Keep default costs bounded while allowing an explicit single-call recovery."""
from decimal import Decimal
import json
from types import SimpleNamespace
import subprocess

import pytest
from pydantic import ValidationError
from kaname._cli_arguments import parse_args, validate_args
from kaname.pipeline import Pipeline
from kaname.audit import audit_run
from test_daily_preflight import inputs, workflow


@pytest.mark.parametrize('options', [[], ['--max-calls','1'], ['--max-cost-usd','1'],
    ['--max-calls','2','--max-cost-usd','1'], ['--max-calls','0','--max-cost-usd','1'],
    ['--max-calls','1','--max-cost-usd','NaN'], ['--max-calls','1','--max-cost-usd','1','--llm-mode','batch']])
def test_override_requires_one_budgeted_standard_call(harness, options):
    with pytest.raises(ValueError):
        validate_args(parse_args(['run','--max-output-tokens','4096',*options]),harness.app)
    assert harness.app.llm.max_output_tokens==2048


@pytest.mark.parametrize('value', ['0','-1','65537'])
def test_invalid_token_override_is_rejected(harness, value):
    with pytest.raises(ValueError):
        validate_args(parse_args(['run','--max-output-tokens',value,'--max-calls','1','--max-cost-usd','1']),harness.app)


def test_non_run_and_default_behavior(harness):
    validate_args(parse_args(['run']),harness.app)
    assert harness.app.llm.max_output_tokens==2048 and harness.app.llm.max_calls_per_run==30 and harness.app.llm.retries==3
    with pytest.raises(ValueError):
        validate_args(parse_args(['dry-run','--max-output-tokens','4096','--max-calls','1','--max-cost-usd','1']),harness.app)


def test_larger_output_usage_is_journaled_and_pending_is_preserved(harness):
    h=harness
    h.fetcher.pages['https://example.com/b']=b'<article><h1>Other</h1><p>Other body</p></article>'
    h.app.processing.article_policy='new_only'
    args=parse_args(['run','--max-calls','1','--max-cost-usd','1','--max-output-tokens','4096'])
    validate_args(args,h.app)
    assert h.app.llm.retries==0
    original=h.sdk.generate_content
    def generate(**kwargs):
        assert kwargs['config'].max_output_tokens==4096
        result=original(**kwargs);result.usage_metadata.candidates_token_count=2800
        return result
    h.sdk.generate_content=generate
    report=Pipeline(h.app,[h.source],h.store,h.fetcher,h.converter,h.gemini,max_cost_usd=args.max_cost_usd).run()
    assert report.saved==report.llm_calls==report.llm_http_attempts==1 and report.pending_after==1
    assert report.total_output_tokens==2800 and report.llm_usage_unavailable==0
    assert audit_run(h.store,report.run_id,expected_success_before=0)['status']=='success'
    before=dict(h.store.data);h.app.llm.max_calls_per_run=0
    again=h.pipeline.run()
    assert again.saved==again.llm_calls==0 and len(h.sdk.calls)==1
    assert all(h.store.data[name]==data for name,data in before.items())


def test_truncated_response_is_not_repaired_or_regenerated(harness):
    h=harness;original=h.sdk.generate_content
    def generate(**kwargs):
        result=original(**kwargs);result.text='{"title_ja":"unfinished'
        result.candidates=[SimpleNamespace(finish_reason='MAX_TOKENS')]
        result.usage_metadata.candidates_token_count=2048
        return result
    h.sdk.generate_content=generate
    with pytest.raises(ValidationError):h.gemini.enrich({},'body')
    assert len(h.sdk.calls)==1 and h.gemini.last_usage.output_tokens==2048 and h.gemini.last_usage_available


def test_recovery_timeout_has_one_http_attempt_and_unknown_usage_stops(harness):
    import httpx
    h=harness
    args=parse_args(['run','--max-calls','1','--max-cost-usd','1','--max-output-tokens','4096'])
    validate_args(args,h.app)
    h.sdk.error=httpx.ReadTimeout('private response')
    report=Pipeline(h.app,[h.source],h.store,h.fetcher,h.converter,h.gemini,max_cost_usd=args.max_cost_usd).run()
    assert len(h.sdk.calls)==report.llm_http_attempts==1
    assert report.status=='failed' and report.saved==0 and report.llm_usage_unavailable==1
    assert report.budget_stop_reason=='generation_failed' and report.pending_after==1


@pytest.mark.parametrize('override', [{'max_calls':'2'},{'max_cost_usd':''},{'max_output_tokens':'0'},
    {'max_output_tokens':'65537'},{'max_output_tokens':'$(private)'},{'collection_mode':'batch'},
    {'publish_only':True},{'verification_run_id':'saved'},{'diagnostic_batch_id':'saved'},{'expected_success_before':'0'}])
def test_workflow_conflicts_rejected_before_auth(workflow, override):
    steps=workflow['jobs']['collect']['steps']
    guard=next(s for s in steps if s.get('name')=='Validate execution mode')
    assert steps.index(guard)<next(i for i,s in enumerate(steps) if s.get('id')=='gcp_auth')
    config=inputs(collection_mode='standard',max_calls='1',max_cost_usd='0.20',max_output_tokens='4096')|override
    env={k.upper():str(v).lower() for k,v in config.items()};env['VERIFY_RUN_ID']=env.pop('VERIFICATION_RUN_ID')
    result=subprocess.run(['/bin/bash','-c',guard['run']],env=env,capture_output=True)
    assert result.returncode==1


def test_workflow_admits_recovery_and_passes_it_as_an_argument(workflow):
    steps=workflow['jobs']['collect']['steps'];guard=next(s for s in steps if s.get('name')=='Validate execution mode')
    config=inputs(collection_mode='standard',max_calls='1',max_cost_usd='0.20',max_output_tokens='4096')
    env={k.upper():str(v).lower() for k,v in config.items()};env['VERIFY_RUN_ID']=env.pop('VERIFICATION_RUN_ID')
    assert subprocess.run(['/bin/bash','-c',guard['run']],env=env,capture_output=True).returncode==0
    collect=next(s for s in steps if s.get('id')=='collection')
    assert 'args+=(--max-output-tokens "$MAX_OUTPUT_TOKENS")' in collect['run']


@pytest.mark.parametrize('changes', [dict(retry_standard_content='$(private)'), dict(collection_mode='batch'),
    dict(max_calls='2'), dict(max_cost_usd=''), dict(max_cost_usd='0'), dict(max_cost_usd='NaN'),
    dict(publish_only=True), dict(verification_run_id='saved')])
def test_workflow_rejects_invalid_standard_retry_before_auth(workflow, changes):
    steps = workflow['jobs']['collect']['steps']
    guard = next(step for step in steps if step.get('name') == 'Validate execution mode')
    assert guard['env']['RETRY_STANDARD_CONTENT'] == '${{ inputs.retry_standard_content }}'
    config = inputs(retry_standard_content='a' * 64, collection_mode='standard', max_calls='1', max_cost_usd='1') | changes
    env = {key.upper(): str(value).lower() for key, value in config.items()}
    env['VERIFY_RUN_ID'] = env.pop('VERIFICATION_RUN_ID')
    assert subprocess.run(['/bin/bash', '-c', guard['run']], env=env, capture_output=True).returncode == 1
    assert steps.index(guard) < next(i for i, step in enumerate(steps) if step.get('id') == 'gcp_auth')


def test_workflow_passes_explicit_standard_retry_as_a_quoted_argument(workflow):
    steps = workflow['jobs']['collect']['steps']
    guard = next(step for step in steps if step.get('name') == 'Validate execution mode')
    config = inputs(retry_standard_content='a' * 64, collection_mode='standard', max_calls='1', max_cost_usd='1')
    env = {key.upper(): str(value).lower() for key, value in config.items()}
    env['VERIFY_RUN_ID'] = env.pop('VERIFICATION_RUN_ID')
    assert subprocess.run(['/bin/bash', '-c', guard['run']], env=env, capture_output=True).returncode == 0
    collect = next(step for step in steps if step.get('id') == 'collection')
    assert collect['env']['RETRY_STANDARD_CONTENT'] == '${{ inputs.retry_standard_content }}'
    assert 'args+=(--retry-standard-content "$RETRY_STANDARD_CONTENT")' in collect['run']
