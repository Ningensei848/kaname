from pathlib import Path
import importlib.util
import subprocess

import pytest

from techkb.distribution import publish_snapshot
from techkb.remote_publication import publish_remote
from techkb.publication import export_notes, ExportError
from test_distribution import git
from test_publication import add_note


@pytest.fixture
def remote(harness, tmp_path):
    harness.pipeline.run()
    first = tmp_path / 'first'; export_notes(harness.store, first)
    bare = tmp_path / 'remote.git'; git('init', '--bare', '--initial-branch=content', bare)
    result = publish_snapshot(first, bare)
    return first, bare, result


def test_remote_unchanged_update_and_verified_roundtrip(remote, harness, tmp_path):
    snapshot, bare, original = remote
    unchanged = publish_remote(snapshot, str(bare), tmp_path)
    assert unchanged['unchanged'] and unchanged['commit'] == original['commit']
    add_note(harness, url='https://example.com/new', at='2026-10-06T00:00:00Z')
    changed = tmp_path / 'changed'; export_notes(harness.store, changed)
    result = publish_remote(changed, str(bare), tmp_path)
    assert not result['unchanged'] and result['notes'] == 2
    assert git('--git-dir=' + str(bare), 'rev-parse', 'content^').stdout.decode().strip() == original['commit']
    assert publish_remote(changed, str(bare), tmp_path)['unchanged']


def test_invalid_or_missing_remote_cannot_initialize_distribution(remote, tmp_path):
    snapshot, _, _ = remote
    empty = tmp_path / 'empty.git'; git('init', '--bare', empty)
    with pytest.raises(ExportError, match='content_remote_unavailable'):
        publish_remote(snapshot, str(empty), tmp_path)
    for invalid in ('https://user:secret@github.com/owner/repo.git', 'https://example.com/repo.git'):
        with pytest.raises(ExportError, match='invalid_publication_remote'):
            publish_remote(snapshot, invalid, tmp_path)


def test_invalid_snapshot_preserves_remote_commit(remote, tmp_path):
    snapshot, bare, original = remote
    next((snapshot / 'notes').iterdir()).write_text('corrupt Note')
    with pytest.raises(ExportError): publish_remote(snapshot, str(bare), tmp_path)
    assert git('--git-dir=' + str(bare), 'rev-parse', 'content').stdout.decode().strip() == original['commit']


def test_concurrent_remote_change_is_not_overwritten(remote, harness, tmp_path, monkeypatch):
    snapshot, bare, original = remote
    add_note(harness, url='https://example.com/new', at='2026-10-06T00:00:00Z')
    changed = tmp_path / 'changed'; export_notes(harness.store, changed)
    runner = subprocess.run
    calls = 0
    winner = None
    def run(command, *args, **kwargs):
        nonlocal calls, winner
        if 'ls-remote' in command:
            calls += 1
            if calls == 2:
                winner = publish_snapshot(changed, bare)['commit']
        return runner(command, *args, **kwargs)
    monkeypatch.setattr('techkb.remote_publication.subprocess.run', run)
    with pytest.raises(ExportError, match='content_remote_conflict'):
        publish_remote(snapshot, str(bare), tmp_path)
    assert git('--git-dir=' + str(bare), 'rev-parse', 'content').stdout.decode().strip() == winner
    assert winner != original['commit']


def test_publication_failure_event_and_issue_deduplication():
    import httpx
    from techkb.operations import publish_issues
    spec = importlib.util.spec_from_file_location('notification_wrapper', Path(__file__).parents[1] / 'scripts/notify_publication.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    assert module.failure_event('123', 'owner/repo', 'success', 'success', 'success', 'success', 'success') == []
    events = module.failure_event('123', 'owner/repo', 'failure', 'failure', 'skipped', 'skipped', 'skipped')
    assert events[0]['stages'] == ['audit']
    issues = []
    def handler(request):
        import json
        if request.method == 'GET': return httpx.Response(200, json=issues)
        issues.append(json.loads(request.content) | {'state': 'closed'})
        return httpx.Response(201, json=issues[-1])
    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert publish_issues(events, 'owner/repo', 'unused', client)['created'] == 1
    assert publish_issues(events, 'owner/repo', 'unused', client)['created'] == 0
    assert 'https://github.com/owner/repo/actions/runs/123' in issues[0]['body']
