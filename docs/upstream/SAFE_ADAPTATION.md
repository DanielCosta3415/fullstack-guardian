# Safe local adaptation of the VoltAgent reference catalog

Guardian reviews the MIT-licensed `VoltAgent/awesome-codex-subagents` catalog as
reference material. It does not bulk-install its profiles, execute its prompts,
provision servers, or synchronize a moving remote branch. The source lock pins
175 profile hashes at commit `16f880a2a0486f880da75d2baffcd68af4cc4811`.
A local path is required. Documentation is inventoried but is not covered by
those profile hashes. A hash match establishes bytes, not expertise or safety.

## N12 — Correct the authoring example locally

The upstream README uses `[instructions]` plus `text`; its 175 actual TOMLs and
CONTRIBUTING contract use top-level `developer_instructions`. Use the actual
profile contract as the safe reference:

```toml
name = "bounded-reviewer"
description = "Review the delegated component and report reproducible findings."
developer_instructions = """
Read only the assigned scope. Return evidence, uncertainty, checks performed,
and unresolved questions. Never claim checks that were not performed.
"""
```

Model selection is intentionally inherited. This example does not grant tools,
create a sandbox, spawn a thread, or establish compatibility with every client.
Validate discovery and effective permissions in the target Codex session.

## N13 — Make truth and authorization non-waivable

Several terminal upstream rules end in an exception for a parent request,
including `error-coordinator` (line 40) and `eval-engineer` (line 35). A parent's
request cannot make an unsupported conclusion true or authorize an otherwise
unauthorized target. Replace that pattern during any future reviewed adaptation:

- State confirmed facts, inferences, uncertainties and missing evidence separately.
- Never invent evidence, claim unexecuted checks, conceal disagreement, or certify
  full security/accessibility/compliance from a narrow review.
- Scope expansion may be authorized; truthfulness and permission boundaries cannot
  be waived. Higher-priority instructions and effective controls always apply.

The linter marks these patterns as blocking for adaptation. This is static
screening, not proof that every unsafe wording will be detected.

## N14 — Separate declarations from effective confinement

A TOML `sandbox_mode` request is not independent evidence of restrictions in
Codex Desktop, inherited shells or MCP tools. Availability and permission checks
must be observed in the intended client. Keep reviewer and implementer roles
separate. Record unsupported capabilities and stop dependent risky execution.
Never claim sandbox guarantees merely because a profile parsed successfully.

## N15 — Treat models, MCP and global install text as prerequisites

Upstream pins three model names; pins do not perform adaptive specialist routing
or establish current model availability, quality or budget. Guardian retains its
parent model unless an explicit compatible policy authorizes an override.

`browser-debugger` declares a localhost MCP URL; `docs-researcher` declares a
remote documentation MCP. Neither configuration proves a trusted, available
server. Independently verify the endpoint, transport, authentication, allowed
operations, data exposure and actual tool contract. The local linter does not
connect to either endpoint.

`visual-asset-generator` requests asset writes and an unpinned global npm install
while declaring read-only mode. Do not execute that setup text. Use an already
authorized capability where suitable, or perform a separately scoped dependency
and installation review. No MCP, npm package or model is installed by this guide.

## N16 — Derive indexes and routing ownership from actual files

The snapshot has 191 tracked files and 175 local profiles in 13 categories.
Developer Experience has 15 profiles, while both its index and main index omit
`visual-asset-generator` and the main count says 14. Meta & Orchestration has 11
local profiles; the main count of 12 includes an external `pied-piper` link.
An external reference is not an installed specialist.

The Guardian source-lock mapping for `performance-monitor` is corrected to
`S19` (capacity/performance), `S21` (observability), and `A00` (orchestration).
Previous `S15` referred to supply-chain security. A mapping denotes responsibility
fit; it is not proof of domain proficiency or a passed practical evaluation.

## N17 — Reproduce the local review without remote execution

From the Guardian source checkout, with the reviewed catalog supplied locally:

```text
python tools/guardian_upstream.py review --source-dir <local-voltagent-checkout>
python -m unittest discover -s tests -p test_upstream_review.py -v
```

The tool reads bounded regular files, rejects symlinks/reparse components and
unlocked/missing/drifted TOMLs, parses locked profiles only after checking all
hashes, and reports inventory, declaration warnings and blocking truth exceptions.
Exit 0 means no blocking wording found; exit 2 means a completed review found
blocking patterns; exit 3 means invalid/drifted/unsafe input. Exit 0 does not mean
expert competence, production readiness, or permission to import. Review results
always disable installation and remote synchronization. The caller may store
stdout in a private report; the tool does not write upstream or Codex files.

A new upstream revision requires human-reviewed changes to the lock and tests;
there is no fetch, install, execute, plugin-provisioning or auto-sync command.
The local directory must be operator-controlled: the linter is not a sandbox
against a concurrent hostile filesystem writer.

## Adoption decision

Adapt bounded working modes, concrete return contracts, source citations,
minimal changes, parallel ownership and explicit unverified checks. Avoid
marketing superiority claims, global provisioning text, fixed platform
assumptions, conflicting terminal exceptions, and persona count as a quality
metric. Extend specialization through task-shaped playbooks and independently
scored realistic evaluations before expanding the permanent agent roster.

The upstream MIT notice and existing attribution remain in
`THIRD_PARTY_NOTICES.md`. No upstream source files are copied by this guide.
