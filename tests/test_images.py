import json

import pytest
import yaml

from techkb.images import article_images, image_url, image_block
from techkb.publication import export_notes, ExportError
from techkb.state import State
from techkb.site import load_snapshot, finish_html
from bs4 import BeautifulSoup
from test_batch import setup


ARTICLE = b'''<article><p>Architecture and evaluation</p>
<figure><img src="/architecture.png" alt="Architecture diagram">
<figcaption>Evaluation architecture</figcaption></figure>
<p>More details</p></article>'''


def select(h, after='key_point_1', image_id='img-1'):
    h.fetcher.pages['https://example.com/a'] = ARTICLE
    response = json.loads(h.sdk.text)
    response['images'] = [dict(image_id=image_id, after=after)]
    h.sdk.text = json.dumps(response)


@pytest.mark.parametrize('after', ['summary', 'key_point_1', 'key_point_2', 'positioning'])
def test_standard_places_images_and_exports_same_bytes_without_extra_calls(harness, tmp_path, after):
    h = harness
    select(h, after)
    result = h.pipeline.run()
    assert result.saved == 1 and len(h.sdk.calls) == 1
    row = State(h.store).rows[0]
    data = h.store.read(row['note_object'])
    text = data.decode()
    meta = yaml.safe_load(text.split('---', 2)[1])
    image = meta['article_images'][0]
    assert image == dict(image_id='img-1', url='https://example.com/architecture.png',
                         alt='Architecture diagram', after=after)
    assert image_block(image) in text
    anchor = {'summary': '> 本文に基づく要約です。', 'key_point_1': '- 要点',
              'key_point_2': '- 追加要点', 'positioning': '技術記事の内容を整理した資料です。後から技術判断を確認する際に参照できます。'}[after]
    assert anchor + image_block(image) in text
    content = json.loads(h.sdk.calls[0]['contents'])
    assert content['metadata']['image_candidates'][0]['image_id'] == 'img-1'
    assert 'architecture.png' not in h.sdk.calls[0]['contents']
    assert '![' not in content['article_markdown']
    assert '- Word count: 9\n' in text
    output = tmp_path / 'export'
    assert export_notes(h.store, output)['notes'] == 1
    entry = json.loads((output / 'manifest.json').read_bytes())['notes'][0]
    assert (output / entry['path']).read_bytes() == data
    assert h.pipeline.run().saved == 0 and len(h.sdk.calls) == 1


def test_batch_retains_candidates_through_recovery_and_no_double_charge(harness, tmp_path):
    h = harness
    select(h, 'summary')
    sdk = setup(h)
    assert h.pipeline.run().batch_submitted == 1
    ledger = json.loads(h.store.read(h.store.list('state/batches/')[0]))
    assert ledger['items'][0]['image_candidates'][0]['url'] == 'https://example.com/architecture.png'
    sdk.finish()
    h.app.llm.max_calls_per_run = 0
    assert h.pipeline.run().batch_saved == 1
    assert export_notes(h.store, tmp_path / 'export')['notes'] == 1
    assert h.pipeline.run().batch_saved == 0
    assert len(sdk.created) == 1 and not h.sdk.calls
    assert len(h.store.list('state/receipts/')) == 1
    assert len([name for name in h.store.list('runs/')
                if json.loads(h.store.read(name))['record_kind'] == 'batch_usage']) == 1


def test_extracts_body_images_resolves_lazy_url_and_respects_input_cut():
    raw = b'''<nav><img src="/logo.png" alt="logo"></nav><article>
        <figure><img src="data:image/png;base64,abc" data-src="//cdn.example.com/plot.png" alt="Plot">
        <figcaption>Measured result</figcaption></figure>
        <img src="/pixel.png" width="1" alt="Pixel">
        <figure><img src="/later.png" alt="Later"><figcaption>Beyond the cut</figcaption></figure>
        </article>'''
    images = article_images(raw, 'https://example.com/a', 'Plot Measured result Pixel')
    assert len(images) == 1 and images[0]['url'] == 'https://cdn.example.com/plot.png'
    assert images[0]['caption'] == 'Measured result'


