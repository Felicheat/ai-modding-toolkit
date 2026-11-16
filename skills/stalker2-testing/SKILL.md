---
name: stalker2-testing
description: Tests STALKER 2 mods in game with a console mod (items, spawning, coordinates, weather and time, emissions, A-Life, quest, dialog and debug-draw commands) and designs test paks that settle a question (a loud canary, a control first and last, one variable per pak). Use when planning an in-game test, writing console commands or test steps for the user, or when a test looked different, did nothing or gave mixed results.
license: MIT
compatibility: A console mod of the user's choice installed in the game (Kynes Commands Console by KynesPeace / ZunaSW is one that works)
metadata:
  pack: STALKER 2 AI Modding Toolkit
  pack-version: "1.0.0"
  author: STALKER 2 AI Modding Toolkit contributors
  verified-on: "STALKER 2 Steam build 26123434 (game 2.1), Zone Kit 2.1.0"
---

# Testing STALKER 2 mods in game

The user installs a console mod of their choice; Kynes Commands Console (by KynesPeace / ZunaSW, F10 opens it) is one
that works. The console spawns items and creatures, sets weather and time and starts events, so a test reaches its
scene in seconds instead of an hour of play.

## Most used commands
| Task | Command | Watch out |
|---|---|---|
| Item at your feet | `XSpawnItemNearPlayerBySID <SID>` | ONE item: for ammo, one round. A spawned gun has no upgrades. |
| Items in the inventory | `XCreateItemInInventoryByID <SID> 0 <count> <durability>` | Not run in a recorded test. |
| Where am I | `XShowPlayerCoordinates` | Centimetres. |
| Spawn a creature or NPC | `XSpawnObjBySID <SID> Veteran false X Y Z 0 0 0` | cm (X + 1500 = 15 m away). No negative coordinates. A misspelled SID crashes the game (`Blinddog`, not `BlindDog`). |
| Weather, instantly | `XForceWeather <Weather>` | Clears a running blend and restarts the weather sound. |
| Weather, blended | `XSwitchToWeather <Weather>` | A natural transition: use it to test blends. |
| Time | `XSetWeatherTime hh mm ss` | 24 h, three numbers: `XSetWeatherTime 20 45 00`. Never decimal hours. |
| Emission | `XStartEmission` / `XStopEmission` | Real event (siren, damage, red post-process). For the weather alone, `XForceWeather Emission`. |
| A-Life scenario | `XSpawnALifeDirectorScenario <ScenarioSID>` | Unconfirmed. |

Weather names: `Clearly`, `Cloudy`, `Fogy`, `LightRainy`, `Rainy`, `Thundery`, `Stormy`, `CalmBeforeEmission`, `Emission`.
**God mode (`XSetGodMode true`) may not work: plan tests around noclip**, hovering above the scene.

Read references/commands.md before using any command not in this table, when a command fails or crashes, before a
quest command (some are broken or destructive), and before weather, time, sound or A-Life tests (the running clock, exposure,
sound restarts, every unconfirmed command).

Read references/command-list.md before guessing a command name or its arguments: the game's full list by topic
(quests, NPCs, player, items, world, dialogs and UI, saves, debug draws). It gives names, not test results.

## Test pak design
- **Loud canary first.** A value vanilla cannot produce (an item that weighs 500 kg, a price of 1, a bright red material). It
  proves the change reaches the game before any subtle value is judged. Repeat it after every packaging change.
- **Control first and last.** The same scene without the test pak (or with the unchanged variant) before and after: it catches
  drift and a defect that every build carries.
- **One variable per pak.** Name each pak after its variable so the user can see which one is in.
- Write PASS and FAIL before the test: what each would look like and what you do next. If you cannot, the test is not ready.
- **Ship only measured values.** Walk down from the canary to a shippable value in game; never ship an unmeasured "safer" cut.
- A loose `_<N>_P` pak tests one file over a deployed mod (naming and priority: stalker2-paks). The game locks its paks: the
  user closes it to swap them.
- **Remove every test pak before judging a release build.**

## Scene variance
- One "it looked different" run is not proof when the scene itself varies (AI choices, spawns, weather, cloud drift). Two
  unrelated test paks can both "show" the same effect by chance.
- Prove a lever with a canary that cannot be mistaken, repeated (twice at least), then judge smaller values.
- Count instead of eyeballing where you can: hits, seconds, metres, how many times out of ten.
- Bisecting by removing paks finds nothing when the defect is in every build; the control (mod removed) shows it.

## Reading results
- A loud value that shows no change: the change is not loading, or the lever is not connected. Stop tuning; check the pak
  (stalker2-paks, stalker2-zonekit) and the lever.
- A failed prediction is a result: say so, work out what the change really did.
- Unknown multipliers can sit between a value and its effect (the difficulty setting scales weapon damage): measure the
  vanilla baseline in the same scene first.
- When the user's verdict and a measurement disagree, check the measurement first.
- Say which results were measured and which are inferred.

## Writing test steps for the user
- One line per step: the exact command, where to look, and the ONE thing to note, at the moment the user does it. Questions
  in a list after the steps get missed.
- Fixed order of commands and shots (a screenshot does not record which command was active); control first and last.
- Times always as `hh mm ss`. The clock keeps running after `XSetWeatherTime`: repeat it when the exact hour matters.
- Background and risks go above the steps in two or three short lines.
