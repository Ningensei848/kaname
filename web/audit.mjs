// Accept only explicitly reviewed advisories; new advisories remain fatal.
import { spawnSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

// Fixed nodes AND the complete propagation graph reviewed for this build.
// A familiar advisory at a new location or through a new parent needs review.
const reviewed = {
  '@jackyzha0/quartz': ['node_modules/@jackyzha0/quartz', '5.0.0', ['globby', 'gray-matter']],
  globby: ['node_modules/globby', '16.2.4', ['fast-glob', 'micromatch']],
  'fast-glob': ['node_modules/fast-glob', '3.3.3', ['micromatch']],
  micromatch: ['node_modules/micromatch', '4.0.8', ['braces']],
  braces: ['node_modules/braces', '3.0.3', []],
  'gray-matter': ['node_modules/gray-matter', '4.0.3', ['js-yaml']],
  'js-yaml': ['node_modules/gray-matter/node_modules/js-yaml', '3.15.2', ['argparse']],
  argparse: ['node_modules/gray-matter/node_modules/argparse', '1.0.10', ['sprintf-js']],
  'sprintf-js': ['node_modules/sprintf-js', '1.0.3', []],
}

export function checkReport(report, lock) {
  if (!report?.vulnerabilities || Array.isArray(report.vulnerabilities) || report.error) throw Error('dependency_audit_unavailable')
  let braces = 0, sprintf = 0
  for (const item of Object.values(report.vulnerabilities)) {
    const rule = reviewed[item?.name]
    if (!rule || item.nodes?.length !== 1 || item.nodes[0] !== rule[0] ||
      !Array.isArray(item.via) || item.via.length === 0 ||
      Object.values(reviewed).some(([path, version]) => lock?.packages?.[path]?.version !== version)) {
      throw Error(`unreviewed_dependency_advisory: ${item?.name}`)
    }
    for (const via of item.via) {
      if (typeof via === 'string') {
        if (!rule[2].includes(via) || !report.vulnerabilities[via]) throw Error(`unreviewed_dependency_path: ${item.name}`)
        continue
      }
      if (item.name === 'braces' && via.url === 'https://github.com/advisories/GHSA-vfj7-8cjw-p6xm') braces++
      else if (item.name === 'sprintf-js' && via.url === 'https://github.com/advisories/GHSA-hp3w-g68c-fv3c') sprintf++
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
