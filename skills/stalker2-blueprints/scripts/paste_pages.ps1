# A small always-on-top window for the user: one "Copy" button per page of a paginated Blueprint paste
# (bp_graph.paginate: <dir>\pages.json + one .txt per page). Pages whose digest differs from <dir>\pasted.json (the
# last state the agent confirmed in the editor) are marked CHANGED and listed first; the others need no paste.
# The agent starts it (the user never runs commands), from the skill folder:
#   Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','scripts\paste_pages.ps1','-Dir','<dir>'
# After the user's "done" (and a check in the editor), the agent copies pages.json over pasted.json.
# pages.json and pasted.json: { "<page name>": { "file": "<page>.txt", "nodes": <count>, "digest": "<page_digest>" }, ... }
param([Parameter(Mandatory)][string]$Dir, [switch]$All)
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
$Dir = (Resolve-Path $Dir).Path
$man = Get-Content (Join-Path $Dir "pages.json") -Raw | ConvertFrom-Json
$old = $null
if (Test-Path (Join-Path $Dir "pasted.json")) { $old = Get-Content (Join-Path $Dir "pasted.json") -Raw | ConvertFrom-Json }
$rows = foreach ($p in $man.PSObject.Properties) {
    $changed = $All -or -not $old -or -not $old.($p.Name) -or $old.($p.Name).digest -ne $p.Value.digest
    [pscustomobject]@{ Name = $p.Name; File = $p.Value.file; Nodes = $p.Value.nodes; Changed = $changed }
}
$form = New-Object Windows.Forms.Form
$form.Text = "Paste pages: " + (Split-Path $Dir -Leaf)
$form.TopMost = $true
$form.Font = New-Object Drawing.Font("Segoe UI", 10)
$form.AutoSize = $true; $form.AutoSizeMode = "GrowAndShrink"; $form.Padding = New-Object Windows.Forms.Padding(10)
$flow = New-Object Windows.Forms.FlowLayoutPanel
$flow.FlowDirection = "TopDown"; $flow.AutoSize = $true; $flow.WrapContents = $false
$form.Controls.Add($flow)
$help = New-Object Windows.Forms.Label
$help.AutoSize = $true; $help.MaximumSize = New-Object Drawing.Size(460, 0)
$n = @($rows | Where-Object Changed).Count
$help.Text = if ($n) { "$n page(s) to paste, top to bottom. For each: click Copy, open the graph tab with that name in the Blueprint (a missing one: My Blueprint > Graphs > +, give it that name), click inside it, Ctrl+A, Delete, Ctrl+V. At the end: File > Refresh All Nodes, Compile, Save." } else { "Nothing changed: no paste needed." }
$flow.Controls.Add($help)
$first = @($rows | Where-Object { $_.Changed -and $_.Name -ne "EventGraph" }) + @($rows | Where-Object { $_.Changed -and $_.Name -eq "EventGraph" })   # the main page (the calls) last
foreach ($r in $first + @($rows | Where-Object { -not $_.Changed })) {
    $line = New-Object Windows.Forms.FlowLayoutPanel
    $line.AutoSize = $true; $line.WrapContents = $false
    $b = New-Object Windows.Forms.Button
    $b.Text = "Copy"; $b.Width = 80; $b.Height = 30
    $b.Tag = Join-Path $Dir $r.File
    $b.Enabled = $r.Changed
    $b.Add_Click({ param($s, $e)
        [Windows.Forms.Clipboard]::SetText([IO.File]::ReadAllText($s.Tag))
        $s.Text = "Copied"; $s.BackColor = [Drawing.Color]::LightGreen })
    $l = New-Object Windows.Forms.Label
    $l.AutoSize = $true; $l.Padding = New-Object Windows.Forms.Padding(0, 6, 0, 0)
    $l.Text = "$($r.Name)  ($($r.Nodes) nodes)" + $(if ($r.Changed) { "  - CHANGED" } else { "  - unchanged, skip" })
    if (-not $r.Changed) { $l.ForeColor = [Drawing.Color]::Gray }
    $line.Controls.Add($b); $line.Controls.Add($l)
    $flow.Controls.Add($line)
}
[void]$form.ShowDialog()


# Changed here: the header comment only (the script path, "user" for "tester", the pages.json shape spelled out).
# Copied from the Stalker 2 modding harness, https://github.com/noahsemus/stalker2-modding-harness (commit 15b171c).
# MIT License, Copyright (c) 2026 Noah Semus. Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the
# Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above
# copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
