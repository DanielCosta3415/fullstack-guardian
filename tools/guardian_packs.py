#!/usr/bin/env python3
"""Explicit, reversible installation of OPTIONAL Guardian specialist packs.

No network or remote execution; dry-run by default. Does not change models,
permissions, AGENTS.md or config.toml. Install only from a reviewed source.
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
    from .guardian_registry import ROOT, RegistryError, discover
except ImportError:
    from guardian_registry import ROOT, RegistryError, discover

NAME = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")
SHA = re.compile(r"^[a-f0-9]{64}$")


class PackInstallError(ValueError):
    pass


def _safe(path: Path) -> Path:
    p = Path(os.path.abspath(path))
    for item in [p, *p.parents]:
        if item.is_symlink() or (item.exists() and getattr(item.lstat(), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
            raise PackInstallError("Symlink/reparse path forbidden")
    return p


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _read(path: Path) -> bytes | None:
    _safe(path)
    return path.read_bytes() if path.is_file() else None


def _write_atomic(path: Path, data: bytes) -> None:
    _safe(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".guardian-", suffix=".tmp", delete=False) as temp:
            temp_name = temp.name
            temp.write(data)
            temp.flush()
            os.fsync(temp.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def _receipt(path: Path) -> dict:
    raw = _read(path)
    if raw is None:
        return {"schema_version": 1, "packs": {}}
    try:
        value = json.loads(raw)
    except ValueError as exc:
        raise PackInstallError("Malformed pack receipt") from exc
    if not isinstance(value, dict) or value.get("schema_version") != 1 or not isinstance(value.get("packs"), dict):
        raise PackInstallError("Invalid pack receipt schema")
    for name, info in value["packs"].items():
        if not NAME.fullmatch(name) or not isinstance(info, dict) or not isinstance(info.get("files"), dict):
            raise PackInstallError("Invalid pack receipt contents")
        for filename, digest in info["files"].items():
            if not NAME.fullmatch(filename.removesuffix(".toml")) or not filename.endswith(".toml") or not isinstance(digest, str) or not SHA.fullmatch(digest):
                raise PackInstallError("Unsafe pack receipt file entry")
    return value


def operation(pack: str, codex_home: Path, root: Path = ROOT,
              action: str = "install", apply: bool = False) -> dict:
    if not isinstance(pack, str) or not NAME.fullmatch(pack):
        raise PackInstallError("Invalid pack identifier")
    if action not in ("install", "update", "uninstall"):
        raise PackInstallError("Invalid operation")
    home = _safe(codex_home)
    receipt_path = _safe(home / "guardian-packs.json")
    target_dir = _safe(home / "agents")
    catalog = discover(root)
    matches = [p for p in catalog["packs"] if p["name"] == pack]
    if not matches and action != "uninstall":
        raise PackInstallError("Pack not found in verified source")
    desired = {}
    if action != "uninstall":
        for agent in matches[0]["agents"]:
            source = _safe(Path(root) / agent["file"])
            desired[agent["name"] + ".toml"] = source.read_bytes()
    receipt_original = _read(receipt_path)
    receipt = _receipt(receipt_path)
    existing = receipt["packs"].get(pack)
    if action == "install" and existing:
        raise PackInstallError("Already installed; use explicit update")
    if action in ("update", "uninstall") and existing is None:
        raise PackInstallError("Pack not managed here")
    owned = (existing or {}).get("files", {})
    if action == "update" and set(owned) != set(desired):
        raise PackInstallError("Pack membership changed; migrate manually with review")
    changes = {}
    for filename in set(owned) | set(desired):
        dest = _safe(target_dir / filename)
        current = _read(dest)
        if filename in owned:
            if current is None or _digest(current) != owned[filename]:
                raise PackInstallError("Locally modified or missing agent; refuse overwrite/removal")
        elif current is not None:
            raise PackInstallError("Existing unmanaged agent; refuse overwrite")
        new_data = desired.get(filename)
        if current != new_data:
            changes[dest] = new_data
    updated = json.loads(json.dumps(receipt))
    if action == "uninstall":
        del updated["packs"][pack]
    else:
        updated["packs"][pack] = {"files": {f: _digest(d) for f, d in desired.items()}}
    summary = {"pack": pack, "action": action, "apply": apply, "agent_files": len(desired),
               "changes": len(changes), "managed": True,
               "warning": "Agent configuration takes effect only in a new compatible Codex session; permissions and quotas remain unchanged."}
    if not apply:
        return summary
    home.mkdir(parents=True, exist_ok=True)
    lock = _safe(home / ".guardian-packs.lock")
    try:
        handle = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise PackInstallError("Another pack operation is in progress") from exc
    originals = {}
    prior_receipt = receipt_original
    try:
        with os.fdopen(handle, "w") as f:
            f.write("Guardian pack maintenance lock; remove only after investigating interrupted operation.\n")
        # Recheck current state under lock, before changing any file.
        if _read(receipt_path) != receipt_original:
            raise PackInstallError("Concurrent receipt change")
        for dest in changes:
            current = _read(dest)
            if dest.name in owned and (current is None or _digest(current) != owned[dest.name]):
                raise PackInstallError("Concurrent agent modification")
            if dest.name not in owned and current is not None:
                raise PackInstallError("Unmanaged destination created concurrently")
            originals[dest] = current
        for dest, data in changes.items():
            if data is None:
                dest.unlink()
            else:
                _write_atomic(dest, data)
        _write_atomic(receipt_path, (json.dumps(updated, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    except BaseException:
        for dest, original in originals.items():
            try:
                if original is None:
                    dest.unlink(missing_ok=True)
                else:
                    _write_atomic(dest, original)
            except OSError:
                pass  # Preserve the initial failure; operator must inspect.
        if prior_receipt is None:
            receipt_path.unlink(missing_ok=True)
        else:
            _write_atomic(receipt_path, prior_receipt)
        raise
    finally:
        lock.unlink(missing_ok=True)
    return summary


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("operation", choices=("install", "update", "uninstall"))
    p.add_argument("--pack", required=True)
    scope = p.add_mutually_exclusive_group(required=True)
    scope.add_argument("--user", action="store_true")
    scope.add_argument("--project", type=Path)
    p.add_argument("--home", type=Path, help="Explicit Codex home for --user, not its parent directory")
    p.add_argument("--apply", action="store_true", help="Otherwise only simulate")
    args = p.parse_args()
    if args.project and args.home:
        p.error("--home requires --user")
    if args.user:
        home = args.home or Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))
    else:
        if not args.project.is_dir():
            p.error("Project path must exist")
        home = args.project / ".codex"
    try:
        result = operation(args.pack, home, action=args.operation, apply=args.apply)
    except (OSError, ValueError, RegistryError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
