// Text serializer for s2cfgtojson Struct trees that keeps names verbatim.
// s2cfgtojson's Struct.toString() renders any key that parseInt() reads as a number as an
// array index (a 32-hex GUID key such as 4EB1...D54 comes out as "[4]"), and once a struct
// holds one [*] entry it renders every sibling as [*]. Its text parser also renames nested
// struct keys (non-word characters become "_", leading digits are dropped) while keeping the
// real name in __internal__.rawName. This writer avoids all three: struct children are written
// under their rawName, "[N]" / "[*]" only for real array slots, everything else verbatim.
// Format otherwise as s2cfgtojson: 3-space indent, "Name : struct.begin {refs}", the raw
// literal of each value as decoded ("600.f" stays "600.f"), "key =" for an empty value,
// "Key : removenode".
import { Struct, parseValue } from 's2cfgtojson';

const TAB = '   ';
const RAW = '__rawLiterals__';
const KEYWORDS = ['refurl', 'refkey', 'bskipref', 'bpatch'];

export function refsText(internal) {
  return KEYWORDS.map((k) => [k, internal[k]])
    .filter(([, v]) => v !== '' && v !== undefined && v !== false)
    .map(([k, v]) => (v === true ? k : `${k}=${v}`))
    .join(';');
}

/** The name an entry is written under. */
export function keyName(parent, key, value) {
  const internal = parent.__internal__ || {};
  const base = `${key}`.replace(/_dupe_\d+$/, '');
  const raw = value instanceof Struct ? value.__internal__ && value.__internal__.rawName : undefined;
  // Only real array slots get brackets: a container flagged isArray can still
  // carry named siblings (e.g. a type field next to [0], [1]).
  if (internal.isArray && /^\d+$/.test(base)) {
    // A struct slot keeps what its own header said ([3] or [*]); a value slot cannot tell.
    if (typeof raw === 'string' && /^\[(\d+|\*)\]$/.test(raw)) return raw;
    return internal.useAsterisk ? '[*]' : `[${base}]`;
  }
  if (typeof raw === 'string' && raw !== '' && !raw.startsWith('[')) return raw;
  return base;
}

/** The text a value is written as: its decoded literal when it still matches the value. */
export function literal(parent, key, value) {
  const raw = parent[RAW] && parent[RAW][key];
  if (raw !== undefined && parseValue(raw) === value) return raw;
  return `${value}`;
}

/** One struct as text. name = the header name, or null for a bare "struct.begin". */
export function structToText(node, name, depth = 0, comment = null) {
  const internal = node.__internal__ || {};
  const indent = TAB.repeat(depth);
  if (depth === 0 && internal.removenode) return `${name} : removenode`;
  const refs = refsText(internal);
  const lines = [];
  if (comment) lines.push(`${indent}// ${comment}`);
  lines.push(`${indent}${name !== null ? `${name} : ` : ''}struct.begin${refs ? ` {${refs}}` : ''}`);
  for (const [key, value] of Object.entries(node)) {
    if (key === '__internal__') continue;
    const kn = keyName(node, key, value);
    if (value instanceof Struct) {
      if (value.__internal__ && value.__internal__.removenode) {
        lines.push(`${indent}${TAB}${kn} : removenode`);
      } else {
        lines.push(structToText(value, kn, depth + 1));
      }
    } else if (value === '') {
      lines.push(`${indent}${TAB}${kn} =`);
    } else {
      lines.push(`${indent}${TAB}${kn} = ${literal(node, key, value)}`);
    }
  }
  lines.push(`${indent}struct.end`);
  return lines.join('\n');
}

/** Several root structs as one cfg text. commentFor(root) may return a line to put above a root. */
export function rootsToText(roots, commentFor = null) {
  return roots.map((r) => structToText(r, r.__internal__.rawName, 0, commentFor ? commentFor(r) : null)).join('\n') + '\n';
}

/** A plain, order-keeping form of a struct for comparisons: exactly what this writer prints. */
export function canonical(node) {
  const out = { refs: refsText(node.__internal__ || {}), removenode: !!(node.__internal__ && node.__internal__.removenode), e: [] };
  for (const [key, value] of Object.entries(node)) {
    if (key === '__internal__') continue;
    const kn = keyName(node, key, value);
    out.e.push([kn, value instanceof Struct ? canonical(value) : value === '' ? '' : literal(node, key, value)]);
  }
  return out;
}
