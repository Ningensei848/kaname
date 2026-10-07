"""Read-only, public-safe baseline for the separately approved Batch acceptance."""
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from techkb.audit import audit_state
from techkb.batch import BatchManager
from techkb.config import load_config
from techkb.costs import cost_report
from techkb.reporting import now
from techkb.storage import GCSStore


class ReadOnlyStore:
    def __init__(self, store):
        self._store = store

    def list(self, prefix):
        return self._store.list(prefix)

    def read(self, name):
        return self._store.read(name)

    def write(self, *args, **kwargs):
        raise RuntimeError('Batch preflight is read-only')


def preflight(store, app):
    store = ReadOnlyStore(store)
    audit = audit_state(store)
    batches = BatchManager(store, None)
    costs = cost_report(store, app)
    blockers = []
    if audit['status'] != 'success':
        blockers.append('state_audit_failed')
    if batches.jobs:
        blockers.append('active_batch_ledgers')
    if costs['pending_batch_items']:
        blockers.append('unbilled_batch_items')
    if costs['incomplete_standard_runs']:
        blockers.append('incomplete_standard_usage')
    # Existing unknown usage remains visible; it is never labelled reconciled.
    return dict(status='blocked' if blockers else 'ready', checked_at=now(),
                audit_status=audit['status'], audit_issues=len(audit['issues']),
                success_rows=audit['success_rows'], pending=audit['pending'],
                active_batch_ledgers=len(batches.jobs),
                unbilled_batch_items=costs['pending_batch_items'],
                incomplete_standard_runs=costs['incomplete_standard_runs'],
                uncertain_runs=costs['uncertain_runs'], blockers=blockers)


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
