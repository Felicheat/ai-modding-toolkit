---
name: stalker2-vortex
description: How Vortex and its STALKER 2 extension install and deploy mods. Covers ~mods folders with load-order prefixes, FOMOD archives going through Vortex's own installer, the Load Order tab, when an update replaces the old version or installs beside it, stale folders and extension updates. Use when a mod lands in the wrong place, is missing from Load Order, two versions load at once, or Vortex will not update the extension.
license: MIT
metadata:
  pack: STALKER 2 AI Modding Toolkit
  pack-version: "1.0.0"
  author: STALKER 2 AI Modding Toolkit contributors
  verified-on: "STALKER 2 Steam build 26123434 (game 2.1), Zone Kit 2.1.0"
---

# Vortex and the STALKER 2 extension

Facts read from the source of ChemBoy1's STALKER 2 Vortex extension and of Vortex core. Read
references/internals.md before patching the extension, packaging anything other than a plain pak or a FOMOD
archive, or debugging the Load Order tab.

## How a mod lands in ~mods
| Archive holds | Claimed by | Deploys to |
|---|---|---|
| `.pak` (+ `.utoc` `.ucas`), no fomod | the extension's pak installer | `<mods>/<prefix>-<mod id>/`, pak-family files only, folders flattened |
| `fomod/ModuleConfig.xml` | Vortex's built-in FOMOD installer (every extension installer yields to it) | see FOMOD below |
| other layouts (LogicMods, `GameLite`, `Stalker2/` root, ini, `.sav`) | other installers | internals.md |

- **Prefix** = the mod's Load Order position as three letters (`AAA`, `AAB`, ...); `ZZZZ-` when it is not in the
  order. Reordering renames the folders at the next deploy. The prefix only sorts by path: a `_<N>_P` mount priority
  tail outranks it (stalker2-paks).
- A plain archive with more than one trio opens a "Multiple .pak files" checkbox dialog. Ship one variant per
  archive, or a FOMOD.
- **FOMOD**: the built-in installer sets no mod type, so files go flat into `<mods>` along their FOMOD destination
  paths, with no Load Order row. Since extension 2.1.1, FOMOD-installed pak mods are retagged after install so they
  get a prefix folder and show in Load Order, if the staged files are paks only (no LogicMods, combo, `GameLite` or
  merger layout, nothing under a `Stalker2/` game-root path). On older versions they still load, unsorted.
- Symlink deployment is off for this game: Vortex hardlinks (staging on the same drive as the game) or moves files.
- A disabled mod lives only in the staging folder, not in `<mods>`.

## Updates: replace or install beside
Vortex core treats an installed mod as the previous version only if:
1. its `newestFileId` (set by the Nexus update check, following the author's "new version of this file" link)
   is the incoming file, or
2. it has the same Nexus mod AND the identical Nexus file name AND a different file.

An archive with no Nexus file id gets no check. On a match (automatic with one profile, asked with several) the new
version reuses the old mod id: same staging folder name, Load Order slot and prefix folder. Otherwise it installs
as a second mod and BOTH versions stay enabled and load; Vortex shows no conflict because each has its own folder.
- Authors: keep the Nexus file name stable (the version goes in the version field) and upload each release as a
  new version of the previous file.
- Users: after any update, check for an older entry of the same mod and disable or remove it.

## Never trust a folder name
A Vortex folder (staging and `<mods>`) keeps the name of the version FIRST installed: an update swaps the files and
keeps the name. To say what is installed, hash the paks against the release builds (stalker2-paks has the script;
compare the `.utoc`, an IoStore `.pak` stub says little). Never report a version from a folder name.

## Stale folders
Purge removes only what Vortex's deployment manifests list (`<mods>/vortex.deployment.<mod type>.json`). Deleting
or replacing a mod can leave an old folder deployed; hand-copied folders are never touched. The extension has no
cleanup of its own. When a result looks wrong, list `<mods>` first and compare it with the manifests.

## Extension updates
- Vortex never reads the extension's mod page to find an update. It downloads `extensions-manifest.json` from the
  public GitHub repo `Nexus-Mods/Vortex-Backend` (folder `out/`), caches it for an hour in
  `%APPDATA%/Vortex/temp/` and compares versions. "extension list outdated, will update" in
  `%APPDATA%/Vortex/vortex.log` is that cache expiring, not an error.
- When that list is stale, Vortex offers no update, and the page's "Mod manager download" button silently does
  nothing for the extension. Workaround: "Manual download" on the extension's page, then drag the archive onto
  Vortex's Extensions tab.
- Testing a local patch of the extension needs a full Vortex restart: extensions load at startup only. A real
  update installs a new plugin folder and silently replaces a manual patch.
- Never trust the displayed version after a partial deploy (dev copy tools may skip `info.json`, so the old number
  stays). Grep the deployed `index.js` for the function you changed.

## Traps
- Editing a deployed file in place also edits the staging copy (a hardlink is the same file). Rebuild, redeploy.
- Hand-copied test folders in `<mods>` survive every purge: remove them yourself.
- FOMOD destinations under `Stalker2/Content/Paks/~mods/` deploy a nested tree that is never retagged: install flat.
- A pak archive that also holds a loose `GameLite` folder is claimed by the extension's GameLite installer and
  lands in `<game>/Stalker2/Content/`, not in `<mods>`.
