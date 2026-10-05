import json
from pathlib import Path

import pytest

from techkb.cli import main
from techkb.composer import compose
from techkb.metadata_refresh import refresh_note_metadata
from techkb.models import ArticleEnrichment
from techkb.pending import Candidate
from techkb.publication import export_notes, ExportError, ExportDirectorySnapshot, sha256
from techkb.state import INDEX_COLUMNS, encode_tsv, decode_tsv


def add_note(harness, url="https://example.com/a", at="2026-10-01T00:00:00Z", title="公開Note", truncated=False):
    digest = sha256((url + at + title).encode())
    raw_hash = sha256(("raw" + digest).encode())
    enrichment = ArticleEnrichment(title_ja=title, summary_ja="記事の要約です。",
        key_points=["重要なポイント", "追加のポイント"], positioning_ja="技術の位置づけを説明します。",
        category="ai-llm", tags=["AI"], related_concepts=["Concept", "Other concept"], source_language="en")
    name, note = compose(Candidate(at, harness.source.id, url, title="Original"), harness.source,
        enrichment, "Original fixture text", url, at, raw_hash, digest, "fixture-model", truncated,
        input_char_limit=20000)
    row = dict(processed_at=at, source_id=harness.source.id, source_url=url, canonical_url=url,
        published_at="", raw_html_sha256=raw_hash, content_sha256=digest, status="success",
        note_object=name, llm_model="fixture-model", input_tokens=100, output_tokens=20,
        thinking_tokens=5, llm_input_truncated=str(truncated).lower())
    index = "state/index/" + at[:7] + ".tsv"
    rows = decode_tsv(harness.store.data.get(index), INDEX_COLUMNS)
    rows.append({k: str(row[k]) for k in INDEX_COLUMNS})
    harness.store.data[index] = encode_tsv(rows, INDEX_COLUMNS)
    receipt = f"state/receipts/{digest}.json"
    harness.store.data[receipt] = json.dumps(dict(row=row, note=note), ensure_ascii=False).encode()
    harness.store.data[name] = note.encode()
    return row, receipt


def change_note(harness, row, receipt_path, change):
    receipt = json.loads(harness.store.data[receipt_path])
    receipt["note"] = change(receipt["note"])
    harness.store.data[row["note_object"]] = receipt["note"].encode()
    harness.store.data[receipt_path] = json.dumps(receipt, ensure_ascii=False).encode()


def manifest(root):
    return json.loads((root / "manifest.json").read_bytes())


def test_export_actual_pipeline_notes_is_readonly(harness, tmp_path):
    harness.pipeline.run()
    before, writes, calls = dict(harness.store.data), list(harness.store.writes), len(harness.sdk.calls)
    output = tmp_path / "public"
    result = export_notes(harness.store, output, categories=harness.app.categories)
    entries = manifest(output)["notes"]
    assert result["status"] == "success" and result["notes"] == 1
    assert manifest(output)["schema_version"] == 1
    original = next(data for name, data in before.items() if name.startswith("notes/"))
    assert (output / entries[0]["path"]).read_bytes() == original
    assert entries[0]["sha256"] == sha256(original)
    assert set(p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()) == {
        "README.md", "manifest.json", entries[0]["path"]}
    assert harness.store.data == before and harness.store.writes == writes
    assert len(harness.sdk.calls) == calls
    assert "note_object" not in json.dumps(manifest(output))


def test_latest_revision_id_and_tiebreak_are_order_independent(harness, tmp_path):
    old, _ = add_note(harness, title="旧版")
    latest, _ = add_note(harness, at="2026-10-02T00:00:00Z", title="最新版")
    tied, _ = add_note(harness, at="2026-10-02T00:00:00Z", title="同時刻の版")
    add_note(harness, url="https://example.com/b")
    export_notes(harness.store, tmp_path / "first")
    m1 = manifest(tmp_path / "first")
    winner = max((latest, tied), key=lambda r: r["content_sha256"])
    entry = next(e for e in m1["notes"] if e["canonical_url"] == "https://example.com/a")
    assert (tmp_path / "first" / entry["path"]).read_bytes() == harness.store.data[winner["note_object"]]
    assert harness.store.data[old["note_object"]] != (tmp_path / "first" / entry["path"]).read_bytes()
    for name in harness.store.list("state/index/"):
        harness.store.data[name] = encode_tsv(list(reversed(decode_tsv(harness.store.data[name], INDEX_COLUMNS))), INDEX_COLUMNS)
    original_list = harness.store.list
    harness.store.list = lambda prefix: list(reversed(original_list(prefix)))
    export_notes(harness.store, tmp_path / "second")
    assert manifest(tmp_path / "second") == m1
    for path in (tmp_path / "first").rglob("*"):
        if path.is_file():
            assert path.read_bytes() == (tmp_path / "second" / path.relative_to(tmp_path / "first")).read_bytes()


