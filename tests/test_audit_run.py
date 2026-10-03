import json
import pytest
from techkb.audit import audit_run


def saved(h):
    report = h.pipeline.run()
    return report.run_id, h.store.list('runs/')[0]


def test_compare_report_without_writes(harness):
    rid, _ = saved(harness)
    writes = list(harness.store.writes)
    result = audit_run(harness.store, rid, expected_success_before=0)
    assert result['status'] == 'success'
    assert result['report']['saved'] == 1
    assert harness.store.writes == writes
    assert 'source_url' not in json.dumps(result)


@pytest.mark.parametrize('field,value,code', [
    ('llm_calls', 31, 'invalid_llm_counts'),
    ('pending_after', 1, 'pending_mismatch'),
    ('saved', 2, 'invalid_saved_count'),
    ('status', 'failed', 'unsuccessful_report'),
    ('total_input_tokens', True, 'invalid_report'),
])
def test_report_failures(harness, field, value, code):
    rid, name = saved(harness)
    report = json.loads(harness.store.read(name))
    report[field] = value
    harness.store.data[name] = json.dumps(report).encode()
    result = audit_run(harness.store, rid, expected_success_before=0)
    assert result['status'] == 'failed'
    assert {'code': code} in result['issues']


def test_baseline_and_missing_report(harness):
    rid, name = saved(harness)
    assert {'code': 'index_delta_mismatch'} in audit_run(harness.store, rid, expected_success_before=1)['issues']
    del harness.store.data[name]
    assert audit_run(harness.store, rid)['issues'] == [{'code': 'missing_report'}]
    with pytest.raises(ValueError):
        audit_run(harness.store, '../../notes/secret')
