"""HTML postprocessing and complete, immutable Web artifact validation."""
import json
import os
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from techkb.publication import ExportError, ExportDirectorySnapshot, json_bytes, sha256, note_frontmatter, reject_symlinks
from techkb.publication.common import digest_matches, digest_value
from techkb.publication.snapshot import load_snapshot, unique_json
from .validation import artifact_path, hash_manifest, valid_site_marker, snapshot_matches


def finish_html(compiled, manifest, fixture=False, files=None):
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
        entry = entries.get(path.stem) if path.parent.name == "notes" else None
        images = []
        if entry and files is not None:
            images = note_frontmatter(files[entry['path']])[2].get('article_images', [])
        approved = {image['url'] for image in images}
        found = []
        for tag in soup.select('img'):
            url = tag.get('src', '')
            if urlsplit(url).scheme in ('http', 'https'):
                if url not in approved or tag.get('srcset'):
                    raise ExportError('unexpected_article_image')
                found.append(url)
                tag['referrerpolicy'] = 'no-referrer'
                tag['loading'] = 'lazy'
        if sorted(found) != sorted(approved):
            raise ExportError('missing_article_image')
        origins = sorted({f'https://{urlsplit(url).netloc}' for url in approved})
        image_policy = "img-src 'self' data:" + (" " + " ".join(origins) if origins else "") + "; "
        policy = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
                  "font-src 'self'; " + image_policy + "connect-src 'self'; object-src 'none'; "
                  "frame-src 'none'; base-uri 'self'")
        soup.head.insert(0, soup.new_tag("meta", attrs={"http-equiv": "Content-Security-Policy", "content": policy}))
        if fixture:
            robots = soup.new_tag("meta", attrs={"name": "robots", "content": "noindex, nofollow"})
            soup.head.append(robots)
            banner = soup.new_tag("div", attrs={"class": "fixture-banner"})
            banner.string = "PREVIEW · 架空のNoteで表示を検証しています"
            soup.body.insert(0, banner)
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
    finish_html(compiled, manifest, fixture, files)
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
    artifact_digest = hash_manifest(hashes)
    marker = dict(schema_version=1, artifact_digest=artifact_digest, dataset_digest=manifest["dataset_digest"],
                  fixture=fixture, content_commit=content_commit, files=hashes)
    (compiled / "site-manifest.json").write_bytes(json_bytes(marker))
    return marker


def load_artifact(root):
    reader = ExportDirectorySnapshot(root)
    raw_marker = reader.read("site-manifest.json")
    try:
        marker = json.loads(raw_marker or b"", object_pairs_hook=unique_json)
    except (ValueError, UnicodeError):
        raise ExportError("missing_or_invalid_site_manifest") from None
    if not valid_site_marker(marker):
        raise ExportError("invalid_site_manifest")
    files = {}
    for name, digest in marker["files"].items():
        if not artifact_path(name) or not digest_value(digest):
            raise ExportError("invalid_artifact_path")
        data = reader.read(name)
        if data is None or not digest_matches(data, digest):
            raise ExportError("artifact_hash_mismatch")
        files[name] = data
    if hash_manifest(marker["files"]) != marker["artifact_digest"]:
        raise ExportError("artifact_digest_mismatch")
    files["site-manifest.json"] = raw_marker
    if set(reader.list("")) != files.keys():
        raise ExportError("unexpected_artifact_file")
    snapshot, original, _ = load_snapshot(reader.root / "markdown")
    expected_notes = {"notes/" + e["id"] + ".html" for e in snapshot["notes"]}
    if not snapshot_matches(marker, snapshot, files, original, expected_notes):
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
