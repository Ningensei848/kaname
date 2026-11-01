"""Read-only source health from explicit completion, failures and saved state."""
from collections import Counter
from datetime import datetime, timezone

from .reporting import SOURCE_COUNTERS
from .run_history import history
from .state import State


def _instant(value):
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is None:
        raise ValueError('source health timestamp must have a timezone')
    return stamp.astimezone(timezone.utc)


def source_health(store, sources):
    state = State(store)
    pending = Counter(candidate.source_id for candidate in state.pending())
    success = Counter()
    last_saved = {}
    for row in state.rows:
        if row['status'] == 'success':
            sid = row['source_id']
            success[sid] += 1
            stamp = _instant(row['processed_at'])
            if sid not in last_saved or stamp > last_saved[sid]:
                last_saved[sid] = stamp
    reports = [run for run in history(store)
               if not run.get('dry_run') and run.get('record_kind', 'collection') == 'collection']
    reports.sort(key=lambda run: (_instant(run['started_at']), run['run_id']))
    results = []
    for source in sorted(sources, key=lambda source: source.id):
        sid = source.id
        streak = 0
        last_success = last_failure = latest = outcome = None
        counts = dict.fromkeys(SOURCE_COUNTERS)
        for run in reports:
            failed = {failure['source_id'] for failure in run['failures']}
            completed = set(run.get('source_completed_ids', []))
            source_counts = run.get('source_counts', {}).get(sid)
            if sid not in {*run.get('source_ids', []), *failed, *completed} and source_counts is None:
                continue
            latest = _instant(run['started_at']).isoformat()
            counts = dict.fromkeys(SOURCE_COUNTERS)
            if source_counts is not None:
                if not isinstance(source_counts, dict):
                    raise ValueError('invalid source counts')
                for key in SOURCE_COUNTERS:
                    value = source_counts.get(key)
                    if value is not None and (type(value) is not int or value < 0):
                        raise ValueError('invalid source count')
                    counts[key] = value
            if sid in failed:
                streak += 1
                last_failure = latest
                outcome = 'failed'
            elif sid in completed:
                streak = 0
                last_success = latest
                outcome = 'completed'
            else:
                # Participation or a global success cannot establish recovery.
                outcome = 'incomplete'
        if not source.enabled:
            health = 'disabled'
        elif streak:
            health = 'failing'
        elif last_success is None:
            health = 'unverified'
        elif outcome == 'incomplete':
            health = 'incomplete'
        else:
            health = 'healthy'
        results.append(dict(source_id=sid, enabled=source.enabled, health=health,
                            last_success_at=last_success, last_failure_at=last_failure,
                            consecutive_failures=streak, latest_report_at=latest,
                            latest_run_outcome=outcome, latest_run_counts=counts,
                            success_rows=success[sid], pending_candidates=pending[sid],
                            last_note_saved_at=last_saved[sid].isoformat() if sid in last_saved else None))
    active = {result['health'] for result in results if result['enabled']}
    overall = ('disabled' if not active else 'degraded' if active & {'failing', 'incomplete'}
               else 'unverified' if 'unverified' in active else 'healthy')
    return dict(status='success', health=overall, sources=results)
