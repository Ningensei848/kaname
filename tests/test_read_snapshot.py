"""Parallel I/O must preserve catalog/byte integrity and publication fail-closed."""
import base64
from contextlib import contextmanager
from dataclasses import dataclass
from threading import Barrier, Lock
from types import SimpleNamespace

import google_crc32c
import pytest

from techkb.read_snapshot import GCSReadSnapshot, GenerationCache, SnapshotChangedError, read_snapshot
from techkb.publication import ExportError, export_notes


def checksum(data):
    return base64.b64encode(google_crc32c.value(data).to_bytes(4, 'big')).decode()


@dataclass
class Blob:
    store: object
    name: str
    generation: int
    crc32c: str

    def download_as_bytes(self, *, if_generation_match):
        with self.store.lock:
            self.store.active += 1
            self.store.peak = max(self.store.peak, self.store.active)
            self.store.downloads += 1
        try:
            if self.store.barrier:
                self.store.barrier.wait(timeout=5)
            if self.store.on_download:
                self.store.on_download(self.name)
            generation, data = self.store.objects[self.name]
            if generation != if_generation_match:
                raise SnapshotChangedError('generation changed during download')
            return data
        finally:
            with self.store.lock:
                self.store.active -= 1


class Remote:
    def __init__(self, objects, name='private-bucket'):
        self.objects = {name: (1, data) for name, data in objects.items()}
        self.client = self
        self.bucket = SimpleNamespace(name=name)
        self.lock = Lock()
        self.downloads = self.active = self.peak = 0
        self.barrier = self.on_download = None

    def list_blobs(self, bucket, *, prefix):
        return [Blob(self, name, gen, checksum(data)) for name, (gen, data) in sorted(self.objects.items())
                if name.startswith(prefix)]

    def replace(self, name, data=None):
        gen, old = self.objects[name]
        self.objects[name] = gen + 1, old if data is None else data


def test_bounded_parallel_downloads_without_per_object_metadata_requests():
    remote = Remote({f'notes/{i}.md': str(i).encode() for i in range(12)})
    remote.barrier = Barrier(4)
    with read_snapshot(remote, ('notes/',), workers=4) as view:
        assert [view.read(name) for name in view.list('notes/')] == [remote.objects[name][1] for name in view.list('notes/')]
        assert view.metrics['downloads'] == 12
        assert remote.peak == 4
        with pytest.raises(RuntimeError, match='read-only'):
            view.write('notes/a.md', b'no')
        with pytest.raises(ValueError, match='outside'):
            view.read('raw/private.html')


def test_warm_cache_downloads_only_changed_generation_and_repairs_corrupt_bytes(tmp_path):
    remote = Remote({'notes/a.md': b'a', 'notes/b.md': b'b'})
    with read_snapshot(remote, ('notes/',), cache_dir=tmp_path) as view:
        assert view.metrics['downloads'] == 2
    remote.replace('notes/a.md', b'updated')
    with read_snapshot(remote, ('notes/',), cache_dir=tmp_path) as view:
        assert view.read('notes/a.md') == b'updated'
        assert view.metrics['downloads'] == view.metrics['cache_hits'] == 1
    cache = GenerationCache(tmp_path, remote.bucket.name)
    blob = remote.list_blobs(remote.bucket, prefix='notes/b')[0]
    cache.path(blob).write_bytes(b'wrong cached bytes')
    with read_snapshot(remote, ('notes/',), cache_dir=tmp_path) as view:
        assert view.read('notes/b.md') == b'b'
        assert view.metrics['downloads'] == view.metrics['cache_hits'] == 1
    assert cache.read(blob) == b'b'
    with read_snapshot(remote, ('notes/',), cache_dir=tmp_path) as view:
        assert view.metrics['downloads'] == 0 and view.metrics['cache_hits'] == 2


@pytest.mark.parametrize('change', ['same_bytes', 'changed_bytes', 'deleted', 'added'])
def test_live_catalog_verification_rejects_changes_even_with_cached_bytes(tmp_path, change):
    remote = Remote({'notes/a.md': b'a'})
    with read_snapshot(remote, ('notes/',), cache_dir=tmp_path):
        pass
    with pytest.raises(SnapshotChangedError):
        with read_snapshot(remote, ('notes/',), cache_dir=tmp_path) as view:
            assert view.metrics['downloads'] == 0
            if change == 'same_bytes':
                remote.replace('notes/a.md')
            elif change == 'changed_bytes':
                remote.replace('notes/a.md', b'new')
            elif change == 'deleted':
                del remote.objects['notes/a.md']
            else:
                remote.objects['notes/new.md'] = (1, b'new')


def test_generation_change_during_download_is_never_retried_as_new_snapshot():
    remote = Remote({'notes/a.md': b'a'})
    remote.on_download = remote.replace
    with pytest.raises(SnapshotChangedError):
        GCSReadSnapshot(remote, ('notes/',))


def test_cache_bucket_identity_and_private_files(tmp_path):
    one = Remote({'notes/a.md': b'a'}, 'one')
    two = Remote({'notes/a.md': b'a'}, 'two')
    for remote in (one, two):
        with read_snapshot(remote, ('notes/',), cache_dir=tmp_path) as view:
            assert view.metrics['downloads'] == 1
    assert all(path.stat().st_mode & 0o077 == 0 for path in tmp_path.rglob('*'))


def test_export_rechecks_live_catalog_before_installing_output(harness, tmp_path):
    h = harness
    assert h.pipeline.run().status == 'success'
    remote = Remote(h.store.data)
    view = GCSReadSnapshot(remote, ('notes/', 'state/index/', 'state/receipts/'))
    name = next(name for name in remote.objects if name.startswith('notes/'))
    remote.replace(name)
    output = tmp_path / 'public'
    with pytest.raises(ExportError, match='snapshot_changed'):
        export_notes(view, output, h.app.tracking_parameters, h.app.categories)
    assert not output.exists()


def test_cli_does_not_print_success_or_publish_notifications_before_verification(harness, monkeypatch, capsys):
    from techkb import cli
    h = harness
    assert h.pipeline.run().status == 'success'
    class ChangedStore:
        @contextmanager
        def read_snapshot(self, prefixes, **kwargs):
            yield h.store
            raise SnapshotChangedError('changed')
    monkeypatch.setattr(cli, 'GCSStore', lambda _: ChangedStore())
    monkeypatch.setattr(cli, 'publish_issues', lambda *a: pytest.fail('unverified notification'))
    assert cli.main(['notify', '--apply']) == 1
    assert not capsys.readouterr().out
