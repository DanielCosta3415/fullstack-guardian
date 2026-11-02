# Release acceptance and global rollout

Version 2.2.1 requires explicit release acceptance. A successful package build or a
local AI review does not promote it to stable. Pin every acceptance result to
the final commit and exact ZIP. A version/manifests change creates a new commit
and invalidates earlier revision-specific release evidence.

## Release profiles

`strict` remains the compatible default below. An operator can explicitly choose
`operator-autonomous` when human PR approval and a dedicated remote native test
are outside the product's accepted release process. This deliberate policy choice
is recorded, rather than treated as a missing approval or a completed remote test.
See [the autonomous release policy](AUTONOMOUS_RELEASE_POLICY.md) for its required
corroborated local 39-profile execution and distinct native G01/G02 advisory
reviews. CI, the isolated grader and exact signed ZIP provenance remain remote
requirements under both profiles. There is no automatic fallback between them.

## Required release evidence for strict

1. Full CI matrix and actual installed-runtime tests for the final commit.
2. Local native 39-profile smoke with real case-directory checks, then the
   explicit native workflow's private-safe artifact on the same commit.
   Public typed reasoning observations are a separate evaluation layer.
3. Executed isolated grader acceptance, without skipped backend tests.
4. Independent G01/G02 and a current, authorized independent human PR review.
5. GitHub OIDC build provenance verified for the downloaded ZIP and commit.
6. Installation, update, rollback and uninstall of that exact remote package
   in disposable user and project layouts, preserving existing settings.
7. An explicit operator release decision. The verifier never publishes.

`tools/guardian_release_gate.py --verify-external` checks actual GitHub workflow,
artifact, review and signed provenance evidence. Never generate a substitute
JSON approval, count local logs as the remote native workflow, or approve a PR as
if an independent human. Changing release policy is an explicit operator decision;
unavailable infrastructure alone never selects a less restrictive profile.

### Requirement matrix and decision receipt

`core/release-policy-matrix-v1.json` is the versioned requirement matrix for
`inspect`, external verification and their `requirement_receipt` output. The
verifier rejects missing, duplicated or downgraded policy rows. Each requirement
records whether it is required, its verification method, its observed status and
concrete evidence references. Status is one of `not_verified`,
`verified_external`, `verified_local`, `manual` or `not_applicable`. A `manual`
row explicitly remains **unverified by this tool**; neither a model claim nor
the mere presence of that row satisfies it.

Both profiles require independent G01 **and** G02 advisory reviews. Strict also
requires the human PR approval and remote native workflow; those activities do
not replace either specialist. Supply `--advisory-review G01.json
--advisory-review G02.json` under either profile, using the native-session and
claim binding described in [the autonomous policy](AUTONOMOUS_RELEASE_POLICY.md).
They remain local, same-account mutable evidence even under strict. No claim of
human authentication or stronger host isolation is inferred from that choice.

Older strict invocations can still check remote workflows, human reviews and
provenance without those two reports. Their receipt then has
`external_checks_passed=true`, **`policy_acceptance_passed=false`**, and
`independent_G01_G02` in `pending_verifier_checks`; the CLI exits 2. Imported
approval JSON, incomplete/duplicate reviews, stale commit/ZIP claims or an
unbound native final cannot satisfy the specialist gate.

`policy_acceptance_passed` has the explicit scope
`AUTOMATED_VERIFIER_REQUIREMENTS_ONLY`. It requires every external/local check
in the selected matrix. `complete_release_acceptance_passed` additionally
includes manual obligations and remains false while they are outstanding.
The local preliminary smoke under strict, installation/recovery of the exact
downloaded remote ZIP under both profiles, and the operator release decision
are separate manual obligations. CI distribution tests cover CI-built fixtures;
they do not prove recovery of the exact downloaded, signed release ZIP.
Keep reviewed evidence for those obligations with the release. The verifier
does not authenticate a manual disposition, perform the release decision,
publish, or confer production authorization.

## Native runner provisioning

The native workflow is manual and requires an authenticated Windows runner with
the `guardian-native` label. It must first be registered on the repository's
default branch. Dispatching an unregistered workflow on a feature branch cannot
substitute for registration. Do not merge unrelated changes to bootstrap it.

