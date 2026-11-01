"""Shared parsing must retain fresh link, heading and search safety checks."""
import pytest

from link_acceptance import parse_html, audit_note_anchors, audit_search_links
from kaname.publication import ExportError
from image_acceptance import check_image_pages


@pytest.mark.parametrize('href', ['b#%E8%A6%81%E7%B4%84', 'b.html#%E8%A6%81%E7%B4%84', '/kaname/notes/b#%E8%A6%81%E7%B4%84'])
def test_cross_note_unicode_heading_is_checked_with_shared_documents(href):
    files = {'notes/a.html': f'<a href="{href}">heading</a>'.encode(),
             'notes/b.html': '<h2 id="要約">Summary</h2>'.encode()}
    audit_note_anchors(files, parse_html(files))
    files['notes/b.html'] = b'<h2 id="other">Other</h2>'
    with pytest.raises(ExportError, match='missing_note_anchor'):
        audit_note_anchors(files, parse_html(files))


def test_directory_index_and_external_fragments_preserve_link_contract():
    files = {'notes/a.html': b'<a href="../#top">Home</a><a href="https://example.com/#elsewhere">External</a>',
             'index.html': b'<h1 id="top">Home</h1>'}
    audit_note_anchors(files, parse_html(files))
    files['index.html'] = b'<h1>Home</h1>'
    with pytest.raises(ExportError, match='missing_note_anchor'):
        audit_note_anchors(files)


@pytest.mark.parametrize('damage,error', [('href', 'search_link_mismatch'), ('rel', 'unsafe_search_link'), ('target', 'unsafe_search_link'), ('graph', 'search_link_in_graph')])
def test_shared_search_document_still_rejects_wrong_or_unsafe_links(damage, error):
    manifest = {'notes': [{'id': 'a', 'path': 'notes/a.md', 'title': 'A'}]}
    original = {'notes/a.md': b'---\ntitle: A\n---\n\n[[External]]'}
    anchor = ('<a class="concept-search" href="https://www.google.com/search?q=External" '
              'target="_blank" rel="noopener noreferrer" aria-label="ExternalをGoogle検索で調べる（新しいタブ）">'
              'External <span aria-hidden="true">↗</span></a>')
    files = {'notes/a.html': anchor.encode(), 'static/contentIndex.json': b'{}'}
    assert audit_search_links(manifest, original, files, parse_html(files)) == 1
    if damage == 'href': anchor = anchor.replace('q=External', 'q=Wrong')
    elif damage == 'rel': anchor = anchor.replace('noopener noreferrer', 'noopener')
    elif damage == 'target': anchor = anchor.replace('_blank', '_self')
    else: files['static/contentIndex.json'] = b'{"a":{"links":["https://www.google.com/search?q=External"]}}'
    files['notes/a.html'] = anchor.encode()
    with pytest.raises(ExportError, match=error):
        audit_search_links(manifest, original, files, parse_html(files))


@pytest.mark.parametrize('workers', [0, 3, True])
def test_unbounded_or_noninteger_browser_count_is_rejected(workers):
    with pytest.raises(ValueError, match='invalid_image_workers'):
        check_image_pages('http://unused.invalid', {}, workers)


def test_empty_image_input_needs_no_browser_import(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, 'playwright', None)
    assert check_image_pages('http://unused.invalid', {'a': []}) == dict(notes=0, requests=0, workers=0, images=0)
