"""Read-only, deterministic export of validated compact Notes.

The manifest is the completion marker, installed only after all complete files.
No collection clients, storage writes, or human Vault operations are used here.
"""
import hashlib
import csv
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from datetime import datetime, timezone
from urllib.parse import unquote, urlsplit

import yaml

from .composer import concept, inline, code_span
from .normalize import normalize_url
from .state import INDEX_COLUMNS, decode_tsv


class ExportError(ValueError):
    """Only a fixed code is safe to print; never include Note text or URLs."""


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def object_path(name, prefix, suffix):
    path = PurePosixPath(name)
    if (not name.startswith(prefix) or str(path) != name or ".." in path.parts or
            path.suffix != suffix or re.search(r'[\\\x00-\x1f\x7f]', name)):
        raise ExportError("invalid_object_path")
    return path


def reject_symlinks(path):
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ExportError("symlink_path")


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


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in mapping:
            raise ExportError("invalid_frontmatter")
        mapping[key] = loader.construct_object(value_node)
    return mapping


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)
FRONTMATTER = re.compile(r"\A---\n(.*?)^---\n", re.MULTILINE | re.DOTALL)
FIELDS = {"title", "title_original", "source", "publisher", "author", "published", "created",
          "description", "tags", "canonical_url", "source_language", "category", "ai_model",
          "raw_html_sha256", "content_sha256", "llm_input_truncated"}
SECRET = re.compile(
    r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----|AIza[0-9A-Za-z_-]{35}|"
    r"\bgh[pousr]_[0-9A-Za-z]{20,}|\bgithub_pat_[0-9A-Za-z_]{20,}|\bAKIA[0-9A-Z]{16}|"
    r"[?&](?:access_token|api_key|token|client_secret|password|x-goog-signature|x-amz-signature)=",
    re.IGNORECASE)
UNSAFE = re.compile(r"<[^>\n]+>|javascript\s*:|data\s*:|!\[", re.IGNORECASE)


def reject_secrets(value):
    # The composer escapes Markdown punctuation; decoding those escapes avoids
    # missing e.g. a GitHub token in a generated key point. YAML values are
    # checked separately after parsing, including quoted Unicode escapes.
    decoded = re.sub(r"\\([\\`*_{}\[\]()<>!#|])", r"\1", value)
    if SECRET.search(unquote(decoded)):
        raise ExportError("secret_pattern")


def note_frontmatter(data):
    try:
        text = data.decode("utf-8")
        match = FRONTMATTER.match(text)
        if not match or any(isinstance(t, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken))
                            for t in yaml.scan(match[1])):
            raise ExportError("invalid_frontmatter")
        meta = yaml.load(match[1], Loader=UniqueLoader)
        if not isinstance(meta, dict):
            raise ExportError("invalid_frontmatter")
        return text, match, meta
    except (UnicodeError, yaml.YAMLError):
        raise ExportError("invalid_frontmatter") from None


def instant(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError()
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError):
        raise ExportError("invalid_processed_at") from None


def plain_inline(value):
    decoded = re.sub(r"\\([\\`*_{}\[\]()<>!#|])", r"\1", value)
    if not decoded.strip() or len(decoded) > 2000 or inline(decoded) != value:
        raise ExportError("invalid_compact_body")
    return decoded


