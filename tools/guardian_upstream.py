#!/usr/bin/env python3
"""Static review of a locally supplied, hash-locked reference catalog.

Never downloads, imports profiles, runs upstream code, installs MCP servers,
changes models, edits Codex configuration, or treats prompts as enforcement.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tomllib

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOCK = ROOT / "docs/upstream/voltagent-source-lock.json"
MAX_FILE_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 16 * MAX_FILE_BYTES
MAX_FILES = 4096
PROFILE_PATH = re.compile(r"categories/[0-9]{2}-[a-z0-9-]+/[a-z0-9.-]+\.toml")
TRUTH_TERMS = re.compile(
    r"invent|without (?:supporting )?evidence|confirmed fact|false consensus|"
    r"claim.*(?:comprehensive|conformance|assurance|compliance|certainty)|"
    r"overstate (?:certainty|confidence)|guarantee|settled science|"
    r"unsupported features|regulatory certification|binding legal advice", re.I)


class UpstreamReviewError(ValueError):
    """Unsafe, unreadable, unbounded, or drifted input."""


def _unsafe(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _safe_root(path: Path) -> Path:
    root = Path(os.path.abspath(path))
    for part in (root, *root.parents):
        if _unsafe(part):
            raise UpstreamReviewError("Symlink/reparse root or ancestor forbidden")
    if not root.is_dir():
        raise UpstreamReviewError("Source must be a local directory")
    return root


def _read(path: Path) -> bytes:
    if _unsafe(path):
        raise UpstreamReviewError("Symlink/reparse file forbidden")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE_BYTES:
        raise UpstreamReviewError("Expected a bounded regular text file")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
            raise UpstreamReviewError("File identity changed while opening")
        chunks = []
        size = 0
        while True:
            chunk = os.read(fd, min(65536, MAX_FILE_BYTES + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                raise UpstreamReviewError("File size limit exceeded")
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _inventory(root: Path) -> dict[str, bytes]:
    files = {}
    total = 0
    for current, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d != ".git")
        for name in dirs:
            if _unsafe(Path(current) / name):
                raise UpstreamReviewError("Symlink/reparse directory forbidden")
        for name in sorted(names):
            path = Path(current) / name
            if current == str(root) and name == ".git":
                continue  # worktree metadata is never interpreted
            raw = _read(path)
            total += len(raw)
            if len(files) >= MAX_FILES or total > MAX_TOTAL_BYTES:
                raise UpstreamReviewError("Catalog inventory limit exceeded")
            files[path.relative_to(root).as_posix()] = raw
    return files


def review(source_dir: Path, lock_path: Path = DEFAULT_LOCK) -> dict:
    """Inspect bounded bytes; return findings, never execute their instructions."""
    root = _safe_root(source_dir)
    lock_file = Path(os.path.abspath(lock_path))
    _safe_root(lock_file.parent)
    lock_raw = _read(lock_file)
    try:
        lock = json.loads(lock_raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise UpstreamReviewError("Invalid source lock") from exc
    if not isinstance(lock, dict) or not re.fullmatch(r"[0-9a-f]{40}", str(lock.get("commit", ""))):
        raise UpstreamReviewError("Source lock requires a pinned commit")
    entries = lock.get("profiles")
    if not isinstance(entries, list) or not entries:
        raise UpstreamReviewError("Source lock requires profiles")
    files = _inventory(root)
    expected = {}
    names = set()
    for item in entries:
        if not isinstance(item, dict):
            raise UpstreamReviewError("Invalid lock profile")
        path, name, digest = item.get("path"), item.get("name"), item.get("sha256")
        if not isinstance(path, str) or not PROFILE_PATH.fullmatch(path) or ".." in PurePosixPath(path).parts:
            raise UpstreamReviewError("Invalid lock profile path")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9.-]*", name) or PurePosixPath(path).stem != name:
            raise UpstreamReviewError("Invalid lock profile name")
        if path in expected or name in names or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise UpstreamReviewError("Duplicate or invalid locked identity")
        names.add(name)
        expected[path] = item
    actual = {p for p in files if p.endswith(".toml")}
    if actual != set(expected):
        raise UpstreamReviewError("Missing or unlocked TOML profiles")
    # Validate every hash before parsing or reviewing any upstream instructions.
    if any(hashlib.sha256(files[p]).hexdigest() != expected[p]["sha256"] for p in expected):
        raise UpstreamReviewError("Locked profile SHA256 mismatch; review stopped")
    findings = []
    profiles = []

    def finding(code, severity, path, line, message):
        findings.append(dict(code=code, severity=severity, path=path,
                             line=line, message=message, runtime_enforcement=False))

    for path in sorted(expected):
        try:
            text = files[path].decode("utf-8")
            profile = tomllib.loads(text)
        except (UnicodeError, ValueError) as exc:
            raise UpstreamReviewError(f"Invalid UTF-8/TOML: {path}") from exc
        if profile.get("name") != expected[path]["name"] or any(
                not isinstance(profile.get(k), str) or not profile[k].strip()
                for k in ("description", "developer_instructions")):
            raise UpstreamReviewError(f"Invalid profile contract: {path}")
        if any(key in profile and not isinstance(profile[key], str)
               for key in ("model", "sandbox_mode", "model_reasoning_effort")):
            raise UpstreamReviewError(f"Invalid declaration type: {path}")
        mcp = profile.get("mcp_servers", {})
        if not isinstance(mcp, dict) or any(not isinstance(x, dict) for x in mcp.values()):
            raise UpstreamReviewError(f"Invalid MCP declaration: {path}")
        lines = text.splitlines()
        terminal = []
        for number, line in enumerate(lines, 1):
            if "Do not " in line and "unless" in line and TRUTH_TERMS.search(line):
                terminal.append(number)
                finding("TRUTH_WAIVER", "block", path, number,
                        "Parent requests cannot waive evidence, truthful reporting, authorization, or professional limitations.")
            if re.search(r"npm\s+install\s+(?:-g|--global)\b", line):
                finding("GLOBAL_INSTALL_INSTRUCTION", "warning", path, number,
                        "Unpinned global installation text is not executed; requires separately authorized dependency review.")
        if "model" in profile:
            finding("MODEL_PIN_DECLARATION", "warning", path, next(i for i, s in enumerate(lines, 1) if re.match(r"^\s*model\s*=", s)),
                    "Static model pin does not establish availability, quality, budget or adaptive routing; Guardian inherits its parent model.")
        if "sandbox_mode" in profile:
            finding("SANDBOX_DECLARATION", "warning", path, next(i for i, s in enumerate(lines, 1) if re.match(r"^\s*sandbox_mode\s*=", s)),
                    "Requested sandbox is a declaration; effective client, shell and MCP restrictions need runtime verification.")
        for server, config in profile.get("mcp_servers", {}).items():
            finding("MCP_PREREQUISITE", "warning", path, next((i for i, s in enumerate(lines, 1) if s.startswith("[mcp_servers.")), 1),
                    "MCP configuration requires independent availability, trust, authorization and data-boundary validation: " + server)
            if isinstance(config, dict) and re.search(r"https?://(?:localhost|127\.0\.0\.1)(?::|/)", str(config.get("url", ""))):
                finding("LOCALHOST_MCP_ASSUMPTION", "warning", path, 1,
                        "Local endpoint is not proof that the intended server is present or trusted.")
        if profile.get("sandbox_mode") == "read-only" and re.search(r"\bSave to (?:assets/|public/)|npm\s+install\s+-g", profile["developer_instructions"]):
            finding("READONLY_WRITE_CONTRADICTION", "warning", path, 5,
                    "Instructions request asset writes/global installation despite a read-only declaration.")
        category = path.split("/")[1]
        profiles.append({"name": profile["name"], "path": path, "category": category,
                         "sha256_verified": True, "sha256": expected[path]["sha256"],
                         "fields": sorted(profile), "model": profile.get("model"),
                         "sandbox_mode": profile.get("sandbox_mode"),
                         "model_reasoning_effort": profile.get("model_reasoning_effort"),
                         "instruction_words": len(profile["developer_instructions"].split()),
                         "truth_waiver_lines": terminal,
                         "guardian_mapping": expected[path].get("guardian_mapping"),
                         "competence": "NOT_VERIFIED", "import_allowed": False})
    for path, raw in files.items():
        if not path.endswith(".md"):
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeError as exc:
            raise UpstreamReviewError(f"Invalid UTF-8 documentation: {path}") from exc
        for number, line in enumerate(text.splitlines(), 1):
            if line.strip() == "[instructions]":
                finding("README_WRONG_INSTRUCTION_SCHEMA", "warning", path, number,
                        "Use top-level developer_instructions; the sample differs from every locked profile and contribution contract.")
            if "sandbox_mode" in line and re.search(r"controls filesystem access", line, re.I):
                finding("README_SANDBOX_ENFORCEMENT_CLAIM", "warning", path, number,
                        "A profile request alone cannot certify effective filesystem, network or MCP confinement.")
            count = re.search(r"([0-9]{2})\. ([^<]+).*?\((\d+) agents\)", line)
            if count:
                prefix = count.group(1) + "-"
                observed = sum(x["category"].startswith(prefix) for x in profiles)
                if int(count.group(3)) != observed:
                    finding("README_CATEGORY_COUNT", "warning", path, number,
                            f"Declared {count.group(3)} agents, observed {observed} local profiles; external links are not installed agents.")
    for profile in profiles:
        for index in ("README.md", "categories/" + profile["category"] + "/README.md"):
            text = files.get(index, b"").decode("utf-8")
            if not re.search(r"(?<![a-z0-9-])" + re.escape(profile["name"]) + r"(?![a-z0-9-])", text):
                finding("README_PROFILE_MISSING", "warning", index, 1,
                        "Missing indexed profile: " + profile["name"])
    return {"schema_version": 1, "mode": "local_static_review", "source_commit_declared": lock["commit"],
            "source_commit_git_attested": False, "all_locked_hashes_verified": True,
            "profile_count": len(profiles), "category_counts": dict(sorted(collections.Counter(x["category"] for x in profiles).items())),
            "model_counts": dict(collections.Counter(x["model"] for x in profiles)),
            "sandbox_counts": dict(collections.Counter(x["sandbox_mode"] for x in profiles)),
            "files": [{"path": p, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                       "lines": len(raw.splitlines())} for p, raw in sorted(files.items())],
            "profiles": profiles, "findings": findings,
            "review_ok": not any(f["severity"] == "block" for f in findings),
            "remote_sync_allowed": False, "installation_allowed": False,
            "executed_upstream_code": False, "effective_sandbox_verified": False,
            "limitations": ["Static catalog review is not agent execution or competence certification.",
                            "Only profile bytes are source-locked; documentation hashes are inventoried, not upstream-authenticated.",
                            "Local paths must be operator-controlled; this is not a hostile filesystem sandbox.",
                            "No model, MCP, tool or platform provisioning is performed."]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["review"])
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    args = parser.parse_args(argv)
    try:
        result = review(args.source_dir, args.lock)
    except (OSError, UpstreamReviewError) as exc:
        print(json.dumps({"review_ok": False, "error": str(exc), "installation_allowed": False}))
        return 3
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result["review_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
