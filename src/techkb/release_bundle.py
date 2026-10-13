"""Deterministic public-only checkpoints/deltas; no GitHub, GCS or LLM clients."""
import io
import json
from pathlib import Path
import re
import stat
import tempfile
import zipfile

from .publication.common import ExportError, PUBLIC_README, json_bytes, sha256, digest_value, reject_symlinks
from .publication.install import install_snapshot
from .publication.snapshot import ExportDirectorySnapshot, load_snapshot, unique_json

MAX_DEPTH = 7
MAX_ARCHIVE = 100 * 1024 * 1024
MAX_EXPANDED = 500 * 1024 * 1024
DESCRIPTOR = 'release.json'
ARCHIVE = 'notes.zip'
FIELDS = {'schema_version', 'tag', 'content_commit', 'kind', 'depth', 'base_tag',
          'base_dataset_digest', 'target_dataset_digest', 'snapshot_digest',
          'changed', 'deleted', 'archive_sha256', 'archive_size'}


def release_tag(commit):
    if not isinstance(commit, str) or not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ExportError('invalid_release_commit')
    return 'notes-' + commit


def snapshot_digest(files):
    return sha256(json_bytes([[name, sha256(data)] for name, data in sorted(files.items())]))


def descriptor(data):
    try:
        if len(data) > 1024 * 1024:
            raise ValueError
        value = json.loads(data, object_pairs_hook=unique_json)
        if not isinstance(value, dict) or set(value) != FIELDS:
            raise ValueError
        if (type(value['schema_version']) is not int or value['schema_version'] != 1 or
                value['tag'] != release_tag(value['content_commit']) or
                type(value['depth']) is not int or not 0 <= value['depth'] <= MAX_DEPTH or
                type(value['archive_size']) is not int or not 0 < value['archive_size'] <= MAX_ARCHIVE):
            raise ValueError
        for key in ('target_dataset_digest', 'snapshot_digest', 'archive_sha256'):
            if not digest_value(value[key]):
                raise ValueError
        for key in ('changed', 'deleted'):
            ids = value[key]
            if (not isinstance(ids, list) or len(ids) > 100000 or
                    any(not digest_value(note_id) for note_id in ids) or ids != sorted(set(ids))):
                raise ValueError
        if set(value['changed']) & set(value['deleted']):
            raise ValueError
        if value['kind'] == 'full':
            if value['depth'] != 0 or value['base_tag'] is not None or value['base_dataset_digest'] is not None or value['deleted']:
                raise ValueError
        elif value['kind'] == 'delta':
            if (not value['depth'] or not isinstance(value['base_tag'], str) or
                    not re.fullmatch(r'notes-[0-9a-f]{40}', value['base_tag']) or
                    value['base_tag'] == value['tag'] or not digest_value(value['base_dataset_digest'])):
                raise ValueError
        else:
            raise ValueError
        return value
    except (ValueError, TypeError, KeyError, UnicodeError):
        raise ExportError('invalid_release_descriptor') from None


def public_files(root):
    reader = ExportDirectorySnapshot(root)
    if any(child.name in {'.git', '.gitattributes'} for child in reader.root.iterdir()):
        raise ExportError('release_git_metadata')
    manifest, files, metadata = load_snapshot(root)
    readme = reader.read('README.md')
    if readme != PUBLIC_README:
        raise ExportError('invalid_release_readme')
    files = dict(files, **{'README.md': readme})
    if any(reader.read(name) != data for name, data in files.items()):
        raise ExportError('snapshot_changed')
    return manifest, files, metadata


def validated_files(files):
    # Run exactly the same publication policy as GCS export/Git/Quartz input.
    if (not isinstance(files, dict) or
            any(not isinstance(name, str) or not isinstance(data, bytes) or
                name not in {'README.md', 'manifest.json'} and not re.fullmatch(r'notes/[0-9a-f]{64}\.md', name)
                for name, data in files.items())):
        raise ExportError('invalid_release_files')
    with tempfile.TemporaryDirectory(prefix='kaname-release-validation-') as temporary:
        root = Path(temporary) / 'snapshot'
        install_snapshot(root, files)
        return public_files(root)


