param([Parameter(Mandatory)][string]$Root, [Parameter(Mandatory)][string]$Variant)
$ErrorActionPreference = 'Stop'
if ($Variant -notin @('baseline','whatif-bypass','wildcard-path','parent-reparse-unchecked','cancellation-ignored')) {throw 'Unknown reviewed variant'}
$fixtureRoot = [IO.Path]::GetFullPath($Root)
if (-not (Test-Path -LiteralPath $fixtureRoot -PathType Container)) {throw 'Existing dedicated fixture root required'}
$checks = [Collections.Generic.List[object]]::new()
function Check([string]$Id, [bool]$Passed) {
    $checks.Add(@{id=$Id; status=$(if ($Passed) {'PASSED'} else {'FAILED'})})
}
function Write-Synthetic {
    [CmdletBinding(SupportsShouldProcess)]
    param([string]$LiteralPath, [switch]$Cancelled)
    if ($Cancelled -and $Variant -ne 'cancellation-ignored') {throw [OperationCanceledException]::new('Synthetic cancellation')}
    if ($Variant -eq 'whatif-bypass') {
        # Deliberate controlled fault: .NET IO ignores inherited WhatIfPreference.
        [IO.File]::WriteAllText($LiteralPath, 'changed')
    } elseif ($PSCmdlet.ShouldProcess($LiteralPath, 'Write synthetic data')) {
        Set-Content -LiteralPath $LiteralPath -Value 'changed' -NoNewline
    }
}
$whatIfTarget = Join-Path $fixtureRoot 'whatif.txt'
Write-Synthetic -LiteralPath $whatIfTarget -WhatIf 6>$null
Check 'whatif_no_mutation' (-not (Test-Path -LiteralPath $whatIfTarget))
$literal = Join-Path $fixtureRoot 'literal[1].txt'
Set-Content -LiteralPath $literal -Value 'literal' -NoNewline
Set-Content -LiteralPath (Join-Path $fixtureRoot 'literal1.txt') -Value 'decoy' -NoNewline
$read = if ($Variant -eq 'wildcard-path') {Get-Content -Path $literal -Raw} else {Get-Content -LiteralPath $literal -Raw}
Check 'literal_path_preserves_brackets' ($read -ceq 'literal')
$cancelTarget = Join-Path $fixtureRoot 'cancel.txt'
$cancelled = $false
try {Write-Synthetic -LiteralPath $cancelTarget -Cancelled -Confirm:$false}
catch [OperationCanceledException] {$cancelled=$true}
Check 'cancelled_write_has_no_effect' ($cancelled -and -not (Test-Path -LiteralPath $cancelTarget))

function Assert-NoReparse([string]$Target) {
    $full = [IO.Path]::GetFullPath($Target)
    $relative = [IO.Path]::GetRelativePath($fixtureRoot, $full)
    if ([IO.Path]::IsPathRooted($relative) -or $relative -eq '..' -or $relative.StartsWith('..' + [IO.Path]::DirectorySeparatorChar)) {throw 'Outside fixture root'}
    $current = $fixtureRoot
    $parts = $relative.Split([IO.Path]::DirectorySeparatorChar)
    foreach ($part in $parts) {
        $current = Join-Path $current $part
        if ($Variant -eq 'parent-reparse-unchecked' -and $current -ne $full) {continue}
        if ((Get-Item -LiteralPath $current -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {throw [InvalidOperationException]::new('REPARSE_COMPONENT')}
    }
}
$linkAvailable = $false
try {
    $target = New-Item -ItemType Directory -Path (Join-Path $fixtureRoot 'target')
    Set-Content -LiteralPath (Join-Path $target.FullName 'data.txt') -Value 'canary' -NoNewline
    $kind = if ($IsWindows) {'Junction'} else {'SymbolicLink'}
    $null = New-Item -ItemType $kind -Path (Join-Path $fixtureRoot 'link') -Target $target.FullName
    $linkAvailable = $true
} catch [UnauthorizedAccessException] { }
catch [System.IO.IOException] { }
catch [System.ComponentModel.Win32Exception] { }
if ($linkAvailable) {
    $rejected = $false
    try {Assert-NoReparse (Join-Path $fixtureRoot 'link/data.txt')}
    catch [InvalidOperationException] {$rejected = $_.Exception.Message -eq 'REPARSE_COMPONENT'}
    Check 'parent_reparse_component_rejected' $rejected
} else {
    $checks.Add(@{id='parent_reparse_component_rejected'; status='NOT_AVAILABLE'})
}
@{stack='powershell'; variant=$Variant; checks=@($checks.ToArray())} | ConvertTo-Json -Compress -Depth 5
if ($Variant -eq 'parent-reparse-unchecked' -and -not $linkAvailable) {exit 3}
if ($checks.Where({$_.status -eq 'FAILED'}).Count) {exit 1}
exit 0
