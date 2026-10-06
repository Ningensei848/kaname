import json
from pathlib import Path

import pytest

from techkb.distribution import publish_snapshot
from techkb.pages import content_snapshot, prepare_pages
from techkb.publication import ExportError, export_notes
from techkb.site import load_snapshot, seal_artifact
from test_distribution import git, clone


@pytest.fixture
def pages(harness, tmp_path):
    harness.pipeline.run()
    snapshot = tmp_path / 'snapshot'
    export_notes(harness.store, snapshot)
    repo = tmp_path / 'distribution.git'
    git('init', '--bare', '--initial-branch=content', repo)
    commit = publish_snapshot(snapshot, repo)['commit']
    checkout = clone(repo, tmp_path / 'checkout')
    manifest, files, _ = load_snapshot(checkout)
    artifact = tmp_path / 'compiled'
    artifact.mkdir()
    (artifact / 'index.html').write_text('<html><head></head><body><article>Notes</article></body></html>')
    (artifact / 'about').mkdir()
    (artifact / 'about/snapshot.html').write_text('<html><head></head><body><article>Snapshot</article></body></html>')
    for entry in manifest['notes']:
        note = artifact / 'notes' / (entry['id'] + '.html')
        note.parent.mkdir(exist_ok=True)
        note.write_text('<html><head></head><body><article>Note</article></body></html>')
    seal_artifact(artifact, manifest, files, content_commit=commit)
    return checkout, commit, artifact, tmp_path / 'pages'


def test_fixed_commit_public_only_artifact_and_repeatability(pages):
    checkout, commit, artifact, output = pages
    result = prepare_pages(*pages)
    assert result['content_commit'] == commit and result['notes'] > 0
    assert not result['unchanged']
    assert prepare_pages(*pages)['unchanged']
    manifest, files, _ = content_snapshot(checkout, commit)
    assert result['dataset_digest'] == manifest['dataset_digest']
    for name, data in files.items():
        assert (output / 'markdown' / name).read_bytes() == data
    assert not (output / '.git').exists() and not (output / 'README.md').exists()


@pytest.mark.parametrize('damage', ['tracked', 'untracked', 'ignored', 'symlink'])
def test_dirty_or_linked_content_never_reaches_public_output(pages, damage):
    checkout, commit, artifact, output = pages
    note = next((checkout / 'notes').iterdir())
    if damage == 'tracked':
        note.write_bytes(b'human edit')
    elif damage in ('untracked', 'ignored'):
        if damage == 'ignored':
            (checkout / '.git/info/exclude').write_text('private.txt\n')
        (checkout / 'private.txt').write_text('private data')
    else:
        note.unlink(); note.symlink_to(checkout / 'manifest.json')
    with pytest.raises(ExportError):
        prepare_pages(*pages)
    assert not output.exists()


@pytest.mark.parametrize('commit', ['main', 'f' * 40, 'HEAD;echo unsafe'])
def test_unverified_commit_is_rejected(pages, commit):
    checkout, _, artifact, output = pages
    with pytest.raises(ExportError, match='content_commit'):
        prepare_pages(checkout, commit, artifact, output)
    assert not output.exists()


def test_clean_but_nonpublic_git_tree_is_rejected(pages):
    checkout, _, artifact, output = pages
    (checkout / 'private.txt').write_text('private data')
    git('add', 'private.txt', cwd=checkout)
    git('commit', '-m', 'extra private file', cwd=checkout)
    commit = git('rev-parse', 'HEAD', cwd=checkout).stdout.decode().strip()
    with pytest.raises(ExportError):
        prepare_pages(checkout, commit, artifact, output)
    assert not output.exists()


@pytest.mark.parametrize('damage', ['fixture', 'commit', 'digest', 'bytes', 'extra', 'symlink'])
def test_artifact_provenance_and_integrity_must_match(pages, damage):
    checkout, commit, artifact, output = pages
    marker = artifact / 'site-manifest.json'
    if damage in ('fixture', 'commit', 'digest'):
        data = json.loads(marker.read_bytes())
        data[{'fixture': 'fixture', 'commit': 'content_commit', 'digest': 'dataset_digest'}[damage]] = {
            'fixture': True, 'commit': 'f' * 40, 'digest': 'f' * 64}[damage]
        marker.write_text(json.dumps(data))
    elif damage == 'bytes':
        (artifact / 'index.html').write_text('changed')
    elif damage == 'extra':
        (artifact / 'private.json').write_text('private')
    else:
        (artifact / 'linked').symlink_to(checkout)
    with pytest.raises(ExportError):
        prepare_pages(*pages)
    assert not output.exists()


def test_missing_git_metadata_and_overlapping_output_are_rejected(pages, tmp_path):
    checkout, commit, artifact, _ = pages
    with pytest.raises(ExportError, match='content_checkout_required'):
        content_snapshot(tmp_path, commit)
    for output in (checkout / 'site', artifact / 'site', checkout.parent):
        with pytest.raises(ExportError, match='pages_paths_overlap'):
            prepare_pages(checkout, commit, artifact, output)


def test_deployed_version_and_served_bytes_are_verified(pages):
    import importlib.util
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread
    from techkb.site import load_artifact
    spec = importlib.util.spec_from_file_location('kaname_verify_deployment', Path(__file__).parents[1] / 'web/verify_deployment.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    checkout, commit, artifact, output = pages
    result = prepare_pages(*pages)
    marker, files = load_artifact(output)
    responses = dict(files)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            name = self.path.removeprefix('/kaname/')
            if name not in responses:
                self.send_error(404); return
            self.send_response(200); self.end_headers(); self.wfile.write(responses[name])
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    url = f'http://127.0.0.1:{server.server_port}/kaname/'
    args = (url, commit, marker['dataset_digest'], marker['artifact_digest'], result['notes'])
    try:
        assert module.verify(*args)['notes'] == result['notes']
        with pytest.raises(ValueError, match='version_mismatch'):
            module.verify(url, 'f' * 40, *args[2:])
        with pytest.raises(ValueError, match='snapshot_mismatch'):
            module.verify(*args[:-1], result['notes'] + 1)
        note = next(name for name in responses if name.startswith('markdown/notes/'))
        responses[note] = b'CDN served wrong Note bytes'
        with pytest.raises(ValueError, match='bytes_mismatch'):
            module.verify(*args)
        responses[note] = files[note]
        responses['index.html'] = b'CDN served old homepage'
        with pytest.raises(ValueError, match='bytes_mismatch'):
            module.verify(*args)
        responses['index.html'] = files['index.html']
        responses.pop('about/snapshot.html')
        from urllib.error import HTTPError
        with pytest.raises(HTTPError):
            module.verify(*args)
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
