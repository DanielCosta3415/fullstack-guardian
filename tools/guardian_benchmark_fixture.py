#!/usr/bin/env python3
"""Generate a disposable, independent Python benchmark project with external grader.

No Codex invocation or network; creates NEW path only. The test grader lives
outside the model workspace so the model cannot change its scoring rules.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

SOURCE = {
    "validation.py": '''"""Input normalization with intentionally missing validation."""


def normalize_customer(data):
    return data
''',
    "money.py": '''"""Integer-minor-unit financial calculation (intentionally flawed)."""


def sum_minor_units(amount, fee):
    return float(amount) + float(fee)
''',
    "events.py": '''"""Ordered idempotent event processing (intentionally flawed)."""


def distinct_events(events):
    return list(events)
''',
    "README.md": """# Guardian controlled benchmark fixture

Three deliberately flawed pure-Python modules. All tests are external to this
project. Do not open or write files outside this workspace while solving.
""",
}
CASES = {
    "schema_version": 1,
    "dataset_version": "guardian-python-contracts-2",
    "split": "holdout",
    "cases": [
        {"case_id": "validation", "prompt": "Implement normalize_customer(data) in validation.py. Accept only dict input with nonempty string 'name', strip surrounding whitespace and return a fresh dict with normalized name. Raise ValueError for missing/blank names and TypeError for non-dict inputs. Leave unrelated files untouched.", "checks": ["main"]},
        {"case_id": "money", "prompt": "Fix sum_minor_units(amount, fee) in money.py. Both arguments must be nonnegative Python ints in minor currency units (bool is invalid); return their exact integer sum. Raise TypeError for non-int, ValueError for negatives, never convert via floating point. Keep the public API.", "checks": ["main"]},
        {"case_id": "events", "prompt": "Fix distinct_events(events) in events.py. Accept a list of nonempty string event IDs, return first-seen values in stable order with duplicates removed. Reject non-list or nonstring/blank values using TypeError or ValueError respectively. Never mutate caller input.", "checks": ["main"]},
    ],
}
ORACLE = {'schema_version': 2, 'cases': {'validation': {'checks': {'main': [{'file': 'validation.py', 'function': 'normalize_customer', 'args': [{'name': ' Ada ', 'other': 1}], 'expected': {'kind': 'value', 'value': {'name': 'Ada'}}}, {'file': 'validation.py', 'function': 'normalize_customer', 'args': [{'name': ' '}], 'expected': {'kind': 'exception', 'type': 'ValueError'}}, {'file': 'validation.py', 'function': 'normalize_customer', 'args': [{}], 'expected': {'kind': 'exception', 'type': 'ValueError'}}, {'file': 'validation.py', 'function': 'normalize_customer', 'args': ['Ada'], 'expected': {'kind': 'exception', 'type': 'TypeError'}}]}}, 'money': {'checks': {'main': [{'file': 'money.py', 'function': 'sum_minor_units', 'args': [199, 2], 'expected': {'kind': 'value', 'value': 201}}, {'file': 'money.py', 'function': 'sum_minor_units', 'args': [1152921504606846976, 1152921504606846976], 'expected': {'kind': 'value', 'value': 2305843009213693952}}, {'file': 'money.py', 'function': 'sum_minor_units', 'args': [True, 2], 'expected': {'kind': 'exception', 'type': 'TypeError'}}, {'file': 'money.py', 'function': 'sum_minor_units', 'args': [1.5, 2], 'expected': {'kind': 'exception', 'type': 'TypeError'}}, {'file': 'money.py', 'function': 'sum_minor_units', 'args': [-1, 2], 'expected': {'kind': 'exception', 'type': 'ValueError'}}]}}, 'events': {'checks': {'main': [{'file': 'events.py', 'function': 'distinct_events', 'args': [['a', 'b', 'a', 'c', 'b']], 'expected': {'kind': 'value', 'value': ['a', 'b', 'c']}}, {'file': 'events.py', 'function': 'distinct_events', 'args': ['abc'], 'expected': {'kind': 'exception', 'type': 'TypeError'}}, {'file': 'events.py', 'function': 'distinct_events', 'args': [[3]], 'expected': {'kind': 'exception', 'type': 'TypeError'}}, {'file': 'events.py', 'function': 'distinct_events', 'args': [['']], 'expected': {'kind': 'exception', 'type': 'ValueError'}}]}}}}

GUIDANCE = """Act as a Guardian software engineering specialist. Analyze the exact execution boundary before making changes. Enforce input, type, state and domain invariants. Prefer the smallest compatible fix. Exercise a positive case, a failure case and an edge case when possible. Do not alter tests or unrelated modules. Record actual evidence, not assumptions."""


def create(destination: Path) -> dict:
    root = destination.expanduser().absolute()
    if root.exists():
        raise ValueError("Use a new destination; existing files are never overwritten")
    root.mkdir(parents=True)
    project = root / "project"
    project.mkdir()
    for name, content in SOURCE.items():
        (project / name).write_text(content, encoding="utf-8")
    (root / "dataset.json").write_text(json.dumps(CASES, indent=2) + "\n", encoding="utf-8")
    (root / "trusted_checker.json").write_text(json.dumps(ORACLE, indent=2) + "\n", encoding="utf-8")
    (root / "guardian_guidance.md").write_text(GUIDANCE + "\n", encoding="utf-8")
    commands = [
        ["git", "init", "-q"],
        ["git", "add", "."],
        ["git", "-c", "user.name=Guardian Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-q", "-m", "Intentionally broken evaluation baseline"],
    ]
    for command in commands:
        subprocess.run(command, cwd=project, timeout=30, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return {
        "created": True,
        "dataset": str(root / "dataset.json"),
        "checker": str(root / "trusted_checker.json"),
        "candidate_guide": str(root / "guardian_guidance.md"),
        "project": str(project),
        "output_suggestion": str(root / "results"),
        "codex_run_started": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    try:
        print(json.dumps(create(args.out), indent=2))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
