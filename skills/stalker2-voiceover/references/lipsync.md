# Lip-sync for new lines, and running the editor scripts

Adapted from the Stalker 2 modding harness (github.com/noahsemus/stalker2-modding-harness, MIT, copyright Noah Semus); this part was contributed there by sdwvit.

## What the tools do
Vanilla face anims are `AnimSequence` assets on `SKEL_fac`: float curves and bone tracks, 60 frames per second (EN)
or 30 (UA), no head or body motion. The tools learn audio to face channels from one vanilla speaker's own lines and bake
new anims from copies of that speaker's anims. One fitted speaker's model can serve every NPC speaker in a mod.
The player has no face anims (`fit_lipsync.py` skips speaker `pc`).

## Steps
1. **Pick a speaker**: a folder of their `AS_FAC_*` anims under `/Game/_STALKER2/Animations/CharacterHead/...` (for
   example `Hubs/<Hub>/<speaker>`) whose voice WAVs exist as
   `<kit>/O/Voices/<English(US) or Ukrainian(UA)>/S2_Live/VO_<speaker>_<key>.wav` under the same keys. More lines
   fit better.
2. **Dump** (editor, read-only): `scripts/dump_face_anim.py` with `VANILLA` (that folder) and `OUT` (a work folder).
3. **Fit** (shell): `python scripts/fit_lipsync.py <dump> <kit>/O/Voices <new_lines> <pred.json>`. `<new_lines>`
   holds the padded takes as `en/VO_<speaker>_<PhraseSID>.wav` and `uk/...` (integer PCM WAVs, any rate, mono or
   stereo).
   - Method: ridge regression from 40-band log-mel frames (6 frames of context on each side) to each face channel.
     Channels with held-out correlation above 0.35 are driven by audio (the script prints them); the rest come from
     a base anim (the shortest vanilla line at least as long).
   - It overwrites `<pred.json>`. To extend a set, fit the new lines into a scratch file and merge its `anims`.
   - It needs only numpy. The kit's embedded Python
     (`<kit>/Engine/Binaries/ThirdParty/Python3/Win64/python.exe`) ships it (numpy 2.0.2 seen); any Python 3.11
     with numpy also works.
   - Not yet re-verified in game: the original fit was torch / torchaudio based; this version computes the same
     features in numpy and was smoke-tested on synthetic data only.
4. **Bake** (open editor, saves assets): `scripts/create_face_anims.py` with `PRED`, `VANILLA`, `DEST`, pasted
   into the Output Log. It builds 10 anims per run (one run over everything stalled after about 20): paste again
   until the log says `done; 0 left`. Copies are forced to 30 frames per second before resizing, or an EN base (60)
   plays the line at double speed. Existing anims are skipped: delete one to rebuild it. Its log is `face_anims.txt` next to
   `PRED`.
5. Wire the anims into `<ChainSID>_FaceAnimation`. Check in the anim viewer on the speaker's head, then in game.

The speaker name in `AS_FAC_<L>_<speaker>_<SID>` must have no `_` (the tools split on it).

## Running the editor scripts
`probe_voiceover_keys.py`, `dump_face_anim.py` and `create_face_anims.py` run inside the Zone Kit editor's Python.
They read their inputs from Python variables that are set before the file is executed. Each script's header lists
its variables.

**Paste route** (how upstream ran them, and the only route `create_face_anims.py` was verified with). The user
does this in the open kit with the mod selected: in the Output Log, switch the input line to Python mode, paste one
line, press Enter. You write that line with full paths, for example:

    PKG = "/<Mod>/Dialogs/<ChainSID>_Voiceover"; exec(open(r"<full path of scripts/probe_voiceover_keys.py>").read())
    VANILLA = "/Game/.../<speaker>"; OUT = r"<work>/facedump"; exec(open(r"<full path of scripts/dump_face_anim.py>").read())
    PRED = r"<work>/pred.json"; VANILLA = "/Game/.../<speaker>"; DEST = "/<Mod>/Animations"; exec(open(r"<full path of scripts/create_face_anims.py>").read())

Give the user the steps click by click (stalker2-workflow). `create_face_anims.py` saves into the mod: have the user
back up the mod's content first.

**Headless route** (the two read-only scripts only). Put the same line in a small script file and run it with
stalker2-zonekit's `sdk_run.py` (kit closed; output is the `LogPython:` lines plus the files in `OUT`). A mod asset
needs the registry scan first (stalker2-zonekit, headless Python):

    import unreal
    unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(["/<Mod>/"], True)
    PKG = "/<Mod>/Dialogs/<ChainSID>_Voiceover"; OUT = r"<work>"
    exec(open(r"<full path of scripts/probe_voiceover_keys.py>").read())

Upstream did not run these scripts headless: treat the first run as a test and check the counts it prints (a dump
that reports 0 anims, or a package that "did not load", means the route failed, not that the data is empty).

Do not run `create_face_anims.py` headless or over the editor's remote execution: it duplicates and saves assets,
and over remote execution `duplicate_asset` of `/Game` sources returned None.

## Linux / Proton
- The install folder is the same inside the game folder
  (`<steam>/steamapps/common/<game folder>/Stalker2/Content/Paks/~mods/`); the `~mods` rule applies unchanged.
- `fit_lipsync.py` runs on any Linux Python 3 with numpy (the kit's Windows Python is not needed).
- The editor scripts were run under Proton by the paste route, without remote execution. Every path in the pasted
  line is as the editor sees it (a Wine drive-letter path).
- The kit, prefixes and Wine paths: stalker2-linux. Wwise under Proton: stalker2-audio.
