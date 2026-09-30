from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .normalize import normalize_url

REMOVE = ("script", "style", "noscript", "svg", "form", "iframe")
AUTHOR_META_KEYS = {"author", "article:author", "parsely-author"}

def article_authors(raw: bytes) -> list[str]:
    soup = BeautifulSoup(raw, "html.parser")
    authors = []
    for tag in soup.find_all("meta"):
        key = str(tag.get("name") or tag.get("property") or "").casefold()
        if key not in AUTHOR_META_KEYS:
            continue
        value = " ".join(str(tag.get("content") or "").split())[:300]
        if value and not value.startswith(("http://", "https://")) and value not in authors:
            authors.append(value)
    return authors

def clean_html(raw: bytes) -> bytes:
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup.find_all(REMOVE):
        tag.decompose()
    # Keep image alt text, but no external image requests in Obsidian.
    for image in soup.find_all("img"):
        image.replace_with(image.get("alt", ""))
    return str(soup).encode("utf-8")

def canonical_url(raw: bytes, final_url: str, tracking=()) -> str:
    soup = BeautifulSoup(raw, "html.parser")
    tag = soup.find("link", rel=lambda value: value and "canonical" in value)
    try:
        return normalize_url(urljoin(final_url, tag["href"]), tracking) if tag and tag.get("href") else normalize_url(final_url, tracking)
    except ValueError:
        return normalize_url(final_url, tracking)
