#!/usr/bin/env python3
"""Local append-only hash-chained Guardian event journal.

A checksum chain detects accidental edits but is NOT tamper-proof authentication:
a malicious writer can reconstruct the chain. Never store secrets or personal data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import math
import subprocess
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

EVENTS = frozenset(("plan", "checkpoint", "delegate", "tool_result", "verification", "approval_requested", "approval_recorded", "blocked", "finish"))
SENSITIVE_KEY = re.compile(r"(?i)(password|secret|api.?key|authorization|access.?token|refresh.?token|private.?key|credential|session.?id)")
SENSITIVE_VAL = re.compile(r"(?i)(bearer\s+\S+|-----BEGIN.*PRIVATE KEY|(?:password|api_key|secret)\s*[:=]\s*\S+)")
PERSONAL_VAL = re.compile(r"(?i)([a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)+|(?:C:|/home|/Users)[\\/](?:Users[\\/])?[^\\/\s]+)")
ZERO = "0" * 64
MAX_EVENT_BYTES = 16000
MAX_JOURNAL_BYTES = 16_000_000


class TraceError(ValueError):
    pass


def _guard(path: Path) -> Path:
    p = Path(os.path.abspath(path))
    for current in (p, *p.parents):
        if current.is_symlink() or (current.exists() and getattr(current.lstat(), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
            raise TraceError("Symlink/reparse journal path denied")
    return p


def _clean(payload: object, depth: int = 0) -> object:
    if depth > 10:
        raise TraceError("Payload nesting too deep")
    if isinstance(payload, dict):
        if len(payload) > 100:
            raise TraceError("Payload has too many keys")
        out = {}
        for k, v in payload.items():
            if not isinstance(k, str) or SENSITIVE_KEY.search(k):
                raise TraceError("Sensitive/invalid payload key")
            out[k] = _clean(v, depth+1)
        return out
    if isinstance(payload, list):
        if len(payload) > 100:
            raise TraceError("Payload list too large")
        return [_clean(x, depth+1) for x in payload]
    if isinstance(payload, str):
        if len(payload) > 2000 or SENSITIVE_VAL.search(payload) or PERSONAL_VAL.search(payload):
            raise TraceError("Potentially sensitive or oversized event payload")
        return payload
    if type(payload) is float and not math.isfinite(payload):
        raise TraceError("Non-finite numeric payload")
    if payload is None or type(payload) in (bool, int, float):
        return payload
    raise TraceError("Unsupported payload type")


def _hash(entry: dict) -> str:
    canonical = json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _line(seq: int, event: str, data: dict, prev: str) -> str:
    if event not in EVENTS:
        raise TraceError("Unknown event")
    clean = _clean(data)
    if not isinstance(clean, dict):
        raise TraceError("Event data must be object")
    envelope = {"schema_version": 1, "sequence": seq, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "event": event, "data": clean, "previous": prev}
    envelope["checksum"] = _hash(envelope)
    line = json.dumps(envelope, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
    if len(line.encode("utf-8")) > MAX_EVENT_BYTES:
        raise TraceError("Serialized event exceeds byte limit")
    return line


def verify(path: Path) -> dict:
    path = _guard(path)
    if not path.is_file():
        raise TraceError("Journal not found")
    if path.stat().st_size>MAX_JOURNAL_BYTES:
        raise TraceError('Journal exceeds local retention budget; archive/inspect explicitly')
    previous = ZERO
    count = 0
    with path.open("r", encoding="utf-8") as file:
        for raw in file:
            if not raw.endswith("\n") or len(raw.encode("utf-8")) > MAX_EVENT_BYTES:
                raise TraceError("Truncated or oversized event")
            try:
                event = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise TraceError("Invalid event JSON") from exc
            if not isinstance(event, dict) or set(event) != {"schema_version", "sequence", "timestamp_utc", "event", "data", "previous", "checksum"}:
                raise TraceError("Invalid event shape")
            if event["schema_version"] != 1 or type(event["sequence"]) is not int or event["sequence"] != count:
                raise TraceError("Unexpected sequence")
            if event["event"] not in EVENTS or event["previous"] != previous:
                raise TraceError("Broken event chain")
            if not isinstance(event["checksum"], str) or len(event["checksum"]) != 64:
                raise TraceError("Invalid checksum")
            data = dict(event)
            checksum = data.pop("checksum")
            if checksum != _hash(data):
                raise TraceError("Event content altered")
            if not isinstance(event["data"], dict) or _clean(event["data"]) != event["data"]:
                raise TraceError("Invalid payload")
            previous = checksum
            count += 1
    if count == 0:
        raise TraceError("Empty journal")
    return {"ok": True, "events": count, "last_checksum": previous,
            "authenticated": False, "note": "Integrity checksum only; self-reported events do not prove native execution."}


def init(path: Path) -> dict:
    path = _guard(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as out:
            out.write(_line(0, "plan", {"status": "created", "execution": "not_started"}, ZERO))
            out.flush()
            os.fsync(out.fileno())
    except FileExistsError as exc:
        raise TraceError("Journal exists; cannot overwrite") from exc
    return verify(path)


def append(path: Path, event: str, data: dict) -> dict:
    path = _guard(path)
    lock = _guard(Path(str(path)+".lock"))
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise TraceError("Journal locked") from exc
    try:
        os.close(fd)
        valid = verify(path)
        entry = _line(valid["events"], event, data, valid["last_checksum"])
        if path.stat().st_size+len(entry.encode('utf-8'))>MAX_JOURNAL_BYTES:
            raise TraceError('Journal retention budget exceeded; existing evidence preserved')
        # A same-directory replacement leaves the original valid chain intact if writing fails.
        try:
            from .guardian_maintenance import atomic_write
        except ImportError:
            from guardian_maintenance import atomic_write
        atomic_write(path, path.read_bytes() + entry.encode("utf-8"))
        return verify(path)
    finally:
        lock.unlink(missing_ok=True)


def record_process_result(path: Path, *, check_id: str, tool: str,
                          tool_version: str, exit_code: int | None,
                          artifact_sha256: str | None = None) -> dict:
    """Persist minimal supervisor observations, never model text or raw output.

    A successful process exit is not test correctness or release authorization.
    Callers must supply actual observations; this local API does not authenticate
    who called it. Windows ACL enforcement depends on the host and is NOT VERIFIED.
    """
    for value in (check_id, tool, tool_version):
        if not isinstance(value, str) or not value or len(value) > 100:
            raise TraceError("Invalid observation identifier/version")
    if exit_code is not None and type(exit_code) is not int:
        raise TraceError("Invalid process exit code")
    if artifact_sha256 is not None and (not isinstance(artifact_sha256, str) or not re.fullmatch('[a-f0-9]{64}', artifact_sha256)):
        raise TraceError("Invalid artifact digest")
    return append(path, "tool_result", {"evidence_kind": "supervisor_process_observation",
        "check_id": check_id, "tool": tool, "tool_version": tool_version,
        "exit_code": exit_code, "artifact_sha256": artifact_sha256,
        "execution_status": "NOT_VERIFIED" if exit_code is None else "EXIT_ZERO" if exit_code == 0 else "EXIT_NONZERO",
        "correctness_status": "NOT_VERIFIED", "authenticated": False})


def public_summary(path: Path) -> dict:
    """Return counts and integrity only; never publish raw event payloads."""
    result = verify(path)
    acl=privacy_acl(path)
    return {**result, "raw_events_included": False, "retention": "explicit_checksum_confirmed_expiry",
            "host_acl_verified": acl['verified'], 'acl':acl}


def privacy_acl(path: Path) -> dict:
    """Read effective file DACL/mode without changing permissions or claiming ACL setup.

    This is a conservative privacy observation at this instant, not protection
    against administrators, later ACL edits or a compromised owner.
    """
    path=_guard(path)
    if not path.is_file(): raise TraceError('Journal not found')
    if os.name!='nt':
        private=path.stat().st_uid==os.getuid() and path.stat().st_mode & 0o077==0
        return {'verified':private,'mechanism':'posix_owner_mode','authenticated':False}
    powershell=shutil.which('powershell.exe')
    if not powershell:
        return {'verified':False,'mechanism':'windows_dacl','reason':'ACL reader unavailable'}
    # Path is an environment value, never interpolated as PowerShell program text.
    program="$a=Get-Acl -LiteralPath $env:GUARDIAN_ACL_PATH; $o=$a.Owner; if($o -notmatch '^S-1-'){$o=([System.Security.Principal.NTAccount]$o).Translate([System.Security.Principal.SecurityIdentifier]).Value}; $r=@($a.Access|ForEach-Object{@{sid=$_.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value;allow=($_.AccessControlType -eq 'Allow');rights=[int]$_.FileSystemRights}}); @{owner=$o;current=[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value;rules=$r}|ConvertTo-Json -Compress -Depth 4"
    try:
        env=os.environ.copy(); env['GUARDIAN_ACL_PATH']=str(path)
        proc=subprocess.run([powershell,'-NoProfile','-NonInteractive','-Command',program],env=env,capture_output=True,text=True,timeout=10)
        if proc.returncode or len(proc.stdout)>65536: raise ValueError('ACL probe failed')
        acl=json.loads(proc.stdout); trusted={acl['owner'],'S-1-5-18','S-1-5-32-544'}
        rules=acl['rules']; rules=[rules] if isinstance(rules,dict) else rules
        private=acl['owner']==acl['current'] and bool(rules) and not any(r['allow'] and r['sid'] not in trusted and r['rights'] & 0x1F01FF for r in rules)
        return {'verified':private,'mechanism':'windows_dacl','authenticated':False,
                'reason':'Owner/System/Administrators only' if private else 'Additional allow ACEs or uncertain DACL'}
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError):
        return {'verified':False,'mechanism':'windows_dacl','reason':'ACL observation unavailable'}


def expire(path: Path, *, retention_days: int, confirm_checksum: str | None=None,
           apply: bool=False, now: datetime | None=None) -> dict:
    """Delete one explicitly selected expired journal, never a directory or glob.

    Only a complete finished/integrated journal is eligible; live/uncertain runs
    retain evidence. The exact final checksum is mandatory for deletion.
    """
    path=_guard(path)
    if type(retention_days) is not int or not 1<=retention_days<=3650:
        raise TraceError('Retention days must be 1..3650')
    if _guard(path.parent/'.lock').exists():
        raise TraceError('Execution lock exists; active or uncertain run evidence cannot expire')
    lock=_guard(Path(str(path)+'.lock'))
    try: fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError as exc: raise TraceError('Journal locked') from exc
    try:
        os.close(fd); valid=verify(path)
        last=json.loads(path.read_text(encoding='utf-8').splitlines()[-1])
        finished=last['event']=='finish' or (last['event']=='verification' and last['data'].get('workflow_state')=='integrated')
        timestamp=datetime.fromisoformat(last['timestamp_utc'])
        if timestamp.tzinfo is None: raise TraceError('Journal timestamp has no timezone')
        clock=now or datetime.now(timezone.utc)
        eligible=finished and (clock-timestamp).total_seconds()>=retention_days*86400
        if apply:
            if not eligible or confirm_checksum!=valid['last_checksum']:
                raise TraceError('Deletion requires an expired completed journal and exact checksum confirmation')
            path.unlink()
        return {'eligible':eligible,'deleted':apply,'last_checksum':valid['last_checksum'],
                'retention_days':retention_days,'recursive':False}
    finally: lock.unlink(missing_ok=True)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    for action in ("init", "verify", "append", "privacy", "expire"):
        x = sub.add_parser(action)
        x.add_argument("--file", type=Path, required=True)
        if action == "append":
            x.add_argument("--event", choices=sorted(EVENTS), required=True)
            x.add_argument("--data-file", type=Path, required=True, help="Review and sanitize JSON object before logging")
        if action == 'expire':
            x.add_argument('--retention-days',type=int,required=True)
            x.add_argument('--confirm-checksum')
            x.add_argument('--apply',action='store_true')
    args = p.parse_args()
    try:
        if args.command == "init":
            result = init(args.file)
        elif args.command == "verify":
            result = verify(args.file)
        elif args.command == 'privacy':
            result=privacy_acl(args.file)
        elif args.command == 'expire':
            result=expire(args.file,retention_days=args.retention_days,confirm_checksum=args.confirm_checksum,apply=args.apply)
        else:
            obj = json.loads(_guard(args.data_file).read_text(encoding="utf-8"))
            result = append(args.file, args.event, obj)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (TraceError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
