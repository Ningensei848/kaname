import re
from urllib.parse import urlsplit, urlunsplit, unquote_plus

def normalize_url(url: str, tracking_parameters=()) -> str:
    p = urlsplit(url.strip())
    if p.scheme.lower() not in {"http", "https"} or not p.hostname or p.username or p.password:
        raise ValueError("only public HTTP(S) URLs without credentials are supported")
    host = p.hostname.lower().encode("idna").decode()
    if ":" in host:
        host = f"[{host}]"
    port = p.port
    scheme = p.scheme.lower()
    netloc = host if not port or (scheme, port) in {("http", 80), ("https", 443)} else f"{host}:{port}"
    excluded = {x.lower() for x in tracking_parameters} | {"fbclid", "gclid"}
    # Preserve order and exact encoding of meaningful query parameters.
    query = "&".join(part for part in p.query.split("&") if part and
                     not (unquote_plus(part.split("=", 1)[0]).lower().startswith("utm_") or
                          unquote_plus(part.split("=", 1)[0]).lower() in excluded))
    return urlunsplit((scheme, netloc, p.path or "/", query, ""))

def normalize_markdown(text: str) -> str:
    # Blank lines in fenced code are content; preserve them.
    out, blanks, fence = [], 0, None
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = line.rstrip()
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and not line.strip()[len(token):].strip():
                fence = None
        blanks = blanks + 1 if not line else 0
        if fence or blanks <= 2:
            out.append(line)
    return "\n".join(out).strip()
