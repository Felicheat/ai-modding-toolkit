# Data patterns: detecting another mod, temporary effect icons

Two working patterns built from effects, quest nodes and a small Blueprint. Cfg syntax and quest-node rules:
stalker2-cfg. The Blueprint side (a `ModWorldSubsystem`): stalker2-blueprints.
Adapted from the Stalker 2 modding harness (github.com/noahsemus/stalker2-modding-harness, MIT, copyright Noah Semus); this part was contributed there by sdwvit.

## Detecting another installed mod
Pattern: the **provider** mod puts a flag effect on the player at every world load; the **consumer** mod checks it
with a quest `If`. Verified in game.
1. The provider defines a root effect `<Mod>Installed` (a patch to `EffectPrototypes.cfg`, `{refkey=[0]}`, modelled
   on vanilla `FaustPsyResist`): `Type = EEffectType::FlagEffect`, `bIsPermanent = true`,
   `DuplicationType = EDuplicateResolveType::KeepOld` (the default `KeepAll` stacks a copy per load),
   `ShowUpgradeEffect = false`.
2. The provider applies it from a `ModWorldSubsystem` Blueprint: `OnWorldBeginPlay` -> skip `MainMenuMap` (do not
   gate on `WorldMap_WP`: saves can load into logic levels) -> `Delay 1.0` -> loop until `GetPlayerCharacter(0)` is
   valid -> `Execute Console Command "XApplyEffectOnPlayer <Mod>Installed"`. The SID can be built from the
   Blueprint's own class path (`Get Class` -> soft class reference -> `To String` -> `Get Path` -> `Right Chop 1`
   gives `<Mod>`), so one Blueprint works in any mod. The same Blueprint can run a second console command per load
   (for example `XStartQuestNodeBySID <Mod>_OnWorldLoad`).
3. The subsystem only runs when it is listed in a `*_WorldSubsystemData` asset (the editor's Package Mod writes it).
   `ModAssetSupportSubsystem` finds mod data assets in any folder by file-name suffix: `_LocalizationDatabase`,
   `_ActorReplacementData`, `_ActorDeletionsData`, `_ActorPatchesData`, `_WorldSubsystemData`.
4. The consumer: an `If` node with `ConditionType = EQuestConditionType::Effect`, `ConditionComparance = Equal`,
   `TargetCharacter = AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA`, `EffectPrototypeSID = <Mod>Installed`,
   `RequiredSquadMembers = AllMembers` (vanilla `E08_MQ05_C02.cfg` checks `FaustPsyResist` this way). True =
   installed; False = absent (the effect SID then does not exist, which is fine here).

Rules:
- One action per branch (swapping an item in a container while the player watched left a ghost item).
- Provider-only SIDs go only on the True branch, in their own node (a missing SID nulls the whole node).
- Do not check right at load: the flag lands at least 0.5 s after begin play.
- Only the provider defines the effect. Never remove it.
- Never use a global variable as the flag.

## Temporary effect icons through a camera shake (community method)
A working pattern, not fully verified.
- An effect of `Type = EEffectType::CameraShake` (`CameraShakePrototypeSID`, `ValueMin = ValueMax = 1`,
  `CameraShakeEffectSubtype = ECameraShakeEffectSubtype::AddEffect`) points at a `CameraShakePrototypes.cfg` entry
  (`Type = ECameraShakeType::Constant`, `Scale = 0`, its own `GroupSID`, `CameraShakePath` = a Blueprint).
- A quest `SetCharacterEffect` (target = the player GUID) applies it; the Blueprint (parent `CS_OnShooting`,
  overriding `ReceivePlayShake`) gets a callback when the effect starts and forwards it to a widget or component
  that draws the icon.
- `Scale > 0` makes the player twitch; a dedicated `GroupSID` avoids clashes with other shakes.
- Open: whether effect removal gives a matching callback (hide the icon by separate logic until known), and the
  exact class chain under `CS_OnShooting`.
