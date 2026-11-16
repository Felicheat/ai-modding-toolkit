# Save format, the name limit in numbers, Linux paths

Checked upstream on game 2.0.x saves.
Adapted from the Stalker 2 modding harness (github.com/noahsemus/stalker2-modding-harness, MIT, copyright Noah Semus); this part was contributed there by sdwvit.

## Format
- A `.sav` is a little-endian `uint32` uncompressed size followed by one **Oodle Kraken** stream.
- Oodle ships with the Zone Kit: `<kit>/Engine/Binaries/DotNET/AutomationTool/oo2core_9_win64.dll` (exports
  `OodleLZ_Decompress`, `OodleLZ_Compress`, `OodleLZ_GetCompressedBufferSizeNeeded`; a second copy sits in
  `.../DotNET/UnrealBuildTool/`). A 5 MB save unpacks to about 23 MB.
- The decompressed save is binary Unreal data without field names. It opens with the list of installed paks
  (UTF-16, for example `<ModName>Stalker2-Windows.pak`) and ends with the **quest-node name table**:
  `uint16 count`, then `count` x (`uint16 length` + chars, no NUL) up to the end of the file.
- In the saves checked, the table follows the bytes `GlassToy_14_Christmas\0\0`. `s2sav.py` reads it from there and
  falls back to scanning the last 8 MB for a run of entries that ends at the end of the file and is preceded by its
  own count.
- The save body refers to quest nodes by `uint16` index into that table.
- Most strings in the body are a `uint16` length + chars with no NUL, so a printable length byte sticks to the text
  in a plain strings dump (`&CantBeKnockedDown...` is length 0x26 + text).
- Values (quest states, global variables, inventory) are not decoded by any known tool.

## The name limit: what happens
The table count and the body's indexes are 16-bit. With more than 65,535 distinct names the count wraps (66,400 is
written as 864) and only `count mod 65,536` entries are written. On load, an index past the end of the short table
returns a junk string, and hashing it crashes (the `FCrc::MemCrc32` frame in the crash report). The same read happens
in game when a save is loaded and at boot, where the main menu preloads the newest save.

## Measured counts (one playthrough)
| Save | Names | Result |
|---|---|---|
| long vanilla playthroughs | 46,000 to 50,000 | healthy |
| same playthrough with large quest-node mods | 53,917 | loads; one debug mod alone contributed 20,558 |
| 26 minutes later | 504 to 864 | overflowed, crash on load |
| 10 backups in between | 601 to 1,909 | overflowed |
| 42 older backups | 34,844 to 53,550 | load |

The mods involved had about 32,800 and 16,800 quest nodes; 12,275 of the latter came from one per-location x
per-tier (N x M) node fan-out.

## Linux / Proton
- Saves live inside the game's Proton prefix: `<prefix>/drive_c`, then
  `users/steamuser/AppData/Local/Stalker2/Saved/STEAM/SaveGames/Data/`. `<prefix>` is
  `<steam>/steamapps/compatdata/1643320/pfx` (1643320 is the game's Steam app id; `<steam>` is the library that holds
  the game, two levels above the game folder `steamapps/common/<game>`). `CampaignsSave.sav`, `TempCampaigns/` and
  `Saved/Backups/<SteamID>/` sit at the same relative places.
- Oodle for a native Linux Python: the kit's `Engine/Binaries/DotNET/AutomationTool/liboo2corelinux64.so.9` (same
  exports). `s2sav.py` picks it automatically off Windows.
- The default saves folder off Windows is taken from env `S2_PROTON_PREFIX`, else
  `~/.steam/steam/steamapps/compatdata/1643320/pfx`; or pass the folder to `list`.
