#!/usr/bin/env node
// Diff two folders (or two files) of STALKER 2 cfg tables: records and fields added, removed, changed.
import fs from 'node:fs';
import path from 'node:path';
import { parseArgs, runCli, listFiles, isTable, tableId, loadTable, recordKeys, displayName, flatten, sameValue, UsageError } from './lib/cfgio.mjs';
import { canonical } from './lib/writeCfg.mjs';

const USAGE = `Diff STALKER 2 cfg tables between two folders (e.g. two game builds' GameData extracts) or two files.
Binary .cfg.bin (container v1 or v2) and text .cfg both work; a table pairs with the same path on the
other side (Foo.cfg.bin pairs with Foo.cfg). Records are matched by struct name (a position-named
root like [0] by its SID), fields by path. Numbers compare by value (1.f equals 1.0).

usage:
  node cfg_diff.mjs <old folder | file> <new folder | file> [options]

options:
  --only TEXT     only tables whose path contains TEXT (case-insensitive)
  --max N         field lines shown per table (default 200, 0 = all)
  --records       list added / removed / changed records only, no field lines
  --quiet         print only tables that differ, and the summary
  -h, --help      this text

Exit code: 0 when every paired table has the same content, 1 when anything differs, 2 on bad usage.
Large tables (QuestNodePrototypes, ObjPrototypes) may need: node --max-old-space-size=8192 cfg_diff.mjs ...`;

const short = (s, n = 70) => (s.length > n ? s.slice(0, n - 3) + '...' : s);

function diffRecord(key, a, b, lines) {
  const fa = flatten(a), fb = flatten(b);
  for (const [p, va] of fa) {
    if (!fb.has(p)) lines.push(`  - ${key}.${p}${va === '{struct}' ? ' (struct)' : ` (was ${short(va)})`}`);
    else if (!sameValue(va, fb.get(p))) lines.push(`  ~ ${key}.${p}: ${short(va, 50)} -> ${short(fb.get(p), 50)}`);
  }
  for (const [p, vb] of fb) {
    if (!fa.has(p)) lines.push(`  + ${key}.${p}${vb === '{struct}' ? ' (struct)' : ` = ${short(vb)}`}`);
  }
}

function diffTable(A, B, opts) {
  const ka = recordKeys(A.roots), kb = recordKeys(B.roots);
  const ma = new Map(ka.map((k, i) => [k, A.roots[i]]));
  const mb = new Map(kb.map((k, i) => [k, B.roots[i]]));
  const added = [], removed = [], changed = [], lines = [];
  for (const [k, a] of ma) {
    const b = mb.get(k);
    if (!b) { removed.push(displayName(a)); continue; }
    if (JSON.stringify(canonical(a)) === JSON.stringify(canonical(b))) continue;
    const before = lines.length;
    diffRecord(k, a, b, lines);
    if (lines.length > before) changed.push(k);
  }
  for (const [k, b] of mb) if (!ma.has(k)) added.push(displayName(b));
  return { added, removed, changed, lines, count: [A.roots.length, B.roots.length] };
}

async function main() {
  const opts = parseArgs(process.argv.slice(2), { flags: ['records', 'quiet'], options: ['only', 'max'] });
  if (opts.help) { console.log(USAGE); return 0; }
  if (opts._.length !== 2) throw new UsageError('give an old and a new folder (or file)');
  const [oldIn, newIn] = opts._.map((p) => path.resolve(p));
  const max = opts.max !== undefined ? Number(opts.max) : 200;
  if (!Number.isInteger(max) || max < 0) throw new UsageError('--max needs a whole number');
  const bothFiles = fs.existsSync(oldIn) && fs.statSync(oldIn).isFile() && fs.existsSync(newIn) && fs.statSync(newIn).isFile();
  const index = (input) => new Map(listFiles(input, isTable).map((f) => [bothFiles ? 'table' : tableId(f.rel), f]));
  const O = index(oldIn), N = index(newIn);
  const only = opts.only ? opts.only.toLowerCase() : null;
  const ids = [...new Set([...O.keys(), ...N.keys()])].filter((id) => !only || id.toLowerCase().includes(only)).sort();
  if (!ids.length) throw new UsageError('no .cfg / .cfg.bin tables to compare');
  const tally = { same: 0, changed: 0, onlyOld: 0, onlyNew: 0, failed: 0 };
  for (const id of ids) {
    const o = O.get(id), n = N.get(id);
    const label = bothFiles ? `${path.basename(oldIn)} -> ${path.basename(newIn)}` : id;
    if (!o || !n) {
      tally[o ? 'onlyOld' : 'onlyNew']++;
      console.log(`== ${label}: only in ${o ? 'old' : 'new'}`);
      continue;
    }
    const bo = fs.readFileSync(o.abs), bn = fs.readFileSync(n.abs);
    if (bo.equals(bn)) {
      tally.same++;
      if (!opts.quiet) console.log(`== ${label}: identical (same bytes)`);
      continue;
    }
    let A, B;
    try {
      A = loadTable(o.abs);
      B = loadTable(n.abs);
    } catch (e) {
      tally.failed++;
      console.log(`== ${label}: FAIL ${e.message}`);
      continue;
    }
    const d = diffTable(A, B, opts);
    const fmt = (t) => (t.kind === 'bin' ? `v${t.version}` : 'text');
    const head = `== ${label} (${fmt(A)} -> ${fmt(B)}): ${d.count[0]} -> ${d.count[1]} records`;
    if (!d.added.length && !d.removed.length && !d.changed.length) {
      tally.same++;
      if (!opts.quiet) console.log(`${head}, same content (bytes differ)`);
      continue;
    }
    tally.changed++;
    console.log(`${head}, ${d.added.length} added, ${d.removed.length} removed, ${d.changed.length} changed, ${d.lines.length} field differences`);
    for (const r of d.added.slice(0, max || undefined)) console.log(`  + record ${r}`);
    for (const r of d.removed.slice(0, max || undefined)) console.log(`  - record ${r}`);
    if (opts.records) {
      for (const r of d.changed.slice(0, max || undefined)) console.log(`  ~ record ${r}`);
    } else {
      const shown = max ? d.lines.slice(0, max) : d.lines;
      for (const l of shown) console.log(l);
      if (shown.length < d.lines.length) console.log(`  ... ${d.lines.length - shown.length} more (--max 0 shows all)`);
    }
  }
  console.log(`\n${ids.length} table(s): ${tally.same} same, ${tally.changed} changed, ${tally.onlyOld} only in old, ${tally.onlyNew} only in new${tally.failed ? `, ${tally.failed} failed to load` : ''}`);
  return tally.changed || tally.onlyOld || tally.onlyNew || tally.failed ? 1 : 0;
}

runCli(USAGE, main);
