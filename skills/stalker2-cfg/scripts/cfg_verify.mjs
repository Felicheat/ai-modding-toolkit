#!/usr/bin/env node
// Check STALKER 2 text cfg files: syntax lint, s2cfgtojson round trip and, with --vanilla,
// the patch rules that are proven in game (root keys, position-named roots, created records,
// whole-file replacements, two files setting one field). It also checks refurl / refkey against
// the kind of mod the file ships in (a plain ~mods pak or a Zone Kit mod), told from its path.
import fs from 'node:fs';
import path from 'node:path';
import { Struct } from 's2cfgtojson';
import { parseArgs, runCli, listFiles, isText, tableId, loadTable, readText, recordKeys, isPositional, flatten, slash, UsageError } from './lib/cfgio.mjs';
import { rootsToText, canonical, keyName } from './lib/writeCfg.mjs';

const USAGE = `Check STALKER 2 text cfg files (a mod's patch files, a whole-file replacement, a generator's output).

usage:
  node cfg_verify.mjs <file.cfg | folder>... [--vanilla <folder>] [--dlc-vanilla <folder>]
                      [--target pak|zonekit] [--quiet]

Always:
  line lint     unclosed or extra struct.end, lines s2cfgtojson would silently skip, unknown {flags},
                malformed numbers (0.5.f), trailing // comments, "#" lines, duplicate keys, [*] mixed with [N]
  round trip    parse with s2cfgtojson, compare with the line scan, write back as text, parse again, compare
  refurl rules  by the kind of mod (a path holding ModGameData/ = a Zone Kit mod, GameData/ or DLCGameData/
                without it = a plain ~mods pak, or --target): a relative refurl in a Zone Kit mod, an
                @Name/ refurl (@BaseGame/...) in a pak mod, an @BaseGame refurl to the file being patched
With --vanilla (and --dlc-vanilla for files under DLCGameData/<DLC>/):
  patch rules   root keyed by SID instead of struct name, {bpatch} on a position-named root ([0]),
                created records written with refkey / {bpatch}, fields that are not in the vanilla record,
                vanilla records without {bpatch}, whole-file replacements that drop vanilla records,
                one field set by two files, a refkey without refurl whose parent is not in the file.
  A file at GameData/<Table>.cfg is a whole-file replacement; a file in GameData/<Table>/ (or named
  <Table>.cfg_patch_<Name> beside a table) is a patch of <Table>.

options:
  --vanilla DIR      the game's GameData extract (.cfg.bin tables, either container version, and the text
                     tables). A text tree such as the Zone Kit's also works: its <Table>/ sub-files are
                     merged into <Table>. Files outside a GameData/ or ModGameData/<Mod>/ folder count from the
                     folder you pass.
  --dlc-vanilla DIR  the same for one DLC (e.g. the DLCGameData/DLC1 extract of the Cost of Hope pak)
  --target KIND      pak or zonekit: the kind of mod every file given ships in, instead of telling it from
                     the path. Needed for a Zone Kit mod's patch files that sit under a plain GameData/ path.
  --quiet            print errors only (warnings are still counted)
  -h, --help         this text

Exit code: 1 when any ERROR was found, 0 otherwise (warnings do not fail), 2 on bad usage.`;

const KEYWORDS = new Set(['refurl', 'refkey', 'bskipref', 'bpatch']);
const HEADER = /^(.*?)\s*:\s*struct\.begin\s*(\{([^}]*)\})?\s*(.*)$/;
const BARE_HEADER = /^struct\.begin\s*(\{([^}]*)\})?\s*(.*)$/;
const REMOVE = /^(.+?)\s*:\s*removenode$/;
const KV = /^([^=]+?)\s*=\s*(.*)$/;
const NUMLIKE = /^-?[\d.]+f*$/;
const NUMBER = /^-?(\d+\.?\d*|\.\d+)f?$/;

