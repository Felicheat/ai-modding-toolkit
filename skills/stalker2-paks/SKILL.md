---
name: stalker2-paks
description: Packs, names, installs and inspects STALKER 2 mod paks (plain .pak and the .pak/.utoc/.ucas IoStore trio), sets mount priority with the _N_P suffix, checks conflicts in ~mods and finds which build is really deployed. Use when packing or naming a mod, choosing a load order, asking what a mod or game pak overrides, why two mods clash, or whether an asset exists in the game.
license: MIT
compatibility: Windows. Python 3.8+ (package_id.py also needs pip install cityhash); retoc and repak (see the pack START_HERE.md)
metadata:
  pack: STALKER 2 AI Modding Toolkit
  pack-version: "1.0.0"
  author: STALKER 2 AI Modding Toolkit contributors
  verified-on: "STALKER 2 Steam build 26123434 (game 2.1), Zone Kit 2.1.0"
---

# STALKER 2 paks

## Two kinds of content, two containers
- **Cfg (GameData) ships in a plain `.pak`.** Base tables: `<paks>/pakchunk0-Windows.pak`, entries
  `Stalker2/Content/GameLite/GameData/...` (mostly `.cfg.bin`, a few plain `.cfg` such as `CoreVariables.cfg`).
  Cost of Hope: `<game>/DLC1/S2_DLC1Stalker2-Windows.pak` (`.../DLCGameData/DLC1/`), not under `<paks>`. Edition
  tables: `pakchunk101/102/104-Windows.pak` (`DLCGameData/PreOrder`, `Deluxe`, `Ultimate`). Cfg syntax: stalker2-cfg.
- **Cooked assets (curves, materials, textures, data tables, Niagara) ship as an IoStore trio**: `.pak` stub +
  `.utoc` + `.ucas` with one base name. A cooked asset in a bare legacy `.pak` does nothing (proven in game: the
  engine resolves packages through IoStore first).
- A mod archive can carry cfg in a plain pak next to its trio: always list every `.pak`, not only the `.utoc`.

## Mount priority: decide per mod
- The real order is the engine's mount priority from the `_<N>_P` tail of the file name: higher N wins (proven in
  game for a numbered pair). A bare `_P` ranks above no suffix and below any number (how the conflict script ranks
  them). Alphabetical order and prefixes like `zzz_` only order files of EQUAL priority; a mod manager's order does
  not beat a suffix.
- **No suffix** when the mod only `{bpatch}`es cfg (patches merge with other mods' patches) or adds content nobody
  else touches.
- **`_<N>_P`** when it replaces whole cfg files or cooked assets and must beat other mods replacing the same paths.
  Run the conflict check against the mods it will meet, pick N above the ones it must beat, and leave N+1 free for a
  test copy. Tell users not to rename the suffix away.
- A file at the same path in a higher-priority pak replaces the lower one outright. That is also how to test one file
  over a deployed mod: a loose test pak one step higher. Remove every test pak before judging a release build.

## Tools
| Task | Command |
|---|---|
| Files in a plain pak | `repak list <pak>` (`repak hash-list <pak>` adds sha256 of each file) |
| One file to stdout | `repak get <pak> <entry>` |
| Pack a cfg pak | `repak pack --version V11 <folder> <name>.pak` (folder holds `Stalker2/...`) |
| Packages in a trio | `retoc manifest <utoc>` (writes `pakstore.json` into the CURRENT folder) |
| Legacy cooked files to a trio | `retoc to-zen --version UE5_5 <folder or pak> <outdir>/<name>.utoc` |
| Vanilla cooked asset out | `retoc to-legacy --no-shaders -f <fragment> <paks> <outdir>` |
| What overrides what in ~mods | `python scripts/mods_conflicts.py [--dir <folder>] [--all]` |
| Which build is deployed | `python scripts/mods_identify.py --repos <folder or glob> [...] [--filter <text>]` |
| IoStore package id | `python scripts/package_id.py <package name or file path>` |

Read references/tools.md before packing a trio, extracting with to-legacy, comparing two trios, using package ids,
leaving assets out of a Zone Kit pak, or reading the game's own cfg and edition paks.

## Conflict checks
- `mods_conflicts.py` lists every file provided more than once in `<mods>` and who wins; `--dir` scans a release
  folder or a downloaded mod, `--all` lists every file. A TIE at equal priority is usually a stale older copy of the
  same mod still deployed.
- Byte-different containers can hold identical content (packing order, container name). Compare unpacked chunks,
  never whole container files.

## ~mods: what is really deployed
- The game mounts paks anywhere under `<mods>`, subfolders included. Mod managers deploy one folder per mod;
  manual and FOMOD installs may land flat. Vortex specifics: stalker2-vortex.
- **Never judge an installed version by its folder name.** A mod manager keeps the folder name of the first install
  when it updates a mod. Hash the files against your release builds with `mods_identify.py`; the `.utoc` decides,
  IoStore `.pak` stubs are near-identical across builds and are ignored.
- When a result looks wrong, list `<mods>` first: removing or replacing a mod can leave an old folder deployed. A
  disabled mod lives only in the manager's staging folder.

## Is an asset in the game?
- Fastest: a dry run, `retoc to-legacy -d --no-shaders -f <fragment> <paks> <out>` prints how many assets match and
  writes nothing.
- Full list: run `retoc manifest` on each `<paks>/pakchunk*.utoc` from an empty temp folder, rename each
  `pakstore.json` after its container, then grep. Never run it in a folder holding a `pakstore.json` you keep.

## Traps
- `-f` is a CASE-SENSITIVE substring of the asset's file path (`Content/light/Curves/Clearly`), not of the
  `/Game/...` package name. A wrong folder or case gives "Extracted 0" with no error.
- Always `--version UE5_5` for `to-zen`. `UE5_3` writes container header version 3, which the game logs as
  `Invalid container header` on every launch; its package store entries are ignored and the override only works by
  coincidence.
- `retoc to-legacy` cannot convert a lone mod `.utoc` (it needs the game's global container). Verify mod content
  with `unpack-raw` (references/tools.md).
- Git Bash: an argument starting with `/` (a `/Game/...` name) is rewritten into a path under the Git install; set
  `MSYS_NO_PATHCONV=1` or use PowerShell. Give repak and retoc Windows-style paths, not `/x/...` Git Bash paths, or
  repak reports "path not found". More shell traps: stalker2-workflow.
- A new file date after a game update is not new content: Steam re-stages whole containers. Checking a mod against
  an update: stalker2-updates.
- Two of your own paks bpatching the same field: name order does not reliably decide. Ship the whole file at the
  same path in a higher `_P` pak (patching rules: stalker2-cfg).

- `Content/Paks` is scanned recursively: a "parked" folder anywhere under it still loads. To bisect a multi-pak mod use
  `python scripts/pak_park.py park <name part>` / `restore` / `status`, which moves paks to `<game>/_parked_mods/`.
- Mount order number: no suffix = 3, plain `_P` = 103, `_<N>_P` = 3 + 100 x (N + 1).
- Log line `Failed to mount IoStore container ... Failed reading N bytes`: the `.ucas` ends inside the 16-byte read of its
  last block. The pak looks mounted and the game silently uses its own assets; whether it hits is luck of that block's
  size, so any rebuild can trigger it. Append 16 zero bytes to the `.ucas` (stalker2-zonekit's sdk_cook_mod.py does).
