r"""Add the /Game/ package redirect that retoc's to-zen leaves out of a Zone Kit override container, so the override actually loads.

Why: a Zone Kit override is cooked under the MOD's mount (/<mod>/_Stalker_2/...), so its package id is the hash of that name,
not of the game's /Game/ name. The kit's own packer (UnrealPak) writes a PackageRedirects entry into the container header:
/Game/<path> (source id) -> /<mod>/<path> (target id), plus the /Game/ name in the header's name map. `retoc to-zen` writes no
redirect, so the container mounts, the log looks fine, and the game still loads its own asset. Official example containers
show the redirect layout; `--selftest` rebuilds an official header byte for byte with this writer.

Container header v4 (NoExportInfo) as written here:
  'nCoI' | u32 version | u64 container id | i32 n + n*u64 package ids | i32 bytes + store entries |
  i32 n + optional segment ids | i32 bytes + optional store entries |
  name batch: i32 names; only when names > 0: i32 string bytes, u64 hash algorithm id (0xC1640000), u64 CityHash64(lowercase)
              per name, u16 big-endian length per name, string bytes |
  i32 localized packages | i32 n + n * (u64 source id, u64 target id, u32 mapped name index | 0x40000000 container, u32 number) |
  trailing empty fields (one i32 0, three once a package imports another package; leaving them out makes the game log
  "Invalid container header" and drop the redirects)
Store entry per package: {i32 ImportedPackages num, u32 offset-from-field}, {i32 ShaderMapHashes num, u32 offset}, data.
ShaderMapHashes are also filled (from the cooked ShaderArchive) so the loader preloads the mod's shader map.

    python zen_add_redirect.py <in.utoc> <out dir> [--shadermap <cooked .ushaderbytecode>] [--no-backup]
        rewrites every package's header entry: redirect from /Game/<path> for each package whose manifest file path is
        ../../../Stalker2/Content/<path>.uasset; writes <out dir>/<same name>.utoc/.ucas/.pak. The result is packed and
        verified in a temp folder first. When <out dir> is the input's own folder the input is replaced, after copies to
        <name>.utoc.bak and <name>.ucas.bak (skip them with --no-backup).
    python zen_add_redirect.py --selftest <official override .utoc>        read-only

Needs retoc (see s2paths.py) and the cityhash module (pip install cityhash).
"""
import contextlib, json, os, shutil, struct, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s2paths

MAGIC = 0x496F436E
HASH_ALGO = 0xC1640000
CONTENT = '../../../Stalker2/Content/'
_TOOLS = {}


def need(ok, msg):
    if not ok:
        raise SystemExit(msg)


def _cityhash():
    try:
        import cityhash
    except ImportError:
        raise SystemExit('zen_add_redirect.py needs the cityhash module: pip install cityhash')
    return cityhash


def retoc():
    if 'retoc' not in _TOOLS:
        _TOOLS['retoc'] = s2paths.tool('retoc')
    return _TOOLS['retoc']


@contextlib.contextmanager
def tempdir():
    d = tempfile.mkdtemp(prefix='zen_redirect_')
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def parse(b):
    p = 0

    def u(fmt):
        nonlocal p
        v = struct.unpack_from(fmt, b, p)
        p += struct.calcsize(fmt)
        return v if len(v) > 1 else v[0]

    h = {}
    try:
        need(u('<I') == MAGIC, 'not an IoStore container header (bad magic)')
        h['version'] = u('<I')
        h['container'] = u('<Q')
        n = u('<i')
        h['ids'] = [u('<Q') for _ in range(n)]
        n = u('<i')
        h['store'] = b[p:p + n]
        p += n
        n = u('<i')
        h['opt_ids'] = [u('<Q') for _ in range(n)]
        n = u('<i')
        h['opt_store'] = b[p:p + n]
        p += n
        nn = u('<i')
        names = []
        if nn:
            u('<i')                                                    # string bytes
            need(u('<Q') == HASH_ALGO, 'unexpected name hash algorithm in the container header')
            for _ in range(nn):
                u('<Q')
            lens = [struct.unpack_from('>H', b, p + 2 * i)[0] for i in range(nn)]
            p += 2 * nn
            for L in lens:
                names.append(b[p:p + L].decode('ascii'))
                p += L
        h['names'] = names
        h['localized'] = u('<i')
        need(h['localized'] == 0, 'the container header lists localized packages: not supported')
        n = u('<i')
        h['redirects'] = [u('<QQII') for _ in range(n)]
    except (struct.error, UnicodeDecodeError):
        raise SystemExit('the container header is truncated or not the v4 layout this script knows')
    h['tail'] = b[p:]
    # trailing empty fields after the redirects: one int32 in most containers, three once a package imports another package.
    # build() writes them back verbatim, so only zeros are safe.
    need(h['tail'] and not any(h['tail']), 'expected empty trailing fields after the redirects, got %r' % h['tail'][:32])
    return h


