"""Move paks out of the game's reach and back, to bisect a multi-pak mod. The game mounts every subfolder of Content/Paks,
so a parking folder has to sit outside it: this uses <game>/_parked_mods/ and remembers where each file came from.

    python pak_park.py status                       list parked files and every pak under ~mods
    python pak_park.py park <name part> [more ...]  move matching .pak/.utoc/.ucas/.sig files (case-insensitive part of the file name)
    python pak_park.py restore                      put every parked file back
    add --dry-run to print the moves without making them

The game locks its paks: close it first. Only files under ~mods are ever moved. Stdlib only.
"""
import json, os, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s2paths

EXT = ('.pak', '.utoc', '.ucas', '.sig')


def paths():
    mods = os.path.abspath(s2paths.mods_dir())
    park = os.path.join(os.path.abspath(s2paths.game_dir()), '_parked_mods')
    return mods, park, os.path.join(park, 'parked.json')


def load(index):
    try:
        with open(index, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save(index, data):
    os.makedirs(os.path.dirname(index), exist_ok=True)
    with open(index, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def mod_files(mods):
    for root, _, files in os.walk(mods):
        for f in sorted(files):
            if f.lower().endswith(EXT):
                yield os.path.join(root, f)


def main(argv):
    dry = '--dry-run' in argv
    args = [a for a in argv if a != '--dry-run']
    if not args or args[0] in ('-h', '--help') or args[0] not in ('status', 'park', 'restore') or (args[0] == 'park' and len(args) < 2):
        print(__doc__)
        return 0 if args and args[0] in ('-h', '--help') else 2
    mods, park, index = paths()
    data = load(index)
    if args[0] == 'status':
        print('parked (%d):' % len(data))
        for rel in sorted(data):
            print('   ', rel)
        print('under ~mods:')
        for p in mod_files(mods):
            print('   ', os.path.relpath(p, mods))
        return 0
    if args[0] == 'park':
        parts = [a.lower() for a in args[1:]]
        hits = [p for p in mod_files(mods) if any(x in os.path.basename(p).lower() for x in parts)]
        if not hits:
            print('nothing under ~mods matches %s' % ' '.join(args[1:]))
            return 1
        for p in hits:
            rel = os.path.relpath(p, mods)
            print('%s %s' % ('[dry] park' if dry else 'park', rel))
            if not dry:
                dst = os.path.join(park, 'files', rel)
                if os.path.exists(dst):
                    raise SystemExit('already parked: %s' % rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.move(p, dst)
                data[rel] = True
                save(index, data)
        return 0
    for rel in sorted(data):                         # restore
        src, dst = os.path.join(park, 'files', rel), os.path.join(mods, rel)
        if not os.path.abspath(dst).startswith(mods + os.sep):
            raise SystemExit('refusing a path outside ~mods: %s' % rel)
        if os.path.exists(dst):
            print('SKIPPED, already exists: %s' % rel)
            continue
        print('%s %s' % ('[dry] restore' if dry else 'restore', rel))
        if not dry:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            del data[rel]
            save(index, data)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except s2paths.S2PathError as e:
        print(e)
        sys.exit(2)
