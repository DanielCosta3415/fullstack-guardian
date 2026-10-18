#!/usr/bin/env python3
"""Comparable, paired offline benchmark analyzer. Never invokes Codex or vendors."""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path


class BenchmarkError(ValueError):
    pass


def _parse(payload: dict, expected_group: str) -> dict:
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise BenchmarkError("Unsupported benchmark report schema")
    if payload.get("group") != expected_group:
        raise BenchmarkError("Benchmark group mismatch")
    meta = payload.get("environment")
    if not isinstance(meta, dict) or not all(isinstance(meta.get(k), str) and meta[k] for k in ("model", "effort", "sandbox", "machine_class", "dataset_version")):
        raise BenchmarkError("Model, effort, sandbox, machine class and dataset version are required")
    rows = payload.get("samples")
    if not isinstance(rows, list) or not rows:
        raise BenchmarkError("Non-empty samples required")
    samples = {}
    for row in rows:
        if not isinstance(row, dict):
            raise BenchmarkError("Malformed sample")
        case, repeat = row.get("case_id"), row.get("repeat")
        key = (case, repeat)
        if not isinstance(case, str) or not case or type(repeat) is not int or repeat < 0 or key in samples:
            raise BenchmarkError("Invalid or duplicate case/repetition")
        if type(row.get("passed")) is not bool:
            raise BenchmarkError("passed must be actual bool")
        for metric in ("duration_seconds", "token_count"):
            value = row.get(metric)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise BenchmarkError("Invalid or missing metric: " + metric)
        samples[key] = row
    return {"meta": meta, "samples": samples}


def compare(baseline: dict, candidate: dict) -> dict:
    a, b = _parse(baseline, "baseline"), _parse(candidate, "candidate")
    if a["meta"] != b["meta"]:
        raise BenchmarkError("Unmatched benchmark environments: no valid comparison")
    if a["samples"].keys() != b["samples"].keys():
        raise BenchmarkError("Non-paired case/repetition sets")
    keys = sorted(a["samples"])
    n = len(keys)
    base = [a["samples"][key] for key in keys]
    trial = [b["samples"][key] for key in keys]
    def average(items, metric):
        return round(statistics.mean(x[metric] for x in items), 4)
    base_success = sum(x["passed"] for x in base)
    trial_success = sum(x["passed"] for x in trial)
    gains = sum(not x["passed"] and y["passed"] for x, y in zip(base, trial))
    losses = sum(x["passed"] and not y["passed"] for x, y in zip(base, trial))
    return {
        "schema_version": 1,
        "paired_samples": n,
        "unique_cases": len({c for c, _ in keys}),
        "baseline": {"passed": base_success, "pass_rate": round(base_success / n, 4), "mean_duration_seconds": average(base, "duration_seconds"), "mean_token_count": average(base, "token_count")},
        "candidate": {"passed": trial_success, "pass_rate": round(trial_success / n, 4), "mean_duration_seconds": average(trial, "duration_seconds"), "mean_token_count": average(trial, "token_count")},
        "paired_improvements": gains,
        "paired_regressions": losses,
        "pass_rate_delta": round((trial_success-base_success)/n, 4),
        "sufficient_for_general_claim": False,
        "limits": "Descriptive paired statistics only: no causal, statistical-significance, or security claims. Dataset, repeatability, graders, CI evidence and human review required.",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", required=True, type=Path)
    p.add_argument("--candidate", required=True, type=Path)
    args = p.parse_args()
    try:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
        result = compare(baseline, candidate)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
