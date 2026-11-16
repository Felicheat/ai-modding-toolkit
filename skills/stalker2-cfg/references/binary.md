# .cfg.bin containers

## Versions
| Container | Game | Notes |
|---|---|---|
| v1 | 2.0.4 and older | |
| v2 | 2.0.5 and newer | the first uint32 of the file is the version; blocks carry extra data over v1 |

Reading both is done by s2cfgtojson (by sdwvit), version 9.2 or newer. Its source is the reference for the layout.

## Decoding
- `cfgbin_decode.mjs --check` decodes, writes text, re-reads it and compares: run it on a new game build before trusting any other tool.
- An unknown container (a future game build): `cfgbin_decode.mjs <file> --tokens [--near <text>]` dumps raw tokens so you can see
  what moved. If the decoder fails, check whether a newer s2cfgtojson supports the build first.

## Traps
- Byte-different tables can hold identical content (string pool order). Compare decoded content (`cfg_diff.mjs`), not bytes, before
  calling a table changed; compare bytes first to know which tables to decode.
- The Zone Kit's text tree splits some tables into a `<Table>/` folder of files; the game's binary is one table.
  `cfg_verify.mjs --vanilla` on a text tree merges those sub-files.
- Edition skins (PreOrder / Deluxe / Ultimate) are separate paks with their own records under `DLCGameData/<Edition>/`.
