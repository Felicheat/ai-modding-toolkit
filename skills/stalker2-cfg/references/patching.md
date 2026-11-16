# Patching cfg tables: rules and how each was proven

## Contents
1. Two ways to change a table
2. Where mod cfg files go
3. The rules, with proof
4. What the loader does with a patch
5. Where the sources disagree
6. Designing a patch that settles the question
7. Checks before every build

## 1. Two ways to change a table
| Way | File | Merges with other mods | Use when |
|---|---|---|---|
| Patch | `GameData/<Table>/<name>.cfg` with `{bpatch}` roots | yes, other mods' patches merge | changing a few fields of name-keyed records |
| Whole-file replacement | `GameData/<Table>.cfg` (text) | no, the last one wins outright | position-named roots, overriding your own patch values, tables where merging misbehaves |

A replacement restates EVERY vanilla record and field and changes only yours. Keep the vanilla extract it was
made from: after a game update, compare it with the new vanilla before shipping (stalker2-updates).

## 2. Where mod cfg files go
Paths below `Stalker2/Content/GameLite/GameData/`.
- On loading `X.cfg` the game applies EVERY `.cfg` in the folder `X/` beside it as a patch to `X.cfg`. The `_patch_`
  part of a file name is a convention; any name works. Vanilla relies on this: every file in `ObjPrototypes/`
  (`QuestObjPrototypes.cfg`, `GeneralNPCObjPrototypes.cfg`, the mutant files) is a patch merged into
  `ObjPrototypes.cfg`.
- The folder need not exist in vanilla:
  `WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_<Mod>.cfg` alone is enough.
- A sibling file also loads: `CoreVariables.cfg_patch_<Mod>` next to `CoreVariables.cfg` (seen working in installed
  mods; GSC describes patches in the Zone Kit support article "Config patches").
- Order in which several patch files of one folder apply: not verified (third-party `zz` prefixes assume
  alphabetical).
- DLC data is separate: patch `DLCGameData/{DLC1,Deluxe,PreOrder,Ultimate}/...` too for DLC items and weapons.
- Zone Kit mods: patch files ship as loose files under the GameData path in the mod's OverrideContent pak. New
  prototypes (effects, items, quest nodes) are plain `.cfg` files in the mod's
  `Content/GameLite/ModGameData/<Mod>/<Type>/`, the config path its GameFeatureData adds (action AddConfigsPath).
  Cooking and packing: stalker2-zonekit. The refurl form differs from a pak mod's: SKILL.md.
- Spawn actor patches (`SpawnActorPrototypes/WorldMap_WP/<Level>/<GUID>/<GUID>_patch_<Mod>.cfg`) make repo paths
  longer than 260 characters: Git for Windows refuses to add them ("Filename too long") until
  `git config core.longpaths true` in that repo.
- Offer alternative values as optional pak variants, or at runtime through Blueprint if a setter exists.

## 3. The rules, with proof
Proven in game by this pack.

| Rule | Proof (one line) |
|---|---|
| Key `{bpatch}` roots by the vanilla struct NAME, not the SID. | A root keyed by SID did not patch the record; in the A-Life Director table it crashed the game (null pointer). |
| A position-named root (`[0]`, `[1]`) cannot be patched. | The patch silently created a stray record; the vanilla values stayed in effect. |
| ...but a whole-file replacement of that table loads. | Every vanilla field restated, one value changed: the change showed in game. |
| Write a CREATED record out in full. | `NewSID : struct.begin {bpatch; refkey=Vanilla}` with one nested `[i] {bpatch}` did not inherit the vanilla record: the fields it did not restate were missing in game. Restating every field, entry and list with no refkey and no bpatch fixed it. |
| Created records resolve by SID; a `...PrototypeSID` field of another record reaches them. | Records repointed at a created record used it in game. |
| `[*]` entries appended inside a created record apply. | Appended list entries took effect in game. |
| A name-keyed root patches directly, nested index entries included. | `{bpatch}` on name-keyed roots, with `{bpatch}` on indexed entries (`[0]`, `[2]`) of their nested lists, changed those values in game (the shape of the weapon example in section 4). |
| A file at the same path as another pak's file replaces it outright. | Used for one-file tests: a loose `_<N>_P` pak over a deployed mod. |
| Two patches on one field: the later-sorting pak does NOT reliably win. | An add-on pak's patch of a field lost to the main pak's patch of the same field (measured in game). Fix: the whole file at the same path in a `_P` pak. |
| Present-but-zero is not absent. | Adding a zeroed sub-struct the base record lacked changed behaviour without crashing. |
| Two files proven safe alone can crash together. | A replacement of one table plus a patch of a related table crashed at boot; each alone was fine. |
| Merging can be unstable on some tables. | Patches merged into one group of large tables crashed in one map area; whole-file replacements of those tables fixed it. |

