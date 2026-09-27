from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .normalize import normalize_url

REMOVE = ("script", "style", "noscript", "svg", "form", "iframe")

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
