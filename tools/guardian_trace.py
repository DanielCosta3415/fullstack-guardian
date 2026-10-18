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
import sys
from datetime import datetime, timezone
from pathlib import Path

EVENTS = frozenset(("plan", "delegate", "tool_result", "verification", "approval_requested", "approval_recorded", "blocked", "finish"))
SENSITIVE_KEY = re.compile(r"(?i)(password|secret|api.?key|authorization|access.?token|refresh.?token|private.?key|credential|session.?id)")
SENSITIVE_VAL = re.compile(r"(?i)(bearer\s+\S+|-----BEGIN.*PRIVATE KEY|(?:password|api_key|secret)\s*[:=]\s*\S+)")
ZERO = "0" * 64


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
        if len(payload) > 2000 or SENSITIVE_VAL.search(payload):
            raise TraceError("Potentially sensitive or oversized event payload")
        return payload
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
    return json.dumps(envelope, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"


def verify(path: Path) -> dict:
    path = _guard(path)
    if not path.is_file():
        raise TraceError("Journal not found")
    previous = ZERO
    count = 0
    with path.open("r", encoding="utf-8") as file:
        for raw in file:
            if not raw.endswith("\n") or len(raw) > 16000:
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
            if _clean(event["data"]) != event["data"]:
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
        with path.open("x", encoding="utf-8") as out:
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
        with path.open("a", encoding="utf-8") as out:
            out.write(entry)
            out.flush()
            os.fsync(out.fileno())
        return verify(path)
    finally:
        lock.unlink(missing_ok=True)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    for action in ("init", "verify", "append"):
        x = sub.add_parser(action)
        x.add_argument("--file", type=Path, required=True)
        if action == "append":
            x.add_argument("--event", choices=sorted(EVENTS), required=True)
            x.add_argument("--data-file", type=Path, required=True, help="Review and sanitize JSON object before logging")
    args = p.parse_args()
    try:
        if args.command == "init":
            result = init(args.file)
        elif args.command == "verify":
            result = verify(args.file)
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
