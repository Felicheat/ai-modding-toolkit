# Weapons, ammo, NPC guns and loadouts

## Contents
1. The weapon record chain in full
2. Edition weapons
3. Ammo
4. Upgrades
5. NPC guns
6. Loadouts
7. From an in-game name to every record

## 1. The weapon record chain in full
| Link (field on the item) | Table | Holds |
|---|---|---|
| item itself | `ItemPrototypes/WeaponPrototypes.cfg` | `LocalizationSID`, the three links below |
| `GeneralWeaponSetup` | `WeaponGeneralSetupPrototypes` (most uniques end in `_GS`) | fire modes, FireInterval, RecoilParams, DispersionParams, ammo types and projectiles, attachments, upgrade list |
| `PlayerWeaponAttributes` | `WeaponData/WeaponAttributesPrototypes/PlayerWeaponAttributesPrototypes.cfg` | anim blueprint, VFX, sockets, `DefaultWeaponSettingsSID` (the damage record) |
| `NPCWeaponAttributes` | `.../NPCWeaponAttributesPrototypes.cfg` | third-person anim, sockets, `AIParameters` (behaviour per NPC rank) |
| damage | `WeaponData/CharacterWeaponSettingsPrototypes/PlayerWeaponSettingsPrototypes.cfg`, `NPCWeaponSettingsPrototypes.cfg` | BaseDamage, ArmorPiercing, falloff, bleeding, dispersion, UI cards, FireLoudness (NPC hearing), EffectiveFireDistance and CombatSynchronizationScore (AI use) |

- Uniques name their damage record `<Name>_Player_WS` through `DefaultWeaponSettingsSID`. Base guns and NPC
  records have no `DefaultWeaponSettingsSID` and use the settings record with the same SID.
- Templates carry behaviour through `refkey`. `TemplateRifleSingleFire` = semi-auto only. Read the setup record's
  refkey chain before judging fire rate or DPS.
- Projectile speed lives in `ProjectilePrototypes`; physical-material penetration values in
  `ImpactPhysicalMaterialPrototypes`.

## 2. Edition weapons
- PreOrder, Deluxe and Ultimate items live in `pakchunk101/102/104-Windows.pak` under `DLCGameData/<Edition>/`,
  with their own setup records copied from a base gun (example: the Deluxe Monolith AR416 is
  `Gun_RifleMonolith_AR`, setup `Gun_Monolit_AR_GS`, note the spelling). They share the base gun's player and NPC
  damage records.
- So a mod that changes a base gun's setup (recoil, fire modes, attachments) must patch the edition copies too, or
  the edition gun keeps vanilla behaviour. Whether patch files placed under `DLCGameData/<Edition>/` are honoured in
  game is unverified: test with a loud value first.

## 3. Ammo
- `ItemPrototypes/AmmoPrototypes.cfg`. SIDs are `<caliber><type letter>`: `D` Default, `A` ArmorPiercing, `S`
  Supersonic, `E` Expanding (`A556D`, `A545A`).
- Vanilla modifiers: AP rounds `ArmorPiercingMod` +0.5 and `DamageMod` 0.98; Expanding `ArmorPiercingMod` -0.7 and
  `DamageMod` 1.9.
- Buckshot `A012D` is the only buckshot item (Cost of Hope adds no ammo records). `FractionCount` 12 x `DamageMod`
  0.084 makes a full pattern about 1.0 x BaseDamage; there is no per-pellet multiplication (measured in game).
- Whether NPC shotguns read `A012D`'s AP modifier is unverified.

## 4. Upgrades
- Mostly percentage effects in `EffectPrototypes` (the `ArmorPiercingPos...Effect` family and similar).
- Armor upgrades are percentage `ProtectionStrike` effects as well (`ProtectionStrike1` to `9` and per-suit
  effects, about +5% to +45% per slot).

## 5. NPC guns
- NPC shots take damage and AP from the NPC settings record that the item's `NPCWeaponAttributes` resolves to.
  No cfg field picks an NPC's ammo type (not verified in the engine).
- Boss guns get a stronger record instead of better ammo: Strelok's AK is `GunAK74_Strelok_ST_NPC` (AP 4).
- Vanilla pattern for different NPC ballistics on the same gun: `GuardGunAK74_ST` `refkey`s `GunAK74_ST`, keeps
  its LocalizationSID and swaps `NPCWeaponAttributes` to `GuardGunAK74_ST_NPC` (BaseDamage 500); only guard
  loadouts carry it.
- NPC accuracy is more than weapon dispersion: per-rank ignore-dispersion shots and per-bone odds (AI reference of
  this skill).

## 6. Loadouts
- `ItemGeneratorPrototypes/DynamicItemGenerator.cfg`: one generator per faction and role,
  `GeneralNPC_<Faction>_<Role>_ItemGenerator` and `GuardNPC_...`.
- Entries are `[*]` blocks per `Category`, gated by `PlayerRank` and `Diff`, each with weighted `PossibleItems`.
- Vanilla role archetypes (`GeneralNPC_<Faction>_CloseCombat`, `Recon`, `Stormtrooper`, `Sniper`, `Heavy`) differ
  only by `ItemGeneratorPrototypeSID`, so a role IS its loadout: CloseCombat carries shotguns, Recon SMGs,
  Stormtrooper rifles, Sniper adds marksman rifles, Heavy adds a machine gun. Role behaviour then comes from each
  weapon's `CombatSynchronizationScore`.
- Large overhaul mods often rewrite these generators, so loadout patches meet real conflicts: check with
  stalker2-paks before shipping.
- Appending nested `[*]` entries to a generator through `{bpatch}`: unverified. (The armor and generators reference
  of this skill gives the generator fields in full and the bpatch route for adding a named entry to a trader.)

## 7. From an in-game name to every record
1. `python scripts/locres_lookup.py --items "<name regex>"` gives the item SID.
2. Grep the kit's text tree for `^<SID>\s*:` to read the item, then follow `GeneralWeaponSetup`,
   `PlayerWeaponAttributes` (-> `DefaultWeaponSettingsSID`) and `NPCWeaponAttributes`.
3. Confirm the values in the game's `.cfg.bin` before shipping (the kit lags the game).
4. Spawn the gun to test it: stalker2-testing (a spawned gun has no upgrades).
