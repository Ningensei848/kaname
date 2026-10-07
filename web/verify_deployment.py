"""Verify the served Pages version and original Note bytes; stdlib only."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


# The checkout includes this stdlib-only module; no package install is needed.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from techkb._web_validation import sha256 as digest, valid_deployment_version, verify_pages_bytes


def verify(url, commit, dataset, artifact, notes):
    address = urlsplit(url)
    if (address.scheme != 'https' and not (address.scheme == 'http' and address.hostname == '127.0.0.1')) or address.username or address.password:
        raise ValueError('invalid_pages_url')
    if not valid_deployment_version(commit, dataset, artifact):
        raise ValueError('invalid_pages_version')
    def get(name):
        request = Request(url.rstrip('/') + '/' + name, headers={'Cache-Control': 'no-cache'})
        with urlopen(request, timeout=20) as response:
            data = response.read(20 * 1024 * 1024 + 1)
            if len(data) > 20 * 1024 * 1024:
                raise ValueError('oversized_pages_response')
            return data
    return verify_pages_bytes(get, commit, dataset, artifact, notes)


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
