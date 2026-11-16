# WAAPI (Wwise Authoring API) over HTTP

Adapted from the Stalker 2 modding harness (github.com/noahsemus/stalker2-modding-harness, MIT, copyright Noah Semus); this part was contributed there by sdwvit.

## Basics
Wwise Authoring serves WAAPI by default (HTTP **8090**, WAMP / WebSocket 8080). No client library is needed: POST
JSON to `http://127.0.0.1:8090/waapi`. `python scripts/waapi.py <uri> [args-json|@file] [--return id,name,path]
[--port 8090] [--timeout 600]` wraps it (`@file.json` is handy in PowerShell, whose quoting mangles inline JSON).
- The body is always `{"uri": ..., "args": {...}, "options": {...}}`. Errors come back as
  `{"uri":"ak.wwise.error...", "message":...}`; an empty `{}` is success for setters. Smoke test:
  `ak.wwise.core.getInfo`.
- `options.return` picks fields: `id`, `name`, `type`, `path`, `parent`, `parent.name`, `originalFilePath`,
  `duration`, `@<Property>` (for example `@Target` on event actions).
- **Edit through WAAPI, never by writing `.wwu` files while Wwise is open** (reload prompt, lost state). Finish with
  `ak.wwise.core.project.save`.
- **No GUI**: `WwiseConsole.exe waapi-server <wproj> --http-port 8090 --wamp-port 8080` serves the same API; stop it
  after `project.save`. `WwiseConsole.exe generate-soundbank <wproj> --platform Windows` builds banks.

## Recipes (args JSON)
| Goal | uri | args |
|---|---|---|
| Find containers by name | `ak.wwise.core.object.get` | `{"from":{"path":["\\Actor-Mixer Hierarchy"]},"transform":[{"select":["descendants"]},{"where":["name:matches","^Radio_"]}]}` |
| Event actions and targets | `ak.wwise.core.object.get` | `{"from":{"ofType":["Event"]},"transform":[{"where":["name:matches","^SFX_RadioTable_X_"]},{"select":["children"]}]}` with return `id,parent.name,@Target` |
| Clone a container (keeps bus, attenuation, loop, children) | `ak.wwise.core.object.copy` | `{"object":"<srcId>","parent":"<parentId>","onNameConflict":"rename"}`, then `ak.wwise.core.object.setName` `{"object":"<newId>","value":"Radio_New"}` |
| Swap a Sound's audio, keep its settings | `ak.wwise.core.object.delete` the old AudioFileSource, then `ak.wwise.core.audio.import` | `{"importOperation":"useExisting","default":{"importLanguage":"SFX"},"imports":[{"audioFile":"<kit>\\O\\SFX\\S2_Live\\Track.wav","objectPath":"\\Actor-Mixer Hierarchy\\...\\Radio_New\\<Sound>Track","originalsSubFolder":"S2_Live"}]}` |
| Retarget an event action | `ak.wwise.core.object.setReference` | `{"object":"<actionId>","reference":"Target","value":"<containerId>"}` |
| Save | `ak.wwise.core.project.save` | `{}` |
| Open another project | `ak.wwise.ui.project.open` | `{"path":"<...>.wproj","bypassSave":true}` |

- After an import, check the source's `duration` matches the WAV. Source-level trims and loop points (`TrimBegin`,
  `LoopBegin`) are lost with the deleted source.
- Import from a path inside the Originals folder. A failed import ("File not found") leaves an empty source; placing
  the file at the source's `originalFilePath` afterwards also works.

## Generating banks through WAAPI: the trap
`ak.wwise.core.soundbank.generate` with `soundbanks:[{"name":"<Event>"}]` does **not** select an auto-defined event
bank: it creates an empty 48-byte user-defined bank of that name and regenerates all of the roughly 55k auto-defined
banks (about 30 minutes, WAAPI blocked throughout).
- Untested ways to keep the run small: `events` inside the soundbank entry, or a user-defined bank.
- `writeToDisk:false` is a dry run.
- Read the `logs` field of the reply for errors.
- The official route (F7 in Wwise, or the SoundBank layout with only your work units checked) and
  `WwiseConsole.exe generate-soundbank` are the alternatives.
