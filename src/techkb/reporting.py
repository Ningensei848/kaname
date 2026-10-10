from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
import re
from uuid import uuid4
from .fetcher import audit_url

SOURCE_COUNTERS = ('discovered', 'saved', 'recovered', 'batch_submitted', 'batch_saved')

def now():
    return datetime.now(timezone.utc).isoformat()

@dataclass
class RunReport:
    run_id: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:8])
    started_at: str = field(default_factory=now)
    finished_at: str = ""
    status: str = "running"
    dry_run: bool = False
    record_kind: str = "collection"
    llm_model: str = ""
    llm_mode: str = "standard"
    token_price: dict | None = None
    source_ids: list[str] = field(default_factory=list)
    source_completed_ids: list[str] = field(default_factory=list)
    discovered: int = 0
    pending_before: int = 0
    fetched: int = 0
    raw_duplicates: int = 0
    content_duplicates: int = 0
    filtered: int = 0
    filter_reasons: dict[str, int] = field(default_factory=dict)
    llm_calls: int = 0
    llm_http_attempts: int = 0
    llm_processed: int = 0
    llm_failed: int = 0
    llm_usage_unavailable: int = 0
    batch_submitted: int = 0
    batch_saved: int = 0
    batch_failed: int = 0
    batch_jobs_pending: int = 0
    would_enrich: int = 0
    saved: int = 0
    recovered: int = 0
    pending_after: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_thinking_tokens: int = 0
    source_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    failures: list[dict] = field(default_factory=list)

    def count_source(self, source_id, counter, count=1):
        if counter not in SOURCE_COUNTERS or type(count) is not int or count < 0:
            raise ValueError('invalid source counter')
        counters = self.source_counts.setdefault(source_id, dict.fromkeys(SOURCE_COUNTERS, 0))
        counters[counter] += count

    def fail(self, stage, source_id, url, exc):
        # Exception text can contain request bodies, keys or untrusted markup.
        self.fail_recorded(stage, source_id, url, type(exc).__name__)

    def fail_recorded(self, stage, source_id, url, error_type, diagnostics=None):
        # Replaying a durable Batch outcome must retain its original type without
        # reconstructing an exception from untrusted text.
        if not isinstance(error_type, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,79}", error_type):
            error_type = "Exception"
        failure = {"stage": stage, "source_id": source_id,
                   "url": audit_url(url), "error_type": error_type}
        if diagnostics is not None:
            failure["diagnostics"] = diagnostics
        self.failures.append(failure)

    def finish(self):
        self.finished_at = now()
        self.status = "failed" if self.failures else "success"

    def to_bytes(self):
        return json.dumps(asdict(self), ensure_ascii=False, indent=2).encode("utf-8")
