#!/usr/bin/env python3
"""Read-only specialist registry for Guardian core and optional packs.

This module never installs agents, loads credentials, or executes third-party code.
Agent packs remain opt-in. It uses only the Python standard library.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
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
    # PurePath.absolute() does not normalize '..'. Reject traversal before
    # checking containment, including when a core manifest is untrusted.
    if ".." in path.parts:
        raise RegistryError("Traversal path component forbidden")
    anchor = Path(os.path.normpath(os.path.abspath(root)))
    target = Path(os.path.normpath(os.path.abspath(path)))
    try:
        parts = target.relative_to(anchor).parts
    except ValueError as exc:
        raise RegistryError("Path escapes registry root") from exc

    def unsafe(candidate: Path) -> bool:
        if not candidate.exists() and not candidate.is_symlink():
            return False
        attrs = getattr(candidate.lstat(), "st_file_attributes", 0)
        return candidate.is_symlink() or bool(attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))

    # Inspect the *actual* path components, including Windows junctions.
    current = anchor
    if any(unsafe(item) for item in (current, *current.parents)):
        raise RegistryError("Registry root/ancestor is a symlink/reparse point")
    for part in parts:
        current = current / part
        if unsafe(current):
            raise RegistryError(f"Symlink/reparse point forbidden: {current.name}")
    return target


def discover(root: Path = ROOT, *, policy: dict | None = None, codex_home: Path | None = None) -> dict:
    """Validate catalog and return metadata without changing Codex configuration."""
    policy = {} if policy is None else policy
    if not isinstance(policy, dict) or set(policy) - {"allow_model_overrides", "allowed_models"}:
        raise RegistryError("Invalid registry policy")
    if type(policy.get("allow_model_overrides", False)) is not bool or not isinstance(policy.get("allowed_models", []), list) or any(not isinstance(x, str) or not x for x in policy.get("allowed_models", [])):
        raise RegistryError("Invalid model opt-in policy")
    root = Path(root).absolute()
    def metadata(path, profile, optional):
        diagnostics = []
        model = profile.get("model")
        if model is not None:
            if not isinstance(model, str) or not policy.get("allow_model_overrides") or model not in policy.get("allowed_models", []):
                raise RegistryError("Model override requires explicit allowlisted opt-in")
            diagnostics.append("Explicit model override; availability and cost are not verified")
        if any(k in profile for k in ("sandbox_mode", "mcp_servers", "tools", "skills", "permissions")):
            diagnostics.append("Profile permission/tool/MCP fields are declarations; effective restrictions and inherited MCP require runtime verification")
        supported = {"name", "description", "developer_instructions", "model", "model_reasoning_effort", "nickname_candidates"}
        unknown = sorted(set(profile) - supported)
        if unknown:
            diagnostics.append("Fields require explicit compatibility verification: " + ", ".join(unknown))
        state = "available_optional" if optional else "available_core"
        installed = False
        if codex_home is not None:
            target = _contained(Path(codex_home) / "agents" / path.name, Path(codex_home))
            if target.is_file():
                installed = target.read_bytes() == path.read_bytes()
                state = "installed_not_loaded" if installed else "installed_drifted"
        return {"file": str(path.relative_to(root)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "state": state, "installed": installed, "eligible": not optional or installed,
                "loaded": None, "native_verified": False, "model_policy": "explicit_opt_in" if model else "inherit",
                "diagnostics": diagnostics}

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
        if not isinstance(file, str) or not re.fullmatch(r"global/agents/[a-z][a-z0-9_-]*\.toml", file):
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
        result["core"].append({"id": aid, "name": name, "group": agent.get("group"), **metadata(path, parsed, False)})

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
                names.add(name)
                available.append({"name": name, **metadata(path, profile, True)})
            result["packs"].append({"name": folder.name, "description": manifest.get("description", ""), "agents": available, "optional": True,
                "manifest_sha256": hashlib.sha256((folder / "manifest.json").read_bytes()).hexdigest(),
                "provenance": {"origin": "local_reviewed_catalog", "source": str(folder.relative_to(root)),
                    "declared": manifest.get("provenance"), "license": manifest.get("license", "UNSPECIFIED"),
                    "authenticated": False}})

    result["available_total"] = len(names)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate or inspect Guardian specialist catalog (read-only)")
    parser.add_argument("command", choices=["list", "validate"])
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--codex-home", type=Path, help="Inspect installed bytes; does not claim agents loaded")
    parser.add_argument("--policy", type=Path, help="Explicit model opt-in JSON policy")
    args = parser.parse_args(argv)
    try:
        payload = discover(args.root, policy=_json_file(args.policy) if args.policy else None, codex_home=args.codex_home)
    except RegistryError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2
    if args.command == "validate":
        payload = {"ok": True, "core": len(payload["core"]), "packs": len(payload["packs"]), "available_total": payload["available_total"]}
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
