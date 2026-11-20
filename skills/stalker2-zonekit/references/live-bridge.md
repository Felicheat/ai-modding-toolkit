# Live editor bridge (opt-in)

## Contents
- Why and when to use it
- Security and safety model
- Starting and stopping the bridge
- Built-in structured actions
- Running local Python scripts (--bridge)
- Limits and traps

## Why and when to use it
Cold-launching headless editor Python with `scripts/sdk_run.py <script.py>` parses every gamedata cfg file and takes several minutes per run. When the Zone Kit GUI editor (`Stalker2ModEditor`) is already open for asset inspection or iteration, `scripts/editor_bridge.py` provides an opt-in localhost HTTP listener (`127.0.0.1:18777`) that dispatches Python tasks on the editor's Slate main thread in under a second.

It does NOT start automatically with the pack, runs nothing while the editor is closed, and leaves `scripts/sdk_run.py` headless by default unless you pass `--bridge`, `--bridge-action`, or `--bridge-status`.

## Security and safety model
- **Opt-in only:** Nothing binds a port unless the user explicitly calls `editor_bridge.start_bridge()` inside the Zone Kit Output Log or their own editor startup script.
- **Loopback only:** Refuses non-loopback hosts (`127.0.0.1` / `localhost` only; port overridable with `S2_BRIDGE_PORT`).
- **Per-boot owner-ACL token:** Writes a random 48-hex bearer token (`%LOCALAPPDATA%/Stalker2/Saved/s2_editor_bridge.token`, overridable via `S2_BRIDGE_TOKEN_FILE`) only after the port binds cleanly, restricts its NTFS ACL on Windows via `icacls`, validates `X-S2-Bridge-Token` in constant time, and removes the file on `stop_bridge()`.
- **Commandlet / cook auto-skip:** `is_commandlet_or_unattended()` returns True whenever `-run=`, `-unattended`, or `-nullrhi` is present, so background cooks or headless `sdk_run.py` runs never try to bind a port.
- **Single-slot main-thread queue & budgets:** Rejects overlapping requests immediately with HTTP `429` instead of queueing, cancels on timeout (HTTP `504`), and wraps `unreal` asset loads/saves (`max_loads` default 25 / cap 50, `max_saves` default 5 / cap 10).
- **Script execution disabled by default:** The `run_script` action is locked out until started with `allow_run_script=True` or `S2_BRIDGE_ALLOW_RUN_SCRIPT=1`. Structured read/mod-edit actions work without enabling `run_script`.

## Starting and stopping the bridge
Inside the open Zone Kit editor's **Output Log** (switch the prompt from `Cmd` to `Python`), add the skill `scripts/` folder once and start the bridge:

```python
import sys
sys.path.append(r"<path to stalker2-zonekit/scripts>")
import editor_bridge
editor_bridge.start_bridge()
```

To allow `--bridge <script.py>` file execution for the session:

```python
editor_bridge.start_bridge(allow_run_script=True)
```

To stop and delete the bearer token file:

```python
editor_bridge.stop_bridge()
```

If you want it available every interactive GUI launch, call `start_bridge()` inside your own `<kit>/Stalker2/Content/Python/init_unreal.py` (never committed to mod packs); commandlets auto-skip safely.

## Built-in structured actions
Check whether the bridge is online from any terminal:

```sh
python scripts/sdk_run.py --bridge-status
```

Run built-in structured actions via `--bridge-action <name> [--payload <json|@file.json>]`:

| Action | Payload keys | What it does |
|---|---|---|
| `get_selected` | none | Returns package path, object name and class of selected Content Browser assets |
| `scan_mod` | `mod` | Runs `scan_paths_synchronous(['/<mod>/'], True)` on a mod's Asset Registry path |
| `list_assets` | `path` (default `/Game/`), `recursive`, `limit` (cap 500) | Lists asset package paths under a content path |
| `audit_cross_mod_refs` | optional `assets` list (defaults to selection) | Checks hard package dependencies for foreign `/<OtherMod>/` references |
| `inspect_material_instance` | `asset` | Reads Parent plus overridden scalar, vector and texture parameters |
| `set_mi_params` | `asset`, `scalars`, `vectors`, `save` (bool) | Updates scalar/vector overrides on a `/<Mod>/` instance (refuses `/Game/`) and reads back values |

PowerShell quoting mangles nested JSON quotes: save payloads to a temporary JSON file and pass `--payload @payload.json`.

## Running local Python scripts (--bridge)
When started with `allow_run_script=True` (or `S2_BRIDGE_ALLOW_RUN_SCRIPT=1`), run a local script file inside the live editor with:

```sh
python scripts/sdk_run.py --bridge my_task.py [arg1 arg2 ...]
```

Forward any `S2_*` environment variables, capture `stdout`/`stderr`, and run via `runpy.run_path(..., run_name="__main__")` inside the `_BudgetGuard` limits.

## Limits and traps
- Exposes only what Unreal Editor Python exposes: Blueprint graphs and Niagara internals still cannot be authored through Python.
- Never run `scripts/sdk_cook_mod.py` while the GUI editor is open, whether the bridge is running or not: the editor locks cook caches. Close the editor first.
- `set_mi_params` refuses any asset under `/Game/`, `/Engine/`, or `/Script/`; copy an asset into `/<Mod>/` first.
- Leaving `allow_run_script=True` enabled lets any local process with read access to your user token file execute `.py` scripts inside the editor process; keep it off when structured actions suffice.
