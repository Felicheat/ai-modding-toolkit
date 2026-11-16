r"""Which build of which mod is really deployed in ~mods, by file content.

A Vortex folder name is the version FIRST installed: updating a mod swaps the files and keeps the old folder name, so never
read a version off a folder name. This hashes every .pak/.utoc/.ucas in ~mods and matches it against the release builds
you keep on disk.

    python mods_identify.py --repos <folder-or-glob> [...]                 every Vortex folder in ~mods
    python mods_identify.py --repos "<projects>/*" --filter npc            only folders or files whose name contains "npc"

--repos says where to look for release builds: one or more folders or glob patterns (quote a glob). A folder that holds a
release/ subfolder is read from there (release/v1.2.0/, release/fomod/1.2.0/stage/, ...), any other folder as a whole. A
build is labelled "<folder name> <subfolder path>", e.g. "MyMod v1.2.0".

Per ~mods folder it prints the build every file agrees on. "NO MATCH" means a mod that is not in the given folders, or a
build that was never kept. Hashes are cached by path, size and time in the work folder (see s2paths.py). Read-only.
"""
import argparse, glob, hashlib, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s2paths

EXTS = ('.pak', '.utoc', '.ucas')


def cache_path():
    return os.path.join(s2paths.work_dir(), 'mods_identify_cache.json')


def load_cache():
    try:
        with open(cache_path(), encoding='utf-8') as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def md5(path, cache):
    st = os.stat(path)
    key = '%s|%d|%d' % (os.path.abspath(path), st.st_size, int(st.st_mtime))
    if key not in cache:
        h = hashlib.md5()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 20), b''):
                h.update(chunk)
        cache[key] = h.hexdigest()
    return cache[key]


def label(repo, base, path):
    """'<repo> <build>' from a build path: release/v1.2.0/x.pak -> v1.2.0; release/fomod/1.2.0/stage -> v1.2.0."""
    parts = os.path.relpath(path, base).replace('\\', '/').split('/')[:-1]
    parts = [p for p in parts if p not in ('stage', 'fomod')]
    build = '/'.join(parts) or 'release'
    if build[:1].isdigit():
        build = 'v' + build
    return '%s %s' % (os.path.basename(os.path.normpath(repo)), build)


def repo_folders(patterns):
    out, seen = [], set()
    for pat in patterns:
        hits = glob.glob(pat) if any(c in pat for c in '*?[') else [pat]
        for h in hits:
            key = os.path.normcase(os.path.abspath(h))
            if os.path.isdir(h) and key not in seen:
                seen.add(key)
                out.append(h)
    return out


def index_releases(repos, cache):
    known = {}
    for repo in repos:
        rel = os.path.join(repo, 'release')
        base = rel if os.path.isdir(rel) else repo
        for d, _, files in os.walk(base):
            for f in files:
                if f.lower().endswith(EXTS):
                    p = os.path.join(d, f)
                    known.setdefault(md5(p, cache), set()).add(label(repo, base, p))
    return known


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--repos', nargs='+', metavar='FOLDER_OR_GLOB', help='where to look for release builds')
    ap.add_argument('--filter', default='', help='only ~mods folders or files whose name contains this text')
    a = ap.parse_args()
    if not a.repos:
        print('Tell the script where your release builds are:\n'
              '    python mods_identify.py --repos "<folder>" ["<another folder or glob>" ...] [--filter <text>]\n'
              'Each folder is read from its release/ subfolder if it has one, otherwise as a whole.')
        return 2
    repos = repo_folders(a.repos)
    if not repos:
        print('none of these is a folder: %s' % ', '.join(a.repos))
        return 2
    mods = s2paths.mods_dir()
    if not os.path.isdir(mods):
        print('no ~mods folder at %s' % mods)
        return 2
    filt = a.filter.lower()
    cache = load_cache()
    known = index_releases(repos, cache)
    groups = {}
    for d, _, files in os.walk(mods):
        for f in files:
            if f.lower().endswith(EXTS):
                p = os.path.join(d, f)
                top = os.path.relpath(p, mods).replace('\\', '/').split('/')[0]
                if filt and filt not in top.lower() and filt not in f.lower():
                    continue
                groups.setdefault(top if top != f else '(loose in ~mods)', []).append((f, known.get(md5(p, cache), set())))
    try:
        with open(cache_path(), 'w', encoding='utf-8') as fh:
            json.dump(cache, fh)
    except OSError as e:
        print('(could not save the hash cache: %s)' % e, file=sys.stderr)
    print('release builds indexed from %d folder(s), %d distinct files' % (len(repos), len(known)))
    for top in sorted(groups):
        files = groups[top]
        utocs = {os.path.splitext(f)[0].lower() for f, _ in files if f.lower().endswith('.utoc')}
        # In an IoStore trio the .pak is a near-empty stub shared by many builds; the .utoc names the build.
        voters = [(f, s) for f, s in files if not (f.lower().endswith('.pak') and os.path.splitext(f)[0].lower() in utocs)]
        matched = [s for _, s in voters if s]
        common = set.intersection(*matched) if matched and len(matched) == len(voters) else set()
        print('\n' + top)
        if common:
            print('  REALLY: ' + ', '.join(sorted(common)) + '   (every file agrees; ignore the folder name)')
        elif matched:
            print('  MIXED: the files come from different builds (or some match none); read the lines below')
        for f, s in sorted(files):
            stub = f.lower().endswith('.pak') and os.path.splitext(f)[0].lower() in utocs
            text = (', '.join(sorted(s)[:3]) + (' ...' if len(s) > 3 else '')) if s else 'NO MATCH'
            print('  %-60s %s' % (f, '(IoStore stub, not counted)' if stub else text))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except s2paths.S2PathError as e:
        print(e, file=sys.stderr)
        sys.exit(2)
