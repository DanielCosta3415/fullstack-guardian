"""Shared, fail-closed maintenance lock and filesystem safety primitives.

The lock coordinates cooperating Guardian tools, not arbitrary external writers.
An abandoned lock must be investigated; no tool guesses whether it is safe to remove.
"""
from contextlib import contextmanager, ExitStack
import json
from datetime import datetime, timezone
import os
from pathlib import Path
import stat
import tempfile
import uuid


def safe(path):
    path = Path(os.path.abspath(path))
    for item in (path, *path.parents):
        if item.is_symlink() or (item.exists() and getattr(item.lstat(), 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400)):
            raise ValueError('Symlink/reparse path rejected')
    return path


def atomic_write(path, data):
    path = safe(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.guardian-write-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        safe(path)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def owned_target(path, *, codex, skills, runtime, instruction, agent_names, skill_names):
    """Exact shared installer/recovery ownership predicate; no whole-CODEX_HOME grant."""
    path = safe(path)
    return (path in (safe(instruction), safe(Path(codex) / 'config.toml'))
            or safe(runtime) in path.parents
            or (path.parent == safe(Path(codex) / 'agents') and path.name in agent_names)
            or (path.name == 'SKILL.md' and path.parent.name in skill_names and path.parent.parent == safe(skills)))


@contextmanager
def maintenance_lock(home, operation='maintenance'):
    home = safe(home)
    home.mkdir(parents=True, exist_ok=True)
    path = safe(home / '.guardian-maintenance.lock')
    # Legacy names remain blockers, never silently bypass an older tool's lock.
    for filename in ('.guardian-install.lock', '.guardian-packs.lock', '.guardian-recovery.lock'):
        if safe(home / filename).exists():
            raise ValueError('Guardian maintenance locked; investigate interrupted operation')
    token = uuid.uuid4().hex
    payload = json.dumps({'schema_version': 1, 'pid': os.getpid(), 'operation': operation, 'started_utc': datetime.now(timezone.utc).isoformat(), 'token': token}).encode()
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError('Guardian maintenance locked; investigate interrupted operation') from exc
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        yield
    finally:
        # Never delete a replacement lock created by another actor.
        if safe(path).is_file() and path.read_bytes() == payload:
            path.unlink()


@contextmanager
def maintenance_locks(roots, operation='maintenance'):
    """Lock every mutable scope in deterministic order, including shared skills.

    Distinct CODEX_HOME directories can share the same user skills directory.
    Locking CODEX_HOME alone does not serialize those installations. Failed
    acquisition releases already acquired locks; abandoned locks still require
    investigation and are never automatically removed.
    """
    ordered = sorted({safe(root) for root in roots}, key=lambda path: os.path.normcase(str(path)))
    if not ordered:
        raise ValueError('Maintenance requires at least one mutable root')
    with ExitStack() as stack:
        for root in ordered:
            stack.enter_context(maintenance_lock(root, operation))
        yield
