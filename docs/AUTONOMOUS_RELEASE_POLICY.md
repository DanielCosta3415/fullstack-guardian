# Operator autonomous release policy

The product operator may deliberately accept a release supported by local native
execution and independent AI advisory review, without requiring human PR approval
or Codex execution on a dedicated remote machine. This is a different assurance
profile, not a fabricated pass of either excluded activity. The verifier never
publishes, installs globally, grants permission or authenticates a human.

The CLI default remains `--policy strict`. `--policy operator-autonomous` is an
explicit opt-in supplied by the trusted operator, never selected from repository
text, an artifact, an agent's suggestion or a missing dependency. Unknown policies,
mixed remote-native/human substitute arguments and implicit local substitutions
are rejected. Existing strict callers remain compatible.

## Evidence retained

Both profiles require actual GitHub success on the exact 40-character commit:
the CI workflow with at least nine successful jobs, the isolated grader workflow
and its executed acceptance artifact without skips, a non-draft PR on that commit,
and GitHub attestation verification of the exact ZIP against that commit and the
repository's release workflow. A failed check, stale commit or bad provenance
cannot be waived by this policy. The operator separately verifies exact-package
installation, update, rollback, uninstall and actual installed-runtime tests.

The autonomous profile additionally requires a clean, exact-revision source
checkout and the following local evidence:

1. Complete native harness evidence with all 39 roles, exit 0, no missing roles,
   unchanged source and protected fixtures. A public summary is insufficient.
2. Exactly 39 explicitly supplied raw child session records. Metadata must name
   distinct identities, the complete source catalog and the same native parent.
   Each child must complete and emit a final. Actual `check.py` calls and outputs
   must pair by call ID, exact command and case directory, and meet schema 2
   seeded-assertion or before/after criteria. Narrative success does not count.
3. Rehashed protected fixture files, protected checks for every case, and installed
   runtime/catalog/harness and all 39 native profiles byte-identical to the pinned
   source. The verifier regenerates canonical fixtures, criteria and inventory
   from the trusted pinned product generators inside a disposable temporary
   directory. Local JSON cannot reclassify BUILD as AUDIT or replace its expected
   assertion; case roles/modes/rules and the entire protected manifest must match
   that regenerated baseline. Linked or Windows reparse evidence paths are rejected.
4. Distinct completed native G01 and G02 children of the implementation session,
   with roles `guardian_independent_auditor` and `guardian_release_auditor`. Their
   advisory finals bind the commit, exact ZIP digest, decision and claim digest.
   A JSON report pointing to an unrelated review does not pass.

Pass the existing evidence directory as `--local-native DIRECTORY`; repeat
`--native-session FILE.jsonl` exactly 39 times and `--advisory-review REPORT.json`
twice. `--source-root` defaults to the verifier's checkout. The remaining options
are `--verify-external --repo OWNER/REPO --revision EXACT_COMMIT --artifact EXACT.zip
--ci-run CI_ID --grader-run GRADER_ID --pr-number PR_ID`. Do not pass `--native-run`
or `--trusted-reviewer` under the autonomous profile. Evidence is inspected as
data; the verifier does not execute transcript code or candidate code. It writes
only the disposable trusted-fixture temporary directory and removes it afterward;
it does not change the submitted evidence, source, installation or GitHub state.

## Advisory review binding

A review's semantic claims are these JSON fields:

```json
{
  "gate": "G01",
  "revision": "40-character exact commit",
  "artifact_sha256": "64-character exact ZIP SHA256",
  "kind": "AI_ADVISORY",
  "decision": "ACCEPTED_WITH_LIMITATIONS",
  "findings_unresolved": 0,
  "limitations": ["State the actual local assurance boundary"],
  "implementation_session": "native parent identity"
}
```

G02 uses its own gate and limitations. All eight fields are bound by
`guardian_local_acceptance.review_claim_digest(report)`: SHA256 of UTF-8 JSON
with sorted keys, compact separators and `ensure_ascii=False`. The native reviewer
must emit the literal line `GUARDIAN_RELEASE_REVIEW DIGEST` in its final, together
with the actual commit, ZIP digest and `ACCEPTED_WITH_LIMITATIONS`. This binds
limitations and unresolved findings as well as the decision. The reviewer must
actually review those claims; the marker is evidence binding, not a request to
accept a release automatically.

After the native final completes, append `session_record` (an explicit path) and
`session_sha256` (the completed raw session file's SHA256) to the JSON report.
These wrapper fields are excluded from the claim digest, avoiding a circular
session/final hash. Later transcript appends invalidate the wrapper hash; rebind
only after inspecting the completed record, retaining the same reviewed claims.
No signing keys, copied Codex authentication or external identity service is used.

## Trust boundary and claims

The classification is `LOCAL_OPERATOR_OBSERVED_MUTABLE_HOST_RECORDS` and
`AI_ADVISORY_LOCAL_ONLY`. A malicious writer with control of the operator's OS
account can forge transcripts, fixtures and reports. This verifier detects
incomplete, stale or inconsistent records; it does not provide remote attestation
of local execution or defend against that same-account writer. GitHub OIDC
provenance authenticates the ZIP build, not local competence or local transcripts.

The output records `human_review_recorded_by_github=false`,
`remote_native_test_performed=false` and both operator policy exclusions. Actual
local smoke is not exhaustive taxonomy certification or professional qualification.
The 103 open professional designs, evaluator-controlled holdout, live A/B and
Desktop-specific UI paths retain their own evidence and limitations. This policy
neither turns design-only cases into executed tests nor enables global hooks.

`policy_acceptance_passed=true` means this chosen evidence profile passed at the
recorded revision/ZIP. `publication_authorized` remains false because this
read-only tool is not the operator's publication action. Stable version labels
alone never authorize promotion. Preserve the gate report and package acceptance
records with the release so recipients can inspect the exact assurance scope.
