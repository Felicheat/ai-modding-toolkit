# Kit notes from the modding harness: research, plugins, new content

## Contents
- Research order
- Files to grep
- What editor Python adds
- Asking the user to look
- What is worth opening
- Useful asset paths
- The plugin and its GameFeatureData
- Overrides and new content
- The kit's own cook and its output

Another team's Zone Kit workflow: it cooks with the kit's own `GSCCookMod` and ships NEW content next to overrides, which this
pack's own pages do not cover. Reported by that team from its mods; not re-tested for this pack.
Adapted from the Stalker 2 modding harness by Noah Semus (github.com/noahsemus/stalker2-modding-harness, MIT).

## Research order
The kit is both GSC's mod editor (a monolithic Shipping build) and the best available reference for how the game works. For any
new system: (1) grep the kit's files and cfgs, (2) ask the user to open matching assets in the editor, (3) only then build
something.

## Files to grep
| Path | What |
|---|---|
| `<kit>/Stalker2/Content/GameLite/GameData/**/*.cfg` | All game data in GSC's cfg format: prototypes (items, weapons, NPCs, effects, abilities), `CoreVariables.cfg`, `InputMappingContextPrototypes.cfg` (mapping context names, priorities), dialogue, quests (stalker2-gamedata) |
| `<kit>/Stalker2/Config/` | Engine and game ini (for example `DefaultInput.ini`, still with legacy axis mappings) |
| `<kit>/Stalker2/S2_WwiseProject/GeneratedSoundBanks/Windows/Event/*.txt` | Every Wwise event with samples, switch groups, states (the `.txt` form is the compact one) |
| `<kit>/Stalker2/Content/Paks/FullEditor-WindowsModEditor.pak` | The uncooked game content (388 GB). `UnrealPak <pak> -List` lists the index (slow: save it once; `-Filter` does not filter the listing) |
| `%LOCALAPPDATA%/Stalker2/Saved/` | The player's side: `CustomizeControls.cfg` (rebinds), `Config/WindowsEditor/EditorPerProjectUserSettings.ini` (editor), game logs `Logs/Stalker2*.log` |

The harness also keeps a text dump, made with editor Python, of every reachable Blueprint class, function and property (1,677
classes), and greps it first for whether a function or property exists, with its Blueprint signature and access.

## What editor Python adds
- Native ENUM values (`[x for x in dir(unreal.ActionType) if x.isupper()]`), an asset's triggers and modifiers, class function
  lists (`dir(unreal.SomeClass)`). Run read-only snippets before asking the user to look.
- Properties that are not BlueprintVisible / EditAnywhere are invisible to Python: for those, ask the user to open the Details
  panel.

## Asking the user to look
Grep shows names only. Graph wiring, data-asset values, component defaults, pin bindings and references live in the editor.
Ask targeted questions:
- "Content Browser, search `DA_Weapon*`, open the one for the AKM, screenshot the Details panel."
- "Open `BP_X`, Event Graph, Ctrl+F `Reload`, screenshot the wired nodes."
- "Right-click asset W, Reference Viewer, screenshot."
- Better still for graphs: have the user select all (Ctrl+A), copy (Ctrl+C) and send the clipboard text, or export the graph as
  T3D with editor Python (no user needed).
This beats blind iteration: one look at an anim Blueprint showed that a value assumed to be a float was a struct with three
fields.

## What is worth opening
- Real Blueprints: `BP_*`, `AnimBP_*`, widget Blueprints `W_*` (event graphs, anim graphs, state machines, bindings).
- Data assets `DA_*` / `DS_*` (the Details panel is meaningful), anim sequences and montages (Notifies and Curves tracks), input
  mapping contexts and input actions.
- NOT native classes: almost every `/Script/Stalker2` class (`PC`, `CameraModifier_*`, `AnimNotifyState_*`, the `*IPU` input
  handlers, the player controller, `PlayerEnhancedInputComponent`) is C++ with no graph ("C++ Class" in the Content Browser).
  Look for the assets that USE them instead (anim sequences carrying a notify state, data-asset instances of a native class),
  and use the Reference Viewer on assets, not classes.

## Useful asset paths
- Input: `/Game/_Stalker_2/data/input/InputMappingContexts/IMC_*` (`IMC_Exploration`, `IMC_Dialog`, `IMC_DialogOnTheGo`,
  `IMC_PlayerCA`, `IMC_NoInput`, `IMC_Cutscene`, ...), actions under `/Game/_Stalker_2/data/input/InputActions/` (subfolders
  such as `Delayable/`, `Guitar/`).
