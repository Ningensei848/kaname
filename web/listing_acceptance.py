"""Check every static listing against the fixed public dataset."""
from urllib.parse import urljoin, urlsplit

from kaname.publication import ExportError
from kaname.site import PAGE_SIZE, collection_path, ordered_entries, page_path


def audit_listings(manifest, parsed):
    entries = manifest['notes']
    collections = {'index.md': entries, 'browse/dates.md': entries}
    for kind, field in (('sources', 'source_id'), ('categories', 'category')):
        for value in {entry[field] for entry in entries}:
            collections[collection_path(kind, value)] = [e for e in entries if e[field] == value]
    expected_paths = set()
    pages = 0
    for first, subset in collections.items():
        ordered = ordered_entries(subset)
        total = max(1, (len(ordered) + PAGE_SIZE - 1) // PAGE_SIZE)
        for number in range(1, total + 1):
            name = page_path(first, number)[:-3] + '.html'
            expected_paths.add(name)
            soup = parsed.get(name)
            if soup is None:
                raise ExportError('missing_listing_page')
            base = 'http://localhost/kaname/'
            paths = [urlsplit(urljoin(base + name, a['href'])).path for a in soup.select('a.note-card')]
            start = (number - 1) * PAGE_SIZE
            expected = ['/kaname/' + e['path'][:-3] for e in ordered[start:start + PAGE_SIZE]]
            if paths != expected:
                raise ExportError('listing_membership_mismatch')
            for rel, target in (('prev', number - 1), ('next', number + 1)):
                links = soup.select(f'.pagination a[rel="{rel}"]')
                wanted = '/kaname/' + page_path(first, target)[:-3] + '.html' if 1 <= target <= total else None
                actual = urlsplit(urljoin(base + name, links[0]['href'])).path if len(links) == 1 else None
                # Quartz emits extensionless internal links. Root index may
                # also be simplified to the directory URL.
                clean = lambda path: path.removesuffix('.html').removesuffix('/index').rstrip('/') if path else None
                if clean(actual) != clean(wanted) or len(links) > 1:
                    raise ExportError('listing_navigation_mismatch')
            pages += 1
    if any(name not in expected_paths for name, soup in parsed.items() if soup.select('.note-grid')):
        raise ExportError('unexpected_listing_page')
    return pages


def check_listing_navigation(context, page, home, notes):
    from playwright.sync_api import expect
    page.goto(home)
    expect(page.locator('.note-card')).to_have_count(min(PAGE_SIZE, notes))
    assert page.evaluate("performance.getEntriesByType('resource').filter(r => r.name.includes('contentIndex.json')).length") == 0, 'eager_search_index'
    if notes <= PAGE_SIZE:
        return
    page.locator('.pagination a[rel="next"]').click()
    assert '/page/2' in page.url
    expect(page.locator('.note-card')).to_have_count(min(PAGE_SIZE, notes - PAGE_SIZE))
    page.go_back()
    page.wait_for_selector('.note-card')
    expect(page.locator('.note-card')).to_have_count(PAGE_SIZE)
    # Direct navigation and ordinary anchors work with scripting disabled.
    offline = context.browser.new_context(java_script_enabled=False)
    try:
        plain = offline.new_page()
        plain.goto(home + 'page/2')
        expect(plain.locator('.note-card')).to_have_count(min(PAGE_SIZE, notes - PAGE_SIZE))
        plain.locator('.pagination a[rel="prev"]').click()
        expect(plain.locator('.note-card')).to_have_count(PAGE_SIZE)
    finally:
        offline.close()
