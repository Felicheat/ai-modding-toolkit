---
name: stalker2-gamedata
description: Finds where STALKER 2 game data lives and how a value reaches the player or NPCs, covering the cfg record behind a weapon, item, ammo type, armor, NPC loadout, trader stock or in-game name, the damage and armor formula, AI perception, ranks, faction relations, lairs, map markers, game time and vitals. Use when mapping an in-game name to a record, reading GSC's tables, or checking that a mechanic exists before planning a cfg mod.
license: MIT
compatibility: Python 3.8+; repak (see the pack START_HERE.md)
metadata:
  pack: STALKER 2 AI Modding Toolkit
  pack-version: "1.0.0"
  author: STALKER 2 AI Modding Toolkit contributors
  verified-on: "STALKER 2 Steam build 26123434 (game 2.1), Zone Kit 2.1.0"
---

# STALKER 2 game data

## Where to read
- **Readable first:** the Zone Kit's commented TEXT tree, `<kit>/Stalker2/Content/GameLite/GameData/`. Grep it
  first: GSC's comments and file splits explain a lot. It lags the game (the kit's data is often a patch or more
  behind the game's, and files get re-dated without new data), so it never proves a current value.
- **Truth:** the game's own tables. Base: `<paks>/pakchunk0-Windows.pak`, entries
  `Stalker2/Content/GameLite/GameData/...`. Cost of Hope: `<game>/DLC1/S2_DLC1Stalker2-Windows.pak`
  (`.../DLCGameData/DLC1/`). Editions: `<paks>/pakchunk101/102/104-Windows.pak`
  (`DLCGameData/PreOrder|Deluxe|Ultimate/`, with their own item and weapon-setup records). Pull one table with
  `repak get <pak> <entry> > <file>`. Most are binary `.cfg.bin` (decoding: stalker2-cfg); a few, like
  `CoreVariables.cfg`, are text.
- Confirm anything you ship against the game's tables, and again after a game update (stalker2-updates).
- **Grep trap:** some record headers have no space before the colon (`GunM10_HG_NPC: struct.begin`). Grep
  `^Name\s*:` or a record scan misses them.
- Before relying on a field, find it on a vanilla prototype. The parser accepts any key, so a field name that no
  vanilla record carries is dead text (unless a cooked asset of the same mod reads it).

## Names players use
- In-game names exist only in localization. `python scripts/locres_lookup.py <regex>` searches the game's current
  `Game.locres`; `--items` prints item SIDs, also `--key`, `--name`, `--lang`, `--sdk` (the kit's copy).
- Item keys are `sid_items_<LocalizationSID>_name` / `_description`. LocalizationSID defaults to the item SID;
  variants that borrow a name (guard guns) have no key of their own.

## Weapon record chain
Item record (`ItemPrototypes/WeaponPrototypes.cfg`, for example `GunAK74_ST`):
- `GeneralWeaponSetup` -> `WeaponGeneralSetupPrototypes`: fire modes, FireInterval, recoil, dispersion, ammo
  types and projectiles, attachments, upgrades.
- `PlayerWeaponAttributes` -> anim blueprint, VFX, sockets. **Not damage.** Its `DefaultWeaponSettingsSID` names
  the damage record.
- `NPCWeaponAttributes` -> third-person anim, sockets and `AIParameters` per NPC rank.
- Damage: `WeaponData/CharacterWeaponSettingsPrototypes/` (player and NPC files): BaseDamage, ArmorPiercing,
  falloff, bleeding, dispersion. Uniques use `<Name>_Player_WS`; base guns and NPC records use the settings record
  of the same SID.

Read references/weapons-ammo.md before changing a weapon, ammo type, NPC gun or loadout.

## NPC guns and ammo, in short
- NPC shots take damage and AP from the NPC settings record that `NPCWeaponAttributes` resolves to. No cfg field
  picks an NPC's ammo type: loadouts give a gun and a dropped ammo count, never a type.
- Vanilla's way to give NPCs different ballistics on the same gun: a variant item that `refkey`s the base item,
  keeps its LocalizationSID and swaps `NPCWeaponAttributes` (the guard guns).
- Loadouts: `ItemGeneratorPrototypes/DynamicItemGenerator.cfg`, one generator per faction and role.

## Caution: vanilla numbers
The damage formula, the NPC perception values and the day-length formula in this skill are measurements and cfg
readings of the vanilla game on the stamped build, not statements from GSC. Treat them as a starting point: read the
current tables and test in game before relying on one, and again after a game update. Where two sources disagree
(references/damage.md lists the points), the question is open: say so to the user and test it.

## Damage in one line
Damage per hit = BaseDamage x ammo DamageMod x difficulty multiplier x ArmorDifferenceCoefProjectiles ^ (AP -
Strike), with **no clamp**: when AP is above the target's Strike, hits do MORE than base damage (measured in game).
Human NPCs go down after about 60 damage and die on the next hit. Read references/damage.md before changing
damage, armor, mutants or shotguns. It also holds the game's step-by-step hit resolution (bone coefficients, the
deflect roll, explosions, melee, non-strike damage) and the points where that disagrees with the measured formula
(human HP, the deflect roll).

## AI perception
Read references/npc-ai.md before touching hearing, vision, threat, target choice or any `AIPrototypes` table:
the awareness ladder, vanilla radii and scores, threat types, per-archetype fields. Read it too before
changing what NPCs loot from corpses (they pick guns by price, never swap armor, never repair).

## Armor, loot and traders, upgrade trees
Read references/items-armor.md before adding or changing armor or a helmet (and making it show on NPCs), editing a
loot, loadout or trader generator, or placing a cell in an upgrade tree. `Protection` is the player's value,
`ProtectionNPC` the NPC wearer's; a generator's `PlayerRank` gate is the PLAYER's rank, not the wearer's.

## Ranks, relations, lairs, markers
Read references/world-systems.md before work on player-rank gates, faction relations, lair spawns or lair capture,
placed actors on an existing save, or map markers (a marker once shown stays in the save).

## Mod patterns
Read references/mod-patterns.md before making one mod detect another, or showing a temporary HUD icon for an
effect.

## Time and vitals
Read references/time-vitals.md before changing day length, `TimeCoefCurve` or `RealToGameTimeCoef`, or anything
that runs on the game clock (hunger, sleepiness, radiation, trader restock): how game speed is computed and the
vanilla curve.

## Traps
- A unique item pointing at `Gun_X_Player` while its damage lives in `Gun_X_Player_WS` is normal, not a dangling
  link.
- Templates carry behaviour through `refkey`: `TemplateRifleSingleFire` means semi-auto only, so a FireInterval
  there is just a click-speed cap. Check a weapon's setup refkey before judging its DPS.
- Facts marked "inferred" come from field names, not measurement: prove them with a loud test value before
  shipping (stalker2-testing).
- Large overhaul mods often rewrite loadout generators and weapon records: run the conflict check (stalker2-paks)
  before patching the same tables.
- Patching rules (bpatch, refkey, whole-file replace, created records): stalker2-cfg. Console commands for spawning
  items and creatures: stalker2-testing.
