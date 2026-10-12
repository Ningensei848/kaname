from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup
import pytest

from techkb.markup import inline
from techkb.wikilinks import linked_inline, project_wikilinks
from techkb.publication import export_notes, ExportError
from techkb.publication.snapshot import load_snapshot
from techkb.publication.note import plain_body
from techkb.site import project_content
from link_acceptance import audit_note_anchors, audit_search_links


@pytest.mark.parametrize("term", ['日本語', 'two words', 'C++', 'A&B', '"quoted"', 'a&safe=no', '角括弧以外の(語)'])
def test_search_query_round_trip_without_extra_parameters(term):
    output = project_wikilinks('[[' + term + ']]', {}, 'a' * 64)
    link = BeautifulSoup(output, 'html.parser').a
    target = urlsplit(link['href'])
    assert (target.scheme, target.netloc, target.path) == ('https', 'www.google.com', '/search')
    assert parse_qs(target.query) == {'q': [term]}
    assert link['target'] == '_blank'
    assert set(link['rel']) == {'noopener', 'noreferrer'}
    assert 'Google検索' in link['aria-label'] and '↗' in link.get_text()


def test_unique_title_alias_and_anchor_priority():
    note_id = 'b' * 64
    titles = {'GlucoFM': [note_id]}
    assert project_wikilinks('[[GlucoFM|図を読む]]', titles, 'a' * 64) == '[図を読む](' + note_id + ')'
    assert project_wikilinks(r'[[GlucoFM\|図を読む]]', titles, 'a' * 64) == '[図を読む](' + note_id + ')'
    assert project_wikilinks('[[GlucoFM#重要ポイント|要点]]', titles, 'a' * 64) == '[要点](' + note_id + '#%E9%87%8D%E8%A6%81%E3%83%9D%E3%82%A4%E3%83%B3%E3%83%88)'
    assert 'google.com' not in project_wikilinks('[[GlucoFM#missing]]', titles, 'a' * 64)
    assert project_wikilinks('[[#Summary]]', {}, note_id) == '[\\#Summary](' + note_id + '#summary)'
    output = project_wikilinks('[[Unknown#Heading|表示名]]', titles, 'a' * 64)
    link = BeautifulSoup(output, 'html.parser').a
    assert parse_qs(urlsplit(link['href']).query) == {'q': ['Unknown']}
    assert link.get_text().startswith('表示名')


def test_ambiguous_excluded_and_normalization_proposals_do_not_select_titles():
    for titles in ({}, {'LLM': ['a' * 64, 'b' * 64]}, {'llm': ['a' * 64]}):
        assert 'concept-search' in project_wikilinks('[[LLM]]', titles, 'c' * 64)


@pytest.mark.parametrize('protected', [
    r'\[[GlucoFM]]', '`[[GlucoFM]]`', '``a ` [[GlucoFM]]``',
    '```md\n[[GlucoFM]]\n```\n', '~~~\n[[GlucoFM]]\n~~~~\n',
    '    [[GlucoFM]]\n', '\t[[GlucoFM]]\n', '![[GlucoFM]]',
    '[label [[GlucoFM]]](https://example.com/a(b))',
    '![alt [[GlucoFM]]](https://example.com/image)',
    '[label [[GlucoFM]]][reference]', 'https://example.com/[[GlucoFM]]',
    '<https://example.com/[[GlucoFM]]>',
])
def test_projection_preserves_protected_markdown(protected):
    text = protected + '\nOutside [[GlucoFM]]'
    output = project_wikilinks(text, {}, 'a' * 64)
    assert output.startswith(protected)
    assert output.count('concept-search') == 1


def test_search_alias_cannot_inject_html():
    text = '[[A&B|<script> & "name"]]'
    soup = BeautifulSoup(project_wikilinks(text, {}, 'a' * 64), 'html.parser')
    assert not soup.find('script')
    assert '<script> & "name"' in soup.a.get_text()


