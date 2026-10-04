import pytest
from pydantic import ValidationError
from techkb.config import Source, RelevantFilter
from techkb.extraction import extract_main, parse_listing, relevance
from techkb.pending import Candidate


def test_main_extract_skips_changing_navigation(harness):
    h = harness
    h.source.extract_main = True
    h.fetcher.pages['https://example.com/a'] = b'<nav>old links</nav><article>Stable main text</article><footer>advert</footer>'
    first = h.pipeline.run()
    h.fetcher.pages['https://example.com/a'] = b'<nav>new links</nav><article>Stable main text</article><footer>another advert</footer>'
    second = h.pipeline.run()
    assert first.saved == 1 and second.content_duplicates == 1
    assert len(h.sdk.calls) == 1


def test_missing_selector_remains_pending_without_llm(harness):
    harness.source.content_selector = '.missing'
    result = harness.pipeline.run()
    assert result.status == 'failed' and result.pending_after == 1
    assert not harness.sdk.calls


def test_relevance_is_deterministic_before_llm(harness):
    h = harness
    h.source.relevant_filter = RelevantFilter(exclude_keywords=['ＯＲＩＧＩＮＡＬ'])
    result = h.pipeline.run()
    assert result.filtered == 1 and result.pending_after == 0 and result.saved == 0
    assert result.filter_reasons == {'keyword_excluded': 1}
    assert not h.sdk.calls and not h.store.list('state/index/')


def test_domain_and_configured_category(harness):
    source = harness.source
    item = Candidate('',source.id,'https://example.com/a')
    source.category = 'cloud'
    source.relevant_filter = RelevantFilter(include_domains=['example.com'], include_categories=['cloud'])
    assert relevance(source,item,'') is None
    source.relevant_filter.exclude_domains = ['example.com']
    assert relevance(source,item,'') == 'domain_excluded'
    source.relevant_filter = RelevantFilter(include_categories=['ai-llm'])
    assert relevance(source,item,'AI content') == 'category_not_included'


def test_listing_normalizes_and_rejects_external_links(harness):
    source = harness.source.model_copy(update={'type':'html','listing_url':'https://example.com/blog','link_selector':'.post'})
    raw = b'<a class="post" href="/a?utm_source=x">A</a><a class="post" href="/a">A</a><a class="post" href="https://external.com/a">Other</a><a class="post" href="javascript:bad">bad</a>'
    items = parse_listing(raw,'https://example.com/blog',source,'now')
    assert len(items) == 1 and items[0].url == 'https://example.com/a'
    assert items[0].title == 'A'


def test_html_pipeline_discovers_without_rss(harness):
    h=harness
    h.source.type='html'; h.source.listing_url='https://example.com/blog'; h.source.link_selector='a.post'
    h.fetcher.pages['https://example.com/blog']=b'<a class="post" href="/a">Article</a>'
    result=h.pipeline.run()
    assert result.status=='success' and result.saved==1


def test_html_requires_listing_and_selector():
    with pytest.raises(ValidationError):
        Source(id='a',name='a',type='html',base_url='https://example.com')
    assert b'body' in extract_main(b'<nav>outside</nav><main>body</main>')
