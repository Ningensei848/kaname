"""Targeted image repair; no Gemini client, collection or publication."""
import argparse
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from techkb.browser_fetcher import SourceFetcher
from techkb.config import load_config
from techkb.fetcher import Fetcher
from techkb.image_refresh import load_plan, repair_images
from techkb.storage import GCSStore


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--output', required=True, help='new directory for validated preview')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args(argv)
    store = fetcher = None
    previous_disable = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        plan = load_plan(args.plan)
        app, sources = load_config('config/app.yaml', 'config/sources.yaml')
        store = GCSStore(app.storage.bucket)
        fetcher = SourceFetcher(Fetcher(app.http))
        result = repair_images(store, fetcher, sources, app, plan, apply=args.apply, output=args.output)
        if Path(args.output).is_dir():
            (Path(args.output) / 'result.json').write_text(json.dumps(result))
        print(json.dumps(result))
        return int(result['status'] != 'success')
    except Exception as exc:
        print(json.dumps(dict(status='failed', error_type=type(exc).__name__)))
        return 1
    finally:
        try:
            if fetcher is not None:
                fetcher.close()
        finally:
            try:
                if store is not None:
                    store.client.close()
            finally:
                logging.disable(previous_disable)


if __name__ == '__main__':
    sys.exit(main())
