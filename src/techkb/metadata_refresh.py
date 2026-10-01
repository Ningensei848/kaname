"""Refresh saved Note metadata without invoking the LLM."""
import json
import re
from pathlib import PurePosixPath

import yaml

from .composer import concept, inline
from .html_cleaner import article_authors
from .state import State


FRONTMATTER = re.compile(r"\A---\r?\n(.*?)^---\r?\n", re.MULTILINE | re.DOTALL)


def refresh_note_metadata(note, authors, published_at):
    match = FRONTMATTER.match(note)
    metadata = yaml.safe_load(match[1]) if match else None
    if not isinstance(metadata, dict):
        raise ValueError("invalid frontmatter")
    names = list(dict.fromkeys(c for value in authors if (c := concept(value))))
    if names:
        metadata["author"] = [f"[[{name}]]" for name in names]
    metadata["published"] = published_at[:10] if published_at else None
    body = note[match.end():]
    if names:
        body, author_count = re.subn(r"(?m)^- Author: .*?$", "- Author: " + inline(", ".join(names)), body, count=1)
        if author_count != 1:
            raise ValueError("missing author field")
    published = inline(metadata["published"] or "（取得なし）")
    body, published_count = re.subn(r"(?m)^- Published: .*?$", "- Published: " + published, body, count=1)
    if published_count != 1:
        raise ValueError("missing published field")
    front = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).rstrip()
    return f"---\n{front}\n---\n{body}"


class MetadataRefresh:
    def __init__(self, store, fetcher, sources):
        self.store, self.fetcher = store, fetcher
        self.sources = {source.id: source for source in sources}

    def run(self, apply=False):
        result = {"status": "success", "apply": apply, "success_rows": 0,
                  "planned": 0, "updated": 0, "unchanged": 0,
                  "no_authors": 0, "failures": []}
        changes = []
        state = State(self.store)
        rows = [row for row in state.rows if row["status"] == "success"]
        result["success_rows"] = len(rows)
        if not rows:
            result["failures"].append({"code": "no_success_rows"})
        for number, row in enumerate(rows, 1):
            stage = "validate"
            try:
                source = self.sources.get(row["source_id"])
                if source is None:
                    raise ValueError("unknown source")
                note_name = row["note_object"]
                path = PurePosixPath(note_name)
                if (not note_name.startswith("notes/") or ".." in path.parts or
                        "\\" in note_name or path.suffix != ".md"):
                    raise ValueError("invalid note path")
                note_data = self.store.read(note_name)
                receipt_name = f"state/receipts/{row['content_sha256']}.json"
                receipt_data = self.store.read(receipt_name)
                if note_data is None or receipt_data is None:
                    raise ValueError("missing saved object")
                note = note_data.decode("utf-8")
                receipt = json.loads(receipt_data)
                if (not isinstance(receipt, dict) or not isinstance(receipt.get("row"), dict) or
                        receipt.get("note") != note or receipt["row"].get("content_sha256") != row["content_sha256"]):
                    raise ValueError("inconsistent receipt")
                stage = "fetch"
                fetched = self.fetcher.get(row["source_url"], source.request_interval_seconds, html=True)
                authors = article_authors(fetched.content)
                if not authors:
                    result["no_authors"] += 1
                stage = "compose"
                refreshed = refresh_note_metadata(note, authors, row["published_at"])
                if refreshed == note:
                    result["unchanged"] += 1
                    continue
                receipt["note"] = refreshed
                new_note = refreshed.encode("utf-8")
                new_receipt = json.dumps(receipt, ensure_ascii=False).encode("utf-8")
                changes.append((number, note_name, note_data, new_note,
                                receipt_name, new_receipt))
                result["planned"] += 1
            except Exception:
                result["failures"].append({"row": number, "stage": stage})
        if result["failures"] or not apply:
            result["status"] = "failed" if result["failures"] else "success"
            return result
        for number, note_name, old_note, new_note, receipt_name, new_receipt in changes:
            try:
                self.store.write(note_name, new_note, "text/markdown; charset=utf-8")
                try:
                    self.store.write(receipt_name, new_receipt, "application/json")
                except Exception:
                    self.store.write(note_name, old_note, "text/markdown; charset=utf-8")
                    raise
                result["updated"] += 1
            except Exception:
                result["failures"].append({"row": number, "stage": "write"})
                result["status"] = "failed"
                break
        return result
