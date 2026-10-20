# Opt-in Windows-native Codex acceptance smoke. No elevated permissions or downloads.
# Example dry-run: powershell -File scripts/Validate-WindowsCodex.ps1
# Example quota-consuming: powershell -File scripts/Validate-WindowsCodex.ps1 -RunNative -Out C:\Temp\guardian-native-new

param(
    [switch]$RunNative,
    [string]$Out,
    [switch]$IncludePacks
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
 . (Join-Path $PSScriptRoot 'Find-GuardianPython.ps1')
$guardianPython = Find-GuardianPython
$pythonExecutable = $guardianPython.Executable
$arguments = $guardianPython.Prefix
Push-Location $root
try {
    & $pythonExecutable @arguments tools/guardian_registry.py validate
    if ($LASTEXITCODE -ne 0) { throw 'Registry validation failed' }
    & $pythonExecutable @arguments tools/guardian_platform.py security-lint
    if ($LASTEXITCODE -ne 0) { throw 'Configuration security lint failed' }
    $guardianPreviewArguments = @('--all')
    if ($IncludePacks) { $guardianPreviewArguments += '--include-packs' }
    & $pythonExecutable @arguments tools/test_native_agents.py @guardianPreviewArguments
    if ($LASTEXITCODE -ne 0) { throw 'Native test preview failed' }
    if (-not $RunNative) {
        Write-Output 'DRY-RUN ONLY. No Codex model, quota, permissions or files changed.'
        return
    }
    if ([string]::IsNullOrWhiteSpace($Out)) {
        throw 'Specify a NEW output directory via -Out for native tests.'
    }
    $codex = Get-Command 'codex' -ErrorAction SilentlyContinue
    if (-not $codex) { throw 'Authenticated Codex CLI is required.' }
    $outputPath = [System.IO.Path]::GetFullPath($Out)
    if ((Test-Path -LiteralPath $outputPath) -and ((Get-ChildItem -LiteralPath $outputPath -Force | Measure-Object).Count -gt 0)) {
        throw 'Output path must be new or empty.'
    }
    Write-Output 'The following explicitly authorized command consumes Codex account quota:'
    Write-Output 'python tools/test_native_agents.py --run --all --out <new path>'
    $guardianNativeArguments = @('--run', '--all', '--out', $outputPath)
    if ($IncludePacks) { $guardianNativeArguments += '--include-packs' }
    & $pythonExecutable @arguments tools/test_native_agents.py @guardianNativeArguments
    if ($LASTEXITCODE -ne 0) { throw 'Native validation failed or some agent types were not verified.' }
    Write-Output 'Native smoke completed. Independently inspect result files before claiming operational readiness.'
}
catch {
    Write-Error $_
    exit 2
}
finally {
    Pop-Location
}
