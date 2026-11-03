# Artifact identity and scope checks

The supervisor seals a versioned semantic snapshot of each private checkout:

- SHA-256 of every regular working-tree file, including ignored files;
- filesystem permission bits for those files, so POSIX chmod cannot hide behind `core.filemode=false`;
- the exact Git HEAD/base revision;
- canonical index path, mode, object ID and merge stage;
- SHA-256 of the exact canonical binary diff against HEAD, including mode changes.

Git symlink/gitlink index types and unmerged stages are unsupported and fail
closed. The snapshot does not hash the whole `.git` directory: timestamps,
description, reflogs, index stat caches and other volatile administration are
not the reviewed artifact. The content-only `inventory()` API remains available
for professional path/hash claims; it is insufficient for supervisor acceptance.

`artifact_scope_delta()` evaluates content, filesystem mode and index metadata
per path. A mode-only write is a write: read-only tasks and changes outside
ownership fail, and protected paths remain protected even when explicitly
listed. The executor uses this check in sequential execution, safe read retry,
and parallel read-only execution. The workflow also verifies that supervisor
checks did not mutate the semantic snapshot.

A verified workflow or integration inspection recomputes this snapshot. Changed
bytes, modes, staged metadata, type, base or diff invalidate prior production
and review evidence. The same canonical diff function supplies the reviewed,
confirmed and applied patches. Exact patch SHA-256 confirmation, trusted scoped
grants, locking, applicability checks and post-apply comparison remain required.

Existing runs produced with a content-only artifact seal are deliberately not
upgraded by relabeling their evidence. They require a fresh reviewed run under
the stronger seal. Existing published native qualification results retain their
original revision and scope; a hash format change cannot certify them anew.

These are local drift checks, not authenticated identity, a malicious-writer
boundary or OS containment. Snapshot reads are not an atomic filesystem
transaction. They neither authorize execution nor verify that candidate code
is safe. Runtime permissions and explicit external authorization still apply.
Git patches transfer Git file modes (regular/executable), not every filesystem
permission bit; sealing additional permission bits detects drift and does not
promise to replicate ACLs or arbitrary POSIX permissions at integration.

Regression coverage is in `tests/test_artifact_seal.py` and
`tests/test_guardian_workflow.py`: unchanged positives, index-only chmod, POSIX
chmod (skipped on Windows), mode ownership, unsupported types, staged-only
content drift, cosmetic/volatile metadata stability, and stale patch rejection.

## Historical profile migration regression

`tests/test_audit_installer_migration.py` installs the 39 pinned historical
profile bytes from revision `e476aee7398b60e5c1a086941891262abf55ed0e`
into an isolated fake home, updates the 29 core plus all ten optional profiles,
checks current catalog hashes, and rolls back to byte-exact prior content and
receipts. Separate negative cases preserve edited core/optional profiles and
refuse overwriting. Existing user configuration, policy preamble and an unrelated
custom agent are controls.

The historical fixture is UTF-8 data with per-file SHA-256, not Python code.
The test source image combines those historical profile/policy/version bytes
with current surrounding metadata; only current trusted installer/pack APIs
run. This establishes the profile ownership migration and rollback contract,
not a full historical-runtime compatibility matrix or native Codex loading.
Transaction backup directories are intentionally retained and excluded from
the byte-exact restored-installation comparison. No real global home changes.
