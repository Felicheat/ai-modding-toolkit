# Player animation: structure, safe changes, pose tables, vanilla behaviour

Adapted from the Stalker 2 modding harness by Noah Semus (github.com/noahsemus/stalker2-modding-harness, MIT).
From its dialogue, campfire and looting mods; not re-tested for this pack.

## Contents
- Structure
- Post-process anim instance
- Dynamic montages and slot groups
- Pose tables
- Which montage is playing
- The game's inventory (backpack) animation
- Vanilla behaviour worth knowing
- Dead ends

## Structure
- The player mesh's main anim instance is `AnimBP_Player` (parent `AnimInstancePlayer`, native). Its native update pushes
  about 23 BlueprintReadWrite data structs (`StateData`, `LocomotionData`, `CameraData`, ...) into the main instance only.
  The struct members are mostly NOT Blueprint-writable (`Set members in AnimPlayerStateData` exposes only
  `CombatIdleDuration`), so a mod computes its own values and reroutes bindings instead of writing them.
- Weapon and hands poses are composed in linked anim layers (`WeaponLayer`, for example `AnimBP_player_bh` for bare
  hands; weapon-specific layer Blueprints for guns). Idle and Moving poses come out of that layer.
- Slots: `FullBody` sits after everything in `AnimBP_Player` (`PreFullBodyPose` cache, Slot FullBody, LayeredBoneBlend with
  no layers, out), so any FullBody montage hides the arm-action layers (`PreActionFullbodySlot`, then `MainActionSlot` /
  `UpperBody` inside the bh layer). Item use (eat, drink, PDA, backpack) plays in MainActionSlot / DefaultSlot / UpperBody.
- Dialogue gestures are montages on the main instance (`IsAnyMontagePlaying` true). Linked layers with
  `bUseMainInstanceMontageEvaluationData` read montage data from the component's main instance.
- The camera hangs off `jnt_camera` (child of `jnt_root`, not the head). With `bUseControllerRotationYaw` off only the aim
  offset turns, not the camera.
- Curves such as `AdditiveMovingUpperBody` read 0 on all instances (not a usable signal).

## Post-process anim instance
A mod AnimBlueprint (parent `AnimInstancePlayer`, not plain `AnimInstance`) attached with `SetOverridePostProcessAnimBP`
and switched with `SetDisablePostProcessBlueprint`. A disabled post-process instance is neither updated nor evaluated.
- Copy the main instance's data structs onto it every frame, and set its `WeaponLayer` node's Instance Class statically
  (`LinkAnimClassLayers` at init did not take).
- **Attach exactly once per world, about 1 s after the pawn appears, outside any dialogue or interaction**, with the
  mesh-swap trick: save hidden bones, override None, `Set Skeletal Mesh Asset` (another mesh), override = yours, mesh
  back, `ToggleFOVAndForegroundRender(true)`, re-hide the saved bones. Armour changes re-create it.
- **Disabling it leaves its last frame's notifies firing.** The mesh still dispatches queued anim events on a disabled
  post-process instance every frame, and only an update or `InitializeAnimation` empties its notify queue. Switched off
  on a frame where its walk played a footstep (`AnimNotify_AnyFootOnGround` on the `ar` walk / run sequences), that
  footstep repeats every frame until it is switched on again ("nonstop footsteps after a conversation"). Re-enabling (the
  setter, also behind a `SET bDisablePostProcessBlueprint` node) re-initialises the instance and resets the queue: one
  tick after switching it off, switch it on and straight off again. Its linked layer instances keep being updated, which
  resets their own queues.
- Live per-bone offsets belong here: `Transform (Modify) Bone` nodes bound to variables.

## Dynamic montages and slot groups
- A dynamic montage in the mod's own slot group works: for example a looping additive made from a game sequence
  (`AnimSequence` duplicated, tracks rewritten from Python, additive against a reference frame) played in `FullBody` with
  its own slot group, so UpperBody and action montages do not cancel it. Heal it with `IsPlayingSlotAnimation`.
