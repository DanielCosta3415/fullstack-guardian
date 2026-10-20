#!/usr/bin/env python3
"""Guardian lifecycle installer. Python 3.11+, stdlib only; dry-run by default."""
import argparse
import hashlib
import json
import os
import stat
import sys
import tomllib
import uuid
import tempfile
from pathlib import Path
from tools.guardian_maintenance import maintenance_locks, owned_target

SOURCE = Path(__file__).resolve().parent
START = '<!-- GUARDIAN-V2:START -->'
END = '<!-- GUARDIAN-V2:END -->'

def atomic_write(path, content):
    """Replace a managed file atomically after flushing, without following symlinks."""
    path = safe(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.guardian-write-', dir=path.parent, delete=False) as stream:
            temp = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        safe(path)
        os.replace(temp, path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def sha(path):
    return digest(Path(path).read_bytes())

def digest(data):
    return hashlib.sha256(data).hexdigest()

def safe(path):
    path = Path(os.path.abspath(path))
    for part in [path, *path.parents]:
        if part.exists() or part.is_symlink():
            info = part.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ValueError('Symlink/reparse path rejected: ' + str(part))
    return path

def locations(mode, dest):
    if mode == 'user':
        home = safe(dest or Path.home())
        c = safe(home / '.codex') if dest or not os.environ.get('CODEX_HOME') else safe(Path(os.environ['CODEX_HOME']).expanduser())
        return c, safe(home / '.agents' / 'skills'), c / 'guardian-system', c / 'AGENTS.md', SOURCE / 'global' / 'AGENTS.md'
    project = safe(dest)
    if not project.is_dir() or project == SOURCE:
        raise ValueError('Project must exist and differ from source')
    return project / '.codex', project / '.agents' / 'skills', project / '.guardian', project / 'AGENTS.md', SOURCE / 'project-template' / 'AGENTS.md'

def proposal(mode, dest):
    c, skills, runtime, instruction, piece = locations(mode, dest)
    jobs = []
    roots = ('global', 'core', 'tools', 'tests', 'project-template', 'docs', 'packs', 'scripts', 'eval')
    sources = [item for name in roots if (SOURCE / name).exists() for item in (SOURCE / name).rglob('*')]
    sources.extend(SOURCE / name for name in ('install.py', 'README.md', 'RELEASE_NOTES.md', 'VERSION', 'LICENSE', 'NOTICE.md', 'THIRD_PARTY_NOTICES.md', 'SECURITY.md', 'SUPPORT.md'))
    for f in sources:
        rel = f.relative_to(SOURCE)
        if f.is_file() and not any(x in rel.parts for x in ('__pycache__', '.git')) and f.suffix != '.pyc':
            safe(f)
            jobs.append((f, safe(runtime / rel)))
    for f in (SOURCE / 'global' / 'agents').glob('*.toml'):
        jobs.append((f, safe(c / 'agents' / f.name)))
    for f in (SOURCE / 'global' / 'skills').glob('*/SKILL.md'):
        jobs.append((f, safe(skills / f.parent.name / f.name)))
    return jobs, safe(instruction), piece

def policy_bytes(content, piece, runtime=None):
    policy = piece.read_text(encoding='utf8').strip()
    if runtime is not None:
        policy = policy.replace('{{GUARDIAN_RUNTIME}}', str(runtime).replace('\\', '/'))
    block = (START + '\n' + policy + '\n' + END).encode()
    a, b = START.encode(), END.encode()
    if a in content or b in content:
        if content.count(a) != 1 or content.count(b) != 1 or content.index(a) > content.index(b):
            raise ValueError('Malformed Guardian markers')
        old = content[content.index(a):content.index(b) + len(b)]
        if old != block:
            raise ValueError('Existing Guardian policy differs; use owned update or review manually')
        return content, b''
    addition = (b'\n\n' if content else b'') + block + b'\n'
    return content + addition, addition

def append_instruction(p, piece, apply):
    safe(p)
    old = p.read_bytes() if p.exists() else b''
    new, addition = policy_bytes(old, piece)
    if apply and addition:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(new)
    return 'append' if addition else 'unchanged'

def config_bytes(old):
    text = old.decode('utf8')
    conf = tomllib.loads(text)
    agents = conf.get('agents', {})
    if not isinstance(agents, dict):
        raise ValueError('agents must be a TOML table')
    missing = {k: v for k, v in [('enabled', 'true'), ('max_concurrent_threads_per_session', '4')] if k not in agents}
    if 'max_threads' in agents:
        missing.pop('max_concurrent_threads_per_session', None)
    if not missing:
        return old, b''
    lines = ''.join(k + ' = ' + v + ' # Guardian managed\n' for k, v in missing.items()).encode()
    # Place additions in a literal [agents] table; avoid moving unrelated bytes.
    import re
    match = re.search(rb'(?m)^\s*\[agents\]\s*(?:#[^\r\n]*)?\r?\n', old)
    if 'agents' in conf and not match:
        raise ValueError('Inline/dotted agents configuration requires manual integration')
    if match:
        new = old[:match.end()] + lines + old[match.end():]
        addition = lines
    else:
        header = (b'\n' if old else b'') + b'[agents]\n'
        addition = lines
        new = old + header + lines
    tomllib.loads(new.decode('utf8'))
    return new, addition

def remove_managed(current, entry):
    addition = bytes.fromhex(entry['addition'])
    if current.count(addition) != 1:
        raise ValueError('Managed configuration/policy was edited: ' + entry['path'])
    result = current.replace(addition, b'', 1)
    header = bytes.fromhex(entry.get('header', ''))
    if header and tomllib.loads(result.decode('utf8')).get('agents') == {}:
        if result.count(header) != 1:
            raise ValueError('Managed table header changed')
        result = result.replace(header, b'', 1)
    return result

def read(path):
    safe(path)
    if path.exists() and not path.is_file():
        raise ValueError('Not a regular file: ' + str(path))
    return path.read_bytes() if path.exists() else None

def validate_receipt(raw, mode, identity, owned_path):
    import re
    value = json.loads(raw)
    if not isinstance(value, dict) or value.get('schema') != 1 or value.get('mode') != mode or value.get('identity') != identity or not isinstance(value.get('files'), list) or not value['files']:
        raise ValueError('Invalid ownership receipt')
    seen = set()
    for entry in value['files']:
        if not isinstance(entry, dict) or not isinstance(entry.get('path'), str) or not isinstance(entry.get('hash'), str) or not re.fullmatch('[a-f0-9]{64}', entry['hash']):
            raise ValueError('Invalid ownership entry')
        path = owned_path(entry['path'])
        if path in seen:
            raise ValueError('Duplicate ownership entry')
        seen.add(path)
        if 'adopted' in entry and type(entry['adopted']) is not bool:
            raise ValueError('Invalid adopted flag')
        for key in ('addition', 'header'):
            if key in entry:
                if not isinstance(entry[key], str):
                    raise ValueError('Invalid managed bytes')
                data = bytes.fromhex(entry[key])
                if not data or path not in (safe(identity['instruction']), safe(Path(identity['codex']) / 'config.toml')):
                    raise ValueError('Invalid managed ownership block')
    return value


def lifecycle(mode, dest, operation='install', apply=False, adopt=False):
    if apply:
        c, skills, runtime, instruction, _ = locations(mode, dest)
        # Runtime is already inside c (user) or instruction.parent (project).
        # Locking it separately would create an apparent runtime before receipt
        # validation and is unnecessary for mutual exclusion.
        with maintenance_locks((c, skills, instruction.parent), operation):
            return _lifecycle(mode, dest, operation, apply, adopt)
    return _lifecycle(mode, dest, operation, apply, adopt)


def _lifecycle(mode, dest, operation='install', apply=False, adopt=False):
    c, skills, runtime, instruction, piece = locations(mode, dest)
    receipt_path = safe(c / 'guardian-install.json')
    prior_bytes = read(receipt_path)
    prior = json.loads(prior_bytes) if prior_bytes else None
    identity = {'codex': str(safe(c)), 'skills': str(safe(skills)), 'runtime': str(safe(runtime)), 'instruction': str(safe(instruction))}
    agent_names = {f.name for f in (SOURCE / 'global' / 'agents').glob('*.toml')}
    skill_names = {f.parent.name for f in (SOURCE / 'global' / 'skills').glob('*/SKILL.md')}
    def owned_path(value):
        p = safe(value)
        valid = owned_target(p, codex=c, skills=skills, runtime=runtime, instruction=instruction,
                             agent_names=agent_names, skill_names=skill_names)
        if not valid:
            raise ValueError('Receipt path outside installation roots: ' + str(p))
        return p
    if prior_bytes is not None and (not isinstance(prior, dict) or prior.get('schema') != 1 or prior.get('mode') != mode or prior.get('identity') != identity or not isinstance(prior.get('files'), list)):
        raise ValueError('Incompatible receipt')
    if prior:
        for entry in prior['files']:
            if not isinstance(entry, dict) or not isinstance(entry.get('path'), str) or not isinstance(entry.get('hash'), str):
                raise ValueError('Malformed ownership entry')
            owned_path(entry['path'])
    if prior_bytes is not None:
        validate_receipt(prior_bytes, mode, identity, owned_path)
    if operation == 'doctor':
        if not prior:
            raise ValueError('No ownership receipt; installation not verified')
        failures = []
        for e in prior['files']:
            current = read(owned_path(e['path']))
            if current is None or (current.count(bytes.fromhex(e['addition'])) != 1 if e.get('addition') else digest(current) != e['hash']):
                failures.append(e['path'])
        if failures:
            raise ValueError('Changed/missing installed files: ' + ', '.join(failures))
        _, missing_policy = policy_bytes(read(instruction) or b'', piece, runtime)
        if missing_policy:
            raise ValueError('Guardian coordination policy is missing')
        agents = tomllib.loads((read(c / 'config.toml') or b'').decode('utf8')).get('agents', {})
        warnings = []
        if agents.get('enabled') is not True:
            warnings.append('Existing configuration does not enable agents; automatic delegation is not verified')
        concurrency = agents.get('max_concurrent_threads_per_session', agents.get('max_threads'))
        if not isinstance(concurrency, int) or isinstance(concurrency, bool) or concurrency < 1:
            warnings.append('Agent concurrency is missing or invalid')
        from tools.guardian_capabilities import capability_report
        return {'operation': operation, 'verified_files': len(prior['files']), 'apply': False, 'warnings': warnings,
                'client_capabilities': capability_report(),
                'native_loading': 'NOT_VERIFIED', 'permissions_changed': False}
    if operation in ('update', 'uninstall', 'rollback') and not prior:
        raise ValueError('No receipt; explicit install --adopt is required for identical legacy files')
    changes = {}
    entries = []
    previous = {e['path']: e for e in prior['files']} if prior else {}
    if operation == 'rollback':
        backup = safe(prior['backup'])
        if c / 'guardian-backups' not in backup.parents:
            raise ValueError('Invalid backup location')
        manifest = json.loads(read(backup / 'transaction.json'))
        if not isinstance(manifest, dict) or not isinstance(manifest.get('changes'), list):
            raise ValueError('Invalid rollback manifest')
        seen = set()
        for index, item in enumerate(manifest['changes']):
            if not isinstance(item, dict) or set(item) not in ({'path', 'before', 'after'}, {'path', 'before', 'after', 'before_sha256'}) or item['before'] not in (None, str(index) + '.bin'):
                raise ValueError('Invalid rollback entry')
            p = owned_path(item['path'])
            if p in seen:
                raise ValueError('Duplicate rollback target')
            seen.add(p)
            current = read(p)
            if (digest(current) if current is not None else None) != item['after']:
                raise ValueError('Rollback would overwrite user changes: ' + str(p))
            before_path = safe(backup / item['before']) if item['before'] else None
            if before_path is not None and before_path.parent != backup:
                raise ValueError('Invalid backup file path')
            old = read(before_path) if before_path else None
            if before_path and old is None:
                raise ValueError('Missing backup content')
            if 'before_sha256' in item and item['before_sha256'] != (digest(old) if old is not None else None):
                raise ValueError('Backup content digest mismatch')
            changes[p] = old
        next_receipt = read(backup / 'receipt-before.json')
        if next_receipt is not None:
            validate_receipt(next_receipt, mode, identity, owned_path)
    elif operation == 'uninstall':
        for e in prior['files']:
            p = owned_path(e['path']); current = read(p)
            if current is None:
                continue
            if e.get('addition'):
                changes[p] = remove_managed(current, e) or None
            elif digest(current) != e['hash']:
                raise ValueError('Owned file was edited; preserve and review: ' + str(p))
            elif not e.get('adopted'):
                changes[p] = None
        next_receipt = None
    else:
        jobs, instruction, piece = proposal(mode, dest)
        desired = {str(dst): src.read_bytes() for src, dst in jobs}
        for name, data in desired.items():
            p = owned_path(name); old = read(p); e = previous.get(name)
            if old is not None and old != data:
                if not e or digest(old) != e['hash'] or operation != 'update':
                    raise ValueError('Conflicting existing file: ' + name)
            if old is not None and not e and not adopt:
                raise ValueError('Existing file requires explicit --adopt: ' + name)
            if old != data:
                changes[p] = data
            entries.append({'path': name, 'hash': digest(data), 'adopted': e.get('adopted', False) if e else old is not None})
        for name, e in previous.items():
            if name in desired or e.get('addition'):
                continue
            p = owned_path(name); old = read(p)
            if old is not None and digest(old) != e['hash']:
                raise ValueError('Removed owned file edited: ' + name)
            if not e.get('adopted'):
                changes[p] = None
        for p, kind in [(instruction, 'policy'), (safe(c / 'config.toml'), 'config')]:
            old = read(p) or b''; e = previous.get(str(p))
            base = old
            old_addition = bytes.fromhex(e['addition']) if e and e.get('addition') else b''
            if old_addition:
                if old.count(old_addition) != 1:
                    raise ValueError('Managed block edited: ' + str(p))
                base = remove_managed(old, e)
            new, addition = policy_bytes(base, piece, runtime) if kind == 'policy' else config_bytes(base)
            if new != old:
                changes[p] = new
            if addition:
                entry = {'path': str(p), 'hash': digest(new), 'addition': addition.hex()}
                if kind == 'config' and 'agents' not in tomllib.loads(base.decode('utf8')):
                    entry['header'] = ((b'\n' if base else b'') + b'[agents]\n').hex()
                elif kind == 'config' and e and e.get('header') and base == old.replace(old_addition, b'', 1):
                    entry['header'] = e['header']
                entries.append(entry)
        next_receipt = None
    result = {'operation': operation, 'apply': apply, 'changes': len(changes), 'files': len(entries)}
    if not apply:
        return result
    backup = safe(c / 'guardian-backups' / uuid.uuid4().hex)
    backup.mkdir(parents=True)
    manifest = {'schema_version': 2, 'mode': mode, 'identity': identity, 'operation': operation, 'changes': []}
    originals = {p: read(p) for p in changes}
    for i, (p, new) in enumerate(changes.items()):
        old = originals[p]; filename = str(i) + '.bin' if old is not None else None
        if filename:
            atomic_write(backup / filename, old)
        manifest['changes'].append({'path': str(p), 'before': filename, 'after': digest(new) if new is not None else None, 'before_sha256': digest(old) if old is not None else None})
    if prior_bytes:
        atomic_write(backup / 'receipt-before.json', prior_bytes)
    atomic_write(backup / 'transaction.json', json.dumps(manifest, indent=2).encode())
    if operation in ('install', 'update'):
        next_receipt = json.dumps({'schema': 1, 'mode': mode, 'identity': identity, 'version': (SOURCE / 'VERSION').read_text().strip() if (SOURCE / 'VERSION').exists() else '2.1.0', 'backup': str(backup), 'files': entries}, indent=2).encode()
    try:
        for p, data in changes.items():
            safe(p)
            if data is None:
                p.unlink(missing_ok=True)
            else:
                p.parent.mkdir(parents=True, exist_ok=True)
                atomic_write(p, data)
        if next_receipt is None:
            receipt_path.unlink(missing_ok=True)
        else:
            atomic_write(receipt_path, next_receipt)
    except BaseException:
        for p, data in originals.items():
            if data is None:
                p.unlink(missing_ok=True)
            else:
                atomic_write(p, data)
        if prior_bytes is None:
            receipt_path.unlink(missing_ok=True)
        else:
            atomic_write(receipt_path, prior_bytes)
        raise
    return result

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    scope = ap.add_mutually_exclusive_group(required=True)
    scope.add_argument('--user', action='store_true')
    scope.add_argument('--project', type=Path)
    ap.add_argument('--home', type=Path)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--adopt', action='store_true', help='Explicitly recognize identical legacy files; never deletes adopted files')
    operations = ap.add_mutually_exclusive_group()
    for action in ('update', 'uninstall', 'rollback', 'doctor'):
        operations.add_argument('--' + action, action='store_true')
    args = ap.parse_args()
    if args.home and not args.user:
        ap.error('--home requires --user')
    operation = next((a for a in ('update', 'uninstall', 'rollback', 'doctor') if getattr(args, a)), 'install')
    try:
        mode = 'user' if args.user else 'project'
        destination = args.home if args.user else args.project
        result = lifecycle(mode, destination, operation, args.apply, args.adopt)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, UnicodeError, KeyError, TypeError, AttributeError) as exc:
        print('BLOCKED: ' + str(exc), file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())
