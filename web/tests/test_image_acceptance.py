"""Bounded real browsers keep all image checks and reject worker failures."""
from collections import Counter
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Barrier, Lock, Thread

import pytest

from image_acceptance import check_image_pages


@contextmanager
def pages(script='', barrier=None):
    visited = []; lock = Lock()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if not self.path.startswith('/kaname/notes/'):
                self.send_error(404); return
            with lock: visited.append(self.path.rsplit('/', 1)[1])
            if barrier is not None: barrier.wait(timeout=20)
            data = ('<html><head></head><body><article><img src="https://example.com/approved.svg" '
                    'style="max-width:100%"></article><script>' + script + '</script></body></html>').encode()
            self.send_response(200); self.end_headers(); self.wfile.write(data)
        def log_message(self, *args): pass
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=httpd.serve_forever, daemon=True); thread.start()
    try: yield f'http://127.0.0.1:{httpd.server_port}', visited
    finally: httpd.shutdown(); httpd.server_close(); thread.join(timeout=5)


def test_two_browsers_visit_each_note_once_with_offline_images():
    entries = {name: [{'url': 'https://example.com/approved.svg'}] for name in ('a', 'b', 'c', 'd')}
    entries['without-images'] = []
    with pages(barrier=Barrier(2)) as (origin, visited):
        result = check_image_pages(origin, entries, workers=2)
    assert result == dict(notes=4, requests=4, workers=2)
    assert Counter(visited) == Counter(a=1, b=1, c=1, d=1)


@pytest.mark.parametrize('script', ['throw new Error("worker failure")', 'fetch("https://unexpected.example/resource")'])
def test_failure_in_any_worker_prevents_acceptance(script):
    entries = {name: [{'url': 'https://example.com/approved.svg'}] for name in ('a', 'b')}
    with pages(script=script) as (origin, _):
        with pytest.raises(AssertionError, match='pages_(browser_error|external_resource_request)'):
            check_image_pages(origin, entries, workers=2)


def test_serial_rollback_and_empty_input():
    assert check_image_pages('http://unused.invalid', {'a': []}) == dict(notes=0, requests=0, workers=0)
    with pages() as (origin, visited):
        assert check_image_pages(origin, {'a': [{'url': 'https://example.com/approved.svg'}]}, workers=1) == dict(notes=1, requests=1, workers=1)
    assert visited == ['a']
