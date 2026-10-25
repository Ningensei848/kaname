import json
import logging
from .composer import compose, word_count
from .preparation import prepared_articles
from .images import article_images
from ._receipts import build_receipt
from ._standard import StandardRequest, request_metadata
from .budget import validate_budget, request_reserve, measured_cost, validate_generation_mode, generation_allowance
from .dedupe import Dedupe
from .feeds import parse_feed
from .hashes import content_hash
from .html_cleaner import article_authors, canonical_url
from .pending import merge_pending
from .reporting import RunReport, now
from .state import State
from .fetcher import audit_url
from .extraction import parse_listing, relevance
from .batch import BatchManager, failure_diagnostics
from .usage import has_usage_record
from .standard_requests import StandardRequests, UnresolvedStandardRequest
from .discovery import KnownArticles
from .collection_progress import partition_known, completed_sources, failure_stop_reason, batch_submission_allowed

log = logging.getLogger(__name__)

class Pipeline:
    def __init__(self, app, sources, store, fetcher, converter, gemini=None, *, max_cost_usd=None, retry_standard_content=None):
        validate_generation_mode(app)
        self.max_cost_usd = validate_budget(app, max_cost_usd) if max_cost_usd is not None else None
        if retry_standard_content is not None:
            import re
            if (self.max_cost_usd is None or app.llm.mode != 'standard' or app.llm.max_calls_per_run != 1 or
                    not re.fullmatch(r'[0-9a-f]{64}', retry_standard_content)):
                raise ValueError('standard retry requires a digest and bounded single standard run')
            app.llm.retries = 0
        self.app, self.sources, self.store = app, sources, store
        self.fetcher, self.converter, self.gemini = fetcher, converter, gemini
        self.requests = StandardRequests(store, retry_standard_content)

    def _save_receipt(self, receipt, state, dedupe, report):
        row = receipt["row"]
        self.store.write(row["note_object"], receipt["note"].encode("utf-8"), "text/markdown; charset=utf-8")
        log.info("GCS note save success source=%s url=%s", row["source_id"], audit_url(row["source_url"]))
        # Never update known hashes before both Note and index are durable.
        state.append(row)
        dedupe.add(row)
        report.saved += 1
        report.count_source(row['source_id'], 'saved')

    def _recover_receipts(self, state, dedupe, report):
        for name in self.store.list('state/receipts/'):
            digest = name.rsplit('/', 1)[-1].removesuffix('.json')
            if digest in dedupe.content:
                continue
            receipt = json.loads(self.store.read(name))
            self._save_receipt(receipt, state, dedupe, report)
            report.recovered += 1
            report.count_source(receipt['row']['source_id'], 'recovered')
            if not has_usage_record(self.store, receipt.get('usage_run_id')):
                # Legacy receipts do not establish an original billing identity.
                report.llm_usage_unavailable += 1

    def run(self, dry_run=False):
        price = self.app.costs.prices.get(self.app.llm.model, {}).get(self.app.llm.mode)
        report = RunReport(dry_run=dry_run, llm_model=self.app.llm.model, llm_mode=self.app.llm.mode,
                           token_price=price.model_dump() if price else None,
                           max_cost_usd=str(self.max_cost_usd) if self.max_cost_usd is not None else None,
                           source_ids=[s.id for s in self.sources if s.enabled],
                           article_policy=self.app.processing.article_policy)
        state, candidates, done = None, None, set()
        batch, prepared, active = None, [], set()
        feeds_complete = {}
        run_budget = self.max_cost_usd
        try:
            state = State(self.store)
            dedupe = Dedupe(state.rows)
            previous = state.pending()
            report.pending_before = len(previous)
            if not dry_run:
                standard_blocked = self.requests.recover(self.app.categories, compose)
                self._recover_receipts(state, dedupe, report)
                batch = BatchManager(self.store, self.gemini)
                batch.settle(self._save_receipt, state, dedupe, report, done)
                active = batch.active_hashes()
                if standard_blocked:
                    raise UnresolvedStandardRequest()
                report.generation_budget = generation_allowance(self.store, self.app, report.started_at)
                if report.generation_budget is not None:
                    if report.generation_budget['reason']:
                        report.budget_stop_reason = report.generation_budget['reason']
                    else:
                        remaining = validate_budget(self.app, report.generation_budget['remaining_usd'])
                        run_budget = remaining if run_budget is None else min(run_budget, remaining)
                        report.max_cost_usd = str(run_budget)
            discovered = []
            for source in self.sources:
                if not source.enabled:
                    continue
                try:
                    if source.type == "rss":
                        feed = self.fetcher.get(str(source.feed_url), source.request_interval_seconds)
                        entries = parse_feed(feed.content, source, report.started_at, self.app.tracking_parameters)
                    else:
                        page = self._page(str(source.listing_url), source)
                        entries = parse_listing(page.content, page.url, source, report.started_at, self.app.tracking_parameters)
                    discovered.extend(entries)
                    report.discovered += len(entries)
                    report.count_source(source.id, 'discovered', len(entries))
                    feeds_complete[source.id] = {entry.url for entry in entries}
                except Exception as exc:
                    report.fail("feed", source.id, str(source.feed_url or source.listing_url), exc)
                    log.error("RSS failed source=%s error=%s", source.id, type(exc).__name__)
            candidates = merge_pending(previous, discovered, self.app.tracking_parameters)
            # Durably retain discovery before any paid work or a runner interruption.
            if not dry_run:
                state.save_pending(candidates)
            to_fetch = candidates
            new_only = self.app.processing.article_policy == 'new_only'
            if new_only:
                known = KnownArticles(state.rows, self.app.tracking_parameters)
                enabled = {s.id for s in self.sources if s.enabled}
                to_fetch, skipped = partition_known(candidates, known, enabled)
                done.update(candidate.url for candidate in skipped)
                report.known_articles_skipped += len(skipped)
            def can_fetch():
                return (dry_run or (report.budget_stop_reason not in
                        {'aggregate_usage_uncertain', 'aggregate_limit_reached'} and (not new_only or
                        report.llm_calls + len(prepared) < self.app.llm.max_calls_per_run)))
            attempted_content = set()
            with prepared_articles(self, to_fetch, dedupe.raw, can_continue=can_fetch) as articles:
                for candidate, source, article in articles:
                    stage = "fetch"
                    images = ()
                    response = None
                    log.info("article source=%s url=%s", source.id, audit_url(candidate.url))
                    try:
                        fetched = article.fetched
                        if fetched is None:
                            raise article.error
                        report.fetched += 1
                        if article.filter_reason:
                            report.filtered += 1
                            report.filter_reasons[article.filter_reason] = report.filter_reasons.get(article.filter_reason, 0) + 1
                            done.add(candidate.url)
                            continue
                        raw, rh = article.raw, article.rh
                        if rh in dedupe.raw and source.fetcher != "playwright":
                            report.raw_duplicates += 1
                            done.add(candidate.url)
                            log.info("raw duplicate")
                            continue
                        log.info("raw new")
                        stage = "convert"
                        if article.error is not None:
                            stage = article.stage
                            raise article.error
                        extracted, markdown = article.extracted, article.markdown
                        reason = relevance(source, candidate, markdown)
                        if reason:
                            report.filtered += 1
                            report.filter_reasons[reason] = report.filter_reasons.get(reason, 0) + 1
                            done.add(candidate.url)
                            continue
                        ch = content_hash(markdown)
                        if self.requests.retry_content and ch != self.requests.retry_content:
                            continue
                        if ch in dedupe.content:
                            report.content_duplicates += 1
                            done.add(candidate.url)
                            log.info("content duplicate")
                            continue
                        log.info("content new")
                        if ch in active:
                            continue
                        if dry_run:
                            report.would_enrich += 1
                            # In-memory deduplication only; no external mutation.
                            dedupe.raw.add(rh)
                            dedupe.content.add(ch)
                            continue
                        if report.llm_calls + len(prepared) >= self.app.llm.max_calls_per_run or ch in attempted_content:
                            continue
                        stage = "raw_save"
                        raw_enabled = source.store_raw_html if source.store_raw_html is not None else self.app.storage.store_raw_html
                        if raw_enabled:
                            self.store.write(f"raw/{source.id}/{report.started_at[:4]}/{report.started_at[5:7]}/{rh}.html", raw, "text/html")
                        canon = canonical_url(fetched.content, fetched.url, self.app.tracking_parameters)
                        authors = article_authors(fetched.content)
                        truncated = len(markdown) > self.app.llm.max_input_chars
                        images = article_images(extracted, fetched.url, markdown[:self.app.llm.max_input_chars])
                        if self.app.llm.mode == "batch":
                            stage = "batch_prepare"
                            prepared.append(batch.prepare(candidate, source, markdown, canon, rh, ch, authors, images))
                            attempted_content.add(ch)
                            continue
                        if run_budget is not None:
                            if report.llm_usage_unavailable:
                                report.budget_stop_reason = "usage_uncertain"
                                break
                            metadata = request_metadata(candidate, source, truncated, authors, images)
                            reserve = request_reserve(self.gemini, metadata, markdown, price)
                            if measured_cost(report, price) + reserve > run_budget:
                                report.budget_deferred += 1
                                report.budget_stop_reason = "estimated_cost_limit"
                                continue
                        stage = "llm"
                        report.llm_calls += 1
                        attempted_content.add(ch)
                        context = dict(candidate=candidate.row(), source=source.model_dump(mode='json'),
                            canonical=canon, fetched_at=now(), raw_hash=rh, model=self.app.llm.model,
                            truncated=truncated, authors=authors, input_char_limit=self.app.llm.max_input_chars,
                            source_word_count=word_count(markdown), image_candidates=images)
                        request = StandardRequest(self.store, self.gemini, report, self.requests, ch, context)
                        try:
                            enrichment, usage = request.enrich(candidate, source, markdown, truncated, authors, images)
                        finally:
                            # Keep the original exception type and storage-failure stage.
                            stage = request.stage
                            response = getattr(self.gemini, "last_response", None)
                        log.info("LLM success")
                        stage = "compose"
                        fetched_at = context['fetched_at']
                        receipt = build_receipt(candidate, source, enrichment, markdown, canon, fetched_at,
                                                rh, ch, self.app.llm.model, truncated, authors, usage,
                                                input_char_limit=self.app.llm.max_input_chars,
                                                usage_run_id=report.run_id, compose_note=compose,
                                                image_candidates=images)
                        report.observe_images(len(images), len(enrichment.images), truncated)
                        stage = "receipt_save"
                        self.store.write(f"state/receipts/{ch}.json", json.dumps(receipt, ensure_ascii=False).encode("utf-8"), "application/json")
                        stage = 'standard_response_save'
                        self.requests.complete(request.record)
                        stage = "note_or_index_save"
                        self._save_receipt(receipt, state, dedupe, report)
                        done.add(candidate.url)
                        if run_budget is not None and report.llm_usage_unavailable:
                            report.budget_stop_reason = "usage_uncertain"
                            break
                        if run_budget is not None and measured_cost(report, price) > run_budget:
                            report.budget_stop_reason = "measured_cost_limit"
                            break
                    except Exception as exc:
                        diagnostics = failure_diagnostics(exc, stage, response,
                            image_candidates=images if stage == "compose" else None) if stage in {"llm", "compose"} else None
                        report.fail_recorded(stage, source.id, candidate.url, type(exc).__name__, diagnostics)
                        if stage == "llm":
                            report.llm_failed += 1
                        log.error("%s failed source=%s error=%s", stage, source.id, type(exc).__name__)
                        stop = failure_stop_reason(stage, run_budget is not None)
                        if stop:
                            if stop == 'generation_failed':
                                report.budget_stop_reason = stop
                            break
                        if stage == 'llm' and response is None:
                            report.budget_stop_reason = 'standard_request_unresolved'
                            break
            if prepared and not dry_run and batch_submission_allowed(report.failures):
                batch.submit(prepared, self.app, report)
            if self.requests.retry_content and not self.requests.retried:
                raise ValueError('standard retry target not found')
        except Exception as exc:
            report.fail("state_or_recovery", "", "", exc)
            log.error("state/recovery failed error=%s", type(exc).__name__)
        finally:
            remaining = [c for c in candidates if c.url not in done] if candidates is not None else None
            report.pending_after = len(remaining) if remaining is not None else report.pending_before
            if not dry_run and state is not None and remaining is not None:
                try:
                    state.save_pending(remaining)
                except Exception as exc:
                    report.fail("pending_save", "", "", exc)
            if candidates is not None:
                report.source_completed_ids = completed_sources(feeds_complete, candidates, done)
            report.finish()
            if not dry_run:
                try:
                    self.store.write(f"runs/{report.started_at[:4]}/{report.started_at[5:7]}/{report.run_id}.json",
                                     report.to_bytes(), "application/json")
                except Exception as exc:
                    report.fail("report_save", "", "", exc)
                    report.finish()
            log.info("run_report %s", report.to_bytes().decode("utf-8"))
        return report

    def _page(self, url, source):
        if hasattr(self.fetcher, "page"):
            return self.fetcher.page(url, source)
        return self.fetcher.get(url, source.request_interval_seconds, html=True)
