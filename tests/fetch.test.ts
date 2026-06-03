import { test } from 'node:test';
import * as assert from 'node:assert';
import * as http from 'http';
import { fetchWithRetry, cleanHtml, parseRssFeed, crawlSource } from '../src/crawler/fetch';
import { SsotSource } from '../src/types';

test('Fetch Client and Parser Tests', async (t) => {
  // Spin up a local mock server
  let requestCount = 0;
  const server = http.createServer((req, res) => {
    requestCount++;
    if (req.url === '/304') {
      res.writeHead(304, { 'Last-Modified': 'Wed, 21 Oct 2015 07:28:00 GMT' });
      res.end();
    } else if (req.url === '/500') {
      res.writeHead(500);
      res.end('Server Error');
    } else if (req.url === '/html') {
      res.writeHead(200, {
        'Content-Type': 'text/html',
        'Last-Modified': 'Wed, 21 Oct 2015 07:28:00 GMT',
      });
      res.end(
        '<html><head><title>Test</title><style>body { color: red; }</style><script>console.log(1)</script></head><body><header>Nav</header><main>Hello World &amp; welcome</main><footer>Footer</footer></body></html>'
      );
    } else if (req.url === '/rss') {
      res.writeHead(200, { 'Content-Type': 'application/rss+xml' });
      res.end(`
        <rss version="2.0">
          <channel>
            <item>
              <title><![CDATA[Test Title]]></title>
              <description><![CDATA[Test Description]]></description>
              <pubDate>Wed, 21 Oct 2015 07:28:00 GMT</pubDate>
              <link>https://example.com/item</link>
            </item>
          </channel>
        </rss>
      `);
    } else {
      res.writeHead(200);
      res.end('OK');
    }
  });

  await new Promise<void>((resolve) => {
    server.listen(0, '127.0.0.1', () => {
      resolve();
    });
  });

  const address = server.address() as any;
  const baseUrl = `http://127.0.0.1:${address.port}`;

  await t.test('should successfully fetch content and header', async () => {
    const result = await fetchWithRetry(`${baseUrl}/html`);
    assert.ok(result.content.includes('Hello World'));
    assert.strictEqual(result.lastModifiedHeader, 'Wed, 21 Oct 2015 07:28:00 GMT');
  });

  await t.test('should return empty content on 304 Not Modified', async () => {
    const result = await fetchWithRetry(`${baseUrl}/304`, 3, 10, 'Wed, 21 Oct 2015 07:28:00 GMT');
    assert.strictEqual(result.content, '');
    assert.strictEqual(result.lastModifiedHeader, 'Wed, 21 Oct 2015 07:28:00 GMT');
  });

  await t.test('should retry 3 times and fail on 500 error', async () => {
    requestCount = 0;
    await assert.rejects(async () => {
      await fetchWithRetry(`${baseUrl}/500`, 3, 10);
    }, /Failed to fetch/);
    // Verified 3 attempts
    assert.strictEqual(requestCount, 3);
  });

  await t.test('should clean HTML tags and boilerplates correctly', () => {
    const dirty = `
      <!-- This is a comment -->
      <header>Logo & Nav</header>
      <nav>Sidebar</nav>
      <style>body { color: blue; }</style>
      <script>alert(1);</script>
      <aside>Advertisements</aside>
      <div>
        <p>Main content text &amp; some symbols &lt; &gt; &quot;</p>
      </div>
      <footer>Copyright</footer>
    `;
    const clean = cleanHtml(dirty);
    assert.strictEqual(clean, 'Main content text & some symbols < > "');
  });

  await t.test('should parse RSS XML content correctly', () => {
    const xml = `
      <rss version="2.0">
        <channel>
          <item>
            <title><![CDATA[Test Title]]></title>
            <description><![CDATA[Test Description &amp; Summary]]></description>
            <pubDate>Wed, 21 Oct 2015 07:28:00 GMT</pubDate>
            <link>https://example.com/item</link>
          </item>
        </channel>
      </rss>
    `;
    const parsed = parseRssFeed(xml);
    assert.ok(parsed.includes('Title: Test Title'));
    assert.ok(parsed.includes('Date: Wed, 21 Oct 2015 07:28:00 GMT'));
    assert.ok(parsed.includes('Link: https://example.com/item'));
    assert.ok(parsed.includes('Description: Test Description &amp; Summary'));
  });

  await t.test('should crawl source correctly (HTML page)', async () => {
    const source: SsotSource = {
      id: 'test_html',
      name: 'Test Html',
      url: `${baseUrl}/html`,
      description: 'Test source',
    };
    const crawled = await crawlSource(source);
    assert.strictEqual(crawled.content, 'Hello World & welcome');
    assert.strictEqual(crawled.isNotModified, false);
  });

  await t.test('should crawl source correctly (RSS Feed)', async () => {
    const source: SsotSource = {
      id: 'test_rss',
      name: 'Test Rss',
      url: `${baseUrl}/html`,
      feed_url: `${baseUrl}/rss`,
      description: 'Test feed source',
    };
    const crawled = await crawlSource(source);
    assert.ok(crawled.content.includes('Title: Test Title'));
    assert.strictEqual(crawled.isNotModified, false);
  });

  // Close server
  await new Promise<void>((resolve) => {
    server.close(() => {
      resolve();
    });
  });
});
