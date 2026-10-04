"""Read-only consistency checks for Phase 1 acceptance."""
import json
import re
from pathlib import PurePosixPath

import yaml

from .state import State


def audit_run(store, run_id, max_calls=30, expected_success_before=None):
    """Compare a persisted run with quiescent state without exposing article data."""
    if not re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{8}", run_id or ""):
        raise ValueError("invalid run id")
    if expected_success_before is not None and expected_success_before < 0:
        raise ValueError("invalid baseline")
    audit = audit_state(store)
    issues = []
    name = f"runs/{run_id[:4]}/{run_id[4:6]}/{run_id}.json"
    data = store.read(name)
    if data is None:
        return {"status": "failed", "audit": audit, "issues": [{"code": "missing_report"}]}
    try:
        report = json.loads(data)
    except (ValueError, UnicodeError):
        return {"status": "failed", "audit": audit, "issues": [{"code": "invalid_report"}]}
    fields = ("llm_calls", "llm_http_attempts", "llm_processed", "llm_failed", "saved",
              "recovered", "pending_before", "pending_after", "total_input_tokens",
              "total_output_tokens", "total_thinking_tokens", "llm_usage_unavailable")
    if isinstance(report, dict):
        fields += tuple(k for k in ("batch_submitted", "batch_saved", "batch_failed", "batch_jobs_pending") if k in report)
    if not isinstance(report, dict) or any(type(report.get(k)) is not int or report[k] < 0 for k in fields):
        return {"status": "failed", "audit": audit, "issues": [{"code": "invalid_report"}]}
    if report.get("run_id") != run_id or report.get("status") != "success" or report.get("dry_run") is not False or report.get("failures") != [] or report.get("record_kind", "collection") != "collection":
        issues.append({"code": "unsuccessful_report"})
    if report["llm_calls"] + report.get("batch_submitted", 0) > max_calls or report["llm_failed"] or report.get("batch_failed", 0) or report["llm_processed"] != report["llm_calls"]:
        issues.append({"code": "invalid_llm_counts"})
    if report["saved"] != report["llm_processed"] + report["recovered"] + report.get("batch_saved", 0):
        issues.append({"code": "invalid_saved_count"})
    if report["pending_after"] != audit["pending"]:
        issues.append({"code": "pending_mismatch"})
    if expected_success_before is not None and audit["success_rows"] - expected_success_before != report["saved"]:
        issues.append({"code": "index_delta_mismatch"})
    return {"status": "success" if audit["status"] == "success" and not issues else "failed",
            "run_id": run_id, "report": {k: report[k] for k in fields}, "audit": audit, "issues": issues}


def audit_state(store):
    state = State(store)
    issues = []
    rows = [row for row in state.rows if row["status"] == "success"]
    if not rows:
        issues.append({"code": "no_success_rows"})
    seen = set()
    indexed_notes = set()
    for number, row in enumerate(rows, 1):
        def issue(code):
            # Do not expose article text, titles or URLs in diagnostics.
            issues.append({"row": number, "code": code})

        digest = row["content_sha256"]
        if digest in seen:
            issue("duplicate_content_hash")
        seen.add(digest)
        name = row["note_object"]
        indexed_notes.add(name)
        path = PurePosixPath(name)
        if (not name.startswith("notes/") or ".." in path.parts or
                "\\" in name or path.suffix != ".md"):
            issue("invalid_note_path")
            continue
        note = store.read(name)
        if note is None:
            issue("missing_note")
        else:
            try:
                text = note.decode("utf-8")
                frontmatter = re.match(r"\A---\r?\n(.*?)^---\r?$", text, re.MULTILINE | re.DOTALL)
                metadata = yaml.safe_load(frontmatter[1]) if frontmatter else None
                if not isinstance(metadata, dict):
                    issue("invalid_frontmatter")
                elif any(metadata.get(key) != row[key] for key in
                         ("raw_html_sha256", "content_sha256")):
                    issue("note_hash_mismatch")
                if re.search(r"^## 原文\s*$", text, re.MULTILINE):
                    issue("legacy_original_section")
            except (UnicodeError, yaml.YAMLError):
                issue("invalid_note")
        data = store.read(f"state/receipts/{digest}.json")
        if data is None:
            issue("missing_receipt")
            continue
        try:
            receipt = json.loads(data)
            if not isinstance(receipt, dict) or not isinstance(receipt.get("row"), dict) or not isinstance(receipt.get("note"), str):
                issue("invalid_receipt")
                continue
            if any(str(receipt["row"].get(key, "")) != value for key, value in row.items()):
                issue("receipt_row_mismatch")
            if note is not None and receipt["note"].encode("utf-8") != note:
                issue("receipt_note_mismatch")
        except (ValueError, UnicodeError):
            issue("invalid_receipt")
    unindexed = sum(name.endswith(".json") and PurePosixPath(name).stem not in seen
                    for name in store.list("state/receipts/"))
    if unindexed:
        issues.append({"code": "unindexed_receipts", "count": unindexed})
    unindexed_notes = sum(name.endswith(".md") and name not in indexed_notes
                          for name in store.list("notes/"))
    if unindexed_notes:
        issues.append({"code": "unindexed_notes", "count": unindexed_notes})
    return {"status": "failed" if issues else "success", "success_rows": len(rows),
            "pending": len(state.pending()),
            "truncated_rows": sum(row.get("llm_input_truncated", "").casefold() == "true" for row in rows),
            "issues": issues}
