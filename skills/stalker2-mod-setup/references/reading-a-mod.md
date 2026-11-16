# Reading a mod from its files

Work on copies in a scratch folder; never change the user's files while learning them.

| The inventory shows | What it is | How to read it |
|---|---|---|
| a `.pak` with entries under `GameLite/GameData/` and no `.utoc` beside it | a cfg mod | `repak unpack -o <scratch> <pak>`; folders `GameData/<Table>/*.cfg` are patches, `GameData/<Table>.cfg` are whole-file replacements; decode any `.cfg.bin` and compare with vanilla (stalker2-cfg) |
| `.pak` + `.utoc` + `.ucas` with one base name | an IoStore trio: cooked assets (curves, materials, Blueprints, data tables) | the inventory lists package paths; compare with GSC's copies (stalker2-paks, stalker2-updates `--cooked`); curves: stalker2-curves; Blueprint references: stalker2-blueprints `zen_names.py` |
| a plain `.pak` next to a trio | cfg hidden beside cooked assets | read it like a cfg mod |
| `fomod/ModuleConfig.xml` | a FOMOD installer | the inventory lists its pages and options; each option's files are a variant of the mod (stalker2-release, its FOMOD page) |
| `.uplugin`, `.uasset` under `Content/` | Zone Kit source | uasset-dump and the material readers (stalker2-zonekit); ask the user to open anything that needs the editor |
| `.txt` / `.md` | readme, changelog | read them first: they often name the intent |
| `.dll`, `.lua`, a `Scripts` folder | script-loader content | note it; this pack does not cover script mods |

## Understanding what it changes
1. List the vanilla tables or assets it touches (from the paths above).
2. Get the vanilla copies (stalker2-updates `compare_tables.py --extract` or `--cooked`) into `baseline/`.
3. Diff: `node <stalker2-cfg>/scripts/cfg_diff.mjs <baseline GameData> <mod GameData>` lists every changed record and field.
4. Name the gameplay effect of each change in plain words (stalker2-gamedata for what each record does). Mark guesses as guesses.
5. Mount priority and conflicts: `mods_conflicts.py --dir <mod folder>` (stalker2-paks).

## Questions for the user afterwards
- What should the mod feel like in game? Which values are deliberate, which are placeholders?
- Which version is live on Nexus, and which build is installed now?
- Known bugs, open reports, things still untested?
- Is anything shared with another of their mods (same tables, same assets)?
