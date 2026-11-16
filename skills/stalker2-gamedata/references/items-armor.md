# Armor, NPC appearance, item generators and upgrade trees

How these data-driven systems fit together, by cfg. Paths are relative to
`<kit>/Stalker2/Content/GameLite/GameData/`. Unless marked otherwise, facts come from reading the vanilla cfgs in the
kit, not from in-game tests. Cfg syntax and patching: stalker2-cfg.
Adapted from the Stalker 2 modding harness (github.com/noahsemus/stalker2-modding-harness, MIT, copyright Noah Semus); this part was contributed there by sdwvit.

## Contents
1. Armor and helmets
2. NPC appearance (worn armor and helmet meshes)
3. Item generators (loot, loadouts, traders)
4. Weapon and armor upgrade trees

## 1. Armor and helmets
`ItemPrototypes/ArmorPrototypes.cfg` (body armor and helmets in one file).
- Templates: `TemplateArmor` (body: `ItemSlotType = EInventoryEquipmentSlot::Body`, grid 2x3, `ArtifactSlots = 2`)
  and `TemplateHelmet` (refkey of TemplateArmor: `Head`, grid 2x2, `ArtifactSlots = 0`,
  `PhysicsInteractionPrototypeSID = Helmet`). New armor: refkey the template or a similar armor, restate only the
  changes.
- `Protection` (player) and `ProtectionNPC` (NPC wearers, usually higher) per damage type: `Strike`, `Radiation`,
  `Burn`, `Shock`, `ChemicalBurn`, `PSY`, `Fall`. How protection enters damage: the damage reference of this skill.
- `bBlockHead`: the armor occupies the head slot (heavy, scientific, exoskeleton and many NPC suits).
  `bPreventFromLimping = true` only on the exoskeleton family, which also carries `EffectPrototypeSIDs` (for example
  the sprint block). `IncreaseSpeedCoef` / `NoiseCoef` are set only in the template.
- `VoiceModulatorSID = Gasmask` muffles the wearer's voice (for example `Heavy2_Military_Armor`,
  `Heavy_Varta_Helmet`).
- `Invisible = true` hides NPC-only suits (most `NPC_*` armors) from player-facing UI.
- `MeshPrototypeSID` -> `MeshPrototypes.cfg` is the dropped / inventory static mesh only. What an NPC wears visually
  comes from `NpcMeshGenerator` and the body-mesh system (section 2).
- Upgrades: `UpgradePrototypeSIDs` plus `SectionSettings`, 5 entries keyed by `EUpgradeTargetPartType` (`Barrel`,
  `Handguard`, `Body`, `PistolGrip`, `Stock`), each with `SectionIsEnabled` and UI layout. An upgrade on a section
  that is not enabled cannot be reached in game. `PreinstalledUpgrades` is used once in vanilla
  (`Anomaly_Scientific_Armor_PSY_preinstalled`).
- `ArmorSoundType` appears both as `AkSwitchValue'...'` and `/Script/AkAudio.AkSwitchValue'...'`; same value.

## 2. NPC appearance (worn armor and helmet meshes)
Data-only, no equip callback. Chain:

| cfg | Role |
|---|---|
| `ObjPrototypes/GeneralNPCObjPrototypes.cfg` (+ faction files) | `MeshGeneratorPrototypeSID` per NPC template |
| `MeshGeneratorPrototypes.cfg` | `*_MeshGenerator`: named slots (`BodyArmor`, `Face`, `Head`, `Mas`, `Bpa`, `Hea`...) with weighted `BodyMeshSID` lists |
| `BodyMeshPrototypes/AttachMeshPrototypes.cfg` | each `BodyMeshSID`: `MeshPath`, `BodyMeshType`, `AdditionalMesh`, material variations, optional `ItemPrototypeSID` |
| `ItemPrototypes/ArmorPrototypes.cfg` | item -> `MeshPrototypeSID` |
| `MeshPrototypes.cfg` | dropped / inventory static mesh |

- The generator rolls one compatible combination across slots. `BlockingSlots` and `BlockingBodyMeshes` on a
  candidate rule out other slots / meshes once it wins (a mask face blocks `Head`, `Hea`, `Bpa`, `Fbe`; plain faces
  list the mask variants they exclude).
- **`ItemPrototypeSID` on an attach mesh gates it:** the entry is eligible only while the NPC has that item
  equipped (for example several `Fac_*_mas_*` faces with `ItemPrototypeSID = Light_Duty_Helmet`, one per body /
  backpack combination). It applies to loadout and picked-up items alike.
