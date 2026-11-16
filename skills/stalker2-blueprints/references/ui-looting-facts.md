# Game UI facts: items, the PDA, pickup and the loot window

What a Blueprint mod can see and call around the PDA, loose items and the loot window. The PDA and looting sections
were read from the kit and not checked in game.
Adapted from the Stalker 2 modding harness by Noah Semus (github.com/noahsemus/stalker2-modding-harness, MIT).

## Items and UI
- Artifact inspection has no input action of its own; it launches from the backpack UI.
- The dialogue skip hint `W_SkipHintView` has native show logic (`SkipHintView` base); the Blueprint is layout + fade only.
- Trading opens inside the dialogue (`IsInStaticDialog` stays true) and takes UI-only input.
- No Blueprint-exposed API opens the PDA or inventory views directly (nothing on UIManagerEx / ViewBase / CppMediator).

## PDA (from kit data and headless reads, not yet checked in game)
- Open: `IA_OpenPDA` (P, pad Special Left; Tap + 1 s Hold triggers) and `IA_WorldMap` / `IA_Journal` / `IA_Note` in
  `IMC_Exploration`, then native `PDAOpenIPU`, then USE_PDA (`ActionType` 24). `PC.StartUsePDA(PDAPageType)` is
  Blueprint-callable (MAP 0, JOURNAL 1, NOTES 2, UPGRADES 3, STATISTIC 4, BESTIARY 5, TUTORIAL 6).
  `OnPDAUseStarted/EndedBP` exist on `PC` but only a pawn override can implement them; mods poll `IsUsingPDA`. Every page
  pushes its own Exclusive context (`IMC_PDA_Map` and so on in `InputMappingContextPrototypes.cfg`), none with look or
  walk rows; close = `IA_UI_PDA_Close` (Esc / M / P / pad B).
- Animation: `AnimCollection_fp_pda`, player `MG_fp_pda` (MainActionSlot, 2.3 s: In 0-1.0, Idle loop 1.0-1.133, Out
  -1.967, OutFast -2.3) + device `MG_pda_fp` on `SK_pda` (`AnimBP_PDA`), posture `AnimBP_Player_TwoHandedItem` (as the
  backpack). `AnimNotify_UseHandItem` at 0.833 s opens the UI. No FOV or camera modifier: the device is simply held 13 cm
  before the eye (fills the view), `jnt_camera` pitches to -20 deg. The device animations are in character space
  (`jnt_item` stays at the root). Unused-looking `MG_fp_pda_EMP_a` / `MG_pda_fp_EMP_a` (3 s, no UseHandItem) hold it about
  34 cm ahead with the world around it.
- UI: `W_PDABookView` (native `PDAView`), a fullscreen UMG view with cursor (like `W_Inventory`). The map is
  `BP_WorldMapScene`'s ortho SceneCapture into `RT_WorldMap` (2048x1024) via `M_WorldMapUIMaterial`. The device's own
  screen material `MI_PDA_Screen` is plain emissive (no texture input).

## Pickup and looting (from the kit only, not yet checked in game)
- Every loose item in the world is one of two generic actors, `BP_StaticItemContainer_C` / `BP_SkeletalItemContainer_C`
  (`/Game/GameLite/Blueprints/Interactable/ItemContainers/`, `CoreVariables.cfg` `StaticItemContainer` /
  `SkeletalItemContainer`), parent `InteractableItemContainer`; visual in its `MeshComponent`, interaction in a native
  `ItemContainerInteractionComponent` plus `ItemContainerHold`. Item cfg `MeshPrototypeSID`, then `MeshPrototypes.cfg`
  `MeshPath`, is the world mesh; the item's own `MeshPath` is the first-person hand mesh.
- Pickup of a loose item is instant (no anim collection on the container Blueprints). Already animated in vanilla:
  artifacts (`BP_Artifact`, `AnimCollection_PickupArtifact`, `MG_FP_Player_AR/Det_ArtifactPickup_01`, MainActionSlot,
  forces `AnimBP_Player_TwoHandedItem`), mutant parts (`MutantLootAnimCollection(WithoutWidget)`,
  `UseMutantLootWithoutWidget = true`, `MG_fp_bh_creaturestash_looting_common`), body carry (`MG_fp_dead_body_pickup`).
  Corpse search and stashes only open the loot window.
- `IA_Interact` (`InputActions/Delayable/`) is mapped in `IMC_Interactivity` (F / gamepad face-left, priority High), not
  `IMC_Exploration`; tap against hold is native (`HoldTime`, `HoldPreventFromDefaultInteractionPercent`).
- `PC.get_interaction_target()` gives the `InteractionComponent` under the crosshair; also `get_interacted_actor` /
  `get_interacted_component`. `InteractionComponent` has delegates `on_interacted_event`, `on_end_interacted_event`,
  `on_notify_interact_event`, `on_montage_ended`; `HoldComponent` has `on_hold_started/finished/interrupted_event`
  (BlueprintAssignable or not: unchecked).
- No Blueprint-visible "item added to inventory" event (`ItemManager` has no members; quest `OnPlayerGetItem` needs a fixed
  item SID; the pawn's `on_next_item_to_take_set_bp` needs a pawn override). The pickup sound
  (`PlayerItemsSounds.sfx_pick_up`, `SFX_Item_Pickup`) is posted natively.
- The loot window is the backpack view: corpse search, world stashes, the player's own stash and the I key all open
  `W_Inventory` (parent native `InventoryNew`; `CoreVariables.cfg` `InventoryWidgetClass`) with input context
  `IMC_Inventory` (Exclusive); traders use `W_Trade` / `IMC_Trade`. The widget Blueprint has no logic (open, take, take
  all, drag and drop are native). A mod can see "window open" with
  `EnhancedInputLocalPlayerSubsystem.HasMappingContext` and read the weight texts (`...InventoryWidget / LootGridWidget`,
  `WeightBar`, `CurrentWeightText`, `W_Text_C`, `TextWidget.GetText`) by finding them by path name. World stashes
  (`BP_Stash*`) are subclasses of the item container actors; the own stash is a native `PlayerStash`.
- Which inventory an item used in the loot window came from has no Blueprint-visible signal: the native hook is the pawn
  event `Obj.OnBeforeUseItem_BP(ItemUID)` (a pawn override), `ItemUID` has no Blueprint queries, and the right-click menu
  (`RightClickMenuWidget`, enum `ERightClickMenu`: Use, Take, TakeAll, Put, Drop, Equip, ...) is native. `IMC_Inventory`
  maps LMB double-click to both `IA_UI_Inventory_UseItem` and `IA_UI_Inventory_LootTakeItem` (native picks by grid); the
  right-click menu has its own Exclusive context `IMC_RightClickContextualMenu`. Usable evidence: the two weight texts
  (unconfirmed in game).
