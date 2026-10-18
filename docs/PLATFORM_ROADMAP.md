# Fullstack Guardian — platform evolution roadmap

Status: **incremental development**, not a completed platform or certified security system.

## Baseline

v2.1.0: 29 core profiles, eight skills, 132 capability checks, heuristic router, local installer and opt-in Codex native smoke tests.

## Platform foundation: current development branch

- A read-only extension registry validates existing core agent definitions and optional specialization packages.
- Pack manifests are versioned and must refer to bounded paths inside each pack.
- Model and sandbox settings are intentionally inherited rather than overridden by add-on packages.
- Pack discovery does **not** install plugins or change Codex configuration.
- Initial dotnet pack provides one specialist. Tests use isolated Python fixtures.

Commands from repository root:

```sh
python tools/guardian_registry.py validate
python tools/guardian_registry.py list
python -m unittest tests.test_guardian_registry -v
```

## Roadmap / not yet implemented

1. v2.2 hardening: more installer adversarial tests, transactional write recovery, platform-specific path tests, supply-chain verification.
2. v2.3 specialization: deepen all core profiles, metadata and migration contracts, optional specialization packs.
3. v3.0 orchestration: bounded task-DAG plans, execution ledger and evidence schema, cancellations and independent audits.
4. v3.0 engineering lifecycle: discovery through decommission workflows, explicit acceptance criteria, verification gates.
5. v3.1 observability and benchmark suite: A/B comparisons with identical models and test cases, native execution and transparent quota costs.

## Non-negotiable invariants

- Never claim a static validation is proof of native Codex execution.
- Never change live production, credentials, model selection, sandbox or user config as a side effect of catalog discovery.
- Guard supply-chain trust: review external prompts/scripts and user-granted permissions independently.
- Preserve dry-run, conflict detection, backup and rollback in the current installer.
- Require measurable regression and integration evidence before claiming better quality or readiness.
