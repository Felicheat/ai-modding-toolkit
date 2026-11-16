---
name: stalker2-linux
description: "Explains STALKER 2 modding on Linux: the game under Steam Proton, the Zone Kit through the Heroic Games Launcher in its own Wine prefix, where logs, saves and settings sit inside the prefixes, how Linux paths map to Wine paths, and the traps when cooking or stopping kit programs. Use when the user mods on Linux, when a log, save or path must be found inside a prefix, or when a kit program run through Wine hides its output or will not stop."
license: MIT
compatibility: Linux. Steam with Proton for the game; Heroic Games Launcher with a GE-Proton build for the Zone Kit
metadata:
  pack: STALKER 2 AI Modding Toolkit
  pack-version: "1.0.0"
  author: STALKER 2 AI Modding Toolkit contributors
  verified-on: "Taken from the Stalker 2 modding harness (commit 15b171c); not re-checked by this toolkit"
---

# STALKER 2 modding on Linux (Proton)

The game and the Zone Kit both run under Proton (Wine). Proven upstream: the Zone Kit installed with the Heroic
Games Launcher (Epic account) into its own Wine prefix, driven by a GE-Proton build; the game from Steam with
Proton; mods cooked, installed and released from Linux.
Adapted from the Stalker 2 modding harness (github.com/noahsemus/stalker2-modding-harness, MIT, copyright Noah Semus); this part was contributed there by sdwvit.

## This pack on Linux
- The facts here come from upstream's Linux work with upstream's own tools. Of this pack's scripts only three,
  copied from upstream, state Linux support: `s2sav.py` (stalker2-saves), `waapi.py` (stalker2-audio) and
  `fit_lipsync.py` (stalker2-voiceover). Treat the others as untested on Linux and tell the user so.
- stalker2-zonekit's `sdk_run.py` does not start off Windows, and the kit is not auto-detected on Linux: set env
  `S2_ZONEKIT_DIR` and start kit programs as shown below.

## What runs where
| Piece | On Linux |
|---|---|
| Zone Kit editor (`Stalker2ModEditor-Win64-Shipping.exe`) | Heroic (Epic) in its own Wine prefix (`<kit prefix>`), started from Heroic |
| Cook, `CreatePlainMod`, headless editor Python, UnrealPak | `RunUAT.bat` / the `-Cmd` editor / `UnrealPak.exe`, run through `<proton build>/files/bin/wine` with `WINEPREFIX=<kit prefix>` |
| Game | Steam + Proton, prefix `<steam library>/steamapps/compatdata/1643320/pfx` (`<game prefix>`) |
| Python tools outside the editor | the system `python3` (3.10+) |
| Scripts inside the editor | the editor's own Python under Wine; give them Wine paths |
| `.pak` listing and unpacking | `repak` (native, `cargo install repak`) for plain `.pak` files, or `UnrealPak.exe` through Wine for IoStore `.utoc` |

## Install and folders
- The user installs Steam and the game and starts it once with Proton (this creates the game's prefix); then the
  Heroic Games Launcher, logged in to Epic, and "S.T.A.L.K.E.R. 2 Zone Kit" from it (about 600 GB), started once
  until the editor window is fully open.
- In Heroic's game settings for the kit the user picks a Proton build (GE-Proton worked; Wine-GE and plain Wine are
  untested) and notes the prefix shown there.
- Heroic's config is `~/.config/heroic` (Flatpak: `~/.var/app/com.heroicgameslauncher.hgl/config/heroic`):
  `legendaryConfig/legendary/installed.json` has the kit's install folder; `GamesConfig/<app>.json` has the kit's
  prefix (`winePrefix`) and the Wine build (`wineVersion.bin`; its folder plus `files/bin/wine` is the `wine` to
  call, for example `~/.local/share/Steam/compatibilitytools.d/<GE-Proton build>/files/bin/wine`).
- Steam's `libraryfolders.vdf` (native `~/.steam/steam`, or the Flatpak's) leads to the game folder and its prefix.

