# Evidence-bound coordination

The principal interprets the user's request before the deterministic router. The
router proposes candidates; it never proves semantic understanding or starts an
agent. All tools below are optional, data-only, stdlib-only local adapters. They
do not intercept every Codex Desktop delegation and do not install global hooks.

## Native handoff intake (M07)

`python tools/guardian_handoff.py inspect --project PROJECT --handoff HANDOFF.json
--context SUPERVISOR.json` reads a producer envelope and a separately supplied
supervisor context. The context contains exactly `run`, `task`,
`expected_producer`, `expected_consumer`, `revision`, `contract_sha256`,
`obligations`, `required_checks`, `observations`. The supervisor fixes the
required check set (id/artifact_sha256/obligations) independently before intake;
the producer cannot omit a failed functional check and substitute lint. Use a synthetic `run` label,
never an account identifier or raw native-session token. The supervisor must
retain any necessary native correlation privately; a matching label does not
authenticate a session. The envelope fields are documented by `FIELDS` and
`validate_handoff` in the module. Example producer envelope:

```json
{"schema_version":1,"run":"synthetic-run","task":"fix","revision":"<40-or-64-lowercase-hex>","contract_sha256":"<64-hex>","producer":"S08","consumer":"G01","obligations":["fix"],"artifacts":[{"path":"src/service.py","sha256":"<64-hex>","obligations":["fix"]}],"checks":[{"id":"regression","artifact_sha256":"<same-artifact-digest>","obligations":["fix"]}],"unknowns":[],"status":"produced"}
```

Each observed check contains exactly `id`, `run`, `task`, `revision`, `artifact_sha256`,
`passed` (boolean), `observer` (different from producer). The supervisor supplies
actual observed checks, not a copy of producer claims. File bytes, context,
obligation coverage and check correlation are rechecked on every inspection.
Missing evidence remains `produced`. Blocking unknowns prevent acceptance; put
informational residual limitations in the task report, not an empty fabricated
check. A producer cannot claim `verified` or accept its own handoff.

`consume` adds `--consumer G01 --decision accept --reason checks-reviewed` (or
`reject`). The designated distinct consumer must inspect adequacy and invoke
the decision. Accepted is not integrated, authorized, or cryptographically
authenticated. Reinspect immediately before downstream use: persisted receipts
cannot prevent later artifact changes. `invalidated_tasks` computes transitive
revocation over an acyclic dependency graph, retaining independent tasks.

## Proportional autonomy (M08)

`guardian_policy.assess_action` separates domain consequence, action effect,
existing in-process supervisor `Grant`, actual permission observation and
evidence confidence. A high-risk authorized read continues with independent
review; it does not demand a new approval solely for the word security. A new
production, privileged, external or dependency-install effect requires actual
authority, and no action can override Codex permissions. Unknown effective
permission blocks a dependent mutation/check. A Python boolean is a supervisor
observation, not proof of OS isolation. Imported JSON cannot create a Grant.

Plans in audit/explore modes explicitly describe reads. Build/remediation plans
remain proposals with unassigned scope and no execution authorization. Budgets
may be refined by the principal within the user's existing scope; mandatory
gates and uncovered obligations must never be silently dropped.

## Client observations (M09)

`guardian_capabilities.runtime_context` binds client/version/OS, native role
names and observed profile hashes, exposed tool IDs and effective configuration
digest. The caller must use the current session inventory. Installed files and
declared tool needs alone do not establish availability. `bind_observation`
records short-lived feature evidence (default one hour, maximum one day).
`require_runtime_dependencies` refuses a changed context, expired/future record,
absent role/tool or unknown required feature. Conservatively refresh observations
after any profile digest change, including a display-only edit; the stable role
identity and permissions do not change merely because its presentation changes.

The CLI can bind `--context CONTEXT.json --observations FEATURES.json`; check a
saved bound observation using the same flags plus `--check-bound`, optional
`--require-role`, `--require-tool`, `--require-feature`. stdout is a report; save
it only in a reviewed local evidence directory. `--probe` by itself only reads
the CLI version. No model is invoked and credentials are not inspected.

Legacy version-only reports remain compatible diagnostic views and are not
fresh runtime dependency evidence. For a dependency on a restriction, use the
bound check at the execution boundary; an `unsupported`/`unknown` capability
blocks that action. Never enable a TOML restriction flag from a version guess.
Codex profiles inherit parent permissions; supported feature reductions must
be verified in the actual client. See [official OpenAI subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents)
(consulted 2026-11-02). Guardian adds no OS isolation or permission bypass.

`guardian_platform.py preflight --plan PLAN.json --observation BOUND.json
--context CURRENT.json --tool-bindings BINDINGS.json` checks every proposed
task's required professional/task tools and actual native role/profile digest
against the current canonical catalog and bound observation. Bindings map abstract
tool capabilities to lists of current tool IDs. Restriction features (including
filesystem/network isolation) are checked as features, so binding them to a shell
cannot waive an unknown restriction. A missing/stale role, unknown spawn or missing tool blocks its dependent task;
unaffected tasks retain their own disposition. The principal invokes this before
native delegation when using machine-readable plans. A passing dependency check
does not authorize execution or attest tool correctness/isolation.

## Small teams and useful metrics (M10)

`python tools/guardian_coordination.py team --input TEAM.json` accepts exactly
`obligations`, `candidates`, `mandatory_roles`, `max_agents`. Candidates contain
`id`, `covers` and actual `available` boolean. A deterministic set-cover
heuristic with redundancy pruning keeps mandatory gates, reports uncovered
obligations and refuses budget overflow. The principal must adjudicate semantics;
this is neither global optimization nor proof that the smallest team is best.

`waves` accepts `tasks` (id/dependencies/closed task contract) and `max_parallel`.
Independent tasks can share a wave; declared overlapping write ownership cannot,
including case aliases. Missing dependencies and cycles fail. Actual permissions
and meaningful checks remain necessary before execution.

`metrics` accepts only a numeric ledger of task labels, obligation IDs, elapsed
time, calls, rework, acceptance, optional tokens and cost with an explicit kind
(`unknown`, `estimate`, `billed`) and currency. Multiple currencies/kinds are not
summed together; missing cost/usage stays unknown. An obligation counts accepted
only when every contributing task is accepted. No prompt, raw model output,
account identifier or credential is retained. Metrics are local supervisor
observations, not provider invoices or an authenticated performance benchmark.

Python API names and closed schemas are exercised by `test_native_handoff.py`
and `test_coordination_improvements.py`. The installer copies the modules as
runtime resources; using an adapter does not change global configuration.
