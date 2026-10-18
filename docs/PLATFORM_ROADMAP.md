# Fullstack Guardian — platform engineering status and release gates

**Development preview:** `2.2.0-dev.1` on `feat/guardian-platform-foundation`.  
**Stable branch:** `main` remains at `2.1.0`.  
**Status:** engineering preview with required CI, not a certified production release.

## Features implemented in the PR

1. **29 core specialist playbooks** with task-specific checks, 12 lifecycle stage contracts and 12 corresponding Codex skills.
2. **Ten opt-in specialist packs**, a local registry, path-traversal / symlink / Windows reparse checks, identity collision detection and explicit dry-run-first pack management.
3. **Risk-bounded plan DAGs** with specialist selection, review ordering, approval boundaries and schema-level evidence checks.
4. **Codex CLI executor**, requiring written per-task briefs, a clean Git baseline, an isolated worktree, persistent checkpoints, timeouts and manual recovery after failure. Optional native subagent verification checks local session metadata; no native success is presumed.
5. **Worktree integration preview / explicit apply** (`tools/guardian_integrate.py`). It rejects untracked and protected files, high-risk plans and dirty targets. Requires human review and exact SHA-256 confirmation. It applies an **uncommitted** patch; tests, commits, pushes and deployment remain separate.
6. **Optional comparative benchmark runner**, explicit hashed candidate guidance, same model/effort, an external grader and transparent missing token metrics. A deterministic three-case synthetic fixture generator is supplied.
7. **Installation hardening**, atomic per-file replacement, exclusive lock, backups, dry-run and a separate interrupted-transaction recovery tool. Multi-file crash atomicity is not claimed.
8. **Local hash-chained journal**, reporting of missing evidence without invented authentication, Windows native acceptance script and Python unit/integration CI.
9. **Release supply-chain safeguards**: distinct prerelease version, reproducible ZIP and SHA256 manifest; separate tag/manual GitHub workflow for OIDC-attested archive provenance verified before upload. **No attestation has been issued merely by merging these changes.**
10. **Security scanning:** CodeQL Python workflow on commits/PRs and weekly schedule. A scan is not a formal security certification.

## What the tests establish

The GitHub CI matrix runs on Windows, Ubuntu and macOS with Python 3.11–3.13. Synthetic tests validate Git worktree isolation, state corruption/failure refusal, selective pack install/rollback, SDK-agnostic lifecycle contracts, recovery, hash-confirmed integration, independent grading and release archive reproducibility. **Inspect the PR's actual latest checks**; do not reuse a previous green check after code changes.

Tests with mocked Codex CLI prove harness behavior only. They do **not** demonstrate that a native subagent was spawned or that a generated code patch satisfies user requirements.

## Remaining real-environment requirements

- **Native Windows acceptance:** run the opt-in `scripts/Validate-WindowsCodex.ps1 -RunNative` on an authenticated supported Codex Desktop/CLI environment, inspect child-session records and the 29 roles. This needs the user's local access and quota.
- **Real controlled benchmark:** execute multiple paired runs against more representative tasks (including .NET, API and financial consistency), verify grader independence and report statistical uncertainty. The included three-case Python fixture is only a smoke test.
- **Provenance:** trigger the authorized tag/manual release workflow and verify GitHub's actual signed attestation before publishing a package. A pinned action does not itself sign anything before the workflow runs.
- **Security:** independent human threat-model review, runtime permission testing, hostile filesystem/fault-injection tests and remediation of observed CodeQL findings before release.
- **Operations and cloud:** human-approved integration in representative applications, real incident/restore drills, cloud credential/tenant policies, model entitlement checks and production release authorization. The software cannot guarantee behavior for inaccessible external systems.
- **Long-running native subagents:** true cancellation and reconnection of in-progress Codex sessions is dependent on supported native APIs; the external executor fails closed after interruption rather than re-executing possible side effects.
- **Installer:** OS-level multi-file atomicity across crashes, stale-lock recovery and rollback under every possible power-loss state are not guaranteed.
- **Model routing:** automatically switching reasoning effort using trustworthy live quota telemetry remains unavailable unless exposed by the installed Codex interface; values must not be invented.

## Stable merge / release conditions

Do not merge a draft PR or publish a stable version until required checks pass, code is reviewed, release provenance is verifiable, user configurations are preserved and the native Windows acceptance gate has documented results. A future final version requires an explicit release decision; `2.2.0-dev.1` must not be represented as `2.1.0` or a complete, certified platform.

See [platform instructions](PLATFORM_ENGINEERING.md), [distribution](DISTRIBUTION.md) and [validation](VALIDATION.md).
