r"""Did a game update change the vanilla files a mod replaces or patches? Compare a saved baseline with the game, byte
for byte, or make that baseline before the next update.

A baseline is a folder of vanilla files laid out by their path inside the game, for example
  <baseline>/Stalker2/Content/GameLite/GameData/ItemPrototypes.cfg.bin        (cfg, from a plain .pak)
  <baseline>/Stalker2/Content/Example/Textures/T_Example.uasset + .uexp       (cooked, via retoc)

  python compare_tables.py <baseline>                          compare every cfg file in the baseline with the game
  python compare_tables.py <baseline> --extract <list>         MAKE a baseline: copy these cfg entries out of the game
  python compare_tables.py <baseline> --cooked <fragment>      compare cooked assets whose file path contains
                                                               <fragment> (retoc to-legacy into the work folder)
  python compare_tables.py <baseline> --cooked <fragment> --save   MAKE a cooked baseline from the current game

Options:
  --pak <pak>     search this .pak instead of the defaults (repeatable). Defaults: <paks>/pakchunk0-Windows.pak,
                  <game>/DLC1/S2_DLC1Stalker2-Windows.pak and the edition paks <paks>/pakchunk101/102/104-Windows.pak
  --paks <dir>    the folder retoc reads for --cooked (default <paks>; it must hold global.utoc)
  --force         let --extract / --save overwrite a different file already in the baseline
  --keep          keep the --cooked extraction in the work folder (the path is printed)
  --json          machine-readable result

<list> is a text file with one entry per line, or a comma-separated list. An entry is a full path inside the pak
(Stalker2/Content/GameLite/GameData/CoreVariables.cfg) or a file name or path tail (ItemPrototypes.cfg.bin,
GameData/ItemPrototypes.cfg.bin), looked up in the paks' file lists (every match is taken).
<fragment> is matched by retoc as a CASE-SENSITIVE substring of the asset's file path
(Stalker2/Content/Example/Textures/T_Example), not of the /Game/... package name: "Example/Textures" and
"T_Example" match, "example/textures" and "/Game/Example" match nothing.

Per file: IDENTICAL, CHANGED or MISSING (in the baseline, no longer in the game), with sha256; --cooked also reports
NEW (in the game, not in the baseline). A baseline also gets _baseline.json (build id, date, sha256 per file).
Exit code: 0 = all identical, 1 = something changed, is missing or new, 2 = usage or tool error.
Writes only inside <baseline> (--extract, --save) and inside the pack's work folder (--cooked, removed afterwards
unless --keep). Never touches the game. Needs repak (and retoc for --cooked), found through s2paths.py.
"""
import argparse, datetime, hashlib, json, os, re, shutil, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s2paths

META = '_baseline.json'
COOKED_EXT = ('.uasset', '.uexp', '.ubulk', '.uptnl', '.umap')
SKIP_OUT = ('scriptobjects.bin',)


class Fail(Exception):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def norm(p):
    p = p.replace('\\', '/').strip()
    while p.startswith('../'):
        p = p[3:]
    return p.lstrip('/')


def inside(root, path):
    root, path = os.path.abspath(root), os.path.abspath(path)
    try:
        return os.path.commonpath([root, path]) == root
    except ValueError:
        return False


def default_paks():
    paks = s2paths.paks_dir()
    game = s2paths.game_dir()
    cands = [os.path.join(paks, 'pakchunk0-Windows.pak'), os.path.join(game, 'DLC1', 'S2_DLC1Stalker2-Windows.pak')]
    cands += [os.path.join(paks, 'pakchunk%d-Windows.pak' % n) for n in (101, 102, 104)]
    return [p for p in cands if os.path.isfile(p)]


def pak_index(paks, repak):
    """{entry: pak} from `repak list` of every pak; the first pak listing an entry wins."""
    index = {}
    for pak in paks:
        r = subprocess.run([repak, 'list', pak], capture_output=True, text=True, encoding='utf-8', errors='replace')
        if r.returncode:
            raise Fail('repak list failed for %s: %s' % (pak, (r.stderr or r.stdout).strip()[:300]))
        for line in r.stdout.splitlines():
            e = norm(line)
            if e and e not in index:
                index[e] = pak
    return index


