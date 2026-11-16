# Paste text: details, big graphs, node recipes, silent drops

Adapted from the Stalker 2 modding harness by Noah Semus (github.com/noahsemus/stalker2-modding-harness, MIT).

## Contents
- The text format and the clipboard
- Asset references in a paste
- Big graphs: split them over event graph pages
- Readable layout
- Node recipes
- What a paste drops without an error
- Checking the paste

## The text format and the clipboard
- Graph nodes copy and paste as plain text: `Begin Object Class=/Script/BlueprintGraph.K2Node_... Name="..."`, one
  `CustomProperties Pin (...)` line per pin, links as `LinkedTo=(NodeName PinId,)`, `End Object`. Proven for blocks of
  20-200 nodes, in event graphs and anim graphs.
- Read what the user copied with PowerShell `Get-Clipboard -Raw`. Put your block on the clipboard with
  `Set-Clipboard -Value (Get-Content <file> -Raw)`.
- `scripts/bp_graph.py` builds on `scripts/bp_t3d.py` (pin and type strings, fresh 32-hex GUIDs): `Node(graph, class, name,
  x, y, comment, body)`, `node.pin(name, category, ...)`, `graph.link(a, b)` (written on both ends), `graph.box(...)`,
  `graph.text()` returns the lines for `write`.
- `scripts/t3d_lift.py` lifts real nodes out of an exported T3D (for example the game's own AnimGraph nodes with their nested
  binding sub-objects), renames them, gives every pin a fresh id and lets you relink them.
- Links to nodes that are not in the paste are dropped: keep external wiring to 1-3 pins and name those pins exactly.
- Put `NodeComment` labels and comment boxes in the generated text. Keep mod-specific generators in `<repo>`.

## Asset references in a paste
Asset defaults (`DefaultObject="/<Mod>/.../AS_X.AS_X"`) resolve only for assets LOADED in the editor at paste time. An
unloaded one is dropped silently: empty pin, compiles fine. Assets you just built with editor Python are garbage-collected
once nothing references them (seen: 28 new animations came through empty; the ones the Blueprint already referenced were
fine).
- Before handing over a paste with new asset references, load and hold them from the OPEN editor's Python:
  `builtins._keep = [unreal.load_asset(p) for p in paths]` (the interpreter persists).
- After the save, check the export for each `DefaultObject`.

## Big graphs: split them over event graph pages
Deleting a 3,700-node graph crashed the editor every second time in a session. Keep each paste, and each delete, small.
- `Graph.paginate(roots, default, prefix, self_class)` returns `{page: Graph}`. `roots` is `[(page, [exec nodes])]` in
  priority order: an exec node belongs to the first page whose start nodes reach it along exec links, else to `default`.
- Every exec link between pages becomes a call (`K2Node_CallFunction`, self) to a custom event on the target page, named
  `<prefix><page>_<n>`. Calls are synchronous: the order of execution is unchanged.
- Shared pure trees are cloned per page. Pure nodes nobody reads are dropped. A comment box goes to the page holding most
  of its exec nodes.
- A data link from an exec node's output to another page raises an error: keep both ends on one page, or pass the value
  through a variable. A bound event's `OutputDelegate` must sit on its bind node's page.
- Write one `.txt` per page plus a `pages.json` of `page_digest(lines)` values:
  `{"<page>": {"file": "<page>.txt", "nodes": <count>, "digest": "<digest>"}}`. The digest ignores node names, pin ids,
  GUIDs, positions and box sizes, so a build marks only pages whose content really changed.
- `scripts/paste_pages.ps1 -Dir <dir>` opens a small always-on-top window for the user with one Copy button per CHANGED
  page (compared with `pasted.json` in the same folder; `-All` marks every page). Start it yourself:
  `Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','scripts/paste_pages.ps1','-Dir','<dir>'`.
  After the user says done and you have checked the paste, copy `pages.json` over `pasted.json`.
