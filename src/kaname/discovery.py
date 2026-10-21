"""Identify successful articles before requesting source bodies.

The durable success index is authoritative. Pending/failed work is never added
here, and original RSS URLs remain aliases of a redirected canonical URL.
"""
from .normalize import normalize_url


class KnownArticles:
    def __init__(self, rows, tracking=()):
        self.tracking = tracking
        self.urls = {(row['source_id'], normalize_url(row[field], tracking))
                     for row in rows if row['status'] == 'success'
                     for field in ('source_url', 'canonical_url') if row.get(field)}

    def contains(self, candidate):
        return (candidate.source_id, normalize_url(candidate.url, self.tracking)) in self.urls
