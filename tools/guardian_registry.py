#!/usr/bin/env python3
"""Read-only specialist registry for Guardian core and optional packs.

This module never installs agents, loads credentials, or executes third-party code.
Agent packs remain opt-in. It uses only the Python standard library.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")
CORE_ID = re.compile(r"^[AGS][0-9]{2}$")


class RegistryError(ValueError):
    pass


def _json_file(path: Path) -> dict:
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise RegistryError(f"Cannot parse manifest {path.name}: {exc}") from exc
    if not isinstance(result, dict):
        raise RegistryError(f"Expected object: {path.name}")
    return result


def _contained(path: Path, root: Path) -> Path:
    """Reject symlinks and paths outside the declared package directory."""
    anchor = root.absolute()
    target = path.absolute()
    try:
        parts = target.relative_to(anchor).parts
    except ValueError as exc:
        raise RegistryError("Path escapes registry root") from exc
    current = anchor
    if current.is_symlink():
        raise RegistryError("Registry root is a symlink")
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise RegistryError(f"Symlink forbidden: {current.name}")
    return target


def discover(root: Path = ROOT) -> dict:
    """Validate catalog and return metadata without changing Codex configuration."""
    root = Path(root).absolute()
    core = _json_file(_contained(root / "core" / "agents.json", root))
    entries = core.get("agents")
    if not isinstance(entries, list) or not entries:
        raise RegistryError("Core registry must contain agents")
    names: set[str] = set()
    ids: set[str] = set()
    result = {"core": [], "packs": [], "available_total": 0, "installed": False}
    for agent in entries:
        if not isinstance(agent, dict):
            raise RegistryError("Invalid core agent entry")
        name, aid = agent.get("name"), agent.get("id")
        if not isinstance(name, str) or not IDENTIFIER.fullmatch(name) or not isinstance(aid, str) or not CORE_ID.fullmatch(aid):
            raise RegistryError("Invalid core agent identity")
        if name in names or aid in ids:
            raise RegistryError(f"Duplicate agent: {name}")
        file = agent.get("file")
        if not isinstance(file, str) or not file.startswith("global/agents/"):
            raise RegistryError(f"Invalid agent file: {name}")
        path = _contained(root / file, root)
        try:
            parsed = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RegistryError(f"Invalid profile {name}: {exc}") from exc
        if parsed.get("name") != name or not parsed.get("developer_instructions"):
            raise RegistryError(f"Invalid profile contents: {name}")
        names.add(name)
        ids.add(aid)
        result["core"].append({"id": aid, "name": name, "group": agent.get("group")})

    packs_dir = root / "packs"
    if packs_dir.exists():
        _contained(packs_dir, root)
        for folder in sorted(packs_dir.iterdir()):
            if not folder.is_dir():
                raise RegistryError("Pack entries must be directories")
            _contained(folder, packs_dir)
            if not IDENTIFIER.fullmatch(folder.name):
                raise RegistryError("Invalid pack directory name")
            manifest = _json_file(_contained(folder / "manifest.json", folder))
            if manifest.get("schema_version") != 1 or manifest.get("name") != folder.name:
                raise RegistryError(f"Unsupported pack manifest: {folder.name}")
            profiles = manifest.get("agents")
            if not isinstance(profiles, list) or not profiles:
                raise RegistryError(f"Empty pack: {folder.name}")
            available = []
            for entry in profiles:
                if not isinstance(entry, dict):
                    raise RegistryError("Invalid pack entry")
                name, relative = entry.get("name"), entry.get("file")
                if not isinstance(name, str) or not IDENTIFIER.fullmatch(name) or name in names:
                    raise RegistryError(f"Duplicate or invalid specialist: {name}")
                if not isinstance(relative, str) or not re.fullmatch(r"agents/[a-z][a-z0-9_-]*\.toml", relative):
                    raise RegistryError(f"Invalid pack agent file: {name}")
                path = _contained(folder / relative, folder)
                try:
                    profile = tomllib.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError) as exc:
                    raise RegistryError(f"Invalid specialist {name}: {exc}") from exc
                if profile.get("name") != name or not profile.get("developer_instructions"):
                    raise RegistryError(f"Invalid specialist contents: {name}")
                if "model" in profile or "sandbox_mode" in profile:
                    raise RegistryError(f"Pack must inherit model and sandbox: {name}")
                names.add(name)
                available.append({"name": name, "file": str(path.relative_to(root))})
            result["packs"].append({"name": folder.name, "description": manifest.get("description", ""), "agents": available, "optional": True})

    result["available_total"] = len(names)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate or inspect Guardian specialist catalog (read-only)")
    parser.add_argument("command", choices=["list", "validate"])
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        payload = discover(args.root)
    except RegistryError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2
    if args.command == "validate":
        payload = {"ok": True, "core": len(payload["core"]), "packs": len(payload["packs"]), "available_total": payload["available_total"]}
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
