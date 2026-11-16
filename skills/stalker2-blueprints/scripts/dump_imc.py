"""Dump Input Mapping Context rows (action, key, mappable name, modifiers, triggers) to JSON.

This is editor Python: it runs inside the Zone Kit, not in a plain Python. Headless, with the kit closed, through
stalker2-zonekit's sdk_run script. Set the inputs as environment variables first (PowerShell):

    $env:S2_IMC = '/Game/_Stalker_2/data/input/InputMappingContexts/IMC_Exploration;/<Mod>/...'   optional, ; separated
    $env:S2_OUT = '<folder>'                 optional: output folder (default: the system temp folder)
    python <stalker2-zonekit skill>/scripts/sdk_run.py scripts/dump_imc.py

Output: <S2_OUT>/imc_dump.json; the path is printed (a LogPython line). `mappable` must read OverrideSettings/<Name>
on rows the player can rebind; rows without a mappable name never receive the player's Options > Controls rebinds.
"""
import json
import os
import tempfile
import unreal

# Changed here: inputs come from environment variables (upstream: the ARGS / SCRATCH names its own runner injects).
DEFAULT = "/Game/_Stalker_2/data/input/InputMappingContexts/IMC_Exploration"
paths = [p for p in (os.environ.get("S2_IMC") or DEFAULT).split(";") if p]
SCRATCH = os.environ.get("S2_OUT") or tempfile.gettempdir()
# Changed here: a headless run has no mod content in the asset registry, so scan each mod root first.
for root in sorted({"/" + p.split("/")[1] + "/" for p in paths if not p.startswith("/Game/")}):
    unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([root], True)
out = []


def desc(o):
    if o is None:
        return None
    d = {"class": o.get_class().get_name()}
    for prop in ("order", "value_type", "deadzone", "lower_threshold", "upper_threshold", "type", "scalar",
                 "hold_time_threshold", "is_one_shot", "tap_release_time_threshold"):
        try:
            d[prop] = str(o.get_editor_property(prop))
        except Exception:
            pass
    return d


def mappable(m):
    try:
        beh = str(m.get_editor_property("setting_behavior")).rsplit(".", 1)[-1]
    except Exception:
        beh = None
    try:
        s = m.get_editor_property("player_mappable_key_settings")
        name = str(s.get_editor_property("name")) if s else None
    except Exception:
        name = None
    return f"{beh}/{name}"


for path in paths:
    imc = unreal.load_asset(path)
    if not imc:
        out.append({"imc": path, "error": "load failed"}); continue
    for m in imc.get_editor_property("mappings"):
        act = m.get_editor_property("action")
        out.append({"imc": path.rsplit("/", 1)[1],
                    "action": act.get_name() if act else None,
                    "action_value_type": str(act.get_editor_property("value_type")) if act else None,
                    "action_triggers": [desc(x) for x in act.get_editor_property("triggers")] if act else None,
                    "key": str(m.get_editor_property("key").get_editor_property("key_name")),
                    "mappable": mappable(m),
                    "modifiers": [desc(x) for x in m.get_editor_property("modifiers")],
                    "triggers": [desc(x) for x in m.get_editor_property("triggers")]})
os.makedirs(SCRATCH, exist_ok=True)
dst = os.path.join(SCRATCH, "imc_dump.json")
open(dst, "w", encoding="utf-8").write(json.dumps(out, indent=1))
print(f"IMC dump: {len(out)} rows -> {dst}")


# Changed here: the context list and the output folder are read from the environment variables S2_IMC / S2_OUT; mod roots are scanned.
# Copied from the Stalker 2 modding harness, https://github.com/noahsemus/stalker2-modding-harness (commit 15b171c).
# MIT License, Copyright (c) 2026 Noah Semus. Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the
# Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above
# copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
