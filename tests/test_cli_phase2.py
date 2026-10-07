import json
from types import SimpleNamespace

import pytest

from techkb import cli
from techkb.cli import main
from test_batch import setup as setup_batch


def test_llm_override_cannot_increase_configured_limit():
    assert main(['run','--max-calls','31'])==1
    assert main(['validate-config','--llm-mode','batch'])==1
    assert main(['sync','--max-calls','0'])==1


def test_readonly_operational_cli_without_credentials(tmp_path,capsys):
    snapshot=tmp_path/'state'; snapshot.mkdir()
    for command in ['cost-report','notify','batch-status']:
        assert main([command,'--state-dir',str(snapshot)])==0
    assert '"jobs": []' in capsys.readouterr().out


@pytest.mark.parametrize('command', [
    'validate-config', 'audit-run', 'cost-report', 'notify', 'batch-status', 'sync',
])
def test_remaining_offline_commands_need_no_network_clients(command, harness, tmp_path, monkeypatch, capsys):
    report = harness.pipeline.run()
    snapshot = tmp_path / 'state'
    snapshot.mkdir()
    for name, data in harness.store.data.items():
        path = snapshot / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.setattr(cli, 'load_config', lambda *args: (harness.app, [harness.source]))
    def forbidden(*args, **kwargs):
        pytest.fail('offline command constructed an unnecessary client')
    for name in ('GCSStore', 'Fetcher', 'SourceFetcher', 'Gemini', 'Converter'):
        monkeypatch.setattr(cli, name, forbidden)
    args = [command]
    if command != 'validate-config':
        args += ['--state-dir', str(snapshot)]
    if command == 'audit-run':
        args += ['--run-id', report.run_id, '--expected-success-before', '0']
    elif command == 'sync':
        args += ['--vault', str(tmp_path / 'vault'), '--dry-run']
    assert main(args) == 0
    output = capsys.readouterr().out
    if command == 'validate-config':
        assert output == f'Configuration valid: 1 sources; model={harness.app.llm.model}\n'
    else:
        assert json.loads(output)['status'] == 'success'
    assert len(harness.sdk.calls) == 1  # fixture creation only


def test_lifecycle_cli_uses_only_bucket_and_keeps_apply_explicit(harness, monkeypatch, capsys):
    patches = []
    bucket = SimpleNamespace(lifecycle_rules=[], metageneration=7,
                             patch=lambda **kwargs: patches.append(kwargs))
    monkeypatch.setattr(cli, 'load_config', lambda *args: (harness.app, [harness.source]))
    monkeypatch.setattr(cli, 'GCSStore', lambda _: SimpleNamespace(bucket=bucket))
    def forbidden(*args, **kwargs):
        pytest.fail('lifecycle command constructed a processing client')
    for name in ('Fetcher', 'SourceFetcher', 'Gemini', 'Converter'):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    harness.source.raw_retention_days = 14
    assert main(['raw-lifecycle']) == 0
    assert not json.loads(capsys.readouterr().out)['applied'] and patches == []
    assert main(['raw-lifecycle', '--apply']) == 0
    assert json.loads(capsys.readouterr().out)['applied']
    assert patches == [{'if_metageneration_match': 7}]