def build(h):
    cityhash = _cityhash()
    o = bytearray()
    o += struct.pack('<IIQ', MAGIC, h['version'], h['container'])
    o += struct.pack('<i', len(h['ids'])) + b''.join(struct.pack('<Q', i) for i in h['ids'])
    o += struct.pack('<i', len(h['store'])) + h['store']
    o += struct.pack('<i', len(h['opt_ids'])) + b''.join(struct.pack('<Q', i) for i in h['opt_ids'])
    o += struct.pack('<i', len(h['opt_store'])) + h['opt_store']
    names = h['names']
    o += struct.pack('<i', len(names))
    if names:
        o += struct.pack('<iQ', sum(len(n) for n in names), HASH_ALGO)
        o += b''.join(struct.pack('<Q', cityhash.CityHash64(n.lower().encode('ascii'))) for n in names)
        o += b''.join(struct.pack('>H', len(n)) for n in names)
        o += b''.join(n.encode('ascii') for n in names)
    o += struct.pack('<i', h['localized'])
    o += struct.pack('<i', len(h['redirects'])) + b''.join(struct.pack('<QQII', *r) for r in h['redirects'])
    o += h['tail']
    return bytes(o)


def unpack(utoc, d):
    """retoc unpack-raw into d (must not exist yet). Returns (header chunk path, manifest dict)."""
    r = subprocess.run([retoc(), 'unpack-raw', os.path.abspath(utoc), d], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit('retoc unpack-raw failed: ' + r.stdout + r.stderr)
    chunks = os.path.join(d, 'chunks')
    hdr = [f for f in os.listdir(chunks) if f.endswith('06')] if os.path.isdir(chunks) else []
    need(len(hdr) == 1, 'expected one container header chunk in %s, found %d' % (utoc, len(hdr)))
    man = os.path.join(d, 'manifest.json')
    need(os.path.isfile(man), 'retoc unpack-raw wrote no manifest.json')
    with open(man, encoding='utf-8') as fh:
        return os.path.join(chunks, hdr[0]), json.load(fh)


def package_id(name):
    return _cityhash().CityHash64(name.lower().encode('utf-16-le'))


def selftest(utoc):
    need(os.path.isfile(utoc), 'no such file: %s' % utoc)
    with tempdir() as t:
        path, _ = unpack(utoc, os.path.join(t, 'raw'))
        with open(path, 'rb') as fh:
            b = fh.read()
    h = parse(b)
    same = build(h) == b
    print('header', len(b), 'bytes | names', h['names'], '| redirects', [(hex(s), hex(t)) for s, t, _, _ in h['redirects']],
          '| rebuilt identical:', same)
    for (s, t, _, _), n in zip(h['redirects'], h['names']):
        print('  source id == CityHash64(utf16 lower /Game name):', s == package_id(n))
    return 0 if same else 1


def store_with_shadermap(store, index, shader_hash):
    """Store entries = one 16-byte view pair per package ({ImportedPackages num, offset}, {ShaderMapHashes num, offset}), then
    the data they point at; offsets count from each field's own position. Append the hash and point package `index` at it
    (existing offsets stay valid because nothing moves)."""
    field = index * 16 + 8
    sm_n = struct.unpack_from('<i', store, field)[0]
    if sm_n:
        return store
    return store[:field] + struct.pack('<iI', 1, len(store) - field) + store[field + 8:] + shader_hash


def shader_hashes(shadermap):
    """(single hash or None, {asset path: hash}) from a cooked ShaderArchive-*.ushaderbytecode and its ShaderAssetInfo json."""
    need(os.path.isfile(shadermap), 'no such shader archive: %s' % shadermap)
    with open(shadermap, 'rb') as fh:
        sb = fh.read()
    need(len(sb) >= 8 and struct.unpack_from('<I', sb, 0)[0] == 2, 'unexpected shader archive version in %s' % shadermap)
    count = struct.unpack_from('<i', sb, 4)[0]
    need(0 <= count and len(sb) >= 8 + 20 * count, 'shader archive %s is truncated' % shadermap)
    hashes = [sb[8 + 20 * i:28 + 20 * i] for i in range(count)]
    # which asset owns which shader map: the cook writes ShaderAssetInfo-*.assetinfo.json beside the archive
    folder = os.path.dirname(os.path.abspath(shadermap))
    infos = [f for f in os.listdir(folder) if f.startswith('ShaderAssetInfo-') and f.endswith('.assetinfo.json')]
    by_asset = {}
    if infos:
        with open(os.path.join(folder, infos[0]), encoding='utf-8') as fh:
            info = json.load(fh)
        for entry in info.get('ShaderCodeToAssets') or []:
            h20 = bytes.fromhex(entry['ShaderMapHash'])
            need(h20 in hashes, 'the ShaderAssetInfo json lists a shader map hash that is not in the archive')
            for asset in entry.get('Assets') or []:
                by_asset[asset] = h20
        return None, by_asset
    if count == 1:
        return hashes[0], by_asset
    raise SystemExit('%d shader maps but no ShaderAssetInfo json to assign them' % count)


def add_redirect(utoc, out_dir=None, shadermap=None, backup=True):
    """Rewrite an override container with a /Game redirect per package. out_dir None (or the input's folder) = replace the
    input .utoc/.ucas, after .bak copies unless backup is False. shadermap: the cooked ShaderArchive-*.ushaderbytecode (its
    shader map hashes go into the store entries). Packs and verifies in a temp folder first. Returns the output .utoc path."""
    need(utoc.lower().endswith('.utoc') and os.path.isfile(utoc), 'no such .utoc: %s' % utoc)
    src_dir = os.path.dirname(os.path.abspath(utoc))
    out_dir = os.path.abspath(out_dir) if out_dir else src_dir
    in_place = os.path.normcase(out_dir) == os.path.normcase(src_dir)
    base = os.path.splitext(os.path.basename(utoc))[0]
    src = os.path.join(src_dir, base)
    dst = os.path.join(out_dir, base)
    shader_hash, hash_by_asset = shader_hashes(shadermap) if shadermap else (None, {})
    _cityhash()                                                        # fail early, before any work
    with tempdir() as t:
        work = os.path.join(t, 'raw')
        path, man = unpack(utoc, work)
        with open(path, 'rb') as fh:
            h = parse(fh.read())
        if h['redirects']:
            raise SystemExit('container already has redirects: %s' % h['redirects'])
        # one redirect per package, like the kit's packer writes (official example containers: every package, new ones included)
        h['names'], h['redirects'], materials = [], [], []
        for k, pid in enumerate(h['ids']):
            cid = '%016x' % int.from_bytes(struct.pack('<Q', pid), 'big')
            files = [p for c, p in (man.get('chunk_paths') or {}).items() if c.startswith(cid) and p.endswith('.uasset')]
            need(len(files) == 1, 'package %s: expected one .uasset path in the manifest, found %r' % (cid, files))
            need(files[0].startswith(CONTENT), 'package %s is not under Stalker2/Content/: %s' % (cid, files[0]))
            rel = files[0][len(CONTENT):]
            name = '/Game/' + rel[:-len('.uasset')]
            h['names'].append(name)
            h['redirects'].append((package_id(name), pid, len(h['names']) - 1 | 0x40000000, 0))
            if os.path.basename(rel).startswith(('M_', 'MI_')):
                materials.append(k)
            # an asset listed as '/<mod>/<rel without .uasset>' in the assetinfo gets its own shader map hash
            for asset, h20 in hash_by_asset.items():
                if asset.endswith('/' + rel[:-len('.uasset')]):
                    h['store'] = store_with_shadermap(h['store'], k, h20)
        game_name = ', '.join(h['names'])
        if hash_by_asset:
            assigned = sum(1 for k in range(len(h['ids'])) if struct.unpack_from('<i', h['store'], k * 16 + 8)[0])
            if assigned != len(hash_by_asset):
                raise SystemExit('assigned %d shader maps, the assetinfo lists %d assets' % (assigned, len(hash_by_asset)))
        if shader_hash:
            if len(materials) != 1:
                raise SystemExit('shader map hash given but %d material packages found: %s' % (len(materials), h['names']))
            h['store'] = store_with_shadermap(h['store'], materials[0], shader_hash)
        with open(path, 'wb') as fh:
            fh.write(build(h))
        stage = os.path.join(t, 'out')
        os.makedirs(stage)
        staged = os.path.join(stage, base + '.utoc')
        r = subprocess.run([retoc(), 'pack-raw', work, staged], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit('retoc pack-raw failed: ' + r.stdout + r.stderr)
        # prove the rewrite before anything is written to out_dir: the header must parse back with exactly these
        # redirects, and retoc must verify the container
        chk, _ = unpack(staged, os.path.join(t, 'check'))
        with open(chk, 'rb') as fh:
            hb = parse(fh.read())
        need(hb['redirects'] == h['redirects'] and hb['names'] == h['names'] and hb['store'] == h['store'],
             'the redirect did not survive the repack')
        v = subprocess.run([retoc(), 'verify', staged], capture_output=True, text=True)
        if v.returncode:
            raise SystemExit('retoc verify failed: ' + v.stdout + v.stderr)
        os.makedirs(out_dir, exist_ok=True)
        if in_place:
            if backup:
                for ext in ('.utoc', '.ucas'):
                    if os.path.isfile(src + ext):
                        shutil.copyfile(src + ext, src + ext + '.bak')
                print('  backup: %s.utoc.bak / .ucas.bak' % src)
        else:
            for ext in ('.utoc', '.ucas', '.pak'):
                if os.path.exists(dst + ext):
                    os.remove(dst + ext)
        for ext in ('.utoc', '.ucas', '.pak'):
            if os.path.isfile(os.path.join(stage, base + ext)):
                shutil.copyfile(os.path.join(stage, base + ext), dst + ext)
        if not in_place and os.path.isfile(src + '.pak') and not os.path.exists(dst + '.pak'):
            shutil.copyfile(src + '.pak', dst + '.pak')
    print('  redirect %s -> mod packages%s | verified' % (game_name, ', shader map hashes added' if (shader_hash or hash_by_asset) else ''))
    return dst + '.utoc'


def main():
    a = sys.argv[1:]
    if not a or '-h' in a or '--help' in a:
        print(__doc__)
        return 0 if a else 2
    if a[0] == '--selftest':
        need(len(a) >= 2, '--selftest needs an official override .utoc')
        return selftest(a[1])
    shadermap = None
    skip = set()
    if '--shadermap' in a:
        i = a.index('--shadermap')
        need(i + 1 < len(a), '--shadermap needs a .ushaderbytecode file')
        shadermap = a[i + 1]
        skip = {i, i + 1}
    pos = [x for i, x in enumerate(a) if i not in skip and x != '--no-backup']
    if len(pos) != 2 or any(x.startswith('--') for x in pos):
        print(__doc__)
        return 2
    add_redirect(pos[0], pos[1], shadermap, backup='--no-backup' not in a)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except s2paths.S2PathError as e:
        print(e, file=sys.stderr)
        sys.exit(2)