def test_body_links_longest_candidate_and_identifier_boundaries():
    candidates = ['Copilot', 'GitHub Copilot', 'GlucoFM', 'C++', 'AI', 'technology']
    text = 'GitHub CopilotとGlucoFM。GlucoFM2 xGlucoFM C++ C++20 AI technology'
    assert linked_inline(text, candidates) == '[[GitHub Copilot]]と[[GlucoFM]]。GlucoFM2 xGlucoFM [[C++]] C++20 AI technology'
    assert linked_inline('no matching words', candidates) == inline('no matching words')


@pytest.mark.parametrize('protected', [
    '`GlucoFM`', '[[GlucoFM]]', '[GlucoFM](https://example.com)',
    '![GlucoFM](https://example.com/image)', 'https://example.com/GlucoFM',
    r'\GlucoFM', '<GlucoFM>',
])
def test_raw_body_preserves_markup_as_escaped_text_without_nested_links(protected):
    output = linked_inline(protected + ' GlucoFM', ['GlucoFM'])
    assert output == inline(protected) + ' [[GlucoFM]]'


def test_body_does_not_link_generic_short_or_sanitized_fragments():
    text = 'AI API data cloud 人工知能 機械学習 C# A|B'
    assert linked_inline(text, ['AI', 'API', 'data', 'cloud', '人工知能', '機械学習', 'C#', 'A|B']) == inline(text)


@pytest.mark.parametrize('value', ['[[Unknown]]', '[[GlucoFM|alias]]', '[GlucoFM](https://evil.example)', '<script>bad</script>'])
def test_public_body_rejects_unlisted_links_and_arbitrary_markup(value):
    with pytest.raises(ExportError, match='invalid_compact_body'):
        plain_body(value, ['GlucoFM'])


@pytest.mark.parametrize('mode', ['standard', 'batch'])
def test_shared_composer_and_publication_accept_body_links_and_keep_usage(harness, tmp_path, mode):
    import json
    h = harness
    response = json.loads(h.sdk.text)
    response.update(summary_ja='GlucoFMとGitHub Copilotを比較する。',
                    key_points=['GlucoFMで確認する', 'GitHub Copilotを使う'],
                    positioning_ja='GlucoFMの用途をGitHub Copilotと比較して整理する。',
                    related_concepts=['GlucoFM', 'GitHub Copilot'])
    h.sdk.text = json.dumps(response)
    if mode == 'batch':
        from test_batch import setup
        sdk = setup(h)
        assert h.pipeline.run().batch_submitted == 1
        sdk.finish()
        h.app.llm.max_calls_per_run = 0
    result = h.pipeline.run()
    assert result.saved == 1 and result.status == 'success'
    root = tmp_path / 'snapshot'
    export_notes(h.store, root)
    manifest, files, metadata = load_snapshot(root)
    entry = manifest['notes'][0]
    text = files[entry['path']].decode()
    assert '> [[GlucoFM]]と[[GitHub Copilot]]を比較する。' in text
    assert '- [[GlucoFM]]で確認する' in text
    assert '[[GlucoFM]]の用途を[[GitHub Copilot]]と比較' in text
    assert metadata[entry['id']]['description'] == response['summary_ja']
    before = dict(files)
    projected = project_content(manifest, files, metadata)[entry['path']].decode()
    assert projected.count('concept-search') == 8 and files == before
    assert result.llm_calls == (1 if mode == 'standard' else 0)


def test_missing_internal_heading_remains_an_audit_failure():
    files = {'notes/a.html': b'<h2 id="summary">Summary</h2><a href="a#missing">broken</a>'}
    with pytest.raises(ExportError, match='missing_note_anchor'):
        audit_note_anchors(files)
    files['notes/a.html'] = b'<h2 id="summary">Summary</h2><a href="a#summary">working</a>'
    audit_note_anchors(files)


def test_code_that_looks_like_search_html_is_not_an_expected_link():
    manifest = {'notes': [{'id': 'a', 'path': 'notes/a.md', 'title': 'A'}]}
    original = {'notes/a.md': b'---\ntitle: A\n---\n\n`<a class="concept-search">[[Hidden]]</a>`'}
    files = {'notes/a.html': b'<code>&lt;a class="concept-search"&gt;[[Hidden]]&lt;/a&gt;</code>',
             'static/contentIndex.json': b'{}'}
    assert audit_search_links(manifest, original, files) == 0
