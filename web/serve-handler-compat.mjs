import fs from 'node:fs/promises'
import path from 'node:path'

// serve-handler 6 uses minimatch's former CommonJS function export. Keep its
// routing on the patched matcher without changing installed dependency files.
export async function prepareServeHandler(root, engine) {
  const source = path.join(root, 'node_modules/serve-handler')
  const target = path.join(engine, 'serve-handler')
  const entry = await fs.readFile(path.join(source, 'src/index.js'), 'utf8')
  const oldImport = "const minimatch = require('minimatch');"
  const cli = path.join(engine, 'quartz/cli/handlers.js')
  const handlers = await fs.readFile(cli, 'utf8')
  const oldHandler = 'import serveHandler from "serve-handler"'
  if (entry.split(oldImport).length !== 2 || handlers.split(oldHandler).length !== 2) {
    throw Error('serve_handler_compatibility_mismatch')
  }
  await fs.mkdir(target)
  await fs.cp(path.join(source, 'src'), path.join(target, 'src'), { recursive: true })
  await fs.copyFile(path.join(source, 'package.json'), path.join(target, 'package.json'))
  await fs.symlink(path.join(root, 'node_modules'), path.join(target, 'node_modules'))
  await fs.writeFile(path.join(target, 'src/index.js'),
    entry.replace(oldImport, "const {minimatch} = require('minimatch');"))
  await fs.writeFile(cli,
    handlers.replace(oldHandler, 'import serveHandler from "../../serve-handler/src/index.js"'))
}
