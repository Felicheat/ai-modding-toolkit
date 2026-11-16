# Arms, hands and weapon: first-person facts and left-hand gestures

Adapted from the Stalker 2 modding harness by Noah Semus (github.com/noahsemus/stalker2-modding-harness, MIT).
From its looting mod. Section titles say what was verified in game and what was read from the kit. Not re-tested for
this pack.

## Contents
- Arms, hands and weapon
- Left-hand gestures over a held weapon
- Turning a hand, the knife and the bolt, door leaves
- The LeftHand slot and the game's own gestures
- Left-hand IK and the grip
- Reaching for a point on screen
- First-person arms are drawn squeezed toward the view axis

## Arms, hands and weapon (verified in game)
- Look-vertical additives: `fp_ar_stand_lookvertical` and `AS_fp_bh_lowcrouch_lookvertical` turn spine, arms, hands and
  camera together. The standing bare-hands one (`fp_bh_stand_lookvertical_idle`) turns the camera but leaves the hands
  where they are, so an arm animation laid over bare hands standing drifts up out of view as you look down.
- `VB jnt_camera` and `VB jnt_weapon` are virtual bones under `jnt_spine_03`. The weapon follows `jnt_weapon`, which
  arm-masked slots never move.
- The weapon layer's hand IK (`TwoBoneIK_GSC`) pins each hand to the weapon mesh's own `jnt_l_hand` / `jnt_r_hand` socket,
  alpha `HandsIKData.LeftHand` / `.RightHand`, switched by `AnimNotify_HandIK` (`HandToApply` LEFT_HAND / RIGHT_HAND /
  BOTH_HAND). A weapon hidden with `SetHiddenInGame` stays in the hands, keeps the weapon posture, and its IK keeps the
  hand on the invisible grip until switched off.
- Weapon equip montages `MG_fp_<weapon>_equip` (MainActionSlot; notifies HandIK both on, `WeaponAction`
  UNLOCK_LEFT_HAND_IDLE, `PlayerAction` END EQUIP_MAIN_ITEM) can be replayed with `Montage_Play` on the player with the
  weapon already in hand (no side effects seen). Remember the last one from `OnMontageStarted`.
- Local-space blends take the short way per bone: blending two poses whose bone differs by about 180 deg flips direction
  frame to frame and shows as a near full spin. The vanilla `MG_fp_ak74_weapon_grab` has the left hand 120-180 deg from
  every weapon idle in frames 23-34 (hand at the chest): never blend out there.
- A left-arm local-space additive in FullBody over another weapon's grip pose (to make one gesture fit all weapons)
  looked "like jelly / alien": a dead end.

## Left-hand gestures over a held weapon (verified in game)
- Build them per weapon family on that family's own idle stance, as the game does (`MG_fp_ar_flashlight`,
  `MG_fp_pt_flashlight`, NVG per family). Long-gun idles' left hands (rifle / SMG / sniper / shotgun) lie within about
  0-64 deg (local) of `fp_ar_idle_stand`, pistols within 24 deg of `AS_fp_pm_idle`; the vanilla AK grab's grip is 88 deg
  from a pistol's.
- A gesture keyed on another family's grip flips in the LeftHand slot's blend-in, and the weapon layer's hand IK
  (`AnimNotify_HandIK`) flips whenever it blends between two hand rotations about 180 deg apart: release it over about
  0.06 s before the wrist turns, and re-engage it only once the hand is back near the grip.
- Turn the wrist only after the slot's blend-in, one way round (no per-frame shortest path), half the turn into
  `jnt_l_fore_arm_roll`.
- The family stance's grip is a few cm off each weapon's own grip: end the keyed path left of / below it so the IK's last
  stretch comes in from the side away from the weapon (a straight return clipped through the barrel and wobbled).