def test_canonical_normalization_and_source_identity(harness, tmp_path):
    add_note(harness, url="https://EXAMPLE.com:443/a?utm_source=fixture#fragment")
    add_note(harness, at="2026-10-02T00:00:00Z")
    harness.source.id = "OTHER_Source"
    add_note(harness)
    export_notes(harness.store, tmp_path / "public")
    entries = manifest(tmp_path / "public")["notes"]
    assert len(entries) == 2 and len({e["id"] for e in entries}) == 2
    assert {e["canonical_url"] for e in entries} == {"https://example.com/a"}


def test_metadata_update_changes_digest_but_not_id(harness, tmp_path):
    row, receipt = add_note(harness)
    export_notes(harness.store, tmp_path / "first")
    change_note(harness, row, receipt, lambda note: refresh_note_metadata(note, ["Alice Example"], ""))
    export_notes(harness.store, tmp_path / "second")
    first, second = manifest(tmp_path / "first"), manifest(tmp_path / "second")
    assert first["notes"][0]["id"] == second["notes"][0]["id"]
    assert first["dataset_digest"] != second["dataset_digest"]
    assert first["notes"][0]["sha256"] != second["notes"][0]["sha256"]


def test_truncation_notice_is_preserved(harness, tmp_path):
    row, _ = add_note(harness, truncated=True)
    export_notes(harness.store, tmp_path / "public")
    entry = manifest(tmp_path / "public")["notes"][0]
    data = (tmp_path / "public" / entry["path"]).read_bytes()
    assert entry["llm_input_truncated"] is True
    assert "先頭20,000文字だけを要約" in data.decode()
    assert data == harness.store.data[row["note_object"]]


def legacy_truncated(harness, keep_limit=False):
    row, receipt = add_note(harness, truncated=True)
    warning = ("> [!warning] 要約対象の制限\n"
               "> 入力上限により、変換後の本文の先頭20,000文字だけを要約しています。\n"
               "> 記事後半の論点が含まれない場合があります。記事全体の確認には出典URLを参照してください。\n\n")
    def old_format(text):
        if not keep_limit:
            text = text.replace("llm_input_max_chars: 20000\n", "")
        return text.replace(warning, "")
    change_note(harness, row, receipt, old_format)
    return row, receipt


def test_legacy_truncated_bytes_preserved_with_unknown_scope(harness, tmp_path):
    row, _ = legacy_truncated(harness)
    export_notes(harness.store, tmp_path / "public")
    entry = manifest(tmp_path / "public")["notes"][0]
    assert entry["llm_input_truncated"] is True
    original = harness.store.data[row["note_object"]]
    assert (tmp_path / "public" / entry["path"]).read_bytes() == original
    from techkb.site import load_snapshot, project_content
    rendered = project_content(*load_snapshot(tmp_path / "public"))[entry["path"]].decode()
    assert "上限文字数は記録されていません" in rendered
    assert "20,000" not in rendered
    assert "上限文字数は記録されていません" not in original.decode()


@pytest.mark.parametrize("damage", ["recorded_limit", "unknown_warning", "extra_section"])
def test_legacy_compatibility_does_not_relax_other_gates(harness, tmp_path, damage):
    row, receipt = legacy_truncated(harness, keep_limit=damage == "recorded_limit")
    if damage == "unknown_warning":
        change_note(harness, row, receipt, lambda text: text.replace("> [!abstract] AI要約", "> [!warning] unknown\n> unknown content\n\n> [!abstract] AI要約"))
    elif damage == "extra_section":
        change_note(harness, row, receipt, lambda text: text + "\n## 原文\nprivate original content\n")
    with pytest.raises(ExportError, match="invalid_compact_body"):
        export_notes(harness.store, tmp_path / "public")
    assert not (tmp_path / "public").exists()


def test_withdrawal_excludes_all_revisions_and_rejects_unknown_ids(harness, tmp_path):
    add_note(harness)
    add_note(harness, at="2026-10-02T00:00:00Z")
    export_notes(harness.store, tmp_path / "first")
    note_id = manifest(tmp_path / "first")["notes"][0]["id"]
    export_notes(harness.store, tmp_path / "withdrawn", exclude_ids=[note_id])
    assert manifest(tmp_path / "withdrawn")["notes"] == []
    with pytest.raises(ExportError, match="unknown_exclusion"):
        export_notes(harness.store, tmp_path / "unknown", exclude_ids=["0" * 64])
    assert not (tmp_path / "unknown").exists()


