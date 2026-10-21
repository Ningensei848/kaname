"""Exercise sync on a disposable native filesystem; never takes a user's Vault."""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import techkb.sync as sync


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
        note = vault / 'TechKB/notes/2026/10/fixture.md'
        note.write_bytes(b'human edit')
        store.data[next(iter(store.data))] = b'remote update'
        updated = sync.sync_vault(store, vault)
        assert note.read_bytes() == b'human edit' and updated['incoming_written'] == 1
        incoming = vault / 'TechKB' / updated['updates'][0]['incoming']
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
            assert not (root / 'unsupported.md').exists() and not list(root.glob('.techkb-*'))
        finally:
            sync.os.link = original_link
        result['simulated_unsupported_link_left_no_partial_file'] = True
        base, outside = root / 'aliased-vault', root / 'owned-target'
        base.mkdir(); outside.mkdir()
        alias = base / 'TechKB'
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
        assert not (vault / 'TechKB/.techkb-sync.lock').exists()
        result['alias_blocked_before_writes'] = True
    return result


if __name__ == '__main__':
    try:
        print(json.dumps(verify()))
    except Exception:
        print('{"status":"failed","code":"sync_filesystem_acceptance_failed"}', file=sys.stderr)
        raise SystemExit(1)
