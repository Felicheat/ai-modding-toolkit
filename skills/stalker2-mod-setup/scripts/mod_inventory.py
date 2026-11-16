"""Read-only inventory of one STALKER 2 mod: a folder (Vortex staging, a ~mods subfolder, a release folder, a Zone Kit mod
folder) or a .zip download.

    python mod_inventory.py <folder or .zip> [--out <file.md>] [--json]

Lists every file with size and sha256, groups paks into trios with their mount priority, lists what each .pak and .utoc
holds (repak list / retoc manifest, found through s2paths.py; skipped with a note when missing), and finds loose cfg, a
FOMOD installer and its options, readmes, Zone Kit source and script-loader files. Never changes the input: a zip is
unpacked into a temporary folder that is deleted afterwards.
"""
import hashlib, json, os, re, shutil, subprocess, sys, tempfile, zipfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s2paths

MAX_ZIP = 4 * 1024 ** 3          # refuse to unpack zips larger than this
PAK_EXT = ('.pak', '.utoc', '.ucas')


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def mount_order(stem):
    m = re.search(r'_(\d+)_P$', stem)
    if m:
        return 3 + 100 * (int(m.group(1)) + 1)
    return 103 if stem.endswith('_P') else 3


def tool_or_none(name):
    try:
        return s2paths.tool(name)
    except s2paths.S2PathError:
        return None


def pak_entries(path):
    exe = tool_or_none('repak')
    if not exe:
        return None, 'repak not found: contents not listed'
    r = subprocess.run([exe, 'list', path], capture_output=True, text=True)
    if r.returncode:
        return None, 'repak could not read it: ' + (r.stderr or r.stdout).strip()[:200]
    return [l.strip().replace('\\', '/') for l in r.stdout.splitlines() if l.strip()], ''


def utoc_entries(path):
    exe = tool_or_none('retoc')
    if not exe:
        return None, 'retoc not found: contents not listed'
    with tempfile.TemporaryDirectory() as tmp:          # retoc manifest writes pakstore.json into the current folder
        r = subprocess.run([exe, 'manifest', path], capture_output=True, text=True, cwd=tmp)
        store = os.path.join(tmp, 'pakstore.json')
        if r.returncode or not os.path.isfile(store):
            return None, 'retoc could not read it: ' + (r.stderr or r.stdout).strip()[:200]
        with open(store, encoding='utf-8') as f:
            data = json.load(f)
    out = []
    for e in data.get('oplog', {}).get('entries', []):
        for pd in e.get('packagedata', []):
            p = pd.get('filename', '').replace('\\', '/')
            while p.startswith('../'):
                p = p[3:]
            out.append(p)
    return sorted(set(out)), ''


def fomod_summary(xml_path):
    try:
        root = ET.parse(xml_path).getroot()
    except (ET.ParseError, OSError) as e:
        return {'error': str(e)[:200]}
    strip = lambda t: t.split('}', 1)[-1]
    name = next((el.text for el in root.iter() if strip(el.tag) == 'moduleName'), '')
    pages = []
    for step in (el for el in root.iter() if strip(el.tag) == 'installStep'):
        opts = [p.get('name', '') for p in step.iter() if strip(p.tag) == 'plugin']
        groups = [g.get('name', '') for g in step.iter() if strip(g.tag) == 'group']
        pages.append({'step': step.get('name', ''), 'groups': groups, 'options': opts})
    return {'module': name, 'pages': pages}


def classify(rel):
    low = rel.lower()
    if low.endswith(PAK_EXT):
        return 'pak'
    if low.endswith('fomod/moduleconfig.xml'):
        return 'fomod'
    if '/gamedata/' in '/' + low and (low.endswith('.cfg') or low.endswith('.cfg.bin')):
        return 'loose cfg'
    if low.endswith(('.uplugin', '.uasset', '.uexp', '.umap')):
        return 'zone kit source'
    if low.endswith(('.dll', '.lua', '.asi')) or '/scripts/' in '/' + low:
        return 'script loader content'
    if low.endswith(('.txt', '.md', '.rtf', '.pdf', '.html')):
        return 'readme or notes'
    if low.endswith(('.png', '.jpg', '.jpeg', '.webp')):
        return 'image'
    return 'other'


