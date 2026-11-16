# Quest nodes, conditions, dialogs and save limits

How quest-node and dialog cfg tables behave in game: launchers, node types that bite, conditions, getting a mod
quest to run on an existing save, dialog wiring, the effects a quest can use, and the limits a quest mod must stay
under. Vanilla data to copy from: `<kit>/Stalker2/Content/GameLite/GameData/` (`QuestNodePrototypes/`,
`DialogPrototypes/`, `DialogChainPrototypes/`). "Verified in game" marks are the source's own.
Adapted from the Stalker 2 modding harness (github.com/noahsemus/stalker2-modding-harness, MIT, copyright Noah Semus); this part was contributed there by sdwvit.

## Contents
1. SIDs and keys
2. Quest nodes and launchers
3. Conditions
4. Mod quests on existing saves
5. Dialogs
6. Effects a quest can use
7. Performance and save limits

## 1. SIDs and keys
- Two mods defining the same root SID: the result depends on load order. Only the owner defines a prototype;
  others bpatch it.
- A condition or node naming a SID that does not exist (an item from an absent mod) NULLS THE WHOLE NODE, taking
  every other condition in it along. Isolate optional-SID checks in their own node.
- A quest node started by SID from the console (`XStartQuestNodeBySID <SID>`) can sit in any quest and needs no
  quest prefix in its SID.
- Never reuse a spawn actor GUID that already spawned something: a named NPC kept returning as the old generic
  actor from a reused GUID (verified in game). Refreshing placed actors on existing saves: stalker2-gamedata.

## 2. Quest nodes and launchers
- `Launchers` is a list of groups; each `[n]` is one way to start the node (any one group is enough). A group's
  `Connections` list `{SID, Name}` pairs; `Name` names the source's output when it has several (a `SetDialog`
  ending = its last phrase SID) and is empty for plain sources. A walk-in gate is one group holding
  `[event, condition-pin]` (vanilla SQ18 pins).
- A launcher group with `Excluding = true` undoes the node; vanilla E02_SQ01 removes a `SetQuestGiver` marker this
  way.
- **Disable a node**: empty its `Launchers`. Switching `NodeType` to `Technical` does not: a Technical node still
  executes and downstream nodes still react. Reroute anything launched from it to its upstream trigger.
- **Never `LaunchOnQuestStart = true` on an `If` node**: no vanilla If does it, and it crashed the game on load.
  Start guards from a real start node.
- A `LaunchOnQuestStart` node added to a quest that already started never launches on that save (all vanilla
  `BridgeEvent` nodes are LaunchOnQuestStart).
- `Repeatable` nodes fire again on every quest update (about 200 ms) while their launcher counts as done, even after
  the quest's End. Vanilla has no Repeatable `ConsoleCommand` outside launcher-less debug nodes. Put repeating work
  in a quest that ends with a vanilla `End` node and is reset each time it should run.
- `End` with `ExcludeAllNodesInContainer = true` excludes every node of the quest, and an excluded `Spawn` node
  despawns what it spawned (every `SpawnNodeExcludeType`). A quest that spawns a reward (stash, body) must not End
  afterwards; vanilla stash quests (EQ155_P) have none.
- Never chain off a `Spawn` node's output: a node launched by `SpawnHook` did not run on a save that did spawn the
  NPC. Launch follow-ups from the spawn's own launchers plus a `StartDelay`, gated on `IsCreated`.
- `OnTickEvent` runs every frame; use `Technical` nodes with `StartDelay` for polling.
- `SaveGame` node with only launchers = checkpoint save (vanilla `EQ50_SaveGame_StartEQ`).
- Ending quests: `XEndQuestBySID` from a `ConsoleCommand` inside the quest did not end it; vanilla `End` does.
  `XResetQuestBySID` alone restarts a quest (adding `XStartQuestBySID` started it twice).
- `ItemRemove` on an item the player lacks does not fail the chain.
- Rank: `SetCharacterParam` with `Params [0] { ModifiedCharacterParam = EModifiedCharacterParam::Rank,
  ChangeValueMode = EChangeValueMode::Set, Rank = ERank::Experienced }` (vanilla `E05_MQ02`).
- Relationships: `ChangeRelationships` with `UsePreset = true`, `RelationshipValue` 0 = enemies, 2 = neutral,
  3 = friends, player in `FirstTargetSID` (verified in game). `EDialogAction::Attack` on a dialog line does not make
  a neutral NPC hostile; add `ChangeRelationships` (value 0) and `ResetAI`.

## 3. Conditions
- `Conditions` holds groups `[0]`, `[1]`... joined by `ConditionCheckType = EConditionCheckType::And`. Put ONE
  CONDITION PER GROUP: two conditions in one group behaved as "either" (vanilla
  `SQ18_SetDialog_SQ18_Comment_Gnutyj_Sum_Coming_Pin_2` shows the layout; verified in game).
- An `If` on a global variable that does not exist fires True whatever it compares.
- `IsCreated` (`ConditionComparance = Equal`, `TargetPlaceholder = <GUID>`) tells whether an NPC exists. Bridge
  conditions on vanilla hub nodes (`OnNPCCreateEvent`, `Phase2`, `Technical_*`) read False on a save long past them;
  vanilla never reads those nodes' state. Bridges on your own quest's nodes work.
- `DistanceToPoint` (`TargetPoint` X/Y/Z, `NumericValue` in cm) is vanilla's usual distance check and does not
  depend on the NPC being loaded.
- `IsLairOwnedByFaction` (`TargetLairPlaceholder = <lair spawn-actor GUID>`, `Faction`) works outside the DLC1 war.
- Player GUID in `TargetCharacter` / `TargetQuestGuid`: `AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA`.

