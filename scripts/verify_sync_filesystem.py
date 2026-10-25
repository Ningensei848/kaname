"""Exercise sync on a disposable native filesystem; never takes a user's Vault."""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import kaname.sync as sync


class FixtureStore:
    def __init__(self):
        self.data = {'notes/2026/10/fixture.md': b'original'}

    def list(self, prefix):
        return sorted(name for name in self.data if name.startswith(prefix))

    def read(self, name):
        return self.data.get(name)


def verify():
    result = dict(status='passed', platform=sys.platform)
    with tempfile.TemporaryDirectory(prefix='kaname-sync-acceptance-') as temporary:
        root, store = Path(temporary), FixtureStore()
        if os.name == 'nt':
            filesystem = ctypes.create_unicode_buffer(64)
            if not ctypes.windll.kernel32.GetVolumeInformationW(root.anchor, None, 0, None, None, None, filesystem, 64):
                raise RuntimeError('filesystem_identity_unavailable')
            result['filesystem'] = filesystem.value
        vault = root / 'vault'
        assert sync.sync_vault(store, vault)['written'] == 1
        note = vault / 'kaname/notes/2026/10/fixture.md'
        note.write_bytes(b'human edit')
        store.data[next(iter(store.data))] = b'remote update'
        updated = sync.sync_vault(store, vault)
        assert note.read_bytes() == b'human edit' and updated['incoming_written'] == 1
        incoming = vault / 'kaname' / updated['updates'][0]['incoming']
        incoming.write_bytes(b'human candidate')
        assert sync.sync_vault(store, vault)['updates'][0]['status'] == 'conflict'
        assert incoming.read_bytes() == b'human candidate'
        result['note_and_candidate_edits_preserved'] = True
        target = root / 'already-present.md'
        target.write_bytes(b'existing')
        assert not sync.publish_new(target, b'replacement') and target.read_bytes() == b'existing'
        result['exclusive_publish_preserved'] = True
        original_link = sync.os.link
        def unsupported(*_, **__):
            raise OSError('injected unsupported hard link')
        sync.os.link = unsupported
        try:
            try:
                sync.publish_new(root / 'unsupported.md', b'candidate')
            except OSError:
                pass
            else:
                raise AssertionError('unsupported_hard_link_accepted')
            assert not (root / 'unsupported.md').exists() and not list(root.glob('.kaname-*'))
        finally:
            sync.os.link = original_link
        result['simulated_unsupported_link_left_no_partial_file'] = True
        base, outside = root / 'aliased-vault', root / 'owned-target'
        base.mkdir(); outside.mkdir()
        alias = base / 'kaname'
        if os.name == 'nt':
            subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J', str(alias), str(outside)],
                           check=True, capture_output=True)
        else:
            alias.symlink_to(outside, target_is_directory=True)
        try:
            sync.sync_vault(FixtureStore(), base)
        except ValueError:
            pass
        else:
            raise AssertionError('filesystem_alias_accepted')
        assert not list(outside.iterdir())
        assert not (vault / 'kaname/.kaname-sync.lock').exists()
        result['alias_blocked_before_writes'] = True
        legacy_alias_base = root / 'legacy-aliased-vault'
        legacy_alias_base.mkdir()
        legacy_alias = legacy_alias_base / 'TechKB'
        if os.name == 'nt':
            subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J', str(legacy_alias), str(outside)],
                           check=True, capture_output=True)
        else:
            legacy_alias.symlink_to(outside, target_is_directory=True)
        try:
            sync.sync_vault(FixtureStore(), legacy_alias_base)
        except ValueError:
            pass
        else:
            raise AssertionError('legacy_filesystem_alias_accepted')
        assert not list(outside.iterdir())
        result['legacy_alias_blocked_before_writes'] = True
        # Run the new CLI's sync against an existing old-name layout, including
        # its editor changes, candidate edits and the lock held by an old CLI.
        legacy_vault = root / 'legacy-vault'
        legacy_root = legacy_vault / 'TechKB'
        legacy_note = legacy_root / 'notes/2026/10/fixture.md'
        legacy_note.parent.mkdir(parents=True)
        legacy_note.write_bytes(b'legacy human edit')
        manifest = legacy_root / '.techkb-sync.json'
        manifest.write_text(json.dumps({'notes/2026/10/fixture.md': sync.digest(b'original')}))
        before_manifest = manifest.read_bytes()
        old_lock = legacy_root / '.techkb-sync.lock'
        old_lock.touch()
        try:
            sync.sync_vault(store, legacy_vault)
        except FileExistsError:
            pass
        else:
            raise AssertionError('legacy_lock_ignored')
        assert old_lock.exists() and manifest.read_bytes() == before_manifest
        old_lock.unlink()
        updated = sync.sync_vault(store, legacy_vault)
        assert not (legacy_vault / 'kaname').exists()
        assert legacy_note.read_bytes() == b'legacy human edit'
        candidate = legacy_root / updated['updates'][0]['incoming']
        candidate.write_bytes(b'legacy candidate edit')
        assert sync.sync_vault(store, legacy_vault)['updates'][0]['status'] == 'conflict'
        assert candidate.read_bytes() == b'legacy candidate edit'
        assert manifest.read_bytes() == before_manifest
        result['legacy_edits_candidates_manifest_and_lock_preserved'] = True
        (legacy_vault / 'kaname').mkdir()
        try:
            sync.sync_vault(store, legacy_vault)
        except ValueError:
            pass
        else:
            raise AssertionError('dual_sync_roots_accepted')
        assert not list((legacy_vault / 'kaname').iterdir())
        (legacy_vault / 'kaname').rmdir()
        # Explicit user migration, with every writer stopped, preserves the
        # same manifest and incoming files under the new root and filename.
        migrated = legacy_vault / 'kaname'
        legacy_root.rename(migrated)
        (migrated / '.techkb-sync.json').rename(migrated / '.kaname-sync.json')
        assert sync.sync_vault(store, legacy_vault)['updates'][0]['status'] == 'conflict'
        assert (migrated / candidate.relative_to(legacy_root)).read_bytes() == b'legacy candidate edit'
        assert (migrated / '.kaname-sync.json').read_bytes() == before_manifest
        result['dual_roots_rejected_and_explicit_migration_preserved'] = True
    return result


if __name__ == '__main__':
    try:
        print(json.dumps(verify()))
    except Exception:
        print('{"status":"failed","code":"sync_filesystem_acceptance_failed"}', file=sys.stderr)
        raise SystemExit(1)
