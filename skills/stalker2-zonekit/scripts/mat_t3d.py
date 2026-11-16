r"""Read a material graph that was copied out of the Unreal material editor as text (select all nodes, Ctrl+C, paste in a
text editor, save) and print the REAL wiring as formulas. This is ground truth: every input of every expression names the
expression that feeds it. Prefer it over mat_uasset_tree.py, which only guesses links from the saved .uasset bytes.

  python scripts/mat_t3d.py <graph.txt>                     summary: root inputs, parameters, textures, custom nodes
  python scripts/mat_t3d.py <graph.txt> root [depth]        formula behind every connected root pin
  python scripts/mat_t3d.py <graph.txt> expr <Name> [depth] formula behind one expression (e.g. MaterialExpressionCustom_4)
  python scripts/mat_t3d.py <graph.txt> uses <text>         who consumes expressions whose label contains <text>

Shared sub-expressions are printed once as  @N = ...  and referenced by @N after that, so long chains stay readable.
Read-only, no other tools needed.
"""
import os, re, sys

INPUT_RE = re.compile(r'(?:InputName="(?P<iname>[^"]*)",)?(?:Input=\()?Expression="[^\']*\'(?:(?P<node>MaterialGraphNode[\w]*)\.)?(?P<expr>\w+)\'"(?P<rest>[^)]*)')


class Expr:
    def __init__(self, name, cls):
        self.name, self.cls, self.props, self.inputs = name, cls, {}, []   # inputs: (label, exprName, outputIndex, mask)


