# Opt-in Windows-native Codex acceptance smoke. No elevated permissions or downloads.
# Example dry-run: powershell -File scripts/Validate-WindowsCodex.ps1
# Example quota-consuming: powershell -File scripts/Validate-WindowsCodex.ps1 -RunNative -Out C:\Temp\guardian-native-new

param(
    [switch]$RunNative,
    [string]$Out
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Get-Command 'py' -ErrorAction SilentlyContinue
$arguments = @()
if ($python) {
    $arguments = @('-3')
} else {
    $python = Get-Command 'python' -ErrorAction SilentlyContinue
}
if (-not $python) {
    Write-Error 'Python 3.11+ required. No installation or PATH change was attempted.'
    exit 2
}
& $python.Source @arguments -c 'import sys;sys.exit(0 if sys.version_info >= (3,11) else 1)'
if ($LASTEXITCODE -ne 0) {
    Write-Error 'Python 3.11+ required.'
    exit 2
}
Push-Location $root
try {
    & $python.Source @arguments tools/guardian_registry.py validate
    if ($LASTEXITCODE -ne 0) { throw 'Registry validation failed' }
    & $python.Source @arguments tools/guardian_platform.py security-lint
    if ($LASTEXITCODE -ne 0) { throw 'Configuration security lint failed' }
    & $python.Source @arguments tools/test_native_agents.py --all
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
    & $python.Source @arguments tools/test_native_agents.py --run --all --out $outputPath
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
