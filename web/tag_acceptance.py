"""Verify tag aliases in the index and through the actual search component."""
import json

from playwright.sync_api import expect

from kaname.publication import ExportError, note_frontmatter
from kaname.tags import canonical_tags


def audit_tags(manifest, original, files):
    index = json.loads(files['static/contentIndex.json'])
    for entry in manifest['notes']:
        meta = note_frontmatter(original[entry['path']])[2]
        actual = index.get(entry['path'][:-3], {}).get('tags')
        if actual != canonical_tags(meta['tags']):
            raise ExportError('tag_index_mismatch')


def check_tag_aliases(page, home):
    found = None
    for term in ('#ai-egent', '#AIエージェント', '#ＡＩ－ＡＧＥＮＴ', '#AI agent', '#ai-agent'):
        page.goto(home)
        page.get_by_role('button', name='検索', exact=True).click()
        bar = page.get_by_placeholder('何かを検索...')
        bar.fill(term)
        expect(bar).to_have_value('#ai-agent')
        expect(page.locator('.result-card').first).to_be_visible(timeout=10000)
        # Search is asynchronous; wait for at least one Note rather than a tag
        # suggestion/no-results card, then compare the actual navigation set.
        expect(page.locator('.result-card[href*="notes/"]').first).to_be_visible(timeout=10000)
        result = page.locator('.result-card[href*="notes/"]').evaluate_all('(links) => links.map(a => a.getAttribute("href")).sort()')
        assert result and (found is None or result == found), 'tag_alias_result_mismatch'
        found = result
    return len(found)


def check_search_shortcuts(page, home):
    for shortcut in ('Control+k', 'Meta+k', 'Control+Shift+k', 'Meta+Shift+k'):
        page.goto(home)
        page.keyboard.press(shortcut)
        bar = page.get_by_placeholder('何かを検索...')
        expect(bar).to_be_visible(timeout=10000)
        expect(bar).to_be_focused()
        expect(bar).to_have_value('#' if 'Shift' in shortcut else '')
        page.keyboard.press('Escape')
        expect(bar).not_to_be_visible()
    return 4
