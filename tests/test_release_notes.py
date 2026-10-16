"""Public delta integrity and publication failure/retry boundaries."""
import io
import base64
import json
from pathlib import Path
import stat
import zipfile
import httpx
import pytest
from techkb.publication import ExportError, export_notes, json_bytes, sha256
from techkb.publication.snapshot import load_snapshot
from techkb.release_bundle import (ARCHIVE, DESCRIPTOR, MAX_DEPTH, apply_bundle, public_files,
    build_bundle, descriptor, release_input, release_tag)
from techkb.release_publication import ReleaseClient, publish_release, restore_release
from test_publication import add_note, change_note


@pytest.fixture
def snapshots(harness, tmp_path):
    first, receipt = add_note(harness)
    add_note(harness, url='https://example.com/removed')
    before = tmp_path / 'before'
    export_notes(harness.store, before)
    removed = next(e['id'] for e in load_snapshot(before)[0]['notes'] if e['canonical_url'].endswith('/removed'))
    from techkb.metadata_refresh import refresh_note_metadata
    change_note(harness, first, receipt, lambda note: refresh_note_metadata(note, ['Alice Example'], ''))
    add_note(harness, url='https://example.com/added')
    after = tmp_path / 'after'
    export_notes(harness.store, after, exclude_ids=[removed])
    return before, after, removed


def test_full_delta_update_add_delete_and_deterministic_bytes(snapshots):
    before, after, removed = snapshots
    full, packed = build_bundle(before, '1' * 40)
    assert (full, packed) == build_bundle(before, '1' * 40)
    _, original, _ = apply_bundle(full, packed)
    delta, changed = build_bundle(after, '2' * 40, (full, original))
    assert delta['kind'] == 'delta' and delta['depth'] == 1
    assert delta['deleted'] == [removed] and len(delta['changed']) == 2
    _, restored, _ = apply_bundle(delta, changed, (full, original))
    assert restored == public_files(after)[1]
    assert f'notes/{removed}.md' not in restored
    with zipfile.ZipFile(io.BytesIO(changed)) as archive:
        assert set(archive.namelist()) == {'README.md', 'manifest.json'} | {f'notes/{i}.md' for i in delta['changed']}


def test_checkpoint_bounds_chain(snapshots):
    before, after, _ = snapshots
    base = None
    for index in range(MAX_DEPTH + 3):
        value, packed = build_bundle(before if index == 0 else after, f'{index + 1:040x}', base)
        assert value['kind'] == ('full' if index in (0, MAX_DEPTH + 1) else 'delta')
        _, files, _ = apply_bundle(value, packed, None if value['kind'] == 'full' else base)
        base = value, files


@pytest.mark.parametrize('damage', ['packed', 'digest', 'size', 'target', 'snapshot', 'missing_base', 'base', 'depth', 'deletion'])
def test_corruption_or_wrong_base_never_installs(snapshots, damage):
    full, packed = build_bundle(snapshots[0], '1' * 40)
    _, original, _ = apply_bundle(full, packed)
    value, packed = build_bundle(snapshots[1], '2' * 40, (full, original))
    base = full, original
    if damage == 'packed': packed += b'corrupt'
    elif damage == 'digest': value['archive_sha256'] = 'f' * 64
    elif damage == 'size': value['archive_size'] += 1
    elif damage == 'target': value['target_dataset_digest'] = 'f' * 64
    elif damage == 'snapshot': value['snapshot_digest'] = 'f' * 64
    elif damage == 'missing_base': base = None
    elif damage == 'base': value['base_dataset_digest'] = 'f' * 64
    elif damage == 'depth': value['depth'] = 2
    elif damage == 'deletion': value['deleted'] = ['f' * 64]
    with pytest.raises(ExportError): apply_bundle(value, packed, base)


@pytest.mark.parametrize('damage', ['traversal', 'private', 'duplicate', 'symlink', 'directory', 'oversize'])
def test_hostile_archive_is_never_extracted(snapshots, damage):
    value, packed = build_bundle(snapshots[0], '1' * 40)
    buffer = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(packed)) as source, zipfile.ZipFile(buffer, 'w') as archive:
        for item in source.infolist():
            if damage in ('symlink', 'directory') and item.filename == 'README.md':
                item.external_attr = (stat.S_IFLNK if damage == 'symlink' else stat.S_IFDIR) << 16
            archive.writestr(item, source.read(item))
        if damage in ('traversal', 'private', 'duplicate'):
            archive.writestr({'traversal': '../escaped', 'private': 'state/index.tsv', 'duplicate': 'README.md'}[damage], b'private')
    packed = buffer.getvalue()
    value.update(archive_sha256=sha256(packed), archive_size=len(packed))
    if damage == 'oversize': value['archive_size'] = 101 * 1024 * 1024
    with pytest.raises(ExportError): apply_bundle(value, packed)


