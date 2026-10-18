# Fullstack Guardian — engineering platform roadmap

**Development preview — not a completed, certified or production-ready platform.**
Current stable baseline: v2.1.0 (29 core agents, 8 skills, 132 engineering capabilities).

## Implemented in the development PR

- All 29 core specialists have targeted discipline-specific verification playbooks in `core/specialist-playbooks-v1.json`, attached to task plans on demand.
- Twelve lifecycle stage contracts in `core/lifecycle-v1.json` and twelve additional skills (`lifecycle-*`). Static stage checks do not represent completed work.
- Ten optional specialization packs: .NET, APIs, financial reliability, cloud, data, application security, front-end accessibility, Windows, AI and test engineering. The packs are not activated until the user explicitly installs them.
- `tools/guardian_registry.py` validates agent manifests, TOML identities, scope and collisions.
- `tools/guardian_packs.py` handles pack dry-run, managed installation, update and uninstall without silently overwriting user-owned agents.
- `tools/guardian_platform.py` creates bounded proposal-only task DAGs, performs risk-aware routing and checks evidence fields; **it does not spawn agents**.
- `tools/guardian_executor.py` can consume an approved plan and explicit per-task briefs, invoke Codex CLI sequentially in an isolated Git worktree and resume safely between tasks. Native child delegation is optional, fail-closed and checked against local Codex session logs; no source merge is automatic.
- `tools/guardian_benchmark.py` compares paired samples and refuses unmatched model/test settings.
- `tools/guardian_eval_runner.py` runs opt-in CLI A/B experiments with external immutable checker, identical model/effort and isolated worktrees. No live evaluation has been run from this conversation.
- `tools/guardian_trace.py` maintains an optional local hash-linked event journal. Checksums are not authentication.
- `tools/guardian_recover.py` uses original installer backups for explicit, fail-closed interrupted-transaction recovery.
- The existing installer and deterministic release builder include optional packs. CLI installation now has an exclusive lock and atomic per-file replacement; CI includes lifecycle, registry, security-lint, local Git executor and installation dry-run checks.

## Not yet implemented or independently proven

1. Full native, integrated Codex Desktop DAG orchestration with worktree merge, cancellation/resumption of live subagent sessions and managed lifecycle. The new external CLI runner is sequential, cannot safely replay interrupted work and does not auto-merge. It must not bypass permissions.
2. Fully atomic *multi-file* installation across power loss, signed release attestations, cross-process stale-lock recovery and independent formal security review. Per-file atomicity, locking, backups and an explicit recovery utility now exist, but are not equivalent to a transactional filesystem.
3. Validated real-application Codex benchmarks with external grading, matched clean baselines, reliable token telemetry, statistical confidence, regression thresholds and independent reproducibility. The runner exists, but experiments were not executed here.
4. Live cloud/production integration and validation, incident recovery, human approval interface and any entitlement-dependent feature.
5. Demonstrated correctness of every lifecycle skill across applications, frameworks and environments; formal certification is outside scope.
6. Model/effort routing justified by actual measurements and documented API availability, not guessed quota counters.
7. Verified native Codex Desktop activation on the user's Windows machine; requires user-environment tests.

## Release criteria

No merge/release until all required CI jobs succeed, installer update/uninstall/rollback paths are exercised, security findings are resolved or explicitly accepted, and the change set is reviewed. Treat native Codex tests as opt-in because they consume account quota. Do not claim `main` has these features while this PR remains unmerged.

See `docs/PLATFORM_ENGINEERING.md` for CLI usage and trust boundaries.