- **One montage per slot group, whatever `bStopAllMontages` says**: a montage ASSET in `FullBody` started with
  `Montage_Play(bStopAllMontages = false)` right after a paused dynamic FullBody pose table stopped the table. Two offset
  tables cannot stack in one group.
- Slot groups of the player skeleton (from every player montage, `get_group_name` + `get_montage_slot_names`):

| Group | Slots |
|---|---|
| DefaultGroup | DefaultSlot, LeftHand, RightHand, CameraSlot, WeaponSlot, DeathSlot |
| ActionGroup | MainActionSlot, SecondaryActionSlot, GadgetActionSlot / GadgetActionAimSlot |
| UpperGroup | UpperBody |
| FullBodyGroup | FullBody |
| PreActionGroup | PreActionFullbodySlot |
| CutsceneGroup | CutsceneSlot |

- A montage in one group does not stop the others.
- Slots in the `AnimBP_player_bh` WeaponLayer, in order: MainActionSlot, RightHand / LeftHand (hand masks), CameraSlot,
  DefaultSlot, then the "Additional" input on the left hand. Only `FullBody` in `AnimBP_Player` comes after all of them.
- Item animations do not all use `MainActionSlot`: the antirad injector plays in the bh layer's `LeftHand` slot (after
  MainActionSlot, `left_hand_blend_mask`).
