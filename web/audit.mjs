// Accept only the documented, unpatched braces advisory on our fixed globs.
import { spawnSync } from 'node:child_process'
const result = spawnSync('npm', ['audit', '--omit=dev', '--json'], { encoding: 'utf8' })
let report
try { report = JSON.parse(result.stdout) } catch { throw Error('dependency_audit_unavailable') }
if (!report.vulnerabilities || result.status === null || report.error) throw Error('dependency_audit_unavailable')
let known = 0
for (const item of Object.values(report.vulnerabilities)) {
  for (const via of item.via) {
    if (typeof via === 'string') continue // Aggregate propagation, not another advisory.
    if (item.name === 'braces' && via.url === 'https://github.com/advisories/GHSA-vfj7-8cjw-p6xm') known++
    else throw Error('unreviewed_dependency_advisory')
  }
}
console.log(`Dependency audit checked; documented braces advisory: ${known}. See docs/web-preview.md.`)
