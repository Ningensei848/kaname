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


@pytest.mark.parametrize('redirect_kind', ['resource', 'resource_robots', 'initial_robots'])
def test_real_browser_gateway_blocks_redirect_before_external_request(harness, monkeypatch, redirect_kind):
    import httpx
    from techkb.fetcher import Fetcher
    monkeypatch.setattr('techkb.fetcher.safe_url', lambda url: url)
    calls = []
    def handler(request):
        calls.append(str(request.url))
        assert request.url.host != 'blocked.example', 'Forbidden host reached transport'
        redirect = ((redirect_kind == 'initial_robots' and request.url.host == 'example.com' and request.url.path == '/robots.txt') or
                    (redirect_kind == 'resource_robots' and request.url.host == 'cdn.example' and request.url.path == '/robots.txt') or
                    (redirect_kind == 'resource' and request.url.path == '/app.js'))
        if redirect:
            return httpx.Response(302, headers={'location': 'https://blocked.example/private'}, request=request)
        if request.url.path == '/robots.txt':
            return httpx.Response(404, request=request)
        if request.url.path == '/article':
            return httpx.Response(200, content=b'<article>test</article><script src="https://cdn.example/app.js"></script>', headers={'content-type':'text/html'}, request=request)
        raise AssertionError('Unexpected request')
    source = harness.source
    source.fetcher = 'playwright'; source.resource_domains = ['cdn.example']
    http = Fetcher(harness.app.http, httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda _: None)
    with pytest.raises(FetchError):
        SourceFetcher(http).page('https://example.com/article', source)
    assert calls and all('blocked.example' not in url for url in calls)
