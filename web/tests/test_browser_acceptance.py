"""Shared browser boundaries must fail and clean up on real page errors."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest
from bs4 import BeautifulSoup

import kaname_web.browser_acceptance as acceptance
from techkb.publication import ExportError


@contextmanager
def page_server(body):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers(); self.wfile.write(body)
        def log_message(self, *_):
            return
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=httpd.serve_forever, daemon=True); thread.start()
    try:
        yield f'http://127.0.0.1:{httpd.server_port}'
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=5)


@pytest.mark.parametrize('body', [
    b'<script>throw new Error("fixture error")</script>',
    b'<img src="https://unapproved.example/image.png">',
])
def test_errors_and_unapproved_requests_fail_and_close_browser(body):
    with page_server(body) as origin:
        with pytest.raises(AssertionError, match='browser_error|external_resource_request'):
            with acceptance.browser_session(origin, set()) as (_, page, observed):
                page.goto(origin)
                page.wait_for_timeout(100)
        assert page.is_closed()
        assert observed.errors or observed.external


def test_body_exception_also_closes_browser():
    with page_server(b'<h1>Fixture</h1>') as origin:
        with pytest.raises(RuntimeError, match='injected'):
            with acceptance.browser_session(origin, set()) as (_, page, _):
                page.goto(origin)
                raise RuntimeError('injected')
        assert page.is_closed()


@pytest.mark.parametrize('link,code', [('/private', 'pages_link_escapes_base'),
                                      ('missing.html', 'missing_pages_link')])
def test_static_link_failures_share_the_same_public_boundary(link, code):
    with pytest.raises(ExportError, match=code):
        acceptance.verify_local_links({'index.html': b'fixture'},
            {'index.html': BeautifulSoup(f'<a href="{link}">test</a>', 'html.parser')})
