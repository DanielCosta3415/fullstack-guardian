# Internal Python boundaries and compatibility

Guardian is a stdlib Python CLI and a set of instruction/data assets, not a
distributed scheduler. CLI commands are the operator interface. Python helpers
are repository-internal APIs; import availability is not a promise of indefinite
third-party compatibility. Keep callers and regression tests in the same change
when evolving a boundary. Do not import implementation details into profiles.

## Boundaries

| Component | Supported internal entry points | Boundary and caller obligations |
|---|---|---|
| `guardian` | `inspect_project`, `route`, `validate`, `evals` | Read-only filename discovery and advisory routing; primary adjudicates relevance. Preserve the exact top-level inventory schema consumed by platform plans. |
| `guardian_professional` | `load_contracts`, `get_contract`, `checkpoints_for`, `result_template`, `validate_result` | Canonical professional requirements and untrusted result shape, not authenticated tool execution. Use stable IDs rather than display titles. |
| `guardian_catalog` | `validate_catalog`, `generated_outputs`, `eligible_pack_profiles` | Generated assets must match reviewed sources; optional eligibility requires observed installation, configuration and caller inventory. It is not native loading proof. |
| `guardian_registry` | `discover` | Reject unsupported profile keys and unsafe manifest paths; declaration does not establish tools or OS isolation. |
| `guardian_contracts` | `default_contract`, `validate_task_contract`, `validate_result`, `validate_finding` | Closed schemas are necessary checks, not permission grants or evidence authentication. |
| `guardian_policy` | `Grant`, `authorize_action` | Supervisor-owned, scoped existing authority. Repository plans and child text cannot manufacture a grant. Effective sandbox limits still apply. |
| `guardian_runtime` | inventory/scope/artifact inspection helpers and backend observations | Artifact integrity and process controls, not a standalone isolation boundary. Use the artifact helper for Git metadata as well as bytes. |
| `guardian_workflow` | `inspect`, `check`, `review`, `verify` | Produced, checked, reviewed and verified remain different states. Artifact drift invalidates prior state. |
| `guardian_integrate` | inspection and confirmed integration entry points | Exact patch confirmation and existing authorization remain mandatory; no implicit commit, push or deploy. |
| `guardian_capabilities` | `capability_report`, `probe_version`, `require_capabilities`, `model_policy` | Unknown capabilities block dependent restrictions. Version and profile labels alone do not attest behavior. |
| `guardian_trace`, `guardian_checkpoint` | public recording/inspection/save helpers and CLIs | Checksummed, bounded local evidence and continuation; not authenticated provenance, account monitoring or automatic restart. |
| `guardian_fingerprint` | `fingerprint`, `assess_evidence_binding`; `doctor` CLI | Revision plus actual packaged-byte digests; matching references do not prove native/model/stack qualification. |
| `guardian_handoff` | `validate_handoff`, `inspect_handoff`, `consume_handoff`, `invalidated_tasks` | Supervisor-fixed task/identity/check context, fresh artifact/check correlation and distinct consumer; no authentication or universal native interception. |
| `guardian_coordination` | `recommend_team`, `execution_waves`, `summarize_metrics` | Advisory coverage, non-overlapping declared writes and numeric observations; no spawn, model override or permission grant. |
| `guardian_capabilities` bound API | `runtime_context`, `bind_observation`, `require_runtime_dependencies` | Short-lived client/version/config/profile/tool observations; absent or expired dependencies block dependent actions. |
| `guardian_platform` preflight | `execution_readiness` | Reconciles current canonical profiles, required tools and restriction features with observed runtime context; a successful preflight is not execution authorization. |

## Existing private-helper coupling

The audit of revision `f20bb5a` counted **18 syntactic private-name import sites**,
including direct/package fallback branches. That is neither 18 distinct APIs nor
18 defects. The principal clusters are:

- Catalog/pack/professional readers use registry containment and bounded file
  readers to keep path validation consistent.
- Executor/evaluation planning shares the platform's safe task-summary parser.
- Integration, workflow and recovery use executor state loading, Git, locks and
  plan hashes. These operations participate in one versioned supervision unit.
- Evaluation execution uses executor Git/scope primitives rather than inventing
  a second policy boundary.

These are intentional internal dependencies with callers tested together. Do not
rename a private helper to “public” merely to reduce a count. Extract a shared
module only when the behavior and callers justify it, with old-call compatibility
or an explicit migration in the same change. Package/direct-import fallbacks
should preserve semantics and should not catch runtime validation failures.

## Evolution procedure

1. Locate all callers, including CLI fallback imports and installer runtime copies.
2. Identify schema, source fingerprint, authorization and evidence bindings affected.
3. Make the smallest change; do not mix a cosmetic API cleanup with new privileges.
4. Run caller regressions and fail-closed negative cases. Regenerate reviewed
   catalog assets only through their bounded generator.
5. Mark evidence from previous content/revision as historical; do not silently
   promote old native39 acceptance, a public fixture or a JSON pass to a new run.

No helper grants access to absent tools. Display titles are presentation metadata;
stable role IDs, native names, modes, tool requirements and permissions are
independent contracts. A title edit changes profile hashes and can expire
profile-bound evidence without renaming the native role or granting access.