@pytest.mark.parametrize('field,replacement', [('depth', True), ('changed', ['f' * 64, 'f' * 64]),
    ('content_commit', 'main'), ('base_tag', 'notes-' + '2' * 40), ('kind', 'unknown'), ('schema_version', 2)])
def test_descriptor_schema_is_closed(snapshots, field, replacement):
    value, _ = build_bundle(snapshots[0], '1' * 40)
    value[field] = replacement
    with pytest.raises(ExportError): descriptor(json_bytes(value))


class GitHub:
    """HTTP-shaped GitHub with persistent drafts, assets and lightweight tags."""
    def __init__(self, snapshots):
        self.releases, self.tags, self.data, self.calls = {}, {}, {}, []
        self.fail_upload = None
        self.manifests = {str(i + 1) * 40: (root / 'manifest.json').read_bytes() for i, root in enumerate(snapshots[:2])}

    def handle(self, request):
        path, method = request.url.path, request.method
        self.calls.append((method, path))
        prefix = '/repos/owner/repo'
        assert path.startswith(prefix)
        path = path.removeprefix(prefix)
        if path == '/contents/manifest.json':
            data = self.manifests[request.url.params['ref']]
            return httpx.Response(200, json=dict(encoding='base64', size=len(data), content=base64.b64encode(data).decode()))
        if path.startswith('/git/ref/tags/'):
            tag = path.removeprefix('/git/ref/tags/')
            if tag not in self.tags: return httpx.Response(404)
            return httpx.Response(200, json={'object': {'type': 'commit', 'sha': self.tags[tag]}})
        if path == '/git/refs' and method == 'POST':
            value = json.loads(request.content)
            self.tags[value['ref'].removeprefix('refs/tags/')] = value['sha']
            return httpx.Response(201, json={})
        if path == '/releases' and method == 'GET':
            return httpx.Response(200, json=list(reversed(list(self.releases.values()))))
        if path == '/releases' and method == 'POST':
            value = json.loads(request.content)
            assert value['draft'] and value['make_latest'] == 'false'
            value.update(id=len(self.releases) + 1, assets=[])
            self.releases[value['tag_name']] = value
            return httpx.Response(201, json=value)
        if path.startswith('/releases/tags/'):
            value = self.releases.get(path.removeprefix('/releases/tags/'))
            return httpx.Response(404) if value is None or value['draft'] else httpx.Response(200, json=value)
        if path.startswith('/releases/assets/'):
            return httpx.Response(200, content=self.data[int(path.rsplit('/', 1)[1])])
        release_id = int(path.split('/')[2])
        release = next(v for v in self.releases.values() if v['id'] == release_id)
        if method == 'GET': return httpx.Response(200, json=release)
        if method == 'PATCH':
            assert {a['name'] for a in release['assets']} == {ARCHIVE, DESCRIPTOR}
            release.update(json.loads(request.content))
            return httpx.Response(200, json=release)
        if method == 'POST' and path.endswith('/assets'):
            name = request.url.params['name']
            if self.fail_upload == name: return httpx.Response(503, json={'message': 'secret upstream text'})
            asset_id, data = len(self.data) + 100, request.content
            self.data[asset_id] = data
            release['assets'].append(dict(id=asset_id, name=name, state='uploaded', size=len(data), digest='sha256:' + sha256(data)))
            return httpx.Response(201, json={})
        raise AssertionError((method, path))

    def client(self):
        return ReleaseClient('owner/repo', 'private-token', httpx.Client(transport=httpx.MockTransport(self.handle)))


def test_http_full_delta_restore_and_repeat_without_writes(snapshots, tmp_path):
    api = GitHub(snapshots)
    client = api.client()
    try:
        first = publish_release(snapshots[0], '1' * 40, client)
        assert first['kind'] == 'full' and first['notes'] == 2
        second = publish_release(snapshots[1], '2' * 40, client)
        assert second['kind'] == 'delta' and second['deleted'] == 1
        mutations = len([m for m, _ in api.calls if m != 'GET'])
        assert publish_release(snapshots[1], '2' * 40, client)['unchanged']
        assert len([m for m, _ in api.calls if m != 'GET']) == mutations
        output, receipt = tmp_path / 'restored', tmp_path / 'receipt.json'
        restore_release(second['tag'], '2' * 40, output, receipt, client)
        assert load_snapshot(output)[1] == load_snapshot(snapshots[1])[1]
        assert release_input(output, '2' * 40, receipt)[1] == load_snapshot(output)[1]
        restore_release(second['tag'], '2' * 40, output, receipt, client)
        with pytest.raises(ExportError): release_input(output, '1' * 40, receipt)
        (output / 'private.json').write_text('private')
        with pytest.raises(ExportError): release_input(output, '2' * 40, receipt)
    finally: client.close()


