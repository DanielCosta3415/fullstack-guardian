# Lançador conservador: Python existente, sem downloads ou privilégios.
$ErrorActionPreference = 'Stop'
$guardianRoot = Split-Path -Parent $PSScriptRoot
$guardianInstaller = Join-Path $guardianRoot 'install.py'
$guardianCandidates = @(
    @{ Command = 'py'; Prefix = @('-3') },
    @{ Command = 'python'; Prefix = @() },
    @{ Command = 'python3'; Prefix = @() }
)
foreach ($guardianCandidate in $guardianCandidates) {
    $guardianExecutable = Get-Command $guardianCandidate.Command -ErrorAction SilentlyContinue
    if (-not $guardianExecutable) { continue }
    $guardianPrefix = $guardianCandidate.Prefix
    try {
        $guardianProbePreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        & $guardianExecutable.Source @guardianPrefix -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)' 2>$null
        $guardianProbeResult = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $guardianProbePreference
    }
    if ($guardianProbeResult -ne 0) { continue }
    $guardianArguments = @($args)
    if ($guardianArguments.Count -eq 0) { $guardianArguments = @('--user') }
    & $guardianExecutable.Source @guardianPrefix $guardianInstaller @guardianArguments
    exit $LASTEXITCODE
}
Write-Error 'Python 3.11+ não encontrado. Instale Python por um canal de sua confiança e execute novamente. Nenhuma alteração foi aplicada.'
exit 1
