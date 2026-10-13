"""Public Release wrapper. Never prints HTTP payloads, credentials or Note text."""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from techkb.publication import ExportError
from techkb.release_publication import ReleaseClient, publish_release, restore_release


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository', default=os.environ.get('GITHUB_REPOSITORY'))
    commands = parser.add_subparsers(dest='command', required=True)
    publish = commands.add_parser('publish')
    publish.add_argument('--snapshot', required=True)
    publish.add_argument('--commit', required=True)
    restore = commands.add_parser('restore')
    restore.add_argument('--tag', required=True)
    restore.add_argument('--commit', required=True)
    restore.add_argument('--output', required=True)
    restore.add_argument('--receipt', required=True)
    args = parser.parse_args()
    client = ReleaseClient(args.repository, os.environ.get('GITHUB_TOKEN'))
    try:
        if args.command == 'publish':
            return publish_release(args.snapshot, args.commit, client)
        return restore_release(args.tag, args.commit, args.output, args.receipt, client)
    finally:
        client.close()


if __name__ == '__main__':
    try:
        print(json.dumps(main()))
    except ExportError as exc:
        print(json.dumps(dict(status='failed', code=str(exc))), file=sys.stderr)
        sys.exit(1)
    except Exception:
        print('{"status":"failed","code":"release_operation_failed"}', file=sys.stderr)
        sys.exit(1)
