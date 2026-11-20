"""Git pre-commit guardrail for mod repositories (secrets, user-path leaks, Content/ hygiene).

Checks staged files in the current git repo (or all tracked files with --all) and blocks
accidentally committing tokens, private keys, OS user paths in text logs/notes, nested
Content/Content/ folders, or non-shippable files under Content/.

    python mod_guardrail.py           check git staged files (for .git/hooks/pre-commit)
    python mod_guardrail.py --all     audit all tracked files in the repository

Pure stdlib. Exit code 0 on pass, 1 on block.
"""
import argparse
import os
import re
import subprocess
import sys

BLOCKED_FILENAMES = {
    '.env',
    '.bridge_token',
    's2_editor_bridge.token',
    '.stalker2_publish_secrets.env',
}
ALLOWED_CONTENT_EXTS = {'.uasset', '.uexp', '.ubulk', '.umap', '.cfg', '.wem', '.bnk'}
FORBIDDEN_CONTENT_DIRS = {'.git', '__pycache__', 'node_modules', '.ai'}
USER_PATH_CHECK_EXTS = {'.md', '.txt', '.log'}
TEXT_EXTS = {
    '.py', '.json', '.md', '.txt', '.log', '.cfg', '.ps1', '.bat', '.sh',
    '.mjs', '.js', '.env', '.yml', '.yaml', '.ini', '.hlsl', '.usf',
}

USER_PATH_RX = re.compile(r'(?i)(?:[\\/]' + 'Us' + 'ers' + r'[\\/]|/' + 'ho' + r'me/\w+)')
SECRET_PATTERNS = (
    ('GitHub token', re.compile(r'(?:' + 'gh' + r'p_|' + 'gh' + r'o_|github_' + r'pat_)[A-Za-z0-9_]{10,}')),
    ('Bearer header', re.compile(r'Authorization\s*:\s*' + 'Be' + r'arer\s+[A-Za-z0-9._-]{20,}', re.I)),
    ('Bridge token', re.compile(r'X-S2-Bridge-' + r'Token\s*[:=]\s*[0-9a-fA-F]{24,}', re.I)),
    ('Private key block', re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?' + 'PRIVATE ' + 'KEY-----')),
    ('Cloud access key', re.compile(r'\b' + 'AK' + r'IA[0-9A-Z]{16}\b')),
    ('Mod.io token assignment', re.compile(r'MODIO_ACCESS_' + r'TOKEN\s*=\s*\S{12,}')),
)


def _git_paths(all_tracked=False):
    cmd = ['git', 'ls-files', '-z'] if all_tracked else ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z']
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError('git path lookup failed: %s' % r.stderr.decode('utf-8', 'replace').strip())
    return [p.decode('utf-8', 'replace').replace('\\', '/') for p in r.stdout.split(b'\x00') if p]


def _read_blob(rel_posix, all_tracked=False):
    if all_tracked:
        if not os.path.isfile(rel_posix):
            return b''
        with open(rel_posix, 'rb') as fh:
            return fh.read(512 * 1024 + 1)
    r = subprocess.run(['git', 'show', ':' + rel_posix], capture_output=True)
    return r.stdout if r.returncode == 0 else b''


def _is_scannable_text(rel_posix):
    name = os.path.basename(rel_posix).lower()
    ext = os.path.splitext(name)[1]
    return ext in TEXT_EXTS or ext.startswith('.cfg_patch') or ext == '' or name in ('.gitignore', '.env')


def check_repo(all_tracked=False):
    paths = _git_paths(all_tracked=all_tracked)
    errors = []

    for rel in paths:
        parts = [p for p in rel.split('/') if p]
        if not parts:
            continue
        base_low = parts[-1].lower()
        ext_low = os.path.splitext(base_low)[1]

        if base_low in BLOCKED_FILENAMES or base_low.endswith('_secrets.env'):
            errors.append('[SECRET BLOCK] blocked secret/token filename: %s' % rel)

        if 'Content' in parts:
            c_idx = parts.index('Content')
            sub = parts[c_idx + 1:]
            if 'Content' in sub[:-1]:
                errors.append('[CONTENT BLOCK] nested Content/Content/ path: %s' % rel)
            for bad_dir in FORBIDDEN_CONTENT_DIRS:
                if bad_dir in sub[:-1]:
                    errors.append('[CONTENT BLOCK] forbidden dir (%s) inside Content/: %s' % (bad_dir, rel))
            if not (ext_low in ALLOWED_CONTENT_EXTS or ext_low.startswith('.cfg_patch')):
                errors.append('[CONTENT BLOCK] non-shippable file under Content/: %s' % rel)

        if _is_scannable_text(rel):
            blob = _read_blob(rel, all_tracked=all_tracked)
            if len(blob) <= 512 * 1024:
                text = blob.decode('utf-8', 'replace')
                for label, rx in SECRET_PATTERNS:
                    if rx.search(text):
                        errors.append('[SECRET BLOCK] possible %s in %s' % (label, rel))
                if ext_low in USER_PATH_CHECK_EXTS and USER_PATH_RX.search(text):
                    errors.append('[PATH BLOCK] machine user path leaked in %s' % rel)

    return errors


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--all', action='store_true', help='scan all tracked files instead of staged index')
    args = ap.parse_args(argv)

    try:
        errors = check_repo(all_tracked=args.all)
    except RuntimeError as e:
        print('mod_guardrail: %s' % e, file=sys.stderr)
        return 1

    if errors:
        print('mod_guardrail BLOCKED commit (%d issue(s)):' % len(errors), file=sys.stderr)
        for err in errors:
            print('  %s' % err, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
