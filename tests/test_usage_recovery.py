import json
from decimal import Decimal
from types import SimpleNamespace

import pytest

from techkb.gemini import response_usage
from techkb.operations import cost_report, notification_plan
from techkb.reporting import RunReport
from techkb.state import State


@pytest.mark.parametrize('counts,available,known', [
    ((100, 20, 5), True, (100, 20, 5)),
    ((None, 20, 5), False, (0, 20, 5)),
    ((100, None, 5), False, (100, 0, 5)),
    ((0, 0, None), False, (0, 0, 0)),
    ((-1, 20, 5), False, (0, 20, 5)),
    ((True, '20', 5), False, (0, 0, 5)),
    ((100, 20, -1), False, (100, 20, 0)),
])
def test_partial_usage_preserves_known_counts(counts, available, known):
    usage, complete = response_usage(SimpleNamespace(usage_metadata=SimpleNamespace(
        prompt_token_count=counts[0], candidates_token_count=counts[1], thoughts_token_count=counts[2])))
    assert complete is available
    assert (usage.input_tokens, usage.output_tokens, usage.thinking_tokens) == known


@pytest.mark.parametrize('prefix', ['state/receipts/', 'notes/', 'state/index/', 'runs/'])
def test_interruption_after_durable_writes_recovers_original_cost_once(harness, monkeypatch, prefix):
    h = harness
    original_write = h.store.write
    interrupted = False
    def write(name, *args):
        nonlocal interrupted
        if name.startswith('runs/') and interrupted:
            raise KeyboardInterrupt()
        original_write(name, *args)
        if name.startswith(prefix):
            interrupted = True
            raise KeyboardInterrupt()
    monkeypatch.setattr(h.store, 'write', write)
    with pytest.raises(KeyboardInterrupt):
        h.pipeline.run()
    assert not h.store.list('runs/') or prefix == 'runs/'
    checkpoint = json.loads(h.store.read(h.store.list('state/standard-usage/')[0]))
    h.app.costs.prices[h.app.llm.model]['standard'].input_usd_per_million = 999
    monkeypatch.setattr(h.store, 'write', original_write)
    after = h.pipeline.run()
    assert after.llm_calls == 0 and len(h.sdk.calls) == 1 and len(State(h.store).rows) == 1
    date = checkpoint['started_at'][:10]
    expected = (Decimal(100) * Decimal(str(checkpoint['token_price']['input_usd_per_million'])) +
                Decimal(25) * Decimal(str(checkpoint['token_price']['output_usd_per_million']))) / 1_000_000
    cost = cost_report(h.store, h.app, date)
    assert Decimal(cost['daily_usd'][date]) == expected
    assert Decimal(cost['monthly_usd'][date[:7]]) == expected
    assert cost['status'] == 'success'
    assert cost_report(h.store, h.app, date) == cost


def test_report_failure_and_schema_failure_preserve_usage(harness):
    h = harness
    h.sdk.text = '{}'
    h.store.fail_prefix = 'runs/'
    h.pipeline.run()
    assert not h.store.list('runs/')
    assert json.loads(h.store.read(h.store.list('state/standard-usage/')[0]))['total_input_tokens'] == 100
    assert cost_report(h.store, h.app)['status'] == 'success'


def test_reservation_failure_stops_before_paid_call(harness):
    harness.store.fail_prefix = 'state/standard-usage/'
    result = harness.pipeline.run()
    assert not harness.sdk.calls
    assert result.status == 'failed' and result.failures[0]['stage'] == 'usage_reserve'


def test_interruption_before_usage_persistence_leaves_unknown_billing(harness, monkeypatch):
    h = harness
    original_write = h.store.write
    def write(name, *args):
        if name.startswith('runs/') or (name.startswith('state/standard-usage/') and json.loads(args[0])['pending'] is False):
            raise KeyboardInterrupt()
        original_write(name, *args)
    monkeypatch.setattr(h.store, 'write', write)
    with pytest.raises(KeyboardInterrupt): h.pipeline.run()
    result = cost_report(h.store, h.app)
    assert result['status'] == 'partial' and result['incomplete_standard_runs'] == 1


def test_old_receipt_recovery_is_compatible_and_reports_uncertainty(harness):
    h = harness
    h.store.fail_prefix = 'notes/'
    h.pipeline.run()
    h.store.fail_prefix = None
    name = h.store.list('state/receipts/')[0]
    receipt = json.loads(h.store.read(name)); receipt.pop('usage_run_id')
    h.store.data[name] = json.dumps(receipt).encode()
    result = h.pipeline.run()
    assert result.recovered == 1 and result.llm_calls == 0 and result.llm_usage_unavailable == 1
    assert cost_report(h.store, h.app)['status'] == 'partial'


def test_unverified_sources_keep_streak_until_actual_completion(harness):
    from test_operations import report
    h = harness
    for i in range(3): report(h, i, failed=True)
    before = notification_plan(h.store, h.app, [h.source.id])
    report(h, 3, source_completed_ids=[], source_ids=[h.source.id])
    assert notification_plan(h.store, h.app, [h.source.id]) == before
    report(h, 4, source_completed_ids=[h.source.id])
    assert notification_plan(h.store, h.app, [h.source.id]) == []


