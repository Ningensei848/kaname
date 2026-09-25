from dataclasses import dataclass, asdict
from .normalize import normalize_url

COLUMNS = ["discovered_at", "source_id", "url", "published_at", "title"]

@dataclass
class Candidate:
    discovered_at: str
    source_id: str
    url: str
    published_at: str = ""
    title: str = ""

    def row(self):
        return asdict(self)

def merge_pending(old, new, tracking=()):
    result = {}
    for candidate in [*old, *new]:
        url = normalize_url(candidate.url, tracking)
        candidate = Candidate(**(candidate.row() | {"url": url}))
        result.setdefault(url, candidate)
    return sorted(result.values(), key=lambda c: (c.discovered_at, c.url))
