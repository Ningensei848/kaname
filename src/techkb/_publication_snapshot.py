"""Read-only snapshot selection with byte, generation and catalog rechecks."""
import csv
import io
import json
from pathlib import Path, PurePosixPath
import re

from ._publication_common import (ExportError, PUBLIC_README, sha256, json_bytes,
                                  object_path, reject_symlinks)
from ._public_note import note_frontmatter, validate_note, instant
from .normalize import normalize_url
from .state import INDEX_COLUMNS, decode_tsv


class ExportDirectorySnapshot:
    """Local fixture/state reader that refuses symlinked objects and directories."""
    def __init__(self, root):
        self.root = Path(root).absolute()
        reject_symlinks(self.root)
        if not self.root.is_dir():
            raise ExportError("missing_snapshot")

    def list(self, prefix):
        base = self.root / prefix
        reject_symlinks(base)
        names = []
        if base.exists():
            for path in base.rglob("*"):
                reject_symlinks(path)
                if path.is_file():
                    names.append(path.relative_to(self.root).as_posix())
        return sorted(names)

    def read(self, name):
        path = self.root / name
        reject_symlinks(path)
        if not path.resolve().is_relative_to(self.root.resolve()):
            raise ExportError("invalid_object_path")
        if path.exists() and not path.is_file():
            raise ExportError("invalid_snapshot_object")
        return path.read_bytes() if path.exists() else None


class CheckedReads:
    def __init__(self, store):
        self.store, self.objects = store, {}

    def read(self, name):
        if name not in self.objects:
            data = self.store.read(name)
            if data is None:
                raise ExportError("missing_object")
            generation = getattr(self.store, "generations", {}).get(name)
            self.objects[name] = (data, generation)
        return self.objects[name][0]

    def verify(self, index_names):
        # Indexes are checked last: a collection checkpoint during Note reads
        # must invalidate this attempt. GCS generations also detect ABA changes.
        for name in sorted(self.objects, key=lambda n: (n.startswith("state/index/"), n)):
            data, generation = self.objects[name]
            current = self.store.read(name)
            if (current != data or
                    getattr(self.store, "generations", {}).get(name) != generation):
                raise ExportError("snapshot_changed")
        if index_catalog(self.store) != index_names:
            raise ExportError("snapshot_changed")


def index_catalog(store):
    names = sorted(store.list("state/index/"))
    if len(names) != len(set(names)) or any(not re.fullmatch(r"state/index/\d{4}-\d{2}\.tsv", n) for n in names):
        raise ExportError("invalid_index_catalog")
    return names


def snapshot_files(store, tracking=(), categories=None, exclude_ids=()):
    excluded = set(exclude_ids)
    if any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in excluded):
        raise ExportError("invalid_exclusion")
    names = index_catalog(store)
    reader = CheckedReads(store)
    rows = []
    for name in names:
        data = reader.read(name)
        header = next(csv.reader(io.StringIO(data.decode("utf-8-sig")), delimiter="\t"), [])
        if len(header) != len(set(header)) or set(header) - set(INDEX_COLUMNS):
            raise ExportError("invalid_index_header")
        for row in decode_tsv(data, INDEX_COLUMNS[:12]):
            if row["status"] == "success":
                if row["processed_at"][:7] != PurePosixPath(name).stem:
                    raise ExportError("index_month_mismatch")
                rows.append(row)
    if not rows:
        raise ExportError("no_success_rows")
    selected, seen_hashes = {}, set()
    for row in rows:
        if any(not re.fullmatch(r"[0-9a-f]{64}", row[k]) for k in ("raw_html_sha256", "content_sha256")):
            raise ExportError("invalid_success_hash")
        if row["content_sha256"] in seen_hashes:
            raise ExportError("duplicate_success_hash")
        seen_hashes.add(row["content_sha256"])
        if not re.fullmatch(r"[A-Za-z0-9_-]+", row["source_id"]):
            raise ExportError("invalid_source_id")
        canonical = normalize_url(row["canonical_url"], tracking)
        identity = (row["source_id"], canonical)
        note_id = sha256(json.dumps(identity, ensure_ascii=False, separators=(",", ":")).encode())
        object_path(row["note_object"], "notes/", ".md")
        data = reader.read(row["note_object"])
        _, _, saved_meta = note_frontmatter(data)
        if any(saved_meta.get(k) != row[k] for k in ("raw_html_sha256", "content_sha256")):
            raise ExportError("note_index_mismatch")
        try:
            receipt = json.loads(reader.read(f"state/receipts/{row['content_sha256']}.json"))
        except (ValueError, UnicodeError):
            raise ExportError("invalid_receipt") from None
        if (not isinstance(receipt, dict) or not isinstance(receipt.get("row"), dict) or
                not isinstance(receipt.get("note"), str) or
                any(str(receipt["row"].get(k, "")) != v for k, v in row.items()) or
                receipt["note"].encode() != data):
            raise ExportError("receipt_mismatch")
        # Validate all indexed objects for coherence; only selected public
        # revisions need the publication policy gate (withdrawn IDs stay out).
        order = (instant(row["processed_at"]), row["content_sha256"])
        if note_id in selected and selected[note_id][0] != identity:
            raise ExportError("note_id_collision")
        if note_id not in selected or order > selected[note_id][1]:
            selected[note_id] = (identity, order, row, data)
    if excluded - selected.keys():
        raise ExportError("unknown_exclusion")
    files, entries = {"README.md": PUBLIC_README}, []
    for note_id, (identity, _, row, data) in sorted(selected.items()):
        if note_id in excluded:
            continue
        meta = validate_note(data, row, tracking, categories)
        path = f"notes/{note_id}.md"
        files[path] = data
        entries.append(dict(id=note_id, path=path, sha256=sha256(data), source_id=identity[0],
                            canonical_url=identity[1], title=meta["title"], category=meta["category"],
                            processed_at=row["processed_at"], published=meta["published"],
                            llm_input_truncated=meta["llm_input_truncated"]))
    digest = sha256(json_bytes([[entry["id"], entry["sha256"]] for entry in entries]))
    files["manifest.json"] = json_bytes(dict(schema_version=1, dataset_digest=digest, notes=entries))
    reader.verify(names)
    return files, digest
