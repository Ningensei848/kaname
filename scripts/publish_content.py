"""Actions wrapper; no cloud/LLM clients and no raw Git error logs."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from techkb.remote_publication import publish_remote
from techkb.publication import ExportError

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--remote', required=True)
    parser.add_argument('--workspace', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(publish_remote(args.snapshot, args.remote, args.workspace)))
    except ExportError as exc:
        print(json.dumps(dict(status='failed', code=str(exc))), file=sys.stderr); sys.exit(1)
    except Exception:
        print('{"status":"failed","code":"content_publication_failed"}', file=sys.stderr); sys.exit(1)
