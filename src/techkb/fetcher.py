from dataclasses import dataclass
from urllib.parse import urlsplit, urljoin, urlunsplit
from urllib.robotparser import RobotFileParser
import ipaddress
import logging
import socket
import time
import httpx
from .normalize import normalize_url

log = logging.getLogger(__name__)
RETRY_STATUS = {429, 500, 502, 503, 504}

@dataclass
class FetchResult:
    content: bytes
    url: str
    status: int
    content_type: str

class FetchError(RuntimeError):
    pass

def safe_url(url):
    p = urlsplit(normalize_url(url))
    addresses = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise FetchError("non-public destination blocked")
    return url

def audit_url(url):
    p = urlsplit(url)
    return urlunsplit((p.scheme, p.netloc, p.path, "", ""))

class Fetcher:
    def __init__(self, config, client=None, sleep=time.sleep):
        self.config = config
        self.client = client or httpx.Client(timeout=config.timeout_seconds, follow_redirects=False,
                                            headers={"User-Agent": config.user_agent}, trust_env=False)
        self.sleep = sleep
        self.last_request = {}
        self.robots = {}

    def _request(self, url, interval):
        safe_url(url)
        host = urlsplit(url).netloc
        for attempt in range(self.config.retries + 1):
            wait = interval - (time.monotonic() - self.last_request.get(host, 0))
            if wait > 0:
                self.sleep(wait)
            self.last_request[host] = time.monotonic()
            try:
                with self.client.stream("GET", url) as response:
                    log.info("http url=%s status=%s", audit_url(url), response.status_code)
                    if response.status_code in RETRY_STATUS and attempt < self.config.retries:
                        retry_after = response.headers.get("retry-after", "")
                        delay = min(float(retry_after), 120) if retry_after.isdigit() else min(2**attempt, 30)
                        self.sleep(delay)
                        continue
                    size, chunks = 0, []
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > self.config.max_response_bytes:
                            raise FetchError("response size limit exceeded")
                        chunks.append(chunk)
                    return response, b"".join(chunks)
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt == self.config.retries:
                    raise FetchError("transport failure") from None
                self.sleep(min(2**attempt, 30))
        raise FetchError("retries exhausted")

    def _allowed(self, url, interval):
        p = urlsplit(url)
        origin = f"{p.scheme}://{p.netloc}"
        if origin not in self.robots:
            robot_url = origin + "/robots.txt"
            for _ in range(6):
                response, content = self._request(robot_url, interval)
                if response.status_code in {301, 302, 303, 307, 308}:
                    robot_url = urljoin(robot_url, response.headers.get("location", ""))
                    continue
                break
            robot = RobotFileParser()
            if response.status_code in {404, 410}:
                robot.parse([])
            elif response.status_code == 200:
                robot.parse(content.decode("utf-8", errors="replace").splitlines())
            else:
                raise FetchError("robots unavailable or access denied")
            self.robots[origin] = robot
        robot = self.robots[origin]
        if not robot.can_fetch(self.config.user_agent, url):
            raise FetchError("robots disallows URL")
        return max(interval, robot.crawl_delay(self.config.user_agent) or 0)

    def get(self, url, interval=2, *, html=False):
        for _ in range(6):
            url = normalize_url(url)
            interval = self._allowed(url, interval)
            response, content = self._request(url, interval)
            if response.status_code in {301, 302, 303, 307, 308}:
                if not response.headers.get("location"):
                    raise FetchError("redirect without location")
                url = urljoin(url, response.headers["location"])
                continue
            if response.status_code != 200:
                raise FetchError(f"HTTP {response.status_code}")
            mime = response.headers.get("content-type", "").split(";", 1)[0].lower()
            if html and mime not in {"text/html", "application/xhtml+xml"}:
                raise FetchError("not an HTML response")
            return FetchResult(content, str(response.url), response.status_code, mime)
        raise FetchError("redirect limit exceeded")

    def close(self):
        self.client.close()
