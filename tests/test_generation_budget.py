"""Aggregate limits must stop new paid work without rewriting original usage."""
from datetime import datetime, timezone
from decimal import Decimal
import json

import pytest
from pydantic import ValidationError

from kaname.budget import generation_allowance
from kaname.config import CostConfig
from kaname.reporting import RunReport
from kaname.pipeline import Pipeline
from kaname._cli_arguments import parse_args, validate_args


def stored_usage(h, stamp=None, identity='a' * 8, **changes):
    stamp = stamp or datetime.now(timezone.utc).isoformat()
    run = RunReport(run_id=stamp[:19].replace('-', '').replace(':', '') + 'Z-' + identity,
                    started_at=stamp, llm_model=h.app.llm.model, llm_mode='standard',
                    token_price=dict(input_usd_per_million=0.3, output_usd_per_million=2.5),
                    llm_calls=1, llm_processed=1, llm_http_attempts=1, total_input_tokens=1_000_000)
    value = json.loads(run.to_bytes()) | changes
    path = f"runs/{stamp[:4]}/{stamp[5:7]}/{run.run_id}.json"
    h.store.data[path] = json.dumps(value).encode()
    return path


@pytest.mark.parametrize('field', ['generation_daily_limit_usd', 'generation_monthly_limit_usd'])
def test_exhausted_and_nearly_exhausted_period_prevents_calls_and_keeps_pending(harness, field):
    h = harness
    stored_usage(h)
    before = dict(h.store.data)
    setattr(h.app.costs, field, 0.300001)
    report = h.pipeline.run()
    assert report.status == 'success' and report.llm_calls == 0 and not h.sdk.calls
    assert report.pending_after == 1 and report.budget_stop_reason == 'estimated_cost_limit'
    assert report.generation_budget['status'] == 'ready'
    assert Decimal(report.max_cost_usd) == Decimal('0.000001')
    assert all(h.store.data[name] == data for name, data in before.items())


def test_period_already_over_limit_skips_bodies_without_claiming_recovery(harness):
    h = harness
    stored_usage(h)
    h.app.costs.generation_daily_limit_usd = 0.1
    report = h.pipeline.run()
    assert report.llm_calls == report.fetched == report.saved == 0
    assert report.pending_after == 1 and report.source_completed_ids == []
    assert report.budget_stop_reason == 'aggregate_limit_reached'
    assert not h.sdk.calls


@pytest.mark.parametrize('change', [dict(llm_usage_unavailable=1), dict(token_price=None),
                                  dict(llm_model=''), dict(token_price='missing')])
def test_unknown_or_original_price_missing_usage_never_permits_generation(harness, change):
    h = harness
    path = stored_usage(h, **({} if change.get('token_price') == 'missing' else change))
    if change.get('token_price') == 'missing':
        value = json.loads(h.store.data[path]); value.pop('token_price')
        h.store.data[path] = json.dumps(value).encode()
    h.app.costs.generation_daily_limit_usd = 10
    report = h.pipeline.run()
    assert report.budget_stop_reason == 'aggregate_usage_uncertain'
    assert not h.sdk.calls and report.pending_after == 1


def test_unbilled_batch_is_a_blocker_even_in_standard_mode(harness):
    h = harness
    h.store.data['state/batches/legacy.json'] = json.dumps(dict(status='complete', items=[{}])).encode()
    h.app.costs.generation_monthly_limit_usd = 10
    report = h.pipeline.run()
    assert report.budget_stop_reason == 'aggregate_usage_uncertain' and not h.sdk.calls


def test_utc_month_boundary_original_price_and_two_periods(harness):
    h = harness
    stored_usage(h, '2026-10-01T08:00:00+09:00', identity='1' * 8, llm_usage_unavailable=1)
    stored_usage(h, '2026-10-01T00:30:00+00:00', identity='2' * 8)
    stored_usage(h, '2026-10-02T00:30:00+00:00', identity='3' * 8)
    h.app.costs.generation_daily_limit_usd = 1
    h.app.costs.generation_monthly_limit_usd = 0.8
    h.app.costs.prices[h.app.llm.model]['standard'].input_usd_per_million = 9
    result = generation_allowance(h.store, h.app, '2026-10-02T12:00:00+00:00')
    assert result['status'] == 'ready'
    assert Decimal(result['periods']['daily']['spent_usd']) == Decimal('0.3')
    assert Decimal(result['periods']['monthly']['spent_usd']) == Decimal('0.6')
    assert Decimal(result['remaining_usd']) == Decimal('0.2')


def test_limits_are_optional_and_batch_override_fails_before_clients(harness):
    h = harness
    class NoReads:
        def __getattr__(self, _): pytest.fail('disabled aggregate limit must not read state')
    assert generation_allowance(NoReads(), h.app, '2026-10-16T00:00:00Z') is None
    h.app.costs.generation_daily_limit_usd = 1
    with pytest.raises(ValueError, match='require standard'):
        validate_args(parse_args(['run', '--llm-mode', 'batch']), h.app)
    with pytest.raises(ValueError, match='require standard'):
        Pipeline(h.app, [], NoReads(), None, None)


def test_next_run_deducts_original_usage_and_respects_smaller_manual_cap(harness, monkeypatch):
    h = harness
    h.app.costs.generation_daily_limit_usd = 1
    first = h.pipeline.run()
    assert first.saved == 1
    # The original report and journal represent one bill, not two.
    result = generation_allowance(h.store, h.app, first.started_at)
    spent = Decimal('0.0000925')
    assert Decimal(result['periods']['daily']['spent_usd']) == spent
    assert Decimal(result['remaining_usd']) == Decimal('1') - spent
    h.fetcher.pages['https://example.com/b'] = b'<article><p>Different original article</p></article>'
    monkeypatch.setattr('kaname.pipeline.request_reserve', lambda *args: Decimal('0.0001'))
    second = Pipeline(h.app, [h.source], h.store, h.fetcher, h.converter, h.gemini,
                      max_cost_usd=Decimal('0.000001')).run()
    assert second.llm_calls == 0 and second.pending_after == 1 and len(h.sdk.calls) == 1
    assert second.max_cost_usd == '0.000001'


def test_new_utc_month_and_daily_only_ignore_prior_period_uncertainty(harness):
    h = harness
    stored_usage(h, '2026-10-31T23:59:59Z', llm_usage_unavailable=1)
    h.app.costs.generation_monthly_limit_usd = 1
    result = generation_allowance(h.store, h.app, '2026-11-01T00:00:00Z')
    assert result['status'] == 'ready' and Decimal(result['remaining_usd']) == 1
    h.app.costs.generation_monthly_limit_usd = None
    h.app.costs.generation_daily_limit_usd = 1
    result = generation_allowance(h.store, h.app, '2026-11-01T00:00:00Z')
    assert result['status'] == 'ready' and result['periods']['daily']['key'] == '2026-11-01'


def test_corrupt_period_accounting_stops_pipeline_before_generation(harness):
    h = harness
    stored_usage(h, total_input_tokens=-1)
    h.app.costs.generation_daily_limit_usd = 1
    report = h.pipeline.run()
    assert report.status == 'failed' and report.llm_calls == 0 and not h.sdk.calls
    assert any(f['stage'] == 'state_or_recovery' for f in report.failures)


@pytest.mark.parametrize('limit', [True, 0, -1, float('inf'), float('nan')])
def test_invalid_aggregate_limits_fail_configuration(limit):
    with pytest.raises(ValidationError):
        CostConfig(generation_daily_limit_usd=limit)