def repak_get(repak, pak, entry):
    r = subprocess.run([repak, 'get', pak, entry], capture_output=True)
    if r.returncode:
        raise Fail('repak get failed for %s in %s: %s' % (entry, pak, r.stderr.decode('utf-8', 'replace').strip()[:300]))
    return r.stdout


def baseline_files(base):
    out = []
    for d, dirs, files in os.walk(base):
        dirs.sort()
        for f in sorted(files):
            p = os.path.join(d, f)
            rel = norm(os.path.relpath(p, base))
            if rel != META:
                out.append(rel)
    return out


def load_meta(base):
    try:
        with open(os.path.join(base, META), encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_meta(base, added):
    meta = load_meta(base)
    build = None
    try:
        acf = s2paths.steam_manifest()
        if acf:
            m = re.search(r'"buildid"\s+"(\d+)"', open(acf, encoding='utf-8', errors='replace').read())
            build = m.group(1) if m else None
    except (s2paths.S2PathError, OSError):
        pass
    meta.setdefault('files', {}).update(added)
    meta['build'] = build or meta.get('build')
    meta['updated'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    tmp = os.path.join(base, META + '.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2, sort_keys=True)
    os.replace(tmp, os.path.join(base, META))


def write_into(base, rel, data, force):
    """Write one baseline file. Returns SAVED, THERE (identical file already there) or CONFLICT (a different file
    is there and --force was not given)."""
    dst = os.path.join(base, *rel.split('/'))
    if not inside(base, dst):
        raise Fail('refusing to write outside the baseline: %s' % rel)
    if os.path.isfile(dst):
        if sha_file(dst) == sha(data):
            return 'THERE'
        if not force:
            return 'CONFLICT'
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, 'wb') as f:
        f.write(data)
    return 'SAVED'


def read_list(spec):
    if os.path.isfile(spec):
        items = open(spec, encoding='utf-8').read().splitlines()
    else:
        items = spec.split(',')
    return [norm(i) for i in items if i.strip() and not i.strip().startswith('#')]


def resolve(item, index):
    if item in index:
        return [item]
    low = item.lower()
    exact = [e for e in index if e.lower() == low]
    if exact:
        return exact
    return sorted(e for e in index if e.lower().endswith('/' + low))


# ---------------- modes ----------------

def do_extract(base, spec, paks, repak, force):
    index = pak_index(paks, repak)
    rows, added = [], {}
    for item in read_list(spec):
        hits = resolve(item, index)
        if not hits:
            rows.append({'status': 'NOT FOUND', 'entry': item})
            continue
        for e in hits:
            data = repak_get(repak, index[e], e)
            st = write_into(base, e, data, force)
            rows.append({'status': st, 'entry': e, 'sha256': sha(data), 'size': len(data),
                         'pak': os.path.basename(index[e])})
            if st != 'CONFLICT':
                added[e] = {'sha256': sha(data), 'pak': os.path.basename(index[e])}
    if added:
        save_meta(base, added)
    bad = any(r['status'] in ('NOT FOUND', 'CONFLICT') for r in rows)
    return rows, 1 if bad else 0


def do_compare(base, paks, repak):
    index = pak_index(paks, repak)
    rows, cooked = [], 0
    for rel in baseline_files(base):
        if rel.lower().endswith(COOKED_EXT):
            cooked += 1
            continue
        mine = sha_file(os.path.join(base, *rel.split('/')))
        if rel not in index:
            rows.append({'status': 'MISSING', 'entry': rel, 'baseline_sha256': mine})
            continue
        data = repak_get(repak, index[rel], rel)
        game = sha(data)
        rows.append({'status': 'IDENTICAL' if game == mine else 'CHANGED', 'entry': rel, 'baseline_sha256': mine,
                     'game_sha256': game, 'baseline_size': os.path.getsize(os.path.join(base, *rel.split('/'))),
                     'game_size': len(data), 'pak': os.path.basename(index[rel])})
    if cooked:
        rows.append({'status': 'SKIPPED', 'entry': '%d cooked files' % cooked,
                     'note': 'compare those with --cooked <fragment>'})
    bad = any(r['status'] in ('CHANGED', 'MISSING') for r in rows)
    return rows, 1 if bad else 0


def extract_cooked(fragment, paks_dir, retoc):
    root = os.path.join(s2paths.work_dir(), 'compare_tables')
    os.makedirs(root, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix='cooked_', dir=root)
    out = os.path.join(tmp, 'out')
    r = subprocess.run([retoc, 'to-legacy', '--no-shaders', '-f', fragment, paks_dir, out],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    log = (r.stdout + '\n' + r.stderr).strip()
    if r.returncode:
        shutil.rmtree(tmp, ignore_errors=True)
        raise Fail('retoc to-legacy failed: %s' % log[-600:])
    files = {}
    if os.path.isdir(out):
        for d, _, fs in os.walk(out):
            for f in fs:
                if f.lower() in SKIP_OUT:
                    continue
                p = os.path.join(d, f)
                files[norm(os.path.relpath(p, out))] = p
    m = re.search(r'Extracted (\d+) \((\d+) failed\)', log)
    return tmp, files, (int(m.group(1)), int(m.group(2))) if m else None


def do_cooked(base, fragment, paks_dir, retoc, save, force, keep):
    tmp, files, counts = extract_cooked(fragment, paks_dir, retoc)
    rows, code = [], 0
    try:
        if not files:
            raise Fail('no asset path contains %r (retoc: %s). The fragment is a case-sensitive substring of the '
                       'Stalker2/Content/... file path, not of /Game/...; a wrong folder or case matches nothing. Try '
                       'the bare asset name.' % (fragment, counts))
        if counts and counts[1]:
            rows.append({'status': 'WARNING', 'entry': '', 'note': 'retoc reported %d failed assets' % counts[1]})
        if save:
            added = {}
            for rel in sorted(files):
                data = open(files[rel], 'rb').read()
                st = write_into(base, rel, data, force)
                rows.append({'status': st, 'entry': rel, 'sha256': sha(data), 'size': len(data)})
                if st != 'CONFLICT':
                    added[rel] = {'sha256': sha(data), 'cooked_fragment': fragment}
                else:
                    code = 1
            if added:
                save_meta(base, added)
        else:
            frag = fragment.replace('\\', '/')
            seen = set()
            for rel in sorted(files):
                seen.add(rel)
                game = sha_file(files[rel])
                mine_p = os.path.join(base, *rel.split('/'))
                if not os.path.isfile(mine_p):
                    rows.append({'status': 'NEW', 'entry': rel, 'game_sha256': game})
                    code = 1
                    continue
                mine = sha_file(mine_p)
                same = mine == game
                rows.append({'status': 'IDENTICAL' if same else 'CHANGED', 'entry': rel, 'baseline_sha256': mine,
                             'game_sha256': game, 'baseline_size': os.path.getsize(mine_p),
                             'game_size': os.path.getsize(files[rel])})
                code = code if same else 1
            for rel in baseline_files(base):
                if rel in seen or not rel.lower().endswith(COOKED_EXT):
                    continue
                if frag in rel:                  # retoc's filter: a case-sensitive substring of this path
                    rows.append({'status': 'MISSING', 'entry': rel,
                                 'baseline_sha256': sha_file(os.path.join(base, *rel.split('/')))})
                    code = 1
    finally:
        if keep:
            rows.append({'status': 'KEPT', 'entry': tmp, 'note': 'extraction kept in the work folder'})
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    return rows, code


def print_rows(rows):
    counts = {}
    for r in rows:
        counts[r['status']] = counts.get(r['status'], 0) + 1
        st = r['status']
        if st in ('IDENTICAL', 'SAVED', 'THERE'):
            print('%-10s %s  %s' % (st, r.get('game_sha256') or r.get('sha256'), r['entry']))
        elif st == 'CONFLICT':
            print('%-10s %s  %s   (a different file is already in the baseline: --force replaces it)'
                  % (st, r['sha256'], r['entry']))
        elif st == 'CHANGED':
            print('%-10s %s  %s' % (st, r['baseline_sha256'], r['entry']))
            print('%-10s %s  (game copy; size %d -> %d)' % ('', r['game_sha256'], r['baseline_size'], r['game_size']))
        elif st == 'MISSING':
            print('%-10s %s  %s   (not in the game any more)' % (st, r['baseline_sha256'], r['entry']))
        elif st == 'NEW':
            print('%-10s %s  %s   (not in the baseline)' % (st, r['game_sha256'], r['entry']))
        else:
            print('%-10s %s%s' % (st, r['entry'], ('   ' + r['note']) if r.get('note') else ''))
    print('summary: ' + ', '.join('%d %s' % (n, s.lower()) for s, n in sorted(counts.items())))


def main(argv):
    ap = argparse.ArgumentParser(description='Compare a baseline of vanilla files with the installed game, or make one.',
                                 epilog='Exit 0 = all identical, 1 = changed / missing / new, 2 = error. '
                                        'Full usage: read this script\'s docstring.')
    ap.add_argument('baseline', help='baseline folder (files laid out by their path inside the game)')
    ap.add_argument('--extract', metavar='LIST', help='make a cfg baseline from these entries (file or a,b,c)')
    ap.add_argument('--cooked', metavar='FRAGMENT', help='cooked assets whose file path contains FRAGMENT (case-sensitive)')
    ap.add_argument('--save', action='store_true', help='with --cooked: save into the baseline instead of comparing')
    ap.add_argument('--pak', action='append', help='a .pak to read instead of the defaults (repeatable)')
    ap.add_argument('--paks', help='folder retoc reads for --cooked (default <paks>)')
    ap.add_argument('--force', action='store_true', help='overwrite different files already in the baseline')
    ap.add_argument('--keep', action='store_true', help='keep the --cooked extraction in the work folder')
    ap.add_argument('--json', action='store_true', help='print JSON')
    a = ap.parse_args(argv)
    if a.extract and a.cooked:
        ap.error('--extract and --cooked are separate modes')
    if a.save and not a.cooked:
        ap.error('--save goes with --cooked (use --extract for cfg tables)')
    base = os.path.abspath(a.baseline)
    making = bool(a.extract or a.save)
    try:
        if not making and not os.path.isdir(base):
            raise Fail('baseline folder not found: %s' % base)
        if making:
            os.makedirs(base, exist_ok=True)
        if a.cooked:
            retoc = s2paths.tool('retoc')
            paks_dir = a.paks or s2paths.paks_dir()
            if not os.path.isfile(os.path.join(paks_dir, 'global.utoc')):
                raise Fail('%s has no global.utoc: point --paks at <game>/Stalker2/Content/Paks' % paks_dir)
            rows, code = do_cooked(base, a.cooked, paks_dir, retoc, a.save, a.force, a.keep)
            mode = 'cooked-save' if a.save else 'cooked-compare'
        else:
            repak = s2paths.tool('repak')
            paks = [os.path.abspath(p) for p in a.pak] if a.pak else default_paks()
            for p in paks:
                if not os.path.isfile(p):
                    raise Fail('pak not found: %s' % p)
            if not paks:
                raise Fail('no game paks found (python s2paths.py shows the game folder)')
            if a.extract:
                rows, code = do_extract(base, a.extract, paks, repak, a.force)
                mode = 'extract'
            else:
                rows, code = do_compare(base, paks, repak)
                mode = 'compare'
    except (Fail, s2paths.S2PathError, OSError) as e:
        if a.json:
            print(json.dumps({'error': str(e)}))
        else:
            print('error: %s' % e, file=sys.stderr)
        return 2
    meta = load_meta(base)
    if a.json:
        print(json.dumps({'mode': mode, 'baseline': base, 'baseline_build': meta.get('build'),
                          'rows': rows, 'exit': code}, indent=2))
        return code
    print('baseline: %s%s' % (base, ('   (build %s, updated %s)' % (meta.get('build'), meta.get('updated')))
                              if meta.get('build') else ''))
    print_rows(rows)
    return code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
