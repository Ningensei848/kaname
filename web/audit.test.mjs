import test from 'node:test'
import assert from 'node:assert/strict'
import { checkReport } from './audit.mjs'
const url = 'https://github.com/advisories/GHSA-hp3w-g68c-fv3c'
const lock = { packages: {
  'node_modules/sprintf-js': { version: '1.0.3' },
  'node_modules/gray-matter/node_modules/argparse': { version: '1.0.10' },
  'node_modules/gray-matter/node_modules/js-yaml': { version: '3.15.2' },
} }
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
  assert.deepEqual(checkReport(report('braces', 'https://github.com/advisories/GHSA-vfj7-8cjw-p6xm'), lock), { braces: 1, sprintf: 0 })
  assert.deepEqual(checkReport({ vulnerabilities: {} }, lock), { braces: 0, sprintf: 0 })
})
test('fails closed when audit is unavailable', () => {
  for (const r of [null, {}, { error: 'unavailable', vulnerabilities: {} }]) {
    assert.throws(() => checkReport(r, lock), /dependency_audit_unavailable/)
  }
})