/** Independent line scanner: problems plus counts to hold s2cfgtojson's reading against. */
function scan(text) {
  const problems = [];
  const add = (level, line, msg) => problems.push({ level, line, msg });
  const stack = [];
  const roots = [];
  const refs = [];
  let structs = 0, values = 0;
  const lines = text.split('\n');
  const enter = (name, line) => {
    const parent = stack[stack.length - 1];
    if (parent) note(parent, name, line);
    else roots.push({ name, line });
  };
  const note = (frame, name, line) => {
    if (name === '[*]') frame.star = true;
    else {
      if (/^\[\d+\]$/.test(name)) frame.index = true;
      if (frame.names.has(name)) add('WARN', line, `duplicate key "${name}" in ${frame.name || 'struct'} (first at line ${frame.names.get(name)})`);
      else frame.names.set(name, line);
    }
    if (frame.star && frame.index && !frame.mixWarned) {
      frame.mixWarned = true;
      add('WARN', line, `${frame.name || 'struct'} mixes [*] with [N] entries: s2cfgtojson's toString() renders every slot of it as [*], and in its tree a value slot "[N] = x" cannot be told from an append`);
    }
  };
  lines.forEach((raw, i) => {
    const ln = i + 1;
    let s = raw.trim();
    if (!s) return;
    if (s.startsWith('#')) { add('WARN', ln, 'line starts with "#": s2cfgtojson skips it as a comment, GSC\'s compiler keeps it as a name; use // for comments'); return; }
    if (s.startsWith('//') || s.startsWith(';')) return;
    const c = s.indexOf('//');
    if (c > 0) {
      if (!s.includes('struct.')) add('WARN', ln, 'trailing // comment after a value: s2cfgtojson keeps it as part of the value; put comments on their own line');
      s = s.slice(0, c).trim();
    }
    if (s.includes('struct.begin')) {
      const m = s.match(HEADER) || s.match(BARE_HEADER);
      if (!m) { add('ERROR', ln, 'cannot read this struct.begin line'); return; }
      const bare = !s.match(HEADER);
      const name = bare ? '' : m[1].trim();
      const flagText = bare ? m[2] : m[3];
      const rest = bare ? m[3] : m[4];
      if (rest) add('ERROR', ln, `text after struct.begin: "${rest}"`);
      if (/struct\.(begin|end)/.test(name)) add('ERROR', ln, 'two statements on one line (a name contains "struct.")');
      if (!name) add('WARN', ln, 'struct.begin without a name');
      if (flagText !== undefined) {
        const parts = flagText.split(';').map((x) => x.trim()).filter(Boolean);
        if (parts.length > 1 && !parts[0].includes('=')) {
          add('WARN', ln, `{${flagText.trim()}}: s2cfgtojson reads NO flags from a list that starts with a bare flag, so every tool built on it sees this struct without them; how the game reads it is not proven. GSC's files never combine a bare flag with others; s2cfgtojson reads {refkey=X;bpatch}`);
        }
        const ref = { line: ln, name, refurl: '', refkey: '' };
        for (const part of parts) {
          const k = part.split('=')[0].trim();
          if (!KEYWORDS.has(k)) add('ERROR', ln, `unknown flag "${k}" (known: refurl, refkey, bskipref, bpatch)`);
          else if ((k === 'refurl' || k === 'refkey') && !part.includes('=')) add('ERROR', ln, `${k} needs a value (${k}=...)`);
          else if (k === 'refurl' || k === 'refkey') ref[k] = part.slice(part.indexOf('=') + 1).trim();
        }
        if (ref.refurl || ref.refkey) refs.push(ref);
      }
      enter(name, ln);
      structs++;
      stack.push({ name, line: ln, names: new Map(), star: false, index: false });
      return;
    }
    if (s.includes('struct.end')) {
      if (s !== 'struct.end') add('ERROR', ln, `text around struct.end: "${s}" (s2cfgtojson reads any line holding "struct.end" as one)`);
      if (!stack.length) add('ERROR', ln, 'struct.end with no open struct');
      else stack.pop();
      return;
    }
    const rm = s.match(REMOVE);
    if (rm) {
      enter(rm[1].trim(), ln);
      structs++;
      return;
    }
    const kv = s.match(KV);
    if (kv) {
      const key = kv[1].trim(), value = kv[2].trim();
      if (!stack.length) { add('ERROR', ln, `value outside any struct: "${key}" (ignored by parsers)`); return; }
      if (NUMLIKE.test(value) && !NUMBER.test(value)) add('ERROR', ln, `malformed number "${value}" (forms GSC uses: 1, 1.5, 1.f, 1.5f)`);
      note(stack[stack.length - 1], key, ln);
      values++;
      return;
    }
    add('ERROR', ln, `not a cfg line (parsers skip it silently): "${s.slice(0, 60)}"`);
  });
  for (const f of stack) add('ERROR', f.line, `struct "${f.name}" opened here is never closed`);
  return { problems, roots, refs, structs, values };
}

