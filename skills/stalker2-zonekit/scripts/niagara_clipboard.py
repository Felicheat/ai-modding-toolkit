r"""Decode Niagara stack modules copied from the Zone Kit editor (select a module in an emitter's stack, Ctrl+C, paste to text).

The clipboard is T3D text: a first pass of nested `Begin Object Class=...` shells, then a second pass that fills each object (same
ExportPath) with InputName, InputType, ValueMode (Local / Linked / Dynamic), Linked parameter names and Local(n) raw bytes.
Local bytes are the value's little-endian memory: NiagaraFloat 4 bytes, Vector2f 8, Vector3f 12, Vector4f / LinearColor /
Quat4f 16, NiagaraInt32 and enums (UnderlyingType=3) int32, NiagaraBool 0 or 0xFFFFFFFF. Several modules can be pasted one after
another into one file.

    python niagara_clipboard.py <pasted.txt>

Prints each module as [FunctionName] with its inputs: a local value, "-> <linked parameter>" or a dynamic input tree.
Read-only, no other tools needed.
"""
import os, re, struct, sys

TYPE_SIZES = {'NiagaraFloat': ('f', 1), 'Vector2f': ('f', 2), 'Vector3f': ('f', 3), 'Vector': ('d', 3), 'Vector4f': ('f', 4),
              'LinearColor': ('f', 4), 'Quat4f': ('f', 4), 'NiagaraInt32': ('i', 1), 'NiagaraBool': ('i', 1),
              'NiagaraPosition': ('f', 3), 'NiagaraMatrix': ('f', 16), 'NiagaraID': ('i', 2)}


def parse(text):
    objs, stack = {}, []
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r'Begin Object (?:Class=\S+ )?Name="([^"]+)" ExportPath="[^\']*\'([^\']+)\'"', s)
        if m:
            path = m.group(2)
            objs.setdefault(path, {'name': m.group(1), 'local': {}})
            stack.append(path)
            continue
        if s == 'End Object':
            if stack:
                stack.pop()
            continue
        if not stack:
            continue
        o = objs[stack[-1]]
        m = re.match(r'Local\((\d+)\)=(\d+)', s)
        if m:
            o['local'][int(m.group(1))] = int(m.group(2))
            continue
        m = re.match(r'(Inputs|ChildrenInputs)\((\d+)\)="[^\']*\'([^\']+)\'"', s)
        if m:
            o.setdefault(m.group(1), []).append(stack[-1] + '.' + m.group(3))
            continue
        m = re.match(r'(Dynamic)="[^\']*\'([^\']+)\'"', s)
        if m:
            o['Dynamic'] = stack[-1] + '.' + m.group(2)
            continue
        m = re.match(r'(\w+)=(.*)', s)
        if m:
            o[m.group(1)] = m.group(2).strip('"')
    return objs


def value(o):
    t = o.get('InputType', '')
    raw = bytes(o['local'][i] for i in sorted(o['local']))
    if 'UnderlyingType=3' in t:
        enum = re.search(r"Enums/(?:[^/]+/)*(\w+)\.", t)
        if len(raw) < 4:
            return 'enum %s = (no value bytes)' % (enum.group(1) if enum else '?')
        return 'enum %s = %d' % (enum.group(1) if enum else '?', struct.unpack_from('<i', raw)[0])
    found = re.findall(r"\.(\w+)'", t)          # the last one is the value type (the first is ScriptStruct)
    typ = found[-1] if found else '?'
    if typ in TYPE_SIZES and raw:
        code, n = TYPE_SIZES[typ]
        size = struct.calcsize(code)
        vals = struct.unpack_from('<%d%s' % (min(n, len(raw) // size), code), raw)
        if typ == 'NiagaraBool':
            return 'true' if vals[0] else 'false'
        vals = [round(v, 4) if isinstance(v, float) else v for v in vals]
        return vals[0] if len(vals) == 1 else tuple(vals)
    return raw.hex() if raw else '(none)'


def show(objs, path, depth):
    pad = '  ' * depth
    o = objs.get(path)
    if o is None:
        print('%s(%s: not in the paste)' % (pad, path.rsplit('.', 1)[-1]))
        return
    if 'FunctionName' in o:
        print('%s[%s]  %s' % (pad, o['FunctionName'], o.get('Script', '')))
        for p in o.get('Inputs', []):
            show(objs, p, depth + 1)
        return
    mode = o.get('ValueMode', 'Local')
    if mode == 'Linked':
        v = '-> ' + o.get('Linked', '?')
    elif mode == 'Dynamic':
        v = 'dynamic:'
    else:
        v = value(o)
    print('%s%s = %s' % (pad, o.get('InputName', o['name']), v))
    if mode == 'Dynamic' and o.get('Dynamic') in objs:
        show(objs, o['Dynamic'], depth + 1)
    for p in o.get('ChildrenInputs', []):
        show(objs, p, depth + 1)


def main():
    args = sys.argv[1:]
    if not args or '-h' in args or '--help' in args:
        print(__doc__)
        return 0 if args else 2
    if not os.path.isfile(args[0]):
        raise SystemExit('no such file: %s' % args[0])
    with open(args[0], 'rb') as fh:
        raw = fh.read()
    text = raw.decode('utf-16' if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8-sig', errors='replace')
    for chunk in re.split(r'(?=Begin Object Class=/Script/NiagaraEditor\.NiagaraClipboardContent )', text):
        if not chunk.strip():
            continue
        objs = parse(chunk)
        tops = [p for p, o in objs.items() if 'FunctionName' in o and re.search(r':NiagaraClipboardFunction_\d+$', p)]
        for p in tops:
            show(objs, p, 0)
        print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
