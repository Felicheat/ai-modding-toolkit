# Changelog

## Unreleased
- stalker2-zonekit: `scripts/niagara_constants.py` reads a Niagara system's module constants straight from the uncooked
  `.uasset`, with the kit closed, now supporting both UE5 1008..1011 legacy packages and 1012+ packages. references/niagara.md
  now separates that route from the clipboard route (links, dynamic inputs, expression text).
- shared/s2paths.py: `_detect_kit()` walks parent directories for `Stalker2/Stalker2.uproject` before reading Epic launcher manifests.
- stalker2-zonekit: `scripts/sdk_code_patch.py --list` now prints stored `ScalarParameter` names, defaults and counts;
  `scripts/mat_uasset_tree.py` adds `MaterialAttributesInput` walking; `scripts/sdk_cook_mod.py` packs any `.cfg`/`.cfg_patch*`
  files into a companion `_Cfg[_N]_P.pak` via repak.

## 1.0.0 (2026-11-15)
First public release, under the MIT license. 20 skills for STALKER 2 modding, an interactive installer, and an install
routine any AI agent can follow. Merges the Stalker 2 modding harness by Noah Semus, including the documents and tools sdwvit
wrote for it. Stamped for game 2.1 (Steam build 26123434) with Zone Kit 2.1.0.
