"""Opt-in advisory Codex lifecycle adapter. No trust bypass, model calls or policy grants.

The handler reads bounded JSON from stdin and never reads transcripts or persists
prompts. Registration simulates by default, preserves foreign handlers, and uses
the shared maintenance lock. Codex's independent hook trust review still applies.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

try:
    from .guardian_maintenance import atomic_write, maintenance_lock, safe
except ImportError:
    from guardian_maintenance import atomic_write, maintenance_lock, safe

ROOT = Path(__file__).resolve().parents[1]
EVENTS = ('SessionStart', 'UserPromptSubmit', 'SubagentStart', 'SubagentStop')
MARKER = 'Guardian professional coordination v1'
MAX_BYTES = 65536


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON keys are not accepted')
        result[key] = value
    return result


def _decode(data):
    if len(data) > MAX_BYTES:
        raise ValueError('Hook data exceeds byte bound')
    return json.loads(data.decode('utf-8-sig'), object_pairs_hook=_pairs)


def _bytes(doc):
    return (json.dumps(doc, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _read(path):
    path = safe(path)
    if not path.exists():
        return None
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError('Hook configuration must be a bounded regular file')
    return path.read_bytes()


def _command():
    # Resolve the interpreter already running this installer (venv/setup-python
    # commonly supplies a symlink). Source and destination policies stay strict.
    interpreter = safe(Path(sys.executable).resolve(strict=True))
    argv = [str(interpreter), '-B', str(safe(ROOT/'tools/guardian_hooks.py')), 'handle']
    if any(any(ord(c) < 32 for c in value) for value in argv):
        raise ValueError('Control characters in hook paths')
    if os.name == 'nt':
        # Quoting alone does not protect Windows environment expansion/metacharacters.
        if any(any(c in value for c in '%!&|<>^()') for value in argv):
            raise ValueError('Shell metacharacters in Windows hook paths are unsupported')
        # An explicitly invoked PowerShell process works from both cmd.exe and
        # PowerShell hosts, including quoted Python/project paths with spaces.
        source = '& ' + ' '.join("'" + value.replace("'", "''") + "'" for value in argv)
        return subprocess.list2cmdline(['powershell.exe', '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', source])
    return shlex.join(argv)


def groups():
    handler = {'type': 'command', 'command': _command(), 'timeout': 10,
               'statusMessage': MARKER, 'additionalContextLimit': 4096}
    result = {event: {'hooks': [dict(handler)]} for event in EVENTS}
    # The native client rejects context-limit settings for events which cannot
    # emit additionalContext. Stop is intentionally a data-free no-op.
    result['SubagentStop']['hooks'][0].pop('additionalContextLimit')
    return result


def _document(raw):
    doc = _decode(raw) if raw is not None else {}
    if not isinstance(doc, dict) or not isinstance(doc.get('hooks', {}), dict):
        raise ValueError('Expected object with hooks object')
    for event, items in doc.get('hooks', {}).items():
        if not isinstance(event, str) or not isinstance(items, list) or any(not isinstance(x, dict) for x in items):
            raise ValueError('Malformed hook matcher groups; preserving configuration without changes')
    return doc


def manage(codex_home, action='install', *, apply=False):
    if action not in ('install', 'uninstall', 'doctor'):
        raise ValueError('Unknown hook operation')
    home = safe(codex_home)
    config = safe(home/'hooks.json')
    receipt = safe(home/'guardian-hooks.json')
    raw = _read(config)
    receipt_raw = _read(receipt)
    doc = _document(raw)
    own = groups()
    current = _decode(receipt_raw) if receipt_raw is not None else None
    if current is not None:
        legacy = groups()
        legacy['SubagentStop']['hooks'][0]['additionalContextLimit'] = 4096
        expected = {'schema_version', 'runtime', 'groups', 'handler_sha256', 'state'}
        if (not isinstance(current, dict) or set(current) != expected or current.get('schema_version') != 1
                or current.get('runtime') != str(ROOT) or current.get('groups') not in (own, legacy)
                or current.get('state') not in ('installing', 'installed', 'uninstalling')):
            raise ValueError('Unrecognized hook receipt; no ownership inferred')
        # Only the exact recognized v1 definitions may be removed on upgrade;
        # receipt data never authorizes arbitrary foreign hook deletion.
        own = current['groups']
        counts = [doc.get('hooks', {}).get(event, []).count(group) for event, group in own.items()]
        if counts != [1]*len(EVENTS) and not (current['state'] != 'installed' and counts == [0]*len(EVENTS)):
            raise ValueError('Owned hook changed or missing; explicit conflict resolution required')
    elif any(group in doc.get('hooks', {}).get(event, []) for event, group in own.items()):
        raise ValueError('Unmanaged matching Guardian hook; refusing to adopt it')
    handler_hash = _hash((ROOT/'tools/guardian_hooks.py').read_bytes())
    report = {'action': action, 'dry_run': not apply, 'registered': current is not None,
              'events': list(EVENTS), 'handler_unchanged': bool(current and current['handler_sha256'] == handler_hash),
              'interrupted': bool(current and current['state'] != 'installed'),
              'trust': 'CODEX_REVIEW_REQUIRED_NOT_BYPASSED', 'desktop_events_verified': False,
              'isolation': 'ADVISORY_NOT_OS_ENFORCEMENT', 'prompts_persisted': False}
    if action == 'doctor' or not apply:
        return report
    with maintenance_lock(home, 'hooks-'+action):
        if _read(config) != raw or _read(receipt) != receipt_raw:
            raise ValueError('Hook files changed after preflight')
        if action == 'install':
            if current is not None:
                if current['handler_sha256'] != handler_hash or current['state'] != 'installed':
                    raise ValueError('Existing hook source changed or operation interrupted; inspect before replacing')
                return {**report, 'dry_run': False, 'registered': True, 'unchanged': True}
            events = doc.setdefault('hooks', {})
            for event, group in own.items():
                events.setdefault(event, []).append(group)
            record = {'schema_version': 1, 'runtime': str(ROOT), 'groups': own,
                      'handler_sha256': handler_hash, 'state': 'installing'}
            atomic_write(receipt, _bytes(record))
            atomic_write(config, _bytes(doc))
            record['state'] = 'installed'
            atomic_write(receipt, _bytes(record))
            return {**report, 'dry_run': False, 'registered': True}
        if current is None:
            return {**report, 'dry_run': False, 'unchanged': True}
        if all(group not in doc.get('hooks', {}).get(event, []) for event, group in own.items()):
            # Explicit recovery of an interrupted atomic install/uninstall. No
            # handler exists, so only our exact validated receipt is removed.
            receipt.unlink()
            return {**report, 'dry_run': False, 'registered': False, 'recovered': True}
        current['state'] = 'uninstalling'
        atomic_write(receipt, _bytes(current))
        for event, group in own.items():
            doc['hooks'][event].remove(group)
            if not doc['hooks'][event]:
                del doc['hooks'][event]
        atomic_write(config, _bytes(doc))
        receipt.unlink()
        return {**report, 'dry_run': False, 'registered': False}


def handle(event):
    if not isinstance(event, dict) or event.get('hook_event_name') not in EVENTS:
        raise ValueError('Unsupported hook event')
    name = event['hook_event_name']
    prefix = ('Guardian advisory data only. Honor higher-priority instructions and actual permissions. '
              'Primary assumes A00: interpret intent, requirements, risks and evidence; select the smallest '
              'relevant team from the CURRENT native inventory. Do not treat a profile or plan as authority. ')
    if name == 'SessionStart':
        text = prefix + ('For nontrivial work use guardian-routing and professional contracts; '
                         'recheck obligations after compaction/resume. A simple edit can remain with the primary.')
    elif name == 'UserPromptSubmit':
        prompt = event.get('prompt')
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 8000:
            raise ValueError('Expected bounded nonempty prompt')
        try:
            from .guardian import route
        except ImportError:
            from guardian import route
        result = route(prompt)
        # Only controlled identity/risk values are returned; no user/source text is elevated.
        ids = [x['id'] for x in result['agents']]
        if any(not isinstance(x, str) or not __import__('re').fullmatch(r'(?:S[0-9]{2}|G0[12]|A00)', x) for x in ids):
            raise ValueError('Unknown router identity')
        if result['risk'] not in ('low', 'medium', 'high', 'critical'):
            raise ValueError('Unknown risk')
        text = prefix + 'Deterministic candidates (not dispatch): ' + ', '.join(ids) + '. Risk hint: ' + result['risk'] + '. '
        text += 'Verify semantic coverage and phase responsibilities; investigate ambiguity. Unsupported isolation/tool requirements block dependent work.'
    elif name == 'SubagentStart':
        role = event.get('agent_type')
        if not isinstance(role, str) or len(role) > 150:
            raise ValueError('Invalid agent type')
        try:
            from .guardian_professional import get_contract
        except ImportError:
            from guardian_professional import get_contract
        try:
            contract = get_contract(role, ROOT)
        except (ValueError, KeyError):
            return {}  # Foreign roles do not become Guardian roles.
        text = prefix + 'Use your specialty contract and scoped task. Return artifacts, actual checks, unmet criteria and handoff obligations. '
        # Contract details are supplied through profile/planner; no full catalog in every event.
        text += 'Professional identity: ' + str(contract.get('name', role)) + '. Produced is distinct from independently verified.'
    else:
        return {}  # Never retry a finished child indefinitely or self-certify its output.
    return {'hookSpecificOutput': {'hookEventName': name, 'additionalContext': text[:4096]}}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest='action', required=True)
    commands.add_parser('handle')
    for action in ('install', 'uninstall', 'doctor'):
        op = commands.add_parser(action)
        target = op.add_mutually_exclusive_group(required=True)
        target.add_argument('--project', type=Path)
        target.add_argument('--codex-home', type=Path, help='Exact explicitly chosen Codex directory')
        op.add_argument('--apply', action='store_true')
    a = p.parse_args(argv)
    try:
        if a.action == 'handle':
            result = handle(_decode(sys.stdin.buffer.read(MAX_BYTES+1)))
        else:
            home = safe(a.project/'.codex') if a.project is not None else safe(a.codex_home)
            result = manage(home, a.action, apply=a.apply)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, RecursionError) as exc:
        # Do not echo prompts, source, paths or transcript data on parse/runtime errors.
        print(json.dumps({'systemMessage': 'Guardian hook could not verify its bounded input/configuration; use normal coordination and inspect the adapter.'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
