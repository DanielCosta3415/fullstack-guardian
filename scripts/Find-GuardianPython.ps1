# Return an existing Python >= 3.11; no downloads, PATH or policy changes.
function Find-GuardianPython {
    $guardianCandidates = @(
        @{ Command = 'py'; Prefix = @('-3') },
        @{ Command = 'python'; Prefix = @() },
        @{ Command = 'python3'; Prefix = @() }
    )
    foreach ($guardianCandidate in $guardianCandidates) {
        $guardianExecutable = Get-Command $guardianCandidate.Command -ErrorAction SilentlyContinue
        if (-not $guardianExecutable) { continue }
        $guardianPrefix = $guardianCandidate.Prefix
        $guardianProbeResult = 1
        try {
            $guardianPriorPreference = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            & $guardianExecutable.Source @guardianPrefix -c 'import sys;sys.exit(0 if sys.version_info >= (3,11) else 1)' 2>$null
            $guardianProbeResult = $LASTEXITCODE
        } catch { $guardianProbeResult = 1 }
        finally { $ErrorActionPreference = $guardianPriorPreference }
        if ($guardianProbeResult -eq 0) {
            return @{ Executable = $guardianExecutable.Source; Prefix = $guardianPrefix }
        }
    }
    throw 'Python 3.11+ not found. No installation, PATH change or privilege elevation was attempted.'
}
