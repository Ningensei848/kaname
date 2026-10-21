"""Audit search links and exercise a new-tab navigation without Google traffic."""
from collections import Counter
from urllib.parse import unquote, urljoin, urlsplit

from bs4 import BeautifulSoup

from kaname.publication import ExportError, note_frontmatter
from kaname.wikilinks import project_wikilinks, spans


def parse_html(files):
    """Parse each verified HTML file once, for this acceptance invocation only."""
    return {name: BeautifulSoup(data, 'html.parser') for name, data in files.items() if name.endswith('.html')}


def audit_search_links(manifest, original, files, parsed=None):
    titles = {}
    for entry in manifest['notes']:
        titles.setdefault(entry['title'], []).append(entry['id'])
    count = 0
    for entry in manifest['notes']:
        text, match, _ = note_frontmatter(original[entry['path']])
        expected = []
        for kind, value in spans(text[match.end():]):
            if kind == 'wiki':
                rendered = project_wikilinks(value, titles, entry['id'])
                expected.extend(BeautifulSoup(rendered, 'html.parser').select('a.concept-search'))
        path = 'notes/' + entry['id'] + '.html'
        soup = BeautifulSoup(files[path], 'html.parser') if parsed is None else parsed[path]
        actual = soup.select('a.concept-search')
        signature = lambda link: (link.get('href'), link.get('aria-label'), link.get_text(' ', strip=True))
        if Counter(map(signature, expected)) != Counter(map(signature, actual)):
            raise ExportError('search_link_mismatch')
        for link in actual:
            if link.get('target') != '_blank' or set(link.get('rel', [])) != {'noopener', 'noreferrer'}:
                raise ExportError('unsafe_search_link')
        count += len(actual)
    # An external search must never become a Note graph edge.
    import json
    index = json.loads(files['static/contentIndex.json'])
    if any('google.com' in link for entry in index.values() for link in entry.get('links', [])):
        raise ExportError('search_link_in_graph')
    return count


def audit_note_anchors(files, parsed=None):
    base = 'http://127.0.0.1/kaname/'
    parsed = parse_html(files) if parsed is None else parsed
    identifiers = {name: {tag['id'] for tag in soup.find_all(id=True)} for name, soup in parsed.items()}
    for name, soup in parsed.items():
        for link in soup.select('a[href]'):
            target = urlsplit(urljoin(base + name, link['href']))
            if target.netloc != '127.0.0.1' or not target.fragment:
                continue
            path = unquote(target.path.removeprefix('/kaname/')) or 'index.html'
            if path.endswith('/'):
                path += 'index.html'
            if path not in parsed:
                path += '.html'
            if path in parsed and unquote(target.fragment) not in identifiers[path]:
                raise ExportError('missing_note_anchor')


def check_search_click(context, page):
    link = page.locator('article a.concept-search').first
    if link.count() == 0:
        return 0
    href = link.get_attribute('href')
    requests = []
    def intercept(route):
        requests.append(route.request.url)
        route.fulfill(status=200, content_type='text/html', body='<title>Offline search navigation</title>')
    context.route('https://www.google.com/**', intercept)
    popup = None
    viewport = page.viewport_size
    try:
        for width in (375, 768, 1024, 1440):
            page.set_viewport_size({'width': width, 'height': 900})
            assert page.evaluate('document.documentElement.scrollWidth') <= width, 'search_horizontal_overflow'
        page.set_viewport_size(viewport)
        with page.expect_popup() as event:
            link.click()
        popup = event.value
        popup.wait_for_load_state('domcontentloaded')
        assert popup.url == href and requests == [href], 'wrong_search_navigation'
        assert popup.evaluate('window.opener === null'), 'search_opener_present'
    finally:
        page.set_viewport_size(viewport)
        if popup:
            popup.close()
        context.unroute('https://www.google.com/**', intercept)
    return 1
