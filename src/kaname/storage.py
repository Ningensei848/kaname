from pathlib import Path
from typing import Protocol
from requests.adapters import HTTPAdapter
from google.cloud import storage
from google.api_core.exceptions import NotFound

class Store(Protocol):
    def list(self, prefix: str) -> list[str]: ...
    def read(self, name: str) -> bytes | None: ...
    def write(self, name: str, content: bytes, content_type: str = "application/octet-stream") -> None: ...

class GCSStore:
    """Generation-guarded operations; never silently overwrite a concurrent writer."""
    def __init__(self, bucket_name: str):
        if not bucket_name:
            raise ValueError("GCS_BUCKET or storage.bucket is required")
        self.client = storage.Client()
        self.bucket = self.client.get_bucket(bucket_name)
        if (not self.bucket.iam_configuration.uniform_bucket_level_access_enabled or
                self.bucket.iam_configuration.public_access_prevention != "enforced"):
            raise ValueError("bucket must enforce uniform access and public access prevention")
        self.generations = {}

    def list(self, prefix):
        return sorted(blob.name for blob in self.client.list_blobs(self.bucket, prefix=prefix))

    def read(self, name):
        blob = self.bucket.get_blob(name)
        if blob is None:
            self.generations[name] = 0
            return None
        self.generations[name] = int(blob.generation)
        return blob.download_as_bytes(if_generation_match=int(blob.generation))

    def write(self, name, content, content_type="application/octet-stream"):
        if name not in self.generations:
            self.read(name)
        blob = self.bucket.blob(name)
        blob.upload_from_string(content, content_type=content_type,
                                if_generation_match=self.generations[name])
        self.generations[name] = int(blob.generation)

    def read_snapshot(self, prefixes, *, cache_dir=None, workers=None):
        from .read_snapshot import read_snapshot, read_workers, validate_workers
        workers = read_workers() if workers is None else workers
        validate_workers(workers)
        self._configure_read_pool(workers)
        return read_snapshot(self, prefixes, cache_dir=cache_dir, workers=workers)

    def _configure_read_pool(self, workers):
        """Keep SDK auth, retries, TLS and non-Storage transports unchanged."""
        if getattr(self, '_read_pool_workers', None) == workers:
            return
        session = self.client._http
        endpoint = self.client._connection.API_BASE_URL.rstrip('/') + '/'
        current = session.get_adapter(endpoint)
        # Preserve custom/mTLS adapter subclasses and their certificate policy.
        if type(current) is not HTTPAdapter:
            return
        adapter = HTTPAdapter(pool_connections=workers, pool_maxsize=workers,
                              max_retries=current.max_retries, pool_block=False)
        previous = getattr(self, '_read_adapter', None)
        session.mount(endpoint, adapter)
        self._read_adapter, self._read_pool_workers = adapter, workers
        if previous is not None:
            previous.close()

    def close(self):
        self.client.close()

class DirectorySnapshot:
    """Read-only local state for dry-run. Never used for production writes."""
    def __init__(self, root):
        self.root = Path(root).resolve()

    def list(self, prefix):
        return sorted(str(p.relative_to(self.root)) for p in (self.root / prefix).rglob("*") if p.is_file())

    def read(self, name):
        path = (self.root / name).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("invalid object path")
        return path.read_bytes() if path.exists() else None

    def write(self, *args, **kwargs):
        raise RuntimeError("snapshot is read-only")
