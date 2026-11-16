"""Decode legacy (retoc to-legacy) UCurveFloat / UCurveLinearColor .uexp files, such as the game's light/Curves tree.

    python decode_curves.py <curve.uexp> [more .uexp ...]     prints {file name: [curve keys ...]} as JSON

Get the files with retoc (read-only on the game): retoc to-legacy --no-shaders -f Curves/<State> "<paks>" "<out folder>".
As a module: decode(path) -> list of curves, each a list of {t, v, at, atw, lt, ltw, mode} dicts; key_offsets(path) -> per
curve, the absolute byte offset of each key's Value float, for in-place edits; sample(keys, t) -> linear sample.

Layout: Unreal unversioned property serialization.
  - Top-level fragments: Unreal writes each as a little-endian uint16 (bits 0-6 skipped properties, bit 7 a zero mask
    follows, bit 8 last fragment, bits 9-15 values that follow). Read as big-endian words, as here: bit0 = last fragment,
    bits1-7 = values, bits8-14 = skipped (default) properties, bit15 = a zero mask follows the fragments.
    A CurveFloat has one FRichCurve value, a CurveLinearColor four (R,G,B,A);
    files written by other tools sometimes carry one extra trailing property, which is ignored.
  - Each FRichCurve value: its own fragments; if it declares one value, an int32 key count follows,
    then count x 27-byte keys (InterpMode, TangentMode, TangentWeightMode as bytes, then Time,
    Value, ArriveTangent, ArriveTangentWeight, LeaveTangent, LeaveTangentWeight as float32).
    A curve declaring zero values is empty (the game uses the default, 0).
  - File ends with the 4-byte package tag.
Read-only, no other tools needed.
"""
import struct, sys, json, os

KEY_SIZE = 27


def _frags(b, pos):
    frags = []
    while True:
        if pos + 2 > len(b):
            raise ValueError('ran out of data while reading property fragments at %d' % pos)
        f = int.from_bytes(b[pos:pos + 2], 'big')
        pos += 2
        frags.append(f)
        if f & 1:
            break
    values = sum((f >> 1) & 0x7f for f in frags)
    has_zero_mask = any((f >> 15) & 1 for f in frags)
    if has_zero_mask and values:
        pos += (values + 7) // 8
    return values, pos


def _parse(b):
    """Returns (curves, offsets). curves: list of key lists; offsets: list of lists of Value-float offsets."""
    n_props, pos = _frags(b, 0)
    curves, offsets = [], []
    end = len(b) - 4  # package tag
    for _ in range(min(n_props, 4)):
        if pos + 2 > end:
            break
        vals, pos = _frags(b, pos)
        if vals == 0:
            curves.append([])
            offsets.append([])
            continue
        if pos + 4 > len(b):
            raise ValueError('ran out of data before the key count at %d' % pos)
        count = struct.unpack_from('<i', b, pos)[0]
        pos += 4
        if count < 0 or pos + count * KEY_SIZE > end + 4:
            raise ValueError(f'bad key count {count} at {pos}')
        keys, offs = [], []
        for _k in range(count):
            im, tm, twm = b[pos], b[pos + 1], b[pos + 2]
            t, v, at, atw, lt, ltw = struct.unpack_from('<6f', b, pos + 3)
            keys.append({'t': round(t, 4), 'v': round(v, 6), 'at': at, 'atw': atw, 'lt': lt, 'ltw': ltw, 'mode': (im, tm, twm)})
            offs.append(pos + 3 + 4)  # Value float sits after 3 mode bytes and the Time float
            pos += KEY_SIZE
        if vals > 1:
            # Extra FRichCurve properties after Keys (DefaultValue etc.) have unknown size here; stop.
            curves.append(keys)
            offsets.append(offs)
            break
        curves.append(keys)
        offsets.append(offs)
    return curves, offsets


def decode(path):
    with open(path, 'rb') as fh:
        return _parse(fh.read())[0]


def key_offsets(path):
    with open(path, 'rb') as fh:
        return _parse(fh.read())[1]


def sample(keys, t):
    """Linear sample; vanilla lighting curves use linear interp with zero tangents."""
    if not keys:
        return None
    if t <= keys[0]['t']:
        return keys[0]['v']
    if t >= keys[-1]['t']:
        return keys[-1]['v']
    for a, c in zip(keys, keys[1:]):
        if a['t'] <= t <= c['t']:
            f = (t - a['t']) / (c['t'] - a['t']) if c['t'] != a['t'] else 0
            return a['v'] + f * (c['v'] - a['v'])


def main(argv):
    if not argv or '-h' in argv or '--help' in argv:
        print(__doc__)
        return 0 if argv else 2
    out, bad = {}, 0
    for p in argv:
        if not os.path.isfile(p):
            print('no such file: %s' % p, file=sys.stderr)
            bad += 1
            continue
        try:
            out[os.path.basename(p)] = decode(p)
        except ValueError as e:
            print('%s: %s (not a curve .uexp in the expected layout?)' % (p, e), file=sys.stderr)
            bad += 1
    print(json.dumps(out))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
