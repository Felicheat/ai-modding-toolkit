r"""Which STALKER 2 build is installed, and has it changed since you last checked your mods?

Reads the game's Steam appmanifest_1643320.acf (found through s2paths.py) and, when it can find it, Steam's
logs/content_log.txt. Read-only unless --record.

  python game_build.py                     build id, last update, install state; compared with the build this pack
                                           was verified on and with the build you last recorded
  python game_build.py --json              the same as JSON
  python game_build.py --record [--note "<text>"]
                                           save the installed build as checked, in state.json next to the pack's
                                           paths.json (see s2paths.py); run it after your mods are re-verified

StateFlags 4 means fully installed. Any other value means an update is pending or running: wait for Steam before
testing (a launch that does nothing during an update is not a mod crash).

Exit code: 0 = fully installed and the same build as your last record (or, with no record, the pack's verified
build); 1 = a different build, or an update pending or running; 2 = no Steam manifest (GOG, Game Pass, or not found:
compare files with compare_tables.py instead).
"""
import argparse, datetime, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s2paths

VERIFIED_BUILD = '26123434'          # the Steam build this pack's facts were checked on
STATE_FILE = os.path.join(os.path.dirname(s2paths.CONFIG_FILE), 'state.json')
FIELDS = ('buildid', 'TargetBuildID', 'LastUpdated', 'StateFlags', 'UpdateResult',
          'BytesToDownload', 'BytesDownloaded', 'BytesToStage', 'BytesStaged')


def read_acf(path):
    text = open(path, encoding='utf-8', errors='replace').read()
    out = {}
    for k in FIELDS:                  # top-level keys only; LastOwner and depot ids are never read
        m = re.search(r'^\s*"%s"\s+"([^"]*)"' % re.escape(k), text, re.M)
        if m:
            out[k] = m.group(1)
    return out


def when(unix):
    try:
        return datetime.datetime.fromtimestamp(int(unix)).strftime('%Y-%m-%d %H:%M')
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def load_state():
    try:
        with open(STATE_FILE, encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(data):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    tmp = STATE_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, STATE_FILE)


def content_log():
    """Last update Steam logged for the game: {'log', 'started', 'finished', 'build', 'files_updated', 'running'}."""
    app = s2paths.STEAM_APP_ID
    for root in s2paths._steam_roots():
        path = os.path.join(root, 'logs', 'content_log.txt')
        if not os.path.isfile(path):
            continue
        info = {'log': path, 'started': None, 'finished': None, 'build': None, 'files_updated': None, 'running': False}
        rx_time = re.compile(r'^\[([0-9: -]+)\]')
        try:
            lines = open(path, encoding='utf-8', errors='replace').read().splitlines()
        except OSError:
            return None
        for line in lines:
            if 'AppID %s ' % app not in line:
                continue
            m = rx_time.match(line)
            stamp = m.group(1) if m else None
            if ' update started' in line:
                info['started'], info['running'], info['files_updated'] = stamp, True, None
            elif ' finished update' in line:
                b = re.search(r'BuildID (\d+)', line)
                info['finished'], info['running'] = stamp, False
                info['build'] = b.group(1) if b else None
            elif 'starting commit' in line:
                c = re.search(r':\s*(\d+) updated, (\d+) moved, (\d+) deleted files', line)
                if c:
                    info['files_updated'] = {'updated': int(c.group(1)), 'moved': int(c.group(2)),
                                             'deleted': int(c.group(3))}
        return info
    return None


