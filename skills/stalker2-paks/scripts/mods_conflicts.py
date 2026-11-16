r"""What overrides what in ~mods: list every file each installed pak provides and report files provided more than once.

Every .utoc is read with `retoc manifest` (cooked packages; file entries are the paths the game will load) and every .pak
with `repak list` (plain content such as cfg; mod archives can hide cfg in a plain OverrideContent*.pak next to a trio).
When two containers provide the same file, the higher `_<N>_P` mount priority wins; a name without a number tail sorts
below any numbered one. Equal priorities are reported as a tie. Read-only.

    python mods_conflicts.py                     conflicts in the game's ~mods
    python mods_conflicts.py --all               also list every file per container
    python mods_conflicts.py --dir <folder>      scan another folder (a release folder, an unpacked mod download)

Needs retoc and repak (found through s2paths.py).
"""
import json, os, re, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s2paths

_TOOLS = {}


def tool(name):
    if name not in _TOOLS:
        _TOOLS[name] = s2paths.tool(name)
    return _TOOLS[name]


def norm(p):
    p = p.replace('\\', '/')
    while p.startswith('../'):
        p = p[3:]
    return p


def priority(filename):
    stem = os.path.splitext(filename)[0]
    m = re.search(r'_(\d+)_P$', stem)
    if m:
        return int(m.group(1))
    return 0 if stem.endswith('_P') else -1


def utoc_files(path, tmp):
    r = subprocess.run([tool('retoc'), 'manifest', path], capture_output=True, text=True, cwd=tmp)
    store = os.path.join(tmp, 'pakstore.json')
    if r.returncode or not os.path.isfile(store):
        return None
    try:
        with open(store, encoding='utf-8') as fh:
            data = json.load(fh)
    finally:
        os.remove(store)
    return [norm(pd['filename']) for e in data['oplog']['entries'] for pd in e.get('packagedata', [])]


def pak_files(path):
    r = subprocess.run([tool('repak'), 'list', path], capture_output=True, text=True)
    if r.returncode:
        return None
    return [norm(l.strip()) for l in r.stdout.splitlines() if l.strip()]


def main():
    args = sys.argv[1:]
    if '-h' in args or '--help' in args:
        print(__doc__)
        return 0
    if '--dir' in args:
        i = args.index('--dir')
        if i + 1 >= len(args):
            print('--dir needs a folder')
            return 2
        root = args[i + 1]
    else:
        root = s2paths.mods_dir()
    if not os.path.isdir(root):
        print('no such folder: %s' % root)
        return 2
    providers, unreadable, n = {}, [], 0
    with tempfile.TemporaryDirectory() as tmp:
        for dp, _, files in os.walk(root):
            for f in sorted(files):
                path = os.path.join(dp, f)
                if f.endswith('.utoc'):
                    got = utoc_files(path, tmp)
                elif f.endswith('.pak'):
                    got = pak_files(path)
                else:
                    continue
                label = os.path.relpath(path, root)
                if got is None:
                    unreadable.append(label)
                    continue
                n += 1
                if '--all' in args:
                    print('%s (%d files)' % (label, len(got)))
                    for g in got:
                        print('    ' + g)
                for g in set(got):
                    providers.setdefault(g, []).append((priority(f), label))
    conflicts = {k: v for k, v in providers.items() if len({lbl for _, lbl in v}) > 1}
    print('scanned %d containers in %s, %d files, %d provided more than once' % (n, root, len(providers), len(conflicts)))
    for k in sorted(conflicts):
        v = sorted(conflicts[k], reverse=True)
        top = [x for x in v if x[0] == v[0][0]]
        verdict = 'TIE at priority %s' % v[0][0] if len(top) > 1 else 'winner: ' + v[0][1]
        print('\n' + k + '   (' + verdict + ')')
        for p, lbl in v:
            print('    %-6s %s' % ('_%d_P' % p if p > 0 else ('_P' if p == 0 else 'none'), lbl))
    if unreadable:
        print('\ncould not read: ' + ', '.join(unreadable))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except s2paths.S2PathError as e:
        print(e, file=sys.stderr)
        sys.exit(2)