def validate_note(data, row, tracking, categories):
    if len(data) > 100_000:
        raise ExportError("oversized_note")
    try:
        text, match, meta = note_frontmatter(data)
        reject_secrets(text)
        if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", text):
            raise ExportError("invalid_note")
        if not FIELDS <= meta.keys() or meta.keys() - FIELDS - {"llm_input_max_chars"}:
            raise ExportError("invalid_frontmatter")
        for value in meta.values():
            for part in value if isinstance(value, list) else [value]:
                if isinstance(part, str):
                    reject_secrets(part)
        scalar_fields = FIELDS - {"author", "tags", "published", "llm_input_truncated"}
        if (any(not isinstance(meta[k], str) for k in scalar_fields) or
                (meta["published"] is not None and not isinstance(meta["published"], str))):
            raise ExportError("invalid_frontmatter")
        if any(UNSAFE.search(meta[k]) for k in scalar_fields):
            raise ExportError("unsafe_markup")
        if (not 1 <= len(meta["title"]) <= 300 or not 1 <= len(meta["description"]) <= 1600 or
                not 2 <= len(meta["source_language"]) <= 40 or
                (categories is not None and meta["category"] not in categories)):
            raise ExportError("invalid_frontmatter")
        for key in ("tags", "author"):
            if (not isinstance(meta[key], list) or len(meta[key]) > 64 or
                    any(not isinstance(v, str) or len(v) > 2000 or UNSAFE.search(v) for v in meta[key])):
                raise ExportError("invalid_frontmatter")
        if any(not re.fullmatch(r"[\w/-]+", tag) for tag in meta["tags"]):
            raise ExportError("invalid_frontmatter")
        authors = []
        for author in meta["author"]:
            if not author.startswith("[[") or not author.endswith("]]") or concept(author[2:-2]) != author[2:-2]:
                raise ExportError("invalid_frontmatter")
            authors.append(author[2:-2])
        if (any(meta[k] != row[k] for k in ("raw_html_sha256", "content_sha256")) or
                normalize_url(meta["source"], tracking) != normalize_url(row["source_url"], tracking) or
                normalize_url(meta["canonical_url"], tracking) != normalize_url(row["canonical_url"], tracking) or
                meta["ai_model"] != row["llm_model"] or meta["created"] != row["processed_at"][:10] or
                str(meta["published"] or "") != row["published_at"][:10] or
                type(meta["llm_input_truncated"]) is not bool or
                str(meta["llm_input_truncated"]).lower() != row.get("llm_input_truncated", "false")):
            raise ExportError("note_index_mismatch")
        limit = meta.get("llm_input_max_chars")
        if limit is not None and (type(limit) is not int or limit <= 0):
            raise ExportError("invalid_frontmatter")
        # Require the compact composer structure; arbitrary appended article
        # sections, HTML, Markdown embeds and code blocks cannot pass this gate.
        prefix = "\n# " + inline(meta["title"]) + "\n\n"
        if meta["llm_input_truncated"]:
            scope = f"先頭{limit:,}文字" if limit is not None else "先頭部分"
            prefix += ("> [!warning] 要約対象の制限\n"
                       f"> 入力上限により、変換後の本文の{scope}だけを要約しています。\n"
                       "> 記事後半の論点が含まれない場合があります。記事全体の確認には出典URLを参照してください。\n\n")
        prefix += "> [!abstract] AI要約\n" + "".join("> " + inline(line) + "\n" for line in meta["description"].splitlines())
        prefix += "\n## 重要ポイント\n\n"
        body = text[match.end():]
        if not body.startswith(prefix):
            raise ExportError("invalid_compact_body")
        points, sep, rest = body[len(prefix):].partition("\n\n## 検索キーワード\n\n")
        if not sep or not 2 <= len(points.splitlines()) <= 5:
            raise ExportError("invalid_compact_body")
        for line in points.splitlines():
            if not line.startswith("- "):
                raise ExportError("invalid_compact_body")
            plain_inline(line[2:])
        concepts, sep, rest = rest.partition("\n\n## 資料の位置づけ\n\n")
        if not sep or not 1 <= len(concepts.splitlines()) <= 6:
            raise ExportError("invalid_compact_body")
        for line in concepts.splitlines():
            if not line.startswith("- [[") or not line.endswith("]]") or not line[4:-2] or concept(line[4:-2]) != line[4:-2]:
                raise ExportError("invalid_compact_body")
        positioning, sep, provenance = rest.partition("\n\n---\n\n## 出典情報\n\n")
        if not sep or len(positioning) > 2400:
            raise ExportError("invalid_compact_body")
        for line in positioning.splitlines():
            if line:
                plain_inline(line)
        if not positioning.strip():
            raise ExportError("invalid_compact_body")
        provenance_prefix = (
            "- Title: " + inline(meta["title_original"] or meta["title"]) + "\n"
            "- Publisher/Site: " + inline(meta["publisher"]) + "\n"
            "- Author: " + inline(", ".join(authors) or "（取得なし）") + "\n"
            "- Published: " + inline(str(meta["published"] or "（取得なし）")) + "\n"
            "- Clipped: " + meta["created"] + "\n"
        )
        provenance_prefix += "- Domain: " + inline(urlsplit(meta["canonical_url"]).hostname or "") + "\n"
        provenance_prefix += "- Original URL: `" + code_span(meta["source"]) + "`\n"
        provenance_prefix += "- Original language: " + inline(meta["source_language"]) + "\n"
        if not provenance.startswith(provenance_prefix) or not re.fullmatch(
                r"- Word count: \d+\n" + re.escape("- AI model: " + inline(meta["ai_model"]) + "\n"),
                provenance[len(provenance_prefix):]):
            raise ExportError("invalid_compact_body")
        return meta
    except (UnicodeError, yaml.YAMLError, ValueError) as exc:
        if isinstance(exc, ExportError):
            raise
        raise ExportError("invalid_note") from None


