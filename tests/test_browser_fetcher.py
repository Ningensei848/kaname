import pytest
from techkb.browser_fetcher import SourceFetcher
from techkb.fetcher import FetchResult, FetchError

pytest.importorskip('playwright.sync_api')


def test_real_browser_renders_js_and_blocks_other_traffic(harness):
    class HTTP:
        config=harness.app.http
        calls=[]
        def get(self,url,*args,**kwargs):
            self.calls.append(url)
            if url=='https://example.com/article':
                return FetchResult(b'<article id="content"></article><script src="/app.js"></script>',url,200,'text/html')
            if url=='https://example.com/app.js':
                return FetchResult(b"document.querySelector('article').textContent='Rendered main text'; fetch('http://127.0.0.1/private').catch(()=>{}); new WebSocket('ws://127.0.0.1/socket');",url,200,'application/javascript')
            raise AssertionError('Unexpected request')
    h=HTTP(); source=harness.source
    source.fetcher='playwright'; source.render_selector='article:has-text("Rendered")'
    result=SourceFetcher(h).page('https://example.com/article',source)
    assert b'Rendered main text' in result.content
    assert b'Rendered main text' not in result.raw_content
    assert h.calls==['https://example.com/article','https://example.com/app.js']


def test_browser_resource_failure_is_not_silent(harness):
    class HTTP:
        config=harness.app.http
        def get(self,url,*args,**kwargs):
            if url.endswith('/article'):
                return FetchResult(b'<script src="/missing.js"></script>',url,200,'text/html')
            raise FetchError('robots disallowed')
    source=harness.source; source.fetcher='playwright'
    with pytest.raises(FetchError):
        SourceFetcher(HTTP()).page('https://example.com/article',source)
