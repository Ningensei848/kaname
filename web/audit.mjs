// No active advisory exceptions. Fail closed on new warnings or unavailable data.
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

export function checkReport(report) {
  const entries = report?.vulnerabilities
  const counts = report?.metadata?.vulnerabilities
  if (report?.auditReportVersion !== 2 || report.error || !entries ||
      typeof entries !== 'object' || Array.isArray(entries) || !counts ||
      ['info', 'low', 'moderate', 'high', 'critical', 'total'].some(key =>
        !Number.isInteger(counts[key]) || counts[key] < 0)) throw Error('dependency_audit_unavailable')
  if (Object.keys(entries).length || Object.values(counts).some(value => value !== 0)) {
    throw Error('unreviewed_dependency_advisory')
  }
  return { advisories: 0 }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const result = spawnSync('npm', ['audit', '--omit=dev', '--json'], { encoding: 'utf8' })
  let report
  try { report = JSON.parse(result.stdout) } catch { throw Error('dependency_audit_unavailable') }
  if (![0, 1].includes(result.status)) throw Error('dependency_audit_unavailable')
  const checked = checkReport(report)
  if (result.status !== 0) throw Error('dependency_audit_unavailable')
  console.log(`Dependency audit checked: ${JSON.stringify(checked)}. No advisory exceptions.`)
}
