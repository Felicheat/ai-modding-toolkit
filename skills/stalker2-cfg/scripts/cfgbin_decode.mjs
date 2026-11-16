#!/usr/bin/env node
// Decode STALKER 2 .cfg.bin tables (container v1 and v2) to readable cfg text or JSON.
import fs from 'node:fs';
import path from 'node:path';
import { Struct } from 's2cfgtojson';
import { parseArgs, runCli, listFiles, isBin, loadTable, displayName, recordKeys, UsageError } from './lib/cfgio.mjs';
import { rootsToText, canonical } from './lib/writeCfg.mjs';

const USAGE = `Decode STALKER 2 .cfg.bin tables (container v1 = game 2.0.4 and older, v2 = 2.0.5 and newer).

usage:
  node cfgbin_decode.mjs <table.cfg.bin>                     print the table as cfg text
  node cfgbin_decode.mjs <table.cfg.bin> --record <names>    only the records named (struct name or SID, comma list)
  node cfgbin_decode.mjs <file | folder> --out <folder>      write <rel>.cfg (or .json) for every .cfg.bin
  node cfgbin_decode.mjs <file | folder> --check             decode, write as text, re-read with s2cfgtojson, compare
  node cfgbin_decode.mjs <file> --tokens [--near <text>] [--context N]
                                                             raw token dump, for a container this decoder does not know

options:
  --json       JSON (s2cfgtojson toJson) instead of cfg text
  --out DIR    output folder (mirrors the input tree); never the input folder
  -h, --help   this text

Large tables (QuestNodePrototypes, ObjPrototypes) may need: node --max-old-space-size=8192 cfgbin_decode.mjs ...
The output is GSC data: keep it out of anything you publish.`;

function render(table, opts, roots) {
  if (opts.json) return JSON.stringify(roots.map((r) => r.toJson()), (k, v) => (k === 'origin' ? undefined : v), 2) + '\n';
  const comment = null;
  return rootsToText(roots, comment);
}

function pickRecords(roots, list) {
  const want = new Set(list.split(',').map((s) => s.trim()).filter(Boolean));
  return roots.filter((r) => want.has(r.__internal__.rawName) || (typeof r.SID === 'string' && want.has(r.SID)));
}

