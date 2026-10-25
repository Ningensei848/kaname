"""Crash boundaries must not silently turn a saved request into another bill."""
import json
from decimal import Decimal

import httpx
import pytest
from google.genai.errors import ServerError, ClientError

from kaname._cli_arguments import parse_args, validate_args
from kaname.audit import audit_state
from kaname.cli import main
from kaname.costs import cost_report
from kaname.pipeline import Pipeline
from kaname.standard_requests import PREFIX, StandardRequests
from kaname.state import State


@pytest.mark.parametrize('mode', ['standard', 'batch'])
def test_ambiguous_response_stops_other_articles_and_later_runs(harness, mode):
    h = harness
    h.fetcher.pages['https://example.com/b'] = b'<article>different article</article>'
    h.sdk.error = httpx.ReadTimeout('private response')
    first = h.pipeline.run()
    assert first.status == 'failed' and len(h.sdk.calls) == first.llm_http_attempts == 1
    assert first.pending_after == 2 and first.source_completed_ids == []
    h.sdk.error = None
    h.app.llm.mode = mode
    later = h.pipeline.run()
    assert later.status == 'failed' and later.llm_calls == 0 and len(h.sdk.calls) == 1
    assert len(State(h.store).pending()) == 2
    assert cost_report(h.store, h.app)['status'] == 'partial'
    assert {'code': 'unresolved_standard_requests', 'count': 1} in audit_state(h.store)['issues']


@pytest.mark.parametrize('error', [httpx.ReadTimeout('private'), httpx.WriteError('private'),
                                  httpx.ConnectError('private'), ServerError(503, {})])
def test_transport_or_server_failure_is_not_replayed(harness, error):
    harness.sdk.error = error
    with pytest.raises(type(error)):
        harness.gemini.enrich({}, 'article')
    assert len(harness.sdk.calls) == 1


def test_explicit_rate_limit_retries_remain_bounded(harness):
    harness.sdk.error = ClientError(429, {})
    with pytest.raises(ClientError):
        harness.gemini.enrich({}, 'article')
    assert len(harness.sdk.calls) == harness.app.llm.retries + 1


@pytest.mark.parametrize('after_response_write', [False, True])
def test_kill_at_response_persistence_never_calls_again(harness, monkeypatch, after_response_write):
    h = harness
    write = h.store.write
    interrupted = False
    def kill(name, data, *args):
        nonlocal interrupted
        if name.startswith('runs/') and interrupted:
            raise KeyboardInterrupt()
        if name.startswith(PREFIX) and json.loads(data)['status'] == 'response':
            interrupted = True
            if after_response_write:
                write(name, data, *args)
            raise KeyboardInterrupt()
        write(name, data, *args)
    monkeypatch.setattr(h.store, 'write', kill)
    with pytest.raises(KeyboardInterrupt):
        h.pipeline.run()
    original = json.loads(h.store.read(h.store.list(PREFIX)[0]))
    monkeypatch.setattr(h.store, 'write', write)
    h.app.llm.model = 'different-model'
    h.source.name = 'changed publisher'
    h.app.llm.max_calls_per_run = 0
    recovered = h.pipeline.run()
    assert len(h.sdk.calls) == 1 and recovered.llm_calls == 0
    if after_response_write:
        assert recovered.recovered == 1 and recovered.status == 'success'
        receipt = json.loads(h.store.read(h.store.list('state/receipts/')[0]))
        assert receipt['usage_run_id'] == original['run_id']
        assert receipt['row']['llm_model'] == original['context']['model']
        assert 'publisher: Example' in receipt['note']
        assert audit_state(h.store)['status'] == 'success'
        cost = cost_report(h.store, h.app)
        assert cost['status'] == 'success' and cost['incomplete_standard_runs'] == 0
        assert Decimal(cost['daily_usd'][original['usage_record']['started_at'][:10]]) == Decimal('0.0000925')
    else:
        assert recovered.status == 'failed' and not h.store.list('notes/')
        assert cost_report(h.store, h.app)['status'] == 'partial'


def test_receipt_write_failure_recovers_saved_response_without_generation(harness):
    h = harness
    h.store.fail_prefix = 'state/receipts/'
    first = h.pipeline.run()
    assert first.status == 'failed' and first.saved == 0
    assert json.loads(h.store.read(h.store.list(PREFIX)[0]))['status'] == 'response'
    h.store.fail_prefix = None
    h.app.llm.max_calls_per_run = 0
    later = h.pipeline.run()
    assert later.recovered == 1 and later.llm_calls == 0 and len(h.sdk.calls) == 1
    assert cost_report(h.store, h.app)['status'] == 'success'


def test_explicit_retry_archives_original_result_and_keeps_both_bills(harness):
    h = harness
    valid_text = h.sdk.text
    h.sdk.text = '{}'
    first = h.pipeline.run()
    name = h.store.list(PREFIX)[0]
    old = json.loads(h.store.read(name))
    h.sdk.text = valid_text
    assert h.pipeline.run().status == 'failed' and len(h.sdk.calls) == 1
    args = parse_args(['run', '--retry-standard-content', old['content_sha256'],
                       '--max-calls', '1', '--max-cost-usd', '1'])
    validate_args(args, h.app)
    assert h.app.llm.retries == 0
    retried = Pipeline(h.app, [h.source], h.store, h.fetcher, h.converter, h.gemini,
        max_cost_usd=args.max_cost_usd, retry_standard_content=args.retry_standard_content).run()
    assert retried.status == 'success' and retried.saved == retried.llm_calls == 1
    assert len(h.sdk.calls) == 2
    assert json.loads(h.store.read(h.store.list('state/standard-request-history/')[0])) == old
    assert json.loads(h.store.read(name))['run_id'] != first.run_id
    cost = cost_report(h.store, h.app)
    assert Decimal(cost['daily_usd'][first.started_at[:10]]) == Decimal('0.000185')


