"""Version, path and byte checks shared by artifact and served Pages validation.

Standard library only: deployment verification must not import the renderer,
collection clients, YAML, BeautifulSoup or Playwright.
"""
import json
from pathlib import PurePosixPath
import re

from ._publication_common import sha256, json_bytes


def digest_matches(data, expected):
    return sha256(data) == expected


def hash_manifest(hashes):
    return sha256(json_bytes(sorted(hashes.items())))


def public_version_matches(marker, commit):
    return marker["fixture"] is False and marker["content_commit"] == commit


def snapshot_matches(marker, manifest, files, original, expected_notes=None):
    return (marker["dataset_digest"] == manifest["dataset_digest"] and
            (expected_notes is None or
             {name for name in files if name.startswith("notes/")} == expected_notes) and
            all(files.get("markdown/" + name) == data for name, data in original.items()))


def valid_site_marker(marker):
    return not (not isinstance(marker, dict) or
                set(marker) != {"schema_version", "artifact_digest", "dataset_digest", "fixture", "content_commit", "files"} or
                type(marker["schema_version"]) is not int or marker["schema_version"] != 1 or
                type(marker["fixture"]) is not bool or not digest_value(marker["dataset_digest"]) or
                (marker["content_commit"] is not None and
                 (not isinstance(marker["content_commit"], str) or not re.fullmatch(r"[0-9a-f]{40}", marker["content_commit"]))) or
                not isinstance(marker["files"], dict) or not digest_value(marker["artifact_digest"]))


def valid_deployment_version(commit, dataset, artifact):
    return not (not re.fullmatch(r'[0-9a-f]{40}', commit) or
                any(not re.fullmatch(r'[0-9a-f]{64}', d) for d in (dataset, artifact)))


def digest_value(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def artifact_path(name):
    """Finite output types; Markdown/JSON have dedicated public-only locations."""
    if not isinstance(name, str):
        return False
    pure = PurePosixPath(name)
    if (str(pure) != name or pure.is_absolute() or not pure.parts or
            any(p.startswith(".") for p in pure.parts) or re.search(r'[\\\x00-\x1f\x7f]', name)):
        return False
    if pure.suffix == ".html":
        return (name in {"index.html", "404.html", "about/snapshot.html", "tags/index.html"} or
                bool(re.fullmatch(r"notes/[0-9a-f]{64}\.html", name)) or
                bool(re.fullmatch(r"browse/(sources|categories|dates)\.html", name)) or
                bool(re.fullmatch(r"browse/(sources|categories)/[0-9a-f]{64}\.html", name)) or
                name.startswith("tags/"))
    if name in {"index.css", "prescript.js", "postscript.js", "static/contentIndex.json", "markdown/manifest.json"}:
        return True
    if re.fullmatch(r"markdown/notes/[0-9a-f]{64}\.md", name):
        return True
    return name.startswith("static/") and pure.suffix in {".woff2", ".png", ".svg", ".ico", ".txt"}


def verify_pages_bytes(get, commit, dataset, artifact, notes):
    """Validate served bytes in order using an injected, transport-independent reader."""
    marker = json.loads(get('site-manifest.json'))
    if (not public_version_matches(marker, commit) or
            marker['dataset_digest'] != dataset or marker['artifact_digest'] != artifact):
        raise ValueError('deployed_pages_version_mismatch')
    hashes = marker['files']
    computed = hash_manifest(hashes)
    if computed != artifact:
        raise ValueError('deployed_pages_manifest_mismatch')
    def checked(name):
        data = get(name)
        if not digest_matches(data, hashes[name]):
            raise ValueError('deployed_pages_bytes_mismatch')
        return data
    checked('index.html')
    checked('about/snapshot.html')
    manifest = json.loads(checked('markdown/manifest.json'))
    if manifest['dataset_digest'] != dataset or len(manifest['notes']) != notes:
        raise ValueError('deployed_pages_snapshot_mismatch')
    for entry in manifest['notes']:
        if not re.fullmatch(r'[0-9a-f]{64}', entry['id']) or entry['path'] != 'notes/' + entry['id'] + '.md':
            raise ValueError('invalid_deployed_note_path')
        if not digest_matches(checked('markdown/' + entry['path']), entry['sha256']):
            raise ValueError('deployed_pages_note_mismatch')
    if manifest['notes']:
        checked('notes/' + manifest['notes'][0]['id'] + '.html')
    return dict(status='passed', content_commit=commit, dataset_digest=dataset, artifact_digest=artifact, notes=notes)
