import json

import yaml

from techkb.cli import main
from techkb.metadata_refresh import MetadataRefresh, refresh_note_metadata
from techkb.state import INDEX_COLUMNS, decode_tsv, encode_tsv


def _set_published(harness, value="2026-09-10T21:31:19+00:00"):
    index = next(name for name in harness.store.data if name.startswith("state/index/"))
    rows = decode_tsv(harness.store.data[index], INDEX_COLUMNS)
    rows[0]["published_at"] = value
    harness.store.data[index] = encode_tsv(rows, INDEX_COLUMNS)
    receipt_name = f"state/receipts/{rows[0]['content_sha256']}.json"
    receipt = json.loads(harness.store.data[receipt_name])
    receipt["row"]["published_at"] = value
    harness.store.data[receipt_name] = json.dumps(receipt).encode()


def _add_author_page(harness):
    harness.fetcher.pages["https://example.com/a"] = (
        b'<html><head><meta name="author" content="Alice Example"></head>'
        b'<article><h1>Title</h1><p>Original text</p></article></html>')


def test_refresh_note_metadata_preserves_body_and_normalizes_fields(harness):
    harness.pipeline.run()
    note_name = next(name for name in harness.store.data if name.startswith("notes/"))
    note = harness.store.data[note_name].decode()
    refreshed = refresh_note_metadata(note, ["Alice Example"], "2026-09-10T21:31:19+00:00")
    front = yaml.safe_load(refreshed.split("---", 2)[1])
    assert front["author"] == ["[[Alice Example]]"]
    assert front["published"] == "2026-09-10"
    assert "- Author: Alice Example" in refreshed
    assert "- Published: 2026-09-10" in refreshed
    content = lambda value: value.split("## 重要ポイント", 1)[1].split("\n---\n\n## 出典情報", 1)[0]
    assert content(refreshed) == content(note)


def test_plan_is_read_only_and_apply_updates_note_and_receipt(harness):
    harness.pipeline.run()
    _set_published(harness)
    _add_author_page(harness)
    before = dict(harness.store.data)
    writes = list(harness.store.writes)
    plan = MetadataRefresh(harness.store, harness.fetcher, [harness.source]).run()
    assert plan == {"status": "success", "apply": False, "success_rows": 1,
                    "planned": 1, "updated": 0, "unchanged": 0,
                    "no_authors": 0, "failures": []}
    assert harness.store.data == before
    assert harness.store.writes == writes
    result = MetadataRefresh(harness.store, harness.fetcher, [harness.source]).run(apply=True)
    assert result["status"] == "success" and result["updated"] == 1
    note_name = next(name for name in harness.store.data if name.startswith("notes/"))
    receipt_name = next(name for name in harness.store.data if name.startswith("state/receipts/"))
    note = harness.store.data[note_name].decode()
    assert json.loads(harness.store.data[receipt_name])["note"] == note
    assert "- Author: Alice Example" in note
    assert "- Published: 2026-09-10" in note


def test_apply_rolls_back_note_when_receipt_write_fails(harness):
    harness.pipeline.run()
    _add_author_page(harness)
    note_name = next(name for name in harness.store.data if name.startswith("notes/"))
    old_note = harness.store.data[note_name]
    harness.store.fail_prefix = "state/receipts/"
    result = MetadataRefresh(harness.store, harness.fetcher, [harness.source]).run(apply=True)
    assert result["status"] == "failed"
    assert result["failures"] == [{"row": 1, "stage": "write"}]
    assert harness.store.data[note_name] == old_note


def test_no_author_preserves_author_and_reports_count(harness):
    harness.pipeline.run()
    result = MetadataRefresh(harness.store, harness.fetcher, [harness.source]).run()
    assert result["status"] == "success"
    assert result["no_authors"] == 1
    assert result["unchanged"] == 1


def test_inconsistent_receipt_fails_before_writes(harness):
    harness.pipeline.run()
    receipt_name = next(name for name in harness.store.data if name.startswith("state/receipts/"))
    harness.store.data[receipt_name] = b"{}"
    writes = list(harness.store.writes)
    result = MetadataRefresh(harness.store, harness.fetcher, [harness.source]).run(apply=True)
    assert result["status"] == "failed"
    assert result["failures"] == [{"row": 1, "stage": "validate"}]
    assert harness.store.writes == writes


def test_apply_recovers_interrupted_pair_update(harness):
    harness.pipeline.run()
    _add_author_page(harness)
    note_name = next(name for name in harness.store.data if name.startswith("notes/"))
    receipt_name = next(name for name in harness.store.data if name.startswith("state/receipts/"))
    old_note = harness.store.data[note_name].decode()
    refreshed = refresh_note_metadata(old_note, ["Alice Example"], "")
    for updated_side in ("note", "receipt"):
        harness.store.data[note_name] = old_note.encode()
        receipt = json.loads(harness.store.data[receipt_name])
        receipt["note"] = old_note
        harness.store.data[receipt_name] = json.dumps(receipt).encode()
        if updated_side == "note":
            harness.store.data[note_name] = refreshed.encode()
        else:
            receipt["note"] = refreshed
            harness.store.data[receipt_name] = json.dumps(receipt).encode()
        result = MetadataRefresh(harness.store, harness.fetcher, [harness.source]).run(apply=True)
        assert result["status"] == "success" and result["updated"] == 1
        assert harness.store.data[note_name].decode() == refreshed
        assert json.loads(harness.store.data[receipt_name])["note"] == refreshed


def test_refresh_cli_does_not_construct_gemini(harness, monkeypatch, capsys):
    harness.pipeline.run()
    _add_author_page(harness)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("techkb.cli.load_config", lambda *args: (harness.app, [harness.source]))
    monkeypatch.setattr("techkb.cli.GCSStore", lambda _: harness.store)
    harness.fetcher.close = lambda: None
    monkeypatch.setattr("techkb.cli.Fetcher", lambda _: harness.fetcher)
    monkeypatch.setattr("techkb.cli.Gemini", lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("refresh-metadata must not construct Gemini")))
    assert main(["refresh-metadata"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["planned"] == 1 and result["updated"] == 0
