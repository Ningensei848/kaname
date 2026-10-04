"""Browser acceptance of a synthetic static artifact, never a production run."""
import argparse
import json
from pathlib import Path
import sys
from threading import Thread
from urllib.parse import urljoin, urlsplit

from playwright.sync_api import sync_playwright, expect

from serve import WEB, server
from techkb.site import load_artifact
from techkb.publication import sha256


def check(artifact, screenshots=None):
    marker, files = load_artifact(artifact)
    if marker["fixture"] is not True:
        raise ValueError("fixture_required")
    manifest = json.loads(files["markdown/manifest.json"])
    httpd = server(artifact, 0)
    thread = Thread(target=httpd.serve_forever, daemon=True); thread.start()
    origin = f"http://127.0.0.1:{httpd.server_port}"
    home = origin + "/kaname/"
    errors, external = [], []
    try:
        with sync_playwright() as runtime:
            browser = runtime.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            def guard(route):
                if route.request.url.startswith(origin + "/"):
                    route.continue_()
                else:
                    external.append(route.request.url); route.abort()
            context.route("**/*", guard)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.type) if message.type == "error" else None)
            page.goto(home)
            expect(page.locator(".note-card")).to_have_count(3)
            expect(page.locator(".fixture-banner")).to_be_visible()
            assert page.locator('meta[name="robots"]').get_attribute("content") == "noindex, nofollow"
            page.evaluate("document.fonts.ready")
            if screenshots:
                screenshots.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(screenshots / "desktop.png"), full_page=True)
            # Search a Japanese phrase, then follow the actual result.
            page.get_by_role("button", name="検索", exact=True).click()
            page.get_by_placeholder("何かを検索...").fill("再実行")
            result = page.locator('.result-card').filter(has_text="失敗から再実行できるバッチ設計").first
            expect(result).to_be_visible(timeout=10000)
            result.click()
            expect(page.locator("h1.article-title")).to_have_text("失敗から再実行できるバッチ設計")
            expect(page.locator("article")).to_contain_text("先頭20,000文字だけを要約")
            expect(page.locator("article")).to_contain_text("知識の育て方")
            assert page.locator('article a').filter(has_text="知識の育て方").count() == 0
            related = page.locator('article a').filter(has_text="検索から知識にたどり着く").first
            related.click()
            expect(page.locator("h1.article-title")).to_have_text("検索から知識にたどり着く")
            # Inspect every Note and compare downloaded original bytes.
            for entry in manifest["notes"]:
                page.goto(home + "notes/" + entry["id"])
                expect(page.locator("h1.article-title")).to_have_text(entry["title"])
                expect(page.locator(".source-link")).to_have_attribute("href", entry["canonical_url"])
                link = page.get_by_role("link", name="Markdownを取得 ↗")
                response = context.request.get(urljoin(page.url, link.get_attribute("href")))
                assert response.ok and sha256(response.body()) == entry["sha256"]
            # Every local HTML navigation/asset link resolves under /kaname/.
            for name in files:
                if not name.endswith(".html") or name == "404.html": continue
                page.goto(home + name)
                links = page.locator('[href], [src]').evaluate_all('(es)=>es.map(e=>e.getAttribute("href") ?? e.getAttribute("src"))')
                for link in links:
                    target = urljoin(page.url, link)
                    if not target.startswith(origin + "/"): continue
                    assert urlsplit(target).path.startswith("/kaname/"), "base_path_escape"
                    assert context.request.get(target).ok, "missing_local_link"
            for width in (375, 768, 1024, 1440):
                page.set_viewport_size({"width": width, "height": 900})
                page.goto(home)
                assert page.evaluate("document.documentElement.scrollWidth") <= width, "horizontal_overflow"
                expect(page.get_by_role("button", name="検索", exact=True)).to_be_visible()
                if width == 375 and screenshots:
                    page.evaluate("document.fonts.ready")
                    page.screenshot(path=str(screenshots / "mobile.png"), full_page=True)
                page.locator(".darkmode").click()
                assert page.locator("html").get_attribute("saved-theme") == "dark"
                page.locator(".darkmode").click()
            # Requests for files absent from the completion manifest are refused.
            for path in (".env", "state/index.json", "HANDOFF.md", "markdown/../.env"):
                assert context.request.get(home + path).status == 404
            assert not errors, "browser_error"
            assert not external, "external_resource_request"
            browser.close()
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=5)
    return dict(status="passed", notes=len(manifest["notes"]), browser="chromium", external_requests=0,
                dataset_digest=marker["dataset_digest"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    try:
        artifact = args.artifact or json.loads((WEB / ".cache/last-build.json").read_bytes())["output"]
        print(json.dumps(check(artifact, args.screenshots)))
    except Exception:
        # Do not print rendered content or Playwright's assertion snapshots.
        print("web_acceptance_failed", file=sys.stderr); sys.exit(1)