PUBLIC_README = ("# kaname generated Notes\n\n"
                 "LLMが生成した技術記事の要約です。正確性は出典で確認してください。\n"
                 "記事原文・運用台帳・人力Vaultは含みません。元記事の権利は各権利者に帰属します。\n\n"
                 "manifest.jsonのNote ID・SHA-256・dataset digestで同じ版を照合できます。\n"
                 "Git submoduleではcommitを固定して参照し、更新は利用側で明示してください。\n"
                 "生成領域の変更を強制reset/cleanせず、人の注釈は領域外に保持してください。\n").encode()


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


def existing_matches(root, files):
    actual = set()
    for path in root.rglob("*"):
        reject_symlinks(path)
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
        elif not path.is_dir():
            raise ExportError("invalid_output")
        elif path.relative_to(root).as_posix() != "notes":
            raise ExportError("output_conflict")
    return actual == files.keys() and all((root / name).read_bytes() == data for name, data in files.items())


def export_notes(store, output, tracking=(), categories=None, exclude_ids=()):
    root = Path(output).absolute()
    reject_symlinks(root)
    if isinstance(store, ExportDirectorySnapshot) and root.resolve().is_relative_to(store.root.resolve()):
        raise ExportError("output_inside_snapshot")
    if not root.parent.is_dir():
        raise ExportError("missing_output_parent")
    if not all(hasattr(os, flag) for flag in ("O_DIRECTORY", "O_NOFOLLOW")):
        raise ExportError("unsupported_filesystem")
    files, digest = snapshot_files(store, tracking, categories, exclude_ids)
    result = dict(status="success", dataset_digest=digest, notes=len(files) - 2, output=str(root))
    if root.exists():
        if root.is_dir() and existing_matches(root, files):
            return dict(result, unchanged=True)
        raise ExportError("output_conflict")
    with tempfile.TemporaryDirectory(prefix=".kaname-export-", dir=root.parent) as staging:
        stage = Path(staging)
        for name, data in files.items():
            path = stage / name
            path.parent.mkdir(exist_ok=True)
            with path.open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        reject_symlinks(root)
        # mkdir is exclusive even when another process creates an empty target.
        # An interrupted install has no manifest and must never be published.
        root.mkdir()
        # Anchor writes to directory descriptors so replacing notes/ with a
        # symlink cannot redirect publication into somebody else's directory.
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        root_fd = os.open(root, flags)
        notes_fd = None
        try:
            os.mkdir("notes", dir_fd=root_fd)
            notes_fd = os.open("notes", flags, dir_fd=root_fd)
            for name in sorted(files):
                if name == "manifest.json":
                    continue
                target_fd = notes_fd if name.startswith("notes/") else root_fd
                os.link(stage / name, PurePosixPath(name).name, dst_dir_fd=target_fd)
            os.fsync(notes_fd)
            os.fsync(root_fd)
            reject_symlinks(root / "notes")
            if (root.stat().st_ino != os.fstat(root_fd).st_ino or
                    (root / "notes").stat().st_ino != os.fstat(notes_fd).st_ino):
                raise ExportError("output_changed")
            os.link(stage / "manifest.json", "manifest.json", dst_dir_fd=root_fd)
            os.fsync(root_fd)
        finally:
            if notes_fd is not None:
                os.close(notes_fd)
            os.close(root_fd)
    return dict(result, unchanged=False)
