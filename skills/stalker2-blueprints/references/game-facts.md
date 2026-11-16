# Game behaviour a Blueprint mod runs into

Facts the harness mods established in game or from the kit; each says so where it was not checked in game. Player
animation has its own skill: stalker2-animation.
Adapted from the Stalker 2 modding harness by Noah Semus (github.com/noahsemus/stalker2-modding-harness, MIT).

## Contents
- Player class
- Interactions and contextual actions (the campfire sit)
- Input
- Camera
- Player actions, sprint, reload
- Quest doors and signals

## Player class (`PC`, `/Script/Stalker2.PC`; runtime class `BP_Stalker2Character_C`)
- Useful Blueprint surface (snake_case = the editor Python name): `can_use_inventory`, `contextual_action` / `bInContextualAction`
  (writable, but writing it changes nothing by itself), `is_interaction_in_progress`, `is_using_pda`,
  `is_inspecting_artifact`, `start_use_pda(initial_page_type)`, `start_use_backpack()`, `consume_planned_item`,
  `SetMoveVector` / `MovementInputVector` (the game's own move feed), `IsInStaticDialog`, `IsInCinematic` (on `Obj`),
  `ResetInteractionTarget` / `GetInteractionTarget` / `SetInteractionTarget`, `EnableInputAfterInteraction`,
  `DisableInteractions` / `EnableInteractions`, `ToggleFOVAndForegroundRender`, `ChangeMainHandWeapon`,
  `EquipLastHeldItem`, `HasItemInMainHand`, `IsLeftHandBusy`, `IsUsingBackpack`.
- The native move handler drops `IA_LocomotionForward` while `IsInStaticDialog()`, but not look.
- `IsInStaticDialog()` is also true in story cutscenes that run through the dialogue system: guard with
  `NOT (IsInCinematic OR controller.IsLookInputIgnored)`.
- A dialogue ends by distance (`DialogDistance = 5.0` in CoreVariables), possibly while a key is held, so an input
  action's `Completed` can be lost: zero anything the mod fed after a short stale window.
- `CoreVariables.cfg` `MaxInteractionDistance = 200` applies to every interaction. NPC dialogue distance is
  `MinDialogInteractDistance` / `MaxDialogInteractDistance` on the object prototypes (base `[0]`: 75 / 130; about 75 named
  NPCs override it).

## Interactions and contextual actions (the campfire sit)
- A campfire sit is a `PlayerContextualAction` actor (`BP_PlayerContextualAction*` next to `BP_Stalker2Bonfire*`): it sets
  the contextual-action flag, clamps camera yaw and pitch to the actor's limits and pushes `IMC_PlayerCA` at priority
  Exclusive (`InputMappingContextPrototypes.cfg`).
- The game treats the sit as an **interaction in progress** for its whole length. Native PDA and backpack open paths
  refuse while it is (keys and even direct `StartUsePDA` / `StartUseBackpack` calls do nothing). Clearing the interaction
  target ends the sit itself. Hence an "own seated mode": take over after the vanilla sit-in, then
  `ResetInteractionTarget`, clear the flag, `EnableInputAfterInteraction`, `ToggleFOVAndForegroundRender(true)`,
  `DisableInteractions` (hides the seat prompt), and play the pose yourself.
- **Saving stays locked after a contextual action the game did not finish itself.** Ending the sit by
  `ResetInteractionTarget` (even with `RestoreStatesAfterInteraction` / `EnableInputAfterInteraction` after) left "can't
  save now" until a reload; the lock is not in any reflected property of the pawn or controller. Let the sit's own exit
  run: `SetInteractionTarget(<seat component>)` resumes it, `InjectInputForAction(IA_PlayerCAExit)` at idle exits it.
- The vanilla sit's `SaveStatesBeforeInteraction` is only undone by its own exit (weapon half-state otherwise). Calling
  `SaveStatesBeforeInteraction` / `RestoreStatesAfterInteraction` from a mod stores the weapon (hand type 0) but pinned
  the view pitch at its minimum and left WASD dead after standing: do not.
- Binding `IA_PlayerCAExit` (Started) in a mod actor is fine; crashes once blamed on it were post-process anim swaps
  (stalker2-animation).
- While `IMC_PlayerCA` is applied, W/A/S/D/Space/F/Esc all arrive as `IA_PlayerCAExit`, not as movement. If it stays
  applied after a sit (for example after re-entering the vanilla sit from a mod), the player can look but not walk: remove
  it with the local player subsystem's `RemoveMappingContext`.
- The sit montage `MG_fp_ca_gd_bonfire`: In 0-4 s, Idle 4-10 (loops), Out 10-14. The vanilla sit waits for the
  `InteractAction` notify at 3.9996 s: `Montage_JumpToSection("Idle")` skips it and leaves the sit state unset (stuck);
  `Montage_SetPosition(3.93)` skips the sit-down and still fires it.
- Guitar: `IA_GuitarContextualAction` is in `/Game/_Stalker_2/data/input/InputActions/Guitar/`. It only works inside the
  vanilla sit (setting `bInContextualAction` and injecting the action from a mod's own seated mode does nothing).
  `AnimInstancePlayer.GuitarData.bPlayingGuitar` tells when the guitar is out.
- `Obj.ChangeMainHandWeapon(None, ...)` did nothing after a takeover. `Obj.RemoveWeaponFromHands` hides the weapon (the
  hand type stays the weapon's, so idle weapon fidgets and re-equips still play).
- `CppMediator.lerp_player_to_location_and_rotation` and `CppMediator.start_quest_node(sid)` exist (seat placement,
  time-skip leads).

## Input
- The gamepad is read through GameInput.dll, not XInput. A DualSense without Steam Input is not an XInput device.
- Quick slots have no Blueprint-callable entry on `PC` (only `consume_planned_item`, which needs a natively planned item).

## Camera
- `CameraModifier_LookAt` centres the camera on the NPC in dialogue. `FindCameraModifierByClass`,
  `DisableModifier(true)`, `RemoveCameraModifier` per tick removes it.
- Actor yaw drags `ControlRotation`; `bOrientRotationToMovement` rotates the actor on strafe in dialogue. Camera decouple =
  camera `Set Absolute` (rotation) + `Set World Rotation(Get Control Rotation)`, restoring the saved relative rotation
  after.
- Camera-manager view pitch and yaw limits can be set per tick for a seated look clamp.
- `PC.GetControlRotation` (pawn) and `Controller.GetControlRotation` are overridden and return the camera's view, not
  `ControlRotation`; the controller actor's rotation never updates. A pose that drives `jnt_camera` from them is a feedback
  loop (shake, no look). The first-person camera is the `jnt_camera` bone (a root child). The game's look pitch is
  `AnimInstancePlayer.CameraData.ClampedControlPitch`, the explicit time of `fp_bh_stand_lookvertical_idle` (mesh-space
  additive, 1 s: 0 = +90 deg, 1 = -90 deg); it equals the `ControlRotation` pitch exactly. Yaw from `GetControlRotation`
  is fine (the actor yaw follows it).

## Player actions, sprint, reload
- The action system is native: `ActionType` (read with `unreal.ActionType` in editor Python; includes `RELOAD_WEAPON`,
  `UNLOAD_WEAPON`, `UNJAM_WEAPON`, `SPRINT`, `RUN`, `JOGGING`, `USE_CONSUMABLE_ITEM`, `USE_PDA`, `USE_BACKPACK`, ...),
  `PlayerTriggerState` (`RELOAD_TRIGGER`, `SPRINT_TRIGGER`, `SPRINT_STARTED_TRIGGER`, ...), driven by montage notifies
  `AnimNotify_PlayerAction` (END / INTERRUPT) and `AnimNotify_PlayerActionTrigger`. `PC.is_action_active(ActionType)`
  tests whether an action runs. `MagazineReloadState`: DEFAULT, EJECTED, INSERTED, NONE (`Obj.get_current_reload_state`).
- `Obj` (player base) surface: `can_enter_to_sprint`, `is_sprinting`, `is_should_sprint`, `reload`, `reload_weapon`,
  `interrupt_reload`, `finish_reload`, `is_reload_available`, `set_speed_multiplier` / `get_speed_multiplier`,
  `update_movement_speed`, `force_set_sp` / `get_sp` / `get_max_sp` (stamina); `PC.velocity_multimplier` (sic,
  read-write), `PC.on_sprint_released`.
- Vanilla (player reports, to confirm): sprinting cancels a reload (it restarts from the beginning); pressing reload while
  sprinting drops to a run and reloads. No cfg field governs it. `IA_Sprint` and `IA_Reload` (`InputActions/Delayable/`)
  carry no triggers or modifiers, so there is no asset-side blocker: the rule is native. There is no `ReloadIPU`;
  `SprintIPU` is native.
- Blocking an action by data: effect `EEffectType::BlockAnimationActionType` with `BlockAnimationTypes`
  `EActionType::Sprint` (vanilla `BlockSprintEffect`, permanent, used for heavy exoskeletons; `ConcussionBlockSprint` is
  timed, `Duration = 3`). Stamina gates sprint through `StaminaDisableThresholds` (16.1) and overweight state tags.
- Reload speed by data: effect `EEffectType::ReloadingTime`, `ValueMin/Max` in %, negative = faster
  (vanilla has a -25% effect whose SID starts `ReloadingTimeDec`; sleepiness applies +15% / +18.75% to the player). Per weapon:
  `WeaponReloadTimePerAttachment` multipliers (lower = faster) in `WeaponGeneralSetupPrototypes.cfg`, likely shared with
  NPC weapons.
- Applying an effect from Blueprint: no direct function. Candidates, neither tested: `ApplyEffectComponent.apply_effects
  (target)` / `remove_effects` (its effect list is not visible to Python; check the Details panel), or
  `CppMediator.start_quest_node(sid)` on a mod quest node `EQuestNodeType::SetCharacterEffect` (empty target = player, as
  in `QuestNodePrototypes/Benchmark_combat.cfg`; no "remove effect" node exists, use timed effects).
- About 540 first-person reload montages (`MG_*reload*`) sit behind per-weapon `AnimCollection_fp_*` data assets
  (`PlayerFirearmAnimCollection`) and the layer graph `AnimBP_PlayerWeaponLayer` / `AnimLI_PlayerWeapon*`.

## Quest doors and signals (seen in game, at SIRCAA)
- Quest doors (`BP_DoorView`, double glass doors) are World Partition actors in `WorldMap_WP`, not in the quest logic
  levels. Their receivers (Lock / Unlock / Open / ForceOpen `SignalReceiverComponent`s) are found in the kit's
  `WorldMap-WindowsModEditor.pak` by pairing each GUID with its `BndEvt__BP_DoorView_<Receiver>` delegate. Quest
  `SendSignal` node names often lie about the component (`..._ForceCloseReceiver` was a Lock).
- A door signal sent while the player was 40-80 m away did not take effect (E06_MQ02's unlock / open of `nii_Door_05` /
  `_06`; vanilla relies on it); the same signals sent from `Trigger` nodes when the player walks into the area next to
  the door worked. Re-send door signals from a nearby trigger (`TrackBeforeActive = true`) when a mod depends on them.
  (Assumed cause: the door actor is not loaded when the signal arrives.)
- A forced `SetDialog` gated by a `DistanceToPoint` pin (E06_MQ02 Dalin, 4 m) never started for a user, with or without a
  mod; launching the same SetDialog from an extra launcher group 3 s after the previous dialog ends started it (forced
  dialogs start at any distance).
