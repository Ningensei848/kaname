import json
import re

import pytest

from techkb.markup import concept, plain, valid_saved_concept
from techkb.publication import export_notes, ExportError
from techkb.publication.snapshot import load_snapshot
from techkb import composer


@pytest.mark.parametrize('raw,expected', [
    ('Alpha / Beta', 'Alpha Beta'), ('A::B', 'A B'), (' A # B ', 'A B'),
    ('Repeated   whitespace', 'Repeated whitespace'),
    ('x' * 159 + ' suffix', 'x' * 159), ('x' * 159 + '.suffix', 'x' * 159),
])
def test_concept_normalization_is_idempotent(raw, expected):
    result = concept(raw)
    assert result == expected and concept(result) == result


@pytest.mark.parametrize('term', ['Alpha   Beta', 'x' * 159 + ' ', 'x' * 159 + '.', 'Alpha Beta'])
def test_exact_legacy_formatter_range_is_accepted(term):
    assert valid_saved_concept(term)


@pytest.mark.parametrize('term', ['', ' leading', '.leading', 'trailing ', 'trailing.',
    'Alpha\tBeta', 'Alpha\nBeta', 'Alpha\u2003Beta', 'x' * 161,
    'A/B', 'A#B', 'A|B', '[[A]]', '<script>', 'A\\B', 'A"B', 'A*B', 'A?B'])
def test_non_formatter_output_and_delimiters_are_rejected(term):
    assert not valid_saved_concept(term)


def legacy(value):
    return re.sub(r'[\[\]#|^<>\\/:*?\"]', ' ', plain(value)).strip(' .')[:160]


def test_saved_legacy_note_exports_without_rewriting_note_or_receipt(harness, monkeypatch, tmp_path):
    payload = json.loads(harness.sdk.text)
    payload['related_concepts'] = ['Alpha / Beta', 'GlucoFM']
    harness.sdk.text = json.dumps(payload)
    monkeypatch.setattr(composer, 'concept', legacy)
    monkeypatch.setattr('techkb.pipeline.article_authors', lambda _: ['First / Last'])
    assert harness.pipeline.run().saved == 1
    note = next(harness.store.read(n) for n in harness.store.list('notes/'))
    assert b'- [[Alpha   Beta]]' in note
    assert '[[First   Last]]' in note.decode()
    before = dict(harness.store.data)
    export_notes(harness.store, tmp_path / 'snapshot')
    _, files, _ = load_snapshot(tmp_path / 'snapshot')
    assert note in files.values() and harness.store.data == before


def test_legacy_spacing_does_not_allow_unreviewed_body_links(harness, monkeypatch, tmp_path):
    payload = json.loads(harness.sdk.text)
    payload['related_concepts'] = ['Alpha / Beta', 'GlucoFM']
    harness.sdk.text = json.dumps(payload)
    monkeypatch.setattr(composer, 'concept', legacy)
    harness.pipeline.run()
    name = next(iter(harness.store.list('notes/')))
    original = harness.store.data[name]
    altered = original.replace('- 要点'.encode(), '- [[Alpha   Beta]]'.encode())
    harness.store.data[name] = altered
    receipt_name = next(iter(harness.store.list('state/receipts/')))
    receipt = json.loads(harness.store.read(receipt_name));receipt['note'] = altered.decode()
    harness.store.data[receipt_name] = json.dumps(receipt).encode()
    with pytest.raises(ExportError, match='invalid_compact_body'):
        export_notes(harness.store, tmp_path / 'snapshot')
