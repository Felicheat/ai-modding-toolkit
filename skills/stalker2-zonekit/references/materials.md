# Materials: offline retuning, instances, compile errors

## Contents
- Byte patching a constant or a parameter default
- StateId renewal (or the old shaders ship)
- Custom node code replaced offline (the same-length rule)
- Growing a Custom node with headless Python
- Checking new Custom code before the user pastes it
- Material instances and static switches
- Per-copy instance values
- Compile errors
- What a material edit recompiles
- Proving each dial
- Blueprint pin defaults offline

## Byte patching a constant or a parameter default
Once the user has checked an asset out in the GUI, many retunes need no editor: a material Constant is one float32 in the
checked-out `.uasset`.
1. Dump the asset (uasset-dump) and find the node's export; note the value it reports and the export's byte range
   (`SerialOffset`, `SerialSize`).
2. Find that float inside the range (it must occur exactly once there), write the new value in place, dump again and check.
3. Renew the StateId (next section), then cook.
- A ScalarParameter's default is patched the same way. Find its node by `ParameterName`, never by object name (a GUI save
  renumbers object names and moves every offset).
- To make constants easy to find after a GUI save, ask the user to type unique values in the editor (0.6, 1.001), then set the
  real ones offline.
- Close the asset in the kit before patching it offline.
- The pack's patch scripts write `<file>.bak` before changing a binary file unless you pass `--no-backup`. Keep the user's
  `<repo>` backup as well: the kit folder holds the only other copy.

## StateId renewal (or the old shaders ship)
- The cook takes a material's compiled shader map from the DDC, keyed by the material's StateId (a 16-byte FGuid in the material
  export). Only an editor save renews it. Patch a value without a new StateId and the cook packs the OLD shaders, silently: what
  the user then judges in game is the previous value.
- After every byte patch: `python scripts/sdk_renew_state_id.py <asset .uasset>`. It writes a random new StateId and reads it
  back. `scripts/sdk_code_patch.py` renews it on every write by itself.
- Proof in the cook log: `Missing cached shadermap for <material> ... compiling`. No such line = no recompile = no change.
- Material INSTANCE value patches need no StateId renewal (the values are not compiled into the parent's shaders).

## Custom node code replaced offline (the same-length rule)
A Custom node's code is one ANSI string in the node's export (int32 length including the terminator, then the bytes), stored
once in the file. It can be rewritten without the editor, by a byte patch:
- The new code must NOT be longer than the saved string. Pad it with spaces to the saved byte length and keep the editor's
  trailing line break, so no offset in the package moves.
- The node's INPUTS must stay the same in a byte patch. Give a new Custom node every dial it may ever need as an input from the
  start; a new input later means headless Python (next section) or a paste in the GUI.
- Running out of room: dropping the space after `;` and `,` buys about 100 bytes. Beyond that the node has to grow: with
  headless Python (next section), or by re-pasting it in a kit sitting with longer code.
- A byte diff against the saved asset must show exactly the StateId, the code and any patched floats. Anything else is a bug.
- The tool:

      python scripts/sdk_code_patch.py <full .uasset path> --list                     Custom nodes (by title) and their code sizes
      python scripts/sdk_code_patch.py <full .uasset path> --show <title>             print a node's saved code
      python scripts/sdk_code_patch.py <full .uasset path> --code <title> <file>      write new code (line breaks become CRLF)
      python scripts/sdk_code_patch.py <full .uasset path> --set <param>=<value>      a ScalarParameter default (repeatable)

  Every write renews the StateId and is read back. Then cook.
- Custom code can use `Parameters.SvPosition`, `Parameters.WorldPosition_CamRelative` and `SvPositionToResolvedTranslatedWorld()`
  (Common.ush): they compiled in every permutation of a cook.

## Growing a Custom node with headless Python
The same-length rule is a limit of the offline byte patch, not of the node.
- Shown once, on a material already in the mod, kit closed: a headless editor Python script appended one entry to the Custom
  node's `inputs`, wired it with `connect_material_expressions`, set `code` to a longer string, read the code and every wire
  back (the old wires were unchanged), then ran `recompile_material` and `save_loaded_asset`. The save succeeded, and the
  node afterwards took same-length offline rewrites up to its new size. End the longer code in a spare comment: it is room
  for later offline rewrites.
- Not shown: a longer string written by a byte patch (`sdk_code_patch.py` still refuses one), and the same edit on a `/Game`
  asset that is not in the mod (a headless run cannot save it). Growing an existing node has been done on one material only:
  read the code and the wires back before saving, and prove the result in game with a loud value.
- How to run such a script: SKILL.md names the headless Python page.

## Checking new Custom code before the user pastes it
A compile error costs a kit sitting (or a headless round). Compile the HLSL offline first: wrap the code in a small function
with stub declarations for what it uses (Parameters, View, the texture sample helpers) and compile it with the kit's own
`<kit>/Engine/Binaries/ThirdParty/Windows/DirectX/x64/d3dcompiler_47.dll` (FXC, profile ps_5_0, for example through ctypes). Feed
the stubs non-constant inputs, or constant folding reports "division by zero" warnings that the real material never has.

## Material instances and static switches
- An instance that overrides a **static switch** gets its own shader permutation and needs its OWN shader map. If that permutation
  fails to compile, the cook still packs, the log looks normal unless you search it, and the game draws the engine's default grid
  material in its place.
- Fix: put the switch values in the PARENT material's defaults and leave the instance's switches unticked, so both share one
  shader map.
- A material whose switch default is False never compiles the True branch, so errors in that branch only appear through an
  instance. To see them, flip the default in the editor and Apply.
- The cook log line is `Failed to compile Material ... Default Material will be used in game`. Stop the build on it
  (`scripts/sdk_cook_mod.py` does; the kit's own cook packs anyway).
- A child instance that overrides ANY static switch has its own cooked shaders: changing only its parent never reaches the
  game for that child. Every such child must be cooked in the mod as well, and each one carries its shaders, so the pak grows
  with their number.

## Per-copy instance values
Instance values can be patched offline, after the parameter is ticked as an instance override once in the GUI (headless
editor Python can set instance values directly instead):
- In the checked-out instance, `ScalarParameterValues` / `VectorParameterValues` hold one struct per overridden parameter. The
  float sits 25 bytes after that struct's own `ParameterValue` FName tag; a LinearColor sits 49 bytes after it.
- Locate structurally: the parameter's name tag first, then the next `ParameterValue` tag. Check the value you find. Never search
  for the value's bytes (a 0.0 matches the wrong zero).
- No StateId renewal needed.

## Compile errors
- Common: `Arithmetic between types float4 and float3`. A Material Parameter Collection vector is RGBA (float4); a
  VectorParameter's main pin is RGB. Put a Component Mask (R G B) between them.
- Errors show in the editor's Stats panel and as a red ERROR! banner on the node.

## What a material edit recompiles
- Material functions cook to stubs (their code is compiled into the materials that call them). An edit in a base material
  recompiles the base and every instance that has its own permutation (one shader map each; the cook log lists them).

## Proving each dial
Prove every new dial once in game, not only the pak: an instance value that verifies in the file and changes the cooked package
can still do nothing on screen. A size or colour change riding in the same pak shows that the pak itself loads.

## Blueprint pin defaults offline
A pin default is a plain string in the uncooked `.uasset`: replace it with a SAME-LENGTH string, one occurrence, kit closed. The cook
recompiles the Blueprint; prove it by comparing the cooked `.uexp` with the previous cook, because uasset-dump cannot read cooked bytecode.