- Pages are made once by hand: My Blueprint > Graphs > +, named as the page. Python cannot add event graph pages.
- For each changed page the user opens that graph tab, clicks inside, Ctrl+A, Delete, Ctrl+V. The main page (the calls)
  goes last. Then File > Refresh All Nodes, Compile, Save.
- The first switch from one big graph to pages: on a freshly opened editor delete everything in the old graph FIRST (its
  custom events would collide with the pasted ones and get renamed), then paste the pages.
- Aim for pages of about 200-800 nodes.

## Readable layout
Call `graph.layout_tree()` before writing (a user judged it the best layout). It:
- clones every pure node that feeds more than one pin (pure nodes are re-evaluated per use anyway), so each data input sits
  next to the node that uses it. Set `graph.untangle_limit = <n>` to clone only pure nodes whose upstream pure tree has at
  most n nodes: deep shared trees otherwise multiply into thousands of nodes;
- runs the exec chain left to right on a row inside each comment box, each exec node's data inputs as a small tree to its
  left; Branch false and Sequence then_1.. open rows below; chains longer than `max_row` wrap;
- places the boxes along the flow: a box entered from another box sits to its right, boxes fed by one box are stacked in
  the order of the pins that feed them, unfed boxes (events) start new groups; boxes are resized to fit.

Generator rules that keep it readable:
- Put every exec node inside a comment box (hand coordinates only choose the box). An input event and its chain need a box
  of their own.
- Never wire one exec output (a cast's `As X`, a spawn's `Return Value`) to many places: store it in a variable right after
  the exec node and read the variable at each use (one getter per use), or the wires fan out across the whole graph.
- `layout()` (a plain column grid) is kept only for comparison; it was harder to follow.

## Node recipes
- **Delegate binding pastes fine**: `K2Node_AddDelegate` (`DelegateReference=(MemberParent=<class>,MemberName=...)`, a
  `Delegate` pin whose `PinSubCategoryMemberReference` names the `..._DelegateSignature` in its package) linked to a
  `K2Node_CustomEvent` whose parameters come from `CustomProperties UserDefinedPin (PinName=...,PinType=(...),
  DesiredPinDirection=EGPD_Output)`. Bind once per target object (keep the bound object in a variable and compare).
  `AnimInstance.OnMontageStarted` binds this way.
- **ForEachLoop**: `K2Node_MacroInstance` with `MacroGraphReference=(MacroGraph="/Script/Engine.EdGraph'/Engine/
  EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop'",GraphBlueprint=...StandardMacros'",
  GraphGuid=99DBFD5540A796041F72A5A9DA655026)` (GUID read from the kit's
  `Engine/Content/EditorBlueprintResources/StandardMacros.uasset`),
  `ResolvedWildcardType=(PinCategory="object",PinSubCategoryObject=<class>)`, pins `Exec`, `Array` (container Array),
  `LoopBody`, `Array Element`, `Array Index`, `Completed`.
- **Adding a component**: `Actor.AddComponentByClass` is BlueprintInternalUseOnly. Write the `K2Node_AddComponentByClass`
  node: pins `self` (the actor), `Class` (DefaultObject = the component class), `bManualAttachment`, `RelativeTransform`,
  `ReturnValue`, plus execute / then, like `K2Node_SpawnActorFromClass`. Its ReturnValue comes back typed by the Class pin,
  so a cast after it only draws an "already a ..." note.
- **Purity** after a paste comes from the UFunction (`bDefaultsToPureFunc`), not the pasted `bIsPureFunc`: write `const`
  getters (BlueprintCallable const = pure) without exec pins and static library calls with them, or the reconstructed node
  drops the exec links.
- **Enum pin defaults**: a pin default written right after `PinName` survives for string pins, but an enum pin's is reset
  on paste. Write `DefaultValue=` where the editor does (after the `PinType...` fields, before
  `AutogeneratedDefaultValue`), and never regex-match `DefaultValue=` inside `AutogeneratedDefaultValue=`.
