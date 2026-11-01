from datetime import datetime, timezone
from urllib.parse import urljoin
import calendar
import feedparser
from .pending import Candidate
from .normalize import normalize_url

def parse_feed(raw: bytes, source, discovered_at: str, tracking=()):
    feed = feedparser.parse(raw)
    if not feed.get("version") or (feed.bozo and not feed.entries):
        raise ValueError("invalid RSS/Atom feed")
    result = []
    for entry in feed.entries:
        link = entry.get("link")
        if not link:
            continue
        try:
            url = normalize_url(urljoin(str(source.base_url), link), tracking)
        except ValueError:
            continue
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        published = datetime.fromtimestamp(calendar.timegm(parsed), timezone.utc).isoformat() if parsed else ""
        result.append(Candidate(discovered_at, source.id, url, published, entry.get("title", "")))
    return result
