# Test console: tested commands, status and traps

The user installs a console mod of their choice; Kynes Commands Console (by KynesPeace / ZunaSW, F10) is one that
works. The `X...` commands are the game's own debug commands; a console mod is how they are reached. Status per
command:
- **confirmed**: used in game, syntax as shown.
- **used**: used in game, details unrecorded or partly unclear.
- **unconfirmed**: seen in notes, never run in a recorded test. Try it on a throwaway save first.
- **did not work** / **broken**: run in game, no effect.

"Full list:" in a note quotes the argument names from the full command list of this skill (names as collected, not
tested here).

## Contents
- Items and inventory
- Position and spawning
- Player
- Weather and time
- Emissions
- A-Life
- Quests, variables, markers and the log
- General caveats

## Items and inventory
| Command | Status | Notes |
|---|---|---|
| `XSpawnItemNearPlayerBySID <SID>` | confirmed | Drops ONE item at your feet. For ammo that is one round, not a box. Example SIDs: `GunD12_SG` (a gun), `A012D` (ammo). A spawned gun has no upgrades. |
| `XCreateItemInInventoryByID <SID> 0 <count> <durability>` | unconfirmed | Puts `<count>` items in the inventory; the way to get ammo in bulk. The meaning of the `0` is not recorded. Full list: `PrototypeID ObjUID Count Durability`, example `XCreateItemInInventoryByID Milk 0 1 1`. |

SIDs are cfg record names (item prototypes, ammo prototypes); finding the right record: stalker2-gamedata.

## Position and spawning
| Command | Status | Notes |
|---|---|---|
| `XShowPlayerCoordinates` | confirmed | Prints your position. Units are centimetres. |
| `XSpawnObjBySID <ObjPrototype SID> Veteran false X Y Z 0 0 0` | confirmed | Spawns a creature or NPC at X Y Z (cm). Add 1500 to X for 15 m away. `Veteran` is the rank; the `false` and the last three numbers were used as shown (likely a flag and a rotation; unconfirmed). Full list: `PrototypeSID Rank bDestroyOnOffline Px Py Pz Pitch Yaw Roll`; its example writes rank and flag as numbers (`XSpawnObjBySID GeneralNPC_Duty_Stormtrooper 2 0 0 0 0 0 0 0`). |
| `XTeleportTo ...` | unconfirmed | Teleport for fixed screenshot spots; arguments not recorded. Full list: `XCoord YCoord ZCoord`. |

- No negative coordinates: pick a spawn point whose X Y Z stay positive.
- A misspelled SID CRASHES the game. SIDs are case-sensitive: `Blinddog`, not `BlindDog`.
- Mutant SIDs are ObjPrototypes record names: `Flesh`, `BoggyFlesh`, `Boar`, `Blinddog`, `Bloodsucker`, `Chimera`,
  `Pseudogiant`, `Burer`, `Snork`.

## Player
| Command | Status | Notes |
|---|---|---|
| `XSetGodMode true` | did not work | Plan tests that do not need it. Hover above the scene with noclip instead (use the noclip your console tool provides). The full list gives `XSetGodMode true` as an example without a failure note, and names the game's own noclip `XSetNoClipGSC bNoClipGSC Speed` (not run here). |

## Weather and time
Weather names (EWeather): `Clearly`, `Cloudy`, `Fogy`, `LightRainy`, `Rainy`, `Thundery`, `Stormy`, `CalmBeforeEmission`,
`Emission`. Spell them exactly so (`Fogy` has one g).

| Command | Status | Notes |
|---|---|---|
| `XForceWeather <Weather>` | confirmed | Snaps to the weather instantly and clears any running blend. It also RESTARTS the weather sound. |
| `XSwitchToWeather <Weather>` | confirmed | Blends to the weather like a natural change, using the transition the game defines for that pair. Use it to test transitions. |
| `XSetWeatherTime hh mm ss` | confirmed | 24-hour clock, three numbers: `XSetWeatherTime 20 45 00`, `XSetWeatherTime 04 15 00`. Never decimal hours (`20.75` is wrong). |

- The clock keeps running after `XSetWeatherTime` (game speed: stalker2-gamedata): repeat the command when the exact hour
  matters.
- Auto exposure keeps adapting for a few seconds after a time or weather switch (longest at night).

## Emissions
| Command | Status | Notes |
|---|---|---|
| `XStartEmission` / `XStopEmission` | used | A real emission event: siren, damage and a red post-process. `XForceWeather Emission` sets the emission weather without the event. |

## A-Life
| Command | Status | Notes |
|---|---|---|
| `XSpawnALifeDirectorScenario <ScenarioSID>` | unconfirmed | Starts a Director scenario by its SID, e.g. `HumansEnemyMoveToAllyLair`, `BlinddogPackSmall`. |
| `XRunAttackLair`, `XCaptureLair` | unconfirmed | By their names: start an attack on a lair, capture a lair. Arguments not recorded. |
| `XShowUnitAndSquadUIDs` | unconfirmed | By its name: shows unit and squad ids. Full list: takes `Radius`. |
| `XALifeKillAll` | unconfirmed | By its name: kills the A-Life population, a way to reset a scene. Save first. |

## Quests, variables, markers and the log
| Command | Status | Notes |
|---|---|---|
| `XPrintGlobalVariable SID` | broken | Prints nothing in the in-game console. Do not use it to read quest or global variables; check the effect in game (a spawn, a branch, a debug fade-screen node). |
| `XEnd*`, `XReset*`, `XExclude*`, `XSkipToQuestNode` | destructive | `XEndQuestBySID <quest>` sent for several quests whose `ConsoleCommand` nodes were mid-flight crashed the game. Describe the command and its risk and let the user decide; prefer a throwaway save. |
| `XDiscoverMarker`, `XListMapMarkers`, `XRevealAllMarkers` | empty | They do nothing in the shipping game (map markers: stalker2-gamedata). |

- Commands also run from quest data: a quest node `NodeType = EQuestNodeType::ConsoleCommand` with
  `ConsoleCommand = <command line>`. Vanilla uses it (`XStartQuestNodeBySID <SID>`,
  `XDeactivateAIFeature ALifeDirector`, `XSwitchPlayerRank Master`, even `setbind x xkillnpcinradius ...`; see the
  kit's `QuestNodePrototypes/*.cfg`). A mod can drive repeated work through a few such nodes and avoid quest-node
  fan-out (the save name limit: stalker2-saves).
- `Stalker2.log` holds no lines about the game itself or mods: no console commands, effects, quest nodes or mod
  subsystems. Verify a command by its in-game effect.

## General caveats
- A screenshot does not record which command was active. Give the user a fixed order of commands and shots.
- Console variables and Engine.ini edits are not a mod fix: players do not get them from a pak. Use them to diagnose at most,
  and only when the user agrees.

The "Quests, variables, markers and the log" section and every "Full list:" note:
Adapted from the Stalker 2 modding harness (github.com/noahsemus/stalker2-modding-harness, MIT, copyright Noah Semus); this part was contributed there by sdwvit.
