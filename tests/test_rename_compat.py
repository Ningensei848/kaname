"""A name change must preserve paid jobs, human edits and incident identity."""
import hashlib
import json

import httpx
import pytest

from kaname.compat import env_value
from kaname.notifications import publish_issues
from kaname.read_snapshot import read_workers
from kaname.sync import sync_vault, digest


def test_new_environment_names_take_precedence_with_legacy_fallback(monkeypatch):
    monkeypatch.delenv('KANAME_GCS_READ_WORKERS', raising=False)
    monkeypatch.setenv('TECHKB_GCS_READ_WORKERS', '8')
    assert read_workers() == 8
    monkeypatch.setenv('KANAME_GCS_READ_WORKERS', '2')
    assert read_workers() == 2
    monkeypatch.setenv('TECHKB_READ_CACHE', '/legacy/cache')
    monkeypatch.delenv('KANAME_READ_CACHE', raising=False)
    assert env_value('KANAME_READ_CACHE') == '/legacy/cache'
    monkeypatch.setenv('KANAME_READ_CACHE', '')
    assert env_value('KANAME_READ_CACHE') == ''


def test_legacy_sync_keeps_edits_candidates_and_old_process_lock(harness, tmp_path):
    root = tmp_path / 'TechKB'
    (root / 'notes').mkdir(parents=True)
    note = root / 'notes/a.md'
    note.write_bytes(b'human annotation')
    manifest = root / '.techkb-sync.json'
    manifest.write_text(json.dumps({'notes/a.md': digest(b'old remote')}))
    harness.store.data = {'notes/a.md': b'new remote'}
    result = sync_vault(harness.store, tmp_path)
    assert result['conflicts'] == 1 and note.read_bytes() == b'human annotation'
    assert (root / result['updates'][0]['incoming']).read_bytes() == b'new remote'
    assert not (tmp_path / 'kaname').exists()
    assert json.loads(manifest.read_bytes())['notes/a.md'] == digest(b'old remote')
    (root / '.techkb-sync.lock').touch()
    with pytest.raises(FileExistsError):
        sync_vault(harness.store, tmp_path)


def test_two_sync_roots_are_not_implicitly_merged(harness, tmp_path):
    (tmp_path / 'TechKB').mkdir()
    (tmp_path / 'kaname').mkdir()
    with pytest.raises(ValueError, match='multiple sync roots'):
        sync_vault(harness.store, tmp_path)
    assert list((tmp_path / 'kaname').iterdir()) == []


def test_old_closed_notification_prevents_duplicate_after_rename():
    marker = '<!-- techkb-alert:' + hashlib.sha256(b'existing').hexdigest() + ' -->'
    calls = []
    def respond(request):
        calls.append(request.method)
        return httpx.Response(200, json=[{'state': 'closed', 'body': marker}])
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = publish_issues([dict(kind='failure', key='existing', source_id='example')],
                                'owner/repo', 'fixture-token', client)
    assert result['created'] == 0 and calls == ['GET']


def test_legacy_ambiguous_batch_is_reconciled_without_resubmission(harness):
    from test_batch import setup
    sdk = setup(harness)
    sdk.timeout = True
    assert harness.pipeline.run().status == 'failed'
    name = harness.store.list('state/batches/')[0]
    job = json.loads(harness.store.read(name))
    job['display_name'] = 'techkb-' + job['id']
    harness.store.data[name] = json.dumps(job).encode()
    sdk.jobs['batches/1'].display_name = job['display_name']
    sdk.timeout = False
    sdk.finish()
    result = harness.pipeline.run()
    assert result.status == 'success' and result.batch_saved == 1
    assert len(sdk.created) == 1
