"""Browser and link acceptance for a verified, real public Git snapshot."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from playwright.sync_api import expect

from kaname_web.public_input import public_input
from kaname_web.artifact import load_artifact
from techkb.publication import ExportError
from kaname_web.validation import public_version_matches, snapshot_matches
from image_acceptance import approved_images, check_image_pages
from kaname_web.browser_acceptance import served_artifact, browser_session, verify_local_links
from link_acceptance import parse_html, audit_search_links, audit_note_anchors, check_search_click


def check(content, commit, artifact, release_receipt=None, image_workers=2):
    manifest, original, _ = public_input(content, commit, release_receipt)
    marker, files = load_artifact(artifact)
    parsed = parse_html(files)
    search_links = audit_search_links(manifest, original, files, parsed)
    audit_note_anchors(files, parsed)
    image_entries = approved_images(manifest, original)
    approved = {image['url'] for images in image_entries.values() for image in images}
    if (not public_version_matches(marker, commit) or
            not snapshot_matches(marker, manifest, files, original)):
        raise ExportError('pages_provenance_mismatch')
    for soup in parsed.values():
        if soup.select('.fixture-banner') or soup.select('meta[name="robots"][content*="noindex"]'):
            raise ExportError('fixture_in_pages')
    verify_local_links(files, parsed)
    for entry in manifest['notes']:
        soup = parsed['notes/' + entry['id'] + '.html']
        if not soup.find('a', class_='source-link', href=entry['canonical_url']):
            raise ExportError('missing_pages_source')
    search_clicks = 0
    with served_artifact(artifact) as origin:
        home = origin + '/kaname/'
        with browser_session(origin, approved, error_prefix='pages_') as (context, page, observed):
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
                search_clicks = check_search_click(context, page)
                response = context.request.get(home + 'markdown/' + entry['path'])
                assert response.ok and response.body() == original[entry['path']], 'pages_note_bytes_mismatch'
            page.goto(home + 'about/snapshot')
            expect(page.locator('article')).to_contain_text(commit)
            expect(page.locator('article')).to_contain_text(manifest['dataset_digest'])
            for width in (375, 768, 1024, 1440):
                page.set_viewport_size({'width': width, 'height': 900})
                page.goto(home)
                assert page.evaluate('document.documentElement.scrollWidth') <= width, 'horizontal_overflow'
            for path in ('.env', '.git/config', 'state/index.json', 'README.md'):
                assert context.request.get(home + path).status == 404
        # Finish the navigation browser before starting the bounded image pool.
        images_checked = check_image_pages(origin, image_entries, image_workers)
    return dict(status='passed', notes=len(manifest['notes']), content_commit=commit,
                dataset_digest=manifest['dataset_digest'], external_requests=0,
                search_links=search_links, offline_search_clicks=search_clicks,
                approved_image_requests=len(observed.image_requests) + images_checked['requests'],
                image_notes=images_checked['notes'], image_workers=images_checked['workers'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--content', required=True, type=Path)
    parser.add_argument('--content-commit', required=True)
    parser.add_argument('--artifact', required=True, type=Path)
    parser.add_argument('--release-receipt', type=Path)
    parser.add_argument('--image-workers', type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    try:
        print(json.dumps(check(args.content, args.content_commit, args.artifact, args.release_receipt, args.image_workers)))
    except ExportError as exc:
        print(json.dumps(dict(status='failed', code=str(exc))), file=sys.stderr); sys.exit(1)
    except Exception:
        print('{"status":"failed","code":"pages_acceptance_failed"}', file=sys.stderr); sys.exit(1)
