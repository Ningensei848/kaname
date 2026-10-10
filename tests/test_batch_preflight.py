import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from techkb.batch import preflight, ReadOnlyStore
from test_batch import setup


@pytest.fixture
def preflight_script():
    spec = importlib.util.spec_from_file_location(
        'batch_preflight', Path(__file__).parents[1] / 'scripts/batch_preflight.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preflight_ready_is_read_only_and_keeps_identifiers_private(harness):
    h = harness
    assert h.pipeline.run().saved == 1
    before, writes = dict(h.store.data), list(h.store.writes)
    result = preflight(h.store, h.app)
    assert result['status'] == 'ready'
    assert result['success_rows'] == 1 and result['active_batch_ledgers'] == 0
    assert h.store.data == before and h.store.writes == writes
    rendered = json.dumps(result)
    for forbidden in ['https://', '技術記事', 'Original text', 'note_object', 'run_id', 'daily_usd']:
        assert forbidden not in rendered


def test_active_and_unbilled_batches_block_preflight_without_polling(harness):
    h = harness
    assert h.pipeline.run().saved == 1
    h.fetcher.pages['https://example.com/new'] = b'<article>Different content</article>'
    sdk = setup(h)
    assert h.pipeline.run().batch_submitted == 1
    # Preflight receives no Gemini client and cannot GET or create a job.
    before, writes, calls = dict(h.store.data), list(h.store.writes), len(sdk.created)
    result = preflight(h.store, h.app)
    assert result['status'] == 'blocked'
    assert set(result['blockers']) == {'active_batch_ledgers', 'unbilled_batch_items'}
    assert result['active_batch_ledgers'] == result['unbilled_batch_items'] == 1
    assert h.store.data == before and h.store.writes == writes and len(sdk.created) == calls


def test_completed_failed_batch_does_not_count_as_success_or_active(harness):
    h = harness
    assert h.pipeline.run().saved == 1
    h.fetcher.pages['https://example.com/new'] = b'<article>Different content</article>'
    sdk = setup(h)
    assert h.pipeline.run().batch_submitted == 1
    h.sdk.text = '{}'
    sdk.finish()
    h.app.llm.max_calls_per_run = 0
    assert h.pipeline.run().batch_failed == 1
    result = preflight(h.store, h.app)
    assert result['status'] == 'ready'
    assert result['success_rows'] == 1
    assert result['active_batch_ledgers'] == result['unbilled_batch_items'] == 0


def test_orphan_receipt_blocks_preflight(harness):
    h = harness
    assert h.pipeline.run().saved == 1
    h.store.data['state/receipts/' + 'a' * 64 + '.json'] = b'{}'
    result = preflight(h.store, h.app)
    assert result['status'] == 'blocked'
    assert result['blockers'] == ['state_audit_failed']


def test_storage_wrapper_rejects_writes(harness):
    with pytest.raises(RuntimeError):
        ReadOnlyStore(harness.store).write('private', b'never persisted')
    assert harness.store.writes == []


@pytest.mark.parametrize('fail_read', [False, True])
def test_runner_hides_errors_and_closes_client(harness, preflight_script, monkeypatch, capsys, fail_read):
    h = harness
    assert h.pipeline.run().saved == 1
    closed = []
    h.store.client = SimpleNamespace(close=lambda: closed.append(True))
    monkeypatch.setattr(preflight_script, 'load_config', lambda *args: (h.app, [h.source]))
    monkeypatch.setattr(preflight_script, 'GCSStore', lambda _: h.store)
    if fail_read:
        def failed(*args):
            raise ValueError('PRIVATE_OBJECT_NAME AND CREDENTIAL')
        monkeypatch.setattr(h.store, 'read', failed)
    assert preflight_script.main() == (1 if fail_read else 0)
    result = json.loads(capsys.readouterr().out)
    assert result['status'] == ('failed' if fail_read else 'ready')
    assert 'PRIVATE' not in json.dumps(result)
    assert closed == [True]