@pytest.mark.parametrize("damage", ["missing_note", "missing_receipt", "receipt_row", "receipt_note", "bad_hash", "duplicate", "path", "old_note_hash"])
def test_inconsistent_state_never_produces_output(harness, tmp_path, damage):
    row, receipt_path = add_note(harness)
    data = harness.store.data
    if damage == "old_note_hash":
        add_note(harness, at="2026-10-02T00:00:00Z", title="New valid revision")
        change_note(harness, row, receipt_path, lambda text: text.replace("content_sha256: ", "content_sha256: wrong"))
    elif damage == "missing_note":
        del data[row["note_object"]]
    elif damage == "missing_receipt":
        del data[receipt_path]
    elif damage in {"receipt_row", "receipt_note"}:
        receipt = json.loads(data[receipt_path])
        if damage == "receipt_row":
            receipt["row"]["input_tokens"] += 1
        else:
            receipt["note"] += "changed"
        data[receipt_path] = json.dumps(receipt).encode()
    else:
        name = harness.store.list("state/index/")[0]
        rows = decode_tsv(data[name], INDEX_COLUMNS)
        if damage == "bad_hash":
            rows[0]["content_sha256"] = "bad"
        elif damage == "duplicate":
            rows.append(dict(rows[0]))
        else:
            rows[0]["note_object"] = "notes/../../private.md"
        data[name] = encode_tsv(rows, INDEX_COLUMNS)
    with pytest.raises(ExportError):
        export_notes(harness.store, tmp_path / "public")
    assert not (tmp_path / "public").exists()


@pytest.mark.parametrize("change,code", [
    (lambda text: text + "\n## 原文\nprivate source text\n", "invalid_compact_body"),
    (lambda text: text.replace("- 重要なポイント", "- ![image](https://example.com/image)"), "invalid_compact_body"),
    (lambda text: text.replace("---\n", "---\napi_key: hidden\n", 1), "invalid_frontmatter"),
    (lambda text: text.replace("---\n", "---\ntitle: duplicate\n", 1), "invalid_frontmatter"),
    (lambda text: text.replace("記事の要約です。", "AIza" + "X" * 35), "secret_pattern"),
    (lambda text: text.replace("記事の要約です。", "<script>alert(1)</script>"), "unsafe_markup"),
    (lambda text: text.replace("source: https://example.com/a", "source: https://example.com/a?access_token=secret"), "secret_pattern"),
    (lambda text: text.replace("title: 公開Note", "title: &anchor 公開Note"), "invalid_frontmatter"),
    (lambda text: text.replace("- 重要なポイント", "- ghp\\_" + "X" * 36), "secret_pattern"),
    (lambda text: text.replace("description: 記事の要約です。", 'description: "\\u0041Iza' + "X" * 35 + '"'), "secret_pattern"),
    (lambda text: text.replace("raw_html_sha256: ", "raw_html_sha256: broken"), "note_index_mismatch"),
])
def test_unsafe_content_is_rejected_even_when_receipt_matches(harness, tmp_path, change, code):
    row, receipt = add_note(harness)
    change_note(harness, row, receipt, change)
    with pytest.raises(ExportError, match=code):
        export_notes(harness.store, tmp_path / "public")
    assert not (tmp_path / "public").exists()


def test_snapshot_change_and_new_index_abort(harness, tmp_path):
    row, _ = add_note(harness)
    read = harness.store.read
    calls = 0
    def mutate(name):
        nonlocal calls
        data = read(name)
        if name == row["note_object"]:
            calls += 1
            if calls == 1:
                harness.store.data[name] += b"changed"
        return data
    harness.store.read = mutate
    with pytest.raises(ExportError, match="snapshot_changed"):
        export_notes(harness.store, tmp_path / "changed")
    assert not (tmp_path / "changed").exists()
    harness.store.read = read
    harness.store.data[row["note_object"]] = read(row["note_object"]).removesuffix(b"changed")
    listing = harness.store.list
    listed = 0
    def added_index(prefix):
        nonlocal listed
        listed += 1
        return listing(prefix) + (["state/index/2026-11.tsv"] if listed > 1 else [])
    harness.store.list = added_index
    with pytest.raises(ExportError, match="snapshot_changed"):
        export_notes(harness.store, tmp_path / "added")


