import hashlib
from techkb.hashes import raw_hash, content_hash

def test_hash_bytes_and_unicode():
    assert raw_hash(b"abc") == hashlib.sha256(b"abc").hexdigest()
    assert content_hash("日本語") == hashlib.sha256("日本語".encode()).hexdigest()
    assert raw_hash(b"abc") != raw_hash(b"abc\n")
