# Known crash and error patterns

Each entry: signs, what it means, the checks that settle it. Read the matching entry before proposing a fix.

## Contents
1. Bad export index N/M
2. Misspelled SID in a spawn command
3. Patch root keyed by SID (A-Life Director crash)
4. Patch merging unstable on a large table (the no-op test)
5. Boot crash after adding a second file
6. Access violations: null write vs wild reads
7. Boot crash in general (data load)
8. In-world crash tied to quest state
9. Launch-log findings: SIDDup.err, Mod conflicts.csv, Invalid container header
10. Renderer fatal errors
11. Not crashes, often reported as one
12. Pak "does nothing": Failed to mount IoStore container
13. Bad export index from new variables on a GSC class
14. Kit older than the game: wrong values, no crash
15. EXCEPTION_STACK_OVERFLOW while cfg loads (refurl / refkey loop)
16. DLSS frame generation fails to present (not a mod's crash)
17. Saved state: the fault survives removing the mod
18. Reading the logs: smaller facts

## 1. Bad export index N/M
**Signs**: fatal `ObjectSerializationError ... Bad export index N/M` from `AsyncLoading2.cpp`, often while
serializing a class default object (`Default__X_C`). N is garbage (example: 452984831 = 0x1AFFFFFF), far past M.

**Means**: an object reference read a nonsense index because the bytes are read with the wrong property layout.
The package was cooked against a different version of its parent class or of a struct it uses.

**Checks**:
- The log prints `<UPackageName> (0xID) <PackageToLoad> (0xID)`. The id is the stalker2-paks package id with the
  byte order reversed: the tool prints the bytes little-endian (`aabb70f834846a87`), the log prints the 64-bit
  number (`0x876A8434F870BBAA`).
- Both names under `/Game/...`: the vanilla package or a legacy-format replacement of it. A Zone Kit override shows
  its `/<ModName>/...` name second.
- Compare M with the vanilla export count (pull the vanilla copy with `retoc to-legacy -f <name>`, then dump it
  with uasset-dump from stalker2-zonekit).
- Read the vanilla imports for its parent blueprint. A vanilla child that crashes usually means a mod replaced the
  PARENT (or the child) with a copy built for another game version. Example: the psy phantom NPC
  `BP_AI_PsyPhantomHuman` is a child of `/Game/GameLite/Blueprints/Characters/NPC/Final/BP_AI_Human`, so any mod
  replacing `BP_AI_Human` is a suspect for its crash.
- List what every installed container overrides (stalker2-paks conflict check). Curve, texture and material
  overrides cannot cause this; blueprint, data table and struct replacements can.
- Fix: rebuild the replacement against the current game build (stalker2-zonekit, stalker2-updates).

## 2. Misspelled SID in a spawn command
**Signs**: the game dies right after a console spawn (`XSpawnObjBySID ...`).
**Means**: the SID does not exist. SIDs are the exact ObjPrototypes record names, case included (`Blinddog`, not
`BlindDog`). **Checks**: read the name from the decoded table (stalker2-gamedata) before spawning; never guess the
casing. Treat any SID typed by hand in a test the same way.

## 3. Patch root keyed by SID (A-Life Director crash)
**Signs**: a `{bpatch}` of an A-Life preset or similar singleton struct crashes once the Director runs; the same
values in a correctly keyed patch are fine.
**Means**: a patch root must be keyed by the vanilla struct NAME, not its `SID`. Example: the record with SID
`Default` lives in structs named `ALifeDirectorPreset`, `ALifePopulationManagerPreset`,
`ALifePopulationManagerPresetDLC`. A key that matches no struct adds a stray struct instead of patching: harmless
in some tables, a null dereference in the Director.
**Checks**: read the struct's raw name in the decoded cfg (or the Zone Kit source text) before writing any patch
root (stalker2-cfg). Look for other SID-keyed roots in the same mod: they are the same bug waiting.

## 4. Patch merging unstable on a large table (the no-op test)
**Signs**: crashes in one area or on load that follow no field, region or value; every theory explains one report
and fails the next. Crash signatures may change between builds.
**Means**: merging patches into that vanilla table is itself unstable at that point.
**Checks**: the no-op test. Patch a record far from the crash back onto its own vanilla values (zero data change)
and repeat the repro. Still crashes: the mechanism is the cause, so every value-based theory was coincidence. Fix:
ship the table as a whole-file replacement (stalker2-cfg). Trade-off to tell users: a whole file wins or loses
completely against other mods replacing it, it no longer merges.

## 5. Boot crash after adding a second file
**Signs**: a build that was tested crashes at boot after a related file was added (example: a whole-file
replacement of a base table plus a `{bpatch}` of its Cost of Hope counterpart). Each half alone tested clean.
**Means**: the pairing is a new variable.
**Checks**: test the pair alone, with no other mods. Use the same mechanism for both files (both whole-file, or
both patches) unless the mixed pair is proven. Recheck the "safe" default build too: a pairing bug is systemic.

## 6. Access violations: null write vs wild reads
- `EXCEPTION_ACCESS_VIOLATION writing address 0x10` (or another small address): a clean null pointer. Something
  expected an object that does not exist (a missing record, a stray struct from item 3).
- `reading` wild, non-null addresses that differ between runs (`0x0000001400000001`, `0x00000007ffffffff`):
  memory that was never initialized, typical when a struct or field is absent rather than zero.
- Rule out the script loader first: rename its `dwmapi.dll` and repeat. Still crashing: it is not the script loader.

## 7. Boot crash in general (data load)
**Signs**: SecondsSinceStart about a minute, GameCoordinates 0,0,0, every save affected.
**Checks**, in order: `SIDDup.err` for your records; `Mod conflicts.csv` for the files you change; cfg lint and
syntax (stalker2-cfg: a malformed float such as `0.5.f` in generated text is a classic); then bisect paks, then
records. Compare with the last build that booted: diff the files, not the generator settings.

## 8. In-world crash tied to quest state
**Signs**: crashes in one place only for some players, or only around one quest.
**Checks**: teleport to the crash file's coordinates (stalker2-testing) with mods, then without. Walk the same path
with the quest untouched: clean means quest state, not geography, gates the crash. The crash file's ActiveQuests
list names the running quests; quest ids are internal keys, so confirm the quest-to-name mapping before stating it.
Ask the reporter for a save from just before the crash when you cannot reach the state yourself.

## 9. Launch-log findings
All in `%LOCALAPPDATA%/Stalker2/Saved/Logs/`, rewritten at every launch.
- `SIDDup.err`: lines `class F<Type>Prototype [<SID>]`, one per SID defined twice. Compare with a launch without
  mods: lines that appear only with your mod are yours (usually a created record reusing an existing SID).
- `Mod conflicts.csv`: columns `Modified File`, `Last Applied Mod`, `Conflicting Mods`. One row per cfg path that
  more than one pak changes. Check the winner is the one you expect (mount priority and `_<N>_P`: stalker2-paks).
  `Conflicting mods overview.txt` lists the paks involved.
- `Stalker2.log` with `Invalid container header` on every launch: a `.utoc` packed with header version 3
  (`retoc --version UE5_3`). The game ignores its package store entries; overrides only resolve by coincidence.
  Repack with `UE5_5` (stalker2-paks).

## 10. Renderer fatal errors
`Fatal error: [File:...D3D12RHI/Private/D3D12Util.cpp]` (CrashType Assert) is the renderer losing the GPU
device, not a package or cfg load error. Run the control with mods removed before suspecting a mod. If it only
happens with mods, the only plausible suspects are visual ones (materials, shaders, engine ini cvars).

## 11. Not crashes, often reported as one
- The game never opens: Steam may be installing an update first (stalker2-updates).
- A mod "does nothing": a stale older copy tying at the same priority, a cooked asset shipped in a bare legacy
  `.pak` (it must be an IoStore trio), or the mod losing a conflict (stalker2-paks).
- A fix that stops the crash but visibly changes something else in the game is a failed fix: revert it and keep
  looking.

## 12. Pak "does nothing": Failed to mount IoStore container
**Signs**: no visible change; the game log says `Failed to mount IoStore container ... [Failed reading N bytes at offset X (Read Error)]`.
**Means**: the game reads each compressed block rounded up to 16 bytes and the `.ucas` ends inside that rounding.
**Checks**: grep `%LOCALAPPDATA%/Stalker2/Saved/Logs/Stalker2.log` for `Failed to mount` before anything else. Fix: append 16 zero bytes.

## 13. Bad export index from new variables on a GSC class
**Signs**: crash on load, `ObjectSerializationError ... Bad export index <huge number>` naming a level and a GSC class.
**Means**: GSC's maps hold placed instances read by property index. New member variables or components on a class placed in a cooked
level shift those indices (a float's bits get read as an object index).
**Checks**: compare the Blueprint's variable list with its backup. Graph-only edits are safe; state belongs in a new actor class of your
own, spawned from the graph.

## 14. Kit older than the game: wrong values, no crash
**Signs**: after a game update a kit-cooked override behaves oddly (visible rendering errors) while value tests explain nothing.
**Means**: see stalker2-updates: an added class property shifts unversioned values one slot. **Checks**: park paks to find the file,
then re-cook in the matching kit.

## 15. EXCEPTION_STACK_OVERFLOW while cfg loads (refurl / refkey loop)
**Signs**: `EXCEPTION_STACK_OVERFLOW` while cfg tables load, reported in the Zone Kit.
**Means**: a refurl / refkey lookup that loops. Two shapes are reported (a modder's field report; the cause is
unknown):
- a `@BaseGame` refurl that points at the same file the struct's own file patches (a struct in
  `ObjPrototypes/<patch>.cfg` with `refurl=@BaseGame/ObjPrototypes.cfg`). Some files (EffectPrototypes) are
  reported fine;
- a refkey left without its refurl: it then looks for its parent in the same file.

**Checks**: run the stalker2-cfg linter (`cfg_verify.mjs`, with `--vanilla`, and `--target zonekit` for a Zone Kit
mod's files under a plain `GameData/` path): it warns on both shapes. Search the mod's cfg for `refurl=@BaseGame/`
and compare each target with the table its file patches. Fix: use `{bpatch}` or write the struct out in full
instead of the self-pointing refurl; give the orphaned refkey its refurl back or correct the name. Then bisect the
cfg files as for any data-load crash (item 7). Which refurl form each kind of mod needs: stalker2-cfg.

## 16. DLSS frame generation fails to present (not a mod's crash)
**Signs**: the game log ends with `Streamline/DLSSG present failed ... DXGI_ERROR_INVALID_CALL`. The dump's stack
runs through `sl.interposer.dll` into the game's fatal-error exit; the exception code is 0x4000, raised from
KERNELBASE.
**Means**: DLSS frame generation failed to present a frame. Not a mod's crash.
**Checks**: read the last lines of that run's `Stalker2.log` before bisecting anything. Tell the reporter what the
log shows; the control with mods removed settles any doubt.

## 17. Saved state: the fault survives removing the mod
**Signs**: "nothing of ours runs" still fails, or a fix works once and never again. Example: carrying bodies was dead
on every save made after a mod's first dev builds, even with the mod removed, while a save from before the mod ever
ran carried with the same mod list; 13 bisect builds on the broken save measured nothing.
**Means**: the fault lives in the save, not in the paks.
**Checks**: run one control on a save made BEFORE the mod (or its dev builds) ever ran. Pick it by date: the
timestamps of `%LOCALAPPDATA%/Stalker2/Saved/STEAM/SaveGames/Data/*.sav` against the date of the mod's first build.
Mod removed + old save fine = saved state; mod removed + old save fails = another mod. Test on that clean save from
then on.

## 18. Reading the logs: smaller facts
- `%LOCALAPPDATA%/Stalker2/Saved/Logs/Stalker2.log` holds pak mounts, asserts and the crash summary. Beside it:
  `Stalker2_2.log` and `Stalker2-backup-*.log`.
- Read the logs yourself when you can reach them; do not ask a tester to paste them.
- Blueprint `Print String` is stripped from the shipping game, so a Blueprint mod writes nothing to the log: its
  silence proves nothing (tracing a Blueprint: stalker2-blueprints).
- Player rebinds and settings live in `%LOCALAPPDATA%/Stalker2/Saved/CustomizeControls.cfg` and
  `.../Saved/Config/`: they stay when every mod is removed.
- When a symptom might not be yours, park your dev pak OUTSIDE `Content/Paks/` and have the tester repeat the exact
  steps. Known case that was not the mod under test: a black-screen soft hang after sleeping. It did not happen
  with every pak off and did with the tester's other mods; bisect those if the tester wants it.

Entries 16 to 18 come from upstream. Adapted from the Stalker 2 modding harness by Noah Semus (github.com/noahsemus/stalker2-modding-harness, MIT).
