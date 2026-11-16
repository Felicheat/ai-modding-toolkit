r"""Check release text (mod page, readme, changelog, installer XML) against the writing rules.

    python check_release_text.py <file or folder> [<file or folder> ...] [--rules FILE] [--group NAME ...]
    python check_release_text.py --list-rules [--rules FILE]

Folders are searched recursively for the file extensions the rules file lists. The rules live in
release_text_rules.json next to this script; edit that file to suit (--rules picks another one). Each rule has:
  id, level (FAIL or WARN), pattern (a Python regex), message,
  optional ignore_case (true/false), optional allow (a regex: a line matching it is not reported for this rule),
  optional group ("core" when left out). Core rules always run; other groups run only when named with --group,

Output: one "FAIL file:line [rule] message: excerpt" or "WARN ..." line per finding, then a summary.
FAIL means fix it before release; WARN means a person reads the line and decides.
Exit codes: 0 no FAIL, 1 at least one FAIL, 2 usage error or a broken rules file. Stdlib only, no network.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RULES = os.path.join(HERE, 'release_text_rules.json')
SKIP_DIRS = {'.git', '__pycache__', 'node_modules', 'bin', 'obj'}
LEVELS = ('FAIL', 'WARN')


class RulesError(Exception):
    pass


def load_rules(path):
    try:
        with open(path, encoding='utf-8') as fh:
            data = json.load(fh)
    except (OSError, ValueError) as e:
        raise RulesError('cannot read rules file %s: %s' % (path, e))
    rules = []
    seen = set()
    for i, r in enumerate(data.get('rules', [])):
        rid = r.get('id') or 'rule%d' % i
        if rid in seen:
            raise RulesError('duplicate rule id %r' % rid)
        seen.add(rid)
        level = str(r.get('level', 'WARN')).upper()
        if level not in LEVELS:
            raise RulesError('rule %s: level must be FAIL or WARN' % rid)
        flags = re.IGNORECASE if r.get('ignore_case') else 0
        try:
            rx = re.compile(r['pattern'], flags)
            allow = re.compile(r['allow'], flags) if r.get('allow') else None
        except (KeyError, re.error) as e:
            raise RulesError('rule %s: bad pattern: %s' % (rid, e))
        rules.append({'id': rid, 'level': level, 'rx': rx, 'allow': allow,
                      'message': r.get('message', rid), 'group': r.get('group', 'core')})
    if not rules:
        raise RulesError('no rules in %s' % path)
    exts = [e.lower() for e in data.get('extensions', ['.txt', '.md'])]
    return rules, exts


def read_text(path):
    """Return (text, note). Handles UTF-8 (with or without BOM) and UTF-16 with BOM; falls back to cp1252."""
    raw = open(path, 'rb').read()
    if raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
        return raw.decode('utf-16'), None
    if raw.startswith(b'\xef\xbb\xbf'):
        return raw[3:].decode('utf-8', errors='replace'), None
    try:
        return raw.decode('utf-8'), None
    except UnicodeDecodeError:
        return raw.decode('cp1252', errors='replace'), 'not UTF-8, read as Windows-1252'


def iter_files(paths, exts):
    for p in paths:
        if os.path.isdir(p):
            for dirpath, dirnames, filenames in os.walk(p):
                dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
                for f in sorted(filenames):
                    if os.path.splitext(f)[1].lower() in exts:
                        yield os.path.join(dirpath, f)
        else:
            yield p


def shown(match_text):
    """The matched text, with characters outside printable ASCII written as U+XXXX."""
    return ''.join(c if 32 <= ord(c) < 127 else 'U+%04X' % ord(c) for c in match_text)


def excerpt(line, start, width=110):
    line = line.rstrip('\r\n')
    lo = max(0, start - width // 2)
    text = line[lo:lo + width].strip()
    text = ''.join(c if ord(c) < 0x2000 else '<U+%04X>' % ord(c) for c in text)
    return ('...' if lo > 0 else '') + text + ('...' if lo + width < len(line) else '')


def check_file(path, rules, counts):
    text, note = read_text(path)
    if note:
        print('WARN %s [encoding] %s' % (path, note))
        counts['WARN'] += 1
    for n, line in enumerate(text.splitlines(), 1):
        for r in rules:
            if r['allow'] and r['allow'].search(line):
                continue
            for m in r['rx'].finditer(line):
                print('%s %s:%d [%s] %s: "%s" in: %s' % (r['level'], path, n, r['id'], r['message'],
                                                        shown(m.group(0)), excerpt(line, m.start())))
                counts[r['level']] += 1
                break


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('paths', nargs='*', help='files or folders to check')
    p.add_argument('--rules', default=DEFAULT_RULES, help='rules file (default: release_text_rules.json here)')
    p.add_argument('--group', action='append', default=[], help='also run the rules of this group (repeatable)')
    p.add_argument('--list-rules', action='store_true', help='print the rules and exit')
    a = p.parse_args(argv)
    try:
        sys.stdout.reconfigure(errors='replace')
    except (AttributeError, ValueError):
        pass
    try:
        rules, exts = load_rules(a.rules)
    except RulesError as e:
        print('STOP ' + str(e))
        return 2
    groups = {'core'} | set(a.group)
    unknown = set(a.group) - {r['group'] for r in rules}
    if unknown:
        print('STOP no rules in group(s): %s' % ', '.join(sorted(unknown)))
        return 2
    active = [r for r in rules if r['group'] in groups]
    if a.list_rules:
        for r in rules:
            print('%-4s %-24s group=%-9s %s' % (r['level'], r['id'], r['group'], r['message']))
        return 0
    if not a.paths:
        p.print_usage()
        print('STOP give at least one file or folder')
        return 2
    counts = {'FAIL': 0, 'WARN': 0}
    checked = 0
    for path in iter_files(a.paths, exts):
        if not os.path.isfile(path):
            print('STOP not found: %s' % path)
            return 2
        check_file(path, active, counts)
        checked += 1
    print('checked %d file(s) with %d rule(s) (groups: %s): %d FAIL, %d WARN'
          % (checked, len(active), ', '.join(sorted(groups)), counts['FAIL'], counts['WARN']))
    return 1 if counts['FAIL'] else 0


if __name__ == '__main__':
    sys.exit(main())
