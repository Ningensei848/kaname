import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from kaname.audit import audit_state
from kaname.costs import cost_report
from kaname.note_corrections import NoteCorrectionPlan, correct_note, corrected_note, plan_payload
from kaname.publication import export_notes
from kaname.publication.common import sha256
from kaname.publication.note import correction_trailer, note_frontmatter, validate_note
from kaname.publication.snapshot import snapshot_files, load_snapshot
from kaname.state import State


def plan_for(note, note_id, old='追加要点', new='確認済みの追加要点'):
    return NoteCorrectionPlan(schema_version=1, note_id=note_id, expected_note_sha256=sha256(note),
        expected_text_sha256=sha256(note.decode().replace(old, new).encode()),
        source='https://example.com/a', checked_at='2026-10-25',
        edits=[dict(old=old, new=new, expected_occurrences=note.decode().count(old))])


@pytest.fixture
def correction(harness):
    h = harness
    assert h.pipeline.run().saved == 1
    files, _ = snapshot_files(h.store, categories=h.app.categories)
    entry = json.loads(files['manifest.json'])['notes'][0]
    row = State(h.store).rows[0]
    note = h.store.read(row['note_object'])
    return SimpleNamespace(h=h, row=row, note=note, plan=plan_for(note, entry['id']))


def run(correction, **kwargs):
    return correct_note(correction.h.store, correction.h.app, correction.plan, **kwargs)


def test_preview_changes_no_state_and_labels_assisted_correction(correction, tmp_path):
    h = correction.h
    before, writes = dict(h.store.data), list(h.store.writes)
    result = run(correction, output=tmp_path / 'preview')
    assert result['status'] == 'success' and result['planned'] == 1 and not result['updated']
    assert h.store.data == before and h.store.writes == writes
    note = (tmp_path / 'preview' / (correction.plan.note_id + '.md')).read_bytes()
    meta = validate_note(note, correction.row, h.app.tracking_parameters, h.app.categories)
    assert meta['note_corrections'][-1]['reviewer_kind'] == 'automated_assistant'
    assert '自動支援で訂正' in note.decode() and '確認済みの追加要点' in note.decode()
    assert result['after_sha256'] == sha256(note) and len(h.sdk.calls) == 1


def test_apply_keeps_original_receipt_billing_index_and_public_identity(correction, tmp_path):
    h = correction.h
    before, costs = dict(h.store.data), cost_report(h.store, h.app)
    receipt_name = 'state/receipts/' + correction.row['content_sha256'] + '.json'
    result = run(correction, apply=True)
    assert result['status'] == 'success' and result['updated'] == 1
    receipt = json.loads(h.store.read(receipt_name))
    assert h.store.read(receipt['note_correction']['history']) == before[receipt_name]
    assert receipt['row'] == json.loads(before[receipt_name])['row']
    assert receipt['usage_run_id'] == json.loads(before[receipt_name])['usage_run_id']
    assert h.store.read(correction.row['note_object']) == receipt['note'].encode()
    for name, data in before.items():
        if name not in (receipt_name, correction.row['note_object']):
            assert h.store.read(name) == data
    assert cost_report(h.store, h.app) == costs and audit_state(h.store)['status'] == 'success'
    assert export_notes(h.store, tmp_path / 'export')['status'] == 'success'
    entry = json.loads((tmp_path / 'export/manifest.json').read_text())['notes'][0]
    assert entry['id'] == correction.plan.note_id and entry['sha256'] == result['after_sha256']
    h.store.writes.clear()
    assert run(correction, apply=True)['unchanged'] == 1
    assert not h.store.writes and len(h.sdk.calls) == 1


@pytest.mark.parametrize('prefix', ['state/note-correction-history/', 'state/note-corrections/', 'state/receipts/', 'notes/'])
def test_every_failed_write_can_resume_without_paid_work(correction, prefix):
    h = correction.h
    h.store.fail_prefix = prefix
    assert run(correction, apply=True)['status'] == 'failed'
    h.store.fail_prefix = None
    assert run(correction, apply=True)['status'] == 'success'
    assert audit_state(h.store)['status'] == 'success' and len(h.sdk.calls) == 1


