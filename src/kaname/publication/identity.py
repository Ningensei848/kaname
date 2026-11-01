"""The stable public Note identity shared by export, loading and repair."""
import json

from ..normalize import normalize_url
from .common import sha256


def note_identity(source_id, canonical_url, tracking=()):
    """Preserve schema-v1's UTF-8 compact JSON pair and canonical URL rules."""
    identity = source_id, normalize_url(canonical_url, tracking)
    encoded = json.dumps(identity, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return identity, sha256(encoded)
