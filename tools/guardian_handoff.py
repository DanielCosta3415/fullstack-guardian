"""Optional data-only intake for native handoffs; never an agent interceptor.

The supervisor supplies observed checks separately from the producer document.
Checksums bind content, not identity or authority. No code in an artifact runs.
Logical run labels must be synthetic, not account IDs or native session tokens.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

try:
    from .guardian_checkpoint import evidence_hash, read_json
except ImportError:
    from guardian_checkpoint import evidence_hash, read_json

FIELDS = {'schema_version', 'run', 'task', 'revision', 'contract_sha256', 'producer',
          'consumer', 'obligations', 'artifacts', 'checks', 'unknowns', 'status'}
HASH = re.compile(r'[a-f0-9]{64}')
LABEL = re.compile(r'[A-Za-z][A-Za-z0-9_.:-]{0,127}')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def _label(value):
    if not isinstance(value, str) or not LABEL.fullmatch(value):
        raise ValueError('Use a bounded synthetic label')
    return value


def _labels(values, nonempty=False):
    if not isinstance(values, list) or len(values) > 128 or (nonempty and not values):
        raise ValueError('Invalid label list')
    for value in values:
        _label(value)
    if len(set(values)) != len(values):
        raise ValueError('Duplicate label')


def validate_handoff(value):
    if not isinstance(value, dict) or set(value) != FIELDS or type(value['schema_version']) is not int or value['schema_version'] != 1:
        raise ValueError('Unknown/missing handoff fields')
    for key in ('run', 'task', 'producer', 'consumer'):
        _label(value[key])
    if value['producer'] == value['consumer'] or value['status'] != 'produced':
        raise ValueError('Producer cannot accept or verify its own handoff')
    if not isinstance(value['revision'], str) or not re.fullmatch(r'[a-f0-9]{40,64}', value['revision']):
        raise ValueError('Invalid revision')
    if not isinstance(value['contract_sha256'], str) or not HASH.fullmatch(value['contract_sha256']):
        raise ValueError('Invalid contract digest')
    _labels(value['obligations'], nonempty=True)
    _labels(value['unknowns'])
    for key, fields in (('artifacts', {'path', 'sha256', 'obligations'}),
                        ('checks', {'id', 'artifact_sha256', 'obligations'})):
        records = value[key]
        if not isinstance(records, list) or not 1 <= len(records) <= 128:
            raise ValueError('Artifacts and checks required')
        names = set()
        for record in records:
            if not isinstance(record, dict) or set(record) != fields:
                raise ValueError('Invalid artifact/check fields')
            name = record['path' if key == 'artifacts' else 'id']
            if not isinstance(name, str) or name in names:
                raise ValueError('Duplicate artifact/check')
            names.add(name)
            if key == 'checks':
                _label(name)
            else:
                try:
                    from .guardian_checkpoint import relative
                except ImportError:
                    from guardian_checkpoint import relative
                relative(name)
            _labels(record['obligations'], nonempty=True)
            if not set(record['obligations']) <= set(value['obligations']):
                raise ValueError('Artifact/check names an unknown obligation')
            sha = record['sha256' if key == 'artifacts' else 'artifact_sha256']
            if not isinstance(sha, str) or not HASH.fullmatch(sha):
                raise ValueError('Invalid artifact/check digest')
    return value


def inspect_handoff(project, value, *, run, task, expected_producer, expected_consumer,
                    revision, contract_sha256, obligations, required_checks, observations):
    """Independent caller context is mandatory; producer claims never fill it."""
    validate_handoff(value)
    _labels(obligations, nonempty=True)
    issues = []
    for key, expected in (('run', run), ('task', task), ('producer', expected_producer),
                          ('consumer', expected_consumer), ('revision', revision), ('contract_sha256', contract_sha256)):
        if value[key] != expected:
            issues.append('context:' + key)
    if set(value['obligations']) != set(obligations):
        issues.append('obligation_coverage')
    # Reuse the closed record parser, but never derive required checks from the
    # producer. The independent supervisor fixes this set before accepting work.
    validate_handoff(dict(value, checks=required_checks))
    expected_checks = {check['id']: check for check in required_checks}
    supplied_checks = {check['id']: check for check in value['checks']}
    if expected_checks != supplied_checks:
        issues.append('required_check_set_mismatch')
    if not isinstance(observations, list) or len(observations) > 128:
        raise ValueError('Supervisor observations required')
    observed = {}
    for row in observations:
        if not isinstance(row, dict) or set(row) != {'id', 'run', 'task', 'revision', 'artifact_sha256', 'passed', 'observer'}:
            raise ValueError('Invalid observed check')
        _label(row['id']); _label(row['observer'])
        if row['id'] in observed or type(row['passed']) is not bool:
            raise ValueError('Duplicate/invalid observed check')
        observed[row['id']] = row
    actual = set()
    for artifact in value['artifacts']:
        try:
            current = evidence_hash(Path(project).absolute(), artifact['path'])
        except (ValueError, OSError):
            current = None
        if current != artifact['sha256']:
            issues.append('artifact_drift:' + artifact['path'])
        else:
            actual.add(current)
    covered = set()
    for check in required_checks:
        row = observed.get(check['id'])
        if (row is None or row['run'] != run or row['task'] != task or row['revision'] != revision or
                row['artifact_sha256'] != check['artifact_sha256'] or
                row['artifact_sha256'] not in actual or not row['passed'] or
                row['observer'] == value['producer']):
            issues.append('check_not_independently_observed:' + check['id'])
        else:
            # A check must refer to an artifact covering the SAME obligation.
            artifact_obligations = {o for a in value['artifacts'] if a['sha256'] == row['artifact_sha256'] for o in a['obligations']}
            covered.update(set(check['obligations']) & artifact_obligations)
    if set(obligations) - covered:
        issues.append('unchecked_obligations')
    if value['unknowns']:
        issues.append('unresolved_unknowns')
    return {'schema_version': 1, 'handoff_sha256': digest(value),
            'observations_sha256': digest(observations), 'status': 'checked' if not issues else 'produced',
            'issues': sorted(set(issues)), 'authenticated': False,
            'native_interception': False, 'authorization_granted': False}


def consume_handoff(project, value, *, consumer, decision, reason, **context):
    """A distinct consumer makes an explicit decision after fresh inspection."""
    _label(consumer); _label(reason)
    if consumer != value.get('consumer') or consumer == value.get('producer') or decision not in ('accept', 'reject'):
        raise ValueError('Distinct designated consumer and explicit decision required')
    checked = inspect_handoff(project, value, **context)
    if decision == 'accept' and checked['issues']:
        raise ValueError('Cannot accept incomplete or stale handoff')
    return {**checked, 'status': 'accepted' if decision == 'accept' else 'rejected',
            'consumer': consumer, 'reason': reason, 'acceptance_is_self_reported': True,
            'notice': 'Fresh file/check correlation, not authenticated identity, semantic correctness or release approval.'}


def invalidated_tasks(tasks, revoked_evidence):
    """Transitive revocation; reject unknown dependencies and cycles first."""
    if not isinstance(tasks, list) or not tasks or len(tasks) > 256:
        raise ValueError('Bounded task graph required')
    _labels(revoked_evidence)
    by_id = {}
    for task in tasks:
        if not isinstance(task, dict) or set(task) != {'id', 'depends_on', 'evidence'}:
            raise ValueError('Invalid dependency task')
        _label(task['id']); _labels(task['depends_on']); _labels(task['evidence'])
        if task['id'] in by_id:
            raise ValueError('Duplicate task')
        by_id[task['id']] = task
    done, visiting = set(), set()
    def visit(key):
        if key not in by_id or key in visiting:
            raise ValueError('Unknown dependency or cycle')
        if key in done:
            return
        visiting.add(key)
        for dependency in by_id[key]['depends_on']:
            visit(dependency)
        visiting.remove(key); done.add(key)
    for key in by_id:
        visit(key)
    affected = {key for key, task in by_id.items() if set(task['evidence']) & set(revoked_evidence)}
    for _ in range(len(tasks)):
        expanded = affected | {key for key, task in by_id.items() if set(task['depends_on']) & affected}
        if expanded == affected:
            break
        affected = expanded
    return {'invalidated': sorted(affected), 'remaining': sorted(set(by_id) - affected), 'automatic_execution': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('inspect', 'consume'))
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--handoff', type=Path, required=True)
    parser.add_argument('--context', type=Path, required=True, help='Independent supervisor context/observations')
    parser.add_argument('--consumer'); parser.add_argument('--decision', choices=('accept', 'reject'))
    parser.add_argument('--reason')
    args = parser.parse_args()
    try:
        value, context = read_json(args.handoff), read_json(args.context)
        if set(context) != {'run', 'task', 'expected_producer', 'expected_consumer', 'revision', 'contract_sha256', 'obligations', 'required_checks', 'observations'}:
            raise ValueError('Closed supervisor context required')
        result = (inspect_handoff(args.project, value, **context) if args.command == 'inspect' else
                  consume_handoff(args.project, value, consumer=args.consumer, decision=args.decision, reason=args.reason, **context))
        print(json.dumps(result, indent=2))
        return 0 if not result['issues'] and result['status'] != 'rejected' else 2
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(json.dumps({'error': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
