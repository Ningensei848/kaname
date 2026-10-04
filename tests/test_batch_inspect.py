import json
from types import SimpleNamespace

import pytest

from techkb.batch import inspect_batch
from techkb.cli import main
from test_batch import setup


def prepared(h):
    sdk = setup(h)
    h.pipeline.run()
    name = h.store.list('state/batches/')[0]
    return sdk, json.loads(h.store.read(name))['id'], name


def test_inspect_complete_ledger_without_clients_or_writes(harness):
    h = harness
    sdk, batch_id, name = prepared(h)
    h.sdk.text = '{}'
    sdk.finish()
    h.app.llm.max_calls_per_run = 0
    h.pipeline.run()
    before = dict(h.store.data)
    writes = list(h.store.writes)
    result = inspect_batch(h.store, batch_id)
    assert result['ledger_status'] == 'complete' and result['recorded_errors'] == ['ValidationError']
    assert result['remote_inspected'] is False
    assert h.store.data == before and h.store.writes == writes
    assert 'candidate' not in json.dumps(result) and 'Original text' not in json.dumps(result)


def test_remote_inspection_only_gets_existing_job_and_keeps_data_private(harness):
    h = harness
    sdk, batch_id, name = prepared(h)
    h.sdk.text = '{"PRIVATE_FIELD": "PRIVATE_VALUE"}'
    sdk.finish()
    calls = []
    def get(*, name):
        calls.append(name)
        return sdk.jobs[name]
    client = SimpleNamespace(batches=SimpleNamespace(get=get))
    before = dict(h.store.data)
    writes = list(h.store.writes)
    result = inspect_batch(h.store, batch_id, client)
    assert calls == ['batches/1']
    outcome = result['remote_outcomes'][0]
    assert outcome['error_type'] == 'ValidationError'
    assert {'field': '$', 'code': 'extra_forbidden'} in outcome['diagnostics']['validation_errors']
    rendered = json.dumps(result)
    for forbidden in ['PRIVATE', 'Original text', 'https://example.com', 'batches/1']:
        assert forbidden not in rendered
    assert h.store.data == before and h.store.writes == writes


def test_waiting_job_is_not_reported_as_missing_response(harness):
    h = harness
    sdk, batch_id, _ = prepared(h)
    result = inspect_batch(h.store, batch_id, sdk)
    assert result['remote_state'] == 'JOB_STATE_PENDING'
    assert result['remote_outcomes'] == []


def test_remote_inspection_rejects_duplicate_keys_without_writes(harness):
    h = harness
    sdk, batch_id, _ = prepared(h)
    sdk.finish()
    sdk.jobs['batches/1'].dest.inlined_responses *= 2
    before = dict(h.store.data)
    with pytest.raises(ValueError):
        inspect_batch(h.store, batch_id, sdk)
    assert h.store.data == before


def test_snapshot_cli_does_not_construct_network_clients(harness, tmp_path, monkeypatch, capsys):
    h = harness
    _, batch_id, name = prepared(h)
    path = tmp_path / name
    path.parent.mkdir(parents=True)
    path.write_bytes(h.store.read(name))
    def forbidden(*args, **kwargs):
        pytest.fail('ledger inspection must not construct network clients')
    monkeypatch.setattr('techkb.cli.GCSStore', forbidden)
    monkeypatch.setattr('techkb.cli.Gemini', forbidden)
    monkeypatch.setattr('techkb.cli.Fetcher', forbidden)
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    assert main(['batch-inspect', '--batch-id', batch_id, '--state-dir', str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)['items'] == 1


def test_remote_cli_uses_only_get_and_closes_client(harness, monkeypatch, capsys):
    h = harness
    sdk, batch_id, _ = prepared(h)
    sdk.finish()
    calls = []
    def get(*, name):
        calls.append(name)
        return sdk.jobs[name]
    def forbidden(*args, **kwargs):
        pytest.fail('remote inspection must not fetch articles or submit work')
    client = SimpleNamespace(batches=SimpleNamespace(get=get))
    monkeypatch.setattr('techkb.cli.GCSStore', lambda _: h.store)
    monkeypatch.setattr('techkb.cli.Gemini', lambda *args: SimpleNamespace(client=client, close=lambda: calls.append('close')))
    monkeypatch.setattr('techkb.cli.Fetcher', forbidden)
    monkeypatch.setattr('techkb.cli.Converter', forbidden)
    monkeypatch.setenv('GEMINI_API_KEY', 'fixture-only')
    before = dict(h.store.data)
    assert main(['batch-inspect', '--batch-id', batch_id, '--remote']) == 0
    assert json.loads(capsys.readouterr().out)['remote_outcomes'][0]['error_type'] is None
    assert calls == ['batches/1', 'close']
    assert h.store.data == before


@pytest.mark.parametrize('arguments', [
    ['batch-inspect'], ['batch-inspect', '--batch-id', '../../escape'],
    ['batch-inspect', '--job-name', 'batches/x'], ['batch-status', '--remote'],
    ['run', '--batch-id', '20261004T001622Z-e22604f8'],
])
def test_invalid_cli_combinations_fail_before_network(arguments, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('invalid inspection arguments must fail before network')
    monkeypatch.setattr('techkb.cli.GCSStore', forbidden)
    assert main(arguments) == 1
