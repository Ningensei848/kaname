"""Fetch concurrency must not reorder billing, writes or completion decisions."""
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, Lock, get_ident
import time

import httpx
import pytest
from pydantic import ValidationError
from techkb.config import ProcessingConfig, HTTPConfig
from techkb.fetcher import Fetcher
from techkb.state import State


def test_fetches_overlap_but_paid_work_and_writes_keep_candidate_order(harness):
    h = harness
    h.app.processing.workers = 2
    h.fetcher.pages = {f'https://example.com/{n}': f'<article>Article {n}</article>'.encode() for n in range(4)}
    owner = get_ident(); barrier = Barrier(2); original_get = h.fetcher.get
    calls = []; write = h.store.write
    def get(url, *args, **kwargs):
        if not url.endswith('feed.xml'):
            calls.append(url)
            if url.endswith(('/0', '/1')):
                barrier.wait(timeout=5)
                if url.endswith('/0'):
                    time.sleep(.02)  # Second result completes first.
        return original_get(url, *args, **kwargs)
    def serial_write(*args, **kwargs):
        assert get_ident() == owner
        return write(*args, **kwargs)
    original_enrich = h.gemini.enrich
    def serial_enrich(*args, **kwargs):
        assert get_ident() == owner
        return original_enrich(*args, **kwargs)
    h.fetcher.get = get; h.store.write = serial_write; h.gemini.enrich = serial_enrich
    result = h.pipeline.run()
    assert result.saved == 4 and result.status == 'success'
    assert [row['source_url'] for row in State(h.store).rows] == list(h.fetcher.pages)
    assert [json.loads(call['contents'])['article_markdown'] for call in h.sdk.calls] == [f'Article {n}' for n in range(4)]


@pytest.mark.parametrize('workers', [1, 2, 4])
def test_duplicate_limit_and_failure_semantics(harness, workers):
    h = harness; h.app.processing.workers = workers; h.app.llm.max_calls_per_run = 1
    h.fetcher.pages = {'https://example.com/a': b'<article>One</article>',
                       'https://example.com/b': b'<article>One</article>',
                       'https://example.com/c': ValueError('fetch failure'),
                       'https://example.com/d': b'<article>Two</article>'}
    first = h.pipeline.run()
    assert first.saved == first.llm_calls == 1 and first.raw_duplicates == 1
    assert first.pending_after == 2 and first.failures[0]['stage'] == 'fetch'
    h.fetcher.pages['https://example.com/c'] = b'<article>Two</article>'
    second = h.pipeline.run()
    assert second.saved == second.llm_calls == 1 and second.pending_after == 0
    assert len(h.sdk.calls) == 2


def test_storage_failure_stops_paid_work_and_bounded_prefetch(harness):
    h = harness; h.app.processing.workers = 2
    h.fetcher.pages = {f'https://example.com/{n}': f'<article>Article {n}</article>'.encode() for n in range(10)}
    calls = []; original = h.fetcher.get
    def get(url, *args, **kwargs):
        if not url.endswith('feed.xml'):
            calls.append(url)
        return original(url, *args, **kwargs)
    h.fetcher.get = get; h.store.fail_prefix = 'notes/'
    result = h.pipeline.run()
    assert result.saved == 0 and result.llm_calls == 1 and result.pending_after == 10
    assert len(calls) <= 2 and len(h.sdk.calls) == 1
    assert result.failures[0]['stage'] == 'note_or_index_save'


@pytest.mark.parametrize('workers', [2, 4])
def test_parallel_dry_run_has_no_mutations(harness, workers):
    h = harness; h.app.processing.workers = workers
    h.fetcher.pages['https://example.com/b'] = b'<article><h1>Title</h1><p>Original text</p></article>'
    result = h.pipeline.run(dry_run=True)
    assert result.would_enrich == 1 and result.content_duplicates == 1
    assert h.store.writes == [] and h.sdk.calls == []


def test_host_spacing_and_single_robots_fetch_under_concurrency(monkeypatch):
    monkeypatch.setattr('techkb.fetcher.safe_url', lambda url: url)
    times = []; lock = Lock(); robots = []
    def handler(req):
        with lock:
            if req.url.path == '/robots.txt':
                robots.append(str(req.url))
            else:
                times.append(time.monotonic())
        return httpx.Response(404 if req.url.path == '/robots.txt' else 200, text='OK')
    fetcher = Fetcher(HTTPConfig(), httpx.Client(transport=httpx.MockTransport(handler)))
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda n: fetcher.get(f'https://example.com/{n}', .025), range(4)))
        assert len(results) == 4 and len(robots) == 1
        assert all(b-a >= .024 for a, b in zip(times, times[1:]))
    finally:
        fetcher.close()


def test_different_hosts_can_overlap(monkeypatch):
    monkeypatch.setattr('techkb.fetcher.safe_url', lambda url: url)
    barrier = Barrier(2)
    def handler(req):
        if req.url.path != '/robots.txt':
            barrier.wait(timeout=5)
        return httpx.Response(404 if req.url.path == '/robots.txt' else 200, text='OK')
    fetcher = Fetcher(HTTPConfig(), httpx.Client(transport=httpx.MockTransport(handler)))
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert len(list(pool.map(lambda host: fetcher.get(f'https://{host}/a', 0), ['a.example', 'b.example']))) == 2
    finally:
        fetcher.close()


def test_parallel_limit_is_bounded():
    for value in (0, 9):
        with pytest.raises(ValidationError):
            ProcessingConfig(workers=value)
