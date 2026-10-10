"""Build and verify Pages from a clean, fixed public content Git checkout."""
import argparse
import json
from pathlib import Path
import sys

from build import build
from techkb.publication.git_snapshot import content_snapshot
from kaname_web.pages import prepare_pages
from techkb.publication import ExportError


def build_pages(content, commit, output):
    content_snapshot(content, commit)  # Reject private/dirty input before Quartz.
    result = build(content, fixture=False, content_commit=commit)
    return prepare_pages(content, commit, result["output"], output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--content", required=True, type=Path)
    parser.add_argument("--content-commit", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(build_pages(args.content, args.content_commit, args.output)))
    except ExportError as exc:
        print(json.dumps(dict(status="failed", code=str(exc))), file=sys.stderr); sys.exit(1)
    except Exception:
        print('{"status":"failed","code":"pages_build_failed"}', file=sys.stderr); sys.exit(1)
