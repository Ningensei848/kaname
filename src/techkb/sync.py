"""One-way export; existing Notes stay editable and updates become candidates."""
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


def publish_new(path, content):
    """Publish complete bytes without replacing a concurrently created file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.techkb-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content); stream.flush(); os.fsync(stream.fileno())
        try:
            # An exclusive open would expose partial bytes to an editor. A hard
            # link publishes the completed file and fails if the target exists.
            os.link(name, path)
            return True
        except FileExistsError:
            return False
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
            # Separate immutable candidates from editable Notes. Full digests
            # keep paths short and distinguish both source object and revision.
            incoming = safe_destination(root / 'incoming',
                'notes/' + digest(name.encode()) + '/' + remote_hash + '.md')
            action = 'new'
            if path.exists():
                local_hash = digest(path.read_bytes())
                if name in manifest and local_hash == remote_hash:
                    unchanged += 1
                    action = 'unchanged'
                else:
                    # A final rehash cannot make os.replace conditional on the
                    # editor's bytes. Never replace an existing Note at all.
                    conflicts += 1
                    action = 'incoming'
            plan.append((name,path,remote,remote_hash,action,incoming))
        writes = sum(action == 'new' for _,_,_,_,action,_ in plan)
        incoming_planned = sum(action == 'incoming' for _,_,_,_,action,_ in plan)
        actual_writes = incoming_written = 0
        updates = []
        if not dry_run:
            for name,path,content,sha,action,incoming in plan:
                safe_destination(root,name)
                if action == 'unchanged':
                    current = digest(path.read_bytes()) if path.exists() else None
                    if current == sha:
                        manifest[name]=sha
                        continue
                    unchanged -= 1
                    conflicts += 1
                    action = 'incoming'
                if action == 'new' and publish_new(path,content):
                    actual_writes += 1
                    manifest[name]=sha
                    continue
                if action == 'new':
                    # A local file appeared after planning. Preserve it even if
                    # its bytes match; do not adopt an untracked file.
                    conflicts += 1
                safe_destination(root / 'incoming', incoming.relative_to(root / 'incoming').as_posix())
                created = publish_new(incoming,content)
                candidate_status = 'created' if created else 'unchanged'
                if created:
                    incoming_written += 1
                else:
                    safe_destination(root / 'incoming', incoming.relative_to(root / 'incoming').as_posix())
                    if digest(incoming.read_bytes()) != sha:
                        candidate_status = 'conflict'
                updates.append(dict(note=name, incoming=incoming.relative_to(root).as_posix(),
                                    status=candidate_status))
            atomic(manifest_path,json.dumps(manifest,sort_keys=True).encode())
        else:
            updates = [dict(note=name, incoming=incoming.relative_to(root).as_posix(), status='planned')
                       for name,_,_,_,action,incoming in plan if action == 'incoming']
        return dict(status='conflict' if conflicts else 'success', dry_run=dry_run,
                    written=actual_writes, planned=writes, unchanged=unchanged, conflicts=conflicts,
                    incoming_planned=incoming_planned, incoming_written=incoming_written,
                    updates=updates)
    finally:
        os.close(fd); lock.unlink()
