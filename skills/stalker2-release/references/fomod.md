# FOMOD installers for STALKER 2 mods

## Contents
1. How Vortex installs a FOMOD for this game
2. Archive layout and file names
3. ModuleConfig.xml rules
4. Simulate every answer combination
5. Validate against the schema
6. Test in Vortex and tell users
7. Options that differ by a few packages: a base pak plus override paks

## 1. How Vortex installs a FOMOD for this game
The STALKER 2 extension hands every archive with `fomod/ModuleConfig.xml` to Vortex's built-in FOMOD installer.
The chosen files land along their destination paths in `~mods`, and since extension 2.1.1 a pak-only FOMOD mod is
retagged so it gets its own Load Order folder and row (details: stalker2-vortex). Older extension versions still
load it, unsorted. Shipping a plain pak archive beside the FOMOD gives those users a sortable option.

## 2. Archive layout and file names
- `fomod/ModuleConfig.xml` (and optional `fomod/info.xml`, images) at the zip root, one folder per option holding
  its paks. Zip with `make_zip.py` and no `--top`.
- Destinations relative to the mod root (`destination=""` or a plain subfolder). Never `Stalker2/Content/Paks/~mods/`:
  the target is already `~mods`, and a `Stalker2/` path blocks the Load Order retag.
- Keep each pak's `_<N>_P` priority tail; a prefix such as `zzzz_` only orders files of equal priority
  (stalker2-paks).
- Rename an IoStore trio as a set: `.pak`, `.utoc`, `.ucas` share one base name. Never rename one file alone.
- Two options must never install files with the same name into the same place unless one replaces the other on
  purpose.

## 3. ModuleConfig.xml rules
- **Leave every `installStep` name empty** (`name=""`). Vortex labels the Back and Next buttons with the
  neighbouring step's name and falls back to Previous / Next / Finish only when names are empty. The page heading
  comes from the group name, so put the question there.
- **Gate a page with flags**: an earlier option sets a flag (`<conditionFlags><flag name="core">yes</flag>`), the
  later step carries `<visible><dependencies operator="And"><flagDependency flag="core" value="yes"/></dependencies></visible>`.
  Use this for pages that only make sense after a certain choice.
- **Combinations go in `conditionalFileInstalls`**: when the files depend on two answers together, set one flag per
  answer and add one `<pattern>` per combination (`<dependencies operator="And">` with both `flagDependency`
  lines, then its `<files>`). Do not try to express combinations with per-option file lists.
- Radio questions: group type `SelectExactlyOne`, the default option typed `Recommended`. Offer an explicit "Game
  default" option that installs nothing when skipping a part makes sense.
- Option descriptions follow the writing rules; run `check_release_text.py` on `ModuleConfig.xml` too.
- `<moduleName>` and the version in `info.xml` change with every release: include both in the version grep.

## 4. Simulate every answer combination
Write (or keep in the mod repo) a simulator that reads the generated `ModuleConfig.xml` and, for every combination
of answers:
- skips steps whose `visible` flags are not met, exactly as the installer would;
- collects the files from the chosen options plus every matching `conditionalFileInstalls` pattern;
- asserts the result against what that combination must install (count and names), and that every file exists in
  the archive.
Also check the reverse: every file in the archive is installed by at least one combination. Print the number of
combinations; it should match your expectation (hidden pages reduce it). Rerun after every rebuild of a pak.

## 5. Validate against the schema
1. Reference the schema in the root element: `xsi:noNamespaceSchemaLocation="http://qconsulting.ca/fo3/ModConfig5.0.xsd"`.
2. Download that file and the file it redefines, `http://qconsulting.ca/gemm/ModConfig5.0.xsd`, into a scratch
   folder (two different files with the same name: save them as `ModConfig5.0.xsd` and `ModConfig5.0_gemm.xsd`).
3. In the gemm copy, fix the typo `type=" xs:string"` (the `version` attribute of `versionDependency`) to
   `type="xs:string"`.
4. In the fo3 copy, point `<xs:redefine schemaLocation=...>` at your local gemm file.
5. Validate with lxml (`etree.XMLSchema(etree.parse(local_fo3))`, then `schema.assertValid(etree.parse(module_config))`).
   Keep the fixed copies cached; do not fetch them on every build.

## 6. Test in Vortex and tell users
- Install the archive in Vortex once per release with at least the default answers: the buttons read Previous /
  Next / Finish, the deployed files hash-identical to the release build, the mod shows in Load Order.
- Readme and page: tell users to disable or remove an older manual install or an older Vortex entry of the same
  mod first. An update in Vortex can install beside the old version and both load (stalker2-vortex).
- Say which extension version gives Load Order support for the FOMOD (2.1.1 or later).

## 7. Options that differ by a few packages: a base pak plus override paks
A full pak per option makes the installer many times larger than its content.
- Measure first: unpack the options' trios and compare them package by package (stalker2-paks). Options that looked like
  separate builds have differed in one package, or in a few dozen curves.
- Layout: the default option's pak goes in the files everyone gets. Each other option adds a small pak at the next priority
  (`_<N+1>_P` over the base's `_<N>_P`) that holds only the packages that differ.
- Two options that touch the SAME package get ONE pak, chosen by a `conditionalFileInstalls` pattern on both flags. Never two
  paks at one priority.
- An override pak can add or replace a package, not remove one. If the base carries a package that an option never had, put the
  game's own copy of that package in the option's pak.
- Where the small paks come from: curve packages can be cut out of a built pak with `retoc to-legacy` (the game's `global.utoc`
  and `global.ucas` beside the pak), `repak pack --version V11`, `retoc to-zen --version UE5_5`; that round trip is byte-exact
  for curves. It is NOT for Blueprints: cook those in the kit and compare the raw chunk with the tested build (stalker2-zonekit).
- Proof before shipping: base plus small pak equals the old full pak, package by package. The simulation (section 4) asserts
  that exactly one installed pak carries each contested package, and that nothing is installed twice at one priority.
- A re-pack of the same assets differs in container bytes: compare raw chunks (`retoc unpack-raw`), not the trio's hashes.
