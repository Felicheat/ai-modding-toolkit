# The Wwise project: layout, event assets, a worked structure, Linux

Adapted from the Stalker 2 modding harness (github.com/noahsemus/stalker2-modding-harness, MIT, copyright Noah Semus); this part was contributed there by sdwvit.

## Project layout
| What | Where |
|---|---|
| Per-mod project | `<kit>/Stalker2/Mods/<Mod>/S2_WwiseProject/S2_WwiseProject.wproj` (a full copy of the game's project, about 256 MB; not cooked) |
| Its template | `Stalker2/Plugins/ModKit/Templates/ModWwiseOverlay/S2_WwiseProject` inside `<kit>/Stalker2/Content/Paks/Wwise-WindowsModEditor.pak`. "Open Wwise Project" only copies it out. The same pak holds every vanilla `AkAudioEvent` .uasset and the vanilla GeneratedSoundBanks |
| Originals (source WAVs), shared by all mods | `<kit>/O/SFX/...` (the `.wproj` `MiscSettings/Originals` is `..\..\..\..\O`); voice under `<kit>/O/Voices/<Language>/...`; vanilla radio music in `O/SFX/S2_Live/` |
| SoundBank output (what the editor and the cook read) | `<kit>/Stalker2/S2_WwiseProject/GeneratedSoundBanks/Windows`. One auto-defined bank per event (`Event/<EventName>.{bnk,json,xml,txt}`); streamed media loose as `Media/<id>.wem` (about 50k files) |
| Event to UI sound map | `UIRemaster/UISounds/BaseGame_UISounds.uasset` (FullEditor pak) maps `EUISound` to an event |

Without the editor: extract the template folder with
`repak unpack -o <dir> -i Stalker2/Plugins/ModKit/Templates/ModWwiseOverlay <pak>` (seconds) and copy it to
`<kit>/Stalker2/Mods/<Mod>/S2_WwiseProject`.

The project and the Originals are GSC's content: never ship or publish them.

## An event asset without the Wwise Browser (headless checkout)
An event asset is the vanilla event re-saved under the mod path. The pak's vanilla event `.uasset`s are UE5 file
version 1008 and the editor writes 1013, so the template has to be an **editor-saved** event from any mod: rename
its package to the new path (`WwiseName` is the same name as the package short name) and replace
`EventInfo.WwiseGuid` / `WwiseShortId` with `Events[0].GUID` / `.Id` from the new bank's `.json`. No tool in this
pack does this (the package rename needs a header rewriter); the Checkout click is simpler.

## Example: radio structure
- Events in `Events/S2 Live/Interactive Objects/IO_RadioTable.wwu`: `SFX_RadioTable_<Place>_On/_Off/_FreqSwitch`.
  On plays the `S_IO_RadioTable_On` click plus the music container, then seeks to a random position (ActionType 36,
  SeekPercent 0 to 100); FreqSwitch stops, replays and seeks; Off stops.
- Music containers: `Actor-Mixer Hierarchy\S2 Live\Interactive Objects\IO_RadioTable\Radio_Music\{Factions,Unique}`.
  Hubs often reuse faction playlists (the 100 Rads bar plays `Radio_Freedom`): to change one radio, clone a
  container and retarget only that radio's events.
- `Radio_Sidorovich` is the single-track template: a sequence container, `PlayMechanismLoop` on, one streamed Sound
  on the `IO_Radio_Music` bus with 3D attenuation.

## Linux / Proton
For a kit running under Proton (`<proton>` = the Proton build's `proton` script, `<prefix>` = the kit's Wine
prefix; both: stalker2-linux).
- Install Wwise once on Windows (or in a Windows VM, below) and copy the install into the prefix as
  `<prefix>/drive_c/Audiokinetic/Wwise_2024.1.10.8979`; set `WWISEROOT` / `WWISESDK` for that prefix. Prefer opening
  Wwise from the editor (Audio Modding > Open Wwise Project). **Do not start Wwise under a second wineserver while
  the kit editor is up**: it clobbers the prefix registry.
- WAAPI is reachable from Linux directly (Wine shares the host network): `waapi.py` or curl to `127.0.0.1:8090` from
  the host shell.
- Paths given to Wwise must be visible inside the Proton / pressure-vessel sandbox, under a drive letter the prefix
  maps. `/tmp` (and per-tool scratch dirs) are not: imports report "File not found" and leave an empty source. Copy
  WAVs into the Originals folder first. A fresh prefix may lack the drive letter the per-mod `.wproj` paths use; use
  one the prefix does map.
- `WwiseConsole.exe` output is swallowed by Proton: run
  `<proton> run cmd /c "<path>\WwiseConsole.exe <args> > <log file on a mapped drive> 2>&1"`. `proton run` returns
  at once while WwiseConsole keeps running: wait by polling the process list for `WwiseConsole.exe <op>`, and never
  `pkill -f` a pattern that also appears in your own shell's command line (it kills the shell). Stop a
  `waapi-server` with `kill <pid>` after `project.save`.
- Audiokinetic's site gates on the operating system: from a Linux browser its project-registration form landed on
  an access-denied page and the download page hides the Windows Launcher. Fallback: a Windows VM (for example
  Windows 11 LTSC evaluation under QEMU/KVM, about 10 GB qcow2) for registration, licence requests and the Wwise
  install; share a host folder over SMB to move files and logs both ways.
- Play candidates with `ffplay -nodisp -autoexit <wav>`.
