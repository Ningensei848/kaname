import json
from techkb.state import State

def test_identical_raw_skips_before_converter(harness):
    h = harness
    assert h.pipeline.run().saved == 1
    converter_calls = h.converter.calls
    r = h.pipeline.run()
    assert r.raw_duplicates == 1 and r.llm_calls == 0
    assert h.converter.calls == converter_calls
    assert len(h.sdk.calls) == 1

def test_dynamic_html_same_markdown(harness):
    h = harness
    h.pipeline.run()
    h.fetcher.pages["https://example.com/a"] += b"<script>nonce=changed</script>"
    r = h.pipeline.run()
    assert r.content_duplicates == 1 and r.llm_calls == 0

def test_same_url_updated(harness):
    h = harness
    h.pipeline.run()
    h.fetcher.pages["https://example.com/a"] = b"<article>New text</article>"
    r = h.pipeline.run()
    assert r.llm_calls == 1 and r.saved == 1
    assert len(h.store.list("notes/")) == 2

def test_different_url_same_content(harness):
    h = harness
    h.fetcher.pages["https://example.com/b"] = b"<div><article><h1>Title</h1><p>Original text</p></article></div>"
    r = h.pipeline.run()
    assert r.llm_calls == 1 and r.content_duplicates == 1
    assert not State(h.store).pending()

def test_schema_error_no_index_and_no_repair(harness):
    h = harness
    h.sdk.text = '{"title_ja": "invalid"}'
    r = h.pipeline.run()
    assert r.status == "failed" and r.llm_failed == 1
    assert not State(h.store).rows
    assert len(State(h.store).pending()) == 1
    assert len(h.sdk.calls) == 1
    assert r.total_input_tokens == 100  # Failed validation is still billed.

def test_note_upload_failure_and_recovery(harness):
    h = harness
    h.store.fail_prefix = "notes/"
    r = h.pipeline.run()
    assert r.status == "failed" and not State(h.store).rows
    assert len(h.store.list("state/receipts/")) == 1
    h.store.fail_prefix = None
    r = h.pipeline.run()
    assert r.recovered == 1 and r.llm_calls == 0
    assert len(h.sdk.calls) == 1 and len(State(h.store).rows) == 1

def test_index_upload_failure_and_recovery(harness):
    h = harness
    h.store.fail_prefix = "state/index/"
    r = h.pipeline.run()
    assert r.status == "failed" and len(h.store.list("notes/")) == 1
    assert not State(h.store).rows
    h.store.fail_prefix = None
    r = h.pipeline.run()
    assert r.recovered == 1 and r.llm_calls == 0
    assert len(h.store.list("notes/")) == 1

def test_thirty_call_limit_keeps_remaining(harness):
    h = harness
    h.fetcher.pages = {f"https://example.com/{i}": f"<p>Article {i}</p>".encode() for i in range(31)}
    r = h.pipeline.run()
    assert r.llm_calls == 30 and r.saved == 30 and r.pending_after == 1
    assert len(State(h.store).pending()) == 1

def test_dry_run_never_writes_or_calls_llm(harness):
    h = harness
    r = h.pipeline.run(dry_run=True)
    assert r.would_enrich == 1 and r.fetched == 1
    assert h.store.writes == [] and h.sdk.calls == []

def test_truncation_and_no_tools(harness):
    h = harness
    h.app.llm.max_input_chars = 5
    h.pipeline.run()
    call = h.sdk.calls[0]
    body = json.loads(call["contents"])
    assert len(body["article_markdown"]) == 5
    assert body["metadata"]["llm_input_truncated"] is True
    assert not call["config"].tools
    assert call["config"].automatic_function_calling.disable is True
    assert State(h.store).rows[0]["llm_input_truncated"] == "true"

def test_http_failure_stays_pending(harness):
    h = harness
    h.fetcher.pages["https://example.com/a"] = OSError("failure")
    r = h.pipeline.run()
    assert r.status == "failed" and r.pending_after == 1 and r.llm_calls == 0

def test_convert_failure_never_calls_llm(harness, monkeypatch):
    def fail(*args):
        raise ValueError("bad conversion")
    monkeypatch.setattr(harness.converter, "convert", fail)
    r = harness.pipeline.run()
    assert r.status == "failed" and r.llm_calls == 0 and r.pending_after == 1

def test_failed_content_not_retried_within_same_run(harness):
    h = harness
    h.fetcher.pages["https://example.com/b"] = h.fetcher.pages["https://example.com/a"]
    h.sdk.text = "{}"
    r = h.pipeline.run()
    assert r.llm_calls == 1 and r.pending_after == 2

def test_report_failure_is_failure(harness):
    harness.store.fail_prefix = "runs/"
    assert harness.pipeline.run().status == "failed"

def test_receipt_failure_stops_paid_work(harness):
    h = harness
    h.fetcher.pages["https://example.com/b"] = b"<p>Other</p>"
    h.store.fail_prefix = "state/receipts/"
    r = h.pipeline.run()
    assert r.llm_calls == 1 and r.status == "failed" and r.pending_after == 2

def test_note_and_receipt_never_store_full_text(harness):
    h = harness
    h.pipeline.run()
    for name in h.store.list("notes/") + h.store.list("state/receipts/"):
        assert b"Original text" not in h.store.read(name)
