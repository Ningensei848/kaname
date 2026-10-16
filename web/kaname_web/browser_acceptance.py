"""Shared acceptance infrastructure; never imported by deployed byte checks."""
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Thread
from urllib.parse import unquote, urljoin, urlsplit

from playwright.sync_api import sync_playwright

from serve import server
from image_acceptance import image_guard
from techkb.publication import ExportError


@contextmanager
def served_artifact(artifact):
    httpd = server(artifact, 0)
    thread = Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{httpd.server_port}'
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


@dataclass
class BrowserObservations:
    errors: list = field(default_factory=list)
    external: list = field(default_factory=list)
    image_requests: list = field(default_factory=list)


@contextmanager
def browser_session(origin, approved, *, error_prefix=''):
    observed = BrowserObservations()
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        try:
            context = browser.new_context(viewport={'width': 1440, 'height': 1000})
            context.route('**/*', lambda route: image_guard(
                route, origin, approved, observed.external, observed.image_requests))
            page = context.new_page()
            page.on('pageerror', lambda error: observed.errors.append(str(error)))
            page.on('console', lambda message: observed.errors.append(message.type) if message.type == 'error' else None)
            yield context, page, observed
            assert not observed.errors, error_prefix + 'browser_error'
            assert not observed.external, error_prefix + 'external_resource_request'
        finally:
            browser.close()


def verify_local_links(files, parsed, *, skip_not_found=False):
    base = 'http://127.0.0.1/kaname/'
    for name, soup in parsed.items():
        if skip_not_found and name == '404.html':
            continue
        for tag in soup.select('[href], [src]'):
            target = urlsplit(urljoin(base + name, tag.get('href', tag.get('src'))))
            if target.netloc != '127.0.0.1' or target.path == '/kaname':
                continue
            if not target.path.startswith('/kaname/'):
                raise ExportError('pages_link_escapes_base')
            path = unquote(target.path.removeprefix('/kaname/')) or 'index.html'
            if path.endswith('/'):
                path += 'index.html'
            if path not in files and path + '.html' not in files:
                raise ExportError('missing_pages_link')