@pytest.mark.parametrize('mismatch', [False, True])
def test_bind_cli_only_gets_reserved_batch_and_closes_llm(mismatch, harness, monkeypatch, capsys):
    sdk = setup_batch(harness)
    sdk.timeout = True
    assert harness.pipeline.run().status == 'failed'
    path = harness.store.list('state/batches/')[0]
    batch_id = json.loads(harness.store.read(path))['id']
    calls = []
    original_get = sdk.get
    def get(name):
        calls.append(('get', name))
        return original_get(name)
    sdk.get = get
    if mismatch:
        sdk.jobs['batches/1'].display_name = 'different reservation'
    harness.app.prompt_file = 'missing-prompt-not-needed-for-bind'
    monkeypatch.setenv('GEMINI_API_KEY', 'fixture-only')
    monkeypatch.setattr(cli, 'load_config', lambda *args: (harness.app, [harness.source]))
    monkeypatch.setattr(cli, 'GCSStore', lambda _: harness.store)
    monkeypatch.setattr(cli, 'Gemini', lambda *args: SimpleNamespace(client=sdk, close=lambda: calls.append('close')))
    def forbidden(*args, **kwargs):
        pytest.fail('binding must not fetch, convert or submit new work')
    for name in ('Fetcher', 'SourceFetcher', 'Converter'):
        monkeypatch.setattr(cli, name, forbidden)
    before = dict(harness.store.data)
    assert main(['batch-bind', '--batch-id', batch_id, '--job-name', 'batches/1']) == int(mismatch)
    assert calls == [('get', 'batches/1'), 'close']
    assert len(sdk.created) == 1 and not harness.sdk.calls
    if mismatch:
        assert harness.store.data == before and capsys.readouterr().out == ''
    else:
        assert capsys.readouterr().out == '{"status": "success", "bound": true}\n'
        assert json.loads(harness.store.read(path))['name'] == 'batches/1'


