import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from techkb.audit import audit_state
from techkb.browser_fetcher import SourceFetcher
from techkb.image_refresh import ImageRepairPlan, original_bytes, repair_images
from techkb.publication import export_notes
from techkb.publication.common import sha256
from techkb.publication.snapshot import snapshot_files
from techkb.state import State


@pytest.fixture
def repair(harness):
    h = harness
    raw = b'''<article><p>Original text</p>
        <figure><img src="/first.png" alt="First_plot"><figcaption>First result.</figcaption></figure>
        <figure><img src="/second.png" alt="Second_plot"><figcaption>Second result.</figcaption></figure>
        </article>'''
    h.fetcher.pages['https://example.com/a'] = raw
    assert h.pipeline.run().saved == 1
    row = State(h.store).rows[0]
    note = h.store.read(row['note_object'])
    files, _ = snapshot_files(h.store, categories=h.app.categories)
    note_id = json.loads(files['manifest.json'])['notes'][0]['id']
    plan = ImageRepairPlan(schema_version=1, note_id=note_id,
                           expected_note_sha256=sha256(note), source_markdown_sha256=row['content_sha256'],
                           images=[dict(url='https://example.com/first.png', after='summary'),
                                   dict(url='https://example.com/second.png', after='key_point_1')])
    return SimpleNamespace(h=h, plan=plan, row=row, note=note, fetcher=SourceFetcher(h.fetcher))


def run(repair, **kwargs):
    h = repair.h
    return repair_images(h.store, repair.fetcher, [h.source], h.app, repair.plan, **kwargs)


def test_preview_is_read_only_and_preserves_every_original_byte(repair, tmp_path):
    h = repair.h
    before, writes = dict(h.store.data), list(h.store.writes)
    output = tmp_path / 'preview'
    result = run(repair, output=output)
    assert result['status'] == 'success' and result['planned'] == 1 and result['updated'] == 0
    assert h.store.data == before and h.store.writes == writes
    preview = (output / f'{repair.plan.note_id}.md').read_bytes()
    assert original_bytes(preview) == repair.note
    assert result['after_sha256'] == sha256(preview)
    assert len(yaml.safe_load(preview.decode().split('---', 2)[1])['article_images']) == 2
    assert len(h.sdk.calls) == 1  # only fixture creation


def test_apply_changes_only_note_and_receipt_and_preserves_public_id_and_billing(repair, tmp_path):
    h = repair.h
    before = dict(h.store.data)
    h.store.writes.clear()
    result = run(repair, apply=True)
    assert result['status'] == 'success' and result['updated'] == 1
    receipt_name = f"state/receipts/{repair.row['content_sha256']}.json"
    assert h.store.writes == [receipt_name, repair.row['note_object']]
    for name, data in before.items():
        if name not in h.store.writes:
            assert h.store.read(name) == data
    receipt = json.loads(h.store.read(receipt_name))
    assert receipt['row'] == json.loads(before[receipt_name])['row']
    assert receipt['usage_run_id'] == json.loads(before[receipt_name])['usage_run_id']
    assert receipt['note'].encode() == h.store.read(repair.row['note_object'])
    assert original_bytes(receipt['note'].encode()) == repair.note
    assert audit_state(h.store)['status'] == 'success'
    export_notes(h.store, tmp_path / 'export')
    entry = json.loads((tmp_path / 'export/manifest.json').read_bytes())['notes'][0]
    assert entry['id'] == repair.plan.note_id and entry['sha256'] == result['after_sha256']
    assert entry['processed_at'] == repair.row['processed_at']
    h.store.writes.clear()
    h.fetcher.pages['https://example.com/a'] = RuntimeError('must not fetch again')
    repeated = run(repair, apply=True)
    assert repeated['status'] == 'success' and repeated['unchanged'] == 1
    assert h.store.writes == [] and len(h.sdk.calls) == 1


@pytest.mark.parametrize('prefix', ['state/receipts/', 'notes/'])
def test_failed_pair_update_resumes_without_fetching_or_paid_work(repair, prefix):
    h = repair.h
    before = dict(h.store.data)
    h.store.fail_prefix = prefix
    result = run(repair, apply=True)
    assert result['status'] == 'failed' and result['updated'] == 0
    assert h.store.read(repair.row['note_object']) == repair.note
    if prefix == 'state/receipts/':
        assert h.store.data == before
    else:
        assert audit_state(h.store)['status'] == 'failed'
        h.fetcher.pages['https://example.com/a'] = RuntimeError('resume must not re-fetch')
    h.store.fail_prefix = None
    recovered = run(repair, apply=True)
    assert recovered['status'] == 'success' and recovered['updated'] == 1
    assert audit_state(h.store)['status'] == 'success'
    assert len(h.sdk.calls) == 1


