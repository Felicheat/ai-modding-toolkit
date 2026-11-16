# Reimporting meshes whose stored source path is gone

## Where the source path lives
A kit mesh stores its source file in AssetImportData, as JSON inside the .uasset:
`[{ "RelativeFilename" : "<path>", "Timestamp" : ..., "FileMD5" : "<hex>" }]`.
Show it with `grep -a -o '[ -~]\{0,120\}<mesh name>\.glb[ -~]\{0,200\}' <mesh>.uasset` (or the same search in Python).

## The symptom
When that path no longer exists (another machine, a removed drive or folder), Reimport says "N assets with missing source file
path". If the user skips the file pickers, Interchange logs "There was no data to import" and changes nothing; Save All then only
re-saves the unchanged meshes. Picking every file by hand works but costs one dialog per mesh.

## The fix: recreate the old path for a moment
Suppose the stored path is `<drive>:/<top>/<rest>` and the files now live in `<real folder>/<rest>`. In cmd (backslashes; `mklink`
and `rmdir` are cmd built-ins):

    mkdir "%TEMP%\kitroot"
    mklink /J "%TEMP%\kitroot\<top>" "<real folder>"
    subst <drive>: "%TEMP%\kitroot"

Then the user reimports in the kit. It may take one Reimport click per mesh, but no file dialogs. Save.

## Cleanup, in this order
    subst <drive>: /D
    cmd /c rmdir "%TEMP%\kitroot\<top>"
    rmdir "%TEMP%\kitroot"

- `rmdir` on the junction removes the JUNCTION only, never the files it points to.
- Never use PowerShell `Remove-Item -Recurse` on a junction: it can walk into the target and delete the real files.
- The stored path does not change, so the next reimport needs the same mapping again.

## Verify offline
Each mesh's .uasset holds its source file's MD5 as hex in that JSON. Compare it with `hashlib.md5(open(src, 'rb').read()).hexdigest()`
of the new source file: every mesh must match. The .uasset sizes also change with the new geometry.