def main(argv):
    ap = argparse.ArgumentParser(description='Installed STALKER 2 build vs the last one you checked.',
                                 epilog='Exit 0 = same build, 1 = new build or update pending, 2 = no Steam manifest.')
    ap.add_argument('--json', action='store_true', help='print JSON')
    ap.add_argument('--record', action='store_true', help='save the installed build as checked (state.json)')
    ap.add_argument('--note', default='', help='with --record: a short note, e.g. which mods were re-verified')
    a = ap.parse_args(argv)

    try:
        acf = s2paths.steam_manifest()
    except s2paths.S2PathError as e:
        acf = None
        print(e, file=sys.stderr)
    if not acf:
        msg = ('No Steam manifest (appmanifest_%s.acf) found. Not a Steam install, or the game folder is not set '
               '(python s2paths.py). Compare files instead: compare_tables.py.' % s2paths.STEAM_APP_ID)
        print(json.dumps({'error': msg}) if a.json else msg)
        return 2

    m = read_acf(acf)
    build = m.get('buildid')
    target = m.get('TargetBuildID') or build
    try:
        flags = int(m.get('StateFlags', '0'))
    except ValueError:
        flags = 0
    installed = flags == 4 and target == build
    rec = (load_state().get('game_build') or {})
    log = content_log()

    if not installed:
        verdict, code = ('UPDATE PENDING OR RUNNING (StateFlags %d, target build %s): let Steam finish, then run '
                         'this again.' % (flags, target)), 1
    elif rec.get('buildid'):
        if rec['buildid'] == build:
            verdict, code = ('SAME BUILD as your last check (recorded %s): nothing to re-verify.'
                             % rec.get('recorded_at', '?')), 0
        else:
            verdict, code = ('NEW BUILD since your last check (%s -> %s): re-verify your mods before trusting them, '
                             'then run --record.' % (rec['buildid'], build)), 1
    elif build == VERIFIED_BUILD:
        verdict, code = ('This is the build the pack was verified on. Nothing recorded yet: run --record once your '
                         'mods are checked on it.'), 0
    else:
        verdict, code = ('DIFFERENT from the pack\'s verified build %s: the pack\'s build facts may be stale; '
                         're-verify your mods, then run --record.' % VERIFIED_BUILD), 1

    if a.record:
        if not installed:
            verdict = 'NOT RECORDED: ' + verdict
            code = 1
        else:
            data = load_state()
            data['game_build'] = {'buildid': build, 'last_updated': when(m.get('LastUpdated')),
                                  'recorded_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
                                  'note': a.note}
            save_state(data)
            rec = data['game_build']
            verdict, code = 'RECORDED build %s as checked (%s).' % (build, STATE_FILE), 0

    out = {
        'manifest': acf,
        'buildid': build,
        'target_build': target,
        'last_updated': when(m.get('LastUpdated')),
        'state_flags': flags,
        'fully_installed': installed,
        'download_bytes': [m.get('BytesDownloaded'), m.get('BytesToDownload')],
        'stage_bytes': [m.get('BytesStaged'), m.get('BytesToStage')],
        'verified_build': VERIFIED_BUILD,
        'same_as_verified': build == VERIFIED_BUILD,
        'recorded': rec or None,
        'same_as_recorded': (rec.get('buildid') == build) if rec.get('buildid') else None,
        'content_log': log,
        'verdict': verdict,
    }
    if a.json:
        print(json.dumps(out, indent=2))
        return code

    print('Steam manifest : %s' % acf)
    print('build id       : %s%s' % (build, '' if target == build else '   (Steam target: %s)' % target))
    print('last updated   : %s (local time)' % (out['last_updated'] or '?'))
    print('state          : %d = %s' % (flags, 'fully installed' if flags == 4 else 'update pending or in progress'))
    if m.get('BytesToStage') and m.get('BytesToDownload'):
        print('last update    : %s MB downloaded, %s MB staged (Steam rewrites whole containers; compare content, '
              'not dates)' % (int(m['BytesToDownload']) // 1000000, int(m['BytesToStage']) // 1000000))
    print('pack verified  : %s (%s)' % (VERIFIED_BUILD, 'same' if build == VERIFIED_BUILD else 'DIFFERENT'))
    if rec.get('buildid'):
        print('your record    : %s, recorded %s%s' % (rec['buildid'], rec.get('recorded_at', '?'),
                                                     ('  (%s)' % rec['note']) if rec.get('note') else ''))
    else:
        print('your record    : none yet (%s)' % STATE_FILE)
    if log:
        if log['running']:
            print('content log    : an update started %s with no finish logged%s' % (
                log['started'], ' (the manifest says installed)' if installed else ''))
        elif log['finished']:
            fu = log['files_updated']
            print('content log    : last update finished %s, build %s%s' % (
                log['finished'], log['build'] or '?',
                (', %d files updated, %d moved, %d deleted' % (fu['updated'], fu['moved'], fu['deleted'])) if fu else ''))
    print('\n' + verdict)
    return code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
