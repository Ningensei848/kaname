"""Pure validation of public compact Note bytes against their index row."""
from datetime import datetime, timezone
import re
from urllib.parse import unquote, urlsplit

import yaml

from .composer import concept, inline, code_span
from .normalize import normalize_url
from ._publication_common import ExportError


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
        # Before the input-scope notice was introduced, compact Notes stored
        # only the truncation flag. Recognize that exact earlier structure;
        # never invent a limit or strip arbitrary sections to make it pass.
        legacy_prefix = ("\n# " + inline(meta["title"]) + "\n\n> [!abstract] AI要約\n" +
                         "".join("> " + inline(line) + "\n" for line in meta["description"].splitlines()) +
                         "\n## 重要ポイント\n\n")
        if (meta["llm_input_truncated"] and "llm_input_max_chars" not in meta and
                body.startswith(legacy_prefix)):
            prefix = legacy_prefix
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
