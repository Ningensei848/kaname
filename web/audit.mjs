// Accept only explicitly reviewed advisories; new advisories remain fatal.
import { spawnSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

export function checkReport(report, lock) {
  if (!report?.vulnerabilities || report.error) throw Error('dependency_audit_unavailable')
  let braces = 0, sprintf = 0
  for (const item of Object.values(report.vulnerabilities)) {
    for (const via of item.via) {
      if (typeof via === 'string') continue // Aggregate propagation.
      if (item.name === 'braces' && via.url === 'https://github.com/advisories/GHSA-vfj7-8cjw-p6xm') braces++
      else if (item.name === 'sprintf-js' && via.url === 'https://github.com/advisories/GHSA-hp3w-g68c-fv3c' &&
        item.nodes.length === 1 && item.nodes[0] === 'node_modules/sprintf-js' &&
        lock.packages['node_modules/sprintf-js']?.version === '1.0.3' &&
        lock.packages['node_modules/gray-matter/node_modules/argparse']?.version === '1.0.10' &&
        lock.packages['node_modules/gray-matter/node_modules/js-yaml']?.version === '3.15.2') sprintf++
      else throw Error(`unreviewed_dependency_advisory: ${item.name} ${via.url}`)
    }
  }
  return { braces, sprintf }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const result = spawnSync('npm', ['audit', '--omit=dev', '--json'], { encoding: 'utf8' })
  let report
  try { report = JSON.parse(result.stdout) } catch { throw Error('dependency_audit_unavailable') }
  if (![0, 1].includes(result.status)) throw Error('dependency_audit_unavailable')
  const reviewed = checkReport(report, JSON.parse(readFileSync(new URL('./package-lock.json', import.meta.url))))
  console.log(`Dependency audit checked; documented advisories: ${JSON.stringify(reviewed)}. See docs/web-preview.md.`)
}
