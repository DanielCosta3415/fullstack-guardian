"""Explicit, bounded continuation checkpoints; never monitors accounts or wakes threads."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tempfile
from datetime import datetime, timezone

MAX_BYTES = 1_000_000
MAX_EVIDENCE_BYTES = 32_000_000
MAX_SOURCE_BYTES = 32_000_000
MAX_SOURCE_PATHS = 2048
SCHEMA_VERSION = 2
STATUSES = {'pending', 'in_progress', 'validated', 'blocked', 'not_verified'}
SIGNALS = {'milestone', 'manual_pause', 'quota_5h', 'quota_weekly', 'quota_unspecified'}
RELEASE_POLICIES = {'strict', 'operator-autonomous', 'unspecified'}
CONSTRAINTS = {'permission_bypass': False, 'credential_copy': False,
               'model_override_to_evade_quota': False,
               'automatic_wakeup': False}


def constraints_for(release_policy):
    if not isinstance(release_policy, str) or release_policy not in RELEASE_POLICIES:
        raise ValueError('Unknown release policy')
    required = {'strict': 'required', 'operator-autonomous': 'not_required_by_owner', 'unspecified': 'unspecified'}[release_policy]
    return {**CONSTRAINTS, 'release_policy': release_policy, 'remote_testing': required, 'human_approval': required}


def plain(path):
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        if part.exists() or part.is_symlink():
            meta = part.lstat()
            if stat.S_ISLNK(meta.st_mode) or getattr(meta, 'st_file_attributes', 0) & 0x400:
                raise ValueError('Symlink/reparse path rejected')
    return path


def fields(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError('Unknown or missing schema fields')


def bounded_text(value, limit=2000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit or any(ord(c) < 32 for c in value):
        raise ValueError('Expected bounded single-line text')
    return value


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('utf-8')


def read_json(path):
    path = plain(path)
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError('Expected bounded regular JSON file')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    def nonfinite(_):
        raise ValueError('Nonfinite JSON number')
    with path.open('rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('JSON exceeds bound')
    return json.loads(data, object_pairs_hook=pairs, parse_constant=nonfinite)


def relative(value):
    bounded_text(value, 500)
    parts = value.split('/')
    path = PurePosixPath(value)
    forbidden = {'.git', '.guardian-state', '.aws', '.ssh', '.codex', 'auth.json', '.env', 'credentials', 'credentials.json'}
    devices = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}
    if path.is_absolute() or '\\' in value or ':' in value or any(p in ('', '.', '..') or p.lower() in forbidden or p.lower().startswith('.env.') or p.lower().endswith(('.pem', '.key', '.p12', '.pfx')) or p.lower() in ('id_rsa', 'id_ed25519', 'id_ecdsa') or p.endswith((' ', '.')) or p.split('.')[0].upper() in devices for p in parts):
        raise ValueError('Unsafe or sensitive evidence path')
    return path


def evidence_hash(project, value):
    path = plain(project / relative(value))
    if not path.is_file() or path.stat().st_size > MAX_EVIDENCE_BYTES:
        raise ValueError('Evidence missing or exceeds bound')
    with path.open('rb') as stream:
        data = stream.read(MAX_EVIDENCE_BYTES + 1)
    if len(data) > MAX_EVIDENCE_BYTES:
        raise ValueError('Evidence exceeds bound')
    return digest(data)


def git_snapshot(project):
    def git(*args):
        result = subprocess.run(['git', '-C', str(project), *args], capture_output=True, timeout=20, check=True)
        if len(result.stdout) > MAX_BYTES:
            raise ValueError('Git snapshot exceeds bound')
        return result.stdout
    head = git('rev-parse', 'HEAD').decode('ascii').strip()
    if re.fullmatch('[0-9a-f]{40,64}', head) is None:
        raise ValueError('Invalid source revision')
    top = Path(git('rev-parse', '--show-toplevel').decode('utf-8').strip())
    if os.path.normcase(str(top.resolve())) != os.path.normcase(str(project.resolve())):
        raise ValueError('Project must be the Git working-tree root')
    # Never persist source filenames, diffs, remotes, prompts, or environment.
    status = git('status', '--porcelain=v1', '-z', '--untracked-files=all', '--', '.', ':(exclude).guardian-state')
    # Index blob identifiers bind staged changes without reading staged contents.
    index_status = git('diff', '--cached', '--raw', '-z', '--no-abbrev', '--no-renames',
                       '--no-ext-diff', '--no-textconv', '--', '.', ':(exclude).guardian-state')
    paths = []
    records = status.split(b'\0')
    index = 0
    while index < len(records) - 1:
        record = records[index]
        index += 1
        if len(record) < 4 or record[2:3] != b' ':
            raise ValueError('Malformed Git status')
        paths.append(record[3:])
        if b'R' in record[:2] or b'C' in record[:2]:
            if index >= len(records) - 1:
                raise ValueError('Missing Git rename source')
            paths.append(records[index])
            index += 1
    paths = sorted(set(paths))
    if len(paths) > MAX_SOURCE_PATHS:
        raise ValueError('Changed path count exceeds checkpoint bound')
    binding = hashlib.sha256()
    remaining = MAX_SOURCE_BYTES
    inspection_required = False
    for encoded_path in paths:
        # Length framing avoids concatenation ambiguity; the path never leaves a hash.
        binding.update(len(encoded_path).to_bytes(8, 'big'))
        binding.update(encoded_path)
        try:
            name = encoded_path.decode('utf-8', errors='strict')
            path = plain(project / relative(name))
        except (ValueError, UnicodeError):
            binding.update(b'UNREADABLE_OR_SENSITIVE')
            inspection_required = True
            continue
        if not path.exists():
            binding.update(b'ABSENT')
            continue
        meta = path.lstat()
        if not stat.S_ISREG(meta.st_mode):
            binding.update(b'NONREGULAR')
            inspection_required = True
            continue
        if meta.st_size > remaining:
            raise ValueError('Changed content exceeds checkpoint bound')
        # Hash only permitted source paths. No raw content is persisted or printed.
        with path.open('rb') as stream:
            content = stream.read(remaining + 1)
        if len(content) > remaining:
            raise ValueError('Changed content exceeds checkpoint bound')
        remaining -= len(content)
        binding.update(b'FILE')
        binding.update(len(content).to_bytes(8, 'big'))
        binding.update(hashlib.sha256(content).digest())
    return {'head': head, 'status_sha256': digest(status), 'index_sha256': digest(index_status), 'content_sha256': binding.hexdigest(),
            'dirty': bool(status), 'inspection_required': inspection_required}


def validate_plan(plan):
    fields(plan, {'tasks', 'next_actions'})
    if not isinstance(plan['tasks'], list) or not 1 <= len(plan['tasks']) <= 256:
        raise ValueError('Expected 1..256 tasks')
    ids = set()
    for task in plan['tasks']:
        fields(task, {'id', 'status'})
        if not isinstance(task['id'], str) or re.fullmatch('[A-Za-z0-9_-]{1,80}', task['id']) is None or task['id'] in ids:
            raise ValueError('Invalid or duplicate task ID')
        ids.add(task['id'])
        if not isinstance(task['status'], str) or task['status'] not in STATUSES:
            raise ValueError('Unknown task status')
    if not isinstance(plan['next_actions'], list) or len(plan['next_actions']) > 64:
        raise ValueError('Expected at most 64 next actions')
    for action in plan['next_actions']:
        bounded_text(action)
    return plan


def output_path(project, out):
    project = plain(project)
    out = plain(out)
    # Explicit output and a dedicated local directory; never writes global policy.
    if out.parent != project / '.guardian-state' or out.suffix != '.json':
        raise ValueError('Output must be PROJECT/.guardian-state/NAME.json')
    relative(out.name)
    return project, out


def load_checkpoint(path):
    value = read_json(path)
    fields(value, {'payload', 'sha256'})
    payload = value['payload']
    fields(payload, {'schema_version', 'sequence', 'previous_sha256', 'recorded_at', 'signal', 'source', 'plan', 'evidence', 'constraints'})
    if type(payload['schema_version']) is not int or payload['schema_version'] != SCHEMA_VERSION:
        raise ValueError('Unknown checkpoint schema')
    if type(payload['sequence']) is not int or not 1 <= payload['sequence'] <= 1_000_000:
        raise ValueError('Invalid sequence')
    if payload['previous_sha256'] is not None and re.fullmatch('[0-9a-f]{64}', str(payload['previous_sha256'])) is None:
        raise ValueError('Invalid predecessor checksum')
    bounded_text(payload['recorded_at'], 40)
    policy = payload['constraints'].get('release_policy') if isinstance(payload['constraints'], dict) else None
    if not isinstance(payload['signal'], str) or payload['signal'] not in SIGNALS or encode(payload['constraints']) != encode(constraints_for(policy)):
        raise ValueError('Unknown signal or policy')
    fields(payload['source'], {'head', 'status_sha256', 'index_sha256', 'content_sha256', 'dirty', 'inspection_required'})
    if re.fullmatch('[0-9a-f]{40,64}', str(payload['source']['head'])) is None or any(re.fullmatch('[0-9a-f]{64}', str(payload['source'][key])) is None for key in ('status_sha256', 'index_sha256', 'content_sha256')) or any(type(payload['source'][key]) is not bool for key in ('dirty', 'inspection_required')):
        raise ValueError('Invalid source binding')
    validate_plan(payload['plan'])
    if not isinstance(payload['evidence'], list) or len(payload['evidence']) > 256:
        raise ValueError('Evidence list exceeds bound')
    seen = set()
    for item in payload['evidence']:
        fields(item, {'path', 'sha256'})
        relative(item['path'])
        if item['path'] in seen or re.fullmatch('[0-9a-f]{64}', str(item['sha256'])) is None:
            raise ValueError('Invalid or duplicate evidence')
        seen.add(item['path'])
    if value['sha256'] != digest(encode(payload)):
        raise ValueError('Checkpoint checksum mismatch')
    return value


def save(project, out, plan, evidence=(), signal='milestone', update=False, accept_revision_change=False, release_policy=None):
    project, out = output_path(project, out)
    validate_plan(plan)
    if release_policy is not None:
        constraints_for(release_policy)
    if signal not in SIGNALS or len(evidence) > 256 or len(set(evidence)) != len(evidence):
        raise ValueError('Invalid signal or evidence list')
    out.parent.mkdir(exist_ok=True)
    lock = plain(out.with_suffix('.lock'))
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    temp = None
    try:
        os.close(fd)
        previous = load_checkpoint(out) if out.exists() else None
        if update != bool(previous):
            raise ValueError('Create requires absent checkpoint; update requires existing checkpoint')
        selected_policy = release_policy if release_policy is not None else (
            previous['payload']['constraints']['release_policy'] if previous else 'unspecified')
        constraints = constraints_for(selected_policy)
        source = git_snapshot(project)
        if previous and previous['payload']['source']['head'] != source['head'] and not accept_revision_change:
            raise ValueError('Source revision changed; inspect resume, then explicitly accept new revision')
        if previous and previous['payload']['sequence'] >= 1_000_000:
            raise ValueError('Checkpoint sequence exhausted; choose a new explicit checkpoint')
        payload = {'schema_version': SCHEMA_VERSION, 'sequence': previous['payload']['sequence'] + 1 if previous else 1,
                   'previous_sha256': previous['sha256'] if previous else None,
                   'recorded_at': datetime.now(timezone.utc).isoformat(), 'signal': signal,
                   'source': source, 'plan': plan,
                   'evidence': [{'path': p, 'sha256': evidence_hash(project, p)} for p in evidence],
                   'constraints': constraints}
        value = {'payload': payload, 'sha256': digest(encode(payload))}
        data = encode(value) + b'\n'
        if len(data) > MAX_BYTES:
            raise ValueError('Checkpoint exceeds bound')
        with tempfile.NamedTemporaryFile(prefix='.checkpoint-', dir=out.parent, delete=False) as stream:
            temp = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, out)
        return value
    finally:
        if temp and temp.exists():
            temp.unlink()
        lock.unlink()


def inspect(project, out):
    project, out = output_path(project, out)
    saved = load_checkpoint(out)
    payload = saved['payload']
    source = git_snapshot(project)
    evidence_failures = 0
    for item in payload['evidence']:
        try:
            evidence_failures += evidence_hash(project, item['path']) != item['sha256']
        except (ValueError, OSError):
            evidence_failures += 1
    revision_changed = source['head'] != payload['source']['head']
    workspace_changed = any(source[key] != payload['source'][key] for key in ('status_sha256', 'index_sha256', 'content_sha256'))
    source_inspection_required = source['inspection_required'] or payload['source']['inspection_required']
    return {'schema_version': SCHEMA_VERSION, 'sequence': payload['sequence'], 'signal': payload['signal'],
            'revision_changed': revision_changed, 'workspace_changed': workspace_changed,
            'evidence_failures': evidence_failures, 'evidence_count': len(payload['evidence']),
            'tasks': {s: sum(t['status'] == s for t in payload['plan']['tasks']) for s in sorted(STATUSES)},
            'next_action_count': len(payload['plan']['next_actions']),
            'release_policy': payload['constraints']['release_policy'],
            'source_inspection_required': source_inspection_required,
            'reinspection_required': revision_changed or workspace_changed or bool(evidence_failures) or source_inspection_required,
            'completion_certified': False, 'automatic_wakeup': False}


def classify_error(text):
    """Heuristic signal only; raw stderr is never persisted or echoed."""
    text = text[:16000].lower()
    if not any(p in text for p in ('usage limit', 'quota exceeded', 'rate limit', 'usage_limit_reached')):
        return 'manual_pause'
    if 'weekly' in text or 'week' in text:
        return 'quota_weekly'
    if '5h' in text or '5 hour' in text or 'five hour' in text:
        return 'quota_5h'
    return 'quota_unspecified'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('create', 'update', 'status', 'resume', 'classify-error'))
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--evidence', action='append', default=[])
    parser.add_argument('--signal', choices=sorted(SIGNALS), default='milestone')
    parser.add_argument('--accept-revision-change', action='store_true')
    parser.add_argument('--release-policy', choices=sorted(RELEASE_POLICIES),
                        help='Explicit policy change; omission preserves an existing checkpoint policy')
    args = parser.parse_args(argv)
    try:
        if args.command == 'classify-error':
            import sys
            print(json.dumps({'signal': classify_error(sys.stdin.read(16001)), 'heuristic_only': True}))
            return 0
        if args.command in ('create', 'update'):
            if args.plan is None:
                raise ValueError('Explicit --plan required')
            save(args.project, args.out, read_json(args.plan), args.evidence, args.signal,
                 args.command == 'update', args.accept_revision_change, args.release_policy)
        result = inspect(args.project, args.out)
        print(json.dumps(result, sort_keys=True))
        return 2 if args.command == 'resume' and result['reinspection_required'] else 0
    except (ValueError, OSError, subprocess.SubprocessError):
        # Do not echo potentially sensitive filesystem paths or subprocess output.
        print(json.dumps({'error': 'Checkpoint operation rejected; inspect schema, paths, source binding, and lock locally.'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
