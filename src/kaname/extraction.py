"""Opt-in extraction and deterministic relevance; no LLM decisions."""
import unicodedata
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup
from .normalize import normalize_url
from .pending import Candidate


def extract_main(raw, selector=None):
    soup = BeautifulSoup(raw, "html.parser")
    if selector:
        selected = soup.select(selector)
        if not selected:
            raise ValueError("content selector did not match")
        return "\n".join(str(node) for node in selected).encode()
    for node in soup.select("script,style,noscript,nav,header,footer,aside,form,iframe"):
        node.decompose()
    nodes = soup.select("article") or soup.select("main")
    if nodes:
        return str(max(nodes, key=lambda n: len(n.get_text(" ", strip=True)))).encode()
    # Prefer the densest substantial semantic block; retain body for simple pages.
    blocks = soup.select("section,div")
    if blocks:
        node = max(blocks, key=lambda n: len(n.get_text(" ", strip=True)))
        if len(node.get_text(" ", strip=True)) >= 200:
            return str(node).encode()
    return str(soup.body or soup).encode()


def parse_listing(raw, url, source, discovered_at, tracking=()):
    result, seen = [], set()
    for node in BeautifulSoup(raw, "html.parser").select(source.link_selector):
        if not node.get("href"):
            continue
        try:
            link = normalize_url(urljoin(url, node["href"]), tracking)
        except ValueError:
            continue
        # Listings may contain navigation to external sites; require same origin.
        if urlsplit(link).netloc != urlsplit(url).netloc or link in seen:
            continue
        seen.add(link)
        result.append(Candidate(discovered_at, source.id, link, "", node.get_text(" ", strip=True)))
    return result


def folded(value):
    return unicodedata.normalize("NFKC", value).casefold()


def relevance(source, candidate, markdown):
    rules = source.relevant_filter
    host = (urlsplit(candidate.url).hostname or "").lower()
    text = folded(candidate.title + "\n" + markdown)
    category = folded(source.category)
    # Domain entries match exactly; explicit '*.example.com' includes subdomains.
    def domain(value):
        value = value.lower().rstrip(".")
        return host == value or (value.startswith("*.") and host.endswith(value[1:]))
    for dimension, includes, excludes, matches in (
        ("domain", rules.include_domains, rules.exclude_domains, domain),
        ("category", rules.include_categories, rules.exclude_categories, lambda v: folded(v) == category),
        ("keyword", rules.include_keywords, rules.exclude_keywords, lambda v: bool(v.strip()) and folded(v) in text),
    ):
        if any(matches(v) for v in excludes):
            return dimension + "_excluded"
        if includes and not any(matches(v) for v in includes):
            return dimension + "_not_included"
    return None
