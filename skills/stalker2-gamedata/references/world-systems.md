# Ranks, faction relations, lairs, placed actors and map markers

How these data-driven systems fit together, by cfg. Paths are relative to
`<kit>/Stalker2/Content/GameLite/GameData/`. Unless marked otherwise, facts come from reading the vanilla cfgs in the
kit, not from in-game tests. Cfg syntax, quest-node rules and patching: stalker2-cfg.
Adapted from the Stalker 2 modding harness (github.com/noahsemus/stalker2-modding-harness, MIT, copyright Noah Semus); this part was contributed there by sdwvit.

## Contents
1. Ranks
2. Faction relations
3. Lairs (A-Life spawn points)
4. Lair ownership and A-Life expansion
5. Placed actors on existing saves
6. Map markers

## 1. Ranks
Values `ERank::Newbie`, `Experienced`, `Veteran`, `Master` (`ERank::GetCount` as a sentinel in scenarios).
- Set by quest nodes `EQuestNodeType::SetCharacterParam` with `EModifiedCharacterParam::Rank` across the main quests
  (E03_MQ01, E05_MQ02, E07_MQ05, E12_MQ01, E16_MQ01, ...), and by the console command `XSwitchPlayerRank Veteran`
  (debug OnGameLaunch scripts, a few boss-fight `ConsoleCommand` nodes).
- Gated by the PLAYER's rank:
  - A-Life: region rank bounds (`AIGlobals.cfg`), scenario limits and minimum rank
    (`ALifePrototypes/ALifeDirectorScenarioPrototypes.cfg`), `MutantCorpseProcessFactionPerRank`.
  - Lairs: `SpawnSettingsPerPlayerRanks` in `LairPrototypes.cfg` / `LairPrototypes/GenericLairPrototypes.cfg`; spawn
    actors' `MinSpawnRank` / `MaxSpawnRank`.
  - Loot: generator `PlayerRank`, `Gamepass_ItemGenerators.cfg`, `PackOfItemsGroupPrototypes.cfg`,
    `StashPrototypes.cfg` (`SmartLootParams`), `CorpseClueStashPrototypes.cfg`.
  - Artifacts: per-rank attempts and rarity luck in `CoreVariables.cfg`.
  - Trade: per-rank buy / sell modifiers in `TradePrototypes.cfg` through `EBoolProviderType::PlayerRank` providers
    (`BoolProviderPrototypes/`).
  - Dialogs: `EQuestConditionType::Rank`; contextual actions: minimum rank on `ContextualActionNodePrototypes/`.
  - Zombie allowed weapons (`ObjPrototypes.cfg`).
- A rank change regenerates items near the player (`CoreVariables.cfg` `RegenerateItemsOnRankUpdateRadius = 40000`,
  `RegenerateItemsOnRankUpdateTimer = 10`).
- NPC rank: `Rank` on quest NPC prototypes (`ObjPrototypes/QuestObjPrototypes.cfg`) or per spawn actor.

## 2. Faction relations
`RelationPrototypes.cfg`: relation bands, minimum relation to trade, rollback / cooldowns, deltas per event (damage,
kill, heal, wounded) for characters and factions, faction hierarchy (for example `Duty` under `Army`, `Freedom` under
`FreeStalkers`), special factions (`ArenaEnemy`, `ArenaFriend`, bosses), and initial relations.
- Player baselines: `Mutant`, `Bandits`, `Monolith`, `Militaries`, `Mercenaries` -800; `Duty`, `Freedom`, `Varta`,
  `Neutrals`, `Spark`, `Scientists`, `Corpus`, `Noon` 0; `ArenaFriend` 800.
- Quests change relations with `ChangeRelationships` (1830 vanilla nodes; most `UsePreset = true` with small values;
  115 use direct deltas, many targeting NPC GUIDs).

