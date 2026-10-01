import json
import logging
from .composer import compose
from .dedupe import Dedupe
from .feeds import parse_feed
from .hashes import raw_hash, content_hash
from .html_cleaner import article_authors, clean_html, canonical_url
from .normalize import normalize_markdown
from .pending import merge_pending
from .reporting import RunReport, now
from .state import State
from .fetcher import audit_url

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
        report = RunReport(dry_run=dry_run)
        state, candidates, done = None, None, set()
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
            discovered = []
            for source in self.sources:
                if not source.enabled:
                    continue
                try:
                    feed = self.fetcher.get(str(source.feed_url), source.request_interval_seconds)
                    entries = parse_feed(feed.content, source, report.started_at, self.app.tracking_parameters)
                    discovered.extend(entries)
                    report.discovered += len(entries)
                except Exception as exc:
                    report.fail("feed", source.id, str(source.feed_url), exc)
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
                    fetched = self.fetcher.get(candidate.url, source.request_interval_seconds, html=True)
                    report.fetched += 1
                    rh = raw_hash(fetched.content)
                    if rh in dedupe.raw:
                        report.raw_duplicates += 1
                        done.add(candidate.url)
                        log.info("raw duplicate")
                        continue
                    log.info("raw new")
                    stage = "convert"
                    markdown = normalize_markdown(self.converter.convert(clean_html(fetched.content)))
                    if not markdown:
                        raise ValueError("empty converted article")
                    ch = content_hash(markdown)
                    if ch in dedupe.content:
                        report.content_duplicates += 1
                        done.add(candidate.url)
                        log.info("content duplicate")
                        continue
                    log.info("content new")
                    if dry_run:
                        report.would_enrich += 1
                        # In-memory deduplication only; no external mutation.
                        dedupe.raw.add(rh)
                        dedupe.content.add(ch)
                        continue
                    if report.llm_calls >= self.app.llm.max_calls_per_run or ch in attempted_content:
                        continue
                    stage = "raw_save"
                    raw_enabled = source.store_raw_html if source.store_raw_html is not None else self.app.storage.store_raw_html
                    if raw_enabled:
                        self.store.write(f"raw/{report.started_at[:4]}/{report.started_at[5:7]}/{rh}.html", fetched.content, "text/html")
                    canon = canonical_url(fetched.content, fetched.url, self.app.tracking_parameters)
                    authors = article_authors(fetched.content)
                    truncated = len(markdown) > self.app.llm.max_input_chars
                    stage = "llm"
                    report.llm_calls += 1
                    attempted_content.add(ch)
                    attempts_before = self.gemini.attempts
                    try:
                        enrichment = self.gemini.enrich({"title": candidate.title[:1000], "source": source.name,
                                                        "authors": authors,
                                                        "published_at": candidate.published_at,
                                                        "llm_input_truncated": truncated}, markdown)
                    finally:
                        usage = self.gemini.last_usage
                        report.total_input_tokens += usage.input_tokens
                        report.total_output_tokens += usage.output_tokens
                        report.total_thinking_tokens += usage.thinking_tokens
                        report.llm_http_attempts += self.gemini.attempts - attempts_before
                        if not self.gemini.last_usage_available:
                            report.llm_usage_unavailable += 1
                    report.llm_processed += 1
                    log.info("LLM success")
                    stage = "compose"
                    fetched_at = now()
                    note_object, note = compose(candidate, source, enrichment, markdown, canon, fetched_at,
                                                rh, ch, self.app.llm.model, truncated, authors,
                                                input_char_limit=self.app.llm.max_input_chars)
                    row = dict(processed_at=fetched_at, source_id=source.id, source_url=candidate.url,
                               canonical_url=canon, published_at=candidate.published_at, raw_html_sha256=rh,
                               content_sha256=ch, status="success", note_object=note_object,
                               llm_model=self.app.llm.model, input_tokens=usage.input_tokens,
                               output_tokens=usage.output_tokens, thinking_tokens=usage.thinking_tokens,
                               llm_input_truncated=str(truncated).lower())
                    receipt = {"row": row, "note": note}
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
                    if stage in {"receipt_save", "note_or_index_save", "raw_save"}:
                        break  # Stop paid work if durability is unavailable.
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
