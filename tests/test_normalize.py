import pytest
from techkb.normalize import normalize_url, normalize_markdown

def test_url_keeps_semantics():
    assert normalize_url("HTTPS://EXAMPLE.COM:443/a?x=a%20b&utm_source=r&x=2&gclid=y#ref") == "https://example.com/a?x=a%20b&x=2"
    assert normalize_url("http://Example.com:80/a?keep=1&track=2", ["track"]) == "http://example.com/a?keep=1"

@pytest.mark.parametrize("url", ["file:///tmp/a", "javascript:alert(1)", "https://user:pw@example.com"])
def test_bad_urls(url):
    with pytest.raises(ValueError):
        normalize_url(url)

def test_normalize_idempotent_and_code():
    md = " A  \r\n\r\n\r\n\r\nB\n```python\nx\n\n\n\ny\n```\n"
    output = normalize_markdown(md)
    assert output.startswith("A\n\n\nB")
    assert "x\n\n\n\ny" in output
    assert normalize_markdown(output) == output
