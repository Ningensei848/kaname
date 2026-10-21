from pathlib import Path
import json
import subprocess

import pytest
from playwright.sync_api import sync_playwright, expect

from test_browser_acceptance import page_server
from kaname.tags import alias_map


@pytest.mark.parametrize('connection,target,wanted', [
    ({'effectiveType': '4g'}, '/kaname/page/2', 1),
    ({'effectiveType': '2g'}, '/kaname/page/2', 0),
    ({'effectiveType': 'slow-2g'}, '/kaname/page/2', 0),
    ({'saveData': True}, '/kaname/page/2', 0),
    ({}, 'https://external.example/page/2', 0),
    ({}, '/private', 0),
])
def test_prefetch_is_one_document_after_load_with_connection_controls(connection, target, wanted):
    source = (Path(__file__).resolve().parents[1] / 'pagination.js').read_text()
    body = f'<html><head></head><body><nav class="pagination"><a rel="next" href="{target}">Next</a></nav></body></html>'.encode()
    with page_server(body) as origin, sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        try:
            page = browser.new_page()
            page.add_init_script('Object.defineProperty(navigator, "connection", {value: ' + json.dumps(connection) + '})')
            page.goto(origin + '/kaname/')
            page.evaluate(source)
            if wanted:
                expect(page.locator('link[rel="prefetch"]')).to_have_count(1)
                assert page.locator('link[rel="prefetch"]').get_attribute('href') == origin + target
                assert page.locator('link[rel="prefetch"]').get_attribute('as') == 'document'
            else:
                page.wait_for_timeout(250)
                assert page.locator('link[rel="prefetch"]').count() == 0
        finally:
            browser.close()


def test_lazy_search_retries_a_failed_load_and_replays_the_open_action():
    source = '''async function setup() {
      const response = await fetch('/index.json');
      if (!response.ok) throw Error('unavailable');
      document.querySelector('.search-button').addEventListener('click', () => {
        document.querySelector('#result').textContent = 'Search ready';
      });
    }
    document.addEventListener("nav",setup);document.addEventListener("render",setup);'''
    web = Path(__file__).resolve().parents[1]
    wrapped = subprocess.check_output(['node', '--input-type=module', '-e',
        "import {lazySearchScript} from './lazy-search.mjs'; process.stdout.write(lazySearchScript(" + json.dumps(source) + '));'],
        cwd=web, text=True)
    body = ('<meta charset="utf-8"><button class="search-button">検索</button><p id="result"></p><script>' + wrapped + '</script>').encode()
    with page_server(body) as origin, sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        try:
            page = browser.new_page()
            attempts = []
            errors = []
            page.on('pageerror', lambda error: errors.append(error))
            def respond(route):
                attempts.append(route.request.url)
                route.fulfill(status=503 if len(attempts) == 1 else 200, body='{}')
            page.route('**/index.json', respond)
            page.goto(origin)
            assert not attempts
            page.keyboard.press('Control+k')
            expect(page.get_by_role('status')).to_contain_text('もう一度')
            page.get_by_role('button', name='検索').click()
            expect(page.locator('#result')).to_have_text('Search ready')
            assert len(attempts) == 2 and not errors
        finally:
            browser.close()


@pytest.mark.parametrize('query,expected', [
    ('#ai-egent', '#ai-agent'), ('#AIエージェント', '#ai-agent'),
    ('#AI agent', '#ai-agent'), ('LLM', 'LLM'), ('AIエージェント', 'AIエージェント'),
    ('LLM decoder ', 'LLM decoder '), ('#C++', '#c-plus-plus'), ('#C# decoder', '#c-sharp decoder'),
])
def test_aliases_only_normalize_tag_filters(query, expected):
    script = ('const kanameTagAliases = ' + json.dumps(alias_map()) + ';\n' +
              (Path(__file__).resolve().parents[1] / 'search-aliases.js').read_text())
    body = ('<meta charset="utf-8"><input class="search-bar"><script>' + script + '</script>').encode()
    with page_server(body) as origin, sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(origin)
            page.locator('input').fill(query)
            expect(page.locator('input')).to_have_value(expected)
        finally:
            browser.close()
