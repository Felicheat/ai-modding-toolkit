"""List the sound events a Niagara system references, by scanning its files as text. Use it when an effect went silent.

    python niagara_sound_refs.py <file or folder> [more ...]

A folder is searched for NS_*.uasset / NS_*.uexp and raw chunks. A working cook lists the event path as text ("events: NONE"
means no event reached that file). Compare with a control from the same kit version. Read-only, stdlib only.
"""
import os, re, sys

PAT = re.compile(rb'[A-Za-z0-9_/.:\-]{4,160}')
KEEP = re.compile(r'SFX_|AkAudioEvent|WwiseEvent|EventToPost|NiagaraDataInterfaceWwise|NiagaraDataInterfaceAk|PostWwise')


def main(argv):
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__)
        return 0 if argv else 2
    files = []
    for p in argv:
        if os.path.isdir(p):
            for r, _, fs in os.walk(p):
                files += [os.path.join(r, f) for f in fs if f.startswith('NS_') and f.endswith(('.uasset', '.uexp'))]
        elif os.path.isfile(p):
            files.append(p)
        else:
            print('not found: %s' % p)
            return 2
    for f in sorted(files):
        with open(f, 'rb') as fh:
            b = fh.read()
        found = sorted({m.group().decode('ascii') for m in PAT.finditer(b) if KEEP.search(m.group().decode('ascii'))})
        ev = [x for x in found if 'SFX_' in x or 'Play_' in x]
        print('== %s (%d bytes)' % (f, len(b)))
        print('   events: %s' % (ev[:30] if ev else 'NONE'))
        print('   other : %s' % [x for x in found if x not in ev][:14])
    print('%d file(s)' % len(files))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
