# NPC AI: perception, targeting, corpse looting

**Caution:** the numbers and formulas here describe the vanilla game as it was read or measured on the build this
skill is stamped with, by a few modders, not by GSC. A game update, the difficulty level or another mod can change
them. Read the current value from the game's own tables and prove it with a test in game before you build on it.

## Contents
1. The awareness ladder
2. Hearing
3. Vision
4. Threat types
5. Choosing a target (EnemyEvaluator)
6. Per-archetype fields, difficulty and rank
7. Corpse looting: what NPCs take from bodies

Tables live under `GameData/AIPrototypes/` (HearingSensor, VisionScanner, VisionTick, FlairSensor, Threat) plus
`EnemyEvaluatorPrototypes`, `CoverEvaluatorPrototypes`, `CombatSynchronizationPrototypes`, `ObjPrototypes`
(`NPCBase`, archetypes) and `CoreVariables.cfg`. Distances are in cm.

## 1. The awareness ladder
- Engine enums: `EThreatAwareness` = Calm, TurnHead, MoveToLocation, SearchEnemy, CallAllies, Battle;
  `EAIThreatState` = Peaceful, SearchForThreat, Combat.
- `DefaultNPC` threat `Actions` thresholds: TurnHead 200, SearchEnemy 350, MoveToLocation 500, CallAllies 700.
- Unidentified sources can push the meter only to `MaxThreatLevelValueBeforeIndentification` = 800 (GSC's
  spelling). Reaching 800 identifies the source by sound alone unless `bIdentifyEnemyByThreatLevel = false`; with
  it false, sound only makes NPCs look, walk and search, and identification needs vision. Mutants set it false and
  use a radius and time instead.
- `DefaultThreatValueFreezeTimeSeconds` 30: the meter holds a long time before it decays (inferred from the
  name).

## 2. Hearing
- `HearingSensorPrototypes` `DefaultNPC` radii: Shot 4600, Explosion 6000, BulletFlyby 200, BulletHit 300, Steps
  1200, Voice 3000. Multiplied by weather (Fogy 0.4, Rainy 0.5) and suppressor multipliers.
- `ReactOnNonEnemySounds` is false on every `QuestNPCBase` descendant (the named camp population, 1,378
  base-game and 320 Cost of Hope records) and true only on the generic `GeneralNPC_` / `GuardNPC_` archetypes.

## 3. Vision
- `MinSignificantVisibilityScore`, `MinCombatSignificantVisibilityScore` (75),
  `MinCombatHoldPositionSignificantVisibilityScore` and `MinCombatSurpriseEnemyLocationSignificantVisibilityScore`
  are 4-entry arrays, identical in every vanilla record. Whether the index is NPC rank or difficulty is unknown
  (untested).
- `LuminanceToDistancePenaltyFactor` 0.5: darkness shortens sight. `TooCloseVisionDistance` and its multiplier
  boost very close detection (inferred from the names).
- `VisionTickPrototypes.PopulateTargetsDelay` = 20, unit unknown.

## 4. Threat types
- `EThreatType`: Sound, Hit, IdentifiedEnemy, UnidentifiedEnemy, PossibleEnemy, Corpse, CrossfireReport, Explosive,
  CharacterTouch, PhysicsTouch, Flashlight.
- Humans have no HP-based retreat: `RetreatActionData` exists only on mutants (32 records) and `RetreatDuration`
  only on Controllers. The human escape system is `EscapeParameters` on `NPCBase` (below).

## 5. Choosing a target (EnemyEvaluator)
- `EnemyEvaluatorPrototypes` coefficients are PENALTIES (the kit comments call them a "fine"): every candidate
  target gets a total and the lowest wins.

## 6. Per-archetype fields, difficulty and rank
On `NPCBase`, inherited by every human archetype:
- `MinReactionTimeToExplosion` / `Max`: 3 / 3.5 s (grenade reaction latency).
- `AgentBehaviourParameters.WeaponHandling`: `MinFireCountQueueScaler` 0.8, `MaxFireCountQueueScaler` 0.5,
  `FarFireQueueDelaySeconds` 0.5, `NearFireQueueDelaySeconds` 1.5, `FireQueueDelayRandomizationFactor` 0.8 (burst
  length and pauses; inferred from names).
