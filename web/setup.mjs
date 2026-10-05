// Prepare only the owned build cache. All plugins come from npm's integrity lock.
import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.dirname(fileURLToPath(import.meta.url))
const readJSON = async p => JSON.parse(await fs.readFile(p, 'utf8'))
const pin = await readJSON(path.join(root, 'quartz.lock.json'))
const lock = await readJSON(path.join(root, 'package-lock.json'))
const pkg = await readJSON(path.join(root, 'package.json'))
const coreLock = lock.packages['node_modules/@jackyzha0/quartz']
if (!pkg.dependencies['@jackyzha0/quartz'].endsWith('/' + pin.engine.commit) ||
    coreLock.resolved !== pin.engine.resolved || coreLock.integrity !== pin.engine.integrity) throw Error('engine_pin_mismatch')
for (const [name, item] of Object.entries(pin.plugins)) {
  const installed = await readJSON(path.join(root, 'node_modules', item.package, 'package.json'))
  const locked = lock.packages['node_modules/' + item.package]
  if (installed.version !== item.version || pkg.dependencies[item.package] !== item.version ||
      ['version','resolved','integrity'].some(k => locked[k] !== item[k]) ||
      installed.quartz.dependencies.length !== 0) throw Error('plugin_pin_mismatch')
}
const cache = path.join(root, '.cache')
for (const p of [cache, path.join(cache, 'engine')]) {
  try { if ((await fs.lstat(p)).isSymbolicLink()) throw Error('cache_symlink') }
  catch (e) { if (e.code !== 'ENOENT') throw e }
}
await fs.mkdir(cache, { recursive: true })
// Stop globby's ancestor .gitignore lookup inside our private cache. This empty
// sentinel is not a checkout and no Git command runs against it.
await fs.mkdir(path.join(cache, '.git'), { recursive: true })
const guard = await fs.open(path.join(cache, '.build.lock'), 'wx')
try {
  const engine = path.join(cache, 'engine')
  try {
    if ((await fs.readFile(path.join(engine, '.kaname-cache'), 'utf8')) !== 'kaname-web-v1\n') throw Error('unowned_cache')
    await fs.rm(engine, { recursive: true })
  } catch (e) { if (e.code !== 'ENOENT') throw e; if (await fs.stat(engine).catch(() => null)) throw Error('unowned_cache') }
  await fs.mkdir(engine)
  await fs.writeFile(path.join(engine, '.kaname-cache'), 'kaname-web-v1\n')
  const core = path.join(root, 'node_modules/@jackyzha0/quartz')
  const nested = path.join(core, 'node_modules')
  await fs.symlink((await fs.stat(nested).catch(() => null)) ? nested : path.join(root, 'node_modules'), path.join(engine, 'node_modules'))
  await fs.cp(path.join(core, 'quartz'), path.join(engine, 'quartz'), { recursive: true })
  await fs.rm(path.join(engine, 'quartz/static/giscus'), { recursive: true, force: true })
  for (const name of ['package.json', 'quartz.ts']) await fs.copyFile(path.join(core, name), path.join(engine, name))
  await fs.copyFile(path.join(root, 'quartz.config.yaml'), path.join(engine, 'quartz.config.yaml'))
  await fs.mkdir(path.join(engine, 'plugins'))
  for (const [name, item] of Object.entries(pin.plugins)) {
    await fs.symlink(path.join(root, 'node_modules', item.package), path.join(engine, 'plugins', name))
  }
  await fs.mkdir(path.join(engine, '.quartz/plugins'), { recursive: true })
  await fs.writeFile(path.join(engine, '.quartz/plugins/index.ts'),
    'export const CustomOgImagesEmitterName = "__disabled__"\nexport type { ContentDetails } from "@quartz-community/content-index"\n')
  const font = path.join(root, 'node_modules/@fontsource/noto-sans-jp')
  const staticFonts = path.join(engine, 'quartz/static/fonts')
  await fs.mkdir(staticFonts, { recursive: true })
  let css = ''
  for (const weight of [400, 600]) {
    const source = await fs.readFile(path.join(font, `${weight}.css`), 'utf8')
    css += source.replace(/, url\([^)]*\.woff\) format\('woff'\)/g, '')
      .replaceAll('url(./files/', 'url(./static/fonts/')
    for (const match of source.matchAll(/url\(\.\/files\/([^)]*\.woff2)\)/g)) {
      await fs.copyFile(path.join(font, 'files', match[1]), path.join(staticFonts, match[1]))
    }
  }
  await fs.copyFile(path.join(font, 'LICENSE'), path.join(engine, 'quartz/static/fonts/LICENSE.txt'))
  const notices = path.join(engine, 'quartz/static/licenses')
  await fs.mkdir(notices, { recursive: true })
  for (const name of ['@jackyzha0/quartz', ...Object.values(pin.plugins).map(p => p.package),
                     '@quartz-community/types', '@quartz-community/utils', 'preact', 'flexsearch']) {
    const directory = path.join(root, 'node_modules', name)
    const license = (await fs.readdir(directory)).find(file => /^licen[cs]e(?:\.(?:md|txt))?$/i.test(file))
    if (!license) throw Error('missing_frontend_license')
    await fs.copyFile(path.join(directory, license), path.join(notices, name.replaceAll(/[^a-z0-9-]/g, '_') + '.txt'))
  }
  await fs.writeFile(path.join(engine, 'quartz/styles/custom.scss'),
    '@use "./base.scss";\n' + css + '\n' + await fs.readFile(path.join(root, 'theme.scss'), 'utf8'))
  console.log('Web engine prepared from fixed local dependencies.')
} finally { await guard.close(); await fs.unlink(path.join(cache, '.build.lock')) }