/** Decode -> text -> s2cfgtojson text parser -> compare. Returns the names of records that differ. */
const COMMENT_NAMED = /^(#|;|\/\/)/;

/** A copy without entries whose names start with a comment character; counts what it drops. */
function withoutCommentNamed(node, drop) {
  const copy = node.clone();
  const strip = (n) => {
    for (const [k, v] of Object.entries(n)) {
      if (k === '__internal__') continue;
      const name = v instanceof Struct ? v.__internal__.rawName || k : k;
      if (COMMENT_NAMED.test(name)) { delete n[k]; drop.count++; continue; }
      if (v instanceof Struct) strip(v);
    }
  };
  strip(copy);
  return copy;
}

function roundTrip(all) {
  // GSC's compiler does not treat "#" as a comment: records and fields whose source lines start
  // with "#" reach the binary under names like "#Name". s2cfgtojson's text parser skips "#" lines,
  // so those cannot round trip; they are counted apart instead of failing the check.
  const skipped = all.filter((r) => COMMENT_NAMED.test(r.__internal__.rawName || '')).map(displayName);
  const drop = { count: 0 };
  const roots = all.filter((r) => !COMMENT_NAMED.test(r.__internal__.rawName || '')).map((r) => withoutCommentNamed(r, drop));
  const back = Struct.fromString(rootsToText(roots));
  const ka = recordKeys(roots);
  const kb = recordKeys(back);
  const byKey = new Map(kb.map((k, i) => [k, back[i]]));
  const bad = [];
  roots.forEach((a, i) => {
    const b = byKey.get(ka[i]);
    if (!b || JSON.stringify(canonical(a)) !== JSON.stringify(canonical(b))) bad.push(displayName(a));
  });
  const known = new Set(ka);
  return { bad, skipped, fields: drop.count, extra: kb.filter((k) => !known.has(k)).length };
}

function tokens(file, near, context) {
  const buf = fs.readFileSync(file);
  const toks = [];
  let pos = 0;
  while (pos + 4 <= buf.length) {
    const len = buf.readUInt32LE(pos);
    if (len >= 1 && len <= 8192 && pos + 4 + len <= buf.length && buf[pos + 4 + len - 1] === 0) {
      const s = buf.subarray(pos + 4, pos + 4 + len - 1);
      let printable = 0;
      for (const b of s) if ((b >= 0x20 && b < 0x7f) || b === 9 || b === 10 || b === 13 || b >= 0x80) printable++;
      if (s.length === 0 || printable / s.length > 0.85) {
        toks.push({ at: pos, str: s.toString('utf8') });
        pos += 4 + len;
        continue;
      }
    }
    toks.push({ at: pos, int: buf.readInt32LE(pos), f32: buf.readFloatLE(pos) });
    pos += 4;
  }
  const show = (i, mark) => {
    const t = toks[i];
    console.log(`${mark}${i} @${t.at} ${t.str !== undefined ? JSON.stringify(t.str) : `int ${t.int} (f32 ${t.f32})`}`);
  };
  console.log(`${file}: ${buf.length} bytes, first uint32 (container version) ${buf.length >= 4 ? buf.readUInt32LE(0) : '?'}, ${toks.length} tokens`);
  if (!near) { for (let i = 0; i < Math.min(toks.length, 400); i++) show(i, '   '); return 0; }
  const hits = toks.map((t, i) => (t.str !== undefined && t.str.includes(near) ? i : -1)).filter((i) => i >= 0);
  console.log(`${hits.length} token(s) contain ${JSON.stringify(near)}`);
  for (const h of hits.slice(0, 5)) {
    console.log(`--- token ${h}`);
    for (let i = Math.max(0, h - 4); i < Math.min(toks.length, h + context); i++) show(i, i === h ? '>> ' : '   ');
  }
  return 0;
}

async function main() {
  const opts = parseArgs(process.argv.slice(2), { flags: ['json', 'check', 'tokens'], options: ['out', 'record', 'near', 'context'] });
  if (opts.help) { console.log(USAGE); return 0; }
  if (opts._.length !== 1) throw new UsageError('give exactly one .cfg.bin file or folder');
  const input = path.resolve(opts._[0]);
  if (opts.tokens) {
    if (!fs.existsSync(input) || !fs.statSync(input).isFile()) throw new UsageError('--tokens needs one file');
    return tokens(input, opts.near, Number(opts.context || 24));
  }
  const files = listFiles(input, isBin);
  if (!files.length) throw new UsageError(`no .cfg.bin under ${input}`);
  const single = files.length === 1 && fs.statSync(input).isFile();
  if (!single && !opts.out && !opts.check) throw new UsageError('a folder needs --out <folder> (or --check)');
  let out = null;
  if (opts.out) {
    out = path.resolve(opts.out);
    if (out === input || (!single && out.startsWith(input + path.sep))) throw new UsageError('--out must be outside the input folder');
  }
  let failed = 0;
  for (const f of files) {
    let table;
    try {
      table = loadTable(f.abs);
    } catch (e) {
      failed++;
      console.error(`FAIL ${f.rel}: ${e.message}`);
      continue;
    }
    let roots = table.roots;
    if (opts.record) {
      roots = pickRecords(roots, opts.record);
      if (!roots.length) { console.error(`${f.rel}: no record named ${opts.record}`); failed++; continue; }
    }
    if (opts.check) {
      const r = roundTrip(roots);
      const status = r.bad.length
        ? `MISMATCH in ${r.bad.length} record(s): ${r.bad.slice(0, 5).join(', ')}${r.extra ? `; ${r.extra} unexpected record(s) after re-reading` : ''}`
        : 'round trip ok';
      console.log(`${f.rel}: container v${table.version}, ${table.roots.length} records, ${status}`);
      if (r.skipped.length) console.log(`   left out ${r.skipped.length} record(s) named with a leading comment character (text parsers drop them): ${r.skipped.slice(0, 5).join(', ')}`);
      if (r.fields) console.log(`   left out ${r.fields} field(s) or sub-struct(s) named with a leading "#" (text parsers drop them)`);
      if (r.bad.length) failed++;
      if (!out) continue;
    }
    const hashNamed = roots.filter((r) => COMMENT_NAMED.test(r.__internal__.rawName || '')).length;
    if (hashNamed && !opts.json && !opts.check) {
      console.error(`${f.rel}: ${hashNamed} record(s) named with a leading "#" are written as GSC has them; s2cfgtojson's text parser skips those lines and reads their sub-structs as records`);
    }
    const text = render(table, opts, roots);
    if (out) {
      const target = path.join(out, single ? path.basename(f.rel) : f.rel).replace(/\.cfg\.bin$/i, opts.json ? '.json' : '.cfg');
      fs.mkdirSync(path.dirname(target), { recursive: true });
      fs.writeFileSync(target, text);
      if (!opts.check) console.error(`${f.rel}: container v${table.version}, ${roots.length} records -> ${target}`);
    } else if (!opts.check) {
      process.stdout.write(text);
      console.error(`${f.rel}: container v${table.version}, ${roots.length} records`);
    }
  }
  return failed ? 1 : 0;
}

runCli(USAGE, main);