- A new helmet that should show on NPCs needs: the armor item, a `MeshPrototypes` entry, one or more attach meshes
  with `ItemPrototypeSID = <item>` and `BodyMeshType = EBodyMeshType::Head`, and those meshes added to the relevant
  generators' slots with blocking rules. Without an attach mesh it equips fine and shows nothing.

## 3. Item generators (loot, loadouts, traders)
`ItemGeneratorPrototypes/DynamicItemGenerator.cfg` (general), `QuestItemGeneratorPrototypes.cfg` (quest / NPC),
`ItemGeneratorPrototypes.cfg` (base, `EmptyQuest`), `QuestStashBodyItemGeneratorPrototypes/`,
`QuestNPCGeneratorPrototypes/`.
- A generator: `SID`, `ItemGenerator` (list of category entries; indexed, `[*]` or named), optional
  `MoneyGenerator`, `RefreshTime`, `SpecificRewardSound`.
- Entry: `Category = EItemGenerationCategory::*` (`WeaponPrimary`, `WeaponPistol`, `WeaponSecondary`, `BodyArmor`,
  `Head`, `Consumable`, `Ammo`, `Attach`, `Artifact`, `Detector`, `NightVision`, `Junk`, `SubItemGenerator`, `None`),
  `PlayerRank` and `Diff` gates (one value or comma list; absent = all), trader-only `ReputationThreshold`,
  `RefreshTime` (for example `1h`), `bAllowSameCategoryGeneration`, and `PossibleItems`.
- `PossibleItems` entry: `ItemPrototypeSID` (or `ItemGeneratorPrototypeSID` under `SubItemGenerator`, composing
  generators), `Weight` (relative priority among entries, loadouts), `Chance` (independent roll, `1` = always,
  consumables), `MinCount` / `MaxCount`, `MinDurability` / `MaxDurability`, `AmmoMinCount` / `AmmoMaxCount` (vanilla
  also has 3 typos `AmmoMaxcount`), `bRequireAmmo`, `bRequireWeapon`, `bUnloadedWeapon`, `Attaches`, `Upgrades`.
- **`PlayerRank` is the player's rank,** not the wearer's: an NPC generator hands out gear by the player's progress.
- Name families: `GeneralNPC_*`, `GuardNPC_*`, `GeneralZombie_*` (NPC loadouts), `Trader_*`, `Bartender_*`,
  `Medic_*`, `Technician_*` and per-location vendors. Medic stocks are
  `Medic_<Location>_Consumables_ItemGenerator`.
- Quest generators usually `refurl` / `refkey` a dynamic one and override categories; resolve the base first. Quest
  nodes reference them through `QuestItemGeneratorSID`.
- Add an item to a trader: bpatch the generator -> `ItemGenerator` -> the right `[n]` -> `PossibleItems`, adding a
  named entry (`ItemPrototypeSID`, `Chance`, `MinCount`, `MaxCount`). (The weapons reference of this skill marks
  appending `[*]` entries to a generator through bpatch as unverified: test the result in game.)

## 4. Weapon and armor upgrade trees
`UpgradePrototypes.cfg` (cells, prerequisites, blocking, lines), `WeaponData/WeaponGeneralSetupPrototypes.cfg` (fire
modes, per-weapon `UpgradePrototypeSIDs`), `NPCPrototypes.cfg` (technician offers and `Enabled` states),
`QuestNodePrototypes/Kazkovy_Hub.cfg` (toolbox unlocks), `EffectPrototypes.cfg` (fire-mode replacement effects).
- `HorizontalPosition` is zero-based (0 / 1 / 2 = tiers 1 / 2 / 3); `UpgradeTargetPart` picks the part's tree;
  `VerticalPosition` the top or bottom cell. Check the cell against the weapon's own `UpgradePrototypeSIDs` (ignore
  `IsModification` entries, shown separately).
- `RequiredUpgradePrototypeSIDs` listing both mutually exclusive previous-tier upgrades means "either one".
- Vanilla top cells connect down (`ConnectionLines = [EConnectionLineState::Down]`), bottom cells up (`Top`); the
  template default is `None`.
- An upgrade targeting a part the weapon has no non-modification branch for most likely does not display (seen on a
  `Body` fire-mode upgrade for the SVU; from config analysis, not checked in game).
