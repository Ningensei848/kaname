import json
import pytest

from techkb.cli import main
from techkb.config import Source
from techkb.reporting import RunReport, SOURCE_COUNTERS
from techkb.source_health import source_health
from test_batch import setup


def record(h, number, *, completed=(), failed=False, counts=None,
           kind='collection', dry=False, start=None):
    run = RunReport(run_id=f'20261001T{number:02d}0000Z-{number:08x}',
                    started_at=start or f'2026-10-01T{number:02d}:00:00+00:00',
                    source_ids=[h.source.id], source_completed_ids=list(completed),
                    record_kind=kind, dry_run=dry)
    if counts is not None:
        run.source_counts[h.source.id] = counts
    if failed:
        run.fail_recorded('fetch', h.source.id, 'https://private.example/PRIVATE', 'OSError')
    run.finish()
    h.store.write(f'runs/2026/10/{run.run_id}.json', run.to_bytes())
    return run


def test_legacy_incomplete_success_never_resets_failure_or_invents_counts(harness):
    h = harness
    record(h, 1, completed=[h.source.id])
    record(h, 2, failed=True)
    record(h, 3)  # Global success and source participation are not completion.
    before = dict(h.store.data), list(h.store.writes)
    result = source_health(h.store, [h.source])
    source = result['sources'][0]
    assert result['health'] == 'degraded' and source['health'] == 'failing'
    assert source['consecutive_failures'] == 1
    assert source['last_success_at'] == '2026-10-01T01:00:00+00:00'
    assert source['latest_run_outcome'] == 'incomplete'
    assert source['latest_run_counts'] == dict.fromkeys(SOURCE_COUNTERS)
    assert (h.store.data, h.store.writes) == before
    assert 'PRIVATE' not in json.dumps(result) and 'run_id' not in json.dumps(result)


def test_completion_resets_failures_and_dry_or_billing_runs_are_ignored(harness):
    h = harness
    record(h, 1, failed=True)
    record(h, 2, completed=[h.source.id], counts=dict.fromkeys(SOURCE_COUNTERS, 0))
    record(h, 3, failed=True, kind='batch_usage')
    record(h, 4, failed=True, dry=True)
    source = source_health(h.store, [h.source])['sources'][0]
    assert source['health'] == 'healthy' and source['consecutive_failures'] == 0
    assert source['latest_report_at'] == '2026-10-01T02:00:00+00:00'
    assert source['latest_run_counts'] == dict.fromkeys(SOURCE_COUNTERS, 0)


def test_success_rows_pending_and_standard_counts_are_per_source(harness):
    h = harness
    assert h.pipeline.run().saved == 1
    h.fetcher.pages['https://example.com/b'] = b'<article>A new different article</article>'
    h.app.llm.max_calls_per_run = 0
    assert h.pipeline.run().saved == 0
    other = Source(id='other', name='Other', enabled=False,
                   feed_url='https://other.example/feed', base_url='https://other.example/')
    result = source_health(h.store, [other, h.source])
    source, disabled = result['sources']
    assert source['source_id'] == 'example' and source['success_rows'] == 1
    assert source['pending_candidates'] == 1 and source['last_note_saved_at'] is not None
    assert source['latest_run_counts'] == dict(discovered=2, saved=0, recovered=0,
                                             batch_submitted=0, batch_saved=0)
    assert source['health'] == 'incomplete'
    assert disabled['health'] == 'disabled' and disabled['success_rows'] == 0
    assert disabled['latest_run_counts'] == dict.fromkeys(SOURCE_COUNTERS)


def test_batch_counts_submission_and_recovery_without_health_double_counting(harness):
    h = harness
    sdk = setup(h)
    first = h.pipeline.run()
    assert first.source_counts[h.source.id]['batch_submitted'] == 1
    sdk.finish()
    h.store.fail_prefix = 'notes/'
    assert h.pipeline.run().status == 'failed'
    h.store.fail_prefix = None
    recovered = h.pipeline.run()
    assert recovered.source_counts[h.source.id]['saved'] == 1
    assert recovered.source_counts[h.source.id]['recovered'] == 1
    assert recovered.source_counts[h.source.id]['batch_saved'] == 0
    source = source_health(h.store, [h.source])['sources'][0]
    assert source['success_rows'] == 1 and source['pending_candidates'] == 0
    assert source['latest_run_counts']['saved'] == 1
    again = h.pipeline.run()
    assert again.source_counts[h.source.id]['saved'] == 0
    assert again.source_counts[h.source.id]['batch_submitted'] == 0


def test_reports_are_ordered_by_instant_across_timezone_offsets(harness):
    h = harness
    record(h, 1, failed=True, start='2026-10-01T10:00:00+09:00')
    record(h, 2, completed=[h.source.id], start='2026-10-01T02:00:00+00:00')
    source = source_health(h.store, [h.source])['sources'][0]
    assert source['health'] == 'healthy' and source['consecutive_failures'] == 0
    assert source['last_success_at'] == '2026-10-01T02:00:00+00:00'


@pytest.mark.parametrize('value', [True, -1, 'PRIVATE'])
def test_invalid_counters_fail_instead_of_fabricating_health(harness, value):
    h = harness
    record(h, 1, counts={'saved': value})
    with pytest.raises(ValueError):
        source_health(h.store, [h.source])


def test_snapshot_cli_requires_no_secrets_or_fetcher_and_writes_nothing(harness, tmp_path, monkeypatch, capsys):
    h = harness
    record(h, 1, failed=True)
    for name, value in h.store.data.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(value)
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    def forbidden(*args, **kwargs):
        pytest.fail('source health must not create a network or LLM client')
    monkeypatch.setattr('techkb.cli.load_config', lambda *args: (h.app, [h.source]))
    for name in ('Fetcher', 'SourceFetcher', 'Gemini', 'GCSStore'):
        monkeypatch.setattr('techkb.cli.' + name, forbidden)
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    assert main(['source-health', '--state-dir', str(tmp_path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['sources'][0]['health'] == 'failing'
    after = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert before == after and 'PRIVATE' not in json.dumps(result)
