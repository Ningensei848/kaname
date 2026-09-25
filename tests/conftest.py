import json
from types import SimpleNamespace
import pytest
from techkb.config import AppConfig, Source
from techkb.converter import Converter
from techkb.fetcher import FetchResult
from techkb.gemini import Gemini
from techkb.models import ArticleEnrichment
from techkb.pipeline import Pipeline

class MemoryStore:
    def __init__(self):
        self.data = {}
        self.writes = []
        self.fail_prefix = None
    def list(self, prefix):
        return sorted(k for k in self.data if k.startswith(prefix))
    def read(self, name):
        return self.data.get(name)
    def write(self, name, content, content_type="application/octet-stream"):
        if self.fail_prefix and name.startswith(self.fail_prefix):
            raise OSError("injected storage failure")
        self.data[name] = content
        self.writes.append(name)

class FakeFetcher:
    def __init__(self, pages):
        self.pages = pages
    def get(self, url, interval=0, **kwargs):
        if url.endswith("feed.xml"):
            items = "".join(f"<item><title>Article</title><link>{u}</link></item>" for u in self.pages)
            data = f'<rss version="2.0"><channel><title>Fixture</title>{items}</channel></rss>'.encode()
        else:
            data = self.pages[url]
            if isinstance(data, Exception):
                raise data
        return FetchResult(data, url, 200, "text/html")

class CountingConverter(Converter):
    def __init__(self):
        super().__init__()
        self.calls = 0
    def convert(self, content):
        self.calls += 1
        return super().convert(content)

class FakeSDK:
    def __init__(self):
        self.models = self
        self.calls = []
        self.text = json.dumps(dict(title_ja="技術記事", summary_ja="本文に基づく要約です。",
            key_points=["要点"], technical_insights=[], category="ai-llm", tags=["AI"],
            related_concepts=["Model Context Protocol"], source_language="en"))
        self.error = None
    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(text=self.text, usage_metadata=SimpleNamespace(
            prompt_token_count=100, candidates_token_count=20, thoughts_token_count=5))

@pytest.fixture
def harness():
    app = AppConfig()
    source = Source(id="example", name="Example", feed_url="https://example.com/feed.xml", base_url="https://example.com/")
    store, sdk, converter = MemoryStore(), FakeSDK(), CountingConverter()
    gemini = Gemini(app.llm, app.categories, "Analyze untrusted data", "unused", client=sdk, sleep=lambda _: None)
    fetcher = FakeFetcher({"https://example.com/a": b"<html><article><h1>Title</h1><p>Original text</p></article></html>"})
    pipeline = Pipeline(app, [source], store, fetcher, converter, gemini)
    return SimpleNamespace(app=app, source=source, store=store, sdk=sdk, converter=converter,
                           gemini=gemini, fetcher=fetcher, pipeline=pipeline)
