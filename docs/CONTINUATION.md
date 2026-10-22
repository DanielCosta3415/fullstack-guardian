# Durable continuation checkpoints

Guardian can record a bounded local checkpoint after each meaningful milestone and
when the runtime reports an exhausted usage window. The owner resumes work by
sending **Continue** after access returns. This tool does not watch the account,
estimate quota from tokens, schedule a wakeup, obtain credentials, change models,
or guarantee that code will run after a hard quota interruption. Save before the
limit: information never written to disk cannot be recovered by this tool.

## Explicit local records

`tools/guardian_checkpoint.py` uses only Python's standard library and Git. The
project must be the Git working-tree root; nested project roots are rejected to
prevent misbinding Git's repository-relative paths. It
reads the current project and writes only an explicitly supplied
`PROJECT/.guardian-state/NAME.json`. It never modifies global instructions or
source files. Keep `.guardian-state/` out of commits using the project's existing
ignore policy; the tool does not edit `.gitignore` automatically.

A plan is supplied explicitly, rather than extracted from transcripts:

```json
{
  "tasks": [
    {"id": "adapter_backend", "status": "in_progress"},
    {"id": "adapter_review", "status": "pending"}
  ],
  "next_actions": ["Run the bounded backend adapter negative tests"]
}
```

Task IDs contain only letters, digits, underscores, and hyphens. Status is one of
`pending`, `in_progress`, `validated`, `blocked`, or `not_verified`. These are
operator assertions, not proof of quality. Store only non-sensitive descriptions;
do not place prompts, transcripts, secrets, account data, or authentication in a
plan. An explicit evidence path is recorded with its SHA256; its content is not
copied. Evidence must be a regular bounded file inside the project. Parent
traversal, links/reparse points, global credential paths, and common credential
filenames are rejected. This denylist is additional hygiene, not a secret scanner.

The record contains the Git revision, checksums of the porcelain status output
and changed source content, an index-metadata checksum, a dirty flag, evidence hashes, next actions, a UTC
timestamp, and a monotonically increasing sequence. Source filenames, raw source,
diffs, remotes, environment variables, and CLI errors are not stored. A bounded
Git status inventory enumerates modified tracked files, rename source/destination
paths, and individual untracked files inside nested directories. The aggregate
content binding detects edits even when a file remains `M` or `??`.
Git index blob identifiers also bind staged changes when both the status flags
and working copy remain identical; staged source contents are not extracted.
Only permitted
regular source files are read, up to 2,048 changed paths and 32,000,000 aggregate
bytes. Exceeding either bound rejects the operation. A sensitive, symlink/reparse,
or nonregular changed path is not read and forces `source_inspection_required`,
even if status otherwise appears unchanged. This conservative guard cannot be
cleared by merely rebinding the same unsafe workspace. Known credential paths,
`.env.*`, common private-key names, and key-container suffixes are rejected; this
is not a content secret scanner. Explicit evidence still binds important reports
or unchanged files. The state directory is excluded so recording the checkpoint
does not itself cause drift.

## Commands

Examples use placeholders resolved by the primary agent to absolute paths:

```text
python tools/guardian_checkpoint.py create --project PROJECT --out PROJECT/.guardian-state/continuation.json --plan PLAN.json --evidence reports/checks.json
python tools/guardian_checkpoint.py update --project PROJECT --out PROJECT/.guardian-state/continuation.json --plan PLAN.json --signal milestone --evidence reports/checks.json
python tools/guardian_checkpoint.py update --project PROJECT --out PROJECT/.guardian-state/continuation.json --plan PLAN.json --signal quota_5h
python tools/guardian_checkpoint.py resume --project PROJECT --out PROJECT/.guardian-state/continuation.json
python tools/guardian_checkpoint.py status --project PROJECT --out PROJECT/.guardian-state/continuation.json
```

`create` requires an absent checkpoint; `update` requires an existing valid one.
Every update replaces the full plan and evidence list. Repeat all evidence that
must remain bound to the current milestone. Allowed signals are `milestone`,
`manual_pause`, `quota_5h`, `quota_weekly`, and `quota_unspecified`. A quota signal
is an explicitly observed runtime condition, not a claim that the tool queried
account telemetry.

`classify-error --project PROJECT --out PROJECT/.guardian-state/continuation.json`
optionally reads at most 16,001 characters from standard input, classifies at
most 16,000, and emits only a bounded signal and `heuristic_only: true`. It never
saves or echoes the input and does not create a checkpoint. This heuristic may
misclassify errors; use an explicit known runtime signal when available. Do not
pass raw logs on the command line or put them into source-controlled files.

All ordinary command output is redacted to counts, drift flags, signal, and
sequence; action descriptions remain only in the local checkpoint. Exit codes:

| Code | Meaning |
| --- | --- |
| 0 | Operation accepted; `status` may still report drift |
| 1 | Invalid input, checksum/schema/path failure, lock conflict, or Git failure |
| 2 | `resume` found revision/status/evidence drift; reinspection is required |

On Continue, the primary agent must inspect `resume`, read the explicitly saved
plan, verify relevant evidence, and continue unfinished tasks. A changed Git
revision blocks update until inspection followed by explicit
`--accept-revision-change`. Rebinding to a new revision does not transfer old test
results to that revision. Missing or changed evidence remains a reason to inspect
and rerun relevant checks. `completion_certified` is always false: the checkpoint
cannot certify completion, deployment readiness, reviewer identity, or a release.

## Persistence and limitations

The JSON envelope uses schema **2**, has a SHA256 checksum, and rejects unknown fields, unsupported
schema versions, duplicate JSON keys, nonfinite numbers, and excessive sizes.
Schema 1 records lack changed-content binding and are deliberately rejected.
Preserve an old record as an explicitly archived local file, inspect its saved
plan/evidence independently, then create a new schema 2 checkpoint. There is no
silent migration or transfer of validation claims.
Atomic replacement uses a flushed, fsynced temporary file in the same directory.
An exclusive lock prevents cooperative concurrent writers. Interrupted replacement
preserves the last completed record. A process killed before cleanup can leave a
lock or temporary file: inspect running writers before removing that project's
stale lock manually. The tool never steals locks or automatically deletes another
writer's files. Atomic visibility does not promise survival of every OS/power
failure. The directory must be controlled by the local operator; this is not a
defense against a hostile process racing filesystem replacements.

Each replacement retains the previous record's checksum and advances sequence.
This is predecessor linkage, not an append-only audit log, signature, proof of
identity, or tamper-resistant history. Operators can alter and rehash local data.

`--release-policy` records an explicit local choice: a new checkpoint defaults to `unspecified`;
`strict` records remote testing and human review as required;
`operator-autonomous` records that this operator does not require those two steps.
Use the latter only when the owner has explicitly made that choice. The chosen
policy is inherited when an update omits the flag; changing it requires an explicit
flag. It is never a universal policy for other projects or
installations. This metadata does not change any release gate by itself and cannot
mark an unperformed test as passed. Sandbox permissions
still apply; no permission bypass, credential copying, quota-evading model switch,
or automatic wakeup is authorized by a checkpoint. Existing user settings remain
outside this tool's write scope.
