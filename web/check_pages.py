"""Browser and link acceptance for a verified, real public Git snapshot."""
import argparse
import json
from pathlib import Path
import sys
from threading import Thread
from urllib.parse import unquote, urljoin, urlsplit

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, expect

from serve import server
from techkb.publication.git_snapshot import content_snapshot
from kaname_web.artifact import load_artifact
from techkb.publication import ExportError
from kaname_web.validation import public_version_matches, snapshot_matches
from image_acceptance import approved_images, image_guard, check_images


def check(content, commit, artifact):
    manifest, original, _ = content_snapshot(content, commit)
    marker, files = load_artifact(artifact)
    image_entries = approved_images(manifest, original)
    approved = {image['url'] for images in image_entries.values() for image in images}
    if (not public_version_matches(marker, commit) or
            not snapshot_matches(marker, manifest, files, original)):
        raise ExportError('pages_provenance_mismatch')
    # Resolve every static local navigation/asset link against the same artifact.
    base = 'http://127.0.0.1/kaname/'
    for name, data in files.items():
        if not name.endswith('.html'):
            continue
        soup = BeautifulSoup(data, 'html.parser')
        if soup.select('.fixture-banner') or soup.select('meta[name="robots"][content*="noindex"]'):
            raise ExportError('fixture_in_pages')
        for tag in soup.select('[href], [src]'):
            value = tag.get('href', tag.get('src'))
            target = urlsplit(urljoin(base + name, value))
            if target.netloc != '127.0.0.1':
                continue
            if target.path == '/kaname':
                continue  # Project Pages redirects its bare base path to /kaname/.
            if not target.path.startswith('/kaname/'):
                raise ExportError('pages_link_escapes_base')
            path = unquote(target.path.removeprefix('/kaname/')) or 'index.html'
            if path.endswith('/'):
                path += 'index.html'
            if path not in files and path + '.html' not in files:
                raise ExportError('missing_pages_link')
    for entry in manifest['notes']:
        soup = BeautifulSoup(files['notes/' + entry['id'] + '.html'], 'html.parser')
        if not soup.find('a', class_='source-link', href=entry['canonical_url']):
            raise ExportError('missing_pages_source')
    httpd = server(artifact, 0)
    thread = Thread(target=httpd.serve_forever, daemon=True); thread.start()
    origin = f'http://127.0.0.1:{httpd.server_port}'
    home = origin + '/kaname/'
    errors, external, image_requests = [], [], []
    try:
        with sync_playwright() as runtime:
            browser = runtime.chromium.launch()
            context = browser.new_context(viewport={'width': 1440, 'height': 1000})
            def guard(route):
                image_guard(route, origin, approved, external, image_requests)
            context.route('**/*', guard)
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda message: errors.append(message.type) if message.type == 'error' else None)
            page.goto(home)
            expect(page.locator('.note-card')).to_have_count(len(manifest['notes']))
            if manifest['notes']:
                entry = manifest['notes'][0]
                page.get_by_role('button', name='検索', exact=True).click()
                page.get_by_placeholder('何かを検索...').fill(entry['title'])
                result = page.locator('.result-card[href*="' + entry['id'] + '"]').first
                expect(result).to_be_visible(timeout=10000)
                result.click()
                expect(page.locator('h1.article-title')).to_have_text(entry['title'])
                expect(page.locator('.source-link')).to_have_attribute('href', entry['canonical_url'])
                response = context.request.get(home + 'markdown/' + entry['path'])
                assert response.ok and response.body() == original[entry['path']], 'pages_note_bytes_mismatch'
            for entry in manifest['notes']:
                if image_entries[entry['id']]:
                    page.goto(home + 'notes/' + entry['id'])
                    check_images(page, image_entries[entry['id']])
            page.goto(home + 'about/snapshot')
            expect(page.locator('article')).to_contain_text(commit)
            expect(page.locator('article')).to_contain_text(manifest['dataset_digest'])
            for width in (375, 768, 1024, 1440):
                page.set_viewport_size({'width': width, 'height': 900})
                page.goto(home)
                assert page.evaluate('document.documentElement.scrollWidth') <= width, 'horizontal_overflow'
            for path in ('.env', '.git/config', 'state/index.json', 'README.md'):
                assert context.request.get(home + path).status == 404
            assert not errors, 'pages_browser_error'
            assert not external, 'pages_external_resource_request'
            browser.close()
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=5)
    return dict(status='passed', notes=len(manifest['notes']), content_commit=commit,
                dataset_digest=manifest['dataset_digest'], external_requests=0,
                approved_image_requests=len(image_requests))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--content', required=True, type=Path)
    parser.add_argument('--content-commit', required=True)
    parser.add_argument('--artifact', required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(check(args.content, args.content_commit, args.artifact)))
    except ExportError as exc:
        print(json.dumps(dict(status='failed', code=str(exc))), file=sys.stderr); sys.exit(1)
    except Exception:
        print('{"status":"failed","code":"pages_acceptance_failed"}', file=sys.stderr); sys.exit(1)