@pytest.mark.parametrize('boundary', ['intent', 'receipt', 'note', 'complete'])
def test_pipeline_recovers_interrupted_correction_before_any_generation(correction, monkeypatch, boundary):
    h = correction.h
    write = h.store.write
    def kill(name, data, *args):
        write(name, data, *args)
        if ((boundary == 'receipt' and name.startswith('state/receipts/')) or
                (boundary == 'note' and name.startswith('notes/')) or
                (boundary in {'intent', 'complete'} and name.startswith('state/note-corrections/') and
                 json.loads(data)['status'] == ('pending' if boundary == 'intent' else 'complete'))):
            raise KeyboardInterrupt()
    monkeypatch.setattr(h.store, 'write', kill)
    with pytest.raises(KeyboardInterrupt):
        run(correction, apply=True)
    monkeypatch.setattr(h.store, 'write', write)
    recovered = h.pipeline.run()
    assert recovered.status == 'success' and recovered.llm_calls == 0 and len(h.sdk.calls) == 1
    assert '確認済みの追加要点' in h.store.read(correction.row['note_object']).decode()
    assert audit_state(h.store)['status'] == 'success'


def test_missing_completion_marker_is_audited_and_recovered(correction, monkeypatch):
    h = correction.h
    write = h.store.write
    def fail_complete(name, data, *args):
        if name.startswith('state/note-corrections/') and json.loads(data)['status'] == 'complete':
            raise OSError('private')
        write(name, data, *args)
    monkeypatch.setattr(h.store, 'write', fail_complete)
    assert run(correction, apply=True)['stage'] == 'intent_complete'
    assert {'code': 'pending_note_corrections', 'count': 1} in audit_state(h.store)['issues']
    monkeypatch.setattr(h.store, 'write', write)
    assert h.pipeline.run().status == 'success' and len(h.sdk.calls) == 1


@pytest.mark.parametrize('old,new', [('publisher: Example', 'publisher: Different'),
    ('ai_model: gemini-3.5-flash-lite', 'ai_model: different'),
    ('Model Context Protocol', 'Different Concept'), ('追加要点', '<script>private</script>')])
def test_plan_cannot_change_identity_graph_declarations_or_unsafe_markup(correction, old, new):
    h = correction.h
    plan = plan_for(correction.note, correction.plan.note_id, old, new)
    before = dict(h.store.data)
    assert correct_note(h.store, h.app, plan, apply=True)['status'] == 'failed'
    assert h.store.data == before


@pytest.mark.parametrize('field,value', [('expected_note_sha256', '0' * 64),
    ('expected_text_sha256', '0' * 64), ('source', 'https://other.example/a'),
    ('edits', [dict(old='追加要点', new='訂正', expected_occurrences=2)])])
def test_stale_hash_source_or_edit_count_fails_without_writes(correction, field, value):
    h = correction.h
    before = dict(h.store.data)
    plan = NoteCorrectionPlan.model_validate(correction.plan.model_dump() | {field: value})
    assert correct_note(h.store, h.app, plan, apply=True)['status'] == 'failed'
    assert h.store.data == before


def test_repeated_corrections_keep_a_chain_and_reject_replaying_old_plan(correction):
    h = correction.h
    assert run(correction, apply=True)['updated'] == 1
    second_note = h.store.read(correction.row['note_object'])
    second = plan_for(second_note, correction.plan.note_id, '確認済みの追加要点', 'さらに確認した要点')
    result = correct_note(h.store, h.app, second, apply=True)
    assert result['status'] == 'success'
    note = h.store.read(correction.row['note_object'])
    assert len(note_frontmatter(note)[2]['note_corrections']) == 2
    assert len(h.store.list('state/note-correction-history/')) == 2
    before = dict(h.store.data)
    assert run(correction, apply=True)['status'] == 'failed' and h.store.data == before


def test_human_edit_after_partial_update_is_preserved_and_blocks_paid_work(correction):
    h = correction.h
    h.store.fail_prefix = 'notes/'
    assert run(correction, apply=True)['status'] == 'failed'
    h.store.fail_prefix = None
    h.store.data[correction.row['note_object']] += b'concurrent edit'
    before = dict(h.store.data)
    assert run(correction, apply=True)['status'] == 'failed' and h.store.data == before
    h.fetcher.pages['https://example.com/b'] = b'<article>New unpaid work</article>'
    assert h.pipeline.run().status == 'failed' and len(h.sdk.calls) == 1


def test_tampered_correction_history_cannot_be_used_for_resume(correction):
    h = correction.h
    h.store.fail_prefix = 'notes/'
    assert run(correction, apply=True)['status'] == 'failed'
    h.store.fail_prefix = None
    name = h.store.list('state/note-correction-history/')[0]
    value = json.loads(h.store.read(name)); value['note'] += 'tampered'
    h.store.data[name] = json.dumps(value).encode()
    before = dict(h.store.data)
    assert run(correction, apply=True)['status'] == 'failed' and h.store.data == before


