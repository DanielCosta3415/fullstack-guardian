# Explicit native stack regression checks

`guardian_stack_checks.py` runs only the fixed, reviewed source fixtures under
`eval/stack-fixtures`. It does not execute candidate-generated code, install a
toolchain, launch a model, open a browser, contact a provider or modify a global
Codex configuration. Ordinary `unittest` runs fast protocol checks with mocks;
native .NET builds occur only through the explicit run command.

```powershell
python -B tools/guardian_stack_checks.py
python -B tools/guardian_stack_checks.py --run --out work/stack-run-001
python -B tools/guardian_stack_checks.py --run --stack powershell --out work/ps-run-001
```

Output directories must be new; no existing evidence is overwritten. Fixtures
are bounded, link-checked, copied into the dedicated directory and compared
again after execution. Each runtime is version-probed first. Commands use argv
without a shell. Profiles, Node preload options, telemetry, automatic tools-path
addition, ASP.NET certificate generation and build servers are disabled where
applicable. .NET uses a new CLI/package/cache directory, a NuGet configuration
with all package sources cleared, no PackageReferences, an explicit offline
restore and `build --no-restore`. An absent SDK/reference pack remains blocked;
there is no download fallback. MSBuild parent Directory.Build imports are disabled.

The reviewed fixtures contain no external network calls, but this harness is
**not an OS network-isolation attestation**. Effective filesystem/network
restrictions still come from the execution environment. Run these checks only
under existing authorization for the dedicated local output directory. The
directory retains per-command stdout/stderr and a structured report; diagnostics
can contain local paths and should remain local.

## Discriminating scenarios

| Stack | Baseline and controlled faults | What remains unverified |
|---|---|---|
| Node.js | Optional-field absence versus explicit null after JSON serialization; strict enum rejection versus tolerant preservation; invalid form navigation; preserving draft input on navigation | Actual HTTP consumers, framework/DOM behavior, browser accessibility, assistive technology and production UI |
| .NET8 target using installed SDK/shared framework | DI rejects singleton→transient→scoped capture; scope factory produces distinct disposed instances; cancellation before an in-memory commit has no effect; post-commit cancellation preserves acknowledgment | Real database/EF transactions, ASP.NET request aborts, distributed commit, provider-specific behavior and production services |
| PowerShell7 | Literal bracket-containing filenames, WhatIf without mutation, cancellation before writing, rejection of a real reparse **ancestor** component | All Windows reparse types, hostile concurrent filesystem races, general OS isolation and arbitrary administration scripts |

Each stack executes one baseline plus four faulty variants. A faulty variant is
accepted as a successful negative check only when it emits the exact expected
failing assertion and exits **1**. Any other assertion, an arbitrary exit1, a
dependency/import failure or a timeout does not count as detecting the intended
fault. Exit codes and unavailable checks are preserved. Missing tools/protocol
remain `BLOCKED`; assertion mismatches are `FAILED`.

PowerShell creates a junction on Windows, or a symlink where supported, whose
target is another directory within the same dedicated fixture root. It never
points at user documents or production. No recursive cleanup is performed by
the fixture. If link creation is denied, the baseline records that subcheck as
`NOT_AVAILABLE` and the dedicated faulty reparse variant exits3 and remains
`BLOCKED`. A separately authorized execution environment may run the same
reviewed fixture; the harness never bypasses the sandbox itself.

## Evidence and scope

The report binds exact fixture and harness SHA256 values, actual runtime versions, actual
exit codes, failed/unavailable check IDs and the distinction between baseline
success and expected-fault rejection. It explicitly keeps browser, model,
production and OS-isolation verification false. These are executable synthetic
regressions addressing narrow role obligations; they do not certify a model,
specialist, private holdout or professional superiority.

During implementation on Windows, the reviewed execution recorded Node24.11.0,
.NET SDK10.0.403 targeting net8.0, and PowerShell7.6.5. All15 variants matched
their predeclared assertions in the final authorized run, including the real
junction negative. The earlier sandbox run honestly retained the reparse block
and a faulty WhatIf test-fixture assumption; the latter was corrected without
weakening its assertion. Re-run the command to establish evidence for another
revision/environment; this paragraph is not an acceptance receipt.

## Primary references used

- [Node24.11.0 strict assertions](https://nodejs.org/download/release/v24.11.0/docs/api/assert.html): precise typed assertion failures.
- [.NET restore](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-restore): control explicit versus implicit restore and configured package sources.
- [.NET dependency-injection guidance](https://learn.microsoft.com/en-us/dotnet/core/extensions/dependency-injection/guidelines): scope lifetime and singleton capture.
- [PowerShell7.6 CmdletBinding](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_functions_cmdletbindingattribute?view=powershell-7.6): SupportsShouldProcess and confirmation behavior.

These references inform the checked-in scenarios. They are not an external
authorization, a claim of broad standards compliance or a newly installed dependency.
