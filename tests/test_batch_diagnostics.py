"""Structural Batch diagnostics must survive persistence without leaking values."""
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from techkb.batch import failure_diagnostics
from techkb.operations import cost_report
from test_batch import setup


@pytest.mark.parametrize("damage,error_type,code", [
    ("json", "ValidationError", "json_invalid"),
    ("missing", "ValidationError", "missing"),
    ("extra", "ValidationError", "extra_forbidden"),
    ("category", "ValueError", "category_not_allowed"),
    ("item", "ValueError", "invalid_enrichment_item"),
])
def test_failure_type_and_safe_details_survive_billing_and_collection(harness, damage, error_type, code):
    h = harness
    sdk = setup(h)
    h.pipeline.run()
    sentinel = "NEVER_LOG_INPUT_OR_KEY"
    payload = json.loads(h.sdk.text)
    if damage == "json":
        h.sdk.text = sentinel
    elif damage == "missing":
        h.sdk.text = "{}"
    else:
        if damage == "extra":
            payload[sentinel] = sentinel
        elif damage == "category":
            payload["category"] = sentinel
        else:
            payload["key_points"][0] = " "
        h.sdk.text = json.dumps(payload)
    sdk.finish()
    h.app.llm.max_calls_per_run = 0
    report = h.pipeline.run()
    ledger = json.loads(h.store.read(h.store.list("state/batches/")[0]))
    outcome = ledger["outcomes"][0]
    billing = [json.loads(h.store.read(name)) for name in h.store.list("runs/")
               if json.loads(h.store.read(name))["record_kind"] == "batch_usage"]
    assert report.batch_failed == 1 and report.saved == 0 and report.pending_after == 1
    assert outcome["error"] == error_type
    assert outcome["diagnostics"]["phase"] == "validation"
    assert report.failures[0]["error_type"] == billing[0]["failures"][0]["error_type"] == error_type
    assert report.failures[0]["diagnostics"] == billing[0]["failures"][0]["diagnostics"] == outcome["diagnostics"]
    details = outcome["diagnostics"]
    if error_type == "ValidationError":
        assert code in {issue["code"] for issue in details["validation_errors"]}
    else:
        assert details["code"] == code
    assert sentinel not in json.dumps(ledger) + report.to_bytes().decode() + json.dumps(billing)
    assert billing[0]["total_input_tokens"] == 100
    costs = cost_report(h.store, h.app)
    h.pipeline.run()
    assert cost_report(h.store, h.app) == costs
    assert len(sdk.created) == 1 and not h.sdk.calls


def test_missing_response_is_distinct_from_invalid_json(harness):
    h = harness
    sdk = setup(h)
    h.pipeline.run()
    sdk.finish()
    sdk.jobs["batches/1"].dest.inlined_responses = []
    h.app.llm.max_calls_per_run = 0
    report = h.pipeline.run()
    assert report.failures[0]["diagnostics"] == {
        "phase": "response", "code": "batch_response_unavailable"}
    assert cost_report(h.store, h.app)["status"] == "partial"


def test_compose_failure_keeps_type_without_exception_text(harness, monkeypatch):
    h = harness
    sdk = setup(h)
    h.pipeline.run()
    sdk.finish()
    h.app.llm.max_calls_per_run = 0
    def fail(*args, **kwargs):
        raise RuntimeError("NEVER_LOG_COMPOSE_INPUT")
    monkeypatch.setattr("techkb.batch.compose", fail)
    report = h.pipeline.run()
    assert report.failures[0]["error_type"] == "RuntimeError"
    assert report.failures[0]["diagnostics"]["phase"] == "compose"
    assert "NEVER_LOG_COMPOSE_INPUT" not in report.to_bytes().decode()


def test_legacy_outcome_without_details_recovers_original_error_type(harness):
    h = harness
    sdk = setup(h)
    h.pipeline.run()
    h.sdk.text = "{}"
    sdk.finish()
    h.app.llm.max_calls_per_run = 0
    h.store.fail_prefix = "runs/"
    assert h.pipeline.run().status == "failed"
    name = h.store.list("state/batches/")[0]
    ledger = json.loads(h.store.read(name))
    del ledger["outcomes"][0]["diagnostics"]
    h.store.data[name] = json.dumps(ledger).encode()
    h.store.fail_prefix = None
    report = h.pipeline.run()
    assert report.failures[0]["error_type"] == "ValidationError"
    assert "diagnostics" not in report.failures[0]
    assert len(sdk.created) == 1 and not h.sdk.calls


def test_validation_details_drop_unknown_field_names_and_parser_input():
    from techkb.models import ArticleEnrichment
    with pytest.raises(ValidationError) as caught:
        ArticleEnrichment.model_validate_json('{"PRIVATE_FIELD_NAME": "PRIVATE_VALUE"}')
    response = SimpleNamespace(text="PRIVATE_RESPONSE", candidates=[SimpleNamespace(
        finish_reason=SimpleNamespace(name="MAX_TOKENS"))])
    details = failure_diagnostics(caught.value, "validation", response)
    assert {"field": "$", "code": "extra_forbidden"} in details["validation_errors"]
    assert details["finish_reason"] == "MAX_TOKENS" and details["text_present"] is True
    assert "PRIVATE" not in json.dumps(details)