## 4. Mod quests on existing saves (verified in game)
- A rootgraph `XStartQuestBySID` launcher did not start a mod quest on a save from before install. On every world
  load, check `If` + Bridge on `<Quest>_Start` and on False run `ConsoleCommand XStartQuestBySID <Quest>`. Progress
  made while the quest was not running is never recorded.
- World load is too early: a chain started at load did nothing, the same chain a minute later worked. Use
  `Technical` `StartDelay = 5`, retry every 5 s while `IsCreated` is False, once more at 30 s.
- Start a node of another quest at the right moment with `ConsoleCommand XStartQuestNodeBySID <SID>`; a parallel
  `SetTimer` of the same length raced the original.
- Debug a broken chain: start each node in turn with `XStartQuestNodeBySID` and ask the user one yes/no question
  per step. `ShowFadeScreen` message streams go by too fast to read.

## 5. Dialogs
- Before anything else on "the game ignores my cfg": diff the mod's cfg against vanilla cfgs of the same kind
  (which fields vanilla always sets, which values vanilla never uses). Most such bugs show there in one step:
  dialog lines with empty `AKEventName` / `AKEventSubPath`, which no vanilla phrase has, played no voice.
- Adding a topic to a hub NPC: use `OverrideDialogTopic = EOverrideDialogTopic::None` (`Info` is the NPC's single
  info slot; the hub refills it). Put the `SetDialog` nodes into the HUB QUEST itself (`QuestSID = <Hub>`, e.g.
  `RookieVillage_Hub`), launched by the nodes that attach the NPC's vanilla topics: a hub re-attaches its NPCs'
  topics per story phase. Hear the result back with `OnInfotopicFinishEvent` (`EventType = OnDialogFinished`,
  `InfotopicLastPhrases` = last phrase SID; vanilla E16_MQ02). Verified in game.
- Quest-giver marker: `EQuestNodeType::SetQuestGiver` (`TargetQuestGuid` = NPC, `MainQuest = false`).
- Launch from a `SetDialog` ending by `Name = <last phrase SID>` plus `Interrupt`. `OutputPinNames` (`End`,
  `End_1`...) are labels only; launchers on them never fire.
- `NextDialogOptions [0] { NextDialogSID = , Terminate = true }` on the last line closes the dialog; with
  `Terminate = false` it stays open until Esc. A line has no on-screen time of its own (split long lines).
- Forced dialog (`StartForcedDialog = true`, `OverrideDialogTopic = Forced`) starts at once at any distance.
- Comment (spoken, no window): chain `DialogOnTheGo = true`, `IsPCDialogMember = false`; phrases
  `Unskippable = true`, `MainReply = false`; `SetDialog` `IsComment = true` (vanilla
  `SQ18_Comment_Gnutyj_Sum_Coming`; not verified for a mod-added chain).
- Branch on a global variable with a dialog `If` (`DialogMemberIndex = -1`, `NextDialogOptions { True {...}
  False {...} }`, vanilla `RSQ05_Dialog_Sich_C11_Finish_If_1`). GlobalVariable conditions on reply options showed
  every variant.
- `EDialogAction::GetItem` (`DialogActionParam` item SID, `ItemsCount`) gives the player an item.
- Named NPC: an `NPCPrototypes.cfg` entry (refkey a generic one) with `NameTextKey`, an ObjPrototype with
  `NPCPrototypeSID = <X>`, and `<X>` as dialog member. `SetAIBehavior` stay with `GoalPriority = HigherThanCombat`
  keeps an NPC from fighting back; `HigherThanALife` holds it in place but combat wins.

## 6. Effects a quest can use
- Quests can test whether an effect is present (`EQuestConditionType::Effect`), never its magnitude.
- A permanent flag: `Type = EEffectType::FlagEffect`, `bIsPermanent = true`. Base `[0]` has
  `DuplicationType = KeepAll`, which stacks a copy per apply; set `EDuplicateResolveType::KeepOld` for anything
  applied repeatedly.
- Consumable buff HUD (number or bar) is set ON THE CONSUMABLE ITEM, in `ItemPrototypes/ConsumablePrototypes.cfg`
  (and `QuestItemPrototypes.cfg` for quest consumables): `EffectsDisplayTypes`, parallel to `EffectPrototypeSIDs`.
  `EEffectDisplayType::EffectLevel` = Weak / Strong / Max bar; `EEffectDisplayType::ValueAndTime` = value +
  duration. `ShouldShowEffects` (bool per entry) hides an effect. `ShowUpgradeEffect` / `ShowUpgradeEffectValue` in
  `EffectPrototypes.cfg` only drive the upgrade screen.
- Console: `XApplyEffectOnPlayer <EffectPrototypeSID>` (console use: stalker2-testing).

## 7. Performance and save limits (verified in game or profiled)
- A running quest costs game-thread time per node: one always-on quest of about 14,000 nodes, and a 4,100-node
  quest left running, each dropped the game to a few frames per second. Bulk work belongs in on-demand quests that
  End.
- Each `XResetQuestBySID` costs about 10 ms of game thread (it walks the UObject array under a lock): never per
  item or in a loop. Ending quests from the
  console while their `ConsoleCommand` nodes were mid-flight crashed the game.
- **Saves store quest-node names in a table with a 16-bit count and indices.** Past 65,535 names the save is written
  truncated and crashes on load (or at boot). A late vanilla playthrough already holds 46,000 to 50,000, leaving
  all mods together roughly 15,000. No N x M node fan-out.
