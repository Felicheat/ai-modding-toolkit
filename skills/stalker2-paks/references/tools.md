# retoc and repak in detail

## Contents
1. Plain cfg paks (repak)
2. Cooked trios (repak + retoc to-zen)
3. Container header version: UE5_5, never UE5_3
4. Vanilla cooked assets out of the game (to-legacy) and its limits
5. Checking a mod trio, comparing two trios
6. Package ids and chunk ids
7. Listing everything the game ships
8. Leaving assets out of a Zone Kit pak
9. Notes from the modding harness: the game's own paks, name search

Tools: retoc (trumank and Archengius), repak (trumank). Put `oo2core_9_win64.dll` next to each exe. Scripts in this
skill find them through `scripts/s2paths.py` (`python scripts/s2paths.py` shows what it found).

## 1. Plain cfg paks (repak)
- Entries read `Stalker2/Content/...`: `list`, `get` and `unpack` strip the default `../../../` mount prefix.
- One file: `repak get <pak> Stalker2/Content/GameLite/GameData/<Table>.cfg.bin > <file>`. No need to unpack the
  whole base pak (about 180 MB).
- Several: `repak unpack -i <entry or folder> [-i ...] -o <outdir> <pak>`. Works on the Zone Kit's large editor pak.
- Whole-pak diff: `repak hash-list <pak>` prints the sha256 of every file's content (well under a second on the
  base pak); diff two listings.
