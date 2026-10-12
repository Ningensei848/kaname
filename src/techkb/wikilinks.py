"""Conservative Markdown spans, deterministic body links and snapshot resolution."""
import html
import re
from urllib.parse import quote, urlencode

from .markup import concept, inline, plain


GENERIC = frozenset(("ai", "ml", "data", "model", "models", "technology", "software",
                     "research", "security", "cloud", "api", "人工知能", "機械学習", "データ",
                     "モデル", "技術", "研究", "ソフトウェア", "セキュリティ", "クラウド"))
WIKI = re.compile(r"\[\[([^\[\]\n]+)\]\]")


def _balanced(text, start, opening, closing):
    depth, i = 0, start
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == opening:
            depth += 1
        elif text[i] == closing:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return start


def spans(text):
    """Yield text/wiki/protected spans; links never nest into protected syntax."""
    i, start = 0, 0
    while i < len(text):
        end, kind = i, "protected"
        if i == 0 or text[i - 1] == "\n":
            fence = re.match(r" {0,3}(`{3,}|~{3,})[^\n]*(?:\n|$)", text[i:])
            if fence:
                marker = fence[1]
                closing = re.search(r"^ {0,3}" + re.escape(marker[0]) + "{" + str(len(marker)) + r",}[ \t]*(?:\n|$)",
                                    text[i + fence.end():], re.MULTILINE)
                end = i + fence.end() + closing.end() if closing else len(text)
            elif text.startswith(("    ", "\t"), i):
                newline = text.find("\n", i)
                end = len(text) if newline < 0 else newline + 1
        if end == i:
            if text[i] == "\\" and i + 1 < len(text):
                end = i + 2
            elif text[i] == "`":
                marker = re.match(r"`+", text[i:])[0]
                closing = re.search(r"(?<!`)" + re.escape(marker) + r"(?!`)", text[i + len(marker):])
                if closing:
                    end = i + len(marker) + closing.end()
            elif text.startswith("![[", i):
                match = WIKI.match(text, i + 1)
                if match:
                    end = match.end()
            elif text.startswith("[[", i):
                match = WIKI.match(text, i)
                if match:
                    end, kind = match.end(), "wiki"
            elif text[i] == "[" or text.startswith("![", i):
                label = i + (1 if text[i] == "!" else 0)
                close = _balanced(text, label, "[", "]")
                if close > label:
                    if text[close:close + 1] == "(":
                        end = _balanced(text, close, "(", ")")
                    elif text[close:close + 1] == "[":
                        end = _balanced(text, close, "[", "]")
                    else:
                        # Also preserve reference/shortcut labels and definitions.
                        end = close
            elif text[i] == "<":
                close = text.find(">", i + 1)
                if close >= 0:
                    end = close + 1
            elif text.startswith(("https://", "http://"), i):
                end = re.match(r"https?://[^\s<>]+", text[i:]).end() + i
        if end > i:
            if start < i:
                yield "text", text[start:i]
            yield kind, text[i:end]
            i = start = end
        else:
            i += 1
    if start < len(text):
        yield "text", text[start:]


def map_wikilinks(text, replace):
    return "".join(replace(value[2:-2]) if kind == "wiki" else value for kind, value in spans(text))


def body_concepts(values):
    return sorted({value for value in values if value == concept(value) and
                   len(value) >= 3 and value.casefold() not in GENERIC}, key=lambda v: (-len(v), v))


def linked_inline(value, values):
    """Escape raw LLM prose, inserting only reviewed candidate occurrences."""
    candidates = body_concepts(values)
    if not candidates:
        return inline(value)
    pattern = re.compile("|".join(re.escape(term) for term in candidates))
    # inline() strips surrounding whitespace; escape spans without losing it.
    escape = lambda text: re.sub(r"([\\`*_{}\[\]()<>!#|])", r"\\\1", text)
    result = []
    for kind, text in spans(plain(value)):
        if kind != "text":
            result.append(escape(text))
            continue
        start = 0
        for match in pattern.finditer(text):
            term = match[0]
            if re.search(r"[A-Za-z0-9]", term) and (
                    match.start() and re.match(r"[A-Za-z0-9_+#]", text[match.start() - 1]) or
                    match.end() < len(text) and re.match(r"[A-Za-z0-9_+#]", text[match.end()])):
                continue
            result.extend((escape(text[start:match.start()]), "[[" + term + "]]"))
            start = match.end()
        result.append(escape(text[start:]))
    return "".join(result)


def search_link(term, label):
    href = "https://www.google.com/search?" + urlencode({"q": term})
    explanation = label + "をGoogle検索で調べる（新しいタブ）"
    return ('<a class="concept-search" href="' + html.escape(href, quote=True) +
            '" target="_blank" rel="noopener noreferrer" aria-label="' +
            html.escape(explanation, quote=True) + '">' + html.escape(label) +
            ' <span aria-hidden="true">↗</span></a>')


def project_wikilinks(text, titles, current_id):
    def resolve(value):
        value = value.replace(r"\|", "|")
        target, separator, label = value.partition("|")
        title, anchor_sep, anchor = target.partition("#")
        shown = label if separator else target
        candidates = [current_id] if not title and anchor_sep else titles.get(title, [])
        if len(candidates) == 1:
            fragment = "#" + quote(anchor.lower().replace(" ", "-"), safe="-_") if anchor_sep else ""
            return "[" + inline(shown) + "](" + candidates[0] + fragment + ")"
        return search_link(title or target, shown)
    return map_wikilinks(text, resolve)
