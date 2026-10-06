"""Read-only, ordered run history with duplicate identity checks."""
from datetime import datetime
import json
import re


def history(store):
    reports = {}
    for name in store.list('runs/'):
        if not name.endswith('.json'):
            continue
        raw = store.read(name)
        if raw is None:
            raise ValueError('run disappeared')
        report = json.loads(raw)
        run_id = report['run_id']
        if not re.fullmatch(r'\d{8}T\d{6}Z-[0-9a-f]{8}',run_id):
            raise ValueError('invalid run identifier')
        datetime.fromisoformat(report['started_at'])
        if run_id in reports and reports[run_id] != report:
            raise ValueError('conflicting duplicate report')
        reports[run_id]=report
    return sorted(reports.values(), key=lambda r: (r['started_at'],r['run_id']))
