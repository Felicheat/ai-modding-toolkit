# Releasing a Zone Kit mod: what the cook really ships

For mods cooked with the kit's own `GSCCookMod` (override and NewContent containers). From another team's releases; not re-tested
for this pack. Adapted from the Stalker 2 modding harness by Noah Semus (github.com/noahsemus/stalker2-modding-harness, MIT).

## Unlisted plugin assets ship in the override pak
- Every asset in the plugin's `Content` folder is cooked and shipped, whether the classifier lists
  (`<kit>/Stalker2/SavedMods/PackageClassifier/<Mod>/OverridePackages.txt` and `NewPackages.txt`) name it or not.
- An asset missing from `NewPackages.txt` lands in the OVERRIDE container. Seen twice: four dev-only assets made an override
  pak 614 KB instead of 1 KB, and 25 unlisted animation assets made one 308 KB instead of 1 KB.
- After adding assets to a plugin, add them to `NewPackages.txt` (the kit copy is what the cook reads).

## The pre-release check
1. Delete dev and unused assets from the kit mod, and from both lists.
   - The asset registry's referencers show what nothing uses.
   - Assets loaded by a path string or a soft class path have no referencers: check those by hand.
2. Cook, then list what the override container holds (extract it with `UnrealPak <x>.utoc -Extract <dir>`, or list it with
   `retoc manifest`, stalker2-paks) and check it holds only what it should.

The classifier lists and the other cook rules: stalker2-zonekit.
