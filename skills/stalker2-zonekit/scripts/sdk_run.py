r"""Run a Python script inside the STALKER 2 Zone Kit editor, headless.

The Zone Kit (UE 5.5.4) ships PythonScriptPlugin and EditorScriptingUtilities enabled, so the editor will execute a script
with no GUI. This script starts the real editor binary directly (the launcher stub Stalker2ModEditor.exe can be blocked by
Smart App Control):

    <kit>/Stalker2/Binaries/Win64/Stalker2ModEditor-Win64-Shipping-Cmd.exe <uproject> -run=pythonscript -script=<file>
        -unattended -nosplash -nopause

Startup costs about six minutes (the editor parses 151k gamedata cfg files every launch), so batch the work into one script.
Everything the script prints lands in the engine log as `LogPython: ...`. The log is
%LOCALAPPDATA%/Stalker2/Saved/Logs/Stalker2.log and the editor rotates the previous one to Stalker2-backup-*.log on start,
so the current log always belongs to the current run.

The editor is started DETACHED: a run outlives the shell that launched it, so a long run cannot be killed by session teardown.
Poll it from a later call instead of holding a process open.

    python sdk_run.py <script.py>            launch, then poll until that run ends
    python sdk_run.py --launch <script.py>   launch and return immediately
    python sdk_run.py --wait                 poll the run that is already going (any running kit editor)

A headless run can read anything and can edit and save assets that are already in a mod folder (materials, material
instances, Blueprint class defaults). It cannot save a /Game asset (no mod is selected, so the checkout has nowhere to go),
add Blueprint graph nodes or edit Niagara: see the stalker2-zonekit skill. Close the kit editor first. Windows only. Needs
the Zone Kit (see s2paths.py).
"""
import csv, os, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s2paths

EDITOR_CMD = 'Stalker2ModEditor-Win64-Shipping-Cmd.exe'
EDITORS = {'stalker2modeditor-win64-shipping.exe', EDITOR_CMD.lower()}      # the GUI editor and the command line one
DETACHED = 0x00000008 | 0x00000200 | 0x08000000  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW


def log_path():
    base = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
    return os.path.join(base, 'Stalker2', 'Saved', 'Logs', 'Stalker2.log')


def editor_pids():
    """PIDs of running kit editors. CSV output keeps full image names (the table format cuts them to 25 characters)."""
    out = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True, text=True, errors='replace').stdout
    return [int(row[1]) for row in csv.reader(out.splitlines())
            if len(row) >= 2 and row[1].isdigit() and row[0].lower() in EDITORS]


def alive(proc=None):
    """proc given: is that started process still running; else: is any kit editor running."""
    if proc is not None:
        return proc.poll() is None
    return bool(editor_pids())


def launch(script):
    script = os.path.abspath(script)
    if not os.path.isfile(script):
        raise SystemExit('no such script: ' + script)
    kit = s2paths.kit_dir()
    exe = os.path.join(kit, 'Stalker2', 'Binaries', 'Win64', EDITOR_CMD)
    uproject = os.path.join(kit, 'Stalker2', 'Stalker2.uproject')
    if not os.path.isfile(exe):
        raise SystemExit('no editor binary at %s' % exe)
    running = editor_pids()
    if running:
        raise SystemExit('a kit editor is already running (pid %s); wait for it or close it' % ', '.join(map(str, running)))
    cmd = [exe, uproject, '-run=pythonscript', '-script=' + script,
           '-unattended', '-nosplash', '-nopause', '-stdout', '-NoLogTimes']
    p = subprocess.Popen(cmd, creationflags=DETACHED, close_fds=True, cwd=kit,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print('launched %s detached (editor pid %d)' % (os.path.basename(script), p.pid))
    return p


def read_log():
    log = log_path()
    if not os.path.isfile(log):
        return []
    with open(log, 'r', encoding='utf-8', errors='replace') as fh:
        return fh.read().splitlines()


def report():
    lines = read_log()
    out = [l.split('LogPython: ', 1)[1] for l in lines if 'LogPython: ' in l and 'Warning:' not in l and 'Display:' not in l]
    err = [l for l in lines if ': Error: ' in l and 'DerivedDataCache' not in l and 'AssetReferenceRestrictions' not in l]
    print('\n'.join(out))
    if err:
        print('--- engine errors ---')
        print('\n'.join(err[-15:]))
    return out


def wait(proc=None, timeout=1800):
    """Poll until the run ends. proc: the process launch() started (exact); None: any kit editor, giving up after 90 s
    if none ever shows."""
    start = time.time()
    started = proc is not None
    while time.time() - start < timeout:
        if alive(proc):
            started = True
        elif started or time.time() - start > 90:
            break                      # the run ended (or never started)
        time.sleep(5)
    out = report()
    print('--- %.0f s, %d python lines, editor %s ---'
          % (time.time() - start, len(out), 'still running' if alive(proc) else 'exited'))
    return out


def main():
    args = sys.argv[1:]
    if not args or '-h' in args or '--help' in args:
        print(__doc__)
        return 0 if args else 2
    if os.name != 'nt':
        raise SystemExit('sdk_run.py runs the Windows Zone Kit editor; it needs Windows')
    if args[0] == '--wait':
        wait()
    elif args[0] == '--launch':
        if len(args) < 2:
            raise SystemExit('--launch needs a script')
        launch(args[1])
    else:
        wait(launch(args[0]))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except s2paths.S2PathError as e:
        print(e, file=sys.stderr)
        sys.exit(2)
