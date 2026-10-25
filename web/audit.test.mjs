import test from 'node:test'
import assert from 'node:assert/strict'
import { checkReport } from './audit.mjs'

const clean = () => ({ auditReportVersion: 2, vulnerabilities: {}, metadata: {
  vulnerabilities: { info: 0, low: 0, moderate: 0, high: 0, critical: 0, total: 0 },
} })

test('accepts a complete clean npm report', () => {
  assert.deepEqual(checkReport(clean()), { advisories: 0 })
})

test('rejects new advisories and the two withdrawn former exceptions', () => {
  for (const [name, url] of [
    ['toml', 'https://github.com/advisories/GHSA-4qx8-w7c3-pj3p'],
    ['braces', 'https://github.com/advisories/GHSA-vfj7-8cjw-p6xm'],
    ['sprintf-js', 'https://github.com/advisories/GHSA-hp3w-g68c-fv3c'],
  ]) {
    const report = clean()
    report.vulnerabilities[name] = { name, via: [{ url }] }
    assert.throws(() => checkReport(report), /unreviewed_dependency_advisory/)
  }
  const inconsistent = clean()
  inconsistent.metadata.vulnerabilities.high = 1
  assert.throws(() => checkReport(inconsistent), /unreviewed_dependency_advisory/)
})

test('fails closed on unavailable or incomplete audit responses', () => {
  for (const value of [null, {}, { vulnerabilities: {} },
    { ...clean(), error: 'unavailable' }, { ...clean(), auditReportVersion: 1 },
    { ...clean(), vulnerabilities: [] }, { ...clean(), metadata: {} }]) {
    assert.throws(() => checkReport(value), /dependency_audit_unavailable/)
  }
  for (const value of [-1, '0', null, 0.5]) {
    const report = clean()
    report.metadata.vulnerabilities.total = value
    assert.throws(() => checkReport(report), /dependency_audit_unavailable/)
  }
})
