# Guardian platform operations — 2.2.0-dev.2

This development candidate extends the existing architecture: 29 core profiles,
21 skills and ten optional packs. The primary Codex thread coordinates normal
prompts. The deterministic router proposes a minimal relevant team; it neither
spawns agents nor grants permissions. Simple tasks remain direct.

## Planning and execution

Run `python tools/guardian_platform.py --help` and its subcommands for current
interfaces. Planning produces a closed, revalidated DAG: catalog identities,
dependencies, risk, phase, owner/reviewer and required G01/G02 gates are checked
again when imported. Use explicit task contracts with scope, checks, effects,
budget and acceptance. Repository instructions and result JSON are data.

The executor is an explicitly labeled CLI backend, not a native collaboration
API. It creates private Git checkouts with independent administrative state.
It requests the client's sandbox but cannot attest per-file read/write/network
or CPU/memory isolation. Unsupported restrictive contracts block. Independent
read-only audits can run concurrently within the configured bound; writes are
sequential and require trusted operator authorization. A completed turn is
`produced`, not proof of correctness. Review verified evidence before integration.

`guardian_integrate.py` previews a patch and its SHA-256; `--apply` additionally
requires `--confirm-sha256` of the reviewed artifact. It checks both sides of
renames, protected paths, scope and concurrent drift under a lock. It applies
uncommitted changes and never commits, pushes or deploys.

## Optional packs and compatibility

`guardian_packs.py` simulates install/update/uninstall unless `--apply` is used.
For project scope use `--project PATH`; for user scope its `--home` is the exact
Codex directory (the main installer's `--home` is the account parent).
Installed, enabled, compatible and native-verified are distinct states. Planning
requires current explicit inventory and capability observations for optional
roles; a profile file alone does not prove availability. Model defaults inherit;
explicit supported overrides require authorization.

## Evaluation

Read [evaluation security](EVALUATION-SAFETY.md) before running evaluation.
Executable checker scripts from earlier previews are incompatible. Generate a
fresh fixture with `guardian_benchmark_fixture.py --out NEW_DIRECTORY`; its
checker is declarative `trusted_checker.json`. Generated targets are never
imported on host Python. Actual grading requires a separately provisioned,
verified rootless Docker backend and a reviewed image pinned by digest. Missing
prerequisites block; there is no host-execution fallback.

Live paired experiments require `--run`, reviewed candidate guidance, holdout
data, explicit model/effort and `--isolated-config`. Both arms use fresh homes
and the same reviewed config, excluding global/project agent policies. Samples
use seeded order and counterbalanced AB/BA. Finite oracle checks and small
holdouts do not establish general superiority. Unknown usage/cost stays unknown.

Domain observation checks are static contracts. Native .NET, HTTP, browser,
PowerShell, database and AI behavior needs its own functional adapter and
controlled environment. Do not label static results as native execution.

## Maintenance, evidence and acceptance

Installation, update, uninstall and rollback simulate by default. Apply only
after inspecting conflicts. Shared maintenance locks cover mutable roots,
including shared user skills across distinct CODEX_HOME values. Interrupted
recovery accepts only proven managed namespaces, identity and matching
fingerprints; it preserves foreign files and drift. Never remove locks blindly.

The optional trace journal validates bounded UTF-8 events before atomic writes.
Hashes detect local inconsistency; they do not authenticate a person, execution
or an unforgeable history. Do not publish raw sessions or private logs.

`test_native_agents.py --all --include-packs` previews 39 selected profiles
without quota. `--run --out NEW_DIRECTORY` consumes quota and requires applicable
permission review. Each profile must spawn individually with the expected type,
parent, completion and recorded check output. These controlled synthetic cases
do not certify all 132 capabilities or every domain technology.

See [implementation status](IMPLEMENTATION-STATUS.md) for R01–R40 evidence and
remaining acceptance work. Stable promotion requires the exact reviewed revision,
real CI/native/grader evidence, independent G01/G02, verified artifact provenance
and an explicit release decision. Preparing a ZIP does not publish it or update
the user's global installation.
