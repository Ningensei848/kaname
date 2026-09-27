import re
import unicodedata
import yaml

def plain(value):
    return " ".join(str(value).split())

def inline(value):
    value = plain(value)
    return re.sub(r"([\\`*_{}\[\]()<>!#|])", r"\\\1", value)

def concept(value):
    return re.sub(r"[\[\]#|^<>\\/:*?\"]", " ", plain(value)).strip(" .")[:160]

def filename(title, day, digest):
    value = unicodedata.normalize("NFC", title)
    value = re.sub(r'[\x00-\x1f\x7f/\\:*?"<>|]', "_", value).strip(" .") or "untitled"
    # UTF-8 byte limit, not just a character limit, for cross-platform filenames.
    value = value.encode("utf-8")[:160].decode("utf-8", errors="ignore").rstrip(" .")
    return f"{day}_{value}_{digest[:12]}.md"

def compose(candidate, source, enrichment, markdown, canonical, fetched_at, raw_hash, content_hash, model, truncated):
    tags = []
    for tag in [*source.tags, *enrichment.tags]:
        cleaned = re.sub(r"[^\w/-]", "-", plain(tag), flags=re.UNICODE).strip("-/")
        if cleaned and cleaned not in tags:
            tags.append(cleaned)
    metadata = dict(title=enrichment.title_ja, title_original=candidate.title, source=source.name,
                    source_url=candidate.url, canonical_url=canonical, published_at=candidate.published_at or None,
                    fetched_at=fetched_at, source_language=enrichment.source_language, category=enrichment.category,
                    tags=tags, ai_model=model, raw_html_sha256=raw_hash, content_sha256=content_hash,
                    llm_input_truncated=truncated)
    sections = ["---", yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).rstrip(), "---", "",
                "# " + inline(enrichment.title_ja), "", "> [!abstract] AI要約"]
    sections.extend("> " + inline(line) for line in enrichment.summary_ja.splitlines())
    for heading, values in [("重要ポイント", enrichment.key_points), ("技術的インサイト", enrichment.technical_insights)]:
        sections += ["", "## " + heading, ""] + ["- " + inline(v) for v in values]
    concepts = list(dict.fromkeys(c for v in enrichment.related_concepts if (c := concept(v))))
    sections += ["", "## 関連概念", ""] + [f"- [[{c}]]" for c in concepts]
    sections += ["", "## 原文", "", markdown if source.store_full_text else "本文保存はsource設定で無効です。原文URLを参照してください。"]
    name = filename(enrichment.title_ja, fetched_at[:10], content_hash)
    return f"notes/{fetched_at[:4]}/{fetched_at[5:7]}/{name}", "\n".join(sections) + "\n"
