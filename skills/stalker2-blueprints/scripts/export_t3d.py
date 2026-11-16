"""Export any asset's graphs as T3D text (AssetExportTask), e.g. to read a Blueprint or AnimBlueprint back after a
paste, or to lift the game's own nodes with t3d_lift (same folder).

This is editor Python: it runs inside the Zone Kit, not in a plain Python. Headless, with the kit closed, through
stalker2-zonekit's sdk_run script. Set the inputs as environment variables first (PowerShell):

    $env:S2_ASSET = '/Game/.../AnimBP_X'     required: the asset's package path (/Game/... or /<Mod>/...)
    $env:S2_OUT = '<folder>'                 optional: output folder (default: the system temp folder)
    python <stalker2-zonekit skill>/scripts/sdk_run.py scripts/export_t3d.py

Output: <S2_OUT>/<AssetName>.t3d; the path is printed (a LogPython line). The export also lists
deleted-but-not-garbage-collected nodes; trust each graph's `Nodes(n)` list, not every K2Node_* block in the file.
"""
import os
import tempfile
import unreal

# Changed here: inputs come from environment variables (upstream: the ARGS / SCRATCH names its own runner injects).
ASSET = os.environ.get("S2_ASSET")
if not ASSET:
    raise RuntimeError("set S2_ASSET to the asset's package path, e.g. /Game/.../AnimBP_X")
SCRATCH = os.environ.get("S2_OUT") or tempfile.gettempdir()
# Changed here: a headless run has no mod content in the asset registry, so scan the mod's root first.
if not ASSET.startswith("/Game/"):
    unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(["/" + ASSET.split("/")[1] + "/"], True)

asset = unreal.load_asset(ASSET)
if asset is None:
    raise RuntimeError("load failed: " + ASSET)
os.makedirs(SCRATCH, exist_ok=True)
dst = os.path.join(SCRATCH, asset.get_name() + ".t3d")
t = unreal.AssetExportTask()
t.object = asset
t.filename = dst
t.automated = True
t.prompt = False
t.replace_identical = True
t.exporter = None
ok = unreal.Exporter.run_asset_export_task(t)
print(f"export ok={ok} -> {dst} ({os.path.getsize(dst) if os.path.exists(dst) else 0} bytes)")


# Changed here: ASSET and the output folder are read from the environment variables S2_ASSET / S2_OUT; mod roots are scanned.
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
