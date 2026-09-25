from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
from uuid import uuid4
from .fetcher import audit_url

def now():
    return datetime.now(timezone.utc).isoformat()

@dataclass
class RunReport:
    run_id: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:8])
    started_at: str = field(default_factory=now)
    finished_at: str = ""
    status: str = "running"
    dry_run: bool = False
    discovered: int = 0
    pending_before: int = 0
    fetched: int = 0
    raw_duplicates: int = 0
    content_duplicates: int = 0
    llm_calls: int = 0
    llm_http_attempts: int = 0
    llm_processed: int = 0
    llm_failed: int = 0
    llm_usage_unavailable: int = 0
    would_enrich: int = 0
    saved: int = 0
    recovered: int = 0
    pending_after: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_thinking_tokens: int = 0
    failures: list[dict] = field(default_factory=list)

    def fail(self, stage, source_id, url, exc):
        # Exception text can contain request bodies, keys or untrusted markup.
        self.failures.append({"stage": stage, "source_id": source_id,
                              "url": audit_url(url), "error_type": type(exc).__name__})

    def finish(self):
        self.finished_at = now()
        self.status = "failed" if self.failures else "success"

    def to_bytes(self):
        return json.dumps(asdict(self), ensure_ascii=False, indent=2).encode("utf-8")