function countTree(roots) {
  let structs = 0, values = 0;
  const visit = (n) => {
    for (const [k, v] of Object.entries(n)) {
      if (k === '__internal__') continue;
      if (v instanceof Struct) { structs++; visit(v); } else values++;
    }
  };
  for (const r of roots) { structs++; visit(r); }
  return { structs, values };
}

/** { rel: path below GameData/, ModGameData/<Mod>/ or DLCGameData/<DLC>/, dlc: true for the last }, or null. */
function gameDataRel(abs) {
  const segs = slash(abs).split('/');
  for (let i = segs.length - 2; i >= 0; i--) {
    if (segs[i] === 'GameData') return { rel: segs.slice(i + 1).join('/'), dlc: false };
    if (i > 0 && segs[i - 1] === 'ModGameData') return { rel: segs.slice(i + 1).join('/'), dlc: false };
    if (i > 0 && segs[i - 1] === 'DLCGameData') return { rel: segs.slice(i + 1).join('/'), dlc: true };
  }
  return null;
}

/** The kind of mod a file ships in, from its path: 'zonekit' (a ModGameData/ folder), 'pak'
 *  (GameData/ or DLCGameData/ without it) or null (cannot tell: give --target). */
function modTarget(abs) {
  const segs = slash(abs).split('/').slice(0, -1);
  if (segs.includes('ModGameData')) return 'zonekit';
  if (segs.includes('GameData') || segs.includes('DLCGameData')) return 'pak';
  return null;
}

const vanillaCache = new Map();
function vanillaTable(dir, id) {
  if (!id) return null;
  const ck = `${dir}|${id}`;
  if (vanillaCache.has(ck)) return vanillaCache.get(ck);
  let t = null;
  const bin = path.join(dir, `${id}.cfg.bin`), txt = path.join(dir, `${id}.cfg`);
  if (fs.existsSync(bin)) t = loadTable(bin);
  else if (fs.existsSync(txt)) {
    t = loadTable(txt);
    const sub = path.join(dir, id);
    if (fs.existsSync(sub) && fs.statSync(sub).isDirectory()) {
      for (const f of listFiles(sub, isText)) t.roots.push(...Struct.fromString(readText(f.abs)));
    }
  }
  if (t) {
    t.byName = new Map();
    t.bySid = new Map();
    for (const r of t.roots) {
      const n = r.__internal__.rawName;
      if (!t.byName.has(n)) t.byName.set(n, r);
      if (typeof r.SID === 'string' && !t.bySid.has(r.SID)) t.bySid.set(r.SID, n);
    }
    t.paths = new Map();
  }
  vanillaCache.set(ck, t);
  return t;
}

/** Every path a vanilla record has, its own plus what its refkey chain (same table) gives it. */
function vanillaPaths(t, name, depth = 0) {
  if (t.paths.has(name)) return t.paths.get(name);
  const r = t.byName.get(name);
  const set = new Set();
  if (r) {
    for (const p of flatten(r).keys()) if (!p.endsWith('{}')) set.add(p);
    const parent = r.__internal__.refkey;
    if (parent && parent !== name && depth < 16 && t.byName.has(parent)) for (const p of vanillaPaths(t, parent, depth + 1)) set.add(p);
  }
  t.paths.set(name, set);
  return set;
}

function hasNestedBpatch(node) {
  for (const [k, v] of Object.entries(node)) {
    if (k !== '__internal__' && v instanceof Struct && (v.__internal__.bpatch || hasNestedBpatch(v))) return true;
  }
  return false;
}

/** Sub-structs that exist in the vanilla record but carry no {bpatch} in the patch. */
function nestedWithoutBpatch(node, vpaths, prefix = '', out = []) {
  for (const [key, v] of Object.entries(node)) {
    if (key === '__internal__' || !(v instanceof Struct)) continue;
    const kn = keyName(node, key, v);
    if (kn === '[*]') continue;
    const p = prefix ? `${prefix}.${kn}` : kn;
    if (!vpaths.has(p)) continue;
    if (!v.__internal__.bpatch && !v.__internal__.removenode) out.push(p);
    else nestedWithoutBpatch(v, vpaths, p, out);
  }
  return out;
}

const PATCH_NAME = /\.cfg_patch_[^/]*$/i;
const isCfgFile = (name) => isText(name) || PATCH_NAME.test(name);

