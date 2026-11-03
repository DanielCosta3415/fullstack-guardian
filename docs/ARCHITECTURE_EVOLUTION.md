# Current architecture and audit-driven evolution

This document describes the package, not a claim of universal competence or
automatic interception of every Codex Desktop action. `VERSION` remains the
published base version while unreleased changes are identified by Git revision
and observed content digests. See the current release notes for release status.

## As-Is: two execution paths, one accountable principal

| Layer | Actual responsibility | Explicit limit |
|---|---|---|
| Global/project policy and skills | Principal assumes A00, understands obligations and chooses applicable workflows | Instructions neither grant permissions nor guarantee a particular client's hot reload |
| Canonical contracts and catalog | 29 core plus 10 optional role definitions, professional methods and 132-capability assignments | Availability, installation, loading, execution and professional competence are separate observations |
| Discovery and planning | Filename inventory, intent obligations and symbolic router suggest relevant owners and waves | They do not prove semantic understanding or authorize execution |
| Native delegation | Primary invokes the actual available Codex roles and checks their bounded deliveries | Native inventory/tools must be observed; the package does not secretly replace the client scheduler |
| Supervised CLI | Closed task contracts, scoped grants, private checkouts, checks, review and integration | Supervisor enforcement is not a general OS sandbox proof |
| Evaluation | Static regressions, data-only cases, native identity runs and domain checks with distinct scopes | Public oracle matches do not establish private holdout or universal professional qualification |
| Distribution and operation | Transactional installer, recovery, opt-in hooks, versioned release policy, trace and continuation | No implicit hook trust, production authority, account access or automatic quota restart |

The source is one Python package with JSON/TOML assets and Git worktrees. Its
control flow has intermediate complexity, while deployment remains simple. Keep
this architecture until measured requirements justify another component. A
project's business criticality and required architecture cannot be inferred from
Guardian's own module count.

## Implemented inventory responsibility boundary (M11)

`inspect_project` scans filenames only; it does not import source or execute
manifests. Product stack signals are separated from tests, fixtures, examples,
generated files and documentation. Counts and excluded extension signals are
reported under `architecture_as_is_heuristic`; the top-level inventory schema
remains compatible with plan validation. CI files remain product delivery signals.
Hyphenated `*-fixtures` roots also count as fixtures. A relative top-level
`work/` directory is treated as generated, while `.guardian-state/` is not
recursed into. These conventional-name hints can be wrong for a particular
project; the principal must inspect an unusual source layout before relying on
them. A project whose own root is named `work` is unaffected by that child rule.

A root `main.py` identifies a Python candidate even without a packaging manifest.
Adding `tests/fixtures/dotnet/demo.csproj` does not promote the product to .NET or
change the implementation specialists. Mixed product `.py`/`.csproj`/`.tsx`
signals are retained together with low confidence; no categorical architecture
or runtime claim follows. Directory names are heuristic responsibility hints,
not a security boundary or a replacement for principal code review.

## Implemented identity boundary (M12)

Run:

```powershell
python -B tools/guardian_fingerprint.py doctor --root .
python -B install.py --user --doctor
```

The standalone doctor reads bounded packaged assets and reports the version,
Git revision where this root has its own Git marker, tracked dirty state,
runtime/profile/contract digests and file counts. Installed roots without their
own Git marker report revision unknown rather than inheriting an unrelated
ancestor project's commit. Installer doctor adds the same observed identity
after its normal receipt/file/policy checks. Neither command calls a model or
reads Codex authentication. Source ZIP and installed layouts may contain
different packaged file sets, so compare exact scopes as well as digests.

An optional `--evidence-file` may contain `runtime_binding` with exactly
`runtime_sha256`, `profiles_sha256`, `contracts_sha256` and `revision` from the
observed identity. Missing bindings remain `NOT_VERIFIED`; differences are
`STALE`; matching references are `MATCHED_NOT_AUTHENTICATED`. All outcomes keep
`native_verified=false`. Native session/model/tool/stack/dataset evidence still
requires its own corroboration. Display-only profile changes expire profile
hashes without changing stable IDs or permissions.

See [internal API boundaries](INTERNAL_APIS.md) for the coupling review and
compatibility procedure. No speculative refactor is required just to eliminate
private-name imports.

## To-Be and acceptance, without unsupported claims

Continue to keep obligations, artifacts, actual checks, unknowns and consumer
decisions together. Artifact verification must cover Git metadata as well as
bytes; role evaluation must discriminate plausible failures; release policy must
distinguish required from observed evidence; and client restrictions must reflect
actual supported behavior. Dedicated modules implement those controls, with
independent review and scoped tests required before a release decision.

The principal selects a minimal sufficient team, separates parallel write
ownership, and re-evaluates when evidence changes. A local identity match is not
proof that every role was executed in this candidate. Unavailable native,
browser, .NET, cloud or private-holdout tests stay explicitly not verified.
