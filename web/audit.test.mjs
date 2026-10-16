import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { checkReport } from './audit.mjs'
const url = 'https://github.com/advisories/GHSA-hp3w-g68c-fv3c'
const lock = JSON.parse(readFileSync(new URL('./package-lock.json', import.meta.url)))
const report = (name, advisory, nodes = ['node_modules/sprintf-js']) => ({ vulnerabilities: {
  [name]: { name, nodes, via: [{ url: advisory }] },
} })
test('accepts the reviewed, pinned CLI-only sprintf advisory', () => {
  assert.deepEqual(checkReport(report('sprintf-js', url), lock), { braces: 0, sprintf: 1 })
})
test('rejects a new advisory, other package, changed version or new dependency path', () => {
  for (const r of [report('sprintf-js', 'https://github.com/advisories/new'), report('other', url),
    report('sprintf-js', url, ['node_modules/other/node_modules/sprintf-js'])]) {
    assert.throws(() => checkReport(r, lock), /unreviewed_dependency_advisory/)
  }
  assert.throws(() => checkReport(report('sprintf-js', url), { packages: {} }), /unreviewed_dependency_advisory/)
})
test('retains braces review and accepts clean reports', () => {
  assert.deepEqual(checkReport(report('braces', 'https://github.com/advisories/GHSA-vfj7-8cjw-p6xm', ['node_modules/braces']), lock), { braces: 1, sprintf: 0 })
  assert.deepEqual(checkReport({ vulnerabilities: {} }, lock), { braces: 0, sprintf: 0 })
})
test('rejects braces version, location, parent and propagation changes', () => {
  const braces = report('braces', 'https://github.com/advisories/GHSA-vfj7-8cjw-p6xm', ['node_modules/braces'])
  const changed = structuredClone(lock)
  changed.packages['node_modules/braces'].version = '3.0.4'
  assert.throws(() => checkReport(braces, changed), /unreviewed_dependency/)
  const parent = structuredClone(lock)
  parent.packages['node_modules/micromatch'].version = '5.0.0'
  assert.throws(() => checkReport(braces, parent), /unreviewed_dependency/)
  assert.throws(() => checkReport(report('braces', braces.vulnerabilities.braces.via[0].url,
    ['node_modules/other/node_modules/braces']), lock), /unreviewed_dependency/)
  const graph = structuredClone(braces)
  graph.vulnerabilities.micromatch = { name: 'micromatch', nodes: ['node_modules/micromatch'], via: ['new-package'] }
  assert.throws(() => checkReport(graph, lock), /unreviewed_dependency_path/)
  const unknown = structuredClone(braces)
  unknown.vulnerabilities.unreviewed = { name: 'unreviewed', nodes: ['node_modules/unreviewed'], via: ['braces'] }
  assert.throws(() => checkReport(unknown, lock), /unreviewed_dependency/)
})
test('fails closed when audit is unavailable', () => {
  for (const r of [null, {}, { error: 'unavailable', vulnerabilities: {} }]) {
    assert.throws(() => checkReport(r, lock), /dependency_audit_unavailable/)
  }
})