@pytest.mark.parametrize('options', [[], ['--max-calls', '2', '--max-cost-usd', '1'],
    ['--max-calls', '1'], ['--max-calls', '1', '--max-cost-usd', '0'],
    ['--max-calls', '1', '--max-cost-usd', '1', '--llm-mode', 'batch']])
def test_retry_cannot_bypass_single_call_cost_guard(harness, options):
    with pytest.raises(ValueError):
        validate_args(parse_args(['run', '--retry-standard-content', 'a' * 64, *options]), harness.app)


def test_status_is_read_only_and_does_not_disclose_generated_text(harness, tmp_path, capsys, monkeypatch):
    h = harness
    h.sdk.text = '{}'
    h.pipeline.run()
    before = dict(h.store.data)
    for name, data in before.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    assert main(['standard-status', '--state-dir', str(tmp_path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['completed'] == 0 and len(result['requests']) == 1
    assert set(result['requests'][0]) == {'content_sha256', 'run_id', 'status'}
    assert h.store.data == before


def test_malformed_request_cannot_permit_generation(harness):
    harness.store.data[PREFIX + 'a' * 64 + '.json'] = b'{"private": "payload"}'
    assert harness.pipeline.run().status == 'failed'
    assert not harness.sdk.calls


def test_legacy_pending_usage_without_a_request_identity_is_not_replayed(harness):
    from kaname.reporting import RunReport
    from kaname.usage import checkpoint
    old = RunReport(llm_calls=1)
    checkpoint(harness.store, old, pending=True)
    assert StandardRequests(harness.store).status()['legacy_pending_runs'] == [old.run_id]
    assert harness.pipeline.run().status == 'failed'
    assert not harness.sdk.calls


def test_explicit_retry_of_interrupted_reservation_keeps_unknown_original_charge(harness, monkeypatch):
    h = harness
    write = h.store.write
    interrupted = False
    def kill(name, data, *args):
        nonlocal interrupted
        if name.startswith('runs/') and interrupted:
            raise KeyboardInterrupt()
        if name.startswith(PREFIX) and json.loads(data)['status'] == 'response':
            interrupted = True
            raise KeyboardInterrupt()
        write(name, data, *args)
    monkeypatch.setattr(h.store, 'write', kill)
    with pytest.raises(KeyboardInterrupt):
        h.pipeline.run()
    record = json.loads(h.store.read(h.store.list(PREFIX)[0]))
    monkeypatch.setattr(h.store, 'write', write)
    h.app.llm.max_calls_per_run = 1
    retried = Pipeline(h.app, [h.source], h.store, h.fetcher, h.converter, h.gemini,
                      max_cost_usd=1, retry_standard_content=record['content_sha256']).run()
    assert retried.saved == 1 and len(h.sdk.calls) == 2
    assert cost_report(h.store, h.app)['status'] == 'partial'
    assert h.pipeline.run().status == 'success' and len(h.sdk.calls) == 2


def test_a_durable_receipt_survives_later_composer_changes(harness, monkeypatch):
    h = harness
    write = h.store.write
    stopped = False
    def interrupt(name, data, *args):
        nonlocal stopped
        write(name, data, *args)
        if name.startswith('state/receipts/') and not stopped:
            stopped = True
            raise KeyboardInterrupt()
    monkeypatch.setattr(h.store, 'write', interrupt)
    with pytest.raises(KeyboardInterrupt):
        h.pipeline.run()
    receipt = h.store.read(h.store.list('state/receipts/')[0])
    monkeypatch.setattr(h.store, 'write', write)
    def forbidden(*args, **kwargs):
        pytest.fail('a durable receipt must not be recomposed')
    monkeypatch.setattr('kaname.pipeline.compose', forbidden)
    assert h.pipeline.run().recovered == 1
    assert h.store.read(h.store.list('state/receipts/')[0]) == receipt
    assert len(h.sdk.calls) == 1


def test_one_unknown_request_does_not_lose_another_saved_response(harness, monkeypatch):
    import kaname.pipeline as pipeline
    h = harness
    h.fetcher.pages['https://example.com/b'] = b'<article>different article</article>'
    compose = pipeline.compose
    monkeypatch.setattr(pipeline, 'compose', lambda *a, **kw: (_ for _ in ()).throw(ValueError('compose interrupted')))
    generate = h.sdk.generate_content
    count = 0
    def fail_second(**kwargs):
        nonlocal count
        count += 1
        if count == 2:
            raise httpx.ReadTimeout('ambiguous')
        return generate(**kwargs)
    h.sdk.generate_content = fail_second
    assert h.pipeline.run().status == 'failed'
    assert count == 2 and not h.store.list('notes/')
    monkeypatch.setattr(pipeline, 'compose', compose)
    later = h.pipeline.run()
    assert later.status == 'failed' and later.recovered == 1
    assert later.llm_calls == 0 and count == 2


def test_unknown_standard_request_still_allows_existing_batch_result_recovery(harness):
    from test_batch import setup
    h = harness
    batch = setup(h)
    assert h.pipeline.run().batch_submitted == 1
    h.app.llm.mode = 'standard'
    h.fetcher.pages['https://example.com/b'] = b'<article>different new article</article>'
    h.sdk.error = httpx.ReadTimeout('ambiguous')
    assert h.pipeline.run().status == 'failed' and len(h.sdk.calls) == 1
    h.sdk.error = None
    batch.finish()
    recovered = h.pipeline.run()
    assert recovered.status == 'failed' and recovered.batch_saved == 1
    assert recovered.llm_calls == 0 and len(h.sdk.calls) == len(batch.created) == 1