/** The file(s) a mod file at rel patches, lower case: <Table>/<any>.cfg and <Table>.cfg_patch_<Name>
 *  patch <Table>.cfg; a file at the top is its own table. */
function patchedFiles(rel) {
  const out = [];
  if (PATCH_NAME.test(rel)) out.push(`${rel.replace(PATCH_NAME, '')}.cfg`);
  const dir = path.posix.dirname(rel);
  out.push(dir === '.' ? rel : `${dir}.cfg`);
  return out.map((p) => p.toLowerCase());
}

/** refurl against the kind of mod. Returns false when the kind is unknown and a refurl needed it. */
function refurlChecks(file, where, target, refs, report) {
  let known = true;
  const patched = where.dlc ? [] : patchedFiles(where.rel);
  for (const r of refs) {
    if (!r.refurl) continue;
    const mount = r.refurl.startsWith('@') ? r.refurl.slice(1).split('/')[0] : null;
    if (!target) known = false;
    if (target === 'zonekit' && mount === null) {
      report('WARN', file, r.line, `refurl=${r.refurl} is relative in a Zone Kit mod: relative refurls are reported to break on console since game 2.0 even when PC works; use refurl=@BaseGame/<path below GameData> (@<ModName>/<path> for a file of the mod's own tree)`);
    }
    if (target === 'pak' && mount !== null) {
      report('WARN', file, r.line, `refurl=${r.refurl} in a plain ~mods pak: no config path is active there (log: "No config paths are active"), so it should fail with "references config path '${mount}' which is not active" (from s2cfgtojson's notes, not tested in game); use a relative refurl`);
    }
    if (mount === 'BaseGame' && patched.includes(r.refurl.slice('@BaseGame/'.length).toLowerCase())) {
      report('WARN', file, r.line, `refurl=${r.refurl} points at the file this one patches: reported to loop in the Zone Kit until EXCEPTION_STACK_OVERFLOW (some files, EffectPrototypes among them, are reported fine; the cause is unknown); use {bpatch} or write the struct out in full`);
    }
  }
  return known;
}

