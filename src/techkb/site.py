"""Validate a public snapshot and project it into isolated Quartz input."""
import html
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re

import yaml
from bs4 import BeautifulSoup

from .composer import inline
from .publication import (ExportError, ExportDirectorySnapshot, json_bytes, sha256,
                          note_frontmatter, validate_note, reject_symlinks, instant)
from .normalize import normalize_url


ENTRY_FIELDS = {"id", "path", "sha256", "source_id", "canonical_url", "title", "category",
                "processed_at", "published", "llm_input_truncated"}


def unique_json(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ExportError("duplicate_json_key")
        result[key] = value
    return result


def digest_value(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def load_snapshot(root, tracking=()):
    reader = ExportDirectorySnapshot(root)
    for child in reader.root.iterdir():
        # A content checkout's Git metadata is never read or rendered.
        if child.name == ".git":
            continue
        reject_symlinks(child)
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
        if data is None or sha256(data) != entry["sha256"]:
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


def relative_link(target, current):
    return posixpath.relpath(target, str(PurePosixPath(current).parent))


def collection_path(kind, value):
    return f"browse/{kind}/{sha256(value.encode())}.md"


def cards(entries, metadata, current):
    lines = ['<div class="note-grid">']
    for entry in sorted(entries, key=lambda e: (instant(e["processed_at"]), e["id"]), reverse=True):
        meta = metadata[entry["id"]]
        href = html.escape(relative_link(entry["path"][:-3], current), quote=True)
        lines.append(f'<a class="note-card" href="{href}">')
        lines.append(f'<span class="note-card-meta">{html.escape(meta["publisher"])} · {html.escape(entry["category"])}</span>')
        lines.append(f'<strong>{html.escape(entry["title"])}</strong>')
        lines.append(f'<span class="note-card-summary">{html.escape(meta["description"])}</span>')
        day = instant(entry["processed_at"]).date().isoformat()
        lines.append(f'<span class="note-card-bottom">収集 {html.escape(day)} <span>Noteを読む ↗</span></span></a>')
    if not entries:
        lines.append('<p class="empty-state">この公開版にはNoteがありません。</p>')
    return "\n".join(lines + ["</div>"])


def project_content(manifest, files, metadata, fixture=False, content_commit=None):
    if content_commit is not None and not re.fullmatch(r"[0-9a-f]{40}", content_commit):
        raise ExportError("invalid_content_commit")
    entries = manifest["notes"]
    latest = max((e["processed_at"] for e in entries), default="2026-01-01T00:00:00Z", key=instant)
    sources = sorted({e["source_id"] for e in entries})
    categories = sorted({e["category"] for e in entries})
    projected = {}

    def page(name, title, body, description="LLMが生成した技術記事のNoteを読む・探す・引用する。", tags=()):
        front = dict(title=title, description=description, created=latest, modified=latest, published=latest,
                     tags=list(tags))
        projected[name] = ("---\n" + yaml.safe_dump(front, allow_unicode=True, sort_keys=False) + "---\n\n" + body + "\n").encode()

    nav = '<nav class="browse-nav">' + "".join(
        f'<a href="browse/{kind}">{label}</a>' for kind, label in
        (("sources", "出典別"), ("categories", "カテゴリ別"), ("dates", "日付順"))) + '</nav>'
    hero = ('<div class="home-intro"><span class="eyebrow">GENERATED KNOWLEDGE LIBRARY</span>'
            '<p>技術の変化を集め、<br>次の理解につなげる。</p>'
            '<span>出典をたどれるAI要約。人が編む知識の、そばに。</span></div>')
    stats = (f'<div class="library-stats"><div><strong>{len(entries):02d}</strong><span>Notes</span></div>'
             f'<div><strong>{len(sources):02d}</strong><span>Sources</span></div>'
             f'<div><strong>{len(categories):02d}</strong><span>Categories</span></div></div>')
    edition = f'<p class="edition-link"><a href="about/snapshot">この公開版について</a> · AI生成の要約です。正確性は原典で確認してください。</p>'
    page("index.md", "技術の知識を、日々。", hero + stats + nav + "\n\n## 最新のNote\n\n" + cards(entries, metadata, "index.md") + edition)

    titles = {}
    for entry in entries:
        titles.setdefault(entry["title"], []).append(entry["id"])
    for entry in entries:
        meta = metadata[entry["id"]]
        _, match, _ = note_frontmatter(files[entry["path"]])
        body = files[entry["path"]].decode()[match.end():]
        body = body.removeprefix("\n# " + inline(meta["title"]) + "\n")
        def wikilink(match):
            title = match[1]
            candidates = titles.get(title, [])
            return f"[{inline(title)}]({candidates[0]})" if len(candidates) == 1 else inline(title)
        body = re.sub(r"\[\[([^\[\]\n]+)\]\]", wikilink, body)
        lead = (f'<div class="note-context"><span class="eyebrow">AI GENERATED NOTE</span>'
                f'<p>{html.escape(meta["publisher"])} · {html.escape(entry["category"])}</p>'
                f'<a class="source-link" href="{html.escape(entry["canonical_url"], quote=True)}" '
                'rel="noopener noreferrer">原典を読む ↗</a></div>\n\n')
        front = dict(title=meta["title"], description=meta["description"], tags=meta["tags"],
                     created=entry["processed_at"], modified=entry["processed_at"],
                     published=entry["published"] or entry["processed_at"])
        projected[entry["path"]] = ("---\n" + yaml.safe_dump(front, allow_unicode=True, sort_keys=False) + "---\n\n" + lead + body).encode()
    for kind, values, label, field in (("sources", sources, "出典別", "source_id"),
                                      ("categories", categories, "カテゴリ別", "category")):
        links = []
        for value in values:
            name = collection_path(kind, value)
            subset = [e for e in entries if e[field] == value]
            shown = metadata[subset[0]["id"]]["publisher"] if kind == "sources" else value
            links.append(f"- [{inline(shown)}]({relative_link(name[:-3], f'browse/{kind}.md')}) — {len(subset)} Notes")
            page(name, shown, cards(subset, metadata, name))
        page(f"browse/{kind}.md", label, "\n".join(links) or "公開Noteはありません。")
    page("browse/dates.md", "日付順", "収集日時（UTC）の新しい順に表示しています。\n\n" + cards(entries, metadata, "browse/dates.md"))
    version = "架空データのpreview" if fixture else "保存済みNoteのsnapshot"
    commit = f"`{content_commit}`" if content_commit else "未配布（Git commitの指定なし）"
    about = (f"{version}です。AI要約は出典の代わりにはなりません。\n\n"
             f"- Note数: {len(entries)}\n- Note集合のdigest: `{manifest['dataset_digest']}`\n"
             f"- 指定された配布commit: {commit}\n\n"
             "各Noteの下部から、同じ版のMarkdownを取得できます。hashはmanifestで照合できます。\n"
             "人力Vaultはこのサイトの入力に含みません。")
    page("about/snapshot.md", "この公開版について", about)
    return projected


def finish_html(compiled, manifest, fixture=False):
    entries = {e["id"]: e for e in manifest["notes"]}
    for path in compiled.rglob("*.html"):
        soup = BeautifulSoup(path.read_bytes(), "html.parser")
        if soup.head is None or soup.body is None:
            raise ExportError("invalid_rendered_html")
        # Quartz community v5 search reads this attribute; core v5.0.0 does
        # not emit it. Keep search results inside the project Pages prefix.
        soup.body["data-basepath"] = "/kaname"
        for tag in soup.select('link[rel="preconnect"], link[rel="dns-prefetch"]'):
            tag.decompose()
        policy = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
                  "font-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; "
                  "frame-src 'none'; base-uri 'self'")
        soup.head.insert(0, soup.new_tag("meta", attrs={"http-equiv": "Content-Security-Policy", "content": policy}))
        if fixture:
            robots = soup.new_tag("meta", attrs={"name": "robots", "content": "noindex, nofollow"})
            soup.head.append(robots)
            banner = soup.new_tag("div", attrs={"class": "fixture-banner"})
            banner.string = "PREVIEW · 架空のNoteで表示を検証しています"
            soup.body.insert(0, banner)
        entry = entries.get(path.stem) if path.parent.name == "notes" else None
        if entry:
            article = soup.find("article")
            if article is None:
                raise ExportError("missing_rendered_note")
            section = soup.new_tag("section", attrs={"class": "edition-links"})
            label = soup.new_tag("h2"); label.string = "同じ版のNoteを手元で読む"; section.append(label)
            link = soup.new_tag("a", href=f"../markdown/{entry['path']}")
            link.string = "Markdownを取得 ↗"; section.append(link)
            details = soup.new_tag("details")
            summary = soup.new_tag("summary"); summary.string = "このNoteのhash"; details.append(summary)
            code = soup.new_tag("code"); code.string = entry["sha256"]; details.append(code)
            section.append(details); article.append(section)
        path.write_text(str(soup), encoding="utf-8")


def seal_artifact(compiled, manifest, files, fixture=False, content_commit=None):
    for path in compiled.rglob("*"):
        reject_symlinks(path)
        if path.is_file() and not artifact_path(path.relative_to(compiled).as_posix()):
            raise ExportError("unexpected_artifact_file")
    finish_html(compiled, manifest, fixture)
    for name, data in files.items():
        destination = compiled / "markdown" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    hashes = {}
    for path in compiled.rglob("*"):
        reject_symlinks(path)
        if path.is_file():
            relative = path.relative_to(compiled).as_posix()
            if not artifact_path(relative):
                raise ExportError("unexpected_artifact_file")
            hashes[relative] = sha256(path.read_bytes())
    for entry in manifest["notes"]:
        if f"notes/{entry['id']}.html" not in hashes or hashes.get("markdown/" + entry["path"]) != entry["sha256"]:
            raise ExportError("missing_rendered_note")
    artifact_digest = sha256(json_bytes(sorted(hashes.items())))
    marker = dict(schema_version=1, artifact_digest=artifact_digest, dataset_digest=manifest["dataset_digest"],
                  fixture=fixture, content_commit=content_commit, files=hashes)
    (compiled / "site-manifest.json").write_bytes(json_bytes(marker))
    return marker


def artifact_path(name):
    """Finite output types; Markdown/JSON have dedicated public-only locations."""
    if not isinstance(name, str):
        return False
    pure = PurePosixPath(name)
    if (str(pure) != name or pure.is_absolute() or not pure.parts or
            any(p.startswith(".") for p in pure.parts) or re.search(r'[\\\x00-\x1f\x7f]', name)):
        return False
    if pure.suffix == ".html":
        return (name in {"index.html", "404.html", "about/snapshot.html", "tags/index.html"} or
                bool(re.fullmatch(r"notes/[0-9a-f]{64}\.html", name)) or
                bool(re.fullmatch(r"browse/(sources|categories|dates)\.html", name)) or
                bool(re.fullmatch(r"browse/(sources|categories)/[0-9a-f]{64}\.html", name)) or
                name.startswith("tags/"))
    if name in {"index.css", "prescript.js", "postscript.js", "static/contentIndex.json", "markdown/manifest.json"}:
        return True
    if re.fullmatch(r"markdown/notes/[0-9a-f]{64}\.md", name):
        return True
    return name.startswith("static/") and pure.suffix in {".woff2", ".png", ".svg", ".ico", ".txt"}


def load_artifact(root):
    reader = ExportDirectorySnapshot(root)
    raw_marker = reader.read("site-manifest.json")
    try:
        marker = json.loads(raw_marker or b"", object_pairs_hook=unique_json)
    except (ValueError, UnicodeError):
        raise ExportError("missing_or_invalid_site_manifest") from None
    if (not isinstance(marker, dict) or
            set(marker) != {"schema_version", "artifact_digest", "dataset_digest", "fixture", "content_commit", "files"} or
            type(marker["schema_version"]) is not int or marker["schema_version"] != 1 or
            type(marker["fixture"]) is not bool or not digest_value(marker["dataset_digest"]) or
            (marker["content_commit"] is not None and
             (not isinstance(marker["content_commit"], str) or not re.fullmatch(r"[0-9a-f]{40}", marker["content_commit"]))) or
            not isinstance(marker["files"], dict) or not digest_value(marker["artifact_digest"])):
        raise ExportError("invalid_site_manifest")
    files = {}
    for name, digest in marker["files"].items():
        if not artifact_path(name) or not digest_value(digest):
            raise ExportError("invalid_artifact_path")
        data = reader.read(name)
        if data is None or sha256(data) != digest:
            raise ExportError("artifact_hash_mismatch")
        files[name] = data
    if sha256(json_bytes(sorted(marker["files"].items()))) != marker["artifact_digest"]:
        raise ExportError("artifact_digest_mismatch")
    files["site-manifest.json"] = raw_marker
    if set(reader.list("")) != files.keys():
        raise ExportError("unexpected_artifact_file")
    snapshot, original, _ = load_snapshot(reader.root / "markdown")
    expected_notes = {"notes/" + e["id"] + ".html" for e in snapshot["notes"]}
    if (snapshot["dataset_digest"] != marker["dataset_digest"] or
            {name for name in files if name.startswith("notes/")} != expected_notes or
            any(files.get("markdown/" + name) != data for name, data in original.items())):
        raise ExportError("artifact_snapshot_mismatch")
    if reader.read("site-manifest.json") != raw_marker:
        raise ExportError("artifact_changed")
    return marker, files


def install_artifact(compiled, output):
    marker, files = load_artifact(compiled)
    root = Path(output).absolute()
    reject_symlinks(root)
    if root.exists():
        _, old_files = load_artifact(root)
        if old_files != files:
            raise ExportError("output_conflict")
        return dict(marker, output=str(root), unchanged=True)
    root.mkdir()
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fds = {".": os.open(root, flags)}
    try:
        directories = sorted({str(parent) for name in files for parent in PurePosixPath(name).parents if str(parent) != "."},
                             key=lambda p: (len(PurePosixPath(p).parts), p))
        for name in directories:
            parent = str(PurePosixPath(name).parent)
            os.mkdir(PurePosixPath(name).name, dir_fd=fds[parent])
            fds[name] = os.open(PurePosixPath(name).name, flags, dir_fd=fds[parent])
        for name in sorted(files):
            if name == "site-manifest.json":
                continue
            with (compiled / name).open("rb") as stream:
                os.fsync(stream.fileno())
            os.link(compiled / name, PurePosixPath(name).name, dst_dir_fd=fds[str(PurePosixPath(name).parent)])
        for name in directories:
            os.fsync(fds[name])
        os.fsync(fds["."])
        # Refuse relocated or substituted directories before the completion mark.
        for name, fd in fds.items():
            path = root if name == "." else root / name
            reject_symlinks(path)
            if (path.stat().st_dev, path.stat().st_ino) != (os.fstat(fd).st_dev, os.fstat(fd).st_ino):
                raise ExportError("output_changed")
        with (compiled / "site-manifest.json").open("rb") as stream:
            os.fsync(stream.fileno())
        os.link(compiled / "site-manifest.json", "site-manifest.json", dst_dir_fd=fds["."])
        os.fsync(fds["."])
    finally:
        for fd in reversed(list(fds.values())):
            os.close(fd)
    return dict(marker, output=str(root), unchanged=False)