## Turning a hand, the knife and the bolt, door leaves
- **Turning a hand a set way round**: a target orientation rolled by about 180 deg lets the slerp pick the way round (a
  user asked for clockwise and got counter-clockwise). Interpolate the unrolled orientation and apply the roll on top,
  `roll(axis, angle x weight)`, so its sign decides. UE axes are left-handed (X forward, Y right, Z up): a NEGATIVE angle
  about the forward reach turns clockwise as the player sees it. Check with the thumb bone's screen angle frame by frame
  (atan2(dy, dz) relative to the hand).
- **The knife and the bolt** (EMainHandEquipmentType 4 / 6) hold the free left hand at (40, -24, -18..-20) cm from the eye
  in view axes at every pitch and stance: their layer = `fp_ar_idle_stand` + the item's mesh-space idle additive
  (`AS_fp_knife_idle_add` / `AS_fp_bolt_idle_add`) + the rifle look. Build left-hand gestures for them on that pose with no
  HandIK-on notify (there is no grip: IK on pulls the free hand to the item's socket, "spinning hands").
- **Door leaves**: a door leaf mesh's pivot is its hinge (`SM_cit_out_door_a_04` 0..104 cm, cupboards -51..0), so the free
  edge = 2 x the leaf component's bounds centre - its location.

## The LeftHand slot and the game's own gestures (from a headless read of the layer AnimBlueprints)
- Every weapon layer has a `LeftHand` slot behind `left_hand_blend_mask` (jnt_l_shoulder to the fingers, local-space
  rotation), after MainActionSlot / UpperBody, chained RightHand, LeftHand, CameraSlot, DefaultSlot:
  `AnimBP_PlayerWeaponLayer` (all firearms, `WeaponSlotsLayer`), `AnimBP_player_bh`, `AnimBP_Player_Knife`,
  `AnimBP_Player_fp_bolt`, `AnimBP_Player_fp_F1`, `AnimBP_Player_TwoHandedItem`, `AnimBP_PlayerDetectorLayer` (weighted by
  `DetectorData.bIsLeftHandSlotEnabled`). In `AnimBP_Player` itself LeftHand appears only in the guitar state.
- Slot group of LeftHand = the default group (with DefaultSlot, WeaponSlot, RightHand, CameraSlot).
- GSC's per-stance left-hand gestures: `Flashlight/Montages/MG_fp_<stance>_flashlight` and
  `NightVisionGoggles/Montages/MG_FP_Player_*_NVG-SwitchOn/Off_01` (LeftHand + WeaponSlot + CameraSlot), the injector
  `Items/Antirad/MG_fp_antirad_use`, `ar/common/showhide/lefthand/MG_fp_remove_left_hand_from_item` /
  `MG_fp_return_left_hand_on_item` (the latter turns HandIK on at 0.136 s: recovery for a cut left-hand montage).
- An unused vanilla left-hand grab with a rifle held: `ar/ak74/MG_fp_ak74_weapon_grab` (= gp37) on
  `ar/common/grabitem/fp_ar_weapon_grab`, 1.667 s, LeftHand, only the left arm moves (camera still). Firearm anim
  collections have a `WeaponAnimations.PickUpItem` field for it, filled only for the grenade-launcher AK / gp37.
- Left-hand item point: bone `jnt_l_weapon` (child of `jnt_l_hand`; the game's `AttachItem PickingUpItem` socket).
  `jnt_item` / `jnt_unequipped_item` / `jnt_camera` are root children, not hand bones.

## Left-hand IK and the grip (headless read plus in-game traces)
- The left hand is held on the foregrip by `TwoBoneIK_GSC` (jnt_l_hand to `jnt_weapon`, alpha
  `HandsIKData.LeftHand.Alpha`, skipped while `StateData.bIsLeftHandBusy`), applied AFTER the LeftHand slot. Montages
  switch it with `AnimNotify_HandIK` (HandToApply LeftHand; defaults Start 0 / End 0 / 0.2 s cubic = off; End 1 = on).
  Rifle and pistol LeftHand montages bracket themselves with an off and an on notify; a dynamic montage of a bare sequence
  has no notifies, so the hand stays glued to the grip.
- **Rifles with an underbarrel idle type pin the left hand**: `AnimBP_PlayerWeaponLayer`, `WeaponUnderbarrelIdleLayer`
  blends the `GripIdle` pose over the left arm with weight `FirearmData.LeftHandCurveValueInverse` = 1 - the montage curve
  `left_hand_curve`. A `LeftHand` montage without that curve plays (slot active, position advancing) but the hand never
  leaves the grip. The game's own left-hand gestures (`MG_fp_ar_flashlight`, NVG) carry `left_hand_curve` (0 to 1 in
  0.17 s, held, back to 0 about 0.25 s before the end): add it to any mod-made LeftHand sequence
  (`AnimationLibrary.add_curve` + `add_float_curve_keys`).
- With empty hands the left-hand IK still pulls a `LeftHand` montage's hand toward the grip point (`jnt_weapon`, just right
  of centre): a default `AnimNotify_HandIK` (LeftHand, End 0) at the start keeps it off; a "back on" one (End 1) makes the
  hand jump there.