function patchChecks(file, rel, roots, rootLines, vdir, tag, report, setters) {
  // <Table>.cfg_patch_<Name> beside a table patches that table; <Table>/<any>.cfg patches <Table>.
  let named = PATCH_NAME.test(rel) ? rel.replace(PATCH_NAME, '') : null;
  // <Table>/<Table>.cfg_patch_<Name>.cfg: no table of that name beside it, so the folder rule applies.
  if (named && isText(rel) && !vanillaTable(vdir, named)) named = null;
  const id = named || tableId(rel);
  const whole = named ? null : vanillaTable(vdir, id);
  const dir = named || path.posix.dirname(rel);
  const table = whole ? null : vanillaTable(vdir, dir === '.' ? '' : dir);
  const lineOf = (i) => (rootLines[i] !== undefined ? rootLines[i] : 0);
  if (whole) {
    const have = new Set(recordKeys(roots));
    const missing = recordKeys(whole.roots).filter((k) => !have.has(k));
    if (missing.length) report('WARN', file, 0, `whole-file replacement of ${id} leaves out ${missing.length} vanilla record(s) (they are gone in game): ${missing.slice(0, 8).join(', ')}${missing.length > 8 ? ', ...' : ''}`);
    roots.forEach((r, i) => { if (r.__internal__.bpatch || hasNestedBpatch(r)) report('WARN', file, lineOf(i), `{bpatch} inside a whole-file replacement (${r.__internal__.rawName}): restate the record in full instead`); });
    return { tid: `${tag}${id}`, table: whole };
  }
  const tid = `${tag}${dir}`;
  if (!table) {
    report('WARN', file, 0, `no vanilla table ${dir === '.' ? id : dir}.cfg.bin (or .cfg) under --vanilla: a patch must sit in a folder named after its table`);
    return { tid, table: null };
  }
  roots.forEach((r, i) => {
    const n = r.__internal__.rawName;
    const ln = lineOf(i);
    const bp = !!r.__internal__.bpatch;
    if (r.__internal__.removenode) {
      if (!table.byName.has(n)) report('WARN', file, ln, `removenode on ${n}, which is not a vanilla record of ${tid}`);
      return;
    }
    if (isPositional(n)) {
      report(bp ? 'ERROR' : 'WARN', file, ln, `root ${n} is named by position: a patch aimed at it makes a stray record instead (proven in game); replace the whole table (GameData/${tid}.cfg) instead`);
      return;
    }
    if (table.byName.has(n)) {
      if (!bp) {
        report('WARN', file, ln, `${n} has no {bpatch}: per s2cfgtojson's notes on the loader the vanilla record is then replaced whole (fields not restated are lost); add {bpatch} to merge`);
        return;
      }
      const vp = vanillaPaths(table, n);
      const missing = [];
      for (const p of flatten(r, { skipAppends: true }).keys()) {
        if (p.endsWith('{}') || vp.has(p)) continue;
        if (missing.some((m) => p.startsWith(m + '.'))) continue;
        missing.push(p);
      }
      for (const p of missing.slice(0, 10)) report('WARN', file, ln, `${n}.${p} is not in the vanilla record (checked through its refkey chain): a typo, or a field this record does not have`);
      if (missing.length > 10) report('WARN', file, ln, `${n}: ${missing.length - 10} more paths not in the vanilla record`);
      for (const p of nestedWithoutBpatch(r, vp)) report('WARN', file, ln, `${n}.${p} has no {bpatch}: whether the game merges or replaces that sub-struct is not proven; mark every edited sub-struct {bpatch} (as s2cfgtojson's fork() does)`);
      for (const [p, v] of flatten(r, { skipAppends: true })) {
        if (p.endsWith('{}') || v === '{struct}') continue;
        const key = `${tid}|${n}.${p}`;
        if (!setters.has(key)) setters.set(key, new Set());
        setters.get(key).add(file);
      }
      return;
    }
    if (table.bySid.has(n)) {
      report('ERROR', file, ln, `${n} is a SID, not a struct name: patch roots are keyed by the struct NAME (here ${table.bySid.get(n)}); keyed by SID the patch adds a stray record`);
      return;
    }
    const key = `${tid}|${n}|created`;
    if (!setters.has(key)) setters.set(key, new Set());
    setters.get(key).add(file);
    const parent = r.__internal__.refkey;
    let left = '';
    if (parent && table.byName.has(parent)) {
      const own = new Set(flatten(r, { skipAppends: true }).keys());
      const gone = [];
      for (const p of vanillaPaths(table, parent)) {
        if (own.has(p) || gone.some((g) => p.startsWith(g + '.'))) continue;
        gone.push(p);
      }
      left = gone.length ? `; it leaves out ${gone.length} path(s) of ${parent}: ${gone.slice(0, 6).join(', ')}${gone.length > 6 ? ', ...' : ''}` : `; it restates every path of ${parent}`;
    }
    if (bp || hasNestedBpatch(r)) {
      report('WARN', file, ln, `${n} is not a vanilla record of ${tid}, so this creates it; a created record built from refkey + {bpatch} did not inherit the vanilla record in game: write it out in full, with no refkey and no {bpatch} inside${left}`);
    } else if (parent) {
      report('NOTE', file, ln, `${n} is created with refkey=${parent}: writing a created record out in full is the proven route${left}`);
    }
  });
  return { tid, table };
}

