"""Bounded GCS reads for operational checks, separate from the writable Store.

A fresh catalog pins generations; downloaded bytes can be reused by later CLI
commands in the same private runner directory. Every successful context checks
the live catalog again, including deletions and same-byte replacement (ABA).
"""
import base64
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib
import logging
import os
from pathlib import Path
import re
import tempfile
import time

log = logging.getLogger(__name__)
DEFAULT_READ_WORKERS = 16


def read_workers(value=None):
    """Bound operational parallelism; allow 8/1 as immediate rollback options."""
    if value is None:
        value = os.environ.get('TECHKB_GCS_READ_WORKERS', str(DEFAULT_READ_WORKERS))
    if not isinstance(value, str) or not re.fullmatch(r'(?:[1-9]|1[0-6])', value):
        raise ValueError('invalid read workers')
    return int(value)


def validate_workers(workers):
    if type(workers) is not int or not 1 <= workers <= 16:
        raise ValueError('invalid read workers')


class SnapshotChangedError(RuntimeError):
    pass


class GenerationCache:
    """An optional, private byte cache. Catalogs and validation are never cached."""
    def __init__(self, root, bucket):
        self.root = None
        if root:
            root = Path(root)
            if root.is_symlink():
                raise ValueError('invalid read cache directory')
            root.mkdir(mode=0o700, parents=True, exist_ok=True)
            self.root = root / hashlib.sha256(bucket.encode()).hexdigest()
            if self.root.is_symlink():
                raise ValueError('invalid read cache directory')
            self.root.mkdir(mode=0o700, exist_ok=True)

    def path(self, blob):
        identity = f'v1\0{blob.name}\0{blob.generation}\0{blob.crc32c}'
        return self.root / hashlib.sha256(identity.encode()).hexdigest()

    @staticmethod
    def matches(data, checksum):
        # Keep local publication helpers usable without the GCS runtime.
        import google_crc32c
        crc = google_crc32c.value(data).to_bytes(4, 'big')
        return base64.b64encode(crc).decode() == checksum

    def read(self, blob):
        if self.root is None:
            return None
        path = self.path(blob)
        try:
            if path.is_symlink():
                return None
            data = path.read_bytes()
        except OSError:
            return None
        return data if self.matches(data, blob.crc32c) else None

    def save(self, blob, data):
        if self.root is None:
            return
        temporary = None
        try:
            fd, name = tempfile.mkstemp(dir=self.root)
            temporary = Path(name)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
            os.replace(temporary, self.path(blob))
        except OSError:
            # Optional cache storage must not turn verified remote bytes into
            # an operational failure. A later command can download them again.
            pass
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


class GCSReadSnapshot:
    """Read-only view; no paid operations, storage writes or public cache."""
    def __init__(self, store, prefixes, *, cache_dir=None, workers=DEFAULT_READ_WORKERS):
        validate_workers(workers)
        self.store = store
        self.prefixes = tuple(sorted(set(prefixes), key=lambda p: (p.startswith('state/index/'), p)))
        if not self.prefixes or any(not p for p in self.prefixes):
            raise ValueError('snapshot prefixes required')
        started = time.monotonic()
        self.blobs = self.catalog()
        self.generations = {name: int(blob.generation) for name, blob in self.blobs.items()}
        cache = GenerationCache(cache_dir, store.bucket.name)

        def download(item):
            name, blob = item
            data = cache.read(blob)
            hit = data is not None
            if not hit:
                data = blob.download_as_bytes(if_generation_match=int(blob.generation))
                if not cache.matches(data, blob.crc32c):
                    raise ValueError('GCS byte checksum mismatch')
                cache.save(blob, data)
            return name, data, hit

        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix='gcs-read') as pool:
            results = list(pool.map(download, self.blobs.items()))
        self.data = {name: data for name, data, _ in results}
        self.metrics = dict(objects=len(results), downloads=sum(not hit for _, _, hit in results),
                            cache_hits=sum(hit for _, _, hit in results), workers=workers,
                            load_seconds=round(time.monotonic() - started, 3))
        log.info('GCS read snapshot %s', self.metrics)

    def catalog(self):
        blobs = {}
        for prefix in self.prefixes:
            for blob in self.store.client.list_blobs(self.store.bucket, prefix=prefix):
                if not blob.generation or not blob.crc32c:
                    raise ValueError('GCS object identity unavailable')
                if blob.name in blobs and self.identity(blobs[blob.name]) != self.identity(blob):
                    raise SnapshotChangedError('GCS catalog changed')
                blobs[blob.name] = blob
        return blobs

    @staticmethod
    def identity(blob):
        return int(blob.generation), blob.crc32c

    def allowed(self, name):
        if not any(name.startswith(prefix) for prefix in self.prefixes):
            raise ValueError('read outside snapshot prefixes')

    def list(self, prefix):
        self.allowed(prefix)
        return sorted(name for name in self.data if name.startswith(prefix))

    def read(self, name):
        self.allowed(name)
        return self.data.get(name)

    def write(self, *args, **kwargs):
        raise RuntimeError('snapshot is read-only')

    def verify(self):
        current = self.catalog()
        if ({n: self.identity(b) for n, b in current.items()} !=
                {n: self.identity(b) for n, b in self.blobs.items()}):
            raise SnapshotChangedError('GCS snapshot changed')


@contextmanager
def read_snapshot(store, prefixes, *, cache_dir=None, workers=DEFAULT_READ_WORKERS):
    snapshot = GCSReadSnapshot(store, prefixes, cache_dir=cache_dir, workers=workers)
    yield snapshot
    snapshot.verify()