def inventory(root, label):
    files, trios = [], {}
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if d not in ('.git', '__pycache__', 'node_modules'))
        for fn in sorted(fns):
            p = os.path.join(dp, fn)
            if os.path.islink(p):
                continue
            rel = os.path.relpath(p, root).replace('\\', '/')
            kind = classify(rel)
            item = {'path': rel, 'kind': kind, 'bytes': os.path.getsize(p), 'sha256': sha(p)}
            if kind == 'pak':
                stem, ext = os.path.splitext(rel)
                trios.setdefault(stem, {}).setdefault('parts', []).append(ext)
                if ext in ('.pak', '.utoc'):
                    got, note = (pak_entries if ext == '.pak' else utoc_entries)(p)
                    trios[stem].setdefault('contents', {})[ext] = {'entries': got, 'note': note}
            if kind == 'fomod':
                item['fomod'] = fomod_summary(p)
            files.append(item)
    paks = []
    for stem, t in sorted(trios.items()):
        parts = sorted(t['parts'])
        contents = t.get('contents', {})
        entries = []
        for ext in ('.utoc', '.pak'):
            entries += (contents.get(ext, {}).get('entries') or [])
        cfg = [e for e in entries if '/GameData/' in '/' + e or e.startswith('GameData/') or '/DLCGameData/' in '/' + e]
        kind = 'IoStore trio (cooked assets)' if '.utoc' in parts else ('cfg pak' if cfg and len(cfg) == len(entries) else 'plain pak')
        paks.append({'name': stem, 'parts': parts, 'kind': kind, 'mount_order': mount_order(os.path.basename(stem)),
                     'entries': sorted(set(entries)), 'cfg_entries': len(cfg),
                     'notes': [c['note'] for c in contents.values() if c.get('note')]})
    return {'input': label, 'files': files, 'paks': paks}


def to_markdown(inv):
    lines = ['# Inventory of %s' % inv['input'], '']
    kinds = {}
    for f in inv['files']:
        kinds.setdefault(f['kind'], []).append(f)
    lines.append('%d files: %s' % (len(inv['files']), ', '.join('%d %s' % (len(v), k) for k, v in sorted(kinds.items()))))
    lines += ['', '## Paks (higher mount order wins)', '']
    if not inv['paks']:
        lines.append('none')
    for p in sorted(inv['paks'], key=lambda x: -x['mount_order']):
        lines.append('- **%s** (%s), parts %s, mount order %d, %d entries (%d cfg)' % (
            p['name'], p['kind'], ' '.join(p['parts']), p['mount_order'], len(p['entries']), p['cfg_entries']))
        for n in p['notes']:
            lines.append('  - note: %s' % n)
        for e in p['entries'][:60]:
            lines.append('  - `%s`' % e)
        if len(p['entries']) > 60:
            lines.append('  - ... %d more (see --json)' % (len(p['entries']) - 60))
    for f in inv['files']:
        if f.get('fomod'):
            fm = f['fomod']
            lines += ['', '## FOMOD installer: %s' % (fm.get('module') or f['path'])]
            if fm.get('error'):
                lines.append('unreadable: %s' % fm['error'])
            for pg in fm.get('pages', []):
                lines.append('- page "%s": groups %s; options %s' % (pg['step'], pg['groups'], pg['options']))
    lines += ['', '## Files', '', '| File | Kind | Bytes | sha256 |', '|---|---|---|---|']
    for f in inv['files']:
        lines.append('| `%s` | %s | %d | `%s` |' % (f['path'], f['kind'], f['bytes'], f['sha256'][:16]))
    return '\n'.join(lines) + '\n'


def main(argv):
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__)
        return 0 if argv else 2
    src = argv[0]
    out = argv[argv.index('--out') + 1] if '--out' in argv else None
    as_json = '--json' in argv
    tmp = None
    try:
        if os.path.isfile(src) and src.lower().endswith('.zip'):
            with zipfile.ZipFile(src) as z:
                total = sum(i.file_size for i in z.infolist())
                if total > MAX_ZIP:
                    print('zip unpacks to %d bytes; unpack it yourself and pass the folder' % total)
                    return 2
                tmp = tempfile.mkdtemp(prefix='mod_inventory_')
                for i in z.infolist():
                    name = i.filename.replace('\\', '/')
                    if name.startswith('/') or '..' in name.split('/') or ':' in name:
                        print('skipped an unsafe zip entry: %s' % name)
                        continue
                    z.extract(i, tmp)
            inv = inventory(tmp, os.path.basename(src))
        elif os.path.isdir(src):
            inv = inventory(src, os.path.basename(os.path.abspath(src)))
        else:
            print('not a folder or .zip: %s' % src)
            return 2
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    text = json.dumps(inv, indent=2) if as_json else to_markdown(inv)
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, 'w', encoding='utf-8') as f:
            f.write(text)
        print('wrote %s (%d files, %d paks)' % (out, len(inv['files']), len(inv['paks'])))
    else:
        sys.stdout.write(text)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
