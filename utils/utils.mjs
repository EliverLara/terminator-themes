import fs from 'fs'
import path from 'path'
import { promisify } from 'util'

export const __dirname = path.dirname(new URL(import.meta.url).pathname)
export const writeFile = promisify(fs.writeFile)
export const readFile = promisify(fs.readFile)
export const readdir = promisify(fs.readdir)
export const unlink = promisify(fs.unlink)
