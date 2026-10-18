#!/usr/bin/env python3
"""Explicitly reviewed integration of a completed Guardian worktree.

Safe by default: inspect only. --apply requires a matching SHA-256 confirmation.
No commits, pushes, deployments or automatic model-based approvals are performed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    from .guardian_executor import _load, _git, safe, ExecutionError, atomic_json
except ImportError:
    from guardian_executor import _load, _git, safe, ExecutionError, atomic_json

HASH = re.compile(r"^[0-9a-f]{64}$")
PROTECTED = re.compile(
    r"(?i)(^|/)(?:\.env(?:\..*)?|AGENTS\.md|config\.toml|id_rsa|secrets?\.(?:json|ya?ml)|[^/]+\.(?:pem|key|pfx))$"
)


class IntegrationError(ValueError):
    pass


def _command(repo: Path, *args: str, data: bytes | None = None, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(["git", "-C", str(repo), *args], input=data,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=60, check=False)
    if check and proc.returncode != 0:
        raise IntegrationError("Git command failed: " + " ".join(args[:2]))
    return proc


def inspect(home: Path) -> tuple[dict, bytes]:
    """Check trust boundary, reviewed state, patch and target applicability."""
    home = safe(home)
    state, plan = _load(home)
    if state.get("overall") != "completed" or state.get("mode") not in ("build", "remediate"):
        raise IntegrationError("Only completed build/remediation runs may be integrated")
    if plan.get("human_authorization_required") or plan.get("risk") in ("high", "critical"):
        raise IntegrationError("High-risk or approval-boundary changes require separate manual integration")
    if any(
        item.get("state") != "completed"
        or item.get("exit_code") != 0
        or item.get("completed_event") is not True
        for item in state["tasks"].values()
    ):
        raise IntegrationError("Execution history does not confirm completed CLI turns")
    root = safe(Path(state["project"]))
    worktree = safe(home / "worktree")
    if not worktree.is_dir() or root == worktree or root in worktree.parents:
        raise IntegrationError("Missing or unsafe isolated worktree")
    if _git(root, "rev-parse", "HEAD") != state["base_commit"]:
        raise IntegrationError("Base revision changed")
    if _git(worktree, "rev-parse", "HEAD") != state["base_commit"]:
        raise IntegrationError("Worktree revision changed")
    if _git(root, "status", "--porcelain", "--untracked-files=all"):
        raise IntegrationError("Original repository is no longer clean")
    untracked = _command(worktree, "ls-files", "--others", "--exclude-standard", "-z").stdout
    if untracked:
        raise IntegrationError("Untracked worktree files require manual inspection/integration")
    paths_raw = _command(worktree, "diff", "--name-only", "-z", "HEAD").stdout
    names = [p.decode("utf-8", "surrogateescape") for p in paths_raw.split(b"\0") if p]
    if not names or len(names) > 500:
        raise IntegrationError("No tracked changes or too many changed paths")
    for name in names:
        p = Path(name)
        if p.is_absolute() or ".." in p.parts or PROTECTED.search(name.replace("\\", "/")):
            raise IntegrationError("Protected or unsafe changed path; manual integration required")
        if root not in safe(root / p).parents or worktree not in safe(worktree / p).parents:
            raise IntegrationError("Changed path escapes expected roots")
    _command(worktree, "diff", "--check", "HEAD")
    patch = _command(worktree, "diff", "--binary", "HEAD").stdout
    if not patch or len(patch) > 5_000_000:
        raise IntegrationError("Patch is empty or exceeds 5 MB")
    _command(root, "apply", "--check", "--binary", "-", data=patch)
    digest = hashlib.sha256(patch).hexdigest()
    return ({
        "dry_run": True, "source": str(root), "base_revision": state["base_commit"],
        "files_changed": len(names), "paths": names, "patch_sha256": digest,
        "patch_bytes": len(patch), "git_apply_check": True, "applied": False,
        "risk": plan["risk"], "tests_verified_independently": False,
        "native_subagents_verified": state.get("native_subagents_verified", False),
        "manual_approval_required": True,
        "notice": "Exact patch reviewed? No tests are verified by this command. Human must inspect diff, run tests and explicitly approve apply.",
    }, patch)


def integrate(home: Path, *, apply: bool = False, confirm_sha256: str | None = None) -> dict:
    report, patch = inspect(home)
    if not apply:
        return report
    if not isinstance(confirm_sha256, str) or not HASH.fullmatch(confirm_sha256) or confirm_sha256 != report["patch_sha256"]:
        raise IntegrationError("Explicit SHA-256 confirmation does not match reviewed patch")
    home = safe(home)
    target = safe(Path(report["source"]))
    lock = safe(home / ".guardian-integration.lock")
    try:
        fd = __import__("os").open(lock, __import__("os").O_CREAT | __import__("os").O_EXCL | __import__("os").O_WRONLY, 0o600)
        __import__("os").close(fd)
    except FileExistsError as exc:
        raise IntegrationError("Integration already running; inspect lock before retry") from exc
    try:
        # Re-read under lock: no stale review or altered source / worktree allowed.
        again, signed_patch = inspect(home)
        if again["patch_sha256"] != confirm_sha256 or signed_patch != patch:
            raise IntegrationError("Reviewed changes drifted before integration")
        atomic_json(home / "integration-intent.json", {
            "schema_version": 1, "patch_sha256": confirm_sha256,
            "base_revision": report["base_revision"], "state": "apply_pending",
        })
        _command(target, "apply", "--binary", "-", data=patch)
        # Git apply does not commit. Ensure output matches the approved patch.
        actual = _command(target, "diff", "--binary", "HEAD").stdout
        if actual != patch:
            raise IntegrationError("Applied patch differs from approved patch; stop and inspect manually")
        atomic_json(home / "integration-result.json", {
            "schema_version": 1, "patch_sha256": confirm_sha256,
            "base_revision": report["base_revision"], "state": "applied_uncommitted",
        })
    finally:
        lock.unlink(missing_ok=True)
    return {
        "applied": True, "files_changed": report["files_changed"],
        "patch_sha256": confirm_sha256, "committed": False, "pushed": False,
        "tested": False, "production_deployed": False,
        "notice": "Patch is now UNCOMMITTED in original repository. Run trusted tests and review before committing.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-sha256", help="Reviewed patch hash; mandatory for --apply")
    args = parser.parse_args()
    try:
        result = integrate(args.home, apply=args.apply, confirm_sha256=args.confirm_sha256)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