- Rebinding pins inside an `AnimBP_Player` override (`Select Float` on your flag, rules OR'd with your flag) works but
  makes the asset a conflict magnet for other mods.

## Pose tables (working)
- A seated pose that follows the view without an AnimBlueprint: bake a sequence whose keys are the pose per view angle
  (yaw rows x pitch keys, 30 frames per second), play it with `PlaySlotAnimationAsDynamicMontage` in `FullBody` and set its position
  every tick from the view (the actor must tick before the mesh: `AddTickPrerequisiteActor`).
- The montage does not stay paused (`Montage_SetPlayRate(0)` did not hold): set position = target - DeltaSeconds x rate
  so the anim update lands on the target.
- A plain pose also overrides `jnt_camera`, so bake the look pitch into it (the pitch source is
  `AnimInstancePlayer.CameraData.ClampedControlPitch`); an additive pose passes the game's look through.
- A dynamic pose-table montage starts at frame 0 unless `InTimeToStartMontageAt` is set: blend it in from the right
  frame, or the first frames blend a wrong pose.
- Item, PDA and backpack montages (`MainActionSlot`; mods may use `DefaultSlot` / `UpperBody`) key the hips 7.4 cm /
  19 deg away from `fp_bh_idle_stand`, the same as `fp_ar_idle_stand`: build an additive meant to run under items on
  `fp_ar_idle_stand`, or the legs swing while an item plays. Root children (`jnt_item`, `jnt_camera`, IK roots) must move
  with a lowered pelvis.
- An actor ticking in `TG_PostUpdateWork` runs after this frame's animation update: a montage started there poses the mesh
  from the next frame, so show what it brings in (a weapon, a spawned mesh in its reference pose) 2 ticks later.

## Which montage is playing
- Ask `IsSlotActive(<slot>)` which kind of montage runs. `GetCurrentActiveMontage` returns the most recent one only, and
  from an actor's tick it is not reliable for "which item is playing" (an item used from the backpack was never returned;
  the mod's own pose montage was).
- Bind `AnimInstance.OnMontageStarted` instead (`K2Node_AddDelegate` + custom event, once per anim instance) and keep the
  last montage it reports.
- Dynamic montages from `PlaySlotAnimationAsDynamicMontage` with a big LoopCount have a huge `GetPlayLength`: filter them
  out by length.
- `Montage_SetPlayRate` / `Montage_IsActive` / `Montage_IsPlaying` with a None montage act on ANY montage.

## The game's inventory (backpack) animation
- All native: `PC.StartUseBackpack` puts the weapon or hands away (an "unequip" montage, about 0.45 s), makes the backpack
  a hand item (`HandItem` BACKPACK; `AnimCollection_fp_Backpack`: `PlayerAnimBlueprint` = `AnimBP_Player_TwoHandedItem`,
  `PlayerAnimCollection` = `AnimCollection_fp_ar`), gives the hand-item mesh `SK_bpa_pla_01` + `AnimBP_Backpack` (a
  DefaultSlot over the bag idle), plays `MG_fp_backpack_inventory` (MainActionSlot; In 1.5 / Idle 5 / Out 0.667 / OutFast
  0.333 s, blend 0) and `MG_backpack_fp_inventory` on the bag. `AnimNotify_UseHandItem` (0.567 s) opens the inventory
  (it is on screen about 0.45 s after the key, before most of the In); the close plays Out and an equip.
  `PC.OpenLootMenu` alone (no interaction in progress) does not turn that into a loot window.
- The bag sequences lock their root (`bForceRootLock`, reference rotation -90 deg about X); their keyed root equals the
  player's `jnt_l_weapon` (= `jnt_second_weapon`) every frame: the bag is held in the left hand. The bag's material is
  first-person (`_fov`). A runtime `SkeletalMeshActor` refreshes bones only when drawn (`AlwaysTickPose`): set
  `AlwaysTickPoseAndRefreshBones` or it stays in its reference pose behind the camera.
- What the backpack posture adds over the montage (`AnimBP_Player_TwoHandedItem`): `jnt_camera` and `jnt_weapon` copied
  from their virtual bones (the montage never moves the camera), `jnt_spine_03` taken from another pose in component
  space (the upper body follows the look), a smooth copy of `jnt_r_fore_arm`. Played over another posture in
  MainActionSlot the montage's camera key won (bare hands: view pitch -51 to -75).
- Playing the bag sequences as an arms-only layer (a montage asset with LeftHand + RightHand slot tracks, `Montage_Play`
  with `bStopAllMontages` false) works over the player's own posture. Its blend-out must start only once the bag is below
  the view (the game's Out has it there from frame 16-18 of 20; its last frame snaps behind the back).

## Vanilla behaviour worth knowing
- In static dialogue the native update keeps running but leaves `StateData.bMoving`, `bWalking`,
  `LocomotionData.MovementPlayRate.{Right,Forward}` at 0 and sets `bWalkingOverride = 1`;
  `StateData.bForceBindedHandsLookVertical` = 1 raises idle arms out of view (the vanilla "no arms in dialogue").
- The campfire sit (`MG_fp_ca_gd_bonfire`, slot FullBody, sections In, Idle (loops), Out) comes with
  `AnimCollection_pca_bonfire` settings `bShouldLerpToInteractable`, `bShouldToggleFOV`: the sit turns the first-person
  FOV / foreground render off and only its own exit turns it back on (`ToggleFOVAndForegroundRender(true)` to restore;
  otherwise first-person items render off-centre and the weapon vanishes).
- **`Obj.RemoveWeaponFromHands` swaps the stance and arm layer in one frame** (item stance to empty hands: hips 7.4 cm /
  19 deg apart). Called while a pose of yours is blending in, it shows as the hips and both hands jumping (measured: hips
  8 cm, hands about 30 cm in one frame). Call it only when your full-body pose is fully in.
- **Every vanilla consumable animation ends by reaching both hands to the weapon-ready pose** (the last 0.1-1.1 s,
  measured per item from the `AS_fp_*_use` sequences). If the weapon is hidden, that reach looks like grabbing nothing:
  leave the item (or hold it, `Montage_SetPlayRate` about 0) before its reach.

## Dead ends
- Montage blend profiles as masks (UE 5.5 clears `ActiveBlendProfile` once the blend-in ends; BlendMask mode is not
  handled for montages).
- `DetectorLayer` (no input pose); a Linked Anim Graph pass-through (never offers an `In Pose` pin).
- Recooking `AnimBP_player_bh` as an override breaks the unarmed sprint left-hand animation from a fresh load, even with
  no edits. Duplicate it to a mod-only path instead.
- `BS_fp_bh_walk` is the bare-hands arm additive, not locomotion.
