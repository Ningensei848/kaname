"""CLI for served Pages verification; no package installation is needed."""
import argparse
import json
import sys
from pathlib import Path


# Explicit paths also support python -I -S, without site-packages/PYTHONPATH.
WEB = Path(__file__).resolve().parent
sys.path.insert(0, str(WEB.parent / "src"))
sys.path.insert(0, str(WEB))
from kaname_web.deployment import verify


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
