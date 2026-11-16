r"""IoStore package ids for STALKER 2 package names.

Package id = CityHash64 of the lower-cased UTF-16LE package name, printed little-endian the way `retoc list` shows chunk ids
(the export chunk of a package is <id>00000001). Check: /Game/Example/Textures/T_Example -> e94f154e93d4f75d.

An override container built by the Zone Kit keeps the MOD's mount in its package name (/<mod>/_Stalker_2/...), so its ids
are NOT the vanilla ids. To see what a container overrides, read its file entries with `retoc manifest` (or run
mods_conflicts.py) instead of searching for vanilla ids.

    python package_id.py /Game/Example/Materials/M_Example [more names ...]
    python package_id.py Stalker2/Content/Example/Materials/M_Example.uasset     (file paths are converted to /Game/...)

Needs: pip install cityhash
"""
import sys


def to_package_name(s):
    s = s.replace('\\', '/').strip()
    # Git Bash rewrites a leading-slash argument (/Game/...) into <drive>/Program Files/Git/Game/...; undo it
    if '/Program Files/Git/' in s:
        s = '/' + s.split('/Program Files/Git/', 1)[1]
    while s.startswith('../'):
        s = s[3:]
    for ext in ('.uasset', '.uexp', '.umap', '.ubulk'):
        if s.endswith(ext):
            s = s[:-len(ext)]
    if s.startswith('Stalker2/Content/'):
        s = '/Game/' + s[len('Stalker2/Content/'):]
    if '.' in s.rsplit('/', 1)[-1]:                 # /Game/Path/Asset.Asset -> /Game/Path/Asset
        s = s.rsplit('.', 1)[0]
    return s


def package_id(name):
    try:
        import cityhash
    except ImportError:
        raise SystemExit('package_id.py needs the cityhash module: pip install cityhash')
    return cityhash.CityHash64(name.lower().encode('utf-16-le')).to_bytes(8, 'little').hex()


def main(argv):
    if not argv or '-h' in argv or '--help' in argv:
        print(__doc__)
        return 0 if argv else 2
    for a in argv:
        n = to_package_name(a)
        print('%s  %s' % (package_id(n), n))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
