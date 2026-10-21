"""Project a validated public snapshot into isolated Quartz Markdown input."""
import html
from pathlib import PurePosixPath
import posixpath
import re

import yaml

from .composer import inline
from .publication import ExportError, sha256, note_frontmatter, instant
from .publication.snapshot import load_snapshot
from .wikilinks import project_wikilinks
from .tags import canonical_tags

PAGE_SIZE = 24


def ordered_entries(entries):
    return sorted(entries, key=lambda e: (instant(e["processed_at"]), e["id"]), reverse=True)


def page_path(first, number):
    if number == 1:
        return first
    base = "" if first == "index.md" else first[:-3] + "/"
    return f"{base}page/{number}.md"


def pagination(first, number, total):
    if total <= 1:
        return ""
    current = page_path(first, number)
    parts = ['<nav class="pagination" aria-label="Note一覧のページ">']
    def link(n, label, extra=""):
        href = html.escape(relative_link(page_path(first, n)[:-3] + '.html', current), quote=True)
        return f'<a href="{href}" {extra}>{label}</a>'
    if number > 1:
        parts.append(link(number - 1, "前へ", 'rel="prev"'))
    visible = sorted({1, total, *range(max(1, number - 1), min(total, number + 1) + 1)})
    previous = 0
    for n in visible:
        if previous and n - previous > 1:
            parts.append('<span aria-hidden="true">…</span>')
        parts.append(f'<span aria-current="page" aria-label="{n}ページ目">{n}</span>' if n == number
                     else link(n, str(n), f'aria-label="{n}ページ目"'))
        previous = n
    if number < total:
        parts.append(link(number + 1, "次へ", 'rel="next"'))
    return "\n".join(parts + ["</nav>"])


def relative_link(target, current):
    return posixpath.relpath(target, str(PurePosixPath(current).parent))


def collection_path(kind, value):
    return f"browse/{kind}/{sha256(value.encode())}.md"


def cards(entries, metadata, current):
    lines = ['<div class="note-grid">']
    for entry in ordered_entries(entries):
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

    def listing(first, title, subset, intro="", outro=None):
        ordered = ordered_entries(subset)
        total = max(1, (len(ordered) + PAGE_SIZE - 1) // PAGE_SIZE)
        for number in range(1, total + 1):
            name = page_path(first, number)
            start = (number - 1) * PAGE_SIZE
            status = f'<p class="page-count">{len(ordered)} Notes · {number} / {total} ページ</p>'
            body = ((intro if number == 1 else "") + status + cards(ordered[start:start + PAGE_SIZE], metadata, name) +
                    pagination(first, number, total) + (outro(name) if outro else ""))
            page(name, title if number == 1 else f"{title} — {number}ページ目", body)

    nav = '<nav class="browse-nav">' + "".join(
        f'<a href="browse/{kind}">{label}</a>' for kind, label in
        (("sources", "出典別"), ("categories", "カテゴリ別"), ("dates", "日付順"))) + '</nav>'
    hero = ('<div class="home-intro"><span class="eyebrow">GENERATED KNOWLEDGE LIBRARY</span>'
            '<p>技術の変化を集め、<br>次の理解につなげる。</p>'
            '<span>出典をたどれるAI要約。人が編む知識の、そばに。</span></div>')
    stats = (f'<div class="library-stats"><div><strong>{len(entries):02d}</strong><span>Notes</span></div>'
             f'<div><strong>{len(sources):02d}</strong><span>Sources</span></div>'
             f'<div><strong>{len(categories):02d}</strong><span>Categories</span></div></div>')
    def edition(current):
        href = relative_link('about/snapshot', current)
        return f'<p class="edition-link"><a href="{href}">この公開版について</a> · AI生成の要約です。正確性は原典で確認してください。</p>'
    listing("index.md", "技術の知識を、日々。", entries, hero + stats + nav + "\n\n## 最新のNote\n\n", edition)

    titles = {}
    for entry in entries:
        titles.setdefault(entry["title"], []).append(entry["id"])
    for entry in entries:
        meta = metadata[entry["id"]]
        _, match, _ = note_frontmatter(files[entry["path"]])
        body = files[entry["path"]].decode()[match.end():]
        body = body.removeprefix("\n# " + inline(meta["title"]) + "\n")
        if (meta["llm_input_truncated"] and "llm_input_max_chars" not in meta and
                "> [!warning] 要約対象の制限" not in body):
            body = ("> [!warning] 要約対象の制限\n"
                    "> このNoteは入力を打ち切って生成されています。保存時点の上限文字数は記録されていません。\n"
                    "> 記事全体の確認には出典URLを参照してください。\n\n" + body.lstrip("\n"))
        body = project_wikilinks(body, titles, entry["id"])
        lead = (f'<div class="note-context"><span class="eyebrow">AI GENERATED NOTE</span>'
                f'<p>{html.escape(meta["publisher"])} · {html.escape(entry["category"])}</p>'
                f'<a class="source-link" href="{html.escape(entry["canonical_url"], quote=True)}" '
                'rel="noopener noreferrer">原典を読む ↗</a></div>\n\n')
        if meta.get("article_images"):
            lead += '> 画像は出典サイトから直接表示します。閲覧時に外部通信が発生し、画像の変更・削除により表示できなくなる場合があります。\n\n'
        front = dict(title=meta["title"], description=meta["description"], tags=canonical_tags(meta["tags"]),
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
            listing(name, shown, subset)
        page(f"browse/{kind}.md", label, "\n".join(links) or "公開Noteはありません。")
    listing("browse/dates.md", "日付順", entries, "収集日時（UTC）の新しい順に表示しています。\n\n")
    version = "架空データのpreview" if fixture else "保存済みNoteのsnapshot"
    commit = f"`{content_commit}`" if content_commit else "未配布（Git commitの指定なし）"
    about = (f"{version}です。AI要約は出典の代わりにはなりません。\n\n"
             f"- Note数: {len(entries)}\n- Note集合のdigest: `{manifest['dataset_digest']}`\n"
             f"- 指定された配布commit: {commit}\n\n"
             "各Noteの下部から、同じ版のMarkdownを取得できます。hashはmanifestで照合できます。\n"
             "人力Vaultはこのサイトの入力に含みません。")
    page("about/snapshot.md", "この公開版について", about)
    return projected