- Player: `/Game/GameLite/Blueprints/Characters/Player/BP_Stalker2Character` (the pawn, parent `/Script/Stalker2.PC`),
  `/Game/_STALKER2/Animations/Player/AnimBP_Player`, `AnimBP_Player_Shadow`, weapon layers such as `AnimBP_player_bh` (bare
  hands), `AnimBP_PlayerWeaponLayer`, `AnimBP_Player_Knife`.
- Player anim sequences: `/Game/_STALKER2/Animations/Player/AnimSequences/` (items, pda, bpa (backpack),
  contextual_action/...). Skeleton: `/Game/_STALKER2/SkeletalMeshes/SK_stalker_Skeleton`.
- UI: `/Game/GameLite/FPS_Game/UIRemaster/...` (for example `Dialogue/W_DialogueView`, `W_SkipHintView`).
- Kit classes for mods: `ModWorldSubsystem` (stalker2-blueprints), one GameFeatureData per mod.

## The plugin and its GameFeatureData
- A mod is a kit "plain mod" plugin at `<kit>/Stalker2/Mods/<Mod>/` (`<Mod>.uplugin`, `Content/`, `Resources/`). The kit folder
  is the editor's source of truth: mirror it into `<repo>` after every save the user reports.
- Create it with `<kit>/CreatePlainMod.bat <Mod>` (= `RunUAT GSCCreatePlainMod -ModName=<Mod>`), then give the descriptor
  `Category "Game Features"`, `Mod: true`, `ExplicitlyLoaded: true`, `BuiltInInitialFeatureState "Registered"`,
  `CanContainContent: true`.
- The editor discovers a new plugin only at startup, and even then it stays unmounted, in the editor and in the commandlet
  ("Found Mod GameFeature ... without a UGameFeatureData asset ... will not load in Mod Editor"). The kit creates
  `/<Mod>/<Mod>` (actions AddToContentPack, AddConfigsPath `Content/GameLite/ModGameData/<Mod>/`, AddWorldPartitionContent) and
  mounts the plugin when the user picks the mod in the editor's toolbar mod selector.
- Do not duplicate another mod's GameFeatureData: its actions carry that mod's names and are not Python-editable. The editor
  also refuses to delete a GameFeatureData while running: delete the file on disk with the editor closed.
- The toolbar selector also decides which mod "Checkout selected content to mod plugin folder" copies into.

## Overrides and new content
- OVERRIDE a game asset: Content Browser, right-click, "Checkout selected content to mod plugin folder". It is copied to
  `Mods/<Mod>/Content/<same relative path>` and ships in `<Mod>Stalker2-Windows-OverrideContent.*` (mounted at "/"), replacing
  the original at runtime. Per asset, the last-mounted pak wins outright: no merging.
- NEW content lives under `/<Mod>/...` (for example `/<Mod>/Runtime/BP_<Short>Subsystem`) and ships in
  `<Mod>Stalker2-Windows-NewContent.*`. Its paths are unique, so there is no mount-order fight: keep the kit's file name for it.
- Blueprint actor overrides get an `Autogenerated_*_ActorReplacementData.uasset` (a ReplacementMap from game class to mod class,
  applied by `ModActorReplacementSubsystem` at spawn). A plain path override works without it: delete it from Content unless an
  actor override needs it, or it is cooked in.

## The kit's own cook and its output
- RunUAT `GSCCookMod` with `-UnrealExe=<kit>/Stalker2/Binaries/Win64/Stalker2ModEditor-Win64-Shipping-Cmd.exe` (required:
  without it UAT looks for a stock `UnrealEditor-Cmd.exe`), `-TargetPlatform=Win64 -nocompile -nocompileuat`. It takes 5 to 6
  minutes; the editor may stay open; wait about 10 s after the user's save.
- Output: `<kit>/Stalker2/SavedMods/Staged/<Mod>/Windows/{OverrideContent,NewContent}/Windows/Stalker2/Mods/<Mod>/Content/Paks/Windows/`.
- Naming, mount order and installing the result: stalker2-paks. Which list each asset belongs in, and what the cook does with
  unlisted ones: SKILL.md points to the cooking page.
