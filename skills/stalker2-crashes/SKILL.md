---
name: stalker2-crashes
description: Triage for STALKER 2 crashes and load errors with mods. Proves first whether a mod is involved, reads the crash folder and the game's launch logs, tells a boot crash from an in-world one, decodes known error patterns, bisects paks, runs the no-op patch test and answers bug reports with data. Use when the game crashes or hangs, a user reports a crash, or a log shows an error.
license: MIT
metadata:
  pack: STALKER 2 AI Modding Toolkit
  pack-version: "1.0.0"
  author: STALKER 2 AI Modding Toolkit contributors
  verified-on: "STALKER 2 Steam build 26123434 (game 2.1), Zone Kit 2.1.0"
---

# STALKER 2 crashes

Prove before you blame: every step gives evidence the user can repeat. Package ids, retoc and conflict listing:
stalker2-paks. Console commands (coordinates, teleport, spawn): stalker2-testing. Patch syntax and keying: stalker2-cfg.

## Triage order
1. **Is it a mod at all?** Run the control: same save, same place, mods removed. Removed means `<mods>` really
   empty (list it after a Vortex purge: stale and hand-copied folders survive), any script loader off (rename its `dwmapi.dll` in
   `<game>/Stalker2/Binaries/Win64/`), no LogicMods, no tweaked ini in `%LOCALAPPDATA%/Stalker2/Saved/Config/Windows/`.
   It crashes without mods: a vanilla bug, stop suspecting mods.
2. **Collect the files** (ask a reporter for the same set):
   - Newest `UECC-Windows-*` folder in `%LOCALAPPDATA%/Stalker2/Saved/Crashes/`: `CrashContext.runtime-xml`
     (ErrorMessage, CrashType, SecondsSinceStart, call stack, `GameCoordinates` X/Y/Z in cm, ActiveQuests, the
     active mod list), that run's `Stalker2.log`, `UEMinidump.dmp`.
   - `%LOCALAPPDATA%/Stalker2/Saved/Logs/`: `Stalker2.log` (older runs: `Stalker2-backup-<time>.log`) and two files
     the game writes at every launch: `SIDDup.err` (SIDs defined twice) and `Mod conflicts.csv` (cfg files changed
     by more than one pak). Check your own builds against them too.
3. **Boot or in-world?**
   - Boot crash: before the world exists (SecondsSinceStart about a minute, GameCoordinates 0,0,0). A data load
     problem, independent of save and place: bisect paks.
   - In-world crash: real coordinates. Teleport there with mods, then without. If the same walk is clean with the
     mod, suspect quest state: compare a save with the crash file's active quest running against one without it.
4. **Read the error** against references/patterns.md (read it whenever a crash file or log has an error line).
5. **Bisect**: take half the paks out, repeat the exact repro, keep halving to one pak, then halve the records
   inside it. One variable per run, the control always first.
6. **No-op patch test**: build the suspect patch with values identical to vanilla. Still crashes: the mechanism
   is the cause (merging on that table, the patch key, a file pairing), not your values; change the mechanism
   (whole-file replacement, stalker2-cfg). Clean: the values are the cause.
7. **Reply with data** (below).

## Facts that save hours
- **"Bad export index N/M"** (AsyncLoading2.cpp, fatal): a package is read with the wrong parent-class or struct
  layout, i.e. cooked for another game version. The log's `(0x...)` package ids are the stalker2-paks package id
  with the byte order reversed. Curve, texture and material overrides cannot cause it. Detail in references/patterns.md.
- **A misspelled SID in a spawn command crashes the game.** SIDs are exact record names, case included
  (`Blinddog`, not `BlindDog`).
- **A `{bpatch}` root keyed by SID instead of the vanilla struct name** matches nothing and adds a stray struct:
  harmless in some tables, a null-pointer crash in the A-Life Director. Check the struct's real name first.
- **Two files proven safe alone are a new variable together** (a whole-file replacement plus a patch of a related
  file crashed at boot). Test the pairing before shipping.
- **Present-but-zero is not absent**: adding a zeroed sub-struct the base file lacked changed behaviour without
  crashing. Test such a change narrowly and wait for the full result before widening it.
- `EXCEPTION_ACCESS_VIOLATION writing address 0x10` is a clean null pointer; `reading` wild addresses that change
  between runs means memory that was never set, often a struct or field missing entirely.
- **`EXCEPTION_STACK_OVERFLOW` while cfg loads** (reported in the Zone Kit): suspect a refurl / refkey loop, a
  `@BaseGame` refurl to the file being patched or a refkey left without its refurl (references/patterns.md 15).
- **A log ending in `Streamline/DLSSG present failed ... DXGI_ERROR_INVALID_CALL`** is DLSS frame generation
  failing to present, not a mod's crash (references/patterns.md 16).
- **The save is a suspect too.** If "nothing of ours runs" still fails, test a save made BEFORE the mod or its dev builds ever
  ran. Mod removed + old save fine = saved state; mod removed + old save fails = another mod.
- The shipping log prints no patch-load lines: a missing line proves nothing either way.

## Replying to a bug report
- Ask for: the newest crash folder zipped (right-click it, Compress to ZIP file), `SIDDup.err`,
  `Mod conflicts.csv`, the mod list with load order, the game build, and what they did just before (quest, place).
  Tell them logs contain their Windows user name in paths; a private message is fine.
- Answer with what you checked and what it showed: what the mod overrides (stalker2-paks), whether the crashing
  package or table is among them, the control result. Say plainly when the evidence points away from your mod.
- Other mods: neutral compatibility facts, no blame without a reproducible test, and respect their permissions.
- A candidate fix ships as "needs your testing"; ask for both "fixed" and "still broken" reports.
- Read the whole reply: "no crash, but X looks wrong" is a failed test. Never call it fixed until the reporter's
  repro is clean.

## Traps
- A Vortex folder name shows the version first installed, not the one inside: hash the paks (stalker2-vortex).
- A launch that shows nothing can be Steam installing an update first (stalker2-updates). A CrashReportClient line
  at launch is the crash monitor starting, not a crash.
- One clean run is not proof for an in-world or quest crash: repeat the full repro path, with the quest state.
- A fix built on a theory that "explains" one report can be coincidence: if the no-op test or a second reporter
  disagrees, drop the theory, not the evidence.

The frame-generation and saved-state entries come from upstream. Adapted from the Stalker 2 modding harness by Noah Semus (github.com/noahsemus/stalker2-modding-harness, MIT).
