"""Discovery skips only durable success; generation limits also bound HTTP work."""
import pytest

from techkb._cli_arguments import parse_args, validate_args
from techkb.config import AppConfig
from techkb.discovery import KnownArticles
from techkb.pending import Candidate
from techkb.state import State


def enable(h, workers=1):
    h.app.processing.article_policy = 'new_only'
    h.app.processing.workers = workers
    calls = []
    original = h.fetcher.get
    def get(url, *args, **kwargs):
        calls.append(url)
        return original(url, *args, **kwargs)
    h.fetcher.get = get
    return calls


def test_known_url_is_not_requested_even_if_body_changed_or_became_unavailable(harness):
    h = harness; calls = enable(h)
    assert h.pipeline.run().saved == 1
    before = dict(h.store.data); calls.clear()
    h.fetcher.pages['https://example.com/a'] = OSError('source unavailable')
    r = h.pipeline.run()
    assert r.status == 'success' and r.known_articles_skipped == 1 and r.fetched == r.llm_calls == 0
    assert calls == ['https://example.com/feed.xml']
    assert r.source_completed_ids == ['example'] and r.pending_after == 0
    assert all(h.store.data[name] == data for name, data in before.items() if name.startswith(('notes/', 'state/receipts/', 'state/index/')))


def test_original_and_canonical_urls_are_normalized_source_specific_aliases():
    rows = [dict(status='success', source_id='one', source_url='https://example.com/original?fbclid=old', canonical_url='https://example.com/canonical'),
            dict(status='failed', source_id='one', source_url='https://example.com/failed', canonical_url='https://example.com/failed')]
    known = KnownArticles(rows, ['fbclid'])
    def candidate(source, url):return Candidate('2026-10-12T00:00:00Z', source, url)
    assert known.contains(candidate('one', 'https://example.com/original?fbclid=new#fragment'))
    assert known.contains(candidate('one', 'https://example.com/canonical'))
    assert not known.contains(candidate('two', 'https://example.com/canonical'))
    assert not known.contains(candidate('one', 'https://example.com/failed'))


@pytest.mark.parametrize('workers', [1, 2, 4])
def test_zero_generation_limit_only_discovers_and_retains_unknown_work(harness, workers):
    h = harness; calls = enable(h, workers)
    h.app.llm.max_calls_per_run = 0
    h.fetcher.pages = {f'https://example.com/{n}': OSError('must not fetch') for n in range(10)}
    r = h.pipeline.run()
    assert r.status == 'success' and r.discovered == r.pending_after == 10
    assert r.fetched == r.llm_calls == 0 and not r.source_completed_ids
    assert calls == ['https://example.com/feed.xml']
    assert len(State(h.store).pending()) == 10 and not h.sdk.calls


@pytest.mark.parametrize('workers', [1, 2, 4])
def test_limit_stops_prefetch_without_dropping_unconsumed_candidates(harness, workers):
    h = harness; calls = enable(h, workers); h.app.llm.max_calls_per_run = 1
    h.fetcher.pages = {f'https://example.com/{n}': f'<article>Article {n}</article>'.encode() for n in range(10)}
    r = h.pipeline.run()
    article_calls = [u for u in calls if not u.endswith('feed.xml')]
    assert r.status == 'success' and r.saved == r.llm_calls == r.fetched == 1
    assert len(article_calls) <= workers and r.pending_after == 9
    assert len(State(h.store).pending()) == 9 and len(h.sdk.calls) == 1
    calls.clear()
    again = h.pipeline.run()
    assert again.saved == 1 and again.known_articles_skipped == 1 and again.pending_after == 8
    assert 'https://example.com/0' not in calls
    assert [row['source_url'] for row in State(h.store).rows] == ['https://example.com/0', 'https://example.com/1']


def test_receipt_recovery_precedes_url_skip_and_never_regenerates(harness):
    h = harness; calls = enable(h)
    h.store.fail_prefix = 'state/index/'
    assert h.pipeline.run().status == 'failed'
    h.store.fail_prefix = None; calls.clear()
    r = h.pipeline.run()
    assert r.status == 'success' and r.recovered == r.saved == r.known_articles_skipped == 1
    assert r.llm_calls == r.fetched == 0 and len(h.sdk.calls) == 1
    assert calls == ['https://example.com/feed.xml']


def test_failed_generation_stays_unknown_and_is_retried(harness):
    h = harness; calls = enable(h); h.sdk.error = OSError('failed generation')
    assert h.pipeline.run().status == 'failed' and len(State(h.store).pending()) == 1
    h.sdk.error = None; calls.clear()
    r = h.pipeline.run()
    assert r.status == 'success' and r.saved == 1 and r.known_articles_skipped == 0
    assert 'https://example.com/a' in calls


def test_recheck_explicitly_detects_same_url_edits(harness):
    h = harness; enable(h)
    assert h.pipeline.run().saved == 1
    h.fetcher.pages['https://example.com/a'] = b'<article>Revised article</article>'
    assert h.pipeline.run().known_articles_skipped == 1 and len(h.sdk.calls) == 1
    h.app.processing.article_policy = 'recheck'
    r = h.pipeline.run()
    assert r.saved == 1 and len(h.sdk.calls) == 2 and len(State(h.store).rows) == 2


def test_dry_run_inspects_unknown_without_writing_or_using_paid_limit(harness):
    h = harness; calls = enable(h); assert h.pipeline.run().saved == 1
    h.app.llm.max_calls_per_run = 0
    h.fetcher.pages['https://example.com/b'] = b'<article>New article</article>'
    before = dict(h.store.data); sdk_calls = len(h.sdk.calls); calls.clear()
    r = h.pipeline.run(dry_run=True)
    assert r.known_articles_skipped == r.would_enrich == r.fetched == 1
    assert 'https://example.com/a' not in calls and 'https://example.com/b' in calls
    assert h.store.data == before and len(h.sdk.calls) == sdk_calls


@pytest.mark.parametrize('command', ['run', 'dry-run'])
def test_cli_recheck_override(command):
    app = AppConfig(); app.processing.article_policy = 'new_only'
    validate_args(parse_args([command, '--recheck-known']), app)
    assert app.processing.article_policy == 'recheck'


def test_cli_recheck_rejects_inspection_command():
    with pytest.raises(ValueError, match='run or dry-run'):
        validate_args(parse_args(['audit-state', '--recheck-known']), AppConfig())


@pytest.mark.parametrize('workers', [1, 2])
def test_batch_prepared_requests_obey_fetch_limit_and_settle_before_skipping(harness, workers):
    from test_batch import setup
    h = harness; calls = enable(h, workers); sdk = setup(h)
    h.app.llm.max_calls_per_run = 1
    h.fetcher.pages = {f'https://example.com/{n}': f'<article>Article {n}</article>'.encode() for n in range(10)}
    r = h.pipeline.run()
    assert r.status == 'success' and r.batch_submitted == 1 and len(sdk.created[0]['src']) == 1
    assert len([u for u in calls if not u.endswith('feed.xml')]) <= workers
    assert r.pending_after == 10
    sdk.finish(); h.app.llm.max_calls_per_run = 0; calls.clear()
    settled = h.pipeline.run()
    assert settled.status == 'success' and settled.batch_saved == settled.saved == settled.known_articles_skipped == 1
    assert settled.pending_after == 9 and len(sdk.created) == 1
    assert calls == ['https://example.com/feed.xml']