def build_bundle(root, commit, base=None):
    manifest, files, _ = public_files(root)
    prior, previous = (None, {}) if base is None else base
    if prior is not None:
        prior = descriptor(json_bytes(prior))
        previous_manifest, previous, _ = validated_files(previous)
        if (previous_manifest['dataset_digest'] != prior['target_dataset_digest'] or
                snapshot_digest(previous) != prior['snapshot_digest']):
            raise ExportError('release_base_mismatch')
    full = prior is None or prior['depth'] == MAX_DEPTH
    old = {name[6:-3]: data for name, data in previous.items() if name.startswith('notes/')}
    notes = {name[6:-3]: data for name, data in files.items() if name.startswith('notes/')}
    changed = sorted(notes if full else (note_id for note_id in notes if notes[note_id] != old.get(note_id)))
    deleted = [] if full else sorted(old.keys() - notes.keys())
    payload = {name: files[name] for name in ('README.md', 'manifest.json')}
    payload.update({f'notes/{note_id}.md': notes[note_id] for note_id in changed})
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(payload.items()):
            entry = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(entry, data, compresslevel=9)
    packed = stream.getvalue()
    value = dict(schema_version=1, tag=release_tag(commit), content_commit=commit,
                 kind='full' if full else 'delta', depth=0 if full else prior['depth'] + 1,
                 base_tag=None if full else prior['tag'],
                 base_dataset_digest=None if full else prior['target_dataset_digest'],
                 target_dataset_digest=manifest['dataset_digest'], snapshot_digest=snapshot_digest(files),
                 changed=changed, deleted=deleted, archive_sha256=sha256(packed), archive_size=len(packed))
    descriptor(json_bytes(value))
    return value, packed


def apply_bundle(value, packed, base=None):
    value = descriptor(json_bytes(value))
    if len(packed) != value['archive_size'] or sha256(packed) != value['archive_sha256']:
        raise ExportError('release_archive_mismatch')
    expected = {'README.md', 'manifest.json'} | {f'notes/{note_id}.md' for note_id in value['changed']}
    try:
        with zipfile.ZipFile(io.BytesIO(packed)) as archive:
            entries = archive.infolist()
            if (len(entries) != len(expected) or {item.filename for item in entries} != expected or
                    sum(item.file_size for item in entries) > MAX_EXPANDED or
                    any(item.flag_bits & 1 or stat.S_IFMT(item.external_attr >> 16) != stat.S_IFREG for item in entries)):
                raise ValueError
            payload = {item.filename: archive.read(item) for item in entries}
    except (ValueError, RuntimeError, zipfile.BadZipFile, NotImplementedError, OSError):
        raise ExportError('invalid_release_archive') from None
    if value['kind'] == 'full':
        if base is not None:
            raise ExportError('release_unexpected_base')
        files = payload
    else:
        if base is None:
            raise ExportError('release_missing_base')
        prior, previous = base
        prior = descriptor(json_bytes(prior))
        previous_manifest, previous, _ = validated_files(previous)
        if (prior['tag'] != value['base_tag'] or prior['depth'] + 1 != value['depth'] or
                prior['target_dataset_digest'] != value['base_dataset_digest'] or
                previous_manifest['dataset_digest'] != value['base_dataset_digest'] or
                snapshot_digest(previous) != prior['snapshot_digest']):
            raise ExportError('release_base_mismatch')
        files = dict(previous)
        for note_id in value['deleted']:
            if files.pop(f'notes/{note_id}.md', None) is None:
                raise ExportError('release_invalid_deletion')
        for note_id in value['changed']:
            name = f'notes/{note_id}.md'
            if files.get(name) == payload[name]:
                raise ExportError('release_redundant_change')
        files.update(payload)
    manifest, checked, metadata = validated_files(files)
    if (manifest['dataset_digest'] != value['target_dataset_digest'] or
            snapshot_digest(checked) != value['snapshot_digest']):
        raise ExportError('release_target_mismatch')
    return manifest, checked, metadata


def release_input(root, commit, receipt):
    """Recheck restored bytes at both build and browser-acceptance boundaries."""
    path = Path(receipt).absolute()
    reject_symlinks(path)
    value = descriptor(path.read_bytes())
    if value['content_commit'] != commit:
        raise ExportError('release_commit_mismatch')
    manifest, files, metadata = public_files(root)
    if (manifest['dataset_digest'] != value['target_dataset_digest'] or
            snapshot_digest(files) != value['snapshot_digest']):
        raise ExportError('release_input_mismatch')
    return manifest, {name: data for name, data in files.items() if name != 'README.md'}, metadata