def test_partial_upload_keeps_draft_and_resumes_without_overwriting(snapshots):
    api = GitHub(snapshots)
    client = api.client()
    try:
        api.fail_upload = ARCHIVE
        with pytest.raises(ExportError, match='release_upload_failed'):
            publish_release(snapshots[0], '1' * 40, client)
        staged = api.releases[release_tag('1' * 40)]
        assert staged['draft'] and len(staged['assets']) == 1
        with pytest.raises(ExportError, match='release_missing'): client.restore_files(staged['tag_name'])
        descriptor_id = staged['assets'][0]['id']
        api.fail_upload = None
        assert not publish_release(snapshots[0], '1' * 40, client)['unchanged']
        assert not staged['draft'] and staged['assets'][0]['id'] == descriptor_id
        assert len(api.releases) == 1
    finally: client.close()


def test_operation_cache_reduces_bytes_without_reusing_metadata_or_changing_publication(snapshots):
    results = []
    for limit in (0, 32 * 1024 * 1024):
        api = GitHub(snapshots)
        client = ReleaseClient('owner/repo', 'private-token',
                               httpx.Client(transport=httpx.MockTransport(api.handle)), cache_bytes=limit)
        try:
            publish_release(snapshots[0], '1' * 40, client)
            api.calls.clear()
            result = publish_release(snapshots[1], '2' * 40, client)
            metadata = [(m, p) for m, p in api.calls if not p.startswith('/repos/owner/repo/releases/assets/')]
            results.append((result, metadata, dict(api.data), dict(api.tags)))
            assert client._cache is None  # No bytes live past a publication.
        finally:
            client.close()
    before, after = results
    assert {k: v for k, v in before[0].items() if k != 'transport'} == {k: v for k, v in after[0].items() if k != 'transport'}
    assert before[1:] == after[1:]  # Fresh metadata calls, writes, tags and asset bytes are identical.
    assert after[0]['transport']['asset_downloads'] < before[0]['transport']['asset_downloads']
    assert after[0]['transport']['download_bytes'] < before[0]['transport']['download_bytes']
    assert after[0]['transport']['cache_hits'] > 0


@pytest.mark.parametrize('change', ['digest', 'size', 'id', 'state', 'missing_digest', 'tag'])
def test_fresh_identity_changes_are_rejected_even_with_warm_bytes(snapshots, change):
    api = GitHub(snapshots)
    client = api.client()
    try:
        tag = publish_release(snapshots[0], '1' * 40, client)['tag']
        with client.operation():
            client.restore_files(tag)
            archive = next(a for a in api.releases[tag]['assets'] if a['name'] == ARCHIVE)
            old = api.data[archive['id']]
            if change == 'digest': archive['digest'] = 'sha256:' + 'f' * 64
            elif change == 'size': archive['size'] += 1
            elif change == 'state': archive['state'] = 'new'
            elif change == 'tag': api.tags[tag] = 'f' * 40
            else:
                if change == 'id': archive['id'] += 1000
                if change == 'missing_digest': archive.pop('digest')
                api.data[archive['id']] = b'x' * len(old)
            with pytest.raises(ExportError):
                client.restore_files(tag)
    finally:
        client.close()


def test_asset_cache_is_bounded_and_missing_digest_is_never_reused():
    calls = []
    def handle(request):
        calls.append(request.url.path)
        return httpx.Response(200, content=b'bytes')
    client = ReleaseClient('owner/repo', client=httpx.Client(transport=httpx.MockTransport(handle)), cache_bytes=8)
    def asset(number, digest=True):
        result = dict(id=number, state='uploaded', size=5)
        if digest: result['digest'] = 'sha256:' + sha256(b'bytes')
        return result
    try:
        with client.operation():
            client.download(asset(1), 100)
            client.download(asset(1), 100)
            assert len(calls) == 1
            client.download(asset(2), 100)  # Evicts asset 1 at the byte cap.
            client.download(asset(1), 100)
            client.download(asset(3, False), 100)
            client.download(asset(3, False), 100)
            assert len(calls) == 5
            assert client.metrics['peak_cache_bytes'] <= 8
        with client.operation():
            client.download(asset(1), 100)
            assert len(calls) == 6  # The previous operation cannot supply bytes.
    finally:
        client.close()


