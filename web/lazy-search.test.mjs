import { test } from 'node:test'
import assert from 'node:assert/strict'
import { Search } from '@quartz-community/search'
import { lazySearchScript } from './lazy-search.mjs'

test('defers only startup while retaining the pinned upstream search body', () => {
  const source = Search().afterDOMLoaded
  const wrapped = lazySearchScript(source)
  const body = source.replace(/document\.addEventListener\("nav",(\w+)\);document\.addEventListener\("render",\1\);\s*$/, 'return $1();')
  assert.ok(wrapped.includes(body))
  assert.ok(wrapped.includes("'aria-busy'"))
})

test('dependency changes cannot silently bypass deferred initialization', () => {
  assert.throws(() => lazySearchScript('document.addEventListener("nav",unknown);'), /upstream_search_startup_changed/)
})
