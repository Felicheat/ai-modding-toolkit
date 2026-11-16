---
name: stalker2-voiceover
description: "Explains how STALKER 2 plays a voiced dialog line and how a mod adds one: phrase cfg, Wwise event, the DialogRuntimeData voice and face-animation maps, lip-sync anims fitted from a vanilla speaker, and gestures during dialog. Use when adding voice or lip-sync to mod dialog, when a line shows subtitles but plays no voice, when the Zone Kit drops voice entries, or when an NPC stands stiff while talking."
license: MIT
compatibility: Windows. STALKER 2 Zone Kit (three scripts run in its editor Python); Wwise for the audio side (see stalker2-audio); Python 3.11+ with numpy for fit_lipsync.py
metadata:
  pack: STALKER 2 AI Modding Toolkit
  pack-version: "1.0.0"
  author: STALKER 2 AI Modding Toolkit contributors
  verified-on: "Taken from the Stalker 2 modding harness (commit 15b171c); not re-checked by this toolkit"
---

# STALKER 2 voiced dialog lines

Voice lines, lip-sync and dialog animation for mod dialogs. Traced upstream on vanilla data (GameLite cfgs, the
kit's editor paks) and in-game tests of a voiced mod quest on game 2.0.x, unless marked *inferred*.
Adapted from the Stalker 2 modding harness (github.com/noahsemus/stalker2-modding-harness, MIT, copyright Noah Semus); this part was contributed there by sdwvit.

Dialog text keys (`sid_phrase_...`): stalker2-localization. Wwise objects, events, banks and event assets:
stalker2-audio. Player animation: stalker2-animation.

## How the game plays a voiced line
- Everything hangs off the phrase's cfg `TextToolPhraseSID`. No cfg field points at audio.
- Once at boot the game takes every `DialogRuntimeData` asset in its asset registry, by class, and loads them all.
  No label, path, DLC or GameFeatureData rule is involved; overriding `QuestAssetLabel` / `PAK_Quest_BaseGame` does
  nothing. The asset's name and folder do not matter.
- The assets are merged by `AssetType` (`Voiceover`, `FaceAnimation`, `VoiceGen`) into one map each. Mod and vanilla
  entries share that map.
- Playing a phrase: the key is its `TextToolPhraseSID`, exactly. Lookup `Voiceover`, then `VoiceGen`;
  `FaceAnimation` uses the same key plus the language.
- A phrase with `ShowNextDialogOptionsAsAnswers = true` (an answer menu, always the player in vanilla) plays no voice.
- A mod's assets are in the registry because the mod plugin's `AssetRegistry.bin` (inside its NewContent `.pak`) is
  appended to the game's registry when the plugin is registered at startup.

## What silently breaks it (subtitles, no voice)
- **Install folder.** Only mods under `<mods>` (or from Steam Workshop) are registered as mod plugins. In any other
  folder under `Paks/`, cfgs, overrides and by-path loads work, but class queries never see the mod's assets, so its
  runtime data is never loaded (tested: a mod in `Paks/notmods/` was silent; moved to `~mods` it played).
- **Unknown speaker.** Loading a `_Voiceover` / `_FaceAnimation` asset in the Zone Kit (editor and cook alike) drops
  every entry whose phrase's TextTool `Character` is `None` or not in the editor's character list (verified by
  elimination: 19 entries in the file, 13 in the editor and in the cooked package). The player must be `PC`
  (`sid_character_PC`); NPCs need a vanilla character SID. The list is the `characters` array
  (`{ id, sid, name_sid }`) of the `TextDatabase_<part>.json` files in the kit's FullEditor pak
  (`Stalker2/Content/TextToolBackup/`). A mod cannot add a file there, so a brand-new NPC character stays silent:
  speak through a vanilla character SID.
- **A generator that writes only lines with a take** silences any line whose take was removed since the last run.
- **The legacy phrase fields** (`AKEventName` and the others in references/pieces.md) play nothing.

## Making a voiced line
1. **Takes**: one WAV per line and language, padded with about 0.1 s of trailing silence before import. Tight takes
   make speaker changes sound rushed, dialog cfgs have no per-phrase delay (`PreblendTime` / `BlendExpForEaseInOut`
   are sequence camera blends), and a Wwise initial delay would put lip-sync out of step.
2. **Wwise**: one Sound Voice (EN + UA sources) and one Event `VO_<speaker>_<PhraseSID>` per phrase, banks for just
   those events, then the event assets (`AkAudioEvent`). Recipe and traps: stalker2-audio.
3. Keep a copy of your events' bank output (`Event/...`, `Media/...`) in `<repo>`: every mod's bank generation
   writes the same shared folder, and the cook bundles whatever is there.
4. **Face anims** (NPC lines only; the player has none): references/lipsync.md.
5. **Runtime data**: `<ChainSID>_Voiceover` (and `_FaceAnimation`). The editor route is the
   `EUW_GenerateDialogruntimeAssets` widget (stalker2-audio), which assumes an editor-authored Dialog Blueprint.
   Cfg-authored dialogs need the assets written another way, for example a vanilla `_Voiceover` package used as a
   binary template with its map rewritten (upstream's writer round-trips a vanilla template byte-identically; no
   such writer is in this pack). Entries are soft object paths `<package>.<asset>`.
6. Cook, install into `<mods>`, then walk "Debugging".

Adding lines to a mod that already has voice: run every step for the new lines only.

## Debugging: subtitles but no voice
Walk the stages in order; the first one missing the key is the culprit.
1. **Source asset**: the runtime data's map holds as many entries as lines expected.
2. **Editor**: `probe_voiceover_keys.py` with `PKG = "/<Mod>/.../<ChainSID>_Voiceover"`. Fewer keys than the file
   holds = the editor dropped them (unknown speaker). `RELOAD = 1` tells a stale editor copy apart.
3. **Cooked**: extract the staged NewContent container (`UnrealPak <x>.utoc -Extract <dir>`) and count the
   `VO_<speaker>_` names in the runtime-data package (stalker2-blueprints' `zen_names.py`). The cook keeps only what
   the editor kept. For audio to be present at all, the event packages need their `.ubulk`.
4. **Mod registry**: the NewContent `.pak` holds `AssetRegistry.bin` and the `.uplugin`; grep the registry file for
   `DialogRuntimeData` and your asset names.
5. **Install folder**: `<mods>` (above).

## Tools (inputs are variables, not arguments: references/lipsync.md)
| Script | Runs | Does |
|---|---|---|
| `scripts/probe_voiceover_keys.py` | kit editor Python, read-only | keys the editor sees in one runtime-data asset |
| `scripts/dump_face_anim.py` | kit editor Python, read-only | a vanilla speaker's face anims to JSON |
| `scripts/fit_lipsync.py` | Python 3.11+ with numpy | fits audio to face channels, predicts tracks for new lines |
| `scripts/create_face_anims.py` | pasted into the OPEN kit editor, saves assets | bakes the predicted `AS_FAC_*` anims |

## Traps
- The speaker name in `VO_<speaker>_<PhraseSID>` and `AS_FAC_<L>_<speaker>_<SID>` must have no `_`: the tools
  split on it.
- An NPC in an armed or combat stance has no dialog gestures: it moves only its head (references/pieces.md).

Read references/pieces.md before building or checking a piece of a voiced phrase by hand (names, paths, the
runtime-data layout, the dead cfg fields) and when gestures or interrupts misbehave.
Read references/lipsync.md before making face anims or running any of the editor scripts.
