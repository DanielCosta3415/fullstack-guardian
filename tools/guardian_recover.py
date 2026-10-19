#!/usr/bin/env python3
"""Repair an interrupted Guardian installer transaction using its own backups.

Requires explicit --apply; validates every proposed target against the install
scope and refuses to overwrite user-modified files. Never runs downloaded code.
This is recovery of an interrupted operation, NOT installation or deployment.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path
try:
    from .guardian_maintenance import maintenance_locks, owned_target
except ImportError:
    from guardian_maintenance import maintenance_locks, owned_target

BACKUP_ID = re.compile(r"^[0-9a-f]{32}$")


class RecoveryError(ValueError):
    pass


def safe(path: Path) -> Path:
    result = Path(os.path.abspath(path))
    for part in (result, *result.parents):
        if part.is_symlink() or (part.exists() and getattr(part.lstat(), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
            raise RecoveryError("Unsafe symlink or reparse path")
    return result


def read(path: Path) -> bytes | None:
    path = safe(path)
    if not path.exists():
        return None
    if not path.is_file():
        raise RecoveryError("Non-file source/target")
    return path.read_bytes()


def sha(data: bytes | None) -> str | None:
    return hashlib.sha256(data).hexdigest() if data is not None else None


def within(target: Path, root: Path) -> bool:
    return target == root or root in target.parents


def inspect(home: Path, backup_id: str, mode: str, *, skills_root: Path | None = None) -> dict:
    home = safe(home)
    if mode not in ("user", "project") or not BACKUP_ID.fullmatch(backup_id):
        raise RecoveryError("Invalid recovery scope or backup id")
    backup = safe(home / "guardian-backups" / backup_id)
    raw = read(backup / "transaction.json")
    if not raw:
        raise RecoveryError("Transaction manifest absent")
    try:
        manifest = json.loads(raw)
    except ValueError as exc:
        raise RecoveryError("Corrupt transaction manifest") from exc
    changes = manifest.get("changes") if isinstance(manifest, dict) else None
    if not isinstance(changes, list) or not changes or len(changes) > 20000:
        raise RecoveryError("Transaction has invalid file list")
    receipt_path = safe(home / "guardian-install.json")
    before_receipt = read(backup / "receipt-before.json")
    current_receipt = read(receipt_path)
    if current_receipt != before_receipt:
        raise RecoveryError("Ownership receipt no longer matches original transaction; refuse rollback")
    source = Path(__file__).resolve().parent.parent
    runtime = safe(home / "guardian-system" if mode == "user" else home.parent / ".guardian")
    skills = safe(skills_root or (home.parent / ".agents" / "skills"))
    instruction = safe(home / "AGENTS.md" if mode == "user" else home.parent / "AGENTS.md")
    identity = {"codex": str(home), "skills": str(skills), "runtime": str(runtime), "instruction": str(instruction)}
    if "identity" in manifest and (manifest.get("identity") != identity or manifest.get("mode") != mode):
        raise RecoveryError("Transaction installation identity does not match explicit recovery scope")
    agent_names = {p.name for p in (source / "global" / "agents").glob("*.toml")}
    skill_names = {p.parent.name for p in (source / "global" / "skills").glob("*/SKILL.md")}
    def owned(target):
        return owned_target(target, codex=home, skills=skills, runtime=runtime, instruction=instruction,
                            agent_names=agent_names, skill_names=skill_names)
    if before_receipt is not None:
        try:
            prior = json.loads(before_receipt)
            if not isinstance(prior, dict) or prior.get("schema") != 1 or prior.get("mode") != mode or prior.get("identity") != identity or not isinstance(prior.get("files"), list):
                raise RecoveryError("Invalid original ownership receipt")
            paths = []
            for entry in prior["files"]:
                if not isinstance(entry, dict) or not isinstance(entry.get("path"), str) or not owned(safe(entry["path"])) or not isinstance(entry.get("hash"), str) or not re.fullmatch("[a-f0-9]{64}", entry["hash"]):
                    raise RecoveryError("Unsafe original receipt contents")
                paths.append(str(safe(entry["path"])))
            if not paths or len(paths) != len(set(paths)):
                raise RecoveryError("Invalid original ownership file list")
        except (ValueError, TypeError) as exc:
            raise RecoveryError("Invalid original ownership receipt") from exc
    planned = []
    for index, entry in enumerate(changes):
        if not isinstance(entry, dict) or set(entry) not in ({"path", "before", "after"}, {"path", "before", "after", "before_sha256"}):
            raise RecoveryError("Invalid transaction entry")
        target = safe(Path(entry["path"]))
        if not owned(target):
            raise RecoveryError("Transaction attempts to change path outside owner scope")
        if within(target, safe(home / "guardian-backups")) or target == safe(home / "guardian-install.json"):
            raise RecoveryError("Transaction attempts to modify recovery evidence or ownership receipt")
        filename = entry["before"]
        if filename is not None and filename != str(index) + ".bin":
            raise RecoveryError("Backup file index invalid")
        old = read(backup / filename) if filename else None
        if filename and old is None:
            raise RecoveryError("Missing backup contents")
        if manifest.get("schema_version") == 2 and "before_sha256" not in entry:
            raise RecoveryError("Missing backup digest")
        if "before_sha256" in entry and entry["before_sha256"] != sha(old):
            raise RecoveryError("Backup digest mismatch")
        after = entry["after"]
        if after is not None and (not isinstance(after, str) or not re.fullmatch(r"[a-f0-9]{64}", after)):
            raise RecoveryError("Invalid after digest")
        current = read(target)
        before_digest = sha(old)
        current_digest = sha(current)
        if current_digest not in (before_digest, after):
            raise RecoveryError("User-modified file detected; refuse to overwrite")
        planned.append({"path": str(target), "before_hash": before_digest,
                        "current_hash": current_digest, "after_hash": after,
                        "requires_restore": current_digest != before_digest,
                        "before_file": filename})
    targets = [e["path"] for e in planned]
    if len(set(targets)) != len(targets):
        raise RecoveryError("Duplicate recovery targets")
    return {"backup": str(backup), "home": str(home), "mode": mode,
            "backup_id": backup_id, "entries": planned, "receipt_before": sha(before_receipt),
            "restore_count": sum(e["requires_restore"] for e in planned),
            "applied": False}


def _atomic(path: Path, content: bytes) -> None:
    path = safe(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".guardian-recovery-", delete=False) as stream:
            name = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        safe(path)
        os.replace(name, path)
    finally:
        if name is not None:
            name.unlink(missing_ok=True)


def restore(home: Path, backup_id: str, mode: str, *, apply: bool = False, skills_root: Path | None = None) -> dict:
    if apply:
        try:
            root = safe(home)
            if mode not in ("user", "project"):
                raise RecoveryError("Invalid recovery mode")
            instruction = root if mode == "user" else root.parent
            skills = skills_root or (root.parent / ".agents" / "skills")
            # c/project policy-parent also covers its nested runtime; do not
            # materialize an empty runtime just to acquire a redundant lock.
            with maintenance_locks((root, skills, instruction), "recover"):
                return _restore(home, backup_id, mode, apply=True, skills_root=skills_root)
        except ValueError as exc:
            raise RecoveryError(str(exc)) from exc
    return _restore(home, backup_id, mode, skills_root=skills_root)


def _restore(home, backup_id, mode, *, apply=False, skills_root=None):
    plan = inspect(home, backup_id, mode, skills_root=skills_root)
    public = {"dry_run": not apply, "files_examined": len(plan["entries"]),
              "files_to_restore": plan["restore_count"], "receipt_verified": True}
    if not apply:
        return public
    root = safe(home)
    try:
        current = inspect(home, backup_id, mode, skills_root=skills_root)
        if current != plan:
            raise RecoveryError("Recovery state changed; review again")
        for entry in plan["entries"]:
            if not entry["requires_restore"]:
                continue
            target = safe(Path(entry["path"]))
            filename = entry["before_file"]
            if filename is None:
                target.unlink(missing_ok=True)
            else:
                original = read(safe(Path(plan["backup"]) / filename))
                if original is None or sha(original) != entry["before_hash"]:
                    raise RecoveryError("Backup file changed during recovery")
                _atomic(target, original)
        after = inspect(home, backup_id, mode, skills_root=skills_root)
        if after["restore_count"]:
            raise RecoveryError("Incomplete recovery; inspect all files")
    finally:
        pass  # Shared maintenance lock is owned by restore().
    return {"dry_run": False, "files_examined": len(plan["entries"]),
            "files_restored": plan["restore_count"], "restored_to_pre_transaction": True}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--home", required=True, type=Path, help="Exact Codex home with guardian-backups/")
    ap.add_argument("--backup-id", required=True)
    ap.add_argument("--skills-root", type=Path, help="Explicit skills directory for nonstandard CODEX_HOME layouts")
    ap.add_argument("--mode", required=True, choices=("user", "project"))
    ap.add_argument("--apply", action="store_true", help="Explicitly restore files; default is dry-run")
    args = ap.parse_args()
    try:
        result = restore(args.home, args.backup_id, args.mode, apply=args.apply, skills_root=args.skills_root)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
