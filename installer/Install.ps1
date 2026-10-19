# Existing Python only; same fallback used by Windows acceptance.
$ErrorActionPreference = 'Stop'
$guardianRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $guardianRoot 'scripts/Find-GuardianPython.ps1')
$guardianPython = Find-GuardianPython
$guardianPrefix = $guardianPython.Prefix
$guardianArguments = @($args)
if ($guardianArguments.Count -eq 0) { $guardianArguments = @('--user') }
& $guardianPython.Executable @guardianPrefix (Join-Path $guardianRoot 'install.py') @guardianArguments
exit $LASTEXITCODE
