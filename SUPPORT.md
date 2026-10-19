# Compatibility and support

Guardian is a local Python 3.11+ toolchain. VERSION is the source of package identity. Development versions are not stable releases.

## Support contract

- Static core, registry, planning, pack lifecycle and installer target Windows, Linux and macOS on Python 3.11–3.13. Actual results are tied to a commit in CI; a target is not a claim that every native client was exercised.
- Native delegation requires authenticated local Codex, supported custom agents/collaboration and readable version-compatible evidence. It consumes quota only after explicit opt-in.
- CLI execution is a separate backend. File ownership postconditions do not turn a Git worktree into an OS sandbox. Unknown permissions or unsupported strict enforcement fail closed.
- Grading untrusted generated code requires the declared verified isolation backend. Missing backend means BLOCKED, never host-Python fallback.
- Models, effort, providers, accounts and permissions are inherited unless a compatible explicit user policy authorizes a change. Unknown availability/quota is unknown.
- Project instructions, organization requirements and user authorization remain authoritative. No production deployment, credentials changes or external communication is authorized by a profile.

## Maintenance

Pin reference commits and compare diffs before updating. New source hashes invalidate prior native evidence and compatibility claims. Regenerate the contract catalog only after reviewing profile changes. Simulate install/update/uninstall/rollback before applying; do not delete conflicts or stale maintenance locks blindly.

Report failures with VERSION, OS, Python/Codex version, command exit code and sanitized evidence. Do not share credentials, raw session logs or personal paths. Security reports should use a private channel to repository maintainers when available; do not post secrets in issues.

Stable release requires the exact revision's tests, independent G01 review, applicable G02 decision, valid provenance and native acceptance evidence. Unverified environments and skips remain explicitly listed in the release record. Breaking contracts require migration notes and a new version; support may be deprecated only with a documented replacement or limitation.
