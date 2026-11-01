"""Audit search links and exercise a new-tab navigation without Google traffic."""
from collections import Counter
from urllib.parse import unquote, urljoin, urlsplit

from bs4 import BeautifulSoup

from kaname.publication import ExportError, note_frontmatter
from kaname.wikilinks import project_wikilinks, spans
from kaname.graph_quality import shared_keyword_links


def audit_shared_keyword_links(manifest, original, files, parsed):
    import json
    expected = shared_keyword_links(manifest, original)
    index = json.loads(files['static/contentIndex.json'])
    count = 0
    for entry in manifest['notes']:
        soup = parsed['notes/' + entry['id'] + '.html']
        actual = soup.select('.shared-keywords a.shared-keyword-note')
        targets = [urlsplit(urljoin('http://localhost/kaname/notes/' + entry['id'], a['href'])).path
                   for a in actual]
        wanted = ['/kaname/notes/' + link['note_id'] for link in expected[entry['id']]]
        if targets != wanted:
            raise ExportError('shared_keyword_link_mismatch')
        explanations = [tag.get_text() for tag in soup.select('.shared-keyword-terms')]
        if explanations != ['共通: ' + ' · '.join(link['terms']) for link in expected[entry['id']]]:
            raise ExportError('shared_keyword_explanation_mismatch')
        edges = index[entry['path'][:-3]].get('links', [])
        if any('notes/' + link['note_id'] not in edges for link in expected[entry['id']]):
            raise ExportError('shared_keyword_edge_missing_from_index')
        count += len(actual)
    return count


def check_shared_keyword_navigation(page, home, manifest, original):
    from playwright.sync_api import expect
    links = shared_keyword_links(manifest, original)
    source = next((note_id for note_id in sorted(links) if links[note_id]), None)
    if source is None:
        return 0
    target = links[source][0]['note_id']
    title = next(entry['title'] for entry in manifest['notes'] if entry['id'] == target)
    for width in (375, 768, 1024, 1440):
        page.set_viewport_size({'width': width, 'height': 900})
        page.goto(home + 'notes/' + source)
        assert page.evaluate('document.documentElement.scrollWidth') <= width, 'related_note_horizontal_overflow'
        page.locator('a.shared-keyword-note').first.click()
        expect(page.locator('h1.article-title')).to_have_text(title)
        page.go_back()
        expect(page.locator('a.shared-keyword-note').first).to_be_visible()
    return 1


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
