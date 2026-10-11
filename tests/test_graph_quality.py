import copy
import json
from pathlib import Path

import pytest

from techkb import cli
from techkb.graph_quality import graph_quality, term_key
from techkb.publication import export_notes
from techkb.publication.snapshot import load_snapshot


CASES = json.loads((Path(__file__).parent / "fixtures/graph_quality.json").read_text())


@pytest.mark.parametrize("left,right", CASES["equivalent"])
def test_reviewed_equivalent_terms(left, right):
    assert term_key(left) == term_key(right)


@pytest.mark.parametrize("left,right", CASES["distinct"])
def test_reviewed_distinct_terms(left, right):
    assert term_key(left) != term_key(right)


def quality_snapshot():
    titles = ["LLM", "C++", "C", "shared", "shared", "origin"]
    entries, files, metadata = [], {}, {}
    for number, title in enumerate(titles):
        note_id = str(number) * 64
        path = f"notes/{note_id}.md"
        terms = ["大規模言語モデル", "ｌｌｍ", "LLM", "C++", "missing", "shared", "origin"] if title == "origin" else [title]
        body = ("---\ntitle: fixture\n---\n\n# Fixture\n\n## 検索キーワード\n\n" +
                "\n".join(f"- [[{term}]]" for term in terms) +
                "\n\n## 資料の位置づけ\n\nFixture\n\n`[[PROVENANCE_NOISE]]`\n")
        entries.append(dict(id=note_id, title=title, path=path))
        files[path] = body.encode()
        metadata[note_id] = dict(tags=["AI", "ai", "ＡＩ", "cloud/security", "cloud-security"])
    return dict(notes=entries, dataset_digest="a" * 64), files, metadata


def test_resolution_duplicates_variants_and_deduplicated_edges():
    snapshot = quality_snapshot()
    before = copy.deepcopy(snapshot)
    result = graph_quality(*snapshot, details=True)
    assert snapshot == before and result["applied"] is False
    assert result["notes"] == 6
    assert result["normalized_duplicates"] == {"tags": 12, "keywords": 2}
    assert result["variant_groups"] == {"tags": 1, "keywords": 1}
    assert result["current_links"] == dict(resolved=2, self=4, unresolved=3, ambiguous=3)
    assert result["proposed_links"] == dict(resolved=4, self=4, unresolved=1, ambiguous=3)
    assert result["current_edges"] == result["proposed_edges"] == 2
    assert result["ambiguous_title_groups"] == 1
    assert "PROVENANCE_NOISE" not in json.dumps(result)
    summary = graph_quality(*snapshot)
    assert "links" not in summary and "variants" not in summary
    assert "大規模言語モデル" not in json.dumps(summary, ensure_ascii=False)


def test_normalized_collision_never_selects_arbitrary_title():
    manifest, files, metadata = quality_snapshot()
    manifest["notes"][2]["title"] = "ｌｌｍ"
    result = graph_quality(manifest, files, metadata, details=True)
    links = [link for link in result["links"] if link["note_id"] == "5" * 64 and term_key(link["term"]) == "llm"]
    assert {link["proposed"] for link in links} == {"ambiguous"}
    assert result["proposed_edges"] == 1


def test_empty_quality_snapshot_and_order_independence():
    assert graph_quality(dict(notes=[], dataset_digest="b" * 64), {}, {})["notes"] == 0
    manifest, files, metadata = quality_snapshot()
    expected = graph_quality(manifest, files, metadata, details=True)
    manifest["notes"].reverse()
    assert graph_quality(manifest, files, metadata, details=True) == expected


@pytest.fixture
def public_snapshot(harness, tmp_path):
    harness.pipeline.run()
    root = tmp_path / "snapshot"
    export_notes(harness.store, root)
    return root


def test_cli_validates_public_bytes_without_clients_or_writes(public_snapshot, monkeypatch, capsys):
    before = {p.relative_to(public_snapshot).as_posix(): p.read_bytes()
              for p in public_snapshot.rglob("*") if p.is_file()}
    def forbidden(*args, **kwargs):
        pytest.fail("graph quality must not create network/storage/LLM clients")
    for name in ("GCSStore", "Gemini", "Fetcher", "SourceFetcher"):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert cli.main(["graph-quality", "--public-snapshot", str(public_snapshot)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["notes"] == 1 and result["occurrences"]["keywords"] == 2
    assert result["dataset_digest"] == load_snapshot(public_snapshot)[0]["dataset_digest"]
    assert result["applied"] is False and "links" not in result
    assert before == {p.relative_to(public_snapshot).as_posix(): p.read_bytes()
                      for p in public_snapshot.rglob("*") if p.is_file()}
    assert cli.main(["graph-quality", "--public-snapshot", str(public_snapshot), "--details"]) == 0
    assert len(json.loads(capsys.readouterr().out)["links"]) == 2


def test_cli_rejects_tampered_snapshot(public_snapshot, capsys):
    note = next((public_snapshot / "notes").glob("*.md"))
    note.write_bytes(note.read_bytes() + b"\nextra")
    assert cli.main(["graph-quality", "--public-snapshot", str(public_snapshot)]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "failed"


@pytest.mark.parametrize("args", [[], ["--apply"], ["--state-dir", "/tmp"], ["--distribution-repo", "/tmp"], ["--max-calls", "0"]])
def test_quality_cli_requires_public_snapshot_and_rejects_mutating_arguments(args):
    assert cli.main(["graph-quality", *args]) == 1


def test_details_are_exclusive_to_quality():
    assert cli.main(["source-health", "--details"]) == 1
