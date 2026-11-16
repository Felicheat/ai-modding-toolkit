"""Create a local repo for one STALKER 2 mod, in the layout the stalker2-mod-setup skill uses.

    python init_mod_repo.py <folder> --name "<Mod name>" [--author "<name>"] [--email <address>] [--no-git]

Creates MOD.md, CHANGELOG.md, LOG.md, source/, release/, baseline/, notes/, .gitignore and .gitattributes, then runs
git init and makes the first commit (when git is installed and --no-git is not given). It never overwrites an existing
file and never adds a remote. Commits use the name and email from --author / --email, else git's own settings, else a
local placeholder (name "modder", email "modder@localhost") set for this repo only. Stdlib only.
"""
import datetime, os, shutil, subprocess, sys

DIRS = ('source', 'release', 'baseline', 'notes')
KEEP = 'Kept by git so the folder exists.\n'


def files(name):
    today = datetime.date.today().isoformat()
    return {
        'MOD.md': f"""# {name}

## What it does
(For the player, in plain words.)

## Files and versions
| Version | Files | Where it is published |
|---|---|---|

## What it changes
| Table or asset | Record or part | Change | Why |
|---|---|---|---|

## Load priority and conflicts
(Mount priority suffix, mods that touch the same files, compatibility notes.)

## How it is built
(Source files, scripts, the Zone Kit mod name, packing steps.)

## Known issues and open questions

## Last game build checked
(Steam build, date, what was compared.)
""",
        'CHANGELOG.md': f"# Changelog: {name}\n\n",
        'LOG.md': f"# Test log: {name}\n\nOne entry per test build: what changed, what was tested, the verdict in the tester's own words.\n\n",
        '.gitignore': "baseline/\nscratch/\n__pycache__/\nnode_modules/\n*.bak\n",
        '.gitattributes': "*.pak binary\n*.utoc binary\n*.ucas binary\n*.uasset binary\n*.uexp binary\n*.ubulk binary\n*.cfg.bin binary\n",
        'baseline/README.md': "Vanilla extracts for update checks. Git-ignored: this is GSC data and stays on this PC.\n",
        'release/README.md': "One folder per shipped version, e.g. release/1.2.0/, holding exactly the files that shipped.\n",
        'source/README.md': "The readable source of the mod: cfg patch files, generator scripts, Zone Kit asset backups.\n",
        'notes/README.md': f"Notes kept with the mod. Started {today}.\n",
    }


def git(args, cwd):
    return subprocess.run(['git'] + args, cwd=cwd, capture_output=True, text=True)


def main(argv):
    if not argv or argv[0] in ('-h', '--help') or '--name' not in argv:
        print(__doc__)
        return 0 if argv and argv[0] in ('-h', '--help') else 2

    def opt(flag):
        return argv[argv.index(flag) + 1] if flag in argv and argv.index(flag) + 1 < len(argv) else None

    folder, name = os.path.abspath(argv[0]), opt('--name')
    if not name or name.startswith('--'):
        print('--name needs a value')
        return 2
    os.makedirs(folder, exist_ok=True)
    made, kept = [], []
    for d in DIRS:
        os.makedirs(os.path.join(folder, d), exist_ok=True)
    for rel, text in files(name).items():
        p = os.path.join(folder, rel)
        if os.path.exists(p):
            kept.append(rel)
            continue
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        made.append(rel)
    print('created: %s' % (', '.join(made) or 'nothing new'))
    if kept:
        print('left as they were: %s' % ', '.join(kept))
    if '--no-git' in argv:
        print('plain folder only (--no-git)')
        return 0
    if not shutil.which('git'):
        print('git is not installed: the folder is ready without version history. Install Git for Windows and run this again.')
        return 0
    if not os.path.isdir(os.path.join(folder, '.git')):
        r = git(['init', '-q', '-b', 'main'], folder)
        if r.returncode:
            r = git(['init', '-q'], folder)
        if r.returncode:
            print('git init failed: %s' % r.stderr.strip())
            return 1
        print('git repo created (local only, no remote)')
    author, email = opt('--author'), opt('--email')
    if author:
        git(['config', 'user.name', author], folder)
    elif not git(['config', 'user.name'], folder).stdout.strip():
        git(['config', 'user.name', 'modder'], folder)
    if email:
        git(['config', 'user.email', email], folder)
    elif not git(['config', 'user.email'], folder).stdout.strip():
        git(['config', 'user.email', 'modder@localhost'], folder)
    git(['add', '-A'], folder)
    if git(['diff', '--cached', '--quiet'], folder).returncode == 0:
        print('nothing new to commit')
        return 0
    r = git(['commit', '-q', '-m', 'Start the %s repo' % name], folder)
    if r.returncode:
        print('commit failed: %s' % (r.stderr or r.stdout).strip())
        return 1
    print('first commit made: %s' % git(['log', '--oneline', '-1'], folder).stdout.strip())
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
