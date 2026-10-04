"""Offline review reproductions; not part of the normal passing test suite.
Run from the repository root with the pinned dependencies and Chromium:
PLAYWRIGHT_BROWSERS_PATH=/tmp/kaname-browsers PYTHONPATH=src:tests python -m pytest -q docs/review-reproductions-2026-10-04.py -k 'not repeated_audit'
On codex/vault-edit-protection: F1/F2 pass; four unresolved findings fail.
The audit notification case expresses an unconfirmed product requirement.
Only fixture HTTP, memory storage and a temporary Vault are used.
"""
import json
from types import SimpleNamespace
import httpx
import pytest
from conftest import harness as repository_harness
from test_batch import setup
from techkb.gemini import response_usage
from techkb.operations import cost_report, notification_plan
from techkb.reporting import RunReport
from techkb.audit import audit_state
import techkb.sync as sync_module


@pytest.fixture
def harness():
    return repository_harness.__wrapped__()


def test_batch_preserves_actual_exception_type(harness):
    h = harness
    sdk = setup(h)
    h.pipeline.run()
    sdk.standard.text = "{}"
    sdk.finish()
    h.app.llm.max_calls_per_run = 0
    result = h.pipeline.run()
    ledger = json.loads(h.store.read(h.store.list("state/batches/")[0]))
    actual = ledger["outcomes"][0]["error"]
    assert actual == "ValidationError"
    assert result.failures[0]["error_type"] == actual


def test_partial_usage_is_not_complete():
    response = SimpleNamespace(usage_metadata=SimpleNamespace(
        prompt_token_count=None, candidates_token_count=20, thoughts_token_count=5))
    usage, available = response_usage(response)
    assert usage.output_tokens == 20
    assert available is False


def test_receipt_recovery_keeps_standard_cost(harness, monkeypatch):
    class PowerLoss(BaseException):
        pass
    def stop_before_run_report(self):
        raise PowerLoss()
    h = harness
    with monkeypatch.context() as patch:
        patch.setattr(RunReport, "finish", stop_before_run_report)
        with pytest.raises(PowerLoss):
            h.pipeline.run()
    assert h.store.list("state/receipts/")
    assert not h.store.list("runs/")
    receipt = json.loads(h.store.read(h.store.list("state/receipts/")[0]))
    assert receipt["row"]["input_tokens"] == 100
    next_run = h.pipeline.run()
    assert next_run.llm_calls == 0 and len(h.sdk.calls) == 1
    costs = cost_report(h.store, h.app)
    assert float(costs["daily_usd"][next_run.started_at[:10]]) > 0


def test_unvisited_source_streak_survives_storage_stop(harness):
    h = harness
    for index in range(4):
        report = RunReport(
            run_id=f"20261001T00000{index}Z-{index:08x}",
            started_at=f"2026-10-01T00:00:0{index}+00:00",
            source_ids=["example", "other"],
            llm_model=h.app.llm.model,
            token_price=h.app.costs.prices[h.app.llm.model]["standard"].model_dump())
        if index < 3:
            report.fail("fetch", "other", "", ValueError())
        else:
            report.fail("raw_save", "example", "", OSError())
        report.finish()
        h.store.write("runs/" + report.run_id + ".json", report.to_bytes())
    events = notification_plan(h.store, h.app, ["example", "other"])
    assert any(e.get("source_id") == "other" for e in events)


def test_repeated_audit_failure_is_visible_to_notifications(harness):
    h = harness
    h.pipeline.run()
    note_name = h.store.list("notes/")[0]
    del h.store.data[note_name]
    for _ in range(3):
        assert h.pipeline.run().status == "success"
        assert audit_state(h.store)["status"] == "failed"
    events = notification_plan(h.store, h.app, [h.source.id])
    assert any(e.get("source_id") == "collector" for e in events)


def test_edit_after_last_hash_check_is_not_lost(harness, tmp_path, monkeypatch):
    h = harness
    name = "notes/a.md"
    h.store.data[name] = b"initial remote"
    sync_module.sync_vault(h.store, tmp_path)
    path = tmp_path / "TechKB" / name
    h.store.data[name] = b"remote update"
    # Inject at the publication boundary in both the old replacement design
    # and the new candidate design. Existing Note bytes must survive either.
    boundary = "publish_new" if hasattr(sync_module, "publish_new") else "atomic"
    original_publish = getattr(sync_module, boundary)
    def edited_publish(destination, content):
        if destination != tmp_path / "TechKB/.techkb-sync.json":
            path.write_bytes(b"user edit after final check")
        return original_publish(destination, content)
    monkeypatch.setattr(sync_module, boundary, edited_publish)
    sync_module.sync_vault(h.store, tmp_path)
    assert path.read_bytes() == b"user edit after final check"


def test_browser_redirect_never_contacts_disallowed_host(harness, monkeypatch):
    pytest.importorskip("playwright.sync_api")
    from techkb.browser_fetcher import SourceFetcher
    from techkb.fetcher import Fetcher, FetchError
    monkeypatch.setattr("techkb.fetcher.safe_url", lambda url: url)
    requests = []
    def handler(request):
        requests.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.host == "outside.example":
            return httpx.Response(200, text="void 0;",
                                  headers={"content-type": "application/javascript"})
        if request.url.path == "/redir.js":
            return httpx.Response(302, headers={"location": "https://outside.example/code.js"})
        return httpx.Response(200, text='<article>Fixture</article><script src="/redir.js"></script>',
                              headers={"content-type": "text/html"})
    source = harness.source
    source.fetcher = "playwright"
    source.request_interval_seconds = 0
    fetcher = Fetcher(harness.app.http,
                      httpx.Client(transport=httpx.MockTransport(handler)),
                      sleep=lambda _: None)
    try:
        with pytest.raises(FetchError):
            SourceFetcher(fetcher).page("https://example.com/article", source)
    finally:
        fetcher.close()
    assert not any("outside.example" in url for url in requests)
