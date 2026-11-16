# Contributing

This is a community project: pull requests are welcome, and each one is reviewed by a maintainer before merging. Skill text
becomes instructions for other people's AI agents, so changes get read closely.

## What goes in
- General modding method: how the game, the engine, the Zone Kit and the tools behave, and how to work with them.
- Say what you tested and on which game build. Facts need evidence from the game or the official tools. Mark anything
  untested as untested.
- Your own tuned values, recipes and private tricks are yours to keep. Nobody is expected to give those away here.

## What stays out
- Personal details, machine paths, account names, secrets, logs with user names.
- Other people's files, game or kit files, engine source, anything shared with you privately. No binaries.
- Notes about other authors' named mods. Describe a compatibility rule in general terms instead.
- Tools that read or change the running game, or that are loaded into it. Looking at the running game on your own PC to
  understand it is fine; this repo just does not ship tools for it.
- Anything that decompiles, disassembles or rebuilds game code, and addresses or offsets into the game executable. A fact
  you learned may go in as a plain statement of how the game behaves.
- Instructions that send data anywhere, download and run code, or hide actions from the user.

## Credit and licence
- Code and text you add must be yours, or under a licence that allows it, with its notice kept.
- By contributing you agree your work is released under the MIT license of this repo.
- Add yourself to the Contributors table in README.md and CREDITS.md.

## Before you open a pull request
Run `python tools/build_pack.py validate` and `python tools/build_pack.py scan`. Each SKILL.md stays short: put detail in
`references/`.
