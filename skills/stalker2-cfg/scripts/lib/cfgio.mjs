// Shared helpers for the cfg CLIs: argument parsing, file listing, loading a table
// (binary .cfg.bin of either container version, or text .cfg), record keys and flattening.
import fs from 'node:fs';
import path from 'node:path';
import { Struct, parseValue } from 's2cfgtojson';
import { keyName, literal, refsText } from './writeCfg.mjs';

export class UsageError extends Error {}

/** argv -> { _: [positionals], <flag>: true, <option>: value }. Unknown dashed words are errors. */
export function parseArgs(argv, { flags = [], options = [] } = {}) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '-h' || a === '--help') { out.help = true; continue; }
    if (a.startsWith('--')) {
      const name = a.slice(2);
      if (flags.includes(name)) { out[name] = true; continue; }
      if (options.includes(name)) {
        if (i + 1 >= argv.length) throw new UsageError(`${a} needs a value`);
        out[name] = argv[++i];
        continue;
      }
      throw new UsageError(`unknown option ${a}`);
    }
    out._.push(a);
  }
  return out;
}

/** Run a CLI main(): usage errors print the usage text and exit 2, other errors exit 1. */
export async function runCli(usage, main) {
  try {
    const code = await main();
    process.exitCode = code || 0;
  } catch (e) {
    if (e instanceof UsageError) {
      console.error(`error: ${e.message}\n\n${usage}`);
      process.exitCode = 2;
    } else {
      console.error(`error: ${e && e.stack ? e.stack : e}`);
      process.exitCode = 1;
    }
  }
}

export const slash = (p) => p.split(path.sep).join('/');

/** Every file under input (or input itself) whose name passes keep(); rel paths use '/'. */
export function listFiles(input, keep) {
  if (!fs.existsSync(input)) throw new UsageError(`not found: ${input}`);
  const st = fs.statSync(input);
  if (st.isFile()) return [{ abs: input, rel: path.basename(input) }];
  const out = [];
  const walk = (dir) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const abs = path.join(dir, e.name);
      if (e.isDirectory()) walk(abs);
      else if (keep(e.name)) out.push({ abs, rel: slash(path.relative(input, abs)) });
    }
  };
  walk(input);
  return out.sort((a, b) => (a.rel < b.rel ? -1 : a.rel > b.rel ? 1 : 0));
}

export const isBin = (name) => name.toLowerCase().endsWith('.cfg.bin');
export const isText = (name) => name.toLowerCase().endsWith('.cfg');
export const isTable = (name) => isBin(name) || isText(name);
/** Table id of a path: the path without .cfg.bin / .cfg, so a binary table and its text form pair up. */
export const tableId = (rel) => rel.replace(/\.cfg\.bin$/i, '').replace(/\.cfg$/i, '');

export function readText(abs) {
  return fs.readFileSync(abs, 'utf8').replace(/^﻿/, '').replace(/\r\n?/g, '\n');
}

/** Load a table: { kind: 'bin' | 'text', version, roots, pool, bytes }. */
export function loadTable(abs) {
  if (isBin(abs)) {
    const bytes = fs.readFileSync(abs);
    const version = bytes.length < 4 ? 0 : bytes.readUInt32LE(0);
    if (version !== 1 && version !== 2) {
      throw new Error(`${abs}: unknown container version ${version} (known: 1, 2). Try cfgbin_decode.mjs --tokens.`);
    }
    return { kind: 'bin', version, roots: Struct.fromBinary(bytes), bytes };
  }
  const text = readText(abs);
  return { kind: 'text', version: 'text', roots: Struct.fromString(text), bytes: null };
}

const POSITIONAL = /^\[\d+\]$/;
export const isPositional = (name) => POSITIONAL.test(name || '');

/** Stable record keys for the roots of one table: the struct name; a position-named root
 *  with a SID is keyed "[SID=X]" (positions shift between builds); repeats get "#2", "#3". */
export function recordKeys(roots) {
  const seen = new Map();
  return roots.map((r) => {
    const name = r.__internal__.rawName || '';
    let k = isPositional(name) && typeof r.SID === 'string' ? `[SID=${r.SID}]` : name;
    const n = (seen.get(k) || 0) + 1;
    seen.set(k, n);
    if (n > 1) k = `${k}#${n}`;
    return k;
  });
}

/** Display name of a root: "Name" or "[3] (SID X)". */
export function displayName(r) {
  const name = r.__internal__.rawName || '';
  return isPositional(name) && typeof r.SID === 'string' ? `${name} (SID ${r.SID})` : name;
}

/** Flatten a struct to Map(path -> literal). Refs show as "<path>{}" = "refkey=X;bpatch".
 *  Struct entries also get "<path>" = "{struct}" so added / removed sub-structs show.
 *  skipAppends: leave out [*] entries and their subtree (appends, not paths). */
export function flatten(node, { prefix = '', skipAppends = false, out = new Map() } = {}) {
  const refs = refsText(node.__internal__ || {});
  if (refs) out.set(`${prefix}{}`, refs);
  const seen = new Map();
  for (const [key, value] of Object.entries(node)) {
    if (key === '__internal__') continue;
    let kn = keyName(node, key, value);
    if (kn === '[*]' && skipAppends) continue;
    const n = (seen.get(kn) || 0) + 1;
    seen.set(kn, n);
    if (n > 1) kn = `${kn}#${n}`;
    const p = prefix ? `${prefix}.${kn}` : kn;
    if (value instanceof Struct) {
      out.set(p, value.__internal__ && value.__internal__.removenode ? 'removenode' : '{struct}');
      flatten(value, { prefix: p, skipAppends, out });
    } else {
      out.set(p, value === '' ? '' : literal(node, key, value));
    }
  }
  return out;
}

/** Two literals mean the same value (1.f == 1.0 == 1). */
export function sameValue(a, b) {
  if (a === b) return true;
  const x = parseValue(a);
  const y = parseValue(b);
  return typeof x === 'number' && typeof y === 'number' && x === y;
}
