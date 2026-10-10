"""One standard request, with durable usage and its current failure stage."""
from .usage import checkpoint
from .images import image_context


class StandardRequest:
    def __init__(self, store, gemini, report):
        self.store, self.gemini, self.report = store, gemini, report
        self.stage = "usage_reserve"

    def enrich(self, candidate, source, markdown, truncated, authors, image_candidates=()):
        report, gemini = self.report, self.gemini
        try:
            checkpoint(self.store, report, pending=True)
        except Exception:
            report.llm_calls -= 1  # No API request was made.
            raise
        self.stage = "llm"
        attempts_before = gemini.attempts
        try:
            enrichment = gemini.enrich({"title": candidate.title[:1000], "source": source.name,
                                       "authors": authors,
                                       "published_at": candidate.published_at,
                                       "image_candidates": image_context(image_candidates),
                                       "llm_input_truncated": truncated}, markdown)
        finally:
            usage = gemini.last_usage
            report.total_input_tokens += usage.input_tokens
            report.total_output_tokens += usage.output_tokens
            report.total_thinking_tokens += usage.thinking_tokens
            report.llm_http_attempts += gemini.attempts - attempts_before
            if not gemini.last_usage_available or gemini.attempts - attempts_before > 1:
                report.llm_usage_unavailable += 1
            self.stage = "usage_save"
            # Propagate storage failures so the pipeline stops further paid work.
            checkpoint(self.store, report, pending=False)
            self.stage = "llm"
        report.llm_processed += 1
        return enrichment, usage
