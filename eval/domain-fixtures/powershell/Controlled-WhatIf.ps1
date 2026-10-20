param([Parameter(Mandatory=$true)][string]$Root)
$ErrorActionPreference = 'Stop'
function Write-ControlledFixture {
    [CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='Low')]
    param([Parameter(Mandatory=$true)][string]$Path)
    if ($PSCmdlet.ShouldProcess($Path, 'Write synthetic fixture')) {
        [System.IO.File]::WriteAllText($Path, 'controlled-fixture')
    }
}
$target = Join-Path $Root 'synthetic.txt'
Write-ControlledFixture -Path $target -WhatIf | Out-Null
$whatIfUnchanged = -not (Test-Path -LiteralPath $target)
Write-ControlledFixture -Path $target -Confirm:$false
$applyCorrect = ([System.IO.File]::ReadAllText($target) -eq 'controlled-fixture')
# WhatIf must also preserve a pre-existing file; this covers a destructive overwrite.
[System.IO.File]::WriteAllText($target, 'existing-synthetic')
Write-ControlledFixture -Path $target -WhatIf | Out-Null
$overwriteUnchanged = ([System.IO.File]::ReadAllText($target) -eq 'existing-synthetic')
@{whatIfUnchanged=$whatIfUnchanged; applyCorrect=$applyCorrect; overwriteUnchanged=$overwriteUnchanged} | ConvertTo-Json -Compress
