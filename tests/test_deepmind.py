"""Source regressions use synthetic text in the observed two public DOM layouts."""
import json
from pathlib import Path

import pytest

from techkb.config import load_config
from techkb.state import State


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('layout', ['legacy', 'google_blog'])
def test_body_selection_preserves_article_and_excludes_cards(harness, layout):
    _, sources = load_config(ROOT / 'config/app.yaml', ROOT / 'config/sources.yaml')
    source = next(s for s in sources if s.id == 'google-deepmind')
    h = harness
    h.source.extract_main = source.extract_main
    h.source.content_selector = source.content_selector
    raw = (ROOT / f'tests/fixtures/corpus/deepmind_{layout}.html').read_bytes()
    raw = raw.replace(b'Navigation links outside article', b'Navigation links outside article ' * 1000)
    h.fetcher.pages['https://example.com/a'] = raw
    report = h.pipeline.run()
    assert report.saved == 1 and len(h.sdk.calls) == 1
    content = json.loads(h.sdk.calls[0]['contents'])
    body = content['article_markdown']
    assert 'Article introduction.' in body and 'Article conclusion.' in body
    assert 'measured limitations' in body and len(body) < h.app.llm.max_input_chars
    assert 'outside article' not in body and 'Related posts' not in body
    assert len(content['metadata']['image_candidates']) == 1
    assert content['metadata']['image_candidates'][0]['alt'] == 'Method diagram'
    # Navigation updates must not buy a second summary of the same body.
    h.fetcher.pages['https://example.com/a'] = raw.replace(b'Navigation links', b'Updated navigation')
    assert h.pipeline.run().content_duplicates == 1
    assert len(h.sdk.calls) == 1


def test_body_layout_missing_stops_before_paid_request(harness):
    _, sources = load_config(ROOT / 'config/app.yaml', ROOT / 'config/sources.yaml')
    source = next(s for s in sources if s.id == 'google-deepmind')
    h = harness
    h.source.extract_main = source.extract_main
    h.source.content_selector = source.content_selector
    h.fetcher.pages['https://example.com/a'] = b'<main><article class="card">Related posts</article></main>'
    report = h.pipeline.run()
    assert report.status == 'failed' and report.pending_after == 1
    assert not h.sdk.calls and not State(h.store).rows
