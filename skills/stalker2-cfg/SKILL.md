---
name: stalker2-cfg
description: Reads, writes and patches STALKER 2 cfg tables, the game's gameplay data. Covers cfg syntax, binary .cfg.bin containers, the bpatch / refkey / refurl rules for pak mods and Zone Kit mods, quest node and dialog tables, and tools that decode .cfg.bin, lint a mod's cfg files and diff tables between game builds. Use before writing or patching any cfg, building a quest or dialog, or when a patch does nothing or crashes.
license: MIT
compatibility: Node.js 24 or newer; run npm install once in scripts/ (fetches s2cfgtojson by sdwvit from npm)
metadata:
  pack: STALKER 2 AI Modding Toolkit
  pack-version: "1.0.0"
  author: STALKER 2 AI Modding Toolkit contributors
  verified-on: "STALKER 2 Steam build 26123434 (game 2.1), Zone Kit 2.1.0"
---

# STALKER 2 cfg tables

Which record holds a weapon, NPC, damage or time value: stalker2-gamedata. Packing a cfg pak and load priority:
stalker2-paks. Checking tables after a game update: stalker2-updates. Crashes from a patch: stalker2-crashes.

## Where the data is
- The game reads binary tables, `Stalker2/Content/GameLite/GameData/<Table>.cfg.bin`, from `<paks>/pakchunk0-Windows.pak`
  (Cost of Hope: `DLCGameData/<DLC>/...` in `<game>/DLC1/S2_DLC1Stalker2-Windows.pak`). Get one with
  `repak get <pak> <entry> > <file>`. A few tables ship as text `.cfg`.
- The Zone Kit holds GSC's commented TEXT tree (`<kit>/Stalker2/Content/GameLite/GameData/`): best for reading, but it
  can lag the game version. Confirm anything you ship against the game's binaries.
- Since game 2.0.5 the binaries are container version 2: tools that only know v1 (s2cfgtojson before 9.2) fail or
  misread them.

## Tools (`npm install` once in scripts/; never publish their output, it is GSC data)
| Need | Command |
|---|---|
| A .cfg.bin as text | `node scripts/cfgbin_decode.mjs <table.cfg.bin> [--record <names>]` |
| A whole extract as text | `node scripts/cfgbin_decode.mjs <folder> --out <text folder>` (`--check` = decode, re-read, compare) |
| Lint a mod's cfg files | `node scripts/cfg_verify.mjs <mod folder> [--vanilla <extract>/GameData] [--dlc-vanilla <dlc GameData>] [--target pak\|zonekit]` |
| What changed between builds | `node scripts/cfg_diff.mjs <old GameData> <new GameData> [--only <text>] [--records]` |

`cfg_verify` always checks syntax, a parse round trip and each refurl against the kind of mod, told from the path
(`ModGameData/` = Zone Kit mod, `GameData/` without it = pak mod; `--target` overrides). With `--vanilla` (the
extracted `GameData` folder itself) it also checks the patch rules below and refkeys whose parent is missing.
Exit 1 = errors. Run it on every build before the user tests. Large tables (QuestNodePrototypes) need
`node --max-old-space-size=8192 ...`.

## Syntax in one screen
```
RecordName : struct.begin {refkey=ParentRecord}
   SID = RecordName
   Value = 0.5
   List : struct.begin
      [0] = First
      [*] = Appended
   struct.end
struct.end
```
- `{refkey=X}` inherits record X of the same file; `{refurl=<file>;refkey=X}` inherits from another file;
  `{bpatch}` on a root patches the existing record of that NAME; `Key : removenode` removes a node.
- A patch goes at `GameData/<Table>/<anything>.cfg` (merged into the table), a whole-file replacement at
  `GameData/<Table>.cfg`. Same under `DLCGameData/<DLC>/`.

## Patching rules (proven in game; proof in references/patching.md)
1. A `{bpatch}` root is keyed by the vanilla struct NAME, never its SID. A SID key adds a stray record (harmless
   in some tables, a crash in the A-Life Director's).
2. A root named by position (`[0]`) cannot be patched: replace the whole table, restating every vanilla field.
3. A record you CREATE must be written out in full, with no refkey and no nested `{bpatch}`. One that refkeyed
   vanilla and bpatched one nested entry did NOT inherit the rest.
4. Created records resolve by SID, so `...PrototypeSID` pointers reach them; `[*]` entries appended inside one apply.
5. A name-keyed root patches directly with `{bpatch}`, nested index entries included (`SoundEvents [0]`). Mark every
   nested struct you edit `{bpatch}` too: a plain struct there replaces that sub-struct whole.
6. Two patch files setting the same field: the later-sorting pak does NOT reliably win. To override a value
   another of your files sets, ship the whole file at the same path in a `_<N>_P` pak.
7. Present-but-zero is not absent: adding a zeroed sub-struct the base record lacks changes behaviour.
8. If merging misbehaves on a table, ship it as a whole-file replacement (and keep its baseline for updates).

The harness (credited below) disagrees on rules 3, 6 and 8: both sides are in references/patching.md section 5.
Caution: those points are open. Tell the user, and test in game before a design relies on either side.
Before tuning a patched value, prove the patch reaches the game with a loud value (stalker2-testing).

## refurl by kind of mod
- **Zone Kit (Game Feature) mod** (Steam Workshop, mod.io, Xbox): `refurl=@BaseGame/<path below GameData>`.
  Relative refurls (`../X.cfg`) break on console since game 2.0 even when PC works.
- **Plain pak in `<mods>`**: no config path is active (the log says "No config paths are active"), so use relative
  refurls. `@BaseGame` should fail there with "references config path ... which is not active" (from
  s2cfgtojson's notes, not tested in game).
- A mod shipped both ways needs different refurls per build.
- `EXCEPTION_STACK_OVERFLOW` while cfg loads: a `@BaseGame` refurl to the same file that is being patched can loop
  in the kit (use `{bpatch}` or the full struct), and a refkey left without its refurl looks in the same file and
  can also overflow.

## Traps
- Writing tables from code: s2cfgtojson's `Struct.toString()` turns keys that parse as numbers (32-hex GUID keys)
  into array indexes and renders every sibling of a `[*]` as `[*]`; its text parser renames nested keys. Use
  `scripts/lib/writeCfg.mjs`, which writes names verbatim, and run every generated table through `cfg_verify`.
- Some vanilla headers have no space before the colon (`GunM10_HG_NPC: struct.begin`): grep `^Name\s*:`.
- GSC writes `600.f`; a typo like `0.5.f` is a bug the game may not report.
- A patch on a template does not reach children that restate the same field.
- A quest condition naming a missing SID nulls its whole node; a save holds at most 65,535 quest-node names.

## References and credit
- Read references/patching.md before writing any patch or replacement, and when a patch did nothing or crashed.
- Read references/inheritance.md before using refkey or refurl, editing a list, patching DLC items, or writing cfg
  for a Zone Kit mod.
- Read references/quests-dialogs.md before writing quest nodes, conditions or dialogs.
- Read references/binary.md when a decoder fails, a new game build changes the container, or you parse tables.

The tools are our own wrappers around s2cfgtojson by sdwvit (github.com/sdwvit/S2CfgToJSON). None of his code is in this
repo: `npm install` fetches it, and its licence terms are his (his readme says non-commercial use).
Loader, refkey / refurl, quest and dialog facts: Adapted from the Stalker 2 modding harness (github.com/noahsemus/stalker2-modding-harness, MIT, copyright Noah Semus); this part was contributed there by sdwvit.
