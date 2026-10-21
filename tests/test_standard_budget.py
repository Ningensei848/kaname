import json
from decimal import Decimal

import httpx
import pytest

from kaname.budget import request_reserve, token_cost
from kaname.pipeline import Pipeline
from kaname.state import State
from kaname._cli_arguments import parse_args, validate_args
from test_images import select


def capped(h, limit):
    return Pipeline(h.app, [h.source], h.store, h.fetcher, h.converter, h.gemini,
                    max_cost_usd=limit).run()


def two_articles(h):
    h.fetcher.pages['https://example.com/b'] = b'<article><h1>Second</h1><p>Different original text</p></article>'


@pytest.mark.parametrize('args', [
    ['run', '--max-cost-usd', 'NaN'], ['run', '--max-cost-usd', 'Infinity'],
    ['run', '--max-cost-usd', '0'], ['run', '--max-cost-usd', '-1'],
    ['dry-run', '--max-cost-usd', '1'], ['run', '--llm-mode', 'batch', '--max-cost-usd', '1'],
    ['publish-notes', '--max-cost-usd', '1'],
])
def test_invalid_budget_rejected_before_clients(harness, args):
    with pytest.raises(ValueError):
        validate_args(parse_args(args), harness.app)


def test_unknown_price_rejected(harness):
    harness.app.costs.prices.clear()
    with pytest.raises(ValueError):
        validate_args(parse_args(['run', '--max-cost-usd', '1']), harness.app)


def test_tiny_budget_retains_pending_without_api_or_false_recovery(harness):
    r = capped(harness, Decimal('0.000001'))
    assert r.status == 'success' and r.llm_calls == r.saved == 0
    assert r.pending_after == r.budget_deferred == 1
    assert r.source_completed_ids == [] and harness.sdk.calls == []
    assert r.budget_stop_reason == 'estimated_cost_limit'
    assert len(State(harness.store).pending()) == 1


def test_reserve_accounts_for_actual_unicode_payload_and_all_attempts(harness):
    g = harness.gemini
    price = harness.app.costs.prices[g.config.model]['standard']
    content, config = g.request({'title': '日本語'}, '本文' * 30000)
    inputs = len((content + config.model_dump_json(exclude_none=True) + g.config.model).encode()) + 1024
    expected = token_cost(price, inputs, 2 * g.config.max_output_tokens) * (g.config.retries + 1)
    assert request_reserve(g, {'title': '日本語'}, '本文' * 30000, price) == expected
    assert inputs > len(content)


def test_measured_spend_is_deducted_before_next_reservation(harness, monkeypatch):
    two_articles(harness)
    monkeypatch.setattr('kaname.pipeline.request_reserve', lambda *args: Decimal('0.01'))
    r = capped(harness, Decimal('0.01'))
    assert r.saved == r.llm_calls == 1 and r.pending_after == 1
    assert r.budget_deferred == 1 and r.source_completed_ids == []
    assert r.total_input_tokens == 100 and r.total_output_tokens == 20


@pytest.mark.parametrize('retry', [False, True])
def test_unknown_or_retried_usage_stops_further_paid_work(harness, retry):
    two_articles(harness)
    original = harness.sdk.generate_content
    calls = 0
    def generate(**kwargs):
        nonlocal calls
        calls += 1
        if retry and calls == 1:
            raise httpx.ReadTimeout('private payload')
        response = original(**kwargs)
        if not retry:
            response.usage_metadata = None
        return response
    harness.sdk.generate_content = generate
    r = capped(harness, Decimal('1'))
    assert r.saved == r.llm_calls == 1 and r.pending_after == 1
    assert r.llm_usage_unavailable == 1 and r.budget_stop_reason == 'usage_uncertain'
    assert calls == (2 if retry else 1)


def test_rejection_stops_budgeted_run_and_records_safe_structure(harness):
    two_articles(harness)
    harness.sdk.text = '{"images": ["private secret"], "private key": "token"}'
    r = capped(harness, Decimal('1'))
    assert r.llm_calls == 1 and r.saved == 0 and r.pending_after == 2
    assert r.budget_stop_reason == 'generation_failed'
    assert r.failures[0]['diagnostics']['phase'] == 'llm'
    assert 'private' not in r.to_bytes().decode() and 'token' not in json.dumps(r.failures)


