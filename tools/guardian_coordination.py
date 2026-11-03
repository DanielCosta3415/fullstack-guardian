"""Small advisory teams, conflict-free waves and privacy-minimal observations.

No spawn, model choice, authorization or billing inference is performed here.
The principal remains responsible for semantic coverage and actual delegation.
"""
from __future__ import annotations
import math
import re
import statistics


def _ids(values, field, *, empty=True):
    if not isinstance(values, list) or len(values) > 256 or (not empty and not values):
        raise ValueError('Invalid ' + field)
    if any(not isinstance(x, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{0,127}', x) for x in values) or len(set(values)) != len(values):
        raise ValueError('Invalid/duplicate ' + field)


def recommend_team(obligations, candidates, *, mandatory_roles=(), max_agents=8):
    """Deterministic bounded set-cover heuristic; never silently drop coverage."""
    _ids(obligations, 'obligations', empty=False)
    if not isinstance(mandatory_roles, (list, tuple)):
        raise ValueError('Mandatory roles must be an explicit list or tuple')
    mandatory_roles = list(mandatory_roles)
    _ids(list(mandatory_roles), 'mandatory_roles')
    if type(max_agents) is not int or not 1 <= max_agents <= 39:
        raise ValueError('Agent budget must be 1..39')
    if not isinstance(candidates, list) or not candidates or len(candidates) > 39:
        raise ValueError('Bounded candidate inventory required')
    known = {}
    for candidate in candidates:
        if not isinstance(candidate, dict) or set(candidate) != {'id', 'covers', 'available'}:
            raise ValueError('Invalid candidate schema')
        _ids([candidate['id']], 'role'); _ids(candidate['covers'], 'covers')
        if candidate['id'] in known or not set(candidate['covers']) <= set(obligations) or type(candidate['available']) is not bool:
            raise ValueError('Invalid candidate coverage/availability')
        known[candidate['id']] = candidate
    selected = list(mandatory_roles)
    blocked = [key for key in selected if key not in known or not known[key]['available']]
    if blocked:
        return {'selected': [], 'blocked_roles': sorted(blocked), 'uncovered': list(obligations), 'within_budget': False, 'proposal_only': True}
    remaining = set(obligations) - {o for key in selected for o in known[key]['covers']}
    while remaining:
        options = [c for c in candidates if c['available'] and c['id'] not in selected and set(c['covers']) & remaining]
        if not options:
            break
        best = min(options, key=lambda c: (-len(set(c['covers']) & remaining), c['id']))
        selected.append(best['id']); remaining -= set(best['covers'])
    # Remove redundant workers, never mandatory gates. This is a heuristic,
    # not a proof of globally optimal cost or complete semantic interpretation.
    for key in reversed(selected[:]):
        if key not in mandatory_roles and set(obligations) <= {o for k in selected if k != key for o in known[k]['covers']}:
            selected.remove(key)
    return {'selected': selected, 'blocked_roles': [], 'uncovered': sorted(remaining),
            'within_budget': len(selected) <= max_agents and not remaining,
            'budget_refinement_required': len(selected) > max_agents,
            'proposal_only': True, 'primary_semantic_review_required': True,
            'method': 'bounded_greedy_with_redundancy_pruning', 'model_policy': 'inherit'}


def _overlap(left, right):
    left = left[:-3] if left.endswith('/**') else left
    right = right[:-3] if right.endswith('/**') else right
    return left == right or left.startswith(right + '/') or right.startswith(left + '/')


def execution_waves(tasks, max_parallel=4):
    """Schedule a validated DAG; declared write overlaps never share a wave."""
    try:
        from .guardian_contracts import validate_task_contract
    except ImportError:
        from guardian_contracts import validate_task_contract
    if type(max_parallel) is not int or not 1 <= max_parallel <= 39 or not isinstance(tasks, list) or not 1 <= len(tasks) <= 256:
        raise ValueError('Bounded tasks/parallelism required')
    by_id = {}
    for task in tasks:
        if not isinstance(task, dict) or set(task) != {'id', 'depends_on', 'contract'}:
            raise ValueError('Invalid scheduling task')
        _ids([task['id']], 'task'); _ids(task['depends_on'], 'dependencies')
        if task['id'] in by_id:
            raise ValueError('Duplicate task')
        validate_task_contract(task)
        by_id[task['id']] = task
    if any(not set(t['depends_on']) <= set(by_id) for t in tasks):
        raise ValueError('Missing dependency')
    done, waves = set(), []
    while len(done) < len(tasks):
        ready = sorted(k for k, task in by_id.items() if k not in done and set(task['depends_on']) <= done)
        if not ready:
            raise ValueError('Dependency cycle')
        wave, paths = [], []
        for key in ready:
            own = by_id[key]['contract']['allowed_paths']
            if len(wave) < max_parallel and not any(_overlap(a.casefold(), b.casefold()) for a in own for b in paths):
                wave.append(key); paths.extend(own)
        done.update(wave); waves.append(wave)
    return {'waves': waves, 'execution_performed': False, 'write_conflicts_parallelized': False}


def summarize_metrics(records):
    """Closed numeric ledger. Missing usage/cost stays unknown, never zero."""
    if not isinstance(records, list) or len(records) > 10000:
        raise ValueError('Bounded metrics required')
    ids = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != {'task', 'obligations', 'elapsed_seconds', 'calls', 'rework', 'accepted', 'tokens', 'cost_minor', 'cost_kind', 'currency'}:
            raise ValueError('Closed numeric metric schema required; no prompts or raw output')
        _ids([record['task']], 'task'); _ids(record['obligations'], 'obligations', empty=False)
        if record['task'] in ids:
            raise ValueError('Duplicate task metric')
        ids.add(record['task'])
        if type(record['elapsed_seconds']) not in (int, float) or not math.isfinite(record['elapsed_seconds']) or record['elapsed_seconds'] < 0:
            raise ValueError('Invalid elapsed time')
        for field in ('calls', 'rework'):
            if type(record[field]) is not int or record[field] < 0:
                raise ValueError('Invalid call/rework count')
        if type(record['accepted']) is not bool:
            raise ValueError('Invalid acceptance observation')
        for field in ('tokens', 'cost_minor'):
            if record[field] is not None and (type(record[field]) is not int or record[field] < 0):
                raise ValueError('Invalid usage/cost')
        if record['cost_kind'] not in ('unknown', 'estimate', 'billed'):
            raise ValueError('Cost must distinguish estimation and billing')
        if record['cost_kind'] == 'unknown':
            if record['cost_minor'] is not None or record['currency'] is not None:
                raise ValueError('Unknown cost cannot carry an amount')
        elif record['cost_minor'] is None or not isinstance(record['currency'], str) or not re.fullmatch('[A-Z]{3}', record['currency']):
            raise ValueError('Known cost requires amount and explicit currency')
    obligations = {o for r in records for o in r['obligations']}
    accepted = {o for o in obligations if all(r['accepted'] for r in records if o in r['obligations'])}
    return {'tasks': len(records), 'accepted_tasks': sum(r['accepted'] for r in records),
            'accepted_obligations': len(accepted), 'calls': sum(r['calls'] for r in records),
            'rework': sum(r['rework'] for r in records),
            'median_elapsed_seconds': statistics.median([r['elapsed_seconds'] for r in records]) if records else None,
            'tokens': sum(r['tokens'] for r in records) if records and all(r['tokens'] is not None for r in records) else None,
            'costs': [{'kind': kind, 'currency': currency, 'minor': sum(r['cost_minor'] for r in records if r['cost_kind'] == kind and r['currency'] == currency)}
                      for kind, currency in sorted({(r['cost_kind'], r['currency']) for r in records if r['cost_kind'] != 'unknown'})],
            'unknown_cost_tasks': sum(r['cost_kind'] == 'unknown' for r in records),
            'observations_authenticated': False, 'model_policy': 'inherit', 'raw_content_stored': False}


def main():
    import argparse
    import json
    from pathlib import Path
    try:
        from .guardian_checkpoint import read_json
    except ImportError:
        from guardian_checkpoint import read_json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('team', 'waves', 'metrics'))
    parser.add_argument('--input', type=Path, required=True)
    args = parser.parse_args()
    try:
        value = read_json(args.input)
        if args.command == 'team':
            if not isinstance(value, dict) or set(value) != {'obligations', 'candidates', 'mandatory_roles', 'max_agents'}:
                raise ValueError('Closed team input required')
            result = recommend_team(**value)
        elif args.command == 'waves':
            if not isinstance(value, dict) or set(value) != {'tasks', 'max_parallel'}:
                raise ValueError('Closed wave input required')
            result = execution_waves(**value)
        else:
            result = summarize_metrics(value)
        print(json.dumps(result, indent=2))
        return 0 if result.get('within_budget', True) else 2
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(json.dumps({'error': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
