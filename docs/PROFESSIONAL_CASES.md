# Professional artifact cases — public objective subscopes

## Public response protocol 2

Each task now publishes a versioned, fixture-independent definition for every output field in `tools/guardian_professional_protocol.py`. It specifies namespaces, formats, decision/fault vocabularies, calculations and whether a field describes supplied observations or a normative recommendation. These rules are supplied verbatim before an evaluation, together with the exact case inventory; they are not generated from expected answers. Native summaries bind the protocol version and public inventory digest. Provenance-valid returned JSON is retained even when its case inventory is invalid.

Three formerly ambiguous fields have explicit protocol-2 names: `verified_claim_ids` contains claim IDs whose required evidence is fully present, never evidence IDs; `unsafe_flow_ids` flags a missing tenant check or a cross-tenant request as static risk without claiming observed disclosure; `secrets_may_be_granted_to_untrusted_code` is a normative prohibition, distinct from the input snapshot's actual secret access. Focus faults, recovery blockers, DI edges and decisions also have published generic vocabularies. Decimal retention calculations use a fixed precision of 28 significant digits.

The initial protocol-1 native development run remains recorded as 37/39 corroborated children, 97 observed cases, 66 passes and 31 failures. Independent review found 27 primarily underspecified response contracts, three domain/oracle ambiguities and one mixed protocol/task-adherence failure. One additional child returned unknown/duplicate case identifiers; another lacked a valid completed final. Quota was observed, but does not explain every failure. No old answer is regraded or silently promoted under protocol 2. A new complete run is required, and passes from different attempts must not be pooled.

All 39 professional profiles additionally require exact identifier/obligation reconciliation, separation of observed facts from recommendations, and a final check of types, units, boundaries and closed output contracts. These practices support professional handoffs; they do not certify expert competence.

This layer supplies **103 versioned fixtures for all 39 Guardian roles**, bound to the original 103 `independent_sme` case IDs and complete source-case digests. It adds concrete data artifacts and checkable tasks; it does not change the original professional corpus, its oracles, execution statuses or qualitative review requirements.

`eval/professional-cases/catalog.json` records every original criterion's digest and scope. Correctness is explicitly **PARTIAL_OBJECTIVE**: only the named artifact projection is checked. Evidence provenance, overall safety and collaboration/recipient acceptance remain **NOT_ASSESSED** by this layer. Every manifest names remaining semantic review. No case has a fabricated SME approval.

## What the tasks actually do

The fixtures are static domain artifacts: transaction journals, migration steps, contract inventories, request/response traces, dependency graphs, recorded measurements, focus/accessibility properties, workflow permissions, source/target keyed values, evidence ledgers and missing-policy inventories. A candidate must produce a structured analysis artifact from those inputs. Trusted, stdlib-only allowlisted functions compute the independent expected projections. Candidate Python, PowerShell, SQL, JavaScript and arbitrary commands are never executed.

These tasks make concrete, narrower assertions than complete professional competence. For example:

- Financial cases calculate conserved minor-unit balances and reject duplicate durable keys; they do not prove a real DB isolation level or gateway behavior.
- API cases compare actual required-field/enum inventories and webhook-delivery timestamps; they do not start an HTTP server or generated client.
- UI cases identify stale responses, missing focus targets and duplicate announcements in supplied traces; they do not execute a browser, screen reader or keyboard session.
- Cloud cases inspect stateful replacement plans, DNS reachability records and zone dependency inventory; they never call a cloud provider or apply infrastructure.
- Performance cases compute nearest-rank p99/median/mean over supplied samples. Results are not a new load test or a representative production benchmark. The 100-sample S19 first case deliberately distinguishes a single maximum from the 99th percentile.
- Evidence-limit cases reject unsupported execution, authorization and recovery claims. This is useful abstention/evidence accounting, not a substitute for the missing execution.

The two policy-dependent originals, **S14:professional:3** (retention/deletion) and **S25:professional:2** (licensing), contain no authorized policy. Their expected objective answer is `ABSTAIN_POLICY_UNAVAILABLE`, with explicit missing-policy IDs and no universal compliance claim. Correct abstention does not answer the underlying legal/policy question. Even a contrast supplying policy identifiers requires authenticated policy review rather than automatic legal approval.

## Commands

```powershell
python tools/guardian_professional_cases.py validate
python tools/guardian_professional_cases.py preview
python tools/guardian_professional_cases.py grade --case S08:professional:1 --result RESULT.json
python tools/test_native_professional.py
```

The first command validates all 103 bindings, fixture hashes and rubric traces. Preview exposes only public scenario/task/input/response schema and remaining scope. Grading is declarative comparison of the candidate's JSON bytes, not code execution. Unknown IDs, wrong types, extra fields, incorrect values and nonfinite numbers do not pass. JSON duplicate keys, symlink/reparse paths and excessive file size are rejected by shared strict readers. Finite number fields (mean_ms and median_ms) accept integer/float notation with relative and absolute tolerance 1e-9. Integer fields, including monetary minor units, require exact integers; booleans never pass as integers. Decimal strings remain exact. Arrays are unordered collections preserving multiplicity except literal_paths, whose literal input order is required. These grading rules are public before native evaluation. Dynamic result-map keys and result array contents are absent from public schemas, preventing answer leakage through schema generation.

