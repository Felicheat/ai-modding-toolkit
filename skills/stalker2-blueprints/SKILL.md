---
name: stalker2-blueprints
description: Writes STALKER 2 mod logic in Blueprints with a Zone Kit that cannot author graphs from code. Generates graph paste text, splits big graphs over pages, catches pastes that silently drop nodes, runs logic in a mod actor without overriding game assets, and covers input, widgets, player and interaction facts and Mod Configuration Menu settings. Use when a mod needs Blueprint logic, a paste compiled but does nothing, or keys and rebinds misbehave.
license: MIT
compatibility: Windows. STALKER 2 Zone Kit; Python 3.8+; PowerShell
metadata:
  pack: STALKER 2 AI Modding Toolkit
  pack-version: "1.0.0"
  author: STALKER 2 AI Modding Toolkit contributors
  verified-on: "STALKER 2 Steam build 26123434 (game 2.1), Zone Kit 2.1.0"
---

# Blueprint logic in STALKER 2 mods

Adapted from the Stalker 2 modding harness by Noah Semus (github.com/noahsemus/stalker2-modding-harness, MIT; the scripts here are
from it and keep its notice). These facts come from its mods and were NOT re-tested for this pack: prove each one in game.
Kit basics and cooking: stalker2-zonekit. Player animation: stalker2-animation.

## The workflow
1. Graphs cannot be authored from Python, only pasted. Ask the user to select a few nodes of the needed types and press Ctrl+C:
   that is the exact pin format for this engine build.
2. Generate the block with `scripts/bp_graph.py` (declare nodes and pins, `graph.link(a, b)` writes both ends, `graph.box(...)`),
   call `graph.layout_tree()` before writing, and save it with `write` from `scripts/bp_t3d.py`. `scripts/t3d_lift.py` lifts real
   nodes out of an exported T3D.
3. A big graph: split it over event graph pages (about 200-800 nodes each) with `Graph.paginate` and hand the pages over
   with `scripts/paste_pages.ps1`, which shows the user one Copy button per changed page.
4. The user clicks into the graph and presses Ctrl+V, then wires only the 1-3 pins that reach outside the block: links to nodes
   not in the paste are dropped. Keep every exec node inside a comment box.
5. Compile, save, export the graph back (`scripts/export_t3d.py`) and compare node and link counts with what you generated.
   Count each graph's `Nodes(n)` list: an export also lists the nodes deleted in this editor session.

## Silent failures: it compiles and does nothing
- A call to a function that does not exist on the named class is dropped; consumers read the pin default. Check every
  `FunctionReference` resolves first (`unreal.find_object(None, "/Script/Engine.<Class>:<Function>")`; inherited functions resolve
  only on the declaring class).
- A call to a BlueprintInternalUseOnly function (such as `Ease`, `Actor.AddComponentByClass`) is dropped: those belong to
  their own K2 node classes.
- A function pasted as pure that is not pure compiles with "was pruned because its Exec pin is not connected" and reads the
  default. Static library functions are impure unless declared pure; `GetConsoleVariableFloatValue` / `IntValue` / `BoolValue`
  are exec nodes in UE 5.5. Put them on the exec chain.
- Two nodes with the same `Name=` in one paste: one is dropped and the exec chain through it ends there.
- An asset default (`DefaultObject=`) resolves only if the asset is loaded in the editor at paste time: hold new assets loaded.
- A struct pin default on a game struct (`PrototypeSID`) came through empty: feed the pin from a variable set on the CDO.
- Cast output pins use the class display name with spaces (`AsDead Body`); a misspelled pin drops its links.
- A pasted `0.0` on a pin whose native default is not zero comes back as the default: feed it from a node.
- A mod-only asset referenced from an override-pass Blueprint is nulled in the cook (stalker2-zonekit, its cooking page).
- `Print String` is stripped in Shipping. Trace with visible effects, or a canary key.

## Where logic lives
Prefer a `ModWorldSubsystem` Blueprint in NewContent that spawns your actor: it overrides nothing, so it cannot conflict.
Keep settings as actor variables with defaults; an optional Mod Configuration Menu provider writes them.

## Console from a Blueprint
- `Execute Console Command` (KismetSystemLibrary) called from a Blueprint works in the shipping game (seen setting render
  cvars on Event BeginPlay; this one fact is from this pack's own mods, not the harness).
- Reading a cvar needs the exec `GetConsoleVariable*Value` nodes above.

## References
- Read references/paste.md before generating paste text, splitting a graph over pages, or when a paste lost something
  (node recipes, every silent drop with its fix, how to check an export).
- Read references/editor.md before any editor Python on assets (duplicate, rename, class defaults, a marker asset), before
  replacing a big graph, and when the editor crashes or loses a headless edit.
- Read references/runtime-input.md before building the subsystem and actor, and before touching input contexts, rebinds
  or widgets.
- Read references/game-facts.md before relying on how the player class, interactions (the campfire sit), the camera,
  sprint and reload or quest doors behave.
- Read references/ui-looting-facts.md before work on the PDA, item pickup, the loot window or other game UI.
- Read references/rendering-facts.md before promising a change to reflections, ray tracing or NPC hair.
- Read references/mcm.md before overriding an asset other mods may share, and before adding Mod Configuration Menu
  settings.

## Traps
- `PC` is the player CHARACTER: `CreateWidget`, input modes and the cursor need `GetPlayerController(0)`.
- Never add member variables or components to a GSC class placed in a cooked level (crash on load).
- Never Ctrl+A / Delete a huge graph in the editor: it can run out of memory. Use pages, or the swap in references/editor.md.
- Never edit an asset headless while the user's editor is open: the editor's next save overwrites the headless edit.
- Do not call a custom event of the same graph from pasted text: the compile fails. Drive it from the tick with a flag.
- Never scan all objects per tick: it stalls the game thread.
- Player animation is owned by stalker2-animation. Read it before any player animation change: `SetAnimInstanceClass`, a
  post-process anim swap during an interaction and several other approaches crash outright.

`scripts/zen_names.py <folder of .uheader>` `[--imports] [--filter REGEX]` lists what a cooked package really references (extract
with `UnrealPak <x>.utoc -Extract <dir>`). Use it on your own builds. `scripts/dump_imc.py` dumps input mapping context rows
in the kit.
