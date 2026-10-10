"""Read-only snapshot selection with byte, generation and catalog rechecks."""
import csv
import io
import json
from pathlib import Path, PurePosixPath
import re

from .common import (ExportError, PUBLIC_README, sha256, json_bytes,
                                  object_path, reject_symlinks, PUBLIC_ATTRIBUTES, digest_matches, digest_value)
from .note import note_frontmatter, validate_note, instant
from ..normalize import normalize_url
from ..state import INDEX_COLUMNS, decode_tsv


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


ENTRY_FIELDS = {"id", "path", "sha256", "source_id", "canonical_url", "title", "category",
                "processed_at", "published", "llm_input_truncated"}


def unique_json(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ExportError("duplicate_json_key")
        result[key] = value
    return result


def load_snapshot(root, tracking=()):
    reader = ExportDirectorySnapshot(root)
    for child in reader.root.iterdir():
        # A content checkout's Git metadata is never read or rendered.
        if child.name == ".git":
            continue
        reject_symlinks(child)
        if child.name == ".gitattributes":
            if reader.read(child.name) != PUBLIC_ATTRIBUTES:
                raise ExportError("invalid_distribution_attributes")
            continue
        if child.name not in {"README.md", "manifest.json", "notes"}:
            raise ExportError("unexpected_snapshot_file")
    raw = reader.read("manifest.json")
    if raw is None:
        raise ExportError("missing_manifest")
    try:
        manifest = json.loads(raw, object_pairs_hook=unique_json)
    except (ValueError, UnicodeError):
        raise ExportError("invalid_manifest") from None
    if (not isinstance(manifest, dict) or set(manifest) != {"schema_version", "dataset_digest", "notes"} or
            type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1 or
            not isinstance(manifest["notes"], list) or not digest_value(manifest["dataset_digest"])):
        raise ExportError("invalid_manifest")
    files, metadata, ids = {"manifest.json": raw}, {}, []
    for entry in manifest["notes"]:
        if (not isinstance(entry, dict) or set(entry) != ENTRY_FIELDS or
                not digest_value(entry["id"]) or not digest_value(entry["sha256"]) or
                entry["path"] != f"notes/{entry['id']}.md" or
                any(not isinstance(entry[k], str) for k in ("source_id", "canonical_url", "title", "category", "processed_at")) or
                not re.fullmatch(r"[A-Za-z0-9_-]+", entry["source_id"]) or
                (entry["published"] is not None and not isinstance(entry["published"], str)) or
                type(entry["llm_input_truncated"]) is not bool):
            raise ExportError("invalid_manifest_entry")
        instant(entry["processed_at"])
        canonical = normalize_url(entry["canonical_url"], tracking)
        identity = json.dumps([entry["source_id"], canonical], ensure_ascii=False, separators=(",", ":")).encode()
        if canonical != entry["canonical_url"] or sha256(identity) != entry["id"]:
            raise ExportError("note_identity_mismatch")
        data = reader.read(entry["path"])
        if data is None or not digest_matches(data, entry["sha256"]):
            raise ExportError("public_note_hash_mismatch")
        _, _, meta = note_frontmatter(data)
        if any(not digest_value(meta.get(k)) for k in ("raw_html_sha256", "content_sha256")):
            raise ExportError("invalid_note_hash")
        row = dict(processed_at=entry["processed_at"], source_url=meta.get("source", ""),
                   canonical_url=entry["canonical_url"], published_at=entry["published"] or "",
                   raw_html_sha256=meta["raw_html_sha256"], content_sha256=meta["content_sha256"],
                   llm_model=meta.get("ai_model", ""), llm_input_truncated=str(entry["llm_input_truncated"]).lower())
        validate_note(data, row, tracking, None)
        if any(entry[k] != meta[k] for k in ("title", "category", "published", "llm_input_truncated")):
            raise ExportError("manifest_note_mismatch")
        ids.append(entry["id"])
        files[entry["path"]] = data
        metadata[entry["id"]] = meta
    if ids != sorted(set(ids)):
        raise ExportError("unsorted_or_duplicate_note_ids")
    pairs = [[e["id"], e["sha256"]] for e in manifest["notes"]]
    if sha256(json_bytes(pairs)) != manifest["dataset_digest"]:
        raise ExportError("dataset_digest_mismatch")
    expected = set(files) - {"manifest.json"}
    if set(reader.list("notes/")) != expected:
        raise ExportError("unexpected_snapshot_file")
    if any(reader.read(name) != data for name, data in files.items()):
        raise ExportError("snapshot_changed")
    if set(reader.list("notes/")) != expected:
        raise ExportError("snapshot_changed")
    return manifest, files, metadata