async function main() {
  const opts = parseArgs(process.argv.slice(2), { flags: ['quiet'], options: ['vanilla', 'dlc-vanilla', 'target'] });
  if (opts.help) { console.log(USAGE); return 0; }
  if (!opts._.length) throw new UsageError('give at least one .cfg file or folder');
  const vdir = opts.vanilla ? path.resolve(opts.vanilla) : null;
  const ddir = opts['dlc-vanilla'] ? path.resolve(opts['dlc-vanilla']) : null;
  for (const [flag, d] of [['--vanilla', vdir], ['--dlc-vanilla', ddir]]) {
    if (d && !(fs.existsSync(d) && fs.statSync(d).isDirectory())) throw new UsageError(`${flag} is not a folder: ${d}`);
  }
  if (opts.target !== undefined && opts.target !== 'pak' && opts.target !== 'zonekit') throw new UsageError(`--target is pak or zonekit, not "${opts.target}"`);
  let dlcSkipped = 0, targetUnknown = 0;
  const orphans = [];
  const tally = { files: 0, ERROR: 0, WARN: 0, NOTE: 0 };
  const report = (level, file, line, msg) => {
    tally[level]++;
    if (opts.quiet && level !== 'ERROR') return;
    console.log(`${level.padEnd(5)} ${file}${line ? `:${line}` : ''}: ${msg}`);
  };
  const setters = new Map();
  for (const input of opts._) {
    const abs = path.resolve(input);
    for (const f of listFiles(abs, isCfgFile)) {
      tally.files++;
      const shown = opts._.length > 1 || fs.statSync(abs).isDirectory() ? slash(path.join(path.basename(abs), f.rel)) : f.rel;
      const text = readText(f.abs);
      const sc = scan(text);
      for (const p of sc.problems) report(p.level, shown, p.line, p.msg);
      let roots;
      try {
        roots = Struct.fromString(text);
      } catch (e) {
        report('ERROR', shown, 0, `s2cfgtojson cannot parse it: ${e.message}`);
        continue;
      }
      if (!roots.length) { report('WARN', shown, 0, 'no structs in this file'); continue; }
      const lint = sc.problems.some((p) => p.level === 'ERROR');
      const ct = countTree(roots);
      if (!lint && (roots.length !== sc.roots.length || ct.structs !== sc.structs || ct.values !== sc.values)) {
        report('ERROR', shown, 0, `s2cfgtojson reads ${roots.length} roots / ${ct.structs} structs / ${ct.values} values, the line scan ${sc.roots.length} / ${sc.structs} / ${sc.values}: some line is misread`);
      }
      const back = Struct.fromString(rootsToText(roots));
      const bad = [];
      for (let i = 0; i < Math.max(roots.length, back.length); i++) {
        if (!roots[i] || !back[i] || JSON.stringify(canonical(roots[i])) !== JSON.stringify(canonical(back[i]))) bad.push(roots[i] ? roots[i].__internal__.rawName : '(extra)');
      }
      if (bad.length) report('ERROR', shown, 0, `does not survive a text round trip in ${bad.length} record(s): ${bad.slice(0, 5).join(', ')}`);
      const where = gameDataRel(f.abs) || { rel: f.rel, dlc: false };
      if (!refurlChecks(shown, where, opts.target || modTarget(f.abs), sc.refs, report)) targetUnknown++;
      if (vdir || ddir) {
        const dir = where.dlc ? ddir : vdir;
        if (!dir) { if (where.dlc) dlcSkipped++; continue; }
        const rootLines = sc.roots.length === roots.length ? sc.roots.map((r) => r.line) : [];
        const ctx = patchChecks(shown, where.rel, roots, rootLines, dir, where.dlc ? 'DLC:' : '', report, setters);
        const own = new Set(sc.roots.map((r) => r.name));
        for (const r of sc.refs) if (r.refkey && !r.refurl) orphans.push({ file: shown, own, ...ctx, ...r });
      }
    }
  }
  for (const [key, files] of setters) {
    if (files.size < 2) continue;
    const [tid, what] = key.split('|');
    const list = [...files].join(', ');
    if (key.endsWith('|created')) report('WARN', list, 0, `record ${what} of ${tid} is created by ${files.size} files: keep one`);
    else report('WARN', list, 0, `${what} (${tid}) is set by ${files.size} files: when two patches set one field the later pak does not reliably win; set it in one file`);
  }
  // A refkey without refurl: its parent must be a root of the same file, of the vanilla table the file
  // patches, or a record another file of the mod creates in that table.
  for (const o of orphans) {
    const fits = (k) => o.own.has(k) || (o.table && o.table.byName.has(k)) || setters.has(`${o.tid}|${k}|created`);
    const parent = fits(o.refkey) ? o.refkey : o.refkey.split('.')[0];
    if (fits(parent)) continue;
    report('WARN', o.file, o.line, `${o.name || 'struct'} has refkey=${o.refkey} and no refurl, but ${parent} is not a root of this file${o.table ? ` or of vanilla ${o.tid}` : ''}: without refurl a refkey looks in the same file, and one left without its refurl is reported to overflow the stack while cfg loads (EXCEPTION_STACK_OVERFLOW); add the refurl or correct the name`);
  }
  if (targetUnknown) console.log(`NOTE  ${targetUnknown} file(s) with a refurl sit outside GameData/ and ModGameData/, so the kind of mod is unknown: give --target pak|zonekit for the refurl checks`);
  if (dlcSkipped) console.log(`NOTE  ${dlcSkipped} file(s) under DLCGameData/ got no patch checks: give --dlc-vanilla <that DLC's extract>`);
  console.log(`\nchecked ${tally.files} file(s): ${tally.ERROR} error(s), ${tally.WARN} warning(s)${tally.NOTE ? `, ${tally.NOTE} note(s)` : ''}`);
  return tally.ERROR ? 1 : 0;
}

runCli(USAGE, main);
