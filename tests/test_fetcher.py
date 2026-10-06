import httpx
import pytest
from techkb.config import HTTPConfig
from techkb.fetcher import Fetcher, FetchError

def test_robots_blocks_article(monkeypatch):
    monkeypatch.setattr('techkb.fetcher.safe_url', lambda u: u)
    calls = []
    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, text='User-agent: *\nDisallow: /private', request=request)
    f = Fetcher(HTTPConfig(), httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda _:None)
    with pytest.raises(FetchError):
        f.get('https://example.com/private', 0)
    assert calls == ['/robots.txt']

def test_stream_size_bound(monkeypatch):
    monkeypatch.setattr('techkb.fetcher.safe_url', lambda u: u)
    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(404, request=request)
        return httpx.Response(200, content=b'x'*20, headers={'Content-Type':'text/html'}, request=request)
    f = Fetcher(HTTPConfig(max_response_bytes=10), httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(FetchError):
        f.get('https://example.com/a', 0, html=True)

def test_retries_429_then_success(monkeypatch):
    monkeypatch.setattr('techkb.fetcher.safe_url', lambda u: u)
    calls = []
    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(404, request=request)
        calls.append(request.url.path)
        return httpx.Response(429 if len(calls)==1 else 200, content=b'<p>ok</p>', headers={'Content-Type':'text/html'}, request=request)
    f = Fetcher(HTTPConfig(), httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda _:None)
    assert f.get('https://example.com/a', 0, html=True).status == 200
    assert len(calls) == 2


@pytest.mark.parametrize('redirect_from', ['/article', '/robots.txt'])
def test_host_policy_blocks_redirect_before_dns_or_transport(monkeypatch, redirect_from):
    checked, calls = [], []
    monkeypatch.setattr('techkb.fetcher.safe_url', lambda url: checked.append(url))
    def handler(request):
        calls.append(str(request.url))
        if request.url.path == redirect_from:
            return httpx.Response(302, headers={'location': 'https://blocked.example/private'}, request=request)
        return httpx.Response(404, request=request)
    f = Fetcher(HTTPConfig(), httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda _: None)
    with pytest.raises(FetchError, match='outside allowed domains'):
        f.get('https://example.com/article', 0, allowed_hosts={'example.com'})
    assert checked and calls
    assert all('blocked.example' not in url for url in checked + calls)


def test_explicit_allowed_redirect_checks_destination_robots(monkeypatch):
    monkeypatch.setattr('techkb.fetcher.safe_url', lambda url: url)
    calls = []
    def handler(request):
        calls.append(str(request.url))
        if request.url.host == 'example.com' and request.url.path == '/article':
            return httpx.Response(302, headers={'location': 'https://cdn.example/asset'}, request=request)
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='User-agent: *\nDisallow: /asset' if request.url.host == 'cdn.example' else '', request=request)
        raise AssertionError('Disallowed destination asset requested')
    f = Fetcher(HTTPConfig(), httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda _: None)
    with pytest.raises(FetchError, match='robots disallows'):
        f.get('https://example.com/article', 0, allowed_hosts={'example.com', 'cdn.example'})
    assert calls == ['https://example.com/robots.txt', 'https://example.com/article', 'https://cdn.example/robots.txt']