def test_published_conflict_cannot_mutate_or_deploy(snapshots, tmp_path):
    api = GitHub(snapshots)
    client = api.client()
    try:
        result = publish_release(snapshots[0], '1' * 40, client)
        calls = len(api.calls)
        with pytest.raises(ExportError, match='release_content_mismatch'):
            publish_release(snapshots[1], '1' * 40, client)
        assert all(m == 'GET' for m, _ in api.calls[calls:])
        api.tags[result['tag']] = 'f' * 40
        with pytest.raises(ExportError, match='release_tag_mismatch'):
            restore_release(result['tag'], '1' * 40, tmp_path / 'output', tmp_path / 'receipt', client)
        assert not (tmp_path / 'output').exists()
    finally: client.close()


@pytest.mark.parametrize('target', ['https://evil.example/asset', 'http://release-assets.githubusercontent.com/asset',
    'https://user:password@release-assets.githubusercontent.com/asset', 'https://release-assets.githubusercontent.com:444/asset'])
def test_redirect_cannot_leak_credentials(target):
    def handler(request):
        assert request.url.host == 'api.github.com'
        return httpx.Response(302, headers={'location': target})
    client = ReleaseClient('owner/repo', 'secret', httpx.Client(transport=httpx.MockTransport(handler)))
    try:
        with pytest.raises(ExportError): client.download(dict(id=1, size=1, state='uploaded'), 100)
    finally: client.close()


def test_redirect_strips_auth_and_checks_digest():
    def handler(request):
        if request.url.host == 'api.github.com':
            assert request.headers['authorization'] == 'Bearer secret'
            return httpx.Response(302, headers={'location': 'https://release-assets.githubusercontent.com/blob'})
        assert 'authorization' not in request.headers
        return httpx.Response(200, content=b'bytes')
    client = ReleaseClient('owner/repo', 'secret', httpx.Client(transport=httpx.MockTransport(handler)))
    try:
        asset = dict(id=1, size=5, state='uploaded', digest='sha256:' + sha256(b'bytes'))
        assert client.download(asset, 100) == b'bytes'
        asset['digest'] = 'sha256:' + 'f' * 64
        with pytest.raises(ExportError): client.download(asset, 100)
    finally: client.close()


def test_daily_uses_release_and_keeps_git_rollback():
    import yaml
    root = Path(__file__).parents[1]
    daily = yaml.load((root / '.github/workflows/daily.yml').read_text(), Loader=yaml.BaseLoader)
    pages = yaml.load((root / '.github/workflows/pages.yml').read_text(), Loader=yaml.BaseLoader)
    assert daily['jobs']['publish']['permissions'] == {'contents': 'write'}
    assert daily['jobs']['pages']['with']['release_tag'] == '${{ needs.publish.outputs.release_tag }}'
    checkout = next(s for s in pages['jobs']['build']['steps'] if s.get('with', {}).get('ref') == 'content')
    assert checkout['if'] == "inputs.release_tag == ''"
    restore = next(s for s in pages['jobs']['build']['steps'] if 'scripts/release_notes.py restore' in s.get('run', ''))
    assert restore['if'] == "inputs.release_tag != ''"
    build = next(s for s in pages['jobs']['build']['steps'] if s.get('id') == 'build')
    assert '--release-receipt' in build['run'] and 'check:pages' in build['run']


def test_incomplete_or_corrupt_remote_chain_cannot_install(snapshots, tmp_path):
    api = GitHub(snapshots)
    client = api.client()
    try:
        first = publish_release(snapshots[0], '1' * 40, client)
        second = publish_release(snapshots[1], '2' * 40, client)
        del api.releases[first['tag']]
        with pytest.raises(ExportError, match='release_missing'):
            restore_release(second['tag'], '2' * 40, tmp_path / 'output', tmp_path / 'receipt', client)
        assert not (tmp_path / 'output').exists()
    finally: client.close()


def test_release_pages_preserves_git_artifact_and_refuses_modified_bytes(pages, tmp_path):
    from techkb.publication import PUBLIC_README
    from techkb.publication.git_snapshot import content_snapshot
    from techkb.publication.install import install_snapshot
    from kaname_web.pages import prepare_pages
    checkout, commit, artifact, _ = pages
    _, files, _ = content_snapshot(checkout, commit)
    root, receipt = tmp_path / 'release-content', tmp_path / 'receipt.json'
    install_snapshot(root, dict(files, **{'README.md': PUBLIC_README}))
    value, _ = build_bundle(root, commit)
    receipt.write_bytes(json_bytes(value))
    result = prepare_pages(root, commit, artifact, tmp_path / 'release-pages', receipt)
    assert result['notes'] > 0
    next((root / 'notes').iterdir()).write_text('modified')
    with pytest.raises(ExportError):
        prepare_pages(root, commit, artifact, tmp_path / 'other-pages', receipt)
    assert not (tmp_path / 'other-pages').exists()


# Reuse the real Git-bound artifact fixture rather than inventing a weaker one.
from test_pages import pages