## Starting a Windows program of the kit
Call the Proton build's `files/bin/wine` directly with `WINEPREFIX=<kit prefix>` set. Do not use the `proton`
script (`proton run ...`): it returns at once while the program keeps running, wraps it in the Steam Runtime
sandbox (paths outside it are invisible) and swallows stdout, and you need the exit code and the log.

## Paths
- Windows programs get Wine paths. Convert every Linux path you pass (`-Project=/media/...`, `-script=/tmp/...`)
  with the prefix's `dosdevices` links: the longest matching drive wins (with drive `u:` linked to `/media`,
  `/media/games/Kit` becomes `games\Kit` on drive U), and `z:` (linked to `/`) is the fallback every prefix has.
  Inside response files and editor scripts, write the same Wine form yourself.
- The game's `%LOCALAPPDATA%/Stalker2` is under `<game prefix>/drive_c`, in
  `users/steamuser/AppData/Local/Stalker2`: `Saved/Logs/Stalker2.log`, `Saved/Crashes/`, `Saved/STEAM/SaveGames/`,
  `Saved/CustomizeControls.cfg`. Every `%LOCALAPPDATA%/Stalker2/...` path in this pack maps there.
- The kit's own `%LOCALAPPDATA%` and `%APPDATA%` (editor settings, UAT logs) are under `<kit prefix>/drive_c`, in
  `users/<user>/AppData/` (`steamuser` with Proton). UAT logs:
  `.../AppData/Roaming/Unreal Engine/AutomationTool/Logs/<kit path>/`.

## Cooking under Proton
- It works with the same UAT cook command and flags as on Windows (stalker2-zonekit), only slower. On an earlier
  kit each pass spent about 21 minutes starting up (Wine file access over the kit's mounted paks), 40 to 45 minutes
  per full cook; on the 2.0 kit one measured cook took 6 min 27 s.
- Editor open during a cook, two statements: upstream cooked with the editor left open in Heroic (same prefix, one
  wineserver); stalker2-zonekit says never to cook while the kit is open, because it locks the cook's cache files.
  Closing the editor before a cook satisfies both.
- **Stopping a cook**: killing the shell that started it does not stop it. `dotnet ... AutomationTool.dll GSCCookMod
  ...` and `Stalker2ModEditor-Win64-Shipping-Cmd.exe -run=Cook ...` keep running and keep writing to `SavedMods/`.
  Kill those by pid, matching the mod name and `AutomationTool` / `-Cmd`. Never kill a bare
  `Stalker2ModEditor-Win64-Shipping.exe` (without `-Cmd`): that is the user's open editor.
- A cook killed between its passes leaves a half-staged tree (OverrideContent only): cook again before installing.

## Game, testing, editor Python
- Installing a mod works with the game closed, exactly as on Windows. There is no Vortex on Linux, so "an installed
  release copy shadows the test build" concerns hand-installed and Steam Workshop copies: a Workshop subscription
  and a `~mods` copy of the same mod both mount.
- Launch the game (`steam steam://run/1643320`) only when the user asks.
- Upstream ran the headless `-run=pythonscript` commandlet through Wine and pasted scripts into the open editor's
  Output Log: both work (command line: stalker2-zonekit). Unreal remote execution into the open editor from the
  host should reach it (Wine uses the host network) but is not confirmed on Linux.

## Traps
- `pgrep -f Stalker2-Win64-Shipping` matches the shell running pgrep itself. Read `ps -eo pid,args` and match
  `Stalker2-Win64-Shipping\.exe`.
- One wineserver per prefix: a program started under a second wineserver while the kit editor is up clobbers the
  prefix registry (seen with Wwise).
- Wwise in the kit's prefix, and Audiokinetic's site refusing Linux: stalker2-audio. Saves and the Linux Oodle
  library: stalker2-saves. Voice scripts: stalker2-voiceover. Publishing: nothing differs (stalker2-publish).