## 3. Lairs (A-Life spawn points)
`SpawnActorPrototypes/WorldMap_WP/<GUID>.cfg` (one lair per file, `SpawnType = ESpawnType::LairSpawner`),
`LairPrototypes.cfg` + `LairPrototypes/GenericLairPrototypes.cfg`, `ObjPrototypes/*` (archetypes),
`ALifePrototypes/ALifePopulationManagerFactionPrototypes.cfg`, `NPCNeedsPresetPrototypes.cfg`.
- **Spawn actor** (key and `SID` = GUID): position, `LairPrototypeSID`, `LairType` (`ALifeLair`, `RestingLair`...),
  `InitialInhabitantFaction`, `CanBeCaptured` / `CanAttack` / `CanDefend`, `ActiveLair`, `SpawnOnStart`,
  `MinSpawnRank` / `MaxSpawnRank` (the player-rank band the lair exists in), volume GUIDs (`LairCoreVolumes`,
  `LairTerritoryVolumes`, `NavModifierVolumes`), `RestrictionRadius`. 381 lairs on the world map; most other
  world-map entries beside them are their trigger volumes. Cost of Hope has 64 more in `DLCGameData/DLC1/`.
- **Lair prototype:** `Preset.PossibleInhabitantFactions.<Faction>` (`Faction`, `FactionPriority`), each with
  `SpawnSettingsPerPlayerRanks.Newbie..Master` (`MaxSpawnQuantity`, `InitialSpawnQuantityPercent`, respawn timers,
  `WipeRespawnTimeoutSeconds`) and `SpawnSettingsPerArchetypes.<ObjPrototype key>` (`MinQuantityPerArchetype`,
  `SpawnWeight`). No inheritance between vanilla lair prototypes.
- The game picks the block for the **player's** rank. Squads already spawned keep their makeup until they die.
- A placed lair spawns only its `InitialInhabitantFaction`'s list even when the prototype allows several; give a
  single lair a different pool through its own prototype (refkey the vanilla one, restate the faction block).
- `SpawnWeight = 0` archetypes never spawn (for example some Heavy variants at every rank).
- Quest control: `ToggleLairActivity` (`Activate`, `ForceDespawn`) is the only lair node vanilla uses (484 nodes,
  230 lairs); `SpawnLair` appears once. The condition `IsLairOwnedByFaction` exists; there are no lair events.
- NPC speed: `MovementParams` Walk / Run / Sprint (and `MovementSpeedCoef`) only changed off-screen movement;
  on-screen speed follows the locomotion animation (verified in game). A `VelocityChange` effect (vanilla
  `ZombificationVelocityChange`) works but takes hold only when movement is recalculated, and cfgs cannot put a
  permanent effect on a spawned NPC.
- Mutant difficulty knobs: `MutantAttackParams.<Attack>.Cooldown` on the ObjPrototype, and per-mutant
  `AbilityPrototypes/<Mutant>Abilities.cfg` abilities (`AbilityType` Attack, Charge, LongJump, PSYStrike, Throw,
  Summon, Shield...) with `TriggeredCooldowns[*].Duration`, `MinCooldown` / `MaxCooldown`, `CooldownMin` /
  `CooldownMax`. An ObjPrototype points at abilities through `Abilities.<key>.SID`.

## 4. Lair ownership and A-Life expansion
How the game behaves, plus observation in play.
- Ownership lives on the lair (a faction plus an index into its prototype's `PossibleInhabitantFactions`). It changes
  only when a squad finishes a capture step: the generic A-Life `AttachToLair` strategy (used by the Expansion need),
  `AttackLairGoal` (A-Life director `CaptureLairs` scenarios), or the faction-war squad capture. Only these fire
  `OnLairOwnershipHasChanged`; preset changes (`FWChangePreset`, `InitialInhabitantFaction`) change the owner
  silently. Nothing captures by presence alone.
- Hard gate: the new owner must be listed in the lair prototype's `PossibleInhabitantFactions`. Vanilla lists only
  the lair's own faction in most prototypes. Also required: `CanBeCaptured`, the owner hostile to the attacker (most
  hostile band), no enemies within 50 m. Capture distances are cvars: `gsc.fw.Capture_DistSquadLair` 20 m,
  `gsc.fw.PlayerCapture_DistSquadLair` 25 m and `gsc.fw.PlayerCapture_DistPlayerLair` 15 m (player-assisted, allied
  player), `gsc.fw.NoEnemyToLairToCapture` 50 m. Despite the `gsc.fw.` prefix they gate generic A-Life. No level,
  DataLayer or quest check.