Provision only a dedicated, disposable machine with an operator-authorized
Codex login, a reviewed commit and the intended repository access. Do not copy
the developer's auth.json to a hosted runner or store it as a repository secret.
Do not register a persistent public-repository runner on a personal workstation
as an incidental installation step. Runner registration, the VM and login need
their own authorization and lifecycle controls. See GitHub's
[workflow dispatch documentation](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)
and [runner security guidance](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions).

## Artifact preparation and verification

The existing `release.yml` workflow can prepare a signed artifact without
publishing a GitHub release. Dispatch it explicitly on the reviewed branch.
Download the `guardian-release` artifact into a new workspace directory, verify
its GitHub attestation with repository, source digest and signer workflow, then
verify ZIP membership, all manifest hashes and CRC before extraction.

Use the downloaded package's `tools/verify_distribution.py` with a short,
workspace-owned `--temp-dir` to exercise disposable user/project lifecycle and
all ten packs. This command does not change the real global installation.
Preserve the workflow ID, commit, artifact digest, manifest and test report.

Canonical release builds use committed bytes from a clean checkout. Working
tree CRLF conversions can change archive hashes despite a clean Git status.
Do not apply a CI artifact's signature to a different locally built ZIP.

## Global update and rollback

Run the exact accepted package's installer in dry-run first. Preserve the
current receipt, user-owned configuration and backups. The installer recognizes
only legacy v2.0/v2.1 policy heading/EOL formatting drift with otherwise identical
nonempty instructions. Any semantic policy edit, malformed marker, changed owned
file or modified configuration remains a conflict requiring explicit review.
Unmanaged bytes outside the policy block remain intact; transaction rollback
restores the complete previous file, including its formatting.

Only after the release decision and filesystem permission grant, apply the
global update, run doctor/catalog/evaluation, verify optional pack ownership
and confirm real native role discovery. Hooks remain opt-in and require native
trust review; installing agents/skills never silently enables global hooks.

## Qualification and product claims

The 103 public open scenarios are evaluation designs. Use
`guardian_professional_review.py` for scoped artifacts and criteria, never to
authenticate a person or certify expertise from imported JSON. AI advisory
reviews, external unauthenticated records and objective checks remain separate.
Private holdout requires a separate evaluator-controlled OS/account and secret
cases. Live A/B requires its explicitly isolated authentication. Missing external
dependencies block those claims; installing the package cannot create them.

## Explicit independent reviewer without repository write access

The external verifier accepts repeatable `--trusted-reviewer LOGIN` options. The
operator must name trusted reviewer accounts explicitly for that invocation;
there are no default personal accounts and no trust inferred from conversation,
PR text, local JSON or artifact content. For the operator-named reviewer:

```powershell
python tools/guardian_release_gate.py --verify-external --repo OWNER/REPO --revision EXACT_COMMIT --artifact EXACT.zip --ci-run CI_ID --native-run NATIVE_ID --grader-run GRADER_ID --pr-number PR_ID --trusted-reviewer cleitonncosta
```

Use actual values for every placeholder. This option authorizes recognizing an
existing GitHub review from that account even when its repository association is
`NONE`; it does not invite the person, grant access, request a review, contact
anyone or create an approval. No collaborator/write permission is required just
to recognize a deliberately named independent reviewer.

The account must still be a GitHub `User`, differ from the PR author (compared
case insensitively), and have an actual `APPROVED` review on the exact commit.
The latest decisive review state per account applies; dismissal and changes
requested revoke an earlier approval, and an outstanding authorized changes
request blocks acceptance even if another reviewer approved. Comments do not
substitute for approval or clear a requested change. Existing OWNER/MEMBER/
COLLABORATOR authorization remains available. Bot reviews, self-approval and
old-commit approval cannot satisfy this gate, including for explicitly named
accounts. Login syntax is validated before any network request.

The explicit account allowlist authenticates neither competence nor personal
independence beyond the recorded GitHub account and different PR author. The
operator remains responsible for choosing an appropriate reviewer. Workflow
revision/results, native individual acceptance, isolated grader evidence and
signed ZIP provenance are still required. Passing the verifier never authorizes
publication by itself.