@pytest.mark.parametrize('arguments', [
    ['run', '--max-calls', '31'],
    ['validate-config', '--llm-mode', 'batch'],
    ['dry-run', '--max-calls', '-1'],
    ['audit-state', '--apply'],
    ['audit-run', '--vault', 'vault'],
    ['refresh-metadata', '--state-dir', 'state', '--apply'],
    ['sync', '--run-id', 'saved-run'],
    ['cost-report', '--remote'],
    ['notify', '--llm-mode', 'standard'],
    ['raw-lifecycle', '--state-dir', 'state'],
    ['batch-status', '--job-name', 'batches/1'],
    ['batch-bind'],
    ['batch-inspect', '--batch-id', '../../escape'],
    ['export-notes'],
    ['publish-notes', '--public-snapshot', 'snapshot'],
])
def test_command_argument_errors_precede_clients(arguments, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('invalid arguments must be rejected before clients are constructed')
    for name in ('GCSStore', 'Fetcher', 'SourceFetcher', 'Gemini', 'Converter'):
        monkeypatch.setattr(cli, name, forbidden)
    assert main(arguments) == 1


@pytest.mark.parametrize('command,extra,clients', [
    ('run', [], ['http', 'gemini']),
    ('validate-config', [], []),
    ('dry-run', [], ['http']),
    ('audit-state', [], []),
    ('audit-run', ['--run-id', '20261007T000000Z-0123abcd'], []),
    ('refresh-metadata', [], ['http']),
    ('sync', ['--vault', 'unused-vault'], []),
    ('cost-report', [], []),
    ('notify', [], []),
    ('raw-lifecycle', [], []),
    ('batch-status', [], []),
    ('batch-bind', ['--batch-id', '20261007T000000Z-0123abcd', '--job-name', 'batches/1'], ['gemini']),
    ('batch-inspect', ['--batch-id', '20261007T000000Z-0123abcd', '--remote'], ['gemini']),
    ('export-notes', ['--output', 'unused-output'], []),
    ('publish-notes', ['--public-snapshot', 'missing-public-snapshot', '--distribution-repo', 'unused-repo'], []),
])
def test_command_failures_close_only_required_clients(command, extra, clients, harness, tmp_path, monkeypatch, capsys, caplog):
    def fail(*args, **kwargs):
        raise OSError('PRIVATE_CREDENTIAL_OR_CONTENT')
    harness.store.read = harness.store.list = fail
    class BrokenBucket:
        @property
        def lifecycle_rules(self):
            return fail()
    harness.store.bucket = BrokenBucket()
    if command == 'validate-config':
        harness.app.prompt_file = 'missing-prompt'
    constructed, closed = [], []
    def client(name):
        constructed.append(name)
        return SimpleNamespace(client=SimpleNamespace(batches=SimpleNamespace(get=fail)),
                               close=lambda: closed.append(name))
    monkeypatch.setattr(cli, 'load_config', lambda *args: (harness.app, [harness.source]))
    monkeypatch.setattr(cli, 'GCSStore', lambda _: harness.store)
    monkeypatch.setattr(cli, 'Fetcher', lambda _: client('http'))
    monkeypatch.setattr(cli, 'SourceFetcher', lambda http: http)
    monkeypatch.setattr(cli, 'Gemini', lambda *args: client('gemini'))
    monkeypatch.setenv('GEMINI_API_KEY', 'fixture-only')
    arguments = [str(tmp_path / value) if value.startswith(('unused-', 'missing-public-')) else value
                 for value in extra]
    assert main([command, *arguments]) == 1
    assert constructed == clients and closed == clients
    assert 'PRIVATE_CREDENTIAL_OR_CONTENT' not in capsys.readouterr().out + caplog.text


def test_source_adapter_failure_closes_its_http_client(harness, monkeypatch):
    calls = []
    monkeypatch.setattr(cli, 'load_config', lambda *args: (harness.app, [harness.source]))
    monkeypatch.setattr(cli, 'GCSStore', lambda _: harness.store)
    monkeypatch.setattr(cli, 'Fetcher', lambda _: SimpleNamespace(close=lambda: calls.append('close')))
    def fail_adapter(http):
        raise RuntimeError('adapter startup failure')
    monkeypatch.setattr(cli, 'SourceFetcher', fail_adapter)
    assert main(['dry-run']) == 1 and calls == ['close']


@pytest.mark.parametrize('command', ['run', 'dry-run'])
def test_collection_failed_report_returns_one_and_closes_clients(command, harness, monkeypatch):
    calls = []
    harness.fetcher.pages['https://example.com/a'] = OSError('article fetch failed')
    harness.fetcher.close = lambda: calls.append('http')
    monkeypatch.setattr(harness.gemini, 'close', lambda: calls.append('gemini'))
    monkeypatch.setattr(cli, 'load_config', lambda *args: (harness.app, [harness.source]))
    monkeypatch.setattr(cli, 'GCSStore', lambda _: harness.store)
    monkeypatch.setattr(cli, 'Fetcher', lambda _: harness.fetcher)
    monkeypatch.setattr(cli, 'Gemini', lambda *args: harness.gemini)
    if command == 'run':
        monkeypatch.setenv('GEMINI_API_KEY', 'fixture-only')
    else:
        monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    assert main([command]) == 1
    assert calls == (['http', 'gemini'] if command == 'run' else ['http'])
    assert not harness.sdk.calls
    if command == 'run':
        reports = [json.loads(harness.store.read(name)) for name in harness.store.list('runs/')]
        assert len(reports) == 1 and reports[0]['status'] == 'failed'
        assert reports[0]['failures'][0]['stage'] == 'fetch'
    else:
        assert harness.store.writes == []


def test_http_close_failure_still_closes_llm(harness, monkeypatch):
    calls = []
    def close_http():
        calls.append('http')
        raise OSError('close failed')
    def fail_pipeline(*args):
        raise ValueError('pipeline startup failure')
    monkeypatch.setattr(cli, 'load_config', lambda *args: (harness.app, [harness.source]))
    monkeypatch.setattr(cli, 'GCSStore', lambda _: harness.store)
    monkeypatch.setattr(cli, 'Fetcher', lambda _: SimpleNamespace(close=close_http))
    monkeypatch.setattr(cli, 'SourceFetcher', lambda http: http)
    monkeypatch.setattr(cli, 'Gemini', lambda *args: SimpleNamespace(close=lambda: calls.append('gemini')))
    monkeypatch.setattr(cli, 'Pipeline', fail_pipeline)
    monkeypatch.setenv('GEMINI_API_KEY', 'fixture-only')
    with pytest.raises(OSError, match='close failed'):
        main(['run'])
    assert calls == ['http', 'gemini']


@pytest.mark.parametrize('arguments', [[], ['unknown-command'], ['run', '--max-calls', 'not-an-int']])
def test_parser_errors_keep_exit_two(arguments):
    with pytest.raises(SystemExit) as exc:
        main(arguments)
    assert exc.value.code == 2
