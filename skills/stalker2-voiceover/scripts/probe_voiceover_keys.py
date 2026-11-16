"""List the phrase keys the editor sees in one DialogRuntimeData asset (`<ChainSID>_Voiceover` / `_FaceAnimation`).

Read-only. Fewer keys than the file was written with = the editor dropped them on load (unknown TextTool speaker,
see the stalker2-voiceover skill); the cook keeps only what the editor kept.

Runs inside the Zone Kit editor's Python: set the inputs, then execute this file.
Paste into the open editor's Output Log (Python mode):
    PKG = "/<Mod>/Dialogs/<ChainSID>_Voiceover"; exec(open(r"<full path of this file>").read())
or put that same line in a small script file and run it headless with the stalker2-zonekit skill's sdk_run.py.

RELOAD = 1 lists the keys, reloads the package from disk, lists them again (tells a stale editor copy apart).
Optional OUT = r"<folder>": also writes <OUT>\\vo_keys.txt.
"""
import os
import unreal


def _inp(key, default=None):
    args = globals().get("ARGS") or {}
    return args.get(key, globals().get(key, default))


PKG = _inp("PKG")
if not PKG:
    raise RuntimeError("probe_voiceover_keys.py: set PKG (see the header)")
RELOAD = str(_inp("RELOAD", "0")) in ("1", "true", "True")
OUT = _inp("OUT")
lines = []


def log(s):
    lines.append(str(s))
    print(s)


def dump(tag):
    obj = unreal.load_asset(PKG)
    if not obj:
        log(f"{tag}: {PKG} did not load")
        return
    log(f"{tag}: {obj.get_name()} class {obj.get_class().get_name()}")
    try:
        log(f"  AssetType {obj.get_editor_property('asset_type')}")
    except Exception as e:
        log(f"  asset_type: {e!r}"[:200])
    container = obj.get_editor_property("asset_container")
    log(f"  container class {container.get_class().get_name() if container else None}")
    if not container:
        return
    try:
        assets = container.get_editor_property("assets")
    except Exception as e:  # FaceAnimation containers use another layout
        log(f"  assets: {e!r}"[:300])
        return
    items = list(assets.items()) if hasattr(assets, "items") else list(assets)
    log(f"  {len(items)} keys")
    for it in items:
        if isinstance(it, tuple):
            k, v = it
            try:
                v = v.export_text()
            except Exception:
                pass
            log(f"    {k} -> {v}")
        else:
            log(f"    {it}")


try:
    dump("loaded")
    if RELOAD:
        pkg = unreal.find_package(PKG) if hasattr(unreal, "find_package") else unreal.load_package(PKG)
        unreal.EditorLoadingAndSavingUtils.reload_packages([pkg], unreal.ReloadPackagesInteractionMode.ASSUME_POSITIVE)
        dump("after reload")
except Exception as e:
    log(f"FAILED: {e!r}")
if OUT:
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "vo_keys.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
unreal.log(f"probe_voiceover_keys: {len(lines)} lines")


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
