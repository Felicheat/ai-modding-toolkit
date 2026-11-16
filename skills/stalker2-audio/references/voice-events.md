# Wwise objects and event assets for dialog voice lines (editor route)

The steps below follow a community guide that upstream credits only as the "Volucris" guide (a PDF); upstream
gives no link to it. The guide assumes a licensed Wwise project.
Adapted from the Stalker 2 modding harness (github.com/noahsemus/stalker2-modding-harness, MIT, copyright Noah Semus); this part was contributed there by sdwvit.

How the game finds a phrase's voice and face animation, and what breaks it at cook: stalker2-voiceover.

## In Wwise (Designer layout, F5)
1. Audio tab: `Actor-Mixer Hierarchy\S2 Live\Voiceover\VO_Voiceover\Voiceover_VM_AM\<type>` (`<type>`: ANC,
   Bossfights, Encounters, General, Hubs, MainQuests, RepeatableSideQuests, SideQuests) > New Child Work Unit
   `VO_<Quest>` > one Actor-Mixer per speaker.
2. One **Sound Voice** per phrase: phrase SID `sid_phrase_<Quest>_<Rest>` gives object
   `VO_<speaker>_<Quest>_<Rest>`. Add Source > Import for English(US), again for Ukrainian(UA) (the files land in
   `<kit>/O/Voices/<Language>/...` as `EN_VO_...` / `UA_VO_...`; Reference language = English(US)).
3. Events tab: `Events\Voiceover\<type>` > Work Unit `VO_<Quest>` > a Virtual Folder per speaker > one Event per
   Sound Voice, same name, a single Play action targeting it.
4. SoundBank layout (F7), Auto-Defined SoundBanks: uncheck Default Work Unit and `S2 Live`; under `Voiceover` check
   only `<type>` > `VO_<Quest>`. Platform Windows; languages English(US) + Ukrainian(UA). Generate Checked, save.
   The result is one bank per event per language.

## In the Zone Kit
5. Audio Modding > Wwise Browser > select the new events (status "UAsset Missing") > Reconcile icon > Reconcile
   Unreal Assets. They appear under
   `/<Mod>/_STALKER2/Audio/WwiseAudio/Events/Voiceover/<type>/VO_<Quest>/<speaker>/`. Many may then show as
   corrupted; restarting the kit fixes it.
6. Editor Preferences > General - Dialog Editor > "Dialog Runtime Data Asset Default Folder" = the mod's dialog
   folder. Run the Editor Utility Widget `/QuestTool/DialogUtilities/EUW_GenerateDialogruntimeAssets`, select the
   Dialog Blueprint, choose `Voiceover`, "Generate for DialogBlueprint". In the generated data asset
   (`NameToAsset_AssetContainer` map) set an AkAudioEvent per phrase key (`<Quest>_<Rest>`, no `sid_phrase_`
   prefix) and save. `RemoveNonExistingPhrases` prunes stale keys.

This route assumes an editor-authored Dialog Blueprint; mapping it onto dialogs generated from cfgs was not tried.

Pad each take with about 0.1 s of trailing silence before import, and keep a copy of the events' bank output in
`<repo>` (why: stalker2-voiceover).
