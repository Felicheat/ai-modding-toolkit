---
name: stalker2-animation
description: Explains how the STALKER 2 first-person player is animated and how a mod changes it without overriding AnimBP_Player (post-process anim instance, dynamic montages, slot groups, pose tables, left-hand gestures over a held weapon), and which approaches crash. Use when a mod adds or changes player animation, arms or hands look wrong, one montage cancels another, or the game crashes after an anim instance change.
license: MIT
compatibility: Windows. STALKER 2 Zone Kit
metadata:
  pack: STALKER 2 AI Modding Toolkit
  pack-version: "1.0.0"
  author: STALKER 2 AI Modding Toolkit contributors
  verified-on: "Taken from the Stalker 2 modding harness (commit 15b171c); not re-checked by this toolkit"
---

# Player animation in STALKER 2 mods

Adapted from the Stalker 2 modding harness by Noah Semus (github.com/noahsemus/stalker2-modding-harness, MIT).
These facts come from its mods (walking in dialogue, an own seated mode, hand gestures while looting) and were NOT
re-tested for this pack: prove each one in game. Blueprint paste text, the mod actor and input: stalker2-blueprints.

## How the player is animated
- Main anim instance: `AnimBP_Player` (parent `AnimInstancePlayer`, native). Its native update pushes about 23 data
  structs (`StateData`, `LocomotionData`, `CameraData`, ...) into the main instance only, and their members are mostly not
  Blueprint-writable: compute your own values and reroute bindings instead of writing them.
- Weapon and hands poses come from linked anim layers (`WeaponLayer`: `AnimBP_player_bh` for bare hands, a layer
  Blueprint per weapon type).
- The `FullBody` slot sits after everything, so a FullBody montage hides the arm-action layers. Item use (eat, drink, PDA,
  backpack) plays in MainActionSlot / DefaultSlot / UpperBody.
- The camera is the `jnt_camera` bone (a child of `jnt_root`, not the head).

## Change animation without overriding AnimBP_Player
Rebinding pins inside an `AnimBP_Player` override works but makes the asset a conflict magnet. Safe ways without it:
- **A dynamic montage in your own slot group**: a sequence built in editor Python, played with
  `PlaySlotAnimationAsDynamicMontage`. With the position set every tick it is a pose table (a pose per view angle).
- **A montage asset with `LeftHand` / `RightHand` slot tracks** for arm gestures over the current posture.
- **A post-process anim instance** (parent `AnimInstancePlayer`, not plain `AnimInstance`), also the place for live
  per-bone offsets. Attach it exactly once per world, about 1 s after the pawn appears, outside any dialogue or
  interaction.

## Crash families: do not retry
- `SetAnimInstanceClass` on the player mesh: an access violation at once (native code keeps the instance it created at
  spawn).
- `SetOverridePostProcessAnimBP(..., Reinit=true)`: access violation (a reinit without waiting for the parallel anim
  task).
- **Any post-process swap during play that overlaps a native interaction** (a contextual-action sit): access violation
  with `PC.IsVaulting` / `PC.HasNightVisionAnimation` on the stack (native code treats the post-process instance as the
  player's `AnimInstancePlayer` while the interaction runs). Even swapping the mod's own class back after a sit crashed.
  Only the single swap at load is known safe.
- `GetCurrentStateName` and other state-machine queries from outside the anim update fault.
- **`LinkAnimClassLayers` of a game posture outside its native flow**: linking `AnimBP_Player_TwoHandedItem` (the backpack
  / two-handed-item posture) into the WeaponLayer from a mod showed no right arm and crashed about 0.5 s after the loot
  window closed, before any re-link. The game links it itself inside `PC.StartUseBackpack`, which always ends in the
  player's own inventory.

## Montage and slot rules
- One montage per slot group, whatever `bStopAllMontages` says. A montage in one group does not stop the others.
- Groups: DefaultGroup (DefaultSlot, LeftHand, RightHand, CameraSlot, WeaponSlot, DeathSlot), ActionGroup
  (MainActionSlot, SecondaryActionSlot, GadgetActionSlot / GadgetActionAimSlot), UpperGroup (UpperBody), FullBodyGroup
  (FullBody), PreActionGroup (PreActionFullbodySlot), CutsceneGroup (CutsceneSlot).
- `GetCurrentActiveMontage` is not reliable from an actor's tick: bind `AnimInstance.OnMontageStarted` and keep the last
  montage, or ask `IsSlotActive(<slot>)`.
- `Montage_SetPlayRate` / `Montage_IsActive` / `Montage_IsPlaying` with a None montage act on ANY montage.
- A dynamic montage does not stay paused at play rate 0: set its position every tick.

## Hands: the short version
- With a weapon in hand the whole arm rig follows the view pitch; with empty hands only `jnt_camera` pitches and the arms
  stay in the body frame.
- The left hand is held on the grip by hand IK applied AFTER the `LeftHand` slot. A LeftHand montage must switch it off
  and on with `AnimNotify_HandIK`, and over rifles with an underbarrel idle it must carry the curve `left_hand_curve`, or
  the hand never leaves the grip.
- Build a left-hand gesture per weapon family on that family's own idle stance. Blending between hand rotations about
  180 deg apart flips the hand.
- First-person arms are drawn squeezed toward the view axis by their materials; bones and sockets are not. A world mesh
  placed at a hand bone shows further out than the hand.

## Traps
- Disabling a post-process instance leaves its last frame's notifies firing every frame (nonstop footsteps): one tick
  after switching it off, switch it on and straight off again.
- `Obj.RemoveWeaponFromHands` swaps the stance in one frame: call it only when your full-body pose is fully in.
- Every vanilla consumable animation ends by reaching both hands to the weapon-ready pose: with the weapon hidden it
  looks like grabbing nothing.
- Recooking `AnimBP_player_bh` as an override breaks the unarmed sprint left-hand animation, even with no edits:
  duplicate it to a mod-only path.
- Montage blend profiles do not work as masks, and a Linked Anim Graph pass-through never offers an `In Pose` pin.
- Property Access nodes only inside AnimGraphs and transition rules: one in an event graph crashed the compiler.

## References
- Read references/player-animation.md before building a post-process instance, a dynamic montage or a pose table, before
  reusing the backpack, PDA or campfire animations, and when a montage is cancelled or cannot be detected.
- Read references/arms-hands.md before any arm, hand or weapon-hand work: left-hand gestures, hand IK, reaching for a point
  on screen, turning a hand a set way round, the knife and the bolt, door leaf pivots, placing a world object at a hand.
