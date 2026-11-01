import assert from 'node:assert/strict'
import fs from 'node:fs/promises'
import http from 'node:http'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test } from 'node:test'
import { prepareServeHandler } from './serve-handler-compat.mjs'

test('patched matcher preserves serve-handler routing, headers and missing files', async () => {
  const root = path.dirname(fileURLToPath(import.meta.url))
  const temp = await fs.mkdtemp(path.join(os.tmpdir(), 'kaname-serve-'))
  const engine = path.join(temp, 'engine')
  let server
  try {
    await fs.mkdir(path.join(engine, 'quartz/cli'), { recursive: true })
    await fs.copyFile(path.join(root, 'node_modules/@jackyzha0/quartz/quartz/cli/handlers.js'),
      path.join(engine, 'quartz/cli/handlers.js'))
    await prepareServeHandler(root, engine)
    const { default: handler } = await import(path.join(engine, 'serve-handler/src/index.js'))
    const content = path.join(temp, 'public')
    await fs.mkdir(path.join(content, 'notes'), { recursive: true })
    await fs.writeFile(path.join(content, 'notes/example.html'), 'verified note')
    server = http.createServer((req, res) => {
      handler(req, res, {
        public: content, cleanUrls: false, directoryListing: false,
        headers: [{ source: '**/*.html', headers: [{ key: 'X-Note', value: 'matched' }] }],
        rewrites: [{ source: '/read/:slug', destination: '/notes/:slug.html' }],
        redirects: [{ source: '/old/:slug', destination: '/read/:slug', type: 302 }],
      }).catch(error => { res.statusCode = 500; res.end(String(error)) })
    })
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
    const base = `http://127.0.0.1:${server.address().port}`
    for (const url of ['/notes/example.html', '/read/example']) {
      const response = await fetch(base + url)
      assert.equal(response.status, 200)
      assert.equal(await response.text(), 'verified note')
      assert.equal(response.headers.get('x-note'), 'matched')
    }
    const redirect = await fetch(base + '/old/example', { redirect: 'manual' })
    assert.equal(redirect.status, 302)
    assert.equal(redirect.headers.get('location'), '/read/example')
    for (const url of ['/missing.html', '/notes/']) {
      const response = await fetch(base + url)
      assert.equal(response.status, 404)
      await response.text()
    }
  } finally {
    if (server) await new Promise(resolve => server.close(resolve))
    await fs.rm(temp, { recursive: true, force: true })
  }
})
