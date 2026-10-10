import json
from pathlib import Path
import subprocess

import pytest

from techkb.cli import main
from techkb.distribution import publish_snapshot, Git, REF
from techkb.publication import export_notes, ExportError, PUBLIC_ATTRIBUTES, sha256
from techkb.publication.snapshot import load_snapshot
from test_publication import add_note


def git(*args, cwd=None, ok=True):
    result = subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.com",
        "-c", "protocol.file.allow=always", *map(str, args)], cwd=cwd, capture_output=True)
    if ok: assert result.returncode == 0, result.stderr.decode()
    return result


@pytest.fixture
def distribution(harness, tmp_path):
    harness.pipeline.run()
    first = tmp_path / "first"
    export_notes(harness.store, first)
    repo = tmp_path / "distribution.git"
    git("init", "--bare", "--initial-branch=content", repo)
    return first, repo


def clone(repo, path):
    git("clone", "--branch", "content", repo, path)
    return path


def test_complete_public_only_snapshot_roundtrips_without_other_files(distribution, tmp_path):
    source, repo = distribution
    (source / "README.md").write_text("private_readme")
    (source / ".git").mkdir(); (source / ".git/config").write_text("private_config")
    before = {p.relative_to(source).as_posix(): p.read_bytes() for p in source.rglob("*") if p.is_file()}
    result = publish_snapshot(source, repo)
    checkout = clone(repo, tmp_path / "checkout")
    manifest, original, _ = load_snapshot(source)
    assert load_snapshot(checkout)[0] == manifest
    for name, data in original.items(): assert (checkout / name).read_bytes() == data
    assert (checkout / ".gitattributes").read_bytes() == PUBLIC_ATTRIBUTES
    assert b"private_readme" not in (checkout / "README.md").read_bytes()
    assert b"private_config" not in (checkout / ".git/config").read_bytes()
    tracked = set(git("ls-tree", "-r", "--name-only", result["commit"], cwd=checkout).stdout.decode().splitlines())
    assert tracked == {*original, "README.md", ".gitattributes"}
    assert {p.relative_to(source).as_posix(): p.read_bytes() for p in source.rglob("*") if p.is_file()} == before


def test_unchanged_does_not_create_commit(distribution):
    source, repo = distribution
    first = publish_snapshot(source, repo)
    second = publish_snapshot(source, repo)
    assert second["unchanged"] and first["commit"] == second["commit"]
    assert Git(repo).call("rev-list", "--count", REF).strip() == b"1"


def test_update_and_withdrawal_preserve_history_and_other_refs(distribution, harness, tmp_path):
    source, repo = distribution
    first = publish_snapshot(source, repo)
    g = Git(repo); g.call("update-ref", "refs/heads/unrelated", first["commit"])
    add_note(harness, url="https://example.com/another", at="2026-10-04T00:00:00Z")
    changed = tmp_path / "changed"; export_notes(harness.store, changed)
    second = publish_snapshot(changed, repo)
    assert g.call("rev-parse", second["commit"] + "^").strip().decode() == first["commit"]
    manifest = load_snapshot(changed)[0]
    withdrawn = tmp_path / "withdrawn"
    export_notes(harness.store, withdrawn, exclude_ids=[e["id"] for e in manifest["notes"]])
    third = publish_snapshot(withdrawn, repo)
    checkout = clone(repo, tmp_path / "empty")
    assert load_snapshot(checkout)[0]["notes"] == []
    assert g.call("rev-list", "--count", REF).strip() == b"3"
    assert g.call("show-ref", "--hash", "refs/heads/unrelated").strip().decode() == first["commit"]
    assert third["notes"] == 0


def test_corrupt_input_does_not_change_ref(distribution):
    source, repo = distribution
    first = publish_snapshot(source, repo)
    note = load_snapshot(source)[0]["notes"][0]
    (source / note["path"]).write_bytes(b"private edit")
    with pytest.raises(ExportError): publish_snapshot(source, repo)
    assert Git(repo).head() == first["commit"]


def test_non_bare_repository_and_local_edits_are_untouched(distribution, tmp_path):
    source, repo = distribution
    publish_snapshot(source, repo)
    checkout = clone(repo, tmp_path / "checkout")
    local = checkout / "HANDOFF.md"; local.write_bytes(b"human edit")
    with pytest.raises(ExportError, match="bare_distribution_repository_required"):
        publish_snapshot(source, checkout)
    assert local.read_bytes() == b"human edit"


def test_symlink_and_overlapping_paths_are_refused(distribution, tmp_path):
    source, repo = distribution
    link = tmp_path / "link"; link.symlink_to(repo, target_is_directory=True)
    with pytest.raises(ExportError, match="symlink_path"): publish_snapshot(source, link)
    with pytest.raises(ExportError, match="distribution_paths_overlap"): publish_snapshot(source, source / "repo")


def test_symbolic_or_code_content_ref_is_refused(distribution):
    source, repo = distribution
    g = Git(repo); g.call("symbolic-ref", REF, "refs/heads/private")
    with pytest.raises(ExportError, match="symbolic_distribution_ref"): publish_snapshot(source, repo)
    g.call("symbolic-ref", "--delete", REF)
    blob = g.call("hash-object", "-w", "--stdin", data=b"private code").strip()
    tree = g.call("mktree", data=b"100644 blob " + blob + b"\tprivate.py\n").strip().decode()
    commit = g.call("commit-tree", tree, data=b"private\n").strip().decode()
    g.call("update-ref", REF, commit)
    with pytest.raises(ExportError, match="invalid_distribution_tree"): publish_snapshot(source, repo)
    assert Git(repo).head() == commit