- **A pure cast** (`K2Node_DynamicCast`, `bIsPureCast=True`) comes in as an exec cast: wire its exec pins.
- **Same-graph custom events**: do not call a custom event of the same graph from pasted text. The paste asks to "Fix Self
  Context Function References" and the compile fails ("In use pin no longer exists"). Drive the follow-up from the tick (a
  flag or a timestamp checked each tick). (`paginate` calls custom events on other pages, and the page holding the calls
  is pasted last.)

## What a paste drops without an error
The graph still compiles in every case below.
- **A call to a function that does not exist on the named class**: its consumers read the pin default. Seen: `SelectString`
  named on `KismetStringLibrary` (it lives in `KismetMathLibrary`); an asset path came out empty and every use loaded the
  fallback animation for seven builds. Check every `FunctionReference` resolves in the editor first
  (`unreal.find_object(None, "/Script/Engine.<Class>:<Function>")`; inherited functions such as `GetSocketLocation` resolve
  only on the declaring class), and after the paste compare function counts of the export with the paste.
- **A call to a BlueprintInternalUseOnly function**: no error, its links vanish. `KismetMathLibrary` `Ease` / `VEase` /
  `REase` belong to the `K2Node_EaseFunction` node; ease by hand (`alpha * alpha` + `VLerp`).
- **A function pasted as pure that is not pure** is pruned at compile and its output reads as the default; the compiler
  warns "<node> was pruned because its Exec pin is not connected". Static library functions are impure unless declared
  BlueprintPure: `KismetMaterialLibrary.GetScalarParameterValue` read 0 this way, and `KismetSystemLibrary`
  `GetConsoleVariableFloatValue` / `IntValue` / `BoolValue` are exec nodes in UE 5.5. Give such a call `execute` / `then`
  pins, put it in the exec chain and keep its result in a variable.
- **Two nodes with the same `Name=` in one paste**: one is dropped and the exec chain through it ends there. Seen: lifted
  nodes numbered 920+k / 930+k / 940+k collided past 10 settings; a register chain stopped at setting 11 and a later call
  never ran. Assert unique names in the generator, and after the paste count the calls in the export.
- **A struct pin default on a game struct came through empty**: `CppMediator.StartQuestNode`'s `SID` pin (struct
  `/Script/Stalker2.PrototypeSID`, const-ref, text form `(Value="X")`), pasted as `DefaultValue="(Value=\"X\")"` where the
  editor writes it, showed `(Value=\"\")` in the export after the paste and Refresh All Nodes, while string defaults on the
  same nodes survived. Feed such pins from a member variable of that struct type whose default is set on the CDO from
  Python (`v = unreal.PrototypeSID(); v.import_text('(Value="X")')`), and check the export or the CDO after.
- **An asset default for an unloaded asset** (see above).
- **Cast output pin names** use the class display name with spaces: `AsInput Mapping Context`,
  `AsInteractable Item Container`, `AsDead Body`. A misspelled pin drops its links.
- **A pasted `0.0` on a function pin whose native default is not zero** comes back as the default (for example
  `Montage_SetPlayRate.NewPlayRate` = 1.0): feed such values from a node output.

## Checking the paste
- **An asset export also contains the nodes deleted in this editor session**: the undo buffer keeps them and a garbage
  collection does not drop them. They come out with the graph's path like live nodes, so counting `Begin Object` lines per
  graph overcounts after every Ctrl+A / Delete / paste (a 754-node page "had" 2968). Count the graph's own `Nodes(<n>)=`
  list (the live nodes) and read compiler messages only from nodes in it.
- Match exported nodes to generated ones by function + comment, not by node name: the editor renames nodes that collide
  with deleted, not yet garbage-collected ones.
- Because exports carry deleted nodes, verify pin VALUES in game, not in an export.
- `scripts/export_t3d.py` writes the export (see its header for how to run it in the kit).
