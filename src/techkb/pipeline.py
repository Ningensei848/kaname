import json
import logging
from .composer import compose
from .images import article_images
from ._receipts import build_receipt
from ._standard import StandardRequest
from .dedupe import Dedupe
from .feeds import parse_feed
from .hashes import raw_hash, content_hash
from .html_cleaner import article_authors, clean_html, canonical_url
from .normalize import normalize_markdown
from .pending import merge_pending
from .reporting import RunReport, now
from .state import State
from .fetcher import audit_url
from .extraction import extract_main, parse_listing, relevance
from .batch import BatchManager
from .usage import checkpoint, has_usage_record

log = logging.getLogger(__name__)

class Pipeline:
    def __init__(self, app, sources, store, fetcher, converter, gemini=None):
        self.app, self.sources, self.store = app, sources, store
        self.fetcher, self.converter, self.gemini = fetcher, converter, gemini

    def _save_receipt(self, receipt, state, dedupe, report):
        row = receipt["row"]
        self.store.write(row["note_object"], receipt["note"].encode("utf-8"), "text/markdown; charset=utf-8")
        log.info("GCS note save success source=%s url=%s", row["source_id"], audit_url(row["source_url"]))
        # Never update known hashes before both Note and index are durable.
        state.append(row)
        dedupe.add(row)
        report.saved += 1

    def run(self, dry_run=False):
        price = self.app.costs.prices.get(self.app.llm.model, {}).get(self.app.llm.mode)
        report = RunReport(dry_run=dry_run, llm_model=self.app.llm.model, llm_mode=self.app.llm.mode,
                           token_price=price.model_dump() if price else None,
                           source_ids=[s.id for s in self.sources if s.enabled])
        state, candidates, done = None, None, set()
        batch, prepared, active = None, [], set()
        feeds_complete = {}
        try:
            state = State(self.store)
            dedupe = Dedupe(state.rows)
            previous = state.pending()
            report.pending_before = len(previous)
            if not dry_run:
                for name in self.store.list("state/receipts/"):
                    digest = name.rsplit("/", 1)[-1].removesuffix(".json")
                    if digest in dedupe.content:
                        continue
                    receipt = json.loads(self.store.read(name))
                    self._save_receipt(receipt, state, dedupe, report)
                    report.recovered += 1
                    if not has_usage_record(self.store, receipt.get("usage_run_id")):
                        # Legacy receipts have no original price/run identity.
                        # Do not invent a billing date or claim complete costs.
                        report.llm_usage_unavailable += 1
                batch = BatchManager(self.store, self.gemini)
                batch.settle(self._save_receipt, state, dedupe, report, done)
                active = batch.active_hashes()
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
                    feeds_complete[source.id] = {entry.url for entry in entries}
                except Exception as exc:
                    report.fail("feed", source.id, str(source.feed_url or source.listing_url), exc)
                    log.error("RSS failed source=%s error=%s", source.id, type(exc).__name__)
            candidates = merge_pending(previous, discovered, self.app.tracking_parameters)
            # Durably retain discovery before any paid work or a runner interruption.
            if not dry_run:
                state.save_pending(candidates)
            sources = {s.id: s for s in self.sources}
            attempted_content = set()
            for candidate in candidates:
                source = sources.get(candidate.source_id)
                if not source or not source.enabled:
                    continue  # Disabled/removed sources retain their pending entries.
                stage = "fetch"
                log.info("article source=%s url=%s", source.id, audit_url(candidate.url))
                try:
                    fetched = self._page(candidate.url, source)
                    report.fetched += 1
                    raw = fetched.raw_content if fetched.raw_content is not None else fetched.content
                    rh = raw_hash(raw)
                    if rh in dedupe.raw and source.fetcher != "playwright":
                        report.raw_duplicates += 1
                        done.add(candidate.url)
                        log.info("raw duplicate")
                        continue
                    log.info("raw new")
                    stage = "convert"
                    extracted = (extract_main(fetched.content, source.content_selector)
                                 if source.extract_main or source.content_selector else fetched.content)
                    markdown = normalize_markdown(self.converter.convert(clean_html(extracted)))
                    if not markdown:
                        raise ValueError("empty converted article")
                    reason = relevance(source, candidate, markdown)
                    if reason:
                        report.filtered += 1
                        report.filter_reasons[reason] = report.filter_reasons.get(reason, 0) + 1
                        done.add(candidate.url)
                        continue
                    ch = content_hash(markdown)
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
                    stage = "llm"
                    report.llm_calls += 1
                    attempted_content.add(ch)
                    request = StandardRequest(self.store, self.gemini, report)
                    try:
                        enrichment, usage = request.enrich(candidate, source, markdown, truncated, authors, images)
                    finally:
                        # Keep the original exception type and storage-failure stage.
                        stage = request.stage
                    log.info("LLM success")
                    stage = "compose"
                    fetched_at = now()
                    receipt = build_receipt(candidate, source, enrichment, markdown, canon, fetched_at,
                                            rh, ch, self.app.llm.model, truncated, authors, usage,
                                            input_char_limit=self.app.llm.max_input_chars,
                                            usage_run_id=report.run_id, compose_note=compose,
                                            image_candidates=images)
                    stage = "receipt_save"
                    self.store.write(f"state/receipts/{ch}.json", json.dumps(receipt, ensure_ascii=False).encode("utf-8"), "application/json")
                    stage = "note_or_index_save"
                    self._save_receipt(receipt, state, dedupe, report)
                    done.add(candidate.url)
                except Exception as exc:
                    report.fail(stage, source.id, candidate.url, exc)
                    if stage == "llm":
                        report.llm_failed += 1
                    log.error("%s failed source=%s error=%s", stage, source.id, type(exc).__name__)
                    if stage in {"receipt_save", "note_or_index_save", "raw_save", "usage_reserve", "usage_save"}:
                        break  # Stop paid work if durability is unavailable.
            if prepared and not dry_run and not any(f["stage"] in {"receipt_save", "note_or_index_save", "raw_save", "usage_reserve", "usage_save"} for f in report.failures):
                batch.submit(prepared, self.app, report)
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
                report.source_completed_ids = sorted(sid for sid in feeds_complete
                    if (feeds_complete[sid] | {c.url for c in candidates if c.source_id == sid}) <= done)
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