## Reaching for a point on screen (in-game traces)
- **With empty hands the arm bones do not follow the view pitch**: only `jnt_camera` pitches, and the arms stay in the body
  frame. A left-arm pose played in `LeftHand` that is right looking straight ahead ends about 50 cm above the view axis
  when looking 30 deg down. A reach meant to land somewhere on screen needs one pose per view pitch (or per item
  elevation): a table of segments in one sequence, started with `InTimeToStartMontageAt` and stopped with `Montage_Stop`.
- The empty-handed spine differs a lot from the rifle stance: the same left-arm locals put the hand about 40 cm higher.
  Solve left-arm poses on the stance's own spine (`fp_bh_idle_stand` matched the in-game rest hand to 1 cm).
- **With a weapon in hand the whole arm rig follows the view** (the weapon layer pitches `jnt_spine_03` with the
  look-vertical additive): a hand position relative to `jnt_camera` in a sequence is its position in view axes in game,
  whatever the view pitch (three traces). Measured hand-bone landing for a planned camera-relative point: ahead + 8.4 cm,
  right x 1.14 + 4.0, up x 1.15 + 2.0 (the sideways scale is about the arms' FOV squeeze).
- A 180 s "pose table" sequence (many segments, `InTimeToStartMontageAt`) works in the bh layer; over a rifle the same form
  never showed (cause not isolated; the missing curve may have been the whole reason). Many short sequences (one per bin)
  cook to about 15 KB each and are a safe alternative.

## First-person arms are drawn squeezed toward the view axis (from the kit materials)
The arm and hand materials (`M_MasterHands`, `MF_ForegroundWithShadowSwitch`, `MF_Foreground`) move every vertex in the
vertex shader: `MF_Foreground_FOVCorrection` scales the sideways part (perpendicular to the camera forward) of the
camera-relative position by `s = tan(view hFOV / 2) / MPC_FOV.TanFOV`, then `MF_Foreground_AntiDepthClipping` scales the
whole camera-relative position by `MPC_FOV.DepthScale` (0.225; screen position unchanged). Bones and sockets are NOT
moved: a normal world mesh placed at a hand bone shows up further out than the hand (off screen at the edges).
To place a world object where a bone is SEEN:
`C + F*dot(F, P) + (P - F*dot(F, P)) * lerp(1, s, MPC_FOV.IsFOVEnabled)` with `P = bone - C`, `C` / `F` the camera
location / forward (`PlayerCameraManager`), and scale it by the same `s`. `MPC_FOV` =
`/Game/_Stalker_2/Materials/MPC/MPC_FOV` (TanFOV, DepthScale, IsFOVEnabled, CurrentFOV, DisplayFOV).
