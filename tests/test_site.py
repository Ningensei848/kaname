import json
import os
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from techkb.publication import export_notes, ExportError, json_bytes, sha256
from techkb.site import load_snapshot, project_content, collection_path
from kaname_web.artifact import seal_artifact, load_artifact, install_artifact


@pytest.fixture
def public_note(harness, tmp_path):
    harness.pipeline.run()
    root = tmp_path / "snapshot"
    export_notes(harness.store, root)
    return root, load_snapshot(root)


def compiled_site(tmp_path, snapshot):
    manifest, files, _ = snapshot
    compiled = tmp_path / "compiled"
    compiled.mkdir()
    (compiled / "index.html").write_text('<html><head></head><body><article>Library</article></body></html>')
    for entry in manifest["notes"]:
        path = compiled / "notes" / (entry["id"] + ".html")
        path.parent.mkdir(exist_ok=True)
        path.write_text('<html><head><link rel="preconnect" href="https://example.com"></head><body><article>Note</article></body></html>')
    seal_artifact(compiled, manifest, files, fixture=True)
    return compiled


def test_pipeline_snapshot_projection_and_original_download(public_note, tmp_path):
    root, snapshot = public_note
    manifest, files, metadata = snapshot
    before = {name: (root / name).read_bytes() for name in files}
    projected = project_content(*snapshot, fixture=True)
    note = manifest["notes"][0]
    assert note["path"] in projected
    assert manifest["dataset_digest"].encode() in projected["about/snapshot.md"]
    assert collection_path("sources", note["source_id"]) in projected
    compiled = compiled_site(tmp_path, snapshot)
    marker, artifact = load_artifact(compiled)
    assert artifact["markdown/" + note["path"]] == files[note["path"]]
    html = artifact["notes/" + note["id"] + ".html"].decode()
    assert "Markdownを取得" in html and note["sha256"] in html
    assert 'Content-Security-Policy' in html and 'noindex, nofollow' in html
    assert 'rel="preconnect"' not in html
    assert 'data-basepath="/kaname"' in html
    assert {name: (root / name).read_bytes() for name in files} == before
    assert marker["dataset_digest"] == manifest["dataset_digest"]


@pytest.mark.parametrize("damage", ["extra_raw", "symlink", "bytes", "id", "duplicate", "manifest_digest", "duplicate_key", "metadata"])
def test_untrusted_snapshot_never_reaches_builder(public_note, damage):
    root, (manifest, _, _) = public_note
    note = manifest["notes"][0]
    if damage == "extra_raw":
        (root / "raw").mkdir(); (root / "raw/private.html").write_text("private")
    elif damage == "symlink":
        target = root / note["path"]
        target.rename(root / "private.md"); target.symlink_to(root / "private.md")
    elif damage == "bytes":
        with (root / note["path"]).open("ab") as stream: stream.write(b"private")
    elif damage == "id":
        note["id"] = "0" * 64
    elif damage == "duplicate":
        manifest["notes"].append(dict(note))
    elif damage == "manifest_digest":
        manifest["dataset_digest"] = "0" * 64
    elif damage == "metadata":
        note["title"] = "another title"
    elif damage == "duplicate_key":
        (root / "manifest.json").write_text('{"schema_version":1,"schema_version":1}')
    if damage in {"id", "duplicate", "manifest_digest", "metadata"}:
        (root / "manifest.json").write_bytes(json_bytes(manifest))
    with pytest.raises(ExportError): load_snapshot(root)


def test_git_metadata_and_readme_do_not_become_pages(public_note):
    root, snapshot = public_note
    (root / ".git").mkdir(); (root / ".git/config").write_text("private_git_metadata")
    (root / "README.md").write_text("private_readme_text")
    actual = load_snapshot(root)
    output = b"\n".join(project_content(*actual).values())
    assert b"private_git_metadata" not in output and b"private_readme_text" not in output
    assert actual == snapshot


def test_empty_snapshot_is_valid_and_has_no_fake_notes(harness, public_note, tmp_path):
    _, (manifest, _, _) = public_note
    root = tmp_path / "empty"
    export_notes(harness.store, root, exclude_ids=[manifest["notes"][0]["id"]])
    projected = project_content(*load_snapshot(root))
    assert b"note-card" not in projected["index.md"]
    assert not any(name.startswith("notes/") for name in projected)


def test_known_concept_links_only_to_unique_present_title(public_note):
    _, (manifest, files, metadata) = public_note
    entry = manifest["notes"][0]
    name = entry["path"]
    text = files[name].decode()
    # Rewrite a keyword in captured public bytes for projection only.
    import re
    title = entry["title"]
    text = re.sub(r"\[\[([^\[\]\n]+)\]\]", "[[" + title + "]]", text, count=1)
    files[name] = text.encode()
    projected = project_content(manifest, files, metadata)[name].decode()
    assert "](" + entry["id"] + ")" in projected
    assert "[[" not in projected
    duplicate = dict(entry, id="0" * 64, path="notes/" + "0" * 64 + ".md")
    manifest["notes"].append(duplicate); files[duplicate["path"]] = files[name]; metadata[duplicate["id"]] = metadata[entry["id"]]
    assert "](" + entry["id"] + ")" not in project_content(manifest, files, metadata)[name].decode()


