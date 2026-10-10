"""Article image candidates and selection validation; never fetch image bytes."""
import ipaddress
import re
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup


def image_url(value):
    if not isinstance(value, str) or len(value) > 2048 or re.search(r'[\s<>"\\\x00-\x1f\x7f]', value):
        raise ValueError("invalid_image_url")
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    if (parsed.scheme != "https" or not host or parsed.username is not None or
            parsed.password is not None or parsed.fragment or parsed.port not in (None, 443) or
            "." not in host or host.endswith((".local", ".localhost", ".internal"))):
        raise ValueError("invalid_image_url")
    if any(not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?', label)
           for label in host.split('.')):
        raise ValueError("invalid_image_url")
    # Browsers also interpret shortened/octal/hexadecimal IPv4 spellings.
    if re.fullmatch(r'(?:[0-9]+|0x[0-9a-f]+)', host.rsplit('.', 1)[-1], re.IGNORECASE):
        raise ValueError("invalid_image_url")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("invalid_image_url")
    if re.search(r'[?&](?:[^=&]*(?:token|secret|password|signature|credential)|sig|key|api_key)=',
                 unquote(value), re.IGNORECASE):
        raise ValueError("invalid_image_url")
    safe = "/:@!$&'()*+,;=-._~%"
    return urlunsplit(("https", host, quote(parsed.path, safe=safe),
                       quote(parsed.query, safe=safe + "?"), ""))


def article_images(raw, base_url, input_markdown):
    soup = BeautifulSoup(raw, "html.parser")
    for node in soup.select("script,style,noscript,nav,header,footer,aside,form,iframe"):
        node.decompose()
    roots = soup.select("article") or soup.select("main") or [soup]
    visible = " ".join(input_markdown.split())
    candidates, seen = [], set()
    for image in (image for root in roots for image in root.find_all("img")):
        if any(str(image.get(k, "")).isdigit() and int(image[k]) <= 2 for k in ("width", "height")):
            continue
        try:
            src = image.get("data-src") or image.get("src")
            if not src:
                continue
            url = image_url(urljoin(base_url, src))
        except ValueError:
            continue
        if url in seen:
            continue
        alt = " ".join(str(image.get("alt") or "").split())[:300]
        if re.search(r'<[^>]+>|!\[|javascript\s*:|data\s*:', alt, re.IGNORECASE):
            continue
        figure = image.find_parent("figure")
        caption_node = figure.find("figcaption") if figure else None
        caption = " ".join(caption_node.get_text(" ", strip=True).split())[:300] if caption_node else ""
        if not alt and re.search(r'<[^>]+>|!\[|javascript\s*:|data\s*:', caption, re.IGNORECASE):
            continue
        nearby = image.find_previous(["p", "h2", "h3"])
        context = " ".join(nearby.get_text(" ", strip=True).split())[:300] if nearby else ""
        # Exclude candidates whose textual evidence lies beyond the input cut.
        evidence = caption or alt or context
        if not evidence or evidence not in visible or not urlsplit(url).path:
            continue
        if context not in visible:
            context = ""
        seen.add(url)
        candidates.append(dict(image_id=f"img-{len(candidates) + 1}", url=url,
                               alt=alt or caption or "記事の画像", caption=caption, context=context))
        if len(candidates) == 12:
            break
    return candidates


def image_context(candidates):
    return [{key: value for key, value in candidate.items() if key != "url"} for candidate in candidates]


def selected_images(enrichment, candidates):
    by_id = {candidate["image_id"]: candidate for candidate in candidates}
    result, seen = [], set()
    for selection in enrichment.images:
        if (selection.image_id not in by_id or selection.image_id in seen or
                (selection.after.startswith("key_point_") and
                 int(selection.after[-1]) > len(enrichment.key_points))):
            raise ValueError("invalid_image_selection")
        candidate = by_id[selection.image_id]
        result.append(dict(image_id=selection.image_id, url=image_url(candidate["url"]),
                           alt=candidate["alt"], after=selection.after))
        seen.add(selection.image_id)
    return result
