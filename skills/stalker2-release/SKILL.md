---
name: stalker2-release
description: Ships a STALKER 2 mod release. Picks the X.Y.Z version, writes changelogs and public text by the writing rules, proves a rebuild, builds zips with forward-slash entries, authors FOMOD installers and closes the release with commit, checkpoint and tag. Use when cutting a version, building release zips or a FOMOD or Vortex installer, writing a changelog, readme or mod page text, or committing and tagging a release.
license: MIT
compatibility: Python 3.8+ (stdlib only) for the scripts; lxml only to validate FOMOD XML.
metadata:
  pack: STALKER 2 AI Modding Toolkit
  pack-version: "1.0.0"
  author: STALKER 2 AI Modding Toolkit contributors
  verified-on: "STALKER 2 Steam build 26123434 (game 2.1), Zone Kit 2.1.0"
---

# Releasing a STALKER 2 mod

A mod repo may keep its own release conventions: read them first. This skill is what holds across mods. What Vortex does
with the archive: stalker2-vortex. Publishing on Steam Workshop or mod.io: stalker2-publish.

## Order of a release
1. Propose the version bump with the plan, before building, so it is agreed with the rest.
2. Build. Bump every place the version lives in one pass (build scripts, installer info, readme headers, page text,
   changelog), then grep the repo for the old number.
3. Prove the build (below).
4. Write the texts, then `python scripts/check_release_text.py <files or folders>`. Fix every FAIL, reword WARNs.
5. Zip with `python scripts/make_zip.py` (below).
6. Give the user the exact upload set: every file with path, size and sha256 (make_zip prints them). Uploading is
   the user's job.
7. Close the release (below).

## Versions: X.Y.Z
- **X**: a new foundation or a rework users must reinstall or re-choose for.
- **Y**: a new feature or optional part: a new option, add-on or installer page.
- **Z**: tuning, fixes, text, confirming a game patch still works.
- Existing version numbers stay as they are; the rule applies from each mod's next release.

## Changelogs
- Newest first, written for the player: what changed and what to do (reinstall, re-choose, nothing).
- A version built but never published rolls into the next: keep its notes under
  "X.Y.Z (built, never published on its own; everything below is in X.Y.Z)".
- One change note per release, reused on every platform.
- Describe what the files carry, not what a patch script printed.

## Prove the build
- **Unchanged parts are unchanged**: hash every file against the last release. For IoStore trios compare unpacked
  chunks: byte-different containers can hold identical content (stalker2-paks).
- **Changed parts are what the user approved**: hash each shipped file against the exact build tested in game.
  A rebuild "with the same settings" is not that build.
- **Zone Kit material values** also need proof the cook recompiled them; a byte patch alone never reaches the
  build (stalker2-zonekit).
- **Zone Kit mods ship everything in the plugin's `Content` folder**, listed or not. Read references/kit-mods.md before
  the release cook of a kit mod: clean out dev and unused assets, then check what the override pak really holds.
- Name every build in your messages (mod, version, file name) so the user knows what is installed and what their
  notes refer to.

## Writing rules (every public text)
Mod page, readme, changelog, installer text:
- No em dashes or en dashes. Use a colon, comma or parentheses.
- No filler. Short, plain, specific: what the mod does, what changed, how to install. Whether to mention AI help is the author's choice; be honest if asked.
- Credit other authors openly: compatibility notes, inspiration credits and recommending their mods are welcome.
- Respect each author's permissions, and say honestly what you built on.
- Numbers only when they help the player; some mods keep their tuning numbers private.
- `scripts/check_release_text.py` checks the mechanical part, with the rules in `release_text_rules.json` beside
  it (the user may edit them). It does not judge tone: read the text as a player.

## Zips
- Never PowerShell `Compress-Archive` or .NET `ZipFile.CreateFromDirectory`: they can write backslash entry names
  (Windows PowerShell 5.1) that other readers reject.
- `python scripts/make_zip.py <folder> <out.zip> [--top <name>]`: forward-slash entries, skips `.git`,
  `__pycache__`, `bin`, `obj`, `node_modules`, refuses symlinks and anything resolving outside the folder, prints
  the file list and the zip's sha256. FOMOD archives take no `--top` (keep `fomod/` at the zip root).
- Read the printed list against what you meant to ship before handing it over.

## FOMOD installers
Read references/fomod.md before building or changing a FOMOD installer: empty step names, `visible` flags,
conditional installs, simulating every answer, schema validation, file naming, telling users about older copies.

## Installer size: one base pak plus small override paks
- When installer options differ by a handful of packages, never ship a full pak per option. Ship the default option's pak
  for everyone, and per option a small pak at the NEXT priority (`_<N+1>_P` over `_<N>_P`) holding only the packages that
  differ.
- An override pak can add or replace a package, never remove one. If the base pak carries a package that an option
  should not have, put the GAME's own copy of it in that option's pak.
- Read references/fomod.md (section 7) before building such a layout: measuring, options that share a package, the proof.

## Closing the release
- Commit the release, then a checkpoint (state, upload set, open items), and tag it `vX.Y.Z`.
- Record anything that shipped untested, in the checkpoint and the project notes, so later feedback is read
  against it.
- List lessons that apply beyond this mod and propose them to the user as skill updates. Never edit skills
  silently.

## Traps
- The old version number survives somewhere: grep after every bump, installer XML and page text included.
- A Vortex folder name is not the installed version (stalker2-vortex): hash.
- A text that passes the checker can still overclaim: no "fixes all crashes" without proof.
- An option renamed in the installer but not in the readme or page text: check every text names the same options.