A successful grade is `OBJECTIVE_SUBSCOPE_OBSERVED`, with `sme_qualified: false` and `private_holdout_validated: false`. Without a corroborated native observation it is only a local data-comparison result: supplied JSON alone does not prove authorship, model identity or execution.

## Optional native observation

After explicit quota coordination and source freeze:

```powershell
python tools/test_native_professional.py --run --out NEW_OUTSIDE_SOURCE_DIRECTORY --timeout 3600
```

Without `--run`, the harness only previews its plan and consumes no model quota. With opt-in it installs the current core profiles and ten optional packs **inside a new disposable project**. It uses existing authorized Codex authentication without copying credentials, changing models or granting permissions. Exactly **39 native children**, each receiving its own two or three tasks, must be spawned with their declared role and `fork_turns="none"`; at most three run concurrently. A00 is first. There is one observation per role, not a repeated-run reliability benchmark.

The parent receives only the public inventory. Children receive only their role's public task data and schema; no expected results, private grading output or another child's answers are supplied. Parent and child tool use is checked against the data-only policy. The allowed parent operations are native collaboration spawn/wait/close/list only; children use no tools or further delegation. The supervisor corroborates each child's actual role, parent, spawn-call/output pair, path, completion, model and unique final JSON using native session records. Missing/duplicate/wrong-role/unexpected children, unauthorized tools or incomplete artifact inventories invalidate success.

The model returns actual final JSON. The supervisor persists that corroborated content as `project/observed-artifacts/professional_NN.json`. **This is a supervisor materialization of model output, not a claim that the child wrote a file.** The installed profile digests, source snapshot, fixture/config snapshot, observed results and remaining limitations are reported. Failed answers remain failed; the harness does not retry until favorable results appear. All 103 objective tasks must pass for exit zero, alongside all 39 corroborated roles and unchanged source/configuration. This still does not certify any complete SME rubric.

`summary-public.json` contains role/case results, hashes and scope limits. Raw prompts, events, stderr and native session identities remain in private local logs. POSIX creation modes are requested, but Windows inherited ACL privacy is **not certified**. The subprocess timeout attempts parent termination; descendant cleanup is **not certified** and may require operator cleanup.

## Separation and remaining gates

The oracles are public project source. Package installation can copy tools/eval into the disposable project; the shared OS account may also read the source checkout. Oracle separation is **procedural and checked after execution**, not OS-enforced secrecy. The harness detects forbidden tool calls; it cannot establish a secret holdout, prevent all same-account observation or provide a rootless boundary by itself. A real private holdout needs independently controlled OS/account access and separately authored secret cases. Do not call these fixtures private or claim held-out generalization.

The 103 complete professional judgments, real framework/provider/AT tests where relevant, authenticated execution provenance and representative stakeholder/business context remain separate requirements. Review by agents and objective checks can inform decisions without assuming human identity, credentials or unlimited correctness.

## Verification

```powershell
python -B -m unittest tests.test_professional_cases -v
```

The suite has manually calculated golden outputs for **each of the 39 families**, plus a separate input contrast changing an independently stated expected outcome in every family. It checks all 103 artifacts against correct data projections and rejects wrong-field mutations and approval-shaped substitutes. Additional checks cover source/fixture/rubric drift, malformed catalogs, missing/duplicate/unknown IDs, traversal, exact native inventories, absent native evidence, schema/prompt oracle omission, forbidden parent tools, complete per-child results and policy abstention. Unit fixtures are synthetic evidence for the harness, never reported as executed models or live applications.

## Family inventory

| Family | Cases |
|---|---:|
| `accessibility` | 3 |
| `backfill` | 1 |
| `boundary` | 1 |
| `checksums` | 1 |
| `cloud_plan` | 2 |
| `cohorts` | 2 |
| `conflicts` | 1 |
| `contract` | 6 |
| `cost` | 2 |
| `counterexample` | 1 |
| `currency` | 2 |
| `di_lifetime` | 1 |
| `dns` | 2 |
| `evidence_limits` | 19 |
| `external_policy` | 2 |
| `fencing` | 1 |
| `focus` | 3 |
| `injection` | 2 |
| `jwt` | 1 |
| `latency` | 3 |
| `ledger` | 6 |
| `locale` | 1 |
| `migration` | 3 |
| `mutants` | 3 |
| `obligations` | 2 |
| `permissions` | 1 |
| `provenance` | 3 |
| `release_context` | 3 |
| `relevance` | 2 |
| `restore` | 3 |
| `ssrf` | 2 |
| `stale_response` | 2 |
| `submission` | 3 |
| `tenant_flows` | 4 |
| `topology` | 1 |
| `traces` | 1 |
| `webhook` | 2 |
| `windows_path` | 3 |
| `workflow` | 2 |

Total: 103 tasks, 39 families, 39 roles.
