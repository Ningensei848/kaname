import json

import pytest

from techkb.audit import audit_state
from techkb.cli import main
from techkb.state import INDEX_COLUMNS, decode_tsv, encode_tsv


def test_audit_pipeline_output_is_read_only(harness):
    harness.pipeline.run()
    before = dict(harness.store.data)
    writes = list(harness.store.writes)
    assert audit_state(harness.store) == {
        "status": "success", "success_rows": 1, "pending": 0, "issues": []}
    assert harness.store.data == before
    assert harness.store.writes == writes


@pytest.mark.parametrize("damage,code", [
    ("note", "missing_note"), ("receipt", "missing_receipt"),
    ("json", "invalid_receipt"), ("legacy", "legacy_original_section"),
    ("hash", "note_hash_mismatch"), ("orphan", "unindexed_receipts"),
])
def test_audit_detects_damage(harness, damage, code):
    harness.pipeline.run()
    data = harness.store.data
    note = next(key for key in data if key.startswith("notes/"))
    receipt = next(key for key in data if key.startswith("state/receipts/"))
    if damage == "note":
        del data[note]
    elif damage == "receipt":
        del data[receipt]
    elif damage == "json":
        data[receipt] = b"[]"
    elif damage == "legacy":
        data[note] += "\n## 原文\nprivate article\n".encode()
    elif damage == "hash":
        data[note] = data[note].replace(b"content_sha256:", b"wrong_hash:")
    else:
        data["state/receipts/" + "0" * 64 + ".json"] = data[receipt]
    result = audit_state(harness.store)
    assert result["status"] == "failed"
    assert code in {item["code"] for item in result["issues"]}
    assert "private article" not in json.dumps(result)


def test_audit_cli_local_snapshot(harness, tmp_path, capsys, monkeypatch):
    harness.pipeline.run()
    for name, data in harness.store.data.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert main(["audit-state", "--state-dir", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["success_rows"] == 1
    next((tmp_path / "notes").rglob("*.md")).unlink()
    assert main(["audit-state", "--state-dir", str(tmp_path)]) == 1


@pytest.mark.parametrize("damage,code", [
    ("row", "receipt_row_mismatch"), ("text", "receipt_note_mismatch"),
    ("duplicate", "duplicate_content_hash"), ("path", "invalid_note_path"),
    ("orphan_note", "unindexed_notes"), ("frontmatter", "invalid_frontmatter"),
])
def test_audit_cross_object_consistency(harness, damage, code):
    harness.pipeline.run()
    data = harness.store.data
    index = next(key for key in data if key.startswith("state/index/"))
    rows = decode_tsv(data[index], INDEX_COLUMNS)
    note = rows[0]["note_object"]
    receipt_path = f"state/receipts/{rows[0]['content_sha256']}.json"
    receipt = json.loads(data[receipt_path])
    if damage == "row":
        receipt["row"]["input_tokens"] += 1
    elif damage == "text":
        receipt["note"] += "changed"
    elif damage == "duplicate":
        rows.append(dict(rows[0]))
    elif damage == "path":
        rows[0]["note_object"] = "notes/../../private.md"
    elif damage == "orphan_note":
        data["notes/extra.md"] = data[note]
    else:
        data[note] = b"not frontmatter"
    data[index] = encode_tsv(rows, INDEX_COLUMNS)
    data[receipt_path] = json.dumps(receipt).encode()
    assert code in {item["code"] for item in audit_state(harness.store)["issues"]}


def test_empty_or_missing_snapshot_fails(tmp_path, capsys):
    assert main(["audit-state", "--state-dir", str(tmp_path)]) == 1
    assert json.loads(capsys.readouterr().out)["issues"] == [{"code": "no_success_rows"}]
    assert main(["audit-state", "--state-dir", str(tmp_path / "missing")]) == 1


def test_frontmatter_separator_must_be_full_line(harness):
    harness.pipeline.run()
    data = harness.store.data
    receipt_path = next(key for key in data if key.startswith("state/receipts/"))
    receipt = json.loads(data[receipt_path])
    # A YAML scalar ending with --- must not terminate frontmatter parsing.
    receipt["note"] = receipt["note"].replace("---\n", "---\ntitle_extra: ending---\n", 1)
    data[receipt["row"]["note_object"]] = receipt["note"].encode()
    data[receipt_path] = json.dumps(receipt).encode()
    assert audit_state(harness.store)["status"] == "success"


def test_audit_does_not_construct_article_or_llm_clients(harness, monkeypatch):
    harness.pipeline.run()
    def forbidden(*args, **kwargs):
        pytest.fail("audit must not construct network processing clients")
    monkeypatch.setattr("techkb.cli.Fetcher", forbidden)
    monkeypatch.setattr("techkb.cli.Gemini", forbidden)
    monkeypatch.setattr("techkb.cli.GCSStore", lambda _: harness.store)
    assert main(["audit-state"]) == 0
