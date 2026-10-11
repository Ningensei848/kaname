"""Bounded, ordered fetch/convert workers. No state, reporting or paid operations."""
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass

from .fetcher import FetchResult
from .extraction import extract_main
from .hashes import raw_hash
from .html_cleaner import clean_html
from .normalize import normalize_markdown


@dataclass
class PreparedArticle:
    fetched: FetchResult | None = None
    raw: bytes = b''
    rh: str = ''
    extracted: bytes = b''
    markdown: str = ''
    stage: str = 'fetch'
    error: Exception | None = None


def prepare_article(pipeline, candidate, source, known_raw):
    result = PreparedArticle()
    try:
        result.fetched = pipeline._page(candidate.url, source)
        result.raw = result.fetched.raw_content if result.fetched.raw_content is not None else result.fetched.content
        result.rh = raw_hash(result.raw)
        if result.rh in known_raw and source.fetcher != 'playwright':
            return result
        result.stage = 'convert'
        result.extracted = (extract_main(result.fetched.content, source.content_selector)
                            if source.extract_main or source.content_selector else result.fetched.content)
        result.markdown = normalize_markdown(pipeline.converter.convert(clean_html(result.extracted)))
        if not result.markdown:
            raise ValueError('empty converted article')
    except Exception as exc:
        result.error = exc
    return result


@contextmanager
def prepared_articles(pipeline, candidates, known_raw):
    sources = {source.id: source for source in pipeline.sources if source.enabled}
    eligible = ((candidate, sources[candidate.source_id]) for candidate in candidates if candidate.source_id in sources)
    workers = pipeline.app.processing.workers
    if workers == 1:
        yield ((candidate, source, prepare_article(pipeline, candidate, source, known_raw))
               for candidate, source in eligible)
        return
    pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix='article')
    queue = deque()
    def submit():
        pair = next(eligible, None)
        if pair is not None:
            candidate, source = pair
            queue.append((candidate, source, pool.submit(prepare_article, pipeline, candidate, source, frozenset(known_raw))))
    def ordered():
        for _ in range(workers):
            submit()
        while queue:
            candidate, source, future = queue.popleft()
            yield candidate, source, future.result()
            # Refill only when the single writer continues after saving/billing.
            submit()
    try:
        yield ordered()
    finally:
        for _, _, future in queue:
            future.cancel()
        pool.shutdown(wait=True, cancel_futures=True)
