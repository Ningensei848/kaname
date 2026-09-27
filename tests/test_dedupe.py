from techkb.dedupe import Dedupe

def test_only_success_hashes():
    d = Dedupe([dict(status="failed", raw_html_sha256="r", content_sha256="c"),
                dict(status="success", raw_html_sha256="a", content_sha256="b")])
    assert d.raw == {"a"} and d.content == {"b"}
