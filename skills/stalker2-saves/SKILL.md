---
name: stalker2-saves
description: "Reads STALKER 2 save files (.sav): where they are, the Oodle-compressed format, unpacking a save and searching it for quest nodes, global variables and paks, and the 65,535 quest-node name limit that makes saves crash on load when mods add too many quest nodes. Use when a save crashes on load or at boot, before shipping a mod with many quest nodes, or to see what a quest step wrote into a save."
license: MIT
compatibility: Python 3.11+ (standard library only). The Oodle library from the user's own Zone Kit (the pack does not include it)
metadata:
  pack: STALKER 2 AI Modding Toolkit
  pack-version: "1.0.0"
  author: STALKER 2 AI Modding Toolkit contributors
  verified-on: "Taken from the Stalker 2 modding harness (commit 15b171c); not re-checked by this toolkit"
---

# STALKER 2 save files

What a save holds, how to open one, and the quest-node name limit that makes saves unloadable when mods add too many
quest nodes. Checked upstream on game 2.0.x saves.
Adapted from the Stalker 2 modding harness (github.com/noahsemus/stalker2-modding-harness, MIT, copyright Noah Semus); this part was contributed there by sdwvit.

## Rules
1. Never write into the live save folder unless the user asks. Unpack into a scratch folder (`-o <dir>`).
2. Saves are compressed: grepping a `.sav` for SIDs finds nothing. Unpack first.
3. **Repacking is untested in game** (see "Repacking" below): work on a copy, never on the user's save.
4. You can read names and text in a save, not values: quest states, global variable values and inventory are not
   decoded by any known tool.

## Where saves are
| What | Path |
|---|---|
| Saves | `%LOCALAPPDATA%/Stalker2/Saved/STEAM/SaveGames/Data/*.sav` (one file per save, hex-GUID names) |
| Save index | `%LOCALAPPDATA%/Stalker2/Saved/STEAM/SaveGames/CampaignsSave.sav` (same compression, no name table) |
| Temporary campaigns | `.../SaveGames/TempCampaigns/` |
| Automatic backups | `%LOCALAPPDATA%/Stalker2/Saved/Backups/<SteamID>/<timestamp>/` (copies of all saves) |

Linux: the same tree inside the game's Proton prefix (references/format.md; prefixes: stalker2-linux).

## scripts/s2sav.py
```
python scripts/s2sav.py list [dir]                  newest first: time, size, name count, file
python scripts/s2sav.py unpack <sav>... -o <dir>    writes <file>.sav.raw
python scripts/s2sav.py names <sav|raw> [--dump]    count; --dump prints "index<TAB>name"
python scripts/s2sav.py strings <sav|raw> [--grep RE] [--offsets] [-n 6]
python scripts/s2sav.py diff <a> <b> [--grep RE]    "- " only in a, "+ " only in b
python scripts/s2sav.py pack <raw> -o <sav>         compress a .raw back (untested in game)
```
- Every command takes a `.sav` (decompressed in memory) or a `.raw`.
- **Oodle is not in this pack.** The script loads the library from the user's own Zone Kit: `--oodle <file>`, else
  env `OODLE_LIB`, else `<kit>/Engine/Binaries/DotNET/AutomationTool/oo2core_9_win64.dll` with the kit found by
  `scripts/s2paths.py` (run it to see what it found). Without a kit the script cannot run.
- Always give `unpack` a scratch folder with `-o`: without it the `.raw` lands next to the save.
- `strings --grep <ModPrefix>` finds one mod's traces (its quest nodes, global variables, pak). `diff` on a save
  from before and one from after a quest step shows what the step wrote.
- What is readable: the name table (every quest node the save refers to), all readable text in file order (quest,
  prototype and global-variable IDs, paks), and text that appears or disappears between two saves.

## Repacking: untested in game
`pack` round-trips byte for byte through `unpack`, but the game has never been tested with a repacked or edited
save. So:
- Keep the original save untouched and work on a copy of it in a scratch folder.
- Write the result under a new name (the script refuses to write over an existing file).
- Say plainly to the user that loading a repacked save is an experiment. Putting it into the save folder is the
  user's decision and the user's action, with the original and the automatic backups kept.

## The 65,535 quest-node name limit
- **Symptom**: a crash on load, or at boot before the main menu (the boot preload reads the newest save), inside
  `FCrc::MemCrc32`. Every save written after some point in a playthrough crashes; older saves still load. It looks
  like save corruption or a render / Lumen crash and is neither.
- **Cause**: the save ends with a table of quest-node names, and its count and the indexes into it are 16-bit. Past
  65,535 distinct names the count wraps (66,400 is written as 864) and only that many names are written. Loading then
  reads past the short table and crashes.
- The table grows as quests run, so a playthrough crosses the limit later than install time: a mod set that is fine
  on a new game can kill a save 30 minutes later.
- **Reading a count** (`names` or `list`): a healthy late-game save shows tens of thousands (long vanilla
  playthroughs: 46,000 to 50,000). A count in the hundreds or low thousands in a mid-game save means it overflowed.
  A brand-new game also has a small count, so compare with older saves of the same playthrough.
- An overflowed save cannot be repaired: the missing names were never written. Remove the mod that pushed it over
  and restore an older save from `Saved/Backups/<SteamID>/<timestamp>/`.

### Rules for mods
- Budget roughly **15k quest-node names for all installed mods together**, on top of a late vanilla playthrough.
- No N x M quest-node fan-out (per location x per tier, per NPC x per state). Drive repeated work through a few
  nodes plus global variables, console-command nodes, or data in prototypes (per-rank blocks) that need no nodes.
- Keep debug and test mods with generated node graphs out of `<mods>` during real play.
- After a large quest-node change, run `list` on a fresh save from a long playthrough.

## Traps
- The game log (`Stalker2.log`) carries nothing about gameplay, quest nodes or mods, so a save is one of the few
  places where quest progress is visible outside the game.
- Most strings in a save carry a length prefix, and a printable length byte sticks to the text in `strings` output
  (`&CantBeKnockedDown...`).
- The save itself can be the crash suspect (pick a save from before a mod ever ran): stalker2-crashes.
- Console commands that save and load (`XExportSaves`, `XLoadLastSave`, `XCallQuickSave`, `XTriggerAutoSave`):
  stalker2-testing.

Read references/format.md before parsing a save yourself, when `names` finds no table, when you need the measured
name counts to judge a save, or when the saves are on Linux.
