from hashlib import sha256

def raw_hash(content: bytes) -> str:
    return sha256(content).hexdigest()

def content_hash(markdown: str) -> str:
    return sha256(markdown.encode("utf-8")).hexdigest()