- Expansion: a squad sets out when its NPCs' `AI.Need.Expansion` (`NPCNeedsPresetPrototypes.cfg` GoalNeeds) fills.
  Vanilla gives it to the generic human preset (and refkey children), zombies and `MutantGenericNeedsPreset`;
  `MutantGenericNeedsNoExpansionPreset` and `_Guard` presets lack it. Cvars `ALife.ExpandToRestingLairs` /
  `ALife.ReuniteToRestingLairs` default on; the search covers lairs within a built-in 700 m (the cfg
  `ALifeLairExpansionRadius = 500000` is a different value).
- Faction modes: each faction in `ALifePopulationManagerFactionPrototypes.cfg` `Default.Factions` has `Aggressive` /
  `Normal` / `Defensive` `MinLairs` / `MaxLairs` ranges (Bandits 1-5 / 6-20 / 21-900) and
  `ALifeLairExpansionBattleChance`. A lair is an expansion target only while its owner is not `Aggressive`, so a
  faction down to a few lairs has them protected. Factions with no entry there (Scientists, NeutralMSOP, IkarVarta,
  ShevchenkoStalkers...) never expand and never own capturable lairs.
- In play, no capturable hostile lair changed hands in about an hour outside the faction war: the non-war paths are
  rare.
- Faction war (`ESpawnType::FactionWar` spawn actors): `FactionsPresets.<preset>.FactionsParams` is a generic list
  (any number of factions, names resolve through the normal faction registry; an unknown name is dropped silently;
  the `FW_` prefix has no meaning to the game). The war follows only the lairs named by its `Reinforcers`'
  `TargetLair`; it has no radius. Reinforcers (`OwningFaction`, `TargetLair`, `DefendersCount`, squad sizes) and
  UnitSpawners (`OwningFaction`, `Lair`, `SpawnedSquadSize`) are one per (faction, lair). The `FW_*` lair prototypes
  are unused. Not known: how attacks are scheduled, and whether ownership persists in saves.

## 5. Placed actors on existing saves (`SpawnActorPrototypes/`)
Source: the Zone Kit support guide "How to Mod Placeholders" (Phase 2), summarized.
- Every placed placeholder (item, NPC, lair, trigger, stash...) has a SpawnActorPrototype cfg keyed by GUID.
  `SpawnOnStart = true` spawns it at game start or load (world items, loot, open-world NPCs); `false` waits for a
  quest or event.
- The editor writes these cfgs for you: a patched vanilla placeholder becomes a bpatch cfg in
  `<kit>/Stalker2/Mods/<Mod>/Content/GameLite/GameData/SpawnActorPrototypes/<level>/<GUID>.cfg`; a deleted one
  becomes `<GUID> : removenode` in the same place; a new one a cfg under `.../ModGameData/SpawnActorPrototypes/`.
  You can also write them by hand.
- Patched cfgs carry `NodePrototypeAppliedMods { <Mod> { NodePrototypeModVersion = N } }`, which is stored in the
  save. On load, an already spawned actor whose prototype changed (mod applied, version different) is deleted and
  then respawned from the new data (`SpawnOnStart`) or spawned when needed. Bump `N` to force a refresh.
- `PackOfItems` placeholders need a new game to change.

## 6. Map markers
Verified in game, plus how the game stores them.
- A `MarkerPrototype` (`MarkType = EMarkerType::Guide`, `WorldPosition`, `InitDiscoverState = EMarkerState::Explored`)
  plus an `ESpawnType::Marker` spawn actor shows an icon. Its `Title` is not displayed on a Guide marker;
  `EQuestNodeType::SetLocationName` (`Location`, `NewTitle`) labels it, repeatedly if needed.
- **The save keeps a marker once shown.** `ShowMarker` creates a record keyed by the marker SID, copying position,
  type and state once, and can only raise the state. `ShowMarker Discovered = false`, despawning its actor,
  `MarkType = None` or moving it all fail to hide or move it. `Despawn` removes a marker record only through the
  handle stored by its own quest's `Spawn` node. The console commands `XDiscoverMarker`, `XListMapMarkers` and
  `XRevealAllMarkers` are empty in the shipping game. So never `ShowMarker` a marker you may need to remove;
  spawning and despawning from one quest is the only candidate (untested).
