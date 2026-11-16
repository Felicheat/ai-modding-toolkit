# Vortex internals for STALKER 2

Source: ChemBoy1's STALKER 2 Vortex extension (open source, GPL-3.0). It lives in the GitHub monorepo
`ChemGuy1611/ChemBoy1-Vortex-Games`, folder `game-stalker2heartofchornobyl/`: one unminified `index.js`, the same
file Vortex runs. The repo's `resources/*.md` notes describe Vortex core and are worth reading before re-deriving
core behaviour. Everything below is paraphrased from reading that source; check its `git log` before relying on a
detail, the repo changes often.

## Contents
1. Installer ladder
2. The pak installer and the prefix folders
3. FOMOD archives and the retag
4. Load Order mechanics
5. Installing over a previous version
6. Deployment, manifests and purge
7. Extension loading, updates and local patches
8. Where things live

## 1. Installer ladder
Lower number is tested first; the first installer that accepts the archive takes it. Every extension installer
refuses an archive containing `fomod/ModuleConfig.xml`, so Vortex's built-in FOMOD installer (priority 10) takes
those. Folder and file names match at any depth, case-insensitive, except `GameLite` (exact case).

| Priority | Installer | Accepts an archive with | Deploys to |
|---|---|---|---|
| 10 | Vortex FOMOD | `fomod/ModuleConfig.xml` | `<mods>`, flat (section 3) |
| 25 | mod merger tool | the merger tool's own exe | its own folder in `<game>` |
| 29 | combo | both a `Content` and a `Binaries` folder | `<game>/Stalker2` |
| 31 | LogicMods | a `LogicMods` folder | `<paks>/LogicMods/` (needs a script loader's blueprint loader) |
| 33 | GameLite | a file or folder named `GameLite` | `<game>/Stalker2/Content` |
| 35 | pak (sortable) | any `.pak`, `.utoc` or `.ucas` | `<mods>/<prefix>-<mod id>/` |
| 37 | script loader | `dwmapi.dll` | the game's binaries folder |
| 39 | script loader Lua mods | a `.lua` file and a `Scripts` folder | the script loader's mods folder |
| 41 | script loader C++ mods | a `.dll` and a `dlls` folder | the script loader's mods folder |
| 43 | root | a folder named `Stalker2` | `<game>`, layout kept |
| 45 | config | `engine.ini`, `game.ini`, `gameusersettings.ini`, `input.ini`, `scalability.ini` and similar | `%LOCALAPPDATA%/Stalker2/Saved/Config/Windows/` |
| 47 | saves | a `.sav` file | the save folder under `%LOCALAPPDATA%/Stalker2/Saved/` |
| 49 | fallback | anything else without a pak | the binaries folder, with a warning to the user |

Consequences for packaging:
- Any archive with a pak-family file never reaches 37 to 49. A `Stalker2/` folder or an `engine.ini` inside a
  pak archive changes nothing, and the pak installer drops every file that is not `.pak`, `.utoc` or `.ucas`.
- A pak archive that also carries a loose `GameLite` tree (cfg sources, for example) goes to the GameLite
  installer instead and lands in the game's Content folder.
- A blueprint `.pak` outside a `LogicMods` folder installs as an ordinary pak mod and does not work.

## 2. The pak installer and the prefix folders
- Copies only `.pak`, `.utoc`, `.ucas`, each to the root of the mod (basename only): two files with the same name
  in different archive folders collide. Records the file names on the mod (`unrealModFiles`) and sets the sortable
  pak mod type.
- More than 3 pak-family files: a "Multiple .pak files" dialog with one checkbox per file and Cancel / Install
  Selected / Install All. Users can pick half a trio; ship variants as separate archives or a FOMOD.
- The sortable type deploys each mod into `<mods>/<prefix>-<mod id>/`. The prefix is the mod's index in the stored
  load order written in base-25 letters, padded to three (`AAA`, `AAB`, ...). A mod missing from the order gets
  `ZZZZ-`. Mods that still carry the old shared mod type from early extension versions deploy as `ZZZZ-`; since
  2.1.2 they are retagged automatically.
- Symlinks are switched off for this game because it uses IoStore containers, so Vortex hardlinks (staging folder
  on the same drive as the game) or falls back to moving files.

## 3. FOMOD archives and the retag
- The built-in FOMOD installer returns copy instructions and never a mod-type instruction, so the mod keeps the
  default type. The default type deploys to `<mods>` merged: the FOMOD destination paths land directly in
  `<mods>`, with no per-mod folder and no Load Order row.
- Vortex stores the user's FOMOD answers on the mod (`installerChoices`); a reinstall reopens the wizard with them
  preselected. Invalid `ModuleConfig.xml` shows an error with an "Ignore" button that retries without validation.
- Since 2.1.1 a `did-install-mod` handler retags a FOMOD-installed mod as a sortable pak mod when:
  its type is still empty; its staged files include a pak-family file; none of the markers of installers above
  the pak installer is present (merger file, combo layout, a `LogicMods` folder, a `GameLite` folder); and no pak
  is staged under a `Stalker2/` folder (a game-root layout would deploy nested, so it is left alone). The paths are
  checked relative to the mod's staging folder. After the retag the extension refreshes the load order and asks
  for a deploy (skipped while a collection is installing; the final deploy picks it up).
- Result for authors: put FOMOD destinations at the mod root (or a plain subfolder), never `Stalker2/...`, and
  the mod gets a prefix folder and a Load Order row on 2.1.1 and later. Shipping a plain pak archive beside the
  FOMOD gives users of older extension versions a sortable option.

## 4. Load Order mechanics
- Vortex's file-based load order keeps the order per profile (`persistent.loadOrder[<profile>]`). The extension's
  `deserializeLoadOrder` rebuilds it from enabled mods of the sortable type: stored entries first, newly enabled
  sortable mods appended. Only that type is listed, which is why an untagged FOMOD mod never showed.
- Reordering only renames prefix folders on the next deploy. The engine itself orders paks by mount priority
  (`_<N>_P`), then by path (stalker2-paks).
- Core reloads the order on profile changes, `did-deploy`, `did-purge` and start-up, but skips every reload while a
  collection installs dependencies.
- During an update core remembers each entry's index (armed by the removal of the old version) and restores it on
  the next deploy, so an updated mod keeps its slot. A manual deploy in the middle of a batch of updates can still
  drop a slot.

## 5. Installing over a previous version
Vortex core (`InstallManager.findPreviousVersionMod`) treats an installed mod as the previous version only when:
1. its `newestFileId`, filled by the Nexus update check from the author's file update chain, equals the incoming
   file id; or
2. it has the same Nexus mod id, an identical logical file name (the Nexus file's display name) and a different
   file id.

No file id (an archive Vortex cannot identify) skips the check. On a match Vortex asks replace or install alongside;
with one profile it replaces automatically. Replace emits a removal flagged as an update, reuses the old mod id
(same staging folder name, Load Order entry and prefix folder) and carries over rules and file overrides (and the
FOMOD answers when the file id is identical). Otherwise the new version is a separate mod; both stay enabled, and
since each deploys into its own `<prefix>-<id>` folder Vortex reports no file conflict while both paks load.
Typical cause: the version is part of the Nexus file name, so rule 2 can never match, and the update chain was not
set on the file the user installed.

## 6. Deployment, manifests and purge
- Deploy order: `will-deploy` handlers, external-change check (files changed in the game folder outside Vortex),
  mod sort, merges, per mod type deployment, then `did-deploy`. A higher-ranked mod's file wins a conflict.
- Each mod type writes a manifest of what it deployed: `<mods>/vortex.deployment.<mod type>.json` for types
  targeting `<mods>`, entries with `relPath`, `source` (the staging folder name) and `target`.
- Purge removes exactly what the manifests list. Files Vortex did not deploy (hand copies, leftovers whose manifest
  entry is gone) are never touched; an orphaned folder with no mod entry and no manifest entry stays forever. The
  extension has no cleanup code; the gap is in core, so a stale folder is the user's to delete.
- Editing a deployed file by hand surfaces as an external change on the next deploy. Under hardlinks, writing into
  the deployed file in place also changes the staging copy.

## 7. Extension loading, updates and local patches
- Vortex loads extensions once, at startup, from the bundled folder and the user plugins folder
  (`%APPDATA%/Vortex/plugins/`, one folder per installed version). A user copy newer than a bundled one replaces
  it; an older one is removed. Any patch needs a full Vortex restart.
- Update offers come only from `extensions-manifest.json` in the public `Nexus-Mods/Vortex-Backend` GitHub repo
  (`out/` folder), regenerated by a daily job there. Each entry has `modId`, `fileId`, `version`, `timestamp`,
  `gameId`. Vortex caches it in `%APPDATA%/Vortex/temp/extensions-manifest.json` for an hour; the repeated
  "extension list outdated, will update" log line is that cache expiring. If the job stops, every extension stays
  frozen at the last listed version, and "check for updates" re-reads the same stale list. You can check the
  repo's commit history for that file to see whether the job runs.
- The Nexus "Mod manager download" button: Vortex's `nxm://` handler sends links for any mod id in that list to the
  in-app extension page instead of downloading, so with a stale list nothing happens (the log shows `handling url`
  and no `start download`). "Manual download", then drag the archive onto the Extensions tab, bypasses the list.
- Local patch workflow: patch the source, copy it into the installed plugin folder (the repo's dev deploy script
  does this; on a per-user Vortex install point it at `%APPDATA%/Vortex/plugins/`), restart Vortex fully, test.
  That script does not copy `info.json` on a partial update, so the displayed version stays old: grep the deployed
  `index.js` for the function you patched. A real update from the extension page installs a new plugin folder and
  your patch is gone.
- Patch hygiene for a pull request: rebase often (the repo is busy), and check a formatter has not reflowed code
  outside your change before committing.

## 8. Where things live
| What | Where |
|---|---|
| Vortex log | `%APPDATA%/Vortex/vortex.log` |
| User extensions | `%APPDATA%/Vortex/plugins/<extension folder>/` (`index.js`, `info.json`) |
| Staging folder | Vortex Settings > Mods shows the mod staging folder |
| Deployment manifests | `<mods>/vortex.deployment.<mod type>.json` |
| Config mods | `%LOCALAPPDATA%/Stalker2/Saved/Config/Windows/` (Xbox build: `WinGDK`) |
| Saves (Steam build) | `%LOCALAPPDATA%/Stalker2/Saved/STEAM/SaveGames/` |
