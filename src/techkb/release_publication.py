"""GitHub Release transport, with drafts, fixed tags and bounded reconstruction."""
import base64
from pathlib import Path
import re
from urllib.parse import urlsplit

import httpx

from .publication.common import ExportError, json_bytes, sha256, reject_symlinks
from .publication.install import install_snapshot
from .release_bundle import (ARCHIVE, DESCRIPTOR, MAX_ARCHIVE, MAX_DEPTH, apply_bundle,
                             build_bundle, descriptor, release_tag, snapshot_digest)


class ReleaseClient:
    def __init__(self, repository, token=None, client=None):
        if not isinstance(repository, str) or not re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9_.-]*/[A-Za-z0-9_-][A-Za-z0-9_.-]*', repository):
            raise ExportError('invalid_release_repository')
        self.repository, self.token = repository, token
        self.client = client or httpx.Client(timeout=120, follow_redirects=False)
        self.prefix = 'https://api.github.com/repos/' + repository

    def close(self):
        self.client.close()

    def request(self, method, path, *, missing=False, **kwargs):
        headers = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2026-03-10'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        try:
            response = self.client.request(method, self.prefix + path, headers=headers, follow_redirects=False, **kwargs)
            if missing and response.status_code == 404:
                return None
            if response.status_code not in (200, 201):
                raise ExportError('release_api_failed')
            return response.json()
        except (httpx.HTTPError, ValueError):
            raise ExportError('release_api_failed') from None

    def get(self, tag, *, missing=False, include_draft=False):
        if not re.fullmatch(r'notes-[0-9a-f]{40}', tag):
            raise ExportError('invalid_release_tag')
        result = self.request('GET', '/releases/tags/' + tag, missing=True)
        # The tag endpoint promises published releases. Drafts are discovered
        # using the authenticated listing, then reread by numeric Release ID.
        if result is None and include_draft and self.token:
            for page in range(1, 101):
                values = self.request('GET', '/releases', params={'per_page': 100, 'page': page})
                if not isinstance(values, list):
                    raise ExportError('invalid_release_listing')
                matches = [value for value in values if value.get('tag_name') == tag]
                if len(matches) > 1:
                    raise ExportError('release_version_conflict')
                if matches:
                    release_id = matches[0].get('id')
                    if type(release_id) is not int or release_id <= 0:
                        raise ExportError('invalid_release_listing')
                    result = self.request('GET', '/releases/' + str(release_id))
                    break
                if len(values) < 100:
                    break
            else:
                raise ExportError('release_listing_limit')
        if result is None and not missing:
            raise ExportError('release_missing')
        return result

    def tag_commit(self, tag, *, missing=False):
        result = self.request('GET', '/git/ref/tags/' + tag, missing=missing)
        if result is None:
            return None
        # This publisher creates lightweight tags only, with the exact commit.
        if not isinstance(result, dict) or result.get('object', {}).get('type') != 'commit':
            raise ExportError('release_tag_mismatch')
        return result['object'].get('sha')

    def previous(self, exclude):
        for page in range(1, 101):
            values = self.request('GET', '/releases', params={'per_page': 100, 'page': page})
            if not isinstance(values, list):
                raise ExportError('invalid_release_listing')
            for value in values:
                tag = value.get('tag_name', '')
                if re.fullmatch(r'notes-[0-9a-f]{40}', tag) and tag != exclude and not value.get('draft'):
                    return tag
            if len(values) < 100:
                return None
        raise ExportError('release_listing_limit')

    def verify_content(self, commit, manifest):
        value = self.request('GET', '/contents/manifest.json', params={'ref': commit})
        try:
            if value.get('encoding') != 'base64' or value.get('size') != len(manifest):
                raise ValueError
            captured = base64.b64decode(value['content'].replace('\n', ''), validate=True)
            if captured != manifest:
                raise ValueError
        except (ValueError, TypeError, KeyError):
            raise ExportError('release_content_mismatch') from None

    def download(self, asset, limit):
        if (type(asset.get('id')) is not int or asset['id'] <= 0 or asset.get('state') != 'uploaded' or
                type(asset.get('size')) is not int or not 0 < asset['size'] <= limit):
            raise ExportError('invalid_release_asset')
        url = self.prefix + '/releases/assets/' + str(asset['id'])
        headers = {'Accept': 'application/octet-stream', 'X-GitHub-Api-Version': '2026-03-10'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        try:
            # Never forward credentials to signed storage URLs or print them.
            for _ in range(4):
                with self.client.stream('GET', url, headers=headers, follow_redirects=False) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        url = response.headers.get('location', '')
                        parts = urlsplit(url)
                        if (parts.scheme != 'https' or parts.hostname != 'release-assets.githubusercontent.com' or
                                parts.port not in (None, 443) or parts.username or parts.password):
                            raise ExportError('invalid_release_redirect')
                        headers = {'Accept': 'application/octet-stream'}
                        continue
                    if response.status_code != 200:
                        raise ExportError('release_download_failed')
                    result = bytearray()
                    for chunk in response.iter_bytes():
                        result.extend(chunk)
                        if len(result) > limit:
                            raise ExportError('release_download_limit')
                    packed = bytes(result)
                    if len(packed) != asset['size']:
                        raise ExportError('release_asset_size_mismatch')
                    digest = asset.get('digest')
                    if digest is not None and digest != 'sha256:' + sha256(packed):
                        raise ExportError('release_asset_digest_mismatch')
                    return packed
            raise ExportError('release_redirect_limit')
        except (httpx.HTTPError, ValueError):
            raise ExportError('release_download_failed') from None

    def bundle(self, tag, *, allow_draft=False):
        release = self.get(tag, include_draft=allow_draft)
        if (release.get('tag_name') != tag or release.get('prerelease') or
                release.get('draft') and not allow_draft):
            raise ExportError('release_not_published')
        assets = release.get('assets', [])
        if len(assets) != 2 or {asset.get('name') for asset in assets} != {DESCRIPTOR, ARCHIVE}:
            raise ExportError('release_assets_incomplete')
        by_name = {asset['name']: asset for asset in assets}
        value = descriptor(self.download(by_name[DESCRIPTOR], 1024 * 1024))
        if value['tag'] != tag or self.tag_commit(tag) != value['content_commit']:
            raise ExportError('release_tag_mismatch')
        packed = self.download(by_name[ARCHIVE], MAX_ARCHIVE)
        return value, packed

    def restore_files(self, tag, *, allow_draft=False):
        bundles, seen = [], set()
        for _ in range(MAX_DEPTH + 1):
            if tag in seen:
                raise ExportError('release_chain_cycle')
            seen.add(tag)
            value, packed = self.bundle(tag, allow_draft=allow_draft and not bundles)
            bundles.append((value, packed))
            if value['kind'] == 'full':
                break
            tag = value['base_tag']
        else:
            raise ExportError('release_chain_limit')
        base = None
        for value, packed in reversed(bundles):
            _, files, _ = apply_bundle(value, packed, base)
            base = value, files
        return base

    def upload(self, release, name, data):
        release_id = release.get('id')
        if type(release_id) is not int or release_id <= 0 or not self.token:
            raise ExportError('invalid_release_upload')
        url = 'https://uploads.github.com/repos/' + self.repository + '/releases/' + str(release_id) + '/assets'
        try:
            response = self.client.post(url, params={'name': name}, content=data,
                headers={'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/octet-stream',
                         'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2026-03-10'},
                follow_redirects=False)
            if response.status_code != 201:
                raise ExportError('release_upload_failed')
        except httpx.HTTPError:
            raise ExportError('release_upload_failed') from None


def publish_release(root, commit, client):
    tag = release_tag(commit)
    existing = client.get(tag, missing=True, include_draft=True)
    # Recompute target bytes before trusting an existing version or staging data.
    target, _ = build_bundle(root, commit)
    client.verify_content(commit, (Path(root) / 'manifest.json').read_bytes())
    if existing is not None and not existing.get('draft'):
        value, files = client.restore_files(tag)
        if value['snapshot_digest'] != target['snapshot_digest']:
            raise ExportError('release_version_conflict')
        return dict(status='success', tag=tag, commit=commit, dataset_digest=value['target_dataset_digest'],
                    notes=sum(name.startswith('notes/') for name in files), kind=value['kind'],
                    depth=value['depth'], unchanged=True, changed=len(value['changed']), deleted=len(value['deleted']))
    if existing is None:
        previous = client.previous(tag)
        base = None if previous is None else client.restore_files(previous)
        value, packed = build_bundle(root, commit, base)
        anchor = client.tag_commit(tag, missing=True)
        if anchor is None:
            client.request('POST', '/git/refs', json={'ref': 'refs/tags/' + tag, 'sha': commit})
        elif anchor != commit:
            raise ExportError('release_tag_mismatch')
        existing = client.request('POST', '/releases', json=dict(tag_name=tag, target_commitish=commit,
            name='Public Notes ' + commit[:12], body='Validated generated Notes. Restore using release.json and notes.zip.',
            draft=True, prerelease=False, make_latest='false', generate_release_notes=False))
    else:
        # Resume only matching staged bytes. An uploaded descriptor fixes the
        # predecessor even if another Release appeared since a partial attempt.
        assets = existing.get('assets', [])
        staged = [asset for asset in assets if asset.get('name') == DESCRIPTOR]
        if staged:
            if len(staged) != 1:
                raise ExportError('release_version_conflict')
            prior = descriptor(client.download(staged[0], 1024 * 1024))
            base = None if prior['base_tag'] is None else client.restore_files(prior['base_tag'])
        else:
            previous = client.previous(tag)
            base = None if previous is None else client.restore_files(previous)
        value, packed = build_bundle(root, commit, base)
    if (not existing.get('draft') or existing.get('tag_name') != tag or
            existing.get('prerelease') or client.tag_commit(tag) != commit):
        raise ExportError('release_version_conflict')
    desired = {DESCRIPTOR: json_bytes(value), ARCHIVE: packed}
    present = existing.get('assets', [])
    if len(present) != len({asset.get('name') for asset in present}) or any(asset.get('name') not in desired for asset in present):
        raise ExportError('release_version_conflict')
    for asset in present:
        if client.download(asset, MAX_ARCHIVE if asset['name'] == ARCHIVE else 1024 * 1024) != desired[asset['name']]:
            raise ExportError('release_version_conflict')
    names = {asset['name'] for asset in present}
    for name, data in desired.items():
        if name not in names:
            client.upload(existing, name, data)
    # Validate remote staged bytes and the entire chain BEFORE making visible.
    staged, files = client.restore_files(tag, allow_draft=True)
    if staged != value or snapshot_digest(files) != target['snapshot_digest']:
        raise ExportError('release_remote_mismatch')
    client.request('PATCH', '/releases/' + str(existing['id']), json=dict(draft=False, make_latest='false'))
    published, files = client.restore_files(tag)
    if published != value:
        raise ExportError('release_remote_mismatch')
    return dict(status='success', tag=tag, commit=commit, dataset_digest=value['target_dataset_digest'],
                notes=sum(name.startswith('notes/') for name in files), kind=value['kind'], depth=value['depth'],
                unchanged=False, changed=len(value['changed']), deleted=len(value['deleted']))


def restore_release(tag, commit, output, receipt, client):
    if tag != release_tag(commit):
        raise ExportError('release_commit_mismatch')
    root, receipt_path = Path(output).absolute(), Path(receipt).absolute()
    reject_symlinks(receipt_path)
    if root == receipt_path or receipt_path.is_relative_to(root):
        raise ExportError('release_receipt_inside_snapshot')
    value, files = client.restore_files(tag)
    data = json_bytes(value)
    # Receipt is separate from the public snapshot and never a Quartz input file.
    if receipt_path.exists() and receipt_path.read_bytes() != data:
        raise ExportError('release_receipt_conflict')
    install_snapshot(root, files)
    if not receipt_path.exists():
        with receipt_path.open('xb') as stream:
            stream.write(data)
    return dict(status='success', tag=tag, commit=commit, dataset_digest=value['target_dataset_digest'],
                notes=sum(name.startswith('notes/') for name in files), kind=value['kind'], depth=value['depth'])
