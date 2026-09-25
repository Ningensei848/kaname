"""Offline E2E: real CLI, Fetcher, feed parser, MarkItDown, Gemini validation, state."""
from pathlib import Path
import httpx
from techkb import cli
from techkb.fetcher import Fetcher
from techkb.state import State

ROOT = Path(__file__).resolve().parents[1]

def prepare(monkeypatch, harness):
    h = harness
    article = (ROOT / 'tests/fixtures/article.html').read_bytes()
    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(404)
        if request.url.path.endswith('feed.xml'):
            return httpx.Response(200, text='<feed xmlns="http://www.w3.org/2005/Atom"><title>Fixture</title><entry><id>1</id><title>Release</title><link href="https://example.com/article"/></entry></feed>', headers={'content-type':'application/atom+xml'})
        return httpx.Response(200, content=article, headers={'content-type':'text/html'})
    monkeypatch.setattr('techkb.fetcher.safe_url', lambda url: url)
    monkeypatch.setattr(cli, 'load_config', lambda *args: (h.app, [h.source]))
    h.source.request_interval_seconds = 0
    monkeypatch.setattr(cli, 'GCSStore', lambda *args: h.store)
    monkeypatch.setattr(cli, 'Fetcher', lambda config: Fetcher(config, httpx.Client(transport=httpx.MockTransport(handler))))
    monkeypatch.setattr(cli, 'Gemini', lambda *args: h.gemini)
    monkeypatch.setattr(h.gemini, 'close', lambda: None)
    monkeypatch.setenv('GEMINI_API_KEY', 'fixture-not-a-real-key')
    return ['--config', str(ROOT / 'config/app.yaml')]

def test_cli_end_to_end_twice(monkeypatch, harness):
    args = prepare(monkeypatch, harness)
    assert cli.main(['run', *args]) == 0
    assert cli.main(['run', *args]) == 0
    assert len(harness.sdk.calls) == 1
    assert len(State(harness.store).rows) == 1
    assert len(harness.store.list('notes/')) == 1
    assert len(harness.store.list('runs/')) == 2
    assert not State(harness.store).pending()

def test_cli_dry_run(monkeypatch, harness):
    args = prepare(monkeypatch, harness)
    monkeypatch.delenv('GEMINI_API_KEY')
    assert cli.main(['dry-run', *args]) == 0
    assert harness.store.writes == []
    assert harness.sdk.calls == []
