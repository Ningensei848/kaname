"""Private, durable standard usage checkpoint, keyed by original run ID.

Written before each paid call and after usage capture, before any Note receipt.
An in-flight reservation denotes unknown billing, never a known zero charge.
"""
import json
import re

FIELDS = ('run_id', 'started_at', 'llm_model', 'llm_mode', 'token_price', 'llm_calls',
          'llm_http_attempts', 'llm_usage_unavailable', 'total_input_tokens',
          'total_output_tokens', 'total_thinking_tokens')


def checkpoint(store, report, pending):
    record = {key: getattr(report, key) for key in FIELDS}
    record.update(schema_version=1, pending=pending)
    store.write('state/standard-usage/' + report.run_id + '.json',
                json.dumps(record, ensure_ascii=False).encode(), 'application/json')


def has_usage_record(store, run_id):
    if not isinstance(run_id, str) or not re.fullmatch(r'\d{8}T\d{6}Z-[0-9a-f]{8}', run_id):
        return False
    return (store.read('state/standard-usage/' + run_id + '.json') is not None or
            store.read('runs/' + run_id[:4] + '/' + run_id[4:6] + '/' + run_id + '.json') is not None)
