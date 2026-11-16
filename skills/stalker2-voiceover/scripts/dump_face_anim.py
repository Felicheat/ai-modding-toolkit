"""Dump one vanilla speaker's face anims (AS_FAC_*: float curves + per-frame bone transforms) to JSON. Read-only.

Input for fit_lipsync.py. Runs inside the Zone Kit editor's Python: set the inputs, then execute this file.
Paste into the open editor's Output Log (Python mode):
    VANILLA = "/Game/.../<speaker>"; OUT = r"<work>\\facedump"; exec(open(r"<full path of this file>").read())
or put that same line in a small script file and run it headless with the stalker2-zonekit skill's sdk_run.py.
VANILLA: content folder holding the speaker's AS_FAC_* anims (searched recursively, EN and UA).
OUT: folder for the JSON files (created if missing).
"""
import json
import os
import unreal


def _inp(key, default=None):
    args = globals().get("ARGS") or {}
    return args.get(key, globals().get(key, default))


VANILLA, OUT = _inp("VANILLA"), _inp("OUT")
if not VANILLA or not OUT:
    raise RuntimeError("dump_face_anim.py: set VANILLA and OUT (see the header)")
lib = unreal.AnimationLibrary
NAMES = sorted(
    str(a.package_name)[len(VANILLA) + 1:]
    for a in unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path(VANILLA, recursive=True)
    if str(a.asset_name).startswith("AS_FAC_")
)
unreal.log(f"[FaceDump] {len(NAMES)} anims under {VANILLA}")


def tr(t):
    r = t.rotation.rotator()
    return [round(v, 4) for v in (t.translation.x, t.translation.y, t.translation.z, r.roll, r.pitch, r.yaw)]


os.makedirs(OUT, exist_ok=True)
for name in NAMES:
    anim = unreal.load_asset(f"{VANILLA}/{name}")
    if not anim:
        unreal.log_warning(f"[FaceDump] missing {name}")
        continue
    frames = lib.get_num_frames(anim)
    out = {
        "name": name,
        "length": lib.get_sequence_length(anim),
        "frames": frames,
        "skeleton": anim.get_editor_property("skeleton").get_path_name(),
        "curves": {},
        "bones": {},
    }
    for c in lib.get_animation_curve_names(anim, unreal.RawCurveTrackTypes.RCT_FLOAT):
        times, values = lib.get_float_keys(anim, c)
        out["curves"][str(c)] = [[round(t, 4), round(v, 4)] for t, v in zip(times, values)]
    for b in lib.get_animation_track_names(anim):
        out["bones"][str(b)] = [tr(lib.get_bone_pose_for_frame(anim, b, f, False)) for f in range(frames)]
    path = os.path.join(OUT, name.replace("/", "_") + ".json")
    with open(path, "w") as fh:
        json.dump(out, fh)
    unreal.log(f"[FaceDump] {name}: {frames} frames, {len(out['curves'])} curves, {len(out['bones'])} bones")


# Changed here: header rewritten for this pack (no harness helper or paths); code unchanged.
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
# Written by sdwvit.