## 4. What the loader does with a patch
From the harness, stated there as how the loader behaves; the game logs none of it at default verbosity.
- Merge is per top-level key, the name before `: struct.begin` (not the `SID` field). Keys can differ from SIDs
  (vanilla `CorpusMedlak` has `SID = CorpMedlak`): match the key.

| Patch node | Key absent in target | Key present |
|---|---|---|
| `Key : struct.begin` (plain) | added | WHOLE NODE REPLACED: every field not restated is gone |
| `Key : struct.begin {bpatch}` | added | recursive field-by-field merge |
| `Key : removenode` | nothing | node deleted |

- The same holds below the top level: a plain struct inside a `{bpatch}` replaces that sub-struct whole. Use it on
  purpose to swap a list (a lair rank block's `SpawnSettingsPerArchetypes`), and avoid it by accident: put
  `{bpatch}` on every struct level down to the field. Fields listed replace or add, everything else is kept;
  top-level prototypes are addressed by name, array elements by index:
```
GunAK74_ST : struct.begin {bpatch}
   WeaponReloadTimePerAttachment : struct.begin {bpatch}
      [0] : struct.begin {bpatch}
         TacticalReloadTimeMultiplier = 0.75
      struct.end
   struct.end
struct.end
```
- Remove an element: `PreinstalledUpgrades : struct.begin {bpatch}`, then `[0] : removenode`, then `struct.end`.
- A plain replacement must re-inherit what it drops with `refurl` + `refkey` to the original. That shape is a
  stack-overflow risk and its refurl depends on the kind of mod: read the refurl rules in SKILL.md first.

## 5. Where the sources disagree
**Caution:** where two sources disagree, neither is settled. Do not pick one because it reads more confident: tell
the user the point is open, and test it in game on the current build before a design relies on it.
Both statements stay until one is disproven in game. Tell the user which one a design leans on.

| Topic | The harness | This pack |
|---|---|---|
| Whole-file replacement | Never ship a whole-file override of a game `.cfg`: it silently replaces every other mod's edits to the same file (a release was re-cut once because a full `CoreVariables.cfg` had slipped into the pak). | A replacement is the only thing that worked for position-named roots, for overriding your own patch value, and where merging crashed (section 3). Agreed part: patch by default, replace only for those cases. |
| Two mods bpatching one field | Per-field last-wins: the later-loaded mod wins that field only; different fields in the same file coexist (one mod's recoil fields and another's reload arrays on the same weapons). | The later-sorting pak did NOT reliably win: an add-on patch lost to the main pak's value, measured in game. Do not rely on order; set a field in one file. |
| A new (created) struct | `refkey` the closest vanilla struct and restate only changed fields; copies only when inherited list entries must go. | `{bpatch; refkey=Vanilla}` with a nested `{bpatch}` did not inherit (section 3); written out in full it worked. The failing shape mixes `{bpatch}` into a created struct, which the harness says only touches existing data, so a plain `{refkey=...}` struct may be fine: this pack has not tested that form (cfg_verify prints a NOTE for it). |
| A nested struct without `{bpatch}` | It replaces the sub-struct whole. | Not tested in game by this pack; cfg_verify warns so that you choose on purpose. |
| `removenode` | One harness document says it only works inside a `{bpatch}`; the other lists a top-level `Key : removenode` as deleting the node. | Not tested. |

## 6. Designing a patch that settles the question
- Loud canary first: a value vanilla cannot produce (an item that weighs 500 kg, a price of 1, a magazine of 999
  rounds) to prove the patch reaches the game. Then walk down to a shippable value.
- One variable per test pak; a control (mod removed) first and last. Bisecting finds nothing when every build
  carries the same defect; the control shows it.
- Ship exactly the values you measured, never an untested "safer" cut.
- The game logs nothing when a patch loads or is ignored: only behaviour in game proves it.
- "The game ignores my cfg": first diff your cfg against vanilla cfgs of the same kind (which fields vanilla always
  sets, which values vanilla never uses). Most such bugs show there in one step.

## 7. Checks before every build
1. `node scripts/cfg_verify.mjs <mod GameData> --vanilla <extract>/GameData` (plus `--dlc-vanilla` for
   Cost of Hope files, `--target zonekit` for a Zone Kit mod's files under a plain `GameData/` path): no errors;
   read every warning (a field not in the vanilla record is usually a typo; a refurl or refkey warning can mean a
   crash on console or a stack overflow).
2. The game writes `%LOCALAPPDATA%/Stalker2/Saved/Logs/SIDDup.err` (SIDs defined twice) and `Mod conflicts.csv`
   (cfg files changed by more than one pak) at every launch: check them with your build installed.
3. Pack the cfg pak (stalker2-paks) and run the loud check in game (stalker2-testing).

Sections 2, 4 and 5 use upstream material from two authors:
Adapted from the Stalker 2 modding harness (github.com/noahsemus/stalker2-modding-harness, MIT, copyright Noah Semus); this part was contributed there by sdwvit.
Adapted from the Stalker 2 modding harness by Noah Semus (github.com/noahsemus/stalker2-modding-harness, MIT).