- Pack: stage `<stage>/Stalker2/Content/GameLite/GameData/<path>.cfg`, then `repak pack --version V11 <stage>
  <out>.pak`. Keep the default mount point. V8B (repak's default) also loads.

## 2. Cooked trios (repak + retoc to-zen)
1. Stage the legacy files (`.uasset`, `.uexp`, `.ubulk` if any) at their cooked path:
   `<stage>/Stalker2/Content/<folder>/<Asset>.uasset`.
2. Either convert the folder directly or go through a legacy pak (both load):
   `retoc to-zen --version UE5_5 <stage> <outdir>/<Name>_<N>_P.utoc`, or
   `repak pack --version V11 <stage> <tmp>/<Name>.pak` then `retoc to-zen --version UE5_5 <tmp>/<Name>.pak
   <outdir>/<Name>_<N>_P.utoc`.
3. `to-zen` writes `.utoc`, `.ucas` and the `.pak` stub side by side. The output folder must already exist. Ship
   those three; never ship the intermediate legacy pak (a cooked asset in a plain pak does nothing).
- The container name becomes part of the files and of the container header chunk id, so name it once, finally.
- Zone Kit cooks produce their own trio: stalker2-zonekit.

## 3. Container header version: UE5_5, never UE5_3
- STALKER 2 is Unreal 5.5. `--version UE5_5` writes container header version 4. `UE5_3` writes version 3: the game
  logs `Invalid container header` on every launch and ignores the package store entries; the override then only
  resolves by coincidence, because the chunk ids equal the game's.
- Check any trio: `retoc unpack-raw <utoc> <newdir>`, open the chunk whose id ends in `06` (ContainerHeader), read
  the uint32 at byte 4 (after the magic `nCoI`): 4 is right, 3 needs a repack. `retoc list <utoc>` shows the chunk
  types.

## 4. Vanilla cooked assets out of the game (to-legacy)
- `retoc to-legacy --no-shaders -f <fragment> <paks> <outdir>`: input is the `<paks>` folder (it holds
  `global.utoc`); output is legacy `.uasset`/`.uexp` under `<outdir>/Stalker2/Content/...` plus `scriptobjects.bin`
  (skip it with `--no-script-objects`). A few assets take about a second.
- `-f` is a case-sensitive substring of the asset's file path: `Content/light/Curves/Clearly` and `TimeCoefCurve`
  match; `curves/clearly` and `/Game/light/Curves` match nothing, silently. Dry-run first: `-d` prints the count
  and writes nothing.
- The output is deterministic: two extractions of the same build are byte-identical, so their hashes work as a
  baseline for update checks (stalker2-updates).
- Limits:
  - A lone mod `.utoc` cannot be converted: to-legacy needs the game's global container (script objects). Check a
    mod with raw chunks (section 5).
  - Cost of Hope cooked assets live in `<game>/DLC1/S2_DLC1Stalker2-Windows.utoc`. to-legacy over `<paks>` does not
    see them and over `<game>/DLC1` alone fails (no script objects). No tested route; compare raw chunks instead.

## 5. Checking a mod trio, comparing two trios
- Did my edit land? Byte-search the `.ucas` for a distinctive value you wrote (for example the 4 bytes of a new
  float; small `to-zen` outputs were searchable as written), or hash the chunk files from `unpack-raw`.
- Comparing two builds of a trio:
  1. `retoc unpack-raw <a.utoc> <dirA>` and the same for b (call the exe by its full path; the output folder must
     not exist yet).
  2. Each `<dir>/manifest.json` maps chunk ids to package file paths (`chunk_paths`); chunk files are
     `<dir>/chunks/<chunk id>`.
  3. Pair chunks by package path and compare bytes. Expect one extra difference: the container header chunk
     (type 06), whose id comes from the container NAME, so even a renamed copy of an identical build shows it. A
     package present in only one build shows as added or removed.
- Byte-different containers often hold identical content (packing order, name). Never judge by whole-file hashes
  of `.ucas` alone.

## 6. Package ids and chunk ids
- Package id = CityHash64 of the lower-cased UTF-16LE package name (`/Game/...`), printed little-endian the way
  `retoc list` shows it. `python scripts/package_id.py <name or Stalker2/Content/... file path>` computes it.
  Example: `/Game/_STALKER2/GameDesign/Time/TimeCoefCurve` gives `2337709ca1d8d0f2`.
- A chunk id is 12 bytes: the package id, then an index and the chunk type in the last byte (`01` export bundle
  data, `06` container header).
- A trio made with `to-zen` from legacy files at vanilla paths carries the vanilla ids. A Zone Kit mod keeps its
  own mount in the package name (`/<ModName>/...`), so its ids are NOT vanilla: never search a mod container for a
  vanilla id. Read `retoc manifest` file entries, or run `scripts/mods_conflicts.py`.

## 7. Listing everything the game ships
- `retoc manifest <utoc>` writes `pakstore.json` (every package name and file path) into the current folder and
  overwrites any file of that name. Run it from an empty temp folder in a loop over `<paks>/pakchunk*.utoc` (and
  the DLC1 `.utoc`), rename each output after its container, then grep the set.
- `retoc info <utoc>` and `retoc list <utoc>` give container details and the chunk list.

## 8. Leaving assets out of a Zone Kit pak
To ship a kit mod's pak without some of its assets (for example large textures that are unused):
- Delete them from the COOKED output (`<kit>/Stalker2/SavedMods/Cooked/<mod>/...`) after the cook, never from the kit mod
  itself, then pack again (stalker2-zonekit: `sdk_cook_mod.py <mod> --pack-only --out <dir>`).
- Before deleting, search the other cooked files for the asset's name. If any of them names it, leave it in.
- Textures were left out this way without trouble.
- A material instance whose shader map is in the shader archive CANNOT be left out: the redirect step stops with
  `assigned N shader maps, the assetinfo lists N+1 assets`.
- The next cook writes the deleted files again: repeat the deletion after every cook.

## 9. Notes from the modding harness: the game's own paks, name search
Reported by the harness for game 2.1; not re-tested for this pack. It uses the kit's `UnrealPak`; `repak` (section 1) reads the
same plain paks.
- `<paks>/pakchunk0-Windows.pak` (182 MB, a legacy pak) holds `Stalker2/Content/GameLite/GameData/...` partly as plain `.cfg`,
  but the big trees are merged binaries: `QuestNodePrototypes.cfg.bin` (44 MB unpacked), `SpawnActorPrototypes.cfg.bin`, one
  `<Type>.cfg.bin` per folder. Decoding them: stalker2-cfg.
- One file out with the kit's tool: `UnrealPak <pak> -Extract <dir> -Filter=*GameData/<Name>.cfg.bin`. `-Filter` does filter
  for `-Extract`; it is `-List` that ignores it.
- Every record in a merged binary keeps its source path (`GameData/SpawnActorPrototypes/WorldMap_WP/<Level>/<GUID>.cfg`), so
  patch-folder placement still follows the original file. SIDs and field names are plain ASCII: a byte search answers "does
  the game still have node or actor X" in seconds.
- The kit's `GameData` cfgs may differ from what the game ships: for a number that matters, read the game pak's cfg.
- Edition paks: `pakchunk101` PreOrder, `pakchunk102` Deluxe, `pakchunk104` Ultimate. Plain unencrypted `.pak`
  (`UnrealPak <pak> -List` / `-Extract <dir>` work); the entries are `.cfg.bin`, readable with any strings dump. DLC cfgs
  (`DLC1`, `Deluxe`, `Ultimate`, `PreOrder`) are not in the kit's GameLite tree: extract them from the game paks
  (`Stalker2/Content/GameLite/DLCGameData/<DLC>/`).
- The game's own IoStore containers are not encrypted either: `UnrealPak <paks>/pakchunkN-Windows.utoc -List`, or
  `-Extract <dir> -Filter=*Name*`, gives a vanilla package to diff against a mod's cooked copy. After a game patch, a
  container whose `.ucas` date predates the patch was not touched.
- Which installed mod paks contain an asset: byte-search every `.utoc`, `.pak` and `.ucas` under `<mods>` for the asset name
  (ASCII and UTF-16LE). A hit in a `.utoc` or `.pak` means that pak ships the package; a hit only in a `.ucas` means something
  references it. Per asset, the last-mounted pak wins outright. `scripts/mods_conflicts.py --all` lists the shipped packages
  from the real manifests.

Section 9 comes from the harness; its edition pak line was contributed there by sdwvit.
Adapted from the Stalker 2 modding harness by Noah Semus (github.com/noahsemus/stalker2-modding-harness, MIT).
