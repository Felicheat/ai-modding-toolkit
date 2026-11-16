# STALKER 2 build history and a model checklist

## Contents
1. Build 25222692 (2.0.5) to 25382007
2. Patch 2.0.4 to 2.0.5 (build 25222692)
3. A model checklist for the next update
4. Build 25382007 to 26123434 (game 2.1)

Use these as a pattern for what an update tends to touch, not as proof for a newer build: re-check every file
your mod depends on.

## 1. Build 25222692 (2.0.5) to 25382007
- No new version name; engine still 5.5.4. About 162 MB downloaded, about 170 GB re-staged (Steam rewrote whole
  containers); the content log counted 56 files updated.
- New files: `Stalker2.exe`, `Stalker2-Win64-Shipping.exe` and its DLLs (boost, tbb, OpenColorIO),
  `CrashReportClient.exe`; `pakchunk0-Windows` `.pak/.utoc/.ucas`; the `.utoc/.ucas` of pakchunks 16, 20, 23, 25,
  26, 27, 30, 31, 32, 34, 35, 36, 37, 39, 40, 41, 42; the DLC1 `.utoc/.ucas`.
- Not re-staged: `DLC1/S2_DLC1Stalker2-Windows.pak` (Cost of Hope cfg) and the edition paks 101, 102, 104.

Byte-identical to 2.0.5 (every file compared in that pass):
| Kind | What was compared |
|---|---|
| Base cfg | about two dozen GameData tables (item, weapon, NPC, world and rule tables) and `CoreVariables.cfg` |
| Cost of Hope and edition cfg | their copies of the item and weapon tables |
| Cooked curves | float and colour curves (`.uasset` and `.uexp`) |
| Other cooked assets | a material instance, a data table, a texture (compared by pixels) |

Not checked in that pass: every table outside that sample; Engine.ini cvars and post-process (the exe changed, so
those need an in-game check).

Reading: a large re-stage with a small download, the exe and some containers new, every checked table and asset
unchanged. Mods that ship cfg only needed no rebuild.

## 2. Patch 2.0.4 to 2.0.5 (build 25222692)
- The binary cfg container moved from version 1 to 2 (first uint32 of the file). Tools that read only v1 fail on
  every table (decoding: stalker2-cfg).
- Base `WeatherSelectionPrototypes`: 255 field changes across every region (durations raised nearly everywhere,
  Stormy BlendWeight zeroed in 13 of the 18 regions that had it). The other weather tables compared were
  unchanged.
- Cost of Hope `WeatherSelectionPrototypes` lost four entries (`Empty_DLC01`, `DLC01_MQ02_WeatherSelection`,
  `IronForestGlobal_DLC01`, `CNPP_Archanomaly_WeatherSelection`); their slots hold verbatim copies of base entries.
  DLC1 `SpawnActorPrototypes` volumes (and a base CNPP volume) still reference three of the lost SIDs: dangling
  references in vanilla, inferred from data (no in-game symptom confirmed).
- Lesson: whole-file replacements silently revert a GSC rebalance. Refresh the baseline from the new game, rebuild,
  and diff the old and new vanilla to see what GSC meant.

## 3. A model checklist for the next update
1. `python scripts/game_build.py`: new build id? StateFlags 4?
2. For each mod, list every vanilla file it replaces or patches (cfg tables, cooked assets, kit replacements).
3. `python scripts/compare_tables.py <baseline>` for cfg; `--cooked <fragment>` for each cooked group (for
   example a content folder, a curve name, a material name).
4. Changed files: decode and diff old vs new vanilla; decide per mod whether the change reaches it (a field it
   patches, a record it replaces, a record that moved or vanished).
5. Exe changed: test cvars and post-process mods in game.
6. Write the report (identical / changed / not checked per mod), rebuild only what changed, prove it in game,
   refresh the baselines from the new build, then `python scripts/game_build.py --record`.

## 4. Build 25382007 to 26123434 (game 2.1)
- Re-staged: the `pakchunk0-Windows` trio, the DLC1 trio, the `.ucas` / `.utoc` of pakchunk104 (its cfg `.pak` kept its old date).
- Byte-identical: about two dozen cfg tables (item, weapon, NPC, world and rule tables of the base game, with the Cost of Hope
  and edition copies of some). One more table, base and DLC1, was compared decoded: identical. One cooked curve was
  md5-identical but now sits in another pakchunk.
- Changed: `AIGlobals.cfg` lost its `CoverSettings` block (not moved elsewhere; a patch of it now targets nothing). DLC1 ItemPrototypes
  renamed one artifact effect SID: `CNPP_Archanomaly_StaminaPerAction` to `CNPP_Archartifact_StaminaPerAction`.
- Engine: one engine class gained a new property. A Blueprint cooked by kit 2.0.4 that holds values of that class then read
  them one slot off: visible rendering errors, and no crash. Re-cooking it in kit 2.1.0 fixed it. The other engine classes compared
  were not affected. Lesson: a Blueprint cooked by an older kit can read the wrong fields once the game's classes or structs
  change, so recook it with the matching kit.
- Not every table was compared here: re-check the ones your mod uses.
