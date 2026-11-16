r"""Zip a folder for release with forward-slash entry names (what every zip reader accepts).

    python make_zip.py <folder> <out.zip> [--top NAME] [--store] [--exclude-dir NAME ...] [--force] [--dry-run]

  <folder>        the folder whose contents go into the zip
  <out.zip>       the zip to write (must be outside <folder>; an existing file needs --force)
  --top NAME      put every entry under NAME/ (a mod folder name). Leave it out for FOMOD archives:
                  fomod/ must sit at the zip root.
  --store         no compression (paks are already compressed; faster on big files)
  --exclude-dir   another folder name to skip (repeatable); always skipped: .git __pycache__ bin obj node_modules
  --dry-run       list what would go in, write nothing

Refuses (exit 2, nothing written) symlinks, directory junctions and anything that resolves outside <folder>.
Prints every entry with its size, the totals and the zip's sha256, then re-reads the zip to check CRCs and
entry names. Exit codes: 0 ok, 1 the written zip failed its check, 2 refused or usage error.
Stdlib only, no network.
"""
import argparse
import hashlib
import os
import shutil
import stat
import sys
import time
import zipfile

SKIP_DIRS = {'.git', '__pycache__', 'bin', 'obj', 'node_modules'}
REPARSE_POINT = getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400)


class Refused(Exception):
    pass


def norm(p):
    return os.path.normcase(os.path.realpath(p))


def inside(path, root_real):
    real = norm(path)
    return real == root_real or real.startswith(root_real.rstrip(os.sep) + os.sep)


def is_link_like(path, is_dir):
    """True for a symlink, or a directory reparse point that points elsewhere (a junction)."""
    if os.path.islink(path):
        return True
    if is_dir:
        isjunction = getattr(os.path, 'isjunction', None)
        if isjunction and isjunction(path):
            return True
        try:
            attrs = getattr(os.lstat(path), 'st_file_attributes', 0)
        except OSError:
            return False
        if attrs & REPARSE_POINT and norm(path) != os.path.normcase(os.path.abspath(path)):
            return True
    return False


def collect(root, skip_dirs):
    """Return [(abs path, entry name, size)] sorted by entry name; raise Refused on links or escapes."""
    root_abs = os.path.abspath(root)
    root_real = norm(root_abs)
    out = []
    for dirpath, dirnames, filenames in os.walk(root_abs, followlinks=False):
        keep = []
        for d in sorted(dirnames):
            full = os.path.join(dirpath, d)
            if d in skip_dirs:
                continue
            if is_link_like(full, True):
                raise Refused('link or junction: %s' % full)
            if not inside(full, root_real):
                raise Refused('folder resolves outside %s: %s' % (root_abs, full))
            keep.append(d)
        dirnames[:] = keep
        for f in sorted(filenames):
            full = os.path.join(dirpath, f)
            if is_link_like(full, False):
                raise Refused('symlink: %s' % full)
            if not inside(full, root_real):
                raise Refused('file resolves outside %s: %s' % (root_abs, full))
            rel = os.path.relpath(full, root_abs).replace(os.sep, '/')
            if '\\' in rel:
                raise Refused('file name contains a backslash: %r' % rel)
            out.append((full, rel, os.path.getsize(full)))
    out.sort(key=lambda t: t[1])
    return out


def zip_time(path):
    t = time.localtime(os.path.getmtime(path))
    return max((t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec), (1980, 1, 1, 0, 0, 0))


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def verify(zpath, expected):
    problems = []
    with zipfile.ZipFile(zpath) as z:
        bad = z.testzip()
        if bad:
            problems.append('CRC error in %s' % bad)
        names = z.namelist()
    for n in names:
        if '\\' in n or n.startswith('/') or '..' in n.split('/') or (len(n) > 1 and n[1] == ':'):
            problems.append('bad entry name %r' % n)
    if sorted(names) != sorted(expected):
        problems.append('entry list differs from what was collected (%d vs %d)' % (len(names), len(expected)))
    return problems


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('folder')
    p.add_argument('out')
    p.add_argument('--top', help='put every entry under this folder name')
    p.add_argument('--store', action='store_true', help='store without compression')
    p.add_argument('--exclude-dir', action='append', default=[], help='another folder name to skip')
    p.add_argument('--force', action='store_true', help='overwrite an existing zip')
    p.add_argument('--dry-run', action='store_true', help='list only, write nothing')
    a = p.parse_args(argv)
    try:
        sys.stdout.reconfigure(errors='replace')
    except (AttributeError, ValueError):
        pass

    if not os.path.isdir(a.folder):
        print('STOP not a folder: %s' % a.folder)
        return 2
    top = (a.top or '').strip().strip('/\\')
    if top and (any(c in top for c in '\\:*?"<>|') or '..' in top.split('/')):
        print('STOP --top must be a plain folder name: %r' % a.top)
        return 2
    out_abs = os.path.abspath(a.out)
    if inside(out_abs, norm(a.folder)):
        print('STOP the zip would land inside the folder it zips; write it somewhere else')
        return 2
    if os.path.exists(out_abs) and not a.force and not a.dry_run:
        print('STOP %s exists (use --force to overwrite)' % out_abs)
        return 2
    try:
        files = collect(a.folder, SKIP_DIRS | set(a.exclude_dir))
    except Refused as e:
        print('STOP refused, nothing written: %s' % e)
        return 2
    if not files:
        print('STOP nothing to zip in %s' % a.folder)
        return 2

    names = [(top + '/' if top else '') + rel for _, rel, _ in files]
    lower = {}
    for n in names:
        lower.setdefault(n.lower(), []).append(n)
    for group in lower.values():
        if len(group) > 1:
            print('WARN names that collide on Windows (case only): %s' % ', '.join(group))

    total = 0
    for (_, _, size), name in zip(files, names):
        print('%12d  %s' % (size, name))
        total += size
    print('%d files, %d bytes before compression' % (len(files), total))
    if a.dry_run:
        print('dry run: nothing written')
        return 0

    method = zipfile.ZIP_STORED if a.store else zipfile.ZIP_DEFLATED
    tmp = out_abs + '.partial'
    os.makedirs(os.path.dirname(out_abs) or '.', exist_ok=True)
    try:
        with zipfile.ZipFile(tmp, 'w', method, allowZip64=True) as z:
            for (src, _, size), name in zip(files, names):
                info = zipfile.ZipInfo(name, zip_time(src))
                info.compress_type = method
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                info.file_size = size
                with open(src, 'rb') as fh, z.open(info, 'w') as dst:
                    shutil.copyfileobj(fh, dst, 1 << 20)
        os.replace(tmp, out_abs)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    problems = verify(out_abs, names)
    print('wrote %s (%d bytes)' % (out_abs, os.path.getsize(out_abs)))
    print('sha256 %s  %s' % (sha256(out_abs), os.path.basename(out_abs)))
    for pr in problems:
        print('FAIL ' + pr)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