- `PerBoneIgnoreDispersionModifiers`: per-bone min/max % chance that a shot ignores weapon spread (Spine 65-75,
  Head 30-45, limbs 40-55, Hips 90-100). The weapon side: `NPCWeaponAttributes`
  `AIParameters.BehaviorTypes.<Rank>.<Short|Medium|Long>` `IgnoreDispersionMinShots` / `MaxShots` (an AK: 4-6, 3-5,
  2-3 shots of a 4-14 burst; shotguns 0; the same for every rank in vanilla). Semantics inferred from names, not
  measured.
- `EscapeParameters`: `FailureChance` 25%, `SquadLostFractionToEscape` 100% (only a squad's last survivor can try to
  escape), `EscapeRadius` 1500. `HumanAmbushParameters` exist too.
- `CoreVariables.cfg`: `StartCombatCooldown` 0.3, `StartThreatCooldown` 0.7 and related values, commented by GSC as
  per-agent desynchronization jitter.

Difficulty and rank:
- `DifficultyPrototypes` has no perception or reaction fields. The only difficulty-keyed AI table is
  `CombatSynchronizationPrototypes`: its Easy, Medium and Hard variants equal Default; the `Stalker` variant halves
  every action cooldown (flank, advance, approach, suppress, grenade, ability).
- Rank scales `SuppressiveFire.MaxScore` (2 / 3 / 4 / 5) and grenade budgets.
- Vanilla `GeneralNPC_<Faction>_<Role>` archetypes differ only in loadout; role behaviour comes from each weapon's
  `CombatSynchronizationScore`.

## 7. Corpse looting: what NPCs take from bodies
| Question | Answer |
|---|---|
| Do NPCs swap to a better gun after looting? | Yes, and "better" means **higher price** only. |
| Do NPCs swap to better armor? | No: no comparison, no equip path; armor is tied to the spawn-time appearance mesh. |
| Do NPCs repair gear? | No: broken gear is never picked up, and no repair is reachable from AI. |

- The AI has one looting goal, `ProcessCorpseGoal`; no armor, artifact or grenade goal exists.
- The scan: the NPC notes the highest price in its own inventory, then walks the corpse inventory (and the corpse's
  dropped weapon, if `AllowWeaponPickupWhenLooting` is on and it lies within `WeaponLootDistance`). A weapon is
  taken when `AllowWeaponPickupBasedOnPrice` is on and its price beats that highest price, or else when its
  durability is above the low-durability percentage; otherwise it is left (reads as a detach or drop, unconfirmed).
  Every other lootable item is taken. That the first item class is "weapon" is inferred.
- **Price is the NPC weapon preference.** Damage, accuracy, calibre, wear and ammo compatibility are not read: an NPC
  trades a working rifle for a pricier one it cannot feed. Changing a weapon's `Cost` changes what NPCs carry after
  a fight.
- **Durability gate:** items with durability (weapons and armor) below the cvar
  `gsc.ItemLootHelper.LowDurabilityPercentage` (default 0.10) are rejected. Before that, quest and unlootable items
  are excluded by flags. Ammo, consumables and artifacts skip the durability test.
- **Armor:** looted non-weapons get no ranking, no protection read and no equip call. The character generator binds
  armor to the appearance mesh at spawn (armor prototypes carry an `NpcMeshGenerator` block for this); there is no
  way to re-dress an NPC at runtime.
- **Repair:** everything named repair is economy or UI (`Repair_Cost`, `BaseRepairCostModifier`,
  `ReputationRepairCostModifiers`, `ArmorSellMinDurability`, `DurabilityBeforeRepair`); `RepairItem` exists only as
  a debug command.
- Knobs: three `AISettings` fields in `AIGlobals.cfg`, parsed by hand with no validation: `WeaponLootDistance`
  300.0, `AllowWeaponPickupWhenLooting` true, `AllowWeaponPickupBasedOnPrice` true (values from the kit's copy,
  which is older than the game: read them from the game's pak before relying on them). Plus the cvar above.
- Not verified: whether a looted armor item is ever equipped by some other system; when and how often an NPC
  decides to loot; artifact auto-equip (`bAutoEquipArtifacts`) and grenade selection (`GrenadePrototypes`).

Section 7:
Adapted from the Stalker 2 modding harness (github.com/noahsemus/stalker2-modding-harness, MIT, copyright Noah Semus); this part was contributed there by sdwvit.
