r"""In-game names <-> localization keys <-> record SIDs, from the game's Game.locres.

The names players see exist only in the localization table, never in the cfg. Item names follow the key pattern
sid_items_<LocalizationSID>_name / _description (LocalizationSID defaults to the item SID; variants such as guard guns
borrow their base gun's key), so a name gives the item SID, and the item gives the rest (GeneralWeaponSetup,
PlayerWeaponAttributes, NPCWeaponAttributes; see the stalker2-gamedata skill).

The table is read from the installed game (<paks>/pakchunk0-Windows.pak, current game version; Cost of Hope strings live
in the same file) with repak and cached in the work folder (see s2paths.py), keyed by the pak's size and date. --sdk reads
the Zone Kit's copy instead (its game version can lag the game's). Read-only.

    python locres_lookup.py sharpshooter                 regex over names and keys (case-insensitive)
    python locres_lookup.py --key Gun_Sharpshooter_AR    keys only
    python locres_lookup.py --name "^Kharod$"            names only
    python locres_lookup.py --items "^AR416$"            item names only, printed as item SIDs
    python locres_lookup.py --lang uk ...                another language folder (default en)
    python locres_lookup.py --locres <file> ...          a .locres already on disk (no repak needed)
"""
import argparse, os, re, struct, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s2paths

ITEM_KEY = re.compile(r'^sid_items_(.+)_(name|description)$')


def fetch(pak, lang):
    if not os.path.isfile(pak):
        raise SystemExit('no such pak: %s' % pak)
    inner = 'Stalker2/Content/Localization/Game/%s/Game.locres' % lang
    st = os.stat(pak)
    tag = '%s_%s_%d_%d.locres' % (os.path.splitext(os.path.basename(pak))[0], lang, st.st_size, int(st.st_mtime))
    out = os.path.join(s2paths.work_dir(), tag)
    if not os.path.isfile(out):
        r = subprocess.run([s2paths.tool('repak'), 'get', pak, inner], capture_output=True)
        if r.returncode or not r.stdout:
            raise SystemExit('repak get failed for %s in %s: %s' % (inner, pak, r.stderr.decode(errors='replace').strip()))
        with open(out, 'wb') as f:
            f.write(r.stdout)
    return out


def parse(path):
    """Unreal .locres, versions 1-3: {(namespace, key): string}."""
    with open(path, 'rb') as fh:
        d = fh.read()
    pos = 0

    def take(fmt):
        nonlocal pos
        v = struct.unpack_from(fmt, d, pos)[0]
        pos += struct.calcsize(fmt)
        return v

    def fstr():
        nonlocal pos
        n = take('<i')
        if n < 0:
            s = d[pos:pos - 2 * n].decode('utf-16le', 'replace')
            pos += -2 * n
        else:
            s = d[pos:pos + n].decode('latin1')
            pos += n
        return s.rstrip('\x00')

    if len(d) < 17:
        raise SystemExit('%s is too short to be a .locres file' % path)
    pos = 16                                   # magic GUID
    ver = d[pos]
    pos += 1
    if ver < 1 or ver > 3:
        raise SystemExit('unsupported locres version %d' % ver)
    try:
        strings_at = take('<q')
        if ver >= 3:
            take('<i')                         # entry count
        header_end = pos
        pos = strings_at
        strings = []
        for _ in range(take('<i')):
            strings.append(fstr())
            if ver >= 3:
                take('<i')                     # ref count
        pos = header_end
        table = {}
        for _ in range(take('<i')):
            if ver >= 2:
                take('<I')                     # namespace hash
            ns = fstr()
            for _ in range(take('<i')):
                if ver >= 2:
                    take('<I')                 # key hash
                key = fstr()
                take('<I')                     # source string hash
                table[(ns, key)] = strings[take('<i')]
    except (struct.error, IndexError):
        raise SystemExit('%s: damaged or unknown .locres layout' % path)
    return table


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pattern', help='regex, case-insensitive')
    scope = ap.add_mutually_exclusive_group()
    scope.add_argument('--key', action='store_true', help='match keys only')
    scope.add_argument('--name', action='store_true', help='match names (strings) only')
    scope.add_argument('--items', action='store_true', help='item names only, print the LocalizationSID (normally the item SID)')
    ap.add_argument('--lang', default='en')
    ap.add_argument('--sdk', action='store_true', help="read the Zone Kit's copy instead of the game's")
    ap.add_argument('--locres', help='read this .locres file')
    a = ap.parse_args()
    if not re.match(r'^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$', a.lang):
        ap.error('--lang must be a language folder name such as en, uk or pt-BR')
    try:
        pat = re.compile(a.pattern, re.I)
    except re.error as e:
        ap.error('bad regex: %s' % e)

    if a.locres:
        path = a.locres
    else:
        pak = s2paths.kit_editor_pak() if a.sdk else os.path.join(s2paths.paks_dir(), 'pakchunk0-Windows.pak')
        path = fetch(pak, a.lang)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='replace')       # a console code page cannot show every language
    hits = 0
    for (ns, key), text in sorted(parse(path).items(), key=lambda kv: kv[0][1]):
        item = ITEM_KEY.match(key)
        if a.items:
            if not item or item.group(2) != 'name' or not pat.search(text):
                continue
            print('%-40s %s' % (item.group(1), text))
        else:
            if a.key:
                ok = pat.search(key)
            elif a.name:
                ok = pat.search(text)
            else:
                ok = pat.search(key) or pat.search(text)
            if not ok:
                continue
            one_line = text.replace('\r', '').replace('\n', ' | ')
            print('%s  [%s]  %s' % (key, ns, one_line[:300]))
        hits += 1
    print('-- %d match(es) in %s' % (hits, path), file=sys.stderr)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except s2paths.S2PathError as e:
        print(e, file=sys.stderr)
        sys.exit(2)
