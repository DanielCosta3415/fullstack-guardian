# Professional review intake — data-only P0

`tools/guardian_professional_review.py` prepares and inspects review evidence for the 103 public `independent_sme` designs. It never runs models, candidate code, shell commands or graders. It does not install dependencies, access credentials or promote release readiness. Standalone defaults resolve relative to the installed tools directory.

The intake is a preparatory mechanism. The 103 scenarios remain designs requiring real task fixtures, execution evidence and appropriate review. An exported empty template is not an executed evaluation. All distributed cases remain public development data.

## Commands

```powershell
python tools/guardian_professional_review.py preview
python tools/guardian_professional_review.py validate --manifest submissions.json --artifact-root evidence
python tools/guardian_professional_review.py review-export --out NEW_DIRECTORY
python tools/guardian_professional_review.py review-export --manifest submissions.json --artifact-root evidence --out NEW_DIRECTORY
python tools/guardian_professional_review.py review-ingest --bundle NEW_DIRECTORY --review reviewed.json
```

`review-export` accepts only a new destination whose parent exists. It exports all 103 cases using an explicit public-field allowlist; no `oracle`, acceptance oracle or future private field is copied. The index includes public scenarios, required artifact names, numbered public criteria and hashes. Optional evidence bytes are copied into content-addressed `.bin` files. The index removes candidate author/model and original artifact paths; submission hashes bind the operator's original manifest. Artifact contents and scenario wording may still identify their author. **This is metadata blinding, not guaranteed anonymity or isolation.** Candidate bytes remain untrusted, potentially sensitive material: review data ownership and disclosure before export. The tool does not redact source artifacts or upload anything.

Without submissions, all candidate evidence and template criteria are explicitly NOT_VERIFIED/unknown. The tool does not generate professional outputs or fill in observations. Example submission manifest (replace the hash with the actual artifact byte digest):

```json
{
  "schema_version": 1,
  "submissions": [{
    "case_id": "S08:professional:1",
    "author_id": "operator-assigned-candidate-id",
    "revision": "operator-supplied-source-revision",
    "model": "observed-model-identifier",
    "artifacts": [{"path": "professional-result.json", "sha256": "64-lowercase-hex-characters"}]
  }]
}
```

Submission metadata is not authenticated execution evidence. Supply the professional result and all relevant independent evidence as referenced files; this module hashes bytes but does not parse or validate the professional-result protocol, execute checks, confirm source revision or corroborate model identity. Use the existing supervisor/professional validator for those separate checks. Paths must be normalized relative paths, with no traversal, drive/UNC forms, backslashes, Windows reserved names, aliases or duplicate case-insensitive paths. Files are bounded at 4 MB each and bundles at 32 MB/1024 unique artifact blobs. JSON rejects duplicate keys and nonfinite constants. Existing symlinks and Windows reparse points are rejected throughout path ancestors. These checks do not establish OS isolation against a concurrently hostile file-system writer; use a protected staging directory with appropriate OS permissions. Export can leave a partial new directory on I/O interruption; inspect it and choose a new destination, never overwrite it.

## Review protocol

Copy `review-template.json` outside the immutable bundle and fill its reviewer identifier, kind, criteria and rationale. Every case and every numbered criterion must appear exactly once, including unreviewed criteria as `unknown`. Allowed judgments are `supported`, `contradicted`, `unknown`; a non-unknown judgment requires hash references belonging to that exact case. The tool requires complete accounting, not positive conclusions. It revalidates corpus, public criteria and every referenced artifact before ingesting. The review binds to the canonical index digest. Renaming cases, missing criteria, extra approval flags and evidence from another case fail closed.

Allowed classes:

- `AI_ADVISORY`: AI-produced suggestions; never human expert certification.
- `EXTERNAL_REVIEW_UNAUTHENTICATED`: external review text whose identity and competence have not been authenticated by this tool.

No authenticated SME backend exists here. A JSON declaration such as `human_approved`, a fabricated signature field or `AUTHENTICATED_SME` is rejected. SHA256 binds supplied bytes; it cannot authenticate a reviewer or prove independence, competence, truth, freshness or execution. Both allowed review classes always report `qualified_cases: 0`, `reviewer_identity_authenticated: false`, `competence_verified: false` and `qualification: NOT_VERIFIED`. A matching positive opinion is never converted to SME PASS.

The returned report includes per-case candidate evidence state, reviewer class, counts of supported/contradicted/unknown criteria and bilateral criterion rows. Candidate claims remain unverified; reviewer judgments are labeled assertions over hash-bound artifacts. Unknowns remain explicit. Raw review rationale is retained in the supplied review file rather than unnecessarily reproduced in the report. Do not publish private artifacts or raw reviews without separate authorization.

## External gates still required

A private holdout requires independently authored cases and evaluator secrets outside the candidate's OS/account access. Hiding oracle fields in this export is insufficient. The report always sets `private_holdout_validated: false` and exported metadata records `BLOCKED_EXTERNAL_ISOLATION_REQUIRED`. A real authorized reviewer identity/competence policy, independent execution receipts, representative task fixtures, calibrated rubric and authenticated approval remain external requirements. No secret holdout or SME certificate is invented to clear those gates. This P0 does not implement private fixtures, trust-policy verification, cryptographic reviewer authentication or execution of the 103 professional tasks.

## Verification

`python -B -m unittest tests.test_professional_review -v` exercises oracle exclusion, explicit unknowns, forged approval rejection, both review classes, case/criterion completeness, hash drift, malformed JSON, output no-overwrite, path aliases, bounded files, simulated Windows reparse attributes and metadata blinding. Tests use synthetic bytes without invoking a model or a specialist. The reparse test is a deterministic attribute simulation, not a privileged junction creation test.