def test_feed_only_success_with_budget_exhaustion_is_not_source_recovery(harness):
    h = harness
    h.app.llm.max_calls_per_run = 0
    result = h.pipeline.run()
    assert result.status == 'success' and result.source_completed_ids == []
    h.app.llm.max_calls_per_run = 30
    assert h.pipeline.run().source_completed_ids == [h.source.id]


def test_multiple_articles_original_month_and_rate_survive_report_loss(harness, monkeypatch):
    h = harness
    original = RunReport
    monkeypatch.setattr('techkb.pipeline.RunReport', lambda **kw: original(**kw,
        run_id='20260930T235959Z-12345678', started_at='2026-09-30T23:59:59+00:00'))
    h.fetcher.pages['https://example.com/b'] = b'<article>Another article</article>'
    h.store.fail_prefix = 'runs/'
    result = h.pipeline.run()
    assert result.llm_calls == 2
    ledger = json.loads(h.store.read(h.store.list('state/standard-usage/')[0]))
    assert ledger['total_input_tokens'] == 200
    h.app.costs.prices[h.app.llm.model]['standard'].input_usd_per_million = 999
    h.store.fail_prefix = None
    monkeypatch.setattr('techkb.pipeline.RunReport', original)
    assert h.pipeline.run().llm_calls == 0
    cost = cost_report(h.store, h.app, '2026-10-06')
    expected = (Decimal(200) * Decimal(str(ledger['token_price']['input_usd_per_million'])) +
                Decimal(50) * Decimal(str(ledger['token_price']['output_usd_per_million']))) / 1_000_000
    assert Decimal(cost['monthly_usd']['2026-09']) == expected
    assert Decimal(cost['monthly_usd']['2026-10']) == 0
    assert len(h.sdk.calls) == 2


@pytest.mark.parametrize('mode', ['standard', 'batch'])
def test_partial_usage_reaches_cost_report_in_both_modes(harness, monkeypatch, mode):
    h = harness
    if mode == 'standard':
        generate = h.sdk.generate_content
        def partial(**kwargs):
            result = generate(**kwargs); result.usage_metadata.prompt_token_count = None; return result
        monkeypatch.setattr(h.sdk, 'generate_content', partial)
        h.pipeline.run()
    else:
        from test_batch import setup
        sdk = setup(h); h.pipeline.run(); sdk.finish()
        sdk.jobs['batches/1'].dest.inlined_responses[0].response.usage_metadata.prompt_token_count = None
        h.pipeline.run()
    costs = cost_report(h.store, h.app)
    assert costs['status'] == 'partial' and costs['uncertain_runs'] == 1
    reports = [json.loads(h.store.read(name)) for name in h.store.list('runs/')]
    assert sum(r['total_output_tokens'] for r in reports) == 20


def test_sources_unprocessed_after_durability_failure_do_not_reset(harness):
    from techkb.config import Source
    from techkb.pending import Candidate
    h = harness
    source_b = Source(id='other', name='Other', feed_url='https://other.example/feed.xml', base_url='https://other.example/')
    h.pipeline.sources.append(source_b)
    # Both feeds succeed, but the first article's Note storage stops the loop.
    h.fetcher.pages['https://other.example/b'] = b'<article>Other source</article>'
    h.store.fail_prefix = 'notes/'
    result = h.pipeline.run()
    assert result.status == 'failed'
    assert source_b.id not in result.source_completed_ids


def test_checkpoint_failure_after_response_uses_final_report_without_double_count(harness, monkeypatch):
    h = harness
    write = h.store.write
    def fail(name, *args):
        if name.startswith('state/standard-usage/') and json.loads(args[0])['pending'] is False:
            raise OSError('usage save unavailable')
        return write(name, *args)
    monkeypatch.setattr(h.store, 'write', fail)
    result = h.pipeline.run()
    assert result.status == 'failed' and len(h.sdk.calls) == 1
    costs = cost_report(h.store, h.app)
    assert costs['status'] == 'success' and costs['incomplete_standard_runs'] == 0
    assert any(Decimal(v) > 0 for v in costs['daily_usd'].values())


def test_invalid_checkpoint_counts_are_rejected(harness):
    h = harness; h.pipeline.run()
    name = h.store.list('state/standard-usage/')[0]
    data = json.loads(h.store.read(name)); data['llm_calls'] = True
    h.store.data[name] = json.dumps(data).encode()
    with pytest.raises(ValueError, match='standard usage count'):
        cost_report(h.store, h.app)


def test_missing_billing_reference_is_not_claimed_as_known_recovery(harness):
    h = harness; h.store.fail_prefix = 'notes/'; h.pipeline.run(); h.store.fail_prefix = None
    name = h.store.list('state/receipts/')[0]
    receipt = json.loads(h.store.read(name)); receipt['usage_run_id'] = '20260901T000000Z-12345678'
    h.store.data[name] = json.dumps(receipt).encode()
    assert h.pipeline.run().llm_usage_unavailable == 1


def test_missing_thoughts_is_only_zero_when_total_proves_it():
    response = SimpleNamespace(usage_metadata=SimpleNamespace(prompt_token_count=100,
        candidates_token_count=20, thoughts_token_count=None, total_token_count=120))
    usage, available = response_usage(response)
    assert available and usage.thinking_tokens == 0
    response.usage_metadata.total_token_count = 125
    assert response_usage(response)[1] is False