@pytest.mark.parametrize('mutation', ['remove_trailer', 'human_reviewer', 'extra_text'])
def test_public_validation_requires_exact_correction_metadata_and_trailer(correction, mutation):
    h = correction.h
    note = corrected_note(correction.note, correction.row, h.app, correction.plan)
    if mutation == 'remove_trailer':
        note = note.split('\n## 訂正記録'.encode())[0]
    elif mutation == 'human_reviewer':
        note = note.replace(b'automated_assistant', b'human')
    else:
        note += b'additional unreviewed text'
    with pytest.raises(ValueError):
        validate_note(note, correction.row, h.app.tracking_parameters, h.app.categories)


def test_existing_output_directory_fails_before_any_mutation(correction, tmp_path):
    before = dict(correction.h.store.data)
    assert run(correction, apply=True, output=tmp_path)['stage'] == 'preview'
    assert correction.h.store.data == before


def date_plan(correction, note=None, after='2026-10-02'):
    original = note or correction.note
    before = note_frontmatter(original)[2]['published']
    assert before != after
    edits = [dict(old='published: ' + (f"'{before}'" if before else 'null'),
                  new=f"published: '{after}'", expected_occurrences=1),
             dict(old='- Published: ' + (before or '（取得なし）'), new='- Published: ' + after, expected_occurrences=1)]
    text = original.decode()
    for edit in edits:
        text = text.replace(edit['old'], edit['new'])
    return NoteCorrectionPlan.model_validate(correction.plan.model_dump() | dict(
        expected_note_sha256=sha256(original), expected_text_sha256=sha256(text.encode()),
        source_published=after, edits=edits))


def test_date_correction_changes_public_date_without_rewriting_generation_or_costs(correction, tmp_path):
    h = correction.h
    before, costs = dict(h.store.data), cost_report(h.store, h.app)
    plan = date_plan(correction)
    result = correct_note(h.store, h.app, plan, apply=True)
    assert result['status'] == 'success' and result['updated'] == 1
    note = h.store.read(correction.row['note_object'])
    meta = validate_note(note, correction.row, h.app.tracking_parameters, h.app.categories)
    old_meta = note_frontmatter(correction.note)[2]
    assert meta['published'] == plan.source_published
    assert meta['created'] == old_meta['created'] and meta['ai_model'] == old_meta['ai_model']
    record = meta['note_corrections'][-1]
    assert record['published_before'] == old_meta['published'] and record['published_after'] == plan.source_published
    assert f"原典公開日 {old_meta['published'] or '不明'} → {plan.source_published}" in note.decode()
    receipt_name = 'state/receipts/' + correction.row['content_sha256'] + '.json'
    receipt = json.loads(h.store.read(receipt_name))
    assert h.store.read(receipt['note_correction']['history']) == before[receipt_name]
    assert receipt['row'] == json.loads(before[receipt_name])['row']
    assert receipt['usage_run_id'] == json.loads(before[receipt_name])['usage_run_id']
    assert {n: v for n, v in before.items() if n != receipt_name and n != correction.row['note_object']} == {
        n: h.store.read(n) for n in before if n != receipt_name and n != correction.row['note_object']}
    assert cost_report(h.store, h.app) == costs and audit_state(h.store)['status'] == 'success'
    assert export_notes(h.store, tmp_path / 'export')['status'] == 'success'
    _, files, metadata = load_snapshot(tmp_path / 'export', h.app.tracking_parameters)
    assert next(iter(metadata.values()))['published'] == plan.source_published
    assert json.loads(files['manifest.json'])['notes'][0]['published'] == plan.source_published
    h.store.writes.clear()
    assert correct_note(h.store, h.app, plan, apply=True)['unchanged'] == 1 and not h.store.writes
    assert len(h.sdk.calls) == 1


@pytest.mark.parametrize('mode', ['undeclared', 'wrong_date', 'no_op'])
def test_date_override_requires_an_explicit_matching_actual_change(correction, mode):
    plan = date_plan(correction)
    values = plan.model_dump()
    if mode == 'undeclared':
        values['source_published'] = None
    elif mode == 'wrong_date':
        values['source_published'] = '2026-10-03'
    else:
        assert correct_note(correction.h.store, correction.h.app, plan, apply=True)['status'] == 'success'
        values = plan_for(correction.h.store.read(correction.row['note_object']), correction.plan.note_id).model_dump() | {
            'source_published': plan.source_published}
    before = dict(correction.h.store.data)
    assert correct_note(correction.h.store, correction.h.app, NoteCorrectionPlan.model_validate(values), apply=True)['status'] == 'failed'
    assert correction.h.store.data == before