@pytest.mark.parametrize('change', ['source', 'canonical', 'note', 'receipt', 'disabled', 'image'])
def test_changed_inputs_are_rejected_before_any_write(repair, change):
    h = repair.h
    if change == 'source':
        h.fetcher.pages['https://example.com/a'] = h.fetcher.pages['https://example.com/a'].replace(b'Original', b'Changed')
    elif change == 'canonical':
        h.fetcher.pages['https://example.com/a'] = b'<link rel="canonical" href="https://example.com/b">' + h.fetcher.pages['https://example.com/a']
    elif change == 'note':
        h.store.data[repair.row['note_object']] = repair.note.replace('要点'.encode(), '別の要点'.encode())
    elif change == 'receipt':
        h.store.data[f"state/receipts/{repair.row['content_sha256']}.json"] = b'{}'
    elif change == 'disabled':
        h.source.enabled = False
    else:
        repair.plan.images[0].url = 'https://example.com/unlisted.png'
    before, writes = dict(h.store.data), list(h.store.writes)
    result = run(repair, apply=True)
    assert result['status'] == 'failed'
    assert h.store.data == before and h.store.writes == writes
    assert len(h.sdk.calls) == 1


def test_latest_public_revision_is_selected_instead_of_stale_plan(repair, monkeypatch):
    h = repair.h
    h.fetcher.pages['https://example.com/a'] = b'<article>New revision</article>'
    monkeypatch.setattr('techkb.pipeline.now', lambda: '2030-01-01T00:00:00+00:00')
    assert h.pipeline.run().saved == 1
    before, writes = dict(h.store.data), list(h.store.writes)
    assert run(repair, apply=True)['status'] == 'failed'
    assert h.store.data == before and h.store.writes == writes


def test_concurrent_note_change_during_fetch_is_not_overwritten(repair, monkeypatch):
    h = repair.h
    page = repair.fetcher.page
    def changed(*args):
        fetched = page(*args)
        h.store.data[repair.row['note_object']] = repair.note + b'concurrent change'
        return fetched
    monkeypatch.setattr(repair.fetcher, 'page', changed)
    writes = list(h.store.writes)
    result = run(repair, apply=True)
    assert result['status'] == 'failed' and result['stage'] == 'recheck'
    assert h.store.writes == writes
    assert h.store.data[repair.row['note_object']].endswith(b'concurrent change')


def test_partial_update_will_not_overwrite_a_subsequent_edit(repair):
    h = repair.h
    h.store.fail_prefix = 'notes/'
    assert run(repair, apply=True)['status'] == 'failed'
    h.store.fail_prefix = None
    h.store.data[repair.row['note_object']] = repair.note + b'local change'
    before, writes = dict(h.store.data), list(h.store.writes)
    assert run(repair, apply=True)['status'] == 'failed'
    assert h.store.data == before and h.store.writes == writes


def test_existing_preview_directory_fails_before_mutating_gcs(repair, tmp_path):
    h = repair.h
    before, writes = dict(h.store.data), list(h.store.writes)
    result = run(repair, apply=True, output=tmp_path)
    assert result['status'] == 'failed' and result['stage'] == 'preview'
    assert h.store.data == before and h.store.writes == writes


@pytest.mark.parametrize('field,value', [('schema_version', True), ('note_id', '../escape'),
                                       ('expected_note_sha256', 'bad'),
                                       ('images', [{'url': 'http://example.com/a', 'after': 'summary'}]),
                                       ('images', [{'url': 'https://example.com/a', 'after': 'key_point_9'}])])
def test_plan_validation_rejects_unsafe_or_ambiguous_requests(repair, field, value):
    data = repair.plan.model_dump() | {field: value}
    with pytest.raises(ValueError):
        ImageRepairPlan.model_validate(data)


def test_runner_needs_no_api_key_and_closes_clients(repair, tmp_path, monkeypatch, capsys):
    spec = importlib.util.spec_from_file_location('repair_note_images', Path(__file__).parents[1] / 'scripts/repair_note_images.py')
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    h = repair.h
    closed = []
    h.store.client = SimpleNamespace(close=lambda: closed.append('store'))
    h.fetcher.close = lambda: closed.append('fetcher')
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.setattr(script, 'load_config', lambda *args: (h.app, [h.source]))
    monkeypatch.setattr(script, 'GCSStore', lambda _: h.store)
    monkeypatch.setattr(script, 'Fetcher', lambda _: h.fetcher)
    plan = tmp_path / 'plan.json'
    plan.write_text(repair.plan.model_dump_json())
    output = tmp_path / 'preview'
    assert script.main(['--plan', str(plan), '--output', str(output)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['planned'] == 1 and result['updated'] == 0
    assert json.loads((output / 'result.json').read_text()) == result
    assert closed == ['fetcher', 'store'] and len(h.sdk.calls) == 1
