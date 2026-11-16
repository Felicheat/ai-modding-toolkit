# The pieces of a voiced phrase, the runtime data, animation during dialog

Traced upstream on vanilla data and in-game tests on game 2.0.x, unless marked *inferred*.
Adapted from the Stalker 2 modding harness (github.com/noahsemus/stalker2-modding-harness, MIT, copyright Noah Semus); this part was contributed there by sdwvit.

## What a voiced phrase is made of
Everything hangs off the phrase's cfg `TextToolPhraseSID`. No cfg field points at audio.

| Piece | What | Where (vanilla) |
|---|---|---|
| Phrase cfg | `DialogPrototypes/<Chain>.cfg`: `SID`, `TextToolPhraseSID`, `DialogMemberIndex`, `HasVOInSequence` | GameLite cfgs |
| Chain cfg | `DialogChainPrototypes/<Chain>.cfg`: `StartingDialogPrototypeSID`, `DialogMembers[*]` (`DialogMemberName`, `IsPCDialogMember`) | GameLite cfgs |
| Wwise | one Sound Voice + one Event `VO_<speaker>_<PhraseSID>` (EN + UA sources) | kit Wwise project |
| `AkAudioEvent` | about 2 KB `.uasset`, `EventInfo { WwiseGuid, WwiseShortId, WwiseName }`, no audio | `/Game/_STALKER2/Audio/WwiseAudio/Events/Voiceover/<Type>/VO_<Quest>/<speaker>/VO_<speaker>_<PhraseSID>` |
| Voice runtime data | `DialogRuntimeData` `<ChainSID>_Voiceover` | `/Game/_Stalker_2/maps/_Stalker2_WorldMap/QuestObjects/Dialogs/<...>/` or `.../QuestObjects/DefaultRuntimeData/` |
| Face runtime data (optional) | `DialogRuntimeData` `<ChainSID>_FaceAnimation` | same folder |
| Face anim (optional) | `AnimSequence` `AS_FAC_<EN or UA>_<speaker>_<PhraseSID>` on `SKEL_fac` | `/Game/_STALKER2/Animations/CharacterHead/<Type>/<Quest>/<speaker>/<EN or UA>/` |

- Who speaks which chain: `NPCPrototypes.cfg` (`HelloDialogChain`, `VoiceUA`, `VoiceEN`) or a quest node
  `EQuestNodeType::SetDialog` with `DialogChainPrototypeSID`. Some hello chains (`..._CallPlayer`) have no chain or
  phrase cfg at all: the NPC prototype names the chain and the voice comes from runtime data alone.
- `<Type>` is a quest-type folder: ANC, Bossfights, Encounters, General, Hubs, MainQuests, RepeatableSideQuests,
  SideQuests.
- **Dead route**: the legacy phrase fields `AKEventName` / `AKEventSubPath` (relative to `.../Events/Voiceover/`),
  `AssetsSubPath`, `FaceAnimationAssetName`, `FaceAnimationSubPath` are still set on about 600 vanilla phrases, but
  pointing a mod phrase at an existing vanilla event this way plays nothing (tested in game).
- Wwise picks the language: one event per phrase, one auto-defined bank per event per language
  (`GeneratedSoundBanks/Windows/Event/<Language>/<Event>.{bnk,json,xml,txt}`, media `Media/<Language>/<id>.wem`,
  loose, not streamed). Voice media also pulls shared SFX media of the voice-modulator effects (`VM_*` ShareSets,
  `RTPC_VM_Preset`). The cook bundles an event's banks and media into a `.ubulk` next to the event asset.

## DialogRuntimeData layout
`DialogRuntimeData` has two properties: `AssetType` (a name: `Voiceover`, `FaceAnimation`, `VoiceGen`) and an
instanced `AssetContainer`.
- `_Voiceover`: `NameToAsset_AssetContainer`, `Assets` = a map from name to soft object path: phrase SID (no
  `sid_phrase_` prefix) to `<event path>.<event name>`.
- `_FaceAnimation`: `NameAndLocalizationToAsset_AssetContainer`: phrase SID, then `None`, then a map from language
  (`ELocalizationLanguage`) to the soft object path of the `AS_FAC_*` anim. A line voiced in one language may point
  both languages at one anim.
- Nothing in the cfgs or in the Dialog Blueprint (editor-only) references these assets, and the runtime data's name
  and folder do not matter at runtime either: the game finds them by class (SKILL.md).

## Animation during dialog
- **Face**: the `FaceAnimation` entry plays from the phrase start. It carries no head or body motion.
- **Body gestures** come from `HumanDefaultAnimCollection`: a phrase's `DialogMembersAnimations[*].DialogAnimations`
  (explicit `EDialogAnimationType`), else a weighted random talking / listening pool. Both are keyed by the NPC's
  pose state, and only contextual-action states have entries (`RelaxStand` maps to `CAStand`, sitting states to
  their own). Armed and combat stances have none: an NPC whose `SetAIBehavior` uses `WeaponState Combat` (or `Relax`
  with a rifle) moves only its head. Give speaking NPCs `EWeaponState::NoWeapon`, as most vanilla Stay goals do.
  About a quarter of the `CAStand` talking pool is low-motion clips, so some lines look stiff regardless.
- **Interrupts**: the face anim is stopped only on the interrupt path of chains with
  `ContinueAfterInterrupt = true`. With `false` the voice stops and the mouth keeps moving to the anim's end
  (vanilla hub topics too, *inferred*).