def parse(path):
    raw = open(path, 'rb').read()
    text = raw.decode('utf-16' if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8', errors='replace')
    blocks = re.split(r'(?m)^(?=Begin Object Class=/Script/UnrealEd\.MaterialGraphNode)', text)
    exprs, nodes = {}, {}
    for b in blocks:
        m = re.match(r'Begin Object Class=/Script/UnrealEd\.(\w+) Name="(\w+)"', b)
        if not m:
            continue
        node = {'cls': m.group(1), 'name': m.group(2), 'pins': [], 'expr': None}
        nodes[node['name']] = node
        d = re.search(r'Begin Object Class=/Script/Engine\.(\w+) Name="(\w+)"', b)
        if d:
            e = Expr(d.group(2), d.group(1).replace('MaterialExpression', ''))
            body = re.search(r'Begin Object Name="%s"[^\n]*\n(.*?)\n   End Object' % re.escape(e.name), b, re.S)
            for line in (body.group(1).splitlines() if body else []):
                line = line.strip()
                if '=' not in line:
                    continue
                key, val = line.split('=', 1)
                if 'Expression="' in val:
                    for im in INPUT_RE.finditer(val):
                        label = im.group('iname') or key
                        rest = im.group('rest')
                        oi = re.search(r'OutputIndex=(\d+)', rest)
                        mask = ''.join(c for c in 'RGBA' if re.search(r'Mask%s=1' % c, rest)) if 'Mask=1' in rest else ''
                        e.inputs.append((label, im.group('expr'), int(oi.group(1)) if oi else 0, mask))
                else:
                    e.props[key] = val.strip('"')
            exprs[e.name] = e
            node['expr'] = e.name
        for pm in re.finditer(r'CustomProperties Pin \((.*)\)\s*$', b, re.M):
            p = pm.group(1)
            pid = re.search(r'PinId=(\w+)', p)
            if not pid:
                continue
            pid = pid.group(1)
            pname = re.search(r'PinName="([^"]*)"', p)
            links = re.findall(r'(MaterialGraphNode\w*) (\w{32})', (re.search(r'LinkedTo=\(([^)]*)\)', p) or [None, ''])[1])
            node['pins'].append({'id': pid, 'name': pname.group(1) if pname else '', 'out': 'EGPD_Output' in p, 'links': links})
    return exprs, nodes


def label(e):
    p = e.props
    if e.cls in ('ScalarParameter', 'VectorParameter', 'StaticSwitchParameter', 'StaticBoolParameter'):
        return "%s[%s]" % (p.get('ParameterName', e.name), p.get('DefaultValue', '0'))
    if e.cls == 'CollectionParameter':
        return "MPC.%s" % p.get('ParameterName', '?')
    if e.cls == 'Constant':
        return p.get('R', '0')
    if e.cls in ('Constant2Vector', 'Constant3Vector', 'Constant4Vector'):
        return "const(%s)" % p.get('Constant', ','.join(p.get(k, '0') for k in 'RGBA' if k in p))
    if e.cls in ('TextureSample', 'TextureSampleParameter2D', 'TextureObjectParameter', 'TextureSampleParameterVolume', 'TextureObject'):
        tex = re.search(r"([\w]+)'\"?$", p.get('Texture', '')) or re.search(r'\.(\w+)', p.get('Texture', ''))
        return "Tex:%s%s" % (p.get('ParameterName', '') and p['ParameterName'] + '=' or '', tex.group(1) if tex else '?')
    if e.cls == 'Custom':
        return "Custom:%s" % p.get('Description', e.name)
    if e.cls == 'MaterialFunctionCall':
        f = re.search(r"\.([\w-]+)'", p.get('MaterialFunction', ''))
        return "Fn:%s" % (f.group(1) if f else '?')
    if e.cls == 'NamedRerouteUsage':
        return "NamedReroute"
    return e.cls


LEAF = ('ScalarParameter', 'VectorParameter', 'CollectionParameter', 'Constant', 'Constant2Vector', 'Constant3Vector', 'Constant4Vector',
        'WorldPosition', 'Time', 'CameraPositionWS', 'TextureObject', 'TextureObjectParameter', 'VolumetricAdvancedMaterialInput',
        'CloudSampleAttribute', 'CameraVectorWS', 'TextureCoordinate')
OPS = {'Multiply': '*', 'Add': '+', 'Subtract': '-', 'Divide': '/'}


class Printer:
    def __init__(self, exprs):
        self.x, self.ids, self.defs, self.count = exprs, {}, [], {}
        for e in exprs.values():
            for _, src, _, _ in e.inputs:
                self.count[src] = self.count.get(src, 0) + 1

    def fmt(self, name, depth, oi=0, mask=''):
        e = self.x.get(name)
        if e is None:
            return '<%s?>' % name
        suffix = ('.' + mask.lower() if mask else '') + ('#%d' % oi if oi else '')
        if e.cls in ('Reroute', 'NamedRerouteDeclaration') and e.inputs:
            return self.fmt(e.inputs[0][1], depth, e.inputs[0][2], e.inputs[0][3] or mask)
        if e.cls in LEAF or not e.inputs:
            return label(e) + suffix
        if name in self.ids:
            return '@%d%s' % (self.ids[name], suffix)
        if depth <= 0:
            return '%s(...)%s' % (label(e), suffix)
        ins = {lab: self.fmt(src, depth - 1, o, m) for lab, src, o, m in e.inputs}
        p = e.props
        if e.cls in OPS:
            a = ins.get('A', p.get('ConstA', '0' if e.cls in ('Add', 'Subtract') else '1'))
            b = ins.get('B', p.get('ConstB', '1' if e.cls in ('Multiply', 'Divide') else ('1' if e.cls == 'Subtract' else '0')))
            s = '(%s %s %s)' % (a, OPS[e.cls], b)
        elif e.cls == 'ComponentMask':
            s = '%s.%s' % (ins.get('Input', '?'), ''.join(c.lower() for c in 'RGBA' if p.get(c) == 'True'))
        elif e.cls == 'LinearInterpolate':
            s = 'lerp(%s, %s, %s)' % (ins.get('A', p.get('ConstA', '0')), ins.get('B', p.get('ConstB', '1')), ins.get('Alpha', p.get('ConstAlpha', '0.5')))
        elif e.cls == 'If':
            s = 'if(%s vs %s: >%s, ==%s, <%s)' % (ins.get('A', '?'), ins.get('B', p.get('ConstB', '0')), ins.get('AGreaterThanB', '?'), ins.get('AEqualsB', '-'), ins.get('ALessThanB', '?'))
        elif e.cls == 'Clamp':
            s = 'clamp(%s, %s, %s)' % (ins.get('Input', '?'), ins.get('Min', p.get('MinDefault', '0')), ins.get('Max', p.get('MaxDefault', '1')))
        elif e.cls == 'Power':
            s = 'pow(%s, %s)' % (ins.get('Base', '?'), ins.get('Exponent', p.get('ConstExponent', '2')))
        elif e.cls == 'OneMinus':
            s = '(1 - %s)' % ins.get('Input', '?')
        else:
            extra = {k: v for k, v in p.items() if k in ('ConstA', 'ConstB', 'Const', 'ConstAlpha', 'SamplerSource', 'MipValueMode', 'ConstMipValue', 'CurveIndex')}
            s = '%s(%s%s)' % (label(e), ', '.join('%s=%s' % kv for kv in ins.items()), (' | ' + str(extra)) if extra else '')
        if self.count.get(name, 0) > 1 and len(s) > 40:
            self.ids[name] = len(self.ids) + 1
            self.defs.append('@%d = %s' % (self.ids[name], s))
            return '@%d%s' % (self.ids[name], suffix)
        return s + suffix


def root_inputs(exprs, nodes):
    root = next((n for n in nodes.values() if n['cls'] == 'MaterialGraphNode_Root'), None)
    if root is None:
        raise SystemExit('no material root node in the paste: select ALL nodes (including the material output) before Ctrl+C')
    pin_owner = {p['id']: (n, p) for n in nodes.values() for p in n['pins']}
    out = []
    for p in root['pins']:
        for node_name, pid in p['links']:
            n, sp = pin_owner.get(pid, (None, None))
            if n and n['expr']:
                out.append((p['name'], n['expr'], sp['name']))
    return out


def main():
    args = sys.argv[1:]
    if not args or '-h' in args or '--help' in args:
        print(__doc__)
        return 0 if args else 2
    if not os.path.isfile(args[0]):
        raise SystemExit('no such file: %s' % args[0])
    mode = args[1] if len(args) > 1 else 'summary'
    if mode not in ('summary', 'root', 'expr', 'uses'):
        raise SystemExit('unknown mode %r (summary, root, expr, uses)' % mode)
    if mode in ('expr', 'uses') and len(args) < 3:
        raise SystemExit('%s needs a name: mat_t3d.py <graph.txt> %s <%s>' % (mode, mode, 'Name' if mode == 'expr' else 'text'))

    def depth_arg(i):
        if len(args) <= i:
            return 60
        if not args[i].isdigit():
            raise SystemExit('depth must be a whole number, got %r' % args[i])
        return int(args[i])

    exprs, nodes = parse(args[0])
    if mode == 'summary':
        print('%d expressions, %d graph nodes' % (len(exprs), len(nodes)))
        print('ROOT PINS:', ', '.join('%s <- %s' % (a, b) for a, b, _ in root_inputs(exprs, nodes)))
        for cls in ('ScalarParameter', 'VectorParameter', 'CollectionParameter'):
            print('\n%s:' % cls)
            print('  ' + ', '.join(sorted(set(label(e) for e in exprs.values() if e.cls == cls))))
        print('\nTEXTURES:', ', '.join(sorted(set(label(e) for e in exprs.values() if 'Texture' in e.cls))))
        print('\nCUSTOM NODES:')
        for e in exprs.values():
            if e.cls == 'Custom':
                print('  %s  inputs=%s\n     %s' % (label(e), [i[0] for i in e.inputs], e.props.get('Code', '')[:400]))
    elif mode == 'root':
        depth = depth_arg(2)
        pr = Printer(exprs)
        tops = [(pin, pr.fmt(src, depth)) for pin, src, _ in root_inputs(exprs, nodes)]
        print('\n'.join(pr.defs))
        print()
        for pin, s in tops:
            print('ROOT.%s = %s\n' % (pin, s))
    elif mode == 'expr':
        depth = depth_arg(3)
        pr = Printer(exprs)
        s = pr.fmt(args[2], depth)
        print('\n'.join(pr.defs))
        print('\n%s = %s' % (args[2], s))
    else:
        key = args[2].lower()
        for e in exprs.values():
            for lab, src, _, _ in e.inputs:
                if src in exprs and key in label(exprs[src]).lower():
                    print('%-34s -> %s.%s  (%s)' % (label(exprs[src]), e.name, lab, label(e)))
    return 0


if __name__ == '__main__':
    sys.exit(main())

