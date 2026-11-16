r"""Give a checked-out Zone Kit material a fresh StateId, so the next cook recompiles its shaders.

Why: the cook takes a material's compiled shader map from the DDC, keyed by the material's StateId, and only an editor save
renews it. A constant patched straight into the .uasset (no editor) is therefore IGNORED by the cook: the old shaders ship
(proven: a patched material cooked byte-identical until its StateId was renewed; then the cook printed "Missing cached
shadermap ... compiling" and the shader chunk changed).

Run it after byte-patching and before cooking (sdk_code_patch.py renews the StateId on its own). Works on any asset whose
main export has a StateId (materials, material instances). Close the asset in the editor first.

    python sdk_renew_state_id.py "<kit>/Stalker2/Mods/<mod>/Content/.../M_Something.uasset" [--no-backup]

Writes <file>.bak first (the file as it was before this write) unless --no-backup. Needs uasset-dump (see s2paths.py).
"""
import json, os, shutil, struct, subprocess, sys, uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s2paths


def check_uncooked(asset):
    if not os.path.isfile(asset):
        raise SystemExit('no such file: %s' % asset)
    if not asset.lower().endswith('.uasset'):
        raise SystemExit('expected a .uasset file, got %s' % asset)
    if os.path.isfile(asset[:-len('.uasset')] + '.uexp'):
        raise SystemExit('%s has a .uexp beside it, so it is a cooked (split) package. Patch the uncooked .uasset in '
                         '<kit>/Stalker2/Mods/<mod>/Content/ instead.' % asset)


def dump(asset, tag='uasset_dump'):
    """uasset-dump the asset to JSON in the work folder and load it."""
    exe = s2paths.uasset_dump()
    if not os.path.isfile(exe):
        raise s2paths.S2PathError('uasset-dump not found at %s (build tools/uasset-dump, see s2paths.py)' % exe)
    out = os.path.join(s2paths.work_dir(), tag + '.json')
    if os.path.exists(out):
        os.remove(out)
    r = subprocess.run([exe, asset, out, 'VER_UE5_5'], capture_output=True, text=True, errors='replace')
    if r.returncode or not os.path.isfile(out):
        raise SystemExit('uasset-dump failed on %s (exit %s): %s' % (asset, r.returncode, (r.stdout + r.stderr).strip()[-800:]))
    with open(out, encoding='utf-8') as fh:
        return json.load(fh)


def main_export(d, asset):
    name = os.path.splitext(os.path.basename(asset))[0]
    exp = next((e for e in d.get('Exports') or [] if e.get('ObjectName') == name), None)
    if exp is None:
        raise SystemExit('no export named %s in %s' % (name, asset))
    return exp


def state_id(exp):
    """The StateId GUID string of an export, or SystemExit."""
    for p in exp.get('Data') or []:
        if isinstance(p, dict) and p.get('Name') == 'StateId':
            v = p.get('Value')
            if isinstance(v, str):
                return v
            for x in v if isinstance(v, list) else []:
                if isinstance(x, dict) and isinstance(x.get('Value'), str):
                    return x['Value']
    raise SystemExit('%s has no StateId' % exp.get('ObjectName'))


def guid_bytes(g):
    h = uuid.UUID(g.strip('{}')).hex
    return struct.pack('<4I', *(int(h[i:i + 8], 16) for i in (0, 8, 16, 24)))   # FGuid = four little-endian uint32


def bytes_guid(b):
    return '%08X-%04X-%04X-%04X-%04X%08X' % tuple(
        [struct.unpack_from('<I', b, 0)[0]] + [x for x in divmod(struct.unpack_from('<I', b, 4)[0], 0x10000)] +
        [x for x in divmod(struct.unpack_from('<I', b, 8)[0], 0x10000)] + [struct.unpack_from('<I', b, 12)[0]])


def renew(raw, d, asset):
    """Write a fresh random StateId into raw (a bytearray of the .uasset). Returns (old guid string, new 16 bytes)."""
    exp = main_export(d, asset)
    g = state_id(exp)
    pat = guid_bytes(g)
    off, size = exp['SerialOffset'], exp['SerialSize']
    hits = [off + i for i in range(size - 15) if raw[off + i:off + i + 16] == pat]
    if len(hits) != 1:
        raise SystemExit('StateId found %d times in the main export, refusing' % len(hits))
    new = uuid.uuid4().bytes
    raw[hits[0]:hits[0] + 16] = new
    return g, new


def backup(path, enabled=True):
    if not enabled:
        return None
    bak = path + '.bak'
    shutil.copyfile(path, bak)
    print('backup: %s' % bak)
    return bak


def same_guid(a, b):
    return a.strip('{}').replace('-', '').upper() == b.strip('{}').replace('-', '').upper()


def main():
    args = sys.argv[1:]
    if '-h' in args or '--help' in args:
        print(__doc__)
        return 0
    no_backup = '--no-backup' in args
    rest = [a for a in args if a != '--no-backup']
    if len(rest) != 1:
        print(__doc__)
        return 2
    asset = rest[0]
    check_uncooked(asset)
    d = dump(asset, 'renew_state_id')
    with open(asset, 'rb') as fh:
        raw = bytearray(fh.read())
    old, new = renew(raw, d, asset)
    backup(asset, not no_backup)
    with open(asset, 'wb') as fh:
        fh.write(bytes(raw))
    now = state_id(main_export(dump(asset, 'renew_state_id'), asset))
    if same_guid(now, old) or not same_guid(now, bytes_guid(new)):
        raise SystemExit('StateId read back as %s after the write; restore the backup and check the file' % now)
    print('StateId %s -> %s' % (old, now))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except s2paths.S2PathError as e:
        print(e, file=sys.stderr)
        sys.exit(2)
