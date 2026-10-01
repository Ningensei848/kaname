"""Read-only consistency checks for Phase 1 acceptance."""
import json
import re
from pathlib import PurePosixPath

import yaml

from .state import State


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
            "pending": len(state.pending()), "issues": issues}
