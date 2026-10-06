"""Verify the served Pages version and original Note bytes; stdlib only."""
import argparse
import hashlib
import json
import re
import sys
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify(url, commit, dataset, artifact, notes):
    address = urlsplit(url)
    if (address.scheme != 'https' and not (address.scheme == 'http' and address.hostname == '127.0.0.1')) or address.username or address.password:
        raise ValueError('invalid_pages_url')
    if not re.fullmatch(r'[0-9a-f]{40}', commit) or any(not re.fullmatch(r'[0-9a-f]{64}', d) for d in (dataset, artifact)):
        raise ValueError('invalid_pages_version')
    def get(name):
        request = Request(url.rstrip('/') + '/' + name, headers={'Cache-Control': 'no-cache'})
        with urlopen(request, timeout=20) as response:
            data = response.read(20 * 1024 * 1024 + 1)
            if len(data) > 20 * 1024 * 1024:
                raise ValueError('oversized_pages_response')
            return data
    marker = json.loads(get('site-manifest.json'))
    if (marker['fixture'] is not False or marker['content_commit'] != commit or
            marker['dataset_digest'] != dataset or marker['artifact_digest'] != artifact):
        raise ValueError('deployed_pages_version_mismatch')
    hashes = marker['files']
    computed = digest((json.dumps(sorted(hashes.items()), ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode())
    if computed != artifact:
        raise ValueError('deployed_pages_manifest_mismatch')
    def checked(name):
        data = get(name)
        if digest(data) != hashes[name]:
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
        if digest(checked('markdown/' + entry['path'])) != entry['sha256']:
            raise ValueError('deployed_pages_note_mismatch')
    if manifest['notes']:
        checked('notes/' + manifest['notes'][0]['id'] + '.html')
    return dict(status='passed', content_commit=commit, dataset_digest=dataset, artifact_digest=artifact, notes=notes)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--content-commit', required=True)
    parser.add_argument('--dataset-digest', required=True)
    parser.add_argument('--artifact-digest', required=True)
    parser.add_argument('--notes', required=True, type=int)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.url, args.content_commit, args.dataset_digest, args.artifact_digest, args.notes)))
    except Exception:
        print('{"status":"failed","code":"deployed_pages_verification_failed"}', file=sys.stderr); sys.exit(1)
