import csv
import io
import re
from .pending import Candidate, COLUMNS as PENDING_COLUMNS

INDEX_COLUMNS = ["processed_at", "source_id", "source_url", "canonical_url", "published_at",
                 "raw_html_sha256", "content_sha256", "status", "note_object", "llm_model",
                 "input_tokens", "output_tokens", "thinking_tokens", "llm_input_truncated"]

def encode_tsv(rows, columns):
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=columns, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode("utf-8")

def decode_tsv(data, required):
    if data is None:
        return []
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline=""), delimiter="\t")
    if not reader.fieldnames or not set(required).issubset(reader.fieldnames):
        raise ValueError("invalid TSV header")
    rows = list(reader)
    if any(None in row or any(row[c] is None for c in required) for row in rows):
        raise ValueError("malformed TSV record")
    return rows

class State:
    def __init__(self, store):
        self.store = store
        self.months = {}
        for name in store.list("state/index/"):
            if name.endswith(".tsv"):
                rows = decode_tsv(store.read(name), INDEX_COLUMNS[:12])
                for row in rows:
                    if row["status"] == "success" and any(not re.fullmatch(r"[0-9a-f]{64}", row[c]) for c in ("raw_html_sha256", "content_sha256")):
                        raise ValueError("invalid success hash")
                self.months[name] = rows
        self.rows = [r for rows in self.months.values() for r in rows]

    def pending(self):
        return [Candidate(**{c: row[c] for c in PENDING_COLUMNS}) for row in
                decode_tsv(self.store.read("state/pending.tsv"), PENDING_COLUMNS)]

    def save_pending(self, candidates):
        self.store.write("state/pending.tsv", encode_tsv([c.row() for c in candidates], PENDING_COLUMNS), "text/tab-separated-values; charset=utf-8")

    def append(self, row):
        if any(r["status"] == "success" and r["content_sha256"] == row["content_sha256"] for r in self.rows):
            return
        name = f"state/index/{row['processed_at'][:7]}.tsv"
        rows = self.months.get(name, []) + [row]
        rows = [{key: r.get(key, "") for key in INDEX_COLUMNS} for r in rows]
        self.store.write(name, encode_tsv(rows, INDEX_COLUMNS), "text/tab-separated-values; charset=utf-8")
        self.months[name] = rows
        self.rows.append(row)
