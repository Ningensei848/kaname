from techkb.html_cleaner import article_authors


def test_article_authors_from_meta():
    raw = b'''<html><head>
        <meta name="author" content=" Alice   Example ">
        <meta property="article:author" content="Bob Example">
        <meta name="author" content="Alice Example">
    </head></html>'''
    assert article_authors(raw) == ["Alice Example", "Bob Example"]


def test_article_authors_ignore_profile_urls():
    raw = b'<meta property="article:author" content="https://example.com/authors/alice">'
    assert article_authors(raw) == []
