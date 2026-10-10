"""Read-only, public-safe baseline for the separately approved Batch acceptance."""
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from techkb.batch import preflight
from techkb.config import load_config
from techkb.storage import GCSStore


def main():
    store = None
    # Exception messages and vendor logs can contain object names or credentials.
    previous_disable = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        app, _ = load_config('config/app.yaml', 'config/sources.yaml')
        store = GCSStore(app.storage.bucket)
        result = preflight(store, app)
        print(json.dumps(result))
        return 0 if result['status'] == 'ready' else 1
    except Exception as exc:
        print(json.dumps(dict(status='failed', error_type=type(exc).__name__)))
        return 1
    finally:
        try:
            if store is not None:
                store.client.close()
        finally:
            logging.disable(previous_disable)


if __name__ == '__main__':
    sys.exit(main())
