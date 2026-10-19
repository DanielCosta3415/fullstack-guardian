# Independent grading and paired experiments

The evaluator never runs an executable checker or imports generated target code
on the host. Python `-I` is not an OS sandbox. Old executable checker files are
incompatible and rejected; regenerate fixtures using
`python tools/guardian_benchmark_fixture.py --out <new-directory>`.

## Preconditions for real grading

An administrator must separately provision a **rootless Docker daemon**, cgroup
v2 with enforced limits, and a reviewed local Python image pinned by digest.
The evaluator does not install Docker, start services, download images, change
permissions or escalate itself. Set `GUARDIAN_GRADER_IMAGE` to the reviewed image
reference (`repository@sha256:<64 hex characters>`). Mutable tags are rejected.

Run `python -c "from tools.guardian_grader_sandbox import probe; print(probe())"`.
An `available: false` response means **NOT VERIFIED**, not an acceptable fallback.
The probe checks the daemon's rootless security option, the local image digest,
and actually runs a restricted preflight container to verify uid 65534,
read-only root filesystem, loopback-only network, memory <=128 MiB, process
limit <=32 and CPU quota <=0.5 CPU. Cgroup delegation that does not enforce these
limits blocks evaluation. The environment used for this implementation did not
have this backend available; native isolation, cancellation and escape tests
were explicitly skipped rather than reported as passing. AST rejection and
container isolation have separate tests: the private native readonly-write probe
bypasses the public fixture language intentionally to exercise the OS boundary;
the timeout fixture defines an accepted pure function containing an infinite
loop, so it reaches container execution instead of stopping at AST rejection.

Each vector starts a fresh container. No host home, credentials, Docker socket
or network is mounted. Workspace input is read-only, links are rejected, all
capabilities are dropped and `no-new-privileges` applies. Writable storage is an
8 MiB noexec tmpfs; captured output is capped at 64 KiB and elapsed time is
bounded. Timeout/cancellation forcibly removes the named server-side container;
failure to confirm removal stops grading. The trusted image and rootless Docker
implementation remain part of the trust boundary; digest pinning is provenance,
not proof that an image is safe.

## Oracle contract and intentionally limited target language

`schema_version: 2` JSON oracles contain cases, named checks and bounded call
vectors. A vector specifies top-level Python file, function, JSON arguments and
expected value or exception. Expected answers stay with the host supervisor.
It requires the exact complete set of checks, checks every vector, uses strict
JSON with duplicate/nonfinite/multiple-document rejection, distinguishes bool
from int and rejects abnormal/timeout process termination. `turn.completed`,
`exit 0`, a model's claim or an arbitrary JSON `passed` field cannot award a
score.

Arbitrary Python can monkeypatch an in-process grader or forge its own result.
Consequently this backend supports **only structurally reviewed pure fixture
functions**, validated before container execution: no imports, runtime/private
attributes, arbitrary function calls, module side effects or builtin shadowing.
SystemExit, os._exit, print-based forged completion and runtime introspection are
rejected. Source is capped at 16 KiB before reading and AST parsing runs in a
killable helper with a three-second parent timeout, at most 4096 nodes and
depth 64. POSIX additionally limits helper CPU to two seconds; Linux additionally
limits address space to 256 MiB. Windows/macOS helper memory is bounded structurally by input budgets,
not by an attested Job Object limit. The helper never executes target code.
A small allowlist permits builtin type/collection operations and
ordinary string/list/set methods. Unsupported application code is NOT VERIFIED;
there is no general Python sandbox claim or unsafe compatibility fallback.
Behavioral correctness outside the finite oracle, mutation invariants not
expressed in its vectors and unseen adversarial cases remain unproven.

## Paired experiment controls

Live runs require `--run`, an explicit model/effort, reviewed candidate guidance,
versioned dataset marked `split: holdout`, and `--isolated-config` pointing to
a directory containing `config.toml`. Do not copy auth.json. An explicitly
configured environment API key may authenticate the CLI. Global agent/skill and
project policy directories are excluded; each sample gets fresh HOME,
USERPROFILE and CODEX_HOME plus a reviewed config copy. Target projects must be
clean controlled Git roots without AGENTS.md, .agents or .codex policies.

Case order is shuffled with `--seed`; paired order alternates AB/BA. Both arms
use identical model, effort, config and dataset hashes. Guidance hash, checker
hash, requested model, event hashes, repeats, actual available token counts and
elapsed time are recorded. The requested model identifier is not an attestation
of the provider's resolved model revision. Monetary cost is not fabricated.
CLI process trees are terminated on cancellation, timeout or output overflow;
worktrees are removed in finally blocks, never merged into the fixture source.

The analyzer reports a case-cluster bootstrap interval (seed 0, 2000 resamples);
it does not count repeated cases as independent evidence. Small holdouts, prompt
differences and provider variability prevent a causal or general superiority
claim. Run separate development and held-out datasets, retain failures, and
review results before promoting policy changes.

## Domain corpus

`eval/domain-fixtures/catalog.json` catalogs .NET, API, financial, data, UI,
PowerShell, cloud-plan and AI tasks with concrete broken input artifacts and
independent expected contracts outside the proposed model workspace. The
financial pure-Python oracle can use the restricted backend above. Native .NET,
HTTP, browser, PowerShell, SQLite and model adapters are **NOT VERIFIED** and are
not silently replaced by text matching. No cloud deployment or real financial
transaction is authorized by these fixtures.