def test_gcs_generation_change_detects_same_bytes_aba(harness, tmp_path):
    row, _ = add_note(harness)
    harness.store.generations = {}
    read = harness.store.read
    def versioned_read(name):
        harness.store.generations[name] = harness.store.generations.get(name, 0) + 1
        return read(name)
    harness.store.read = versioned_read
    with pytest.raises(ExportError, match="snapshot_changed"):
        export_notes(harness.store, tmp_path / "public")
    assert not (tmp_path / "public").exists()


def test_rerun_is_unchanged_and_existing_files_are_never_replaced(harness, tmp_path):
    add_note(harness)
    output = tmp_path / "public"
    export_notes(harness.store, output)
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in output.rglob("*") if p.is_file()}
    assert export_notes(harness.store, output)["unchanged"] is True
    assert {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before} == before
    extra = output / "local.txt"
    extra.write_text("human edits")
    with pytest.raises(ExportError, match="output_conflict"):
        export_notes(harness.store, output)
    assert extra.read_text() == "human edits"
    (tmp_path / "empty").mkdir()
    with pytest.raises(ExportError, match="output_conflict"):
        export_notes(harness.store, tmp_path / "empty")


def test_interrupted_install_has_no_completion_manifest(harness, tmp_path, monkeypatch):
    add_note(harness)
    import techkb.publication as publication
    real_link = publication.os.link
    calls = 0
    def interrupted(source, target, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected install failure")
        return real_link(source, target, **kwargs)
    monkeypatch.setattr(publication.os, "link", interrupted)
    with pytest.raises(OSError):
        export_notes(harness.store, tmp_path / "public")
    assert not (tmp_path / "public" / "manifest.json").exists()
    assert not list(tmp_path.glob(".kaname-export-*"))
    with pytest.raises(ExportError, match="output_conflict"):
        export_notes(harness.store, tmp_path / "public")


def test_concurrent_output_creation_preserves_user_files(harness, tmp_path, monkeypatch):
    add_note(harness)
    output = tmp_path / "public"
    mkdir = Path.mkdir
    def raced_mkdir(path, *args, **kwargs):
        if path == output:
            mkdir(path)
            (path / "local.txt").write_text("concurrent human file")
        return mkdir(path, *args, **kwargs)
    monkeypatch.setattr(Path, "mkdir", raced_mkdir)
    with pytest.raises(FileExistsError):
        export_notes(harness.store, output)
    assert (output / "local.txt").read_text() == "concurrent human file"
    assert not (output / "manifest.json").exists()


def test_local_snapshot_and_output_symlinks_are_refused(harness, tmp_path):
    row, _ = add_note(harness)
    snapshot = tmp_path / "state"
    for name, data in harness.store.data.items():
        path = snapshot / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    note = snapshot / row["note_object"]
    original = tmp_path / "external.md"
    original.write_bytes(note.read_bytes())
    note.unlink()
    note.symlink_to(original)
    with pytest.raises(ExportError, match="symlink_path"):
        export_notes(ExportDirectorySnapshot(snapshot), tmp_path / "public")
    (tmp_path / "linked-output").symlink_to(snapshot, target_is_directory=True)
    with pytest.raises(ExportError, match="symlink_path"):
        export_notes(harness.store, tmp_path / "linked-output")


def test_local_note_fifo_is_refused_without_blocking(harness, tmp_path):
    import os
    row, _ = add_note(harness)
    snapshot = tmp_path / "state"
    for name, data in harness.store.data.items():
        path = snapshot / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    note = snapshot / row["note_object"]
    note.unlink()
    os.mkfifo(note)
    with pytest.raises(ExportError, match="invalid_snapshot_object"):
        export_notes(ExportDirectorySnapshot(snapshot), tmp_path / "public")
    assert not (tmp_path / "public").exists()


def test_cli_offline_constructs_no_network_clients_or_prints_content(harness, tmp_path, monkeypatch, capsys):
    add_note(harness)
    snapshot = tmp_path / "state"
    for name, data in harness.store.data.items():
        path = snapshot / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    def forbidden(*args, **kwargs):
        pytest.fail("export must not construct collection/network clients")
    for cls in ("Fetcher", "SourceFetcher", "Gemini", "Converter", "GCSStore"):
        monkeypatch.setattr("techkb.cli." + cls, forbidden)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert main(["export-notes", "--state-dir", str(snapshot), "--output", str(tmp_path / "public")]) == 0
    output = capsys.readouterr().out
    assert json.loads(output)["notes"] == 1
    assert "Original fixture text" not in output and "https://example.com" not in output
    assert main(["export-notes", "--state-dir", str(snapshot)]) == 1
    assert main(["validate-config", "--output", str(tmp_path / "invalid")]) == 1
    assert main(["export-notes", "--state-dir", str(snapshot), "--output", str(tmp_path / "bad"), "--apply"]) == 1


def test_publication_refuses_empty_and_malformed_index(harness, tmp_path):
    with pytest.raises(ExportError, match="no_success_rows"):
        export_notes(harness.store, tmp_path / "empty")
    add_note(harness)
    name = harness.store.list("state/index/")[0]
    harness.store.data[name] = harness.store.data[name].replace(b"source_id", b"processed_at", 1)
    with pytest.raises(ExportError, match="invalid_index_header"):
        export_notes(harness.store, tmp_path / "malformed")


def test_legacy_index_columns_and_optional_limit_are_supported(harness, tmp_path):
    row, receipt = add_note(harness)
    change_note(harness, row, receipt, lambda text: text.replace("llm_input_max_chars: 20000\n", ""))
    name = harness.store.list("state/index/")[0]
    rows = decode_tsv(harness.store.data[name], INDEX_COLUMNS)
    harness.store.data[name] = encode_tsv([{k: r[k] for k in INDEX_COLUMNS[:12]} for r in rows], INDEX_COLUMNS[:12])
    export_notes(harness.store, tmp_path / "public")
    assert len(manifest(tmp_path / "public")["notes"]) == 1


def test_failed_rows_and_unindexed_receipts_never_become_public(harness, tmp_path):
    row, _ = add_note(harness)
    failed, receipt = add_note(harness, at="2026-10-03T00:00:00Z", title="Failed result")
    index = harness.store.list("state/index/")[0]
    rows = decode_tsv(harness.store.data[index], INDEX_COLUMNS)
    rows[-1]["status"] = "failed"
    harness.store.data[index] = encode_tsv(rows, INDEX_COLUMNS)
    del harness.store.data[failed["note_object"]]
    del harness.store.data[receipt]
    harness.store.data["state/receipts/" + "0" * 64 + ".json"] = b"unindexed operational receipt"
    harness.store.data["raw/private.html"] = b"private original source"
    export_notes(harness.store, tmp_path / "public")
    entry = manifest(tmp_path / "public")["notes"][0]
    assert entry["title"] == "公開Note"
    assert (tmp_path / "public" / entry["path"]).read_bytes() == harness.store.data[row["note_object"]]


def test_output_cannot_mutate_readonly_local_snapshot(harness, tmp_path):
    add_note(harness)
    snapshot = tmp_path / "state"
    for name, data in harness.store.data.items():
        path = snapshot / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    before = {p: p.read_bytes() for p in snapshot.rglob("*") if p.is_file()}
    with pytest.raises(ExportError, match="output_inside_snapshot"):
        export_notes(ExportDirectorySnapshot(snapshot), snapshot / "public")
    assert {p: p.read_bytes() for p in snapshot.rglob("*") if p.is_file()} == before


def test_directory_swap_cannot_redirect_note_writes(harness, tmp_path, monkeypatch):
    add_note(harness)
    output, external = tmp_path / "public", tmp_path / "external"
    external.mkdir()
    import techkb.publication as publication
    real_link = publication.os.link
    swapped = False
    def swap_directory(source, target, **kwargs):
        nonlocal swapped
        if str(source).endswith(".md") and Path(source).name != "README.md" and not swapped:
            swapped = True
            (output / "notes").rename(output / "original-notes")
            (output / "notes").symlink_to(external, target_is_directory=True)
        return real_link(source, target, **kwargs)
    monkeypatch.setattr(publication.os, "link", swap_directory)
    with pytest.raises(ExportError, match="symlink_path"):
        export_notes(harness.store, output)
    assert list(external.iterdir()) == []
    assert not (output / "manifest.json").exists()


def test_gcs_cli_needs_no_gemini_credentials_and_never_writes(harness, tmp_path, monkeypatch, capsys):
    add_note(harness)
    def forbidden(*args, **kwargs):
        pytest.fail("export must not write GCS or construct collection clients")
    for cls in ("Fetcher", "SourceFetcher", "Gemini", "Converter"):
        monkeypatch.setattr("techkb.cli." + cls, forbidden)
    monkeypatch.setattr(harness.store, "write", forbidden)
    monkeypatch.setattr("techkb.cli.GCSStore", lambda bucket: harness.store)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert main(["export-notes", "--output", str(tmp_path / "public")]) == 0
    assert json.loads(capsys.readouterr().out)["notes"] == 1
