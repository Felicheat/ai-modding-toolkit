---
name: stalker2-audio
description: "Covers authoring sound for a STALKER 2 mod with the Zone Kit's Wwise project: GSC's official flow, the per-mod project layout, scripting Wwise through WAAPI, generating SoundBanks, and what an audio change needs so that it ships and is not silent. Use when replacing or adding music, radio tracks, UI sounds or voice events, when a cooked sound is silent in game, or before driving Wwise from scripts."
license: MIT
compatibility: Windows (Linux under Proton, see references/project.md). STALKER 2 Zone Kit; Wwise 2024.1.10.8979 with a licence that fits the project; Python 3.8+ for scripts/waapi.py
metadata:
  pack: STALKER 2 AI Modding Toolkit
  pack-version: "1.0.0"
  author: STALKER 2 AI Modding Toolkit contributors
  verified-on: "Taken from the Stalker 2 modding harness (commit 15b171c); not re-checked by this toolkit"
---

# STALKER 2 audio: Wwise project, WAAPI, SoundBanks, shipping

Authoring sound for a mod with the Zone Kit's Wwise project. Proven upstream on a menu-music replacement, a
radio-playlist mod and about 140 voiced dialog lines.
Adapted from the Stalker 2 modding harness (github.com/noahsemus/stalker2-modding-harness, MIT, copyright Noah Semus); this part was contributed there by sdwvit.

Voiced dialog as a whole (runtime data, lip-sync, debugging a silent line): stalker2-voiceover. Cooking, classifier
lists and checking a container: stalker2-zonekit.

## What the user needs
- The Zone Kit, and the Wwise version that matches the kit's integration: Wwise **2024.1.10.8979** when upstream
  last checked.
- A Wwise licence that fits their project. That is arranged by the user with Audiokinetic.

## Official flow (the user's clicks)
GSC's "Zone Kit - Audio modding quick start guide" (a Google Doc): Mod Editor toolbar **Audio Modding > Open Wwise
Project**, edit, generate SoundBanks (F7), then in the editor's **Wwise Browser** right-click > **Checkout** the
existing AkAudioEvents you changed, or **Reconcile** new ones, then package / cook.
- **Regenerate banks whenever you switch mods**: every mod's project writes into one shared GeneratedSoundBanks
  folder.
- Open the Wwise Browser only after `Stalker2.log` shows "Successfully connected to Wwise Authoring". It once
  deadlocked the editor, and while it is open the editor drops to about 8 FPS: close it when done. "Not connected"
  there can just mean the mod and root project paths differ; it still reads the banks from disk.
- Write these steps for the user click by click (stalker2-workflow).

## Editing the project from scripts
- Wwise Authoring serves WAAPI over HTTP on port 8090 by default. `python scripts/waapi.py <uri> [args-json|@file]
  [--return id,name,path]` posts one call and prints the JSON reply (exit 1 on an `ak.wwise.error...` reply). Smoke
  test: `python scripts/waapi.py ak.wwise.core.getInfo`.
- **Edit through WAAPI, never by writing `.wwu` files while Wwise is open** (reload prompt, lost state). Finish with
  `ak.wwise.core.project.save`.
- No GUI: `WwiseConsole.exe waapi-server <wproj> --http-port 8090 --wamp-port 8080` serves the same API (stop it
  after `project.save`); `WwiseConsole.exe generate-soundbank <wproj> --platform Windows` builds banks.
- After an import, check the source's `duration` matches the WAV.

## What an audio change needs to ship
- A checked-out or reconciled **AkAudioEvent `.uasset`** (about 2 KB, no audio in it) at
  `/<Mod>/_STALKER2/Audio/WwiseAudio/Events/<same path as vanilla>/<Name>` in the mod's `Content`, and in the mod's
  classifier list (stalker2-zonekit).
- **The cook bundles each event's bank and media from the shared GeneratedSoundBanks into a `.ubulk`** next to the
  event. Any mod's later bank generation can overwrite those files, so keep your own copies of your events'
  `Event/<Name>.*` and `Media/<id>.wem` (and the edited `.wwu` work units) in `<repo>`, and copy them back into the
  kit before every cook.
- Check the result: the cook log has `Cooking <mediaId>.wem`, and the staged OverrideContent `.utoc` contains
  `<Event>.ubulk` (`UnrealPak <utoc> -List`, or a strings search). An event cooked without its `.ubulk` is silent in
  game (a radio mod's container went from 7 MB to 151 KB when a hand-made repack left the bulk files out of the
  IoStore list).
- Pick a replacement target by ear before cooking (play the vanilla candidates from `<kit>/O/SFX/S2_Live`) and let
  the user confirm.
- Loudness: measure (`ffmpeg -af ebur128=peak=true`) and match the vanilla source's integrated LUFS before import;
  the Sound's own MakeUpGain / Lowpass still apply on top.

## Traps
- Names mislead: the pause-menu music is `S_UI_IdleScreen_Loop` (event `SFX_UI_IdleScreen`); `S_UI_PauseMenu_Loop`
  is a muffled bed.
- `ak.wwise.core.soundbank.generate` with `soundbanks:[{"name":"<Event>"}]` does NOT select an auto-defined event
  bank: it creates an empty 48-byte user-defined bank of that name and regenerates all of the roughly 55k
  auto-defined banks (about 30 minutes, WAAPI blocked throughout). Details: references/waapi.md.
- A failed import ("File not found") leaves an empty source. Import from a path inside the Originals folder.
- Deleting a source to swap its audio loses the source-level trims and loop points (`TrimBegin`, `LoopBegin`).
- Freshly reconciled event assets may show as corrupted in the kit; restarting the kit fixes it.
- Another mod's bank generation silently replaces your events' files in the shared folder: restore your copies
  before a cook.

## References
- Read references/project.md before touching a mod's Wwise project or the shared folders, to set a project up
  without the editor, to make an event asset without the Wwise Browser, for the radio example, and on Linux.
- Read references/waapi.md before any WAAPI call or any scripted bank generation.
- Read references/voice-events.md before creating the Wwise objects, events and event assets for dialog voice lines.