@pytest.mark.parametrize('image_id,after,field', [
    ('img-99', 'summary', 'unknown_id_count'),
    ('img-1', 'key_point_5', 'missing_key_point_count'),
])
def test_standard_compose_failure_has_selection_counts(harness, image_id, after, field):
    select(harness, after, image_id)
    r = capped(harness, Decimal('1'))
    diagnostic = r.failures[0]['diagnostics']
    assert diagnostic['code'] == 'invalid_image_selection'
    assert diagnostic['image_selection'][field] == 1
    assert image_id not in json.dumps(diagnostic)
    assert r.saved == 0 and r.llm_usage_unavailable == 0


def test_default_run_still_processes_other_articles_after_rejection(harness):
    two_articles(harness)
    harness.sdk.text = '{}'
    r = harness.pipeline.run()
    assert r.llm_calls == 2 and r.budget_stop_reason is None


def test_response_reset_before_next_http_failure(harness):
    harness.pipeline.run()
    assert harness.gemini.last_response is not None
    harness.sdk.error = httpx.ReadTimeout('secret')
    with pytest.raises(httpx.ReadTimeout):
        harness.gemini.enrich({}, 'text')
    assert harness.gemini.last_response is None


@pytest.mark.parametrize('limit', [31, 100])
def test_larger_standard_run_requires_and_keeps_cost_guard(harness, limit):
    args = parse_args(['run', '--max-calls', str(limit), '--max-cost-usd', '0.000001'])
    validate_args(args, harness.app)
    assert harness.app.llm.max_calls_per_run == limit
    r = capped(harness, args.max_cost_usd)
    assert r.llm_calls == 0 and r.pending_after == 1


@pytest.mark.parametrize('options', [[], ['--max-cost-usd', 'NaN'],
                                   ['--max-cost-usd', '1', '--llm-mode', 'batch']])
def test_larger_run_without_valid_standard_budget_rejected(harness, options):
    with pytest.raises(ValueError):
        validate_args(parse_args(['run', '--max-calls', '100', *options]), harness.app)
    assert harness.app.llm.max_calls_per_run == 30


def test_audit_accepts_larger_run_with_known_usage_within_recorded_cap(harness):
    from kaname.audit import audit_run
    two_articles(harness)
    harness.app.llm.max_calls_per_run = 1
    validate_args(parse_args(['run', '--max-calls', '2', '--max-cost-usd', '1']), harness.app)
    r = capped(harness, Decimal('1'))
    assert r.saved == r.llm_calls == 2
    before = dict(harness.store.data)
    assert audit_run(harness.store, r.run_id, max_calls=1, expected_success_before=0)['status'] == 'success'
    assert harness.store.data == before
    r.max_cost_usd = None
    harness.store.data[next(n for n in harness.store.list('runs/'))] = r.to_bytes()
    assert {'code': 'invalid_llm_counts'} in audit_run(harness.store, r.run_id, max_calls=1)['issues']


@pytest.mark.parametrize('field,value', [
    ('max_cost_usd', 'NaN'), ('max_cost_usd', 'Infinity'), ('max_cost_usd', '-1'),
    ('max_cost_usd', 'invalid'), ('max_cost_usd', 1), ('max_cost_usd', '0.000001'),
    ('token_price', None), ('llm_usage_unavailable', 1), ('llm_http_attempts', 2),
    ('llm_mode', 'batch'), ('batch_submitted', 1), ('batch_saved', 1),
])
def test_audit_rejects_invalid_or_unverifiable_recorded_cost_cap(harness, field, value):
    from kaname.audit import audit_run
    r = capped(harness, Decimal('1'))
    setattr(r, field, value)
    harness.store.data[next(n for n in harness.store.list('runs/'))] = r.to_bytes()
    result = audit_run(harness.store, r.run_id)
    assert result['status'] == 'failed' and {'code': 'invalid_cost_cap'} in result['issues']
