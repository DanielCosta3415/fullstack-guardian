# Full-Stack Engineering Guardian — 2.2.0-dev.4

Development candidate: 29 core engineering roles, 20 operational skills, 132 taxonomy capabilities and ten optional specialist packs. The public stable release remains v2.1.0 until a separate reviewed release decision.

Normal prompts are coordinated by the primary Codex thread. It selects the smallest useful team, checks task risk and uses independent review when required. Simple tasks can be completed directly. Profiles, repository content and generated plans never grant permissions.

## Install this reviewed checkout

Python 3.11+ and a compatible local Codex client are required. Installation preserves existing models, providers, permissions, profiles and unrelated instructions.

```sh
python install.py --user
python install.py --user --apply
python install.py --user --doctor
```

The first command simulates. Review conflicts before applying. For project scope replace --user with --project PATH. Start a new chat after configuration. Installing plugin setup alone does not activate the global integration. Optional packs are never installed automatically.

Windows launchers reuse an existing compatible Python, trying alternatives if py is broken; they do not download runtimes or alter PATH:

```powershell
powershell -File installer/Install.ps1 --user
powershell -File scripts/Validate-WindowsCodex.ps1
```

Linux/macOS: `bash install.sh --user`. Global paths can be adjusted through CODEX_HOME and the installer's --home. Note that guardian_packs --home means the exact Codex directory, unlike install.py --home (account parent).

## Completion work in dev.3

Canonical metadata now generates the 39 profiles; supervised checks/review/verification are hash-bound to produced artifacts; read retries have bounded backoff; journals have explicit retention and privacy observations; optional packs have rollback; executable domain fixtures and full installed-runtime acceptance are available. See [completion status](docs/COMPLETION-STATUS.md) for actual evidence and blockers.

## What changed

### Professional assurance in dev.4

All 39 roles have versioned professional contracts: methods, typed capabilities, conditional tool needs, deliverables, completion criteria, handoffs and qualification limits. Core and optional roles have their own checkpoints. Reviewer roles cannot be planned as implementers; internationalization has an explicit S07 overlay.

The primary interprets intent; the router recommends candidates and exposes uncertainty. Plans bind professional contract hashes, obligations and lifecycle responsibilities. Supervised integration requires verified professional outputs by default. Manual integration requires an explicit mode, acknowledgement of absent supervision and the reviewed patch hash.

Professional evaluation is separate from native smoke. A public development corpus contains 103 specialist-judgment scenarios requiring independent SME review and 39 narrow typed postconditions; none is private holdout or universal certification.

```sh
python tools/guardian_professional.py
python tools/guardian_qualification.py validate
python tools/test_native_qualification.py --drypreview
python tools/guardian_hooks.py install --project PATH
```

Hook registration simulates by default. `--apply` registers only; Codex's separate hook review/trust still applies and is never bypassed. Native `--run` tests consume account quota. See [professional assurance](docs/PROFESSIONAL_ASSURANCE.md), [hooks](docs/HOOKS.md) and [safe upstream adaptation](docs/upstream/SAFE_ADAPTATION.md).

- Closed task, result and finding contracts; imported plans revalidate identity, risk, phase gates, budgets and acceptance.
- Reviewed canonical catalog and generated documentation; installed/enabled/compatible optional profiles require an explicit current inventory observation.
- Version-aware unknown capability reporting, inherited model defaults and explicitly authorized overrides.
- CLI supervision with private Git checkouts, real bounded parallel read-only audits, explicit write authorization, artifact/scope postconditions and reliable Windows descendant cancellation.
- Produced results remain separate from correctness verification. Strict unsupported read/file/tool restrictions block rather than pretending a profile is a sandbox.
- Shared maintenance locking across all mutable roots, namespace-limited interrupted recovery, atomic writes, receipts and journal byte bounds.
- Grading uses declarative independent oracles and a verified rootless Docker backend; no generated target or executable checker runs on host Python.
- Paired evaluation uses isolated reviewed config, holdout/version/hash controls, balanced ordering and case-cluster intervals.
- Eight domain observation adapters and sixteen positive/adversarial regressions complement domain-native fixture specifications. A static observation pass is not native application correctness.
- Native acceptance can cover all 29 core plus ten explicitly installed optional roles in a disposable project; public summaries omit raw sessions/prompts.
- Pinned upstream reference identities, hashes and notices; no bulk import or auto-sync of the 175 external profiles.

## Inspect and validate

```sh
python tools/guardian.py validate
python tools/guardian.py eval
python tools/guardian_registry.py validate
python tools/guardian_catalog.py
python tools/guardian_capabilities.py --probe
python tools/guardian_platform.py plan --mode audit --stage integration --prompt "Review API compatibility"
python tools/guardian_domain_checks.py --self-test
python tools/run_tests.py
python tools/verify_distribution.py
```

On Windows, pass --temp-dir SHORT_WRITABLE_DIRECTORY to test/distribution runners if deep temporary paths exceed OS limits. No OS security or long-path setting is changed.

Native tests are opt-in and consume account quota:

```sh
python tools/test_native_agents.py --all --include-packs
python tools/test_native_agents.py --run --all --include-packs --out NEW_EVIDENCE_DIRECTORY
```

The preview does not call a model. The run requires a compatible authenticated Codex and applicable permission review. Recorded role, parent, completion and checks validate controlled cases, not all 132 capabilities. Do not publish raw session logs.

## Safety and operating limits

The CLI backend requests Codex sandboxing but does not prove per-file/read/network or CPU/memory isolation. Restrictive contracts need verified capabilities and fail closed otherwise. Writes are sequential with postcondition enforcement and reviewed integration. Workspaces are private checkouts, not OS sandboxes. Neither a prompt nor a local hash authenticates execution or human authorization.

Real grading additionally requires administrator-provisioned rootless Docker, cgroup v2 limits and an already reviewed local Python image pinned by digest. Missing prerequisites block grading; there is no unsafe host fallback. General application code is outside the pure-function oracle's supported subset. See [evaluation security](docs/EVALUATION-SAFETY.md).

Maintenance simulates by default: --update, --uninstall and --rollback, then --apply only after reviewing conflicts. Modified user-owned files are preserved. Do not delete active/stale locks blindly. See [support](SUPPORT.md), [security boundaries](SECURITY.md) and [implementation status](docs/IMPLEMENTATION-STATUS.md).

## Review and release

CI validates source and extracted-distribution lifecycle on the configured OS/Python matrix. Native and isolated-grader acceptance workflows are manual, operator-provisioned gates. Signed artifact provenance is created and checked by the release preparation workflow; its configuration alone is not an issued attestation.

The release verifier can check actual CI/native/grader runs, the reviewed revision and signed ZIP provenance through explicit read-only network verification. It never publishes or treats local JSON approval as authority. A stable release requires real evidence, G01/G02 and the release decision appropriate to that action. See --help of tools/guardian_release_gate.py.

[Generated 39-role catalog](docs/CATALOG.md) · [Platform operations](docs/PLATFORM_ENGINEERING.md) · [Third-party notices](THIRD_PARTY_NOTICES.md)

MIT. Independent project; not affiliated with OpenAI. Compatibility and risk are versioned, not universal guarantees.
