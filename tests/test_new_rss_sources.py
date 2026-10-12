"""Keep each newly enabled source's article and figures inside the input budget."""
import json
from pathlib import Path

import pytest

from techkb.config import load_config
from techkb.publication.note import validate_note
from techkb.state import State


ROOT = Path(__file__).resolve().parents[1]
CASES = ['microsoft-research', 'meta-engineering', 'apple-ml-research', 'cloudflare-security']


@pytest.mark.parametrize('source_id', CASES)
def test_body_and_figure_reach_model_without_navigation(harness, source_id):
    app, sources = load_config(ROOT / 'config/app.yaml', ROOT / 'config/sources.yaml')
    source = next(s for s in sources if s.id == source_id)
    h = harness
    h.source.extract_main = source.extract_main
    h.source.content_selector = source.content_selector
    raw = (ROOT / f'tests/fixtures/corpus/{source_id.replace("-", "_")}.html').read_bytes()
    raw = raw.replace(b'Navigation outside article', b'Navigation outside article ' * 1000)
    h.fetcher.pages['https://example.com/a'] = raw
    response = json.loads(h.sdk.text)
    response['images'] = [{'image_id': 'img-1', 'after': 'summary'}]
    h.sdk.text = json.dumps(response)
    report = h.pipeline.run()
    assert report.status == 'success' and report.saved == report.llm_calls == 1
    request = json.loads(h.sdk.calls[0]['contents'])
    body = request['article_markdown']
    assert 'Article introduction.' in body and 'Article conclusion.' in body
    assert 'measured limitations' in body and len(body) < app.llm.max_input_chars
    assert 'outside article' not in body and 'Related posts' not in body
    assert len(request['metadata']['image_candidates']) == 1
    assert request['metadata']['image_candidates'][0]['caption'] == 'Measured method and limitations.'
    row = State(h.store).rows[0]
    note = h.store.read(row['note_object'])
    validate_note(note, row, app.tracking_parameters, app.categories)
    assert b'![Method diagram]' in note
    h.fetcher.pages['https://example.com/a'] = raw.replace(b'Navigation outside', b'Changed navigation outside')
    assert h.pipeline.run().content_duplicates == 1 and len(h.sdk.calls) == 1


@pytest.mark.parametrize('source_id', CASES)
def test_missing_body_keeps_pending_without_generation(harness, source_id):
    _, sources = load_config(ROOT / 'config/app.yaml', ROOT / 'config/sources.yaml')
    source = next(s for s in sources if s.id == source_id)
    h = harness
    h.source.extract_main = source.extract_main
    h.source.content_selector = source.content_selector
    h.fetcher.pages['https://example.com/a'] = b'<main><article class="card">Related posts</article></main>'
    report = h.pipeline.run()
    assert report.status == 'failed' and report.pending_after == 1
    assert not h.sdk.calls and not h.store.list('notes/')
