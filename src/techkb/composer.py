import re
import unicodedata
from urllib.parse import urlsplit
import yaml

def plain(value):
    return " ".join(str(value).split())

def inline(value):
    value = plain(value)
    return re.sub(r"([\\`*_{}\[\]()<>!#|])", r"\\\1", value)

def concept(value):
    return re.sub(r"[\[\]#|^<>\\/:*?\"]", " ", plain(value)).strip(" .")[:160]

def word_count(value):
    return len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*|[ぁ-んァ-ヶ一-龠]+", value))

def code_span(value):
    return str(value).replace("`", "%60")

def filename(title, day, digest):
    value = unicodedata.normalize("NFC", title)
    value = re.sub(r'[\x00-\x1f\x7f/\\:*?"<>|]', "_", value).strip(" .") or "untitled"
    # UTF-8 byte limit, not just a character limit, for cross-platform filenames.
    value = value.encode("utf-8")[:160].decode("utf-8", errors="ignore").rstrip(" .")
    return f"{day}_{value}_{digest[:12]}.md"

def compose(candidate, source, enrichment, markdown, canonical, fetched_at, raw_hash, content_hash, model, truncated,
            authors=()):
    tags = []
    for tag in ["clippings", *source.tags, *enrichment.tags]:
        cleaned = re.sub(r"[^\w/-]", "-", plain(tag), flags=re.UNICODE).strip("-/")
        if cleaned and cleaned not in tags:
            tags.append(cleaned)
    author_names = list(dict.fromkeys(c for value in authors if (c := concept(value))))
    published = candidate.published_at[:10] if candidate.published_at else None
    metadata = dict(title=enrichment.title_ja, title_original=candidate.title, source=candidate.url,
                    publisher=source.name, author=[f"[[{name}]]" for name in author_names], published=published,
                    created=fetched_at[:10], description=enrichment.summary_ja, tags=tags,
                    canonical_url=canonical, source_language=enrichment.source_language, category=enrichment.category,
                    ai_model=model, raw_html_sha256=raw_hash, content_sha256=content_hash,
                    llm_input_truncated=truncated)
    sections = ["---", yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).rstrip(), "---", "",
                "# " + inline(enrichment.title_ja), "", "> [!abstract] AI要約"]
    sections.extend("> " + inline(line) for line in enrichment.summary_ja.splitlines())
    sections += ["", "## 重要ポイント", ""] + ["- " + inline(v) for v in enrichment.key_points]
    concepts = list(dict.fromkeys(c for v in enrichment.related_concepts if (c := concept(v))))
    sections += ["", "## 検索キーワード", ""] + [f"- [[{c}]]" for c in concepts]
    sections += ["", "## 資料の位置づけ", ""]
    sections.extend(inline(line) for line in enrichment.positioning_ja.splitlines())
    sections += ["", "---", "", "## 出典情報", "",
                 "- Title: " + inline(candidate.title or enrichment.title_ja),
                 "- Publisher/Site: " + inline(source.name),
                 "- Author: " + inline(", ".join(author_names) or "（取得なし）"),
                 "- Published: " + inline(published or "（取得なし）"),
                 "- Clipped: " + fetched_at[:10],
                 "- Domain: " + inline(urlsplit(canonical).hostname or ""),
                 "- Original URL: `" + code_span(candidate.url) + "`",
                 "- Original language: " + inline(enrichment.source_language),
                 "- Word count: " + str(word_count(markdown)),
                 "- AI model: " + inline(model)]
    name = filename(enrichment.title_ja, fetched_at[:10], content_hash)
    return f"notes/{fetched_at[:4]}/{fetched_at[5:7]}/{name}", "\n".join(sections) + "\n"