@pytest.mark.parametrize('value', ['2026-02-30', '20261002', '2026-10-02T00:00:00Z', 20261002])
def test_source_publication_override_requires_exact_iso_date(correction, value):
    with pytest.raises(ValueError):
        NoteCorrectionPlan.model_validate(correction.plan.model_dump() | {'source_published': value})


@pytest.mark.parametrize('mutation', ['missing_before', 'missing_after', 'wrong_before', 'wrong_after', 'bad_date', 'extra_key'])
def test_date_history_must_be_paired_valid_and_anchored_to_the_original_index(correction, mutation):
    h = correction.h
    note = corrected_note(correction.note, correction.row, h.app, date_plan(correction))
    text, match, meta = note_frontmatter(note)
    body = text[match.end():-len(correction_trailer(meta['note_corrections']))]
    record = meta['note_corrections'][-1]
    if mutation.startswith('missing_'):
        record.pop('published_' + mutation.removeprefix('missing_'))
    elif mutation == 'extra_key':
        record['extra'] = 'private'
    else:
        record[{'wrong_before': 'published_before', 'wrong_after': 'published_after', 'bad_date': 'published_after'}[mutation]] = {
            'wrong_before': '2026-09-01', 'wrong_after': '2026-10-03', 'bad_date': '2026-02-30'}[mutation]
    with pytest.raises(ValueError):
        trailer = correction_trailer(meta['note_corrections'])
        changed = ('---\n' + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False) + '---\n' + body + trailer).encode()
        validate_note(changed, correction.row, h.app.tracking_parameters, h.app.categories)


def test_date_and_text_corrections_chain_and_failed_note_save_recovers(correction):
    h = correction.h
    first = date_plan(correction)
    h.store.fail_prefix = 'notes/'
    assert correct_note(h.store, h.app, first, apply=True)['status'] == 'failed'
    h.store.fail_prefix = None
    assert h.pipeline.run().llm_calls == 0
    second = date_plan(correction, h.store.read(correction.row['note_object']), after='2026-10-03')
    assert correct_note(h.store, h.app, second, apply=True)['status'] == 'success'
    third = plan_for(h.store.read(correction.row['note_object']), correction.plan.note_id)
    assert correct_note(h.store, h.app, third, apply=True)['status'] == 'success'
    note = h.store.read(correction.row['note_object'])
    assert validate_note(note, correction.row, h.app.tracking_parameters, h.app.categories)['published'] == '2026-10-03'
    assert audit_state(h.store)['status'] == 'success' and len(h.sdk.calls) == 1
    before = dict(h.store.data)
    assert correct_note(h.store, h.app, first, apply=True)['status'] == 'failed' and h.store.data == before


def test_text_only_plan_hashes_remain_backward_compatible(correction):
    payload = correction.plan.model_dump()
    payload.pop('source_published')
    assert plan_payload(correction.plan) == payload


def test_cli_previews_local_state_without_clients_and_rejects_apply(correction, tmp_path, monkeypatch, capsys):
    spec = importlib.util.spec_from_file_location('correct_note_text', Path(__file__).parents[1] / 'scripts/correct_note_text.py')
    script = importlib.util.module_from_spec(spec); spec.loader.exec_module(script)
    h = correction.h
    root = tmp_path / 'state'
    for name, data in h.store.data.items():
        p = root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
    def forbidden(*args, **kwargs):
        pytest.fail('preview must not construct a remote client')
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.setattr(script, 'GCSStore', forbidden)
    plan = tmp_path / 'plan.json'; plan.write_text(correction.plan.model_dump_json())
    args = ['--plan', str(plan), '--state-dir', str(root), '--output', str(tmp_path / 'preview')]
    assert script.main(args) == 0
    assert json.loads(capsys.readouterr().out)['planned'] == 1
    assert script.main([*args, '--apply']) == 1
    assert json.loads(capsys.readouterr().out)['status'] == 'failed'
    result_file = tmp_path / 'preview/result.json'
    before = result_file.read_bytes()
    assert script.main(args) == 1
    assert json.loads(capsys.readouterr().out)['status'] == 'failed'
    assert result_file.read_bytes() == before