def test_image_url_has_browser_compatible_canonical_bytes():
    assert image_url('https://EXAMPLE.com:443/図.png?x=日本語') == 'https://example.com/%E5%9B%B3.png?x=%E6%97%A5%E6%9C%AC%E8%AA%9E'
    assert article_images(b'<img alt="Plot">', 'https://example.com/article', 'Plot') == []


@pytest.mark.parametrize('url', ['http://example.com/a.png', 'javascript:alert(1)',
    'data:image/png;base64,a', 'https://user:password@example.com/a.png',
    'https://127.0.0.1/a.png', 'https://private.local/a.png', 'https://localhost/a.png',
    'https://127.1/a.png', 'https://0x7f.0x0.0x0.0x1/a.png',
    'https://example.com/a.png?token=secret', 'https://example.com/a.png?X-Amz-Signature=secret',
    'https://example.com/a.png\n', 'https://evil\'host.example/a.png'])
def test_rejects_unsafe_image_urls(url):
    with pytest.raises(ValueError):
        image_url(url)


@pytest.mark.parametrize('image_id,after', [('img-99', 'summary'), ('img-1', 'key_point_5')])
def test_invalid_llm_image_selection_keeps_usage_without_publishing(harness, image_id, after):
    h = harness
    select(h, after, image_id)
    result = h.pipeline.run()
    assert result.saved == 0 and len(h.sdk.calls) == 1
    assert result.total_input_tokens == 100
    assert not h.store.list('notes/')


def test_export_rejects_moved_or_unregistered_image(harness, tmp_path):
    h = harness
    select(h)
    assert h.pipeline.run().saved == 1
    row = State(h.store).rows[0]
    receipt_path = h.store.list('state/receipts/')[0]
    receipt = json.loads(h.store.read(receipt_path))
    meta = yaml.safe_load(receipt['note'].split('---', 2)[1])
    block = image_block(meta['article_images'][0])
    modified = receipt['note'].replace(block, '').replace('## 検索キーワード', '## 検索キーワード' + block)
    receipt['note'] = modified
    h.store.data[row['note_object']] = modified.encode()
    h.store.data[receipt_path] = json.dumps(receipt).encode()
    with pytest.raises(ExportError, match='invalid_article_images'):
        export_notes(h.store, tmp_path / 'export')


def test_rendered_images_limit_csp_to_the_note_and_do_not_send_referrer(harness, tmp_path):
    h = harness
    select(h)
    h.pipeline.run()
    root = tmp_path / 'snapshot'
    export_notes(h.store, root)
    manifest, files, _ = load_snapshot(root)
    compiled = tmp_path / 'compiled'
    (compiled / 'notes').mkdir(parents=True)
    home = compiled / 'index.html'
    home.write_text('<html><head></head><body><article>Library</article></body></html>')
    note = compiled / 'notes' / (manifest['notes'][0]['id'] + '.html')
    note.write_text('<html><head></head><body><article><img src="https://example.com/architecture.png"></article></body></html>')
    finish_html(compiled, manifest, files=files)
    soup = BeautifulSoup(note.read_text(), 'html.parser')
    image = soup.find('img')
    assert image['referrerpolicy'] == 'no-referrer' and image['loading'] == 'lazy'
    policy = soup.find('meta', attrs={'http-equiv': 'Content-Security-Policy'})['content']
    assert "img-src 'self' data: https://example.com;" in policy
    assert "connect-src 'self';" in policy
    assert 'https://example.com' not in home.read_text()


@pytest.mark.parametrize('markup,code', [
    ('<img src="https://unregistered.example.com/image.png">', 'unexpected_article_image'),
    ('<img src="https://example.com/architecture.png" srcset="https://other.example.com/a.png 2x">', 'unexpected_article_image'),
    ('', 'missing_article_image')])
def test_rendered_image_mismatch_never_becomes_an_artifact(harness, tmp_path, markup, code):
    h = harness
    select(h)
    h.pipeline.run()
    root = tmp_path / 'snapshot'
    export_notes(h.store, root)
    manifest, files, _ = load_snapshot(root)
    compiled = tmp_path / 'compiled'
    (compiled / 'notes').mkdir(parents=True)
    (compiled / 'notes' / (manifest['notes'][0]['id'] + '.html')).write_text(
        '<html><head></head><body><article>' + markup + '</article></body></html>')
    with pytest.raises(ExportError, match=code):
        finish_html(compiled, manifest, files=files)
