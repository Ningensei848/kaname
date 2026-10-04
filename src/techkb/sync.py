"""One-way Obsidian export with atomic files and conservative conflict handling."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
import re


def digest(content):
    return hashlib.sha256(content).hexdigest()


def atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.techkb-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content); stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def safe_destination(root, name):
    pure = PurePosixPath(name)
    if (not name.startswith('notes/') or pure.suffix != '.md' or
            str(pure) != name or '..' in pure.parts or re.search(r'[\\:*?"<>|\x00-\x1f\x7f]', name)):
        raise ValueError('invalid note object path')
    path = root.joinpath(*pure.parts)
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError('symlink in sync path')
        if part == root:
            break
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('sync path escaped vault')
    return path


def sync_vault(store, vault, dry_run=False):
    base = Path(vault).absolute()
    # Keep remote paths under a dedicated vault folder; no .obsidian mutations.
    root = base / 'TechKB'
    if any(p.is_symlink() for p in (root, base, *base.parents)):
        raise ValueError('vault symlink is not supported')
    root.mkdir(parents=True, exist_ok=True)
    lock = root / '.techkb-sync.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        manifest_path = root / '.techkb-sync.json'
        if manifest_path.is_symlink():
            raise ValueError('manifest symlink')
        manifest = json.loads(manifest_path.read_bytes()) if manifest_path.exists() else {}
        if not isinstance(manifest, dict) or any(not isinstance(k,str) or not isinstance(v,str) or
                                               len(v)!=64 for k,v in manifest.items()):
            raise ValueError('invalid sync manifest')
        for name in manifest:
            safe_destination(root,name)
        plan, conflicts, unchanged, seen = [], 0, 0, set()
        baselines = {}
        for name in store.list('notes/'):
            path = safe_destination(root,name)
            key = name.casefold()
            if key in seen:
                raise ValueError('case-insensitive note path collision')
            seen.add(key)
            remote = store.read(name)
            if remote is None:
                raise ValueError('note disappeared during sync')
            remote.decode('utf-8')
            remote_hash = digest(remote)
            baselines[name] = None
            if path.exists():
                local_hash = digest(path.read_bytes())
                baselines[name] = local_hash
                if name not in manifest:
                    conflicts += 1; continue
                if local_hash != manifest[name] and local_hash != remote_hash:
                    conflicts += 1; continue
                if local_hash == remote_hash:
                    unchanged += 1
                    plan.append((name,path,None,remote_hash)); continue
            plan.append((name,path,remote,remote_hash))
        writes = sum(content is not None for _,_,content,_ in plan)
        actual_writes = 0
        if not dry_run:
            for name,path,content,sha in plan:
                safe_destination(root,name)
                current = digest(path.read_bytes()) if path.exists() else None
                if current != baselines[name]:
                    conflicts += 1
                    continue
                if content is not None:
                    atomic(path,content)
                    actual_writes += 1
                manifest[name]=sha
            atomic(manifest_path,json.dumps(manifest,sort_keys=True).encode())
        return dict(status='conflict' if conflicts else 'success', dry_run=dry_run,
                    written=actual_writes, planned=writes, unchanged=unchanged, conflicts=conflicts)
    finally:
        os.close(fd); lock.unlink()
