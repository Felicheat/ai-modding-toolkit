---
name: stalker2-zonekit
description: Works with the official STALKER 2 Zone Kit (SDK) for reading GSC's uncooked source and real material wiring, kit GUI steps, headless editor Python, offline byte patching and Custom node code, cooking and packing an override that really loads, Niagara, mesh reimport and Smart App Control blocks. Use when a change needs the kit, a kit mod built fine but does nothing in game, a cook or pack fails, or the user asks for kit steps.
license: MIT
compatibility: Windows. STALKER 2 Zone Kit. Python 3.8+ with cityhash (pip install cityhash); retoc and repak (see the pack START_HERE.md); the .NET 8 SDK to build tools/uasset-dump
metadata:
  pack: STALKER 2 AI Modding Toolkit
  pack-version: "1.0.0"
  author: STALKER 2 AI Modding Toolkit contributors
  verified-on: "STALKER 2 Steam build 26123434 (game 2.1), Zone Kit 2.1.0"
---

# STALKER 2 Zone Kit

## Kit or no kit
- Needs the kit: material graphs, Niagara systems, meshes, textures, new assets, and every cook (the cook compiles shaders).
- Offline once an asset is checked out: material constants, parameter defaults, Custom node code, instance values (byte
  patches, then a kit cook).
- No kit at all: cfg edits (stalker2-cfg), cooked curves (stalker2-curves), and READING GSC's source (next section).
  Sound for a mod needs the kit and a Wwise project: stalker2-audio.

## Read the source before tuning
- GSC's UNCOOKED assets (full graphs, Niagara systems, source textures, real settings) are in
  `<kit>/Stalker2/Content/Paks/FullEditor-WindowsModEditor.pak`. Settings such as SRGB come from there, never from a cooked file.
- A material's real wiring: the user copies the graph as text, you read it with `python scripts/mat_t3d.py <file> summary`;
  that is ground truth. `python scripts/mat_uasset_tree.py <full .uasset path>` gives a first look from the saved bytes.
  Do this BEFORE trial-and-error tuning.
- `tools/uasset-dump/` dumps any .uasset to JSON (build once: `dotnet build -c Release`; UAssetAPI by atenfyr).

## GUI essentials
- One launch per sitting: loading takes minutes and the open kit edits every mod (switch mods in the main toolbar). Never
  write "close the kit and restart" mid-guide.
- Edit the MOD's copy (`/<mod>/...` in Ctrl+P), not `/Game/...`. Apply, then Save from the ASSET window's toolbar (Ctrl+S in
  the main window is Save Level As). Accept Check Out Assets. Back the checked-out file up into `<repo>`.
- Steps for the user: click by click, plain language. Name each node by title, position and what feeds it ("the Multiply fed
  by Particle Color"), each wire FROM node and pin TO node and pin. Never internal names (`Multiply_5`), never "the 8th module".
- Verify the saved asset offline BEFORE the user closes the kit.
- Headless editor Python (kit closed) edits and saves MOD assets, GSC materials copied into the mod included. It cannot
  save a `/Game` asset, add Blueprint graph nodes or edit Niagara (references/headless-python.md).
- Blueprint logic and paste text: stalker2-blueprints. Never add variables or components to a GSC class placed in a cooked level.

## Traps: it built fine and silently did nothing
1. **Byte patch, no new StateId.** The cook takes a material's shaders from the DDC by StateId, so the OLD shaders ship. Run
   `python scripts/sdk_renew_state_id.py <asset>` after every patch (`scripts/sdk_code_patch.py` renews it itself). Tell: no
   `Missing cached shadermap for <material>` line in the cook log.
2. **retoc-packed override without the /Game redirect.** The cooked package is named `/<mod>/...`; without a PackageRedirects
   entry the pak mounts, the log is clean and the game loads its own asset. `scripts/zen_add_redirect.py` writes it
   (sdk_cook_mod.py calls it). Game log `Invalid container header` = the redirect was dropped.
3. **A static-switch permutation failed.** The kit's cook still packs and the game draws the grid material. Cook log: `Failed to
   compile Material ... Default Material will be used in game` (`sdk_cook_mod.py` stops on it). Put switch values in the
   PARENT's defaults.
4. **Container fails to mount.** Log: `Failed to mount IoStore container`; the game uses its own assets (`sdk_cook_mod.py` pads
   the `.ucas`; stalker2-paks).
5. **Kit older than the game.** Changed classes read one slot off, no crash: match the versions and re-cook (stalker2-updates).
- Also silent: a GSC Niagara system using module scripts the kit lacks cooks clean and renders nothing (check the editor
  log first, references/niagara.md); a child instance that overrides any static switch has its own cooked shaders, so a
  parent-only change never reaches it (cook the children too).

## Cooking
- The kit's own tools first (they write the redirect). Fallback: `python scripts/sdk_cook_mod.py <mod>` (the cook commandlet
  run directly, `retoc to-zen --version UE5_5`, then the redirect).
- `PakPlainMod.bat` as shipped skips the cook (an EMPTY pak on a new mod) and writes a legacy pak that cannot override.
- Never cook while the kit is open (it locks the cook's cache files); never launch the kit during a cook.
- A second kit mod referenced by the first does not cook (the reference becomes NONE): keep linked assets in one mod.
- Run long cooks detached and poll the log: a cold compile of a big material passes 10 minutes, and an agent shell's
  background job dies with the session.

## Prove a cooked change
- Loud value first (0, 2x, a colour no vanilla scene has), after EVERY packaging change. No visible change = the pak is not
  loading: stop tuning, check the pak and the game log.
- The cook log shows the recompile, and `retoc unpack-raw` of the new trio against the previous one shows a changed shader
  chunk. Constants live in compressed shaders: grepping a cooked file for the float proves nothing.
- Prove each dial once: a value that verifies in the file can still do nothing on screen.

## Smart App Control
Windows Smart App Control blocks kit binaries intermittently: UnrealPak exits 0xC0E90002 with no log, UAT fails within seconds,
a ShaderCompileWorker crash closes the editor, or the launcher stub fails. Details and fallbacks: references/cooking.md; switching it off is the user's call, so offer fallbacks first.

## References
- references/reading-source.md: before reading uncooked assets, uasset-dump, texture settings or material wiring.
- references/editor-gui.md: before kit steps, paste blocks, launching the editor, save checks, or Sequencer.
- references/headless-python.md: before headless Python, or creating a mod or copying GSC assets without the GUI.
- references/live-bridge.md: before starting or calling the opt-in localhost HTTP bridge in the open GUI.
- references/materials.md: before patching constants, Custom node code, instance values, or static switches.
- references/cooking.md: before cooking, packing or splitting a mod, or when cook/pack/kit binaries fail.
- references/cook-performance.md: before speeding up `GSCCookMod` or repacking without cooking.
- references/niagara.md: before reading or editing a Niagara system.
- references/paste-text.md: before generating socket, AnimCollection or other Details-panel paste text.
- references/harness-notes.md: before kit game-system research or adding NEW (non-override) content.
- references/meshes.md: before reimporting a mesh with a missing source path.
