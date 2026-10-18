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
    "cases": [
        {"case_id": "validation", "prompt": "Implement normalize_customer(data) in validation.py. Accept only dict input with nonempty string 'name', strip surrounding whitespace and return a fresh dict with normalized name. Raise ValueError for missing/blank names and TypeError for non-dict inputs. Leave unrelated files untouched.", "checks": ["main"]},
        {"case_id": "money", "prompt": "Fix sum_minor_units(amount, fee) in money.py. Both arguments must be nonnegative Python ints in minor currency units (bool is invalid); return their exact integer sum. Raise TypeError for non-int, ValueError for negatives, never convert via floating point. Keep the public API.", "checks": ["main"]},
        {"case_id": "events", "prompt": "Fix distinct_events(events) in events.py. Accept a list of nonempty string event IDs, return first-seen values in stable order with duplicates removed. Reject non-list or nonstring/blank values using TypeError or ValueError respectively. Never mutate caller input.", "checks": ["main"]},
    ],
}
CHECKER = '''#!/usr/bin/env python3
"""Trusted external grader, no dependencies or network."""
import argparse
import importlib.util
from pathlib import Path


def module(root, filename):
    path = root / filename
    spec = importlib.util.spec_from_file_location("test_target_" + filename.removesuffix(".py"), path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def raises(error, callable_):
    try:
        callable_()
    except error:
        return
    raise AssertionError("Expected " + error.__name__)


def run(root, case):
    if case == "validation":
        normalize = module(root, "validation.py").normalize_customer
        x = {"name": " Ada ", "other": 1}
        assert normalize(x) == {"name": "Ada"}
        assert x == {"name": " Ada ", "other": 1}
        raises(ValueError, lambda: normalize({"name": "  "}))
        raises(ValueError, lambda: normalize({}))
        raises(TypeError, lambda: normalize("Ada"))
    elif case == "money":
        calc = module(root, "money.py").sum_minor_units
        assert calc(199, 2) == 201
        assert isinstance(calc(199, 2), int)
        assert calc(2**60, 2**60) == 2**61
        raises(TypeError, lambda: calc(True, 2))
        raises(TypeError, lambda: calc(1.5, 2))
        raises(ValueError, lambda: calc(-1, 2))
    elif case == "events":
        distinct = module(root, "events.py").distinct_events
        original = ["a", "b", "a", "c", "b"]
        assert distinct(original) == ["a", "b", "c"]
        assert original == ["a", "b", "a", "c", "b"]
        raises(TypeError, lambda: distinct("abc"))
        raises(TypeError, lambda: distinct([3]))
        raises(ValueError, lambda: distinct([""]))
    else:
        raise AssertionError("Unknown case")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--checks", required=True)
    args = parser.parse_args()
    assert args.checks == "main"
    run(Path(args.workspace), args.case)


if __name__ == "__main__":
    main()
'''
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
    (root / "trusted_checker.py").write_text(CHECKER, encoding="utf-8")
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
        "checker": str(root / "trusted_checker.py"),
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
