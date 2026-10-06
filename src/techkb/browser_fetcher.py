"""Render through HTTP Fetcher so browser resources obey the same access policy."""
from urllib.parse import urlsplit
from .fetcher import FetchResult, FetchError


class SourceFetcher:
    def __init__(self, http):
        self.http = http

    def get(self, *args, **kwargs):
        return self.http.get(*args, **kwargs)

    def page(self, url, source):
        if source.fetcher == "http":
            return self.http.get(url, source.request_interval_seconds, html=True)
        from playwright.sync_api import sync_playwright
        allowed = {urlsplit(url).hostname, *source.resource_domains}
        initial = self.http.get(url, source.request_interval_seconds, html=True, allowed_hosts=allowed)
        count, size = 0, len(initial.content)
        failure = []
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                context = browser.new_context(service_workers="block", user_agent=self.http.config.user_agent,
                                              accept_downloads=False)
                # No direct WebSocket traffic can escape the HTTP/robots gateway.
                # A routed socket has no server connection unless connect_to_server
                # is called. Leave it isolated; synchronous close in this callback
                # can deadlock the Playwright event loop.
                context.route_web_socket("**/*", lambda ws: None)
                page = context.new_page()
                def route_request(route):
                    nonlocal count, size
                    request = route.request
                    try:
                        if (request.method != "GET" or request.resource_type not in
                                {"document", "script", "stylesheet", "xhr", "fetch"} or
                                urlsplit(request.url).hostname not in allowed):
                            return route.abort()
                        count += 1
                        if count > source.max_browser_requests:
                            raise FetchError("browser request limit")
                        fetched = (initial if request.url == initial.url and count == 1 else
                                   self.http.get(request.url, source.request_interval_seconds, allowed_hosts=allowed))
                        if urlsplit(fetched.url).hostname not in allowed:
                            raise FetchError("browser resource redirect outside allowed domains")
                        if fetched is not initial:
                            size += len(fetched.content)
                        if size > self.http.config.max_response_bytes:
                            raise FetchError("browser resource size limit")
                        route.fulfill(status=200, body=fetched.content,
                                      headers={"content-type": fetched.content_type})
                    except Exception as exc:
                        failure.append(type(exc).__name__)
                        route.abort()
                context.route("**/*", route_request)
                timeout = self.http.config.timeout_seconds * 1000
                page.goto(initial.url, wait_until="load", timeout=timeout)
                if source.render_selector:
                    page.locator(source.render_selector).first.wait_for(timeout=timeout)
                rendered = page.content().encode()
                if failure or len(rendered) > self.http.config.max_response_bytes:
                    raise FetchError("browser resource failed or rendered document exceeded limit")
                return FetchResult(rendered, page.url, 200, "text/html", initial.content)
            finally:
                browser.close()

    def close(self):
        self.http.close()
