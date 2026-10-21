# Release acceptance and global rollout

Version 2.2.0-rc.1 prepares release acceptance. A successful package build or a
local AI review does not promote it to stable. Pin every acceptance result to
the final commit and exact ZIP. A version/manifests change creates a new commit
and invalidates earlier revision-specific release evidence.

## Required release evidence

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
JSON approval, count local logs as the remote native workflow, approve a PR as
if an independent human, or remove a gate simply because its dependency is absent.

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