@pytest.mark.parametrize("failure", ["interrupt", "concurrent"])
def test_last_update_failure_preserves_winner(distribution, harness, tmp_path, monkeypatch, failure):
    source, repo = distribution
    first = publish_snapshot(source, repo)
    add_note(harness, url="https://example.com/new", at="2026-10-04T00:00:00Z")
    changed = tmp_path / "changed"; export_notes(harness.store, changed)
    real = Git.call; winner = first["commit"]
    def intercept(self, *args, **kwargs):
        nonlocal winner
        if args[0] == "update-ref":
            if failure == "interrupt": raise ExportError("fixture_interruption")
            tree = real(self, "rev-parse", first["commit"] + "^{tree}").strip().decode()
            winner = real(self, "commit-tree", tree, "-p", first["commit"], data=b"concurrent publisher\n").strip().decode()
            real(self, "update-ref", REF, winner, first["commit"])
        return real(self, *args, **kwargs)
    monkeypatch.setattr(Git, "call", intercept)
    with pytest.raises(ExportError): publish_snapshot(changed, repo)
    assert Git(repo).head() == winner


def test_hooks_and_environment_cannot_run_or_sign(distribution, tmp_path, monkeypatch):
    source, repo = distribution
    marker = tmp_path / "hook-ran"
    hook = repo / "hooks/reference-transaction"
    hook.write_text('#!/bin/sh\ntouch "' + str(marker) + '"\n'); hook.chmod(0o755)
    git("--git-dir=" + str(repo), "config", "commit.gpgsign", "true")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.hooksPath")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", str(repo / "hooks"))
    publish_snapshot(source, repo)
    assert not marker.exists()


def test_autocrlf_checkout_preserves_markdown_bytes(distribution, tmp_path):
    source, repo = distribution
    publish_snapshot(source, repo)
    checkout = tmp_path / "windows-policy"
    git("-c", "core.autocrlf=true", "clone", "--branch", "content", repo, checkout)
    for name, data in load_snapshot(source)[1].items():
        assert (checkout / name).read_bytes() == data


def test_submodule_commit_is_pinned_until_explicit_update(distribution, harness, tmp_path):
    source, repo = distribution
    first = publish_snapshot(source, repo)
    parent = tmp_path / "parent"; git("init", parent)
    git("submodule", "add", "-b", "content", repo, "generated", cwd=parent)
    git("commit", "-am", "pin generated Note version", cwd=parent)
    module = parent / "generated"
    add_note(harness, url="https://example.com/another", at="2026-10-04T00:00:00Z")
    changed = tmp_path / "changed"; export_notes(harness.store, changed)
    second = publish_snapshot(changed, repo)
    git("submodule", "update", "--init", cwd=parent)
    assert git("rev-parse", "HEAD", cwd=module).stdout.strip().decode() == first["commit"]
    git("fetch", "origin", "content", cwd=module)
    assert not git("status", "--porcelain", "--untracked-files=all", "--ignored", cwd=module).stdout
    git("checkout", "--detach", second["commit"], cwd=module)
    assert load_snapshot(module)[0] == load_snapshot(changed)[0]
    # The parent still pins the old commit until its owner explicitly records it.
    assert first["commit"].encode() in git("ls-tree", "HEAD", "generated", cwd=parent).stdout
    git("add", "generated", cwd=parent); git("commit", "-m", "accept next generated version", cwd=parent)
    assert second["commit"].encode() in git("ls-tree", "HEAD", "generated", cwd=parent).stdout


@pytest.mark.parametrize("kind", ["tracked", "untracked"])
def test_standard_submodule_checkout_refuses_overlapping_edits(distribution, harness, tmp_path, kind):
    source, repo = distribution
    first = publish_snapshot(source, repo)
    checkout = clone(repo, tmp_path / "checkout")
    add_note(harness, url="https://example.com/new", at="2026-10-04T00:00:00Z")
    changed = tmp_path / "changed"; export_notes(harness.store, changed)
    second = publish_snapshot(changed, repo)
    old_paths = set(load_snapshot(source)[1])
    new_paths = set(load_snapshot(changed)[1])
    # For tracked edits use a manifest that actually changes between editions.
    path = "manifest.json" if kind == "tracked" else next(iter(new_paths - old_paths))
    local = checkout / path; local.parent.mkdir(exist_ok=True); local.write_bytes(b"human annotation")
    git("fetch", "origin", "content", cwd=checkout)
    assert git("checkout", "--detach", second["commit"], cwd=checkout, ok=False).returncode != 0
    assert local.read_bytes() == b"human annotation"
    assert git("rev-parse", "HEAD", cwd=checkout).stdout.strip().decode() == first["commit"]


def test_publish_cli_needs_no_collection_credentials(distribution, monkeypatch, capsys):
    source, repo = distribution
    monkeypatch.delenv("GEMINI_API_KEY", raising=False); monkeypatch.delenv("GCS_BUCKET", raising=False)
    assert main(["publish-notes", "--public-snapshot", str(source), "--distribution-repo", str(repo)]) == 0
    assert json.loads(capsys.readouterr().out)["notes"] == 1
    assert main(["validate-config", "--public-snapshot", str(source)]) == 1
