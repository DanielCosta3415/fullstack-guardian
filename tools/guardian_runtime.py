"""Bounded CLI supervision and Git path inspection (no invented native scheduler).

These are integrity checks, not an OS isolation boundary. The executor builds
private checkouts with independent object stores, refs and Git configuration.
"""
from __future__ import annotations
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import subprocess

class RuntimeError(ValueError):
    pass

PROTECTED = re.compile(r"(?i)(^|/)(?:\.git|\.codex|\.agents|\.aws|\.ssh|\.env(?:\..*)?|AGENTS\.md|config\.toml|auth\.json|id_rsa|secrets?\.(?:json|ya?ml)|[^/]+\.(?:pem|key|pfx))(?:/|$)")


def relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
        raise RuntimeError("Invalid changed path")
    # Reject Windows alternate streams, drive-relative paths, UNC, separators and
    # aliases even on POSIX so review has the same meaning on another platform.
    if "\\" in value or ":" in value or value.startswith("/"):
        raise RuntimeError("Absolute or ambiguous changed path")
    parts = PurePosixPath(value).parts
    if any(p in ("", ".", "..") or p.endswith((" ", ".")) for p in value.split("/")):
        raise RuntimeError("Unsafe path component")
    if any(re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", p) for p in parts):
        raise RuntimeError("Reserved Windows path")
    return value


def changed_paths(repo: Path) -> list[str]:
    # --no-renames deliberately exposes BOTH the deletion and addition. Parsing
    # NUL bytes handles whitespace, Unicode and quotes without shell quoting.
    values = []
    for args in (("diff", "--no-ext-diff", "--no-textconv", "--no-renames", "--name-only", "-z", "HEAD"),
                 ("ls-files", "--others", "--exclude-standard", "-z")):
        p = subprocess.run(["git", "-c", "core.fsmonitor=false", "-C", str(repo), *args], capture_output=True, check=True, timeout=30)
        values += [relative_path(x.decode("utf-8", "strict")) for x in p.stdout.split(b"\0") if x]
    names = sorted(set(values))
    if len(names) > 1000:
        raise RuntimeError("Too many changed paths")
    aliases = {}
    for name in names:
        norm = name.casefold()
        if norm in aliases and aliases[norm] != name:
            raise RuntimeError("Case-ambiguous changed paths")
        aliases[norm] = name
    return names


def matches(path: str, patterns: list[str]) -> bool:
    relative_path(path)
    for value in patterns:
        if value == path or (value.endswith("/**") and path.startswith(value[:-2])):
            return True
    return False


def inventory(repo: Path) -> dict:
    # Include ignored files too: Git status intentionally hides e.g. .env and
    # caches, so a status-only snapshot would miss unauthorized writes there.
    result = {}
    total = 0
    for parent, dirs, files in os.walk(repo, followlinks=False):
        parent = Path(parent)
        if parent == repo and ".git" in dirs:
            dirs.remove(".git")
        for name in dirs:
            target = parent / name
            if target.is_symlink() or getattr(target.lstat(), "st_file_attributes", 0) & 0x400:
                raise RuntimeError("Checkout symlink/reparse directory unsupported")
        for name in files:
            target = parent / name
            path = relative_path(target.relative_to(repo).as_posix())
            if target.is_symlink() or getattr(target.lstat(), "st_file_attributes", 0) & 0x400:
                raise RuntimeError("Checkout symlink/reparse file unsupported")
            if not target.is_file():
                raise RuntimeError("Checkout path is not a regular file")
            size = target.stat().st_size
            total += size
            if size > 20_000_000 or total > 1_000_000_000 or len(result) >= 100000:
                raise RuntimeError("Checkout snapshot budget exceeded")
            result[path] = hashlib.sha256(target.read_bytes()).hexdigest()
    return result


def scope_delta(before: dict, after: dict, allowed: list[str], *, read_only: bool) -> list[str]:
    delta = sorted(k for k in set(before) | set(after) if before.get(k, "missing") != after.get(k, "missing"))
    if any(PROTECTED.search(k) for k in delta):
        raise RuntimeError("Protected path changed")
    if read_only and delta:
        raise RuntimeError("Read-only contract changed files")
    if any(not matches(k, allowed) for k in delta):
        raise RuntimeError("Changed path outside task ownership")
    return delta


def _windows_kill_tree(proc):
    """Use Win32 handles, avoiding taskkill's account lookup dependency."""
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    class Entry(ctypes.Structure):
        _fields_ = [("dwSize",wintypes.DWORD),("cntUsage",wintypes.DWORD),
                    ("th32ProcessID",wintypes.DWORD),("th32DefaultHeapID",ctypes.c_size_t),
                    ("th32ModuleID",wintypes.DWORD),("cntThreads",wintypes.DWORD),
                    ("th32ParentProcessID",wintypes.DWORD),("pcPriClassBase",wintypes.LONG),
                    ("dwFlags",wintypes.DWORD),("szExeFile",wintypes.WCHAR*260)]
    kernel.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
    kernel.Process32FirstW.argtypes=[wintypes.HANDLE,ctypes.POINTER(Entry)]
    kernel.Process32NextW.argtypes=[wintypes.HANDLE,ctypes.POINTER(Entry)]
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.TerminateProcess.argtypes=[wintypes.HANDLE,wintypes.UINT]
    kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    snapshot=kernel.CreateToolhelp32Snapshot(2,0)
    if snapshot == wintypes.HANDLE(-1).value:
        proc.kill()
        raise RuntimeError("Cannot enumerate Windows descendants; termination uncertain")
    entries=[]
    try:
        entry=Entry(); entry.dwSize=ctypes.sizeof(Entry)
        ok=kernel.Process32FirstW(snapshot,ctypes.byref(entry))
        while ok:
            entries.append((entry.th32ProcessID,entry.th32ParentProcessID))
            if len(entries)>100000: raise RuntimeError("Process inventory bound exceeded")
            ok=kernel.Process32NextW(snapshot,ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    descendants={proc.pid}; ordered=[]
    for _ in range(64):
        found=[pid for pid,parent in entries if parent in descendants and pid not in descendants]
        if not found: break
        descendants.update(found); ordered.extend(found)
    else:
        proc.kill(); raise RuntimeError("Process depth exceeds termination bound")
    handles=[]
    try:
        for pid in reversed(ordered):
            handle=kernel.OpenProcess(0x00100001,False,pid) # SYNCHRONIZE | PROCESS_TERMINATE
            if handle:
                handles.append(handle)
                if not kernel.TerminateProcess(handle,1):
                    raise RuntimeError("Cannot terminate descendant; mutation state uncertain")
            elif ctypes.get_last_error() != 87: # invalid PID means it exited
                raise RuntimeError("Cannot open descendant; termination uncertain")
        if proc.poll() is None: proc.kill()
        for handle in handles:
            if kernel.WaitForSingleObject(handle,2000) != 0:
                raise RuntimeError("Descendant did not terminate")
    finally:
        if proc.poll() is None:
            proc.kill()
        for handle in handles: kernel.CloseHandle(handle)


def terminate_tree(proc: subprocess.Popen, grace: float = 2.0) -> None:
    """Terminate process descendants; a failure must not be reported as success."""
    if os.name == "nt":
        _windows_kill_tree(proc)
    else:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            pass
        # Kill the original process group even when its leader exited first.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Process tree termination not confirmed") from exc


def backend_capabilities() -> dict:
    return {"adapter": "codex_cli", "native_scheduler": False, "parallel": True, "parallel_writes": False, "parallel_read_only": True,
            "requested_sandbox_modes": ["read-only", "workspace-write"],
            "filesystem_isolation_verified": False, "read_scope": "unrestricted_inherited", "per_file_write_enforcement": False,
            "network_denial_verified": False, "read_only_sandbox_verified": False,
            "write_scope": "postcondition_only", "git_metadata_shared": False, "process_group_termination": True, "hostile_process_escape_containment": False,
            "cpu_memory_process_quotas": False,
            "untrusted_check_execution": False}