def test_completed_artifact_is_idempotent_and_never_overwrites_edit(public_note, tmp_path):
    _, snapshot = public_note
    compiled = compiled_site(tmp_path, snapshot)
    output = tmp_path / "output"
    assert install_artifact(compiled, output)["unchanged"] is False
    first = (output / "site-manifest.json").stat().st_mtime_ns
    assert install_artifact(compiled, output)["unchanged"] is True
    assert (output / "site-manifest.json").stat().st_mtime_ns == first
    # Copies/hard links here are disposable artifacts, never editable Vault Notes.
    (output / "index.html").unlink(); (output / "index.html").write_bytes(b"human edit")
    with pytest.raises(ExportError): install_artifact(compiled, output)
    assert (output / "index.html").read_bytes() == b"human edit"


@pytest.mark.parametrize("extra", [".env", "raw/private.html", "state/index.json", "HANDOFF.md", "notes/private.md", "static/private.json"])
def test_private_files_are_not_sealed_or_served(public_note, tmp_path, extra):
    _, snapshot = public_note
    compiled = compiled_site(tmp_path, snapshot)
    path = compiled / extra; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b"private")
    with pytest.raises(ExportError): load_artifact(compiled)
    (compiled / "site-manifest.json").unlink()
    with pytest.raises(ExportError): seal_artifact(compiled, snapshot[0], snapshot[1])


def test_symlink_artifact_is_refused(public_note, tmp_path):
    _, snapshot = public_note
    compiled = compiled_site(tmp_path, snapshot)
    target = compiled / "index.html"; target.rename(tmp_path / "private"); target.symlink_to(tmp_path / "private")
    with pytest.raises(ExportError): load_artifact(compiled)


def test_interrupted_install_has_no_completion_marker_and_is_not_reused(public_note, tmp_path, monkeypatch):
    _, snapshot = public_note
    compiled = compiled_site(tmp_path, snapshot)
    output = tmp_path / "interrupted"
    real = os.link
    def interrupt(source, destination, **kwargs):
        if destination == "site-manifest.json": raise OSError("interrupted")
        return real(source, destination, **kwargs)
    monkeypatch.setattr(os, "link", interrupt)
    with pytest.raises(OSError): install_artifact(compiled, output)
    assert not (output / "site-manifest.json").exists()
    monkeypatch.setattr(os, "link", real)
    with pytest.raises(ExportError): install_artifact(compiled, output)
    assert install_artifact(compiled, tmp_path / "retry")["unchanged"] is False


def test_recomputed_artifact_digest_cannot_allow_private_path(public_note, tmp_path):
    _, snapshot = public_note
    compiled = compiled_site(tmp_path, snapshot)
    path = compiled / "state/private.json"; path.parent.mkdir(); path.write_bytes(b"{}")
    marker = json.loads((compiled / "site-manifest.json").read_bytes())
    marker["files"]["state/private.json"] = sha256(b"{}")
    marker["artifact_digest"] = sha256(json_bytes(sorted(marker["files"].items())))
    (compiled / "site-manifest.json").write_bytes(json_bytes(marker))
    with pytest.raises(ExportError, match="invalid_artifact_path"): load_artifact(compiled)


def web_builder():
    path = Path(__file__).resolve().parents[1] / "web/build.py"
    spec = importlib.util.spec_from_file_location("web_build", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def test_output_inside_input_cannot_mutate_public_snapshot(public_note):
    root, snapshot = public_note
    before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    with pytest.raises(ExportError, match="output_inside_snapshot"):
        web_builder().build(root, output=root / "site")
    assert {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()} == before


def test_failed_build_preserves_previous_artifact_and_strips_credentials(public_note, tmp_path, monkeypatch):
    root, snapshot = public_note
    builder = web_builder()
    previous = tmp_path / "previous"
    install_artifact(compiled_site(tmp_path, snapshot), previous)
    work = tmp_path / "web"; engine = work / ".cache/engine"; engine.mkdir(parents=True)
    (engine / ".kaname-cache").write_text("kaname-web-v1\n")
    (engine / "quartz.config.yaml").write_bytes((builder.WEB / "quartz.config.yaml").read_bytes())
    (work / "quartz.lock.json").write_bytes((builder.WEB / "quartz.lock.json").read_bytes())
    pointer = work / ".cache/last-build.json"; pointer.write_bytes(json_bytes(dict(output=str(previous))))
    before = pointer.read_bytes()
    monkeypatch.setattr(builder, "WEB", work)
    for key in ("GEMINI_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS", "GCS_BUCKET", "GH_TOKEN"):
        monkeypatch.setenv(key, "fixture-only")
    def fail(*args, **kwargs):
        assert all(key not in kwargs["env"] for key in ("GEMINI_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS", "GCS_BUCKET", "GH_TOKEN"))
        return SimpleNamespace(returncode=1)
    monkeypatch.setattr(builder.subprocess, "run", fail)
    with pytest.raises(ExportError, match="quartz_build_failed"):
        builder.build(root, output=tmp_path / "failed", fixture=True)
    assert pointer.read_bytes() == before and not (tmp_path / "failed").exists()
    assert not (work / ".cache/.build.lock").exists()
    assert load_artifact(previous)[0]["dataset_digest"] == snapshot[0]["dataset_digest"]
