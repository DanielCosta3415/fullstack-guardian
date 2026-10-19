#!/usr/bin/env python3
"""Opt-in repeatable A/B Codex CLI evaluation on synthetic local git projects.

Runs are sequential and isolated. Test scripts are outside the worktree and
never editable by Codex. Model credentials remain managed by the installed CLI.
No claims of causality or model superiority are made by this runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    from .guardian_grader_sandbox import grade_oracle, probe, validate_oracle, strict_json
    from .guardian_benchmark import compare
    from .guardian_executor import safe, _git, ExecutionError, terminate_tree
    from .guardian_platform import _safe_summary
except ImportError:
    from guardian_grader_sandbox import grade_oracle, probe, validate_oracle, strict_json
    from guardian_benchmark import compare
    from guardian_executor import safe, _git, ExecutionError, terminate_tree
    from guardian_platform import _safe_summary


class EvalError(ValueError):
    pass


def fixture(payload: dict) -> dict:
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise EvalError("Invalid dataset schema")
    if set(payload) - {"schema_version", "cases", "dataset_version", "split"}:
        raise EvalError("Unknown dataset fields")
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases or len(cases) > 30:
        raise EvalError("Dataset must contain 1-30 cases")
    names = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {"case_id", "prompt", "checks"}:
            raise EvalError("Each case needs case_id, prompt and checks")
        key = case["case_id"]
        if not isinstance(key, str) or not key.isidentifier() or key in names:
            raise EvalError("Unsafe or duplicate case ID")
        names.add(key)
        _safe_summary(case["prompt"])
        checks = case["checks"]
        if not isinstance(checks, list) or not checks or any(not isinstance(x, str) or not x.isidentifier() for x in checks):
            raise EvalError("Checks must be trusted Python unittest identifiers")
    return payload


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _codex(codex: str, project: Path, prompt: str, model: str, effort: str,
           timeout: int, event_path: Path, config_home: Path | None = None) -> tuple[int | str, bool, int | None]:
    cmd = [codex, "exec", "--json", "--sandbox", "workspace-write",
           "-C", str(project), "--model", model,
           "-c", "model_reasoning_effort=" + json.dumps(effort), "-"]
    event_path.parent.mkdir(parents=True, exist_ok=True)
    with event_path.open("x", encoding="utf-8") as out:
        os.chmod(event_path, 0o600)
        p = subprocess.Popen(cmd, cwd=project, stdin=subprocess.PIPE, stdout=out,
                             stderr=subprocess.DEVNULL, text=True,
                             start_new_session=os.name != "nt",
                             creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
                             env={**{k:v for k,v in os.environ.items() if k.upper() in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "OPENAI_API_KEY")},
                                  "CODEX_HOME": str(config_home), "HOME": str(config_home.parent),
                                  "USERPROFILE": str(config_home.parent)} if config_home else None)
        try:
            deadline = time.monotonic() + timeout
            pending = prompt
            while True:
                if time.monotonic() >= deadline or event_path.stat().st_size > 1_048_576:
                    terminate_tree(p)
                    rc = "timeout_or_output_budget"
                    break
                try:
                    p.communicate(pending, timeout=0.2)
                    rc = p.returncode
                    break
                except subprocess.TimeoutExpired:
                    pending = None
        except BaseException:
            terminate_tree(p)
            raise
    if event_path.stat().st_size > 1_048_576:
        return "output_budget", False, None
    success, tokens = False, None
    completions, failed = 0, False
    with event_path.open(encoding="utf-8") as f:
        for line in f:
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if item.get("type") == "turn.completed":
                completions += 1
                success = True
                usage = item.get("usage") or item.get("turn", {}).get("usage") or {}
                if isinstance(usage, dict):
                    input_tokens = usage.get("input_tokens")
                    output_tokens = usage.get("output_tokens")
                    if all(type(x) is int and x >= 0 for x in (input_tokens, output_tokens)):
                        tokens = input_tokens + output_tokens
            if item.get("type") in ("turn.failed", "error"):
                failed = True
    return rc, success and completions == 1 and not failed, tokens


def grade(checker: Path, case_id: str, worktree: Path, checks: list[str], timeout: int) -> bool:
    """Grade only inside a verified OS sandbox with independent JSON oracle."""
    try:
        return grade_oracle(safe(checker), case_id, safe(worktree), checks, timeout)["passed"]
    except ValueError as exc:
        raise EvalError(str(exc)) from exc



def run(dataset: dict, project: Path, checker: Path, output: Path,
        model: str, effort: str, repeats: int, timeout: int,
        *, apply: bool = False, codex_binary: str | None = None,
        candidate_guidance: str | None = None, seed: int = 0,
        isolated_config: Path | None = None) -> dict:
    dataset = fixture(dataset)
    if type(seed) is not int or not 0 <= seed <= 2**32-1:
        raise EvalError("Seed must be an unsigned 32-bit integer")
    if not isinstance(model, str) or not model or not isinstance(effort, str) or effort not in ("low", "medium", "high", "xhigh"):
        raise EvalError("Model and effort required")
    if type(repeats) is not int or not 1 <= repeats <= 10:
        raise EvalError("Repeats must be 1-10")
    if type(timeout) is not int or not 30 <= timeout <= 3600:
        raise EvalError("Timeout must be 30-3600 seconds")
    project = safe(project)
    checker = safe(checker)
    output = safe(output)
    if not project.is_dir() or not checker.is_file():
        raise EvalError("Project and trusted checker must exist")
    if project == output or project in output.parents or output in project.parents:
        raise EvalError("Results must be in a separate directory")
    if checker == project or project in checker.parents or checker == output or output in checker.parents:
        raise EvalError("Trusted checker must be outside model workspaces and results")
    root = safe(Path(_git(project, "rev-parse", "--show-toplevel")).resolve())
    if project != root or _git(root, "status", "--porcelain", "--untracked-files=all"):
        raise EvalError("Project must be a clean git repository root")
    if any(p.name in ("AGENTS.md", ".agents", ".codex") for p in root.rglob("*") if ".git" not in p.parts):
        raise EvalError("Controlled fixture must exclude inherited project policies, agents and skills")
    base = _git(root, "rev-parse", "HEAD")
    checksum = _sha(checker)
    total = len(dataset["cases"]) * repeats * 2
    if not apply:
        return {"dry_run": True, "experiments": total, "model": model, "effort": effort,
                "checker_sha256": checksum, "codex_quota_used": False,
                "grader_backend": probe(), "seed": seed, "live_config_required": True}
    if dataset.get("split") != "holdout" or not isinstance(dataset.get("dataset_version"), str) or not dataset["dataset_version"]:
        raise EvalError("Live comparisons require an explicit versioned holdout dataset")
    try:
        validate_oracle(strict_json(checker.read_text(encoding="utf-8")))
    except ValueError as exc:
        raise EvalError(str(exc)) from exc
    if not probe()["available"]:
        raise EvalError("Verified rootless grading backend unavailable; NOT VERIFIED, no Codex quota consumed")
    if isolated_config is None:
        raise EvalError("Live evaluation requires an explicit isolated Codex config directory")
    isolated_config = safe(isolated_config)
    if not isolated_config.is_dir() or not (isolated_config / "config.toml").is_file():
        raise EvalError("Isolated config directory and config.toml required")
    if any(p.name in ("AGENTS.md", "agents", "skills", "auth.json") for p in isolated_config.iterdir()):
        raise EvalError("Evaluation config must exclude global policies, agents, skills and copied credentials")
    if not isinstance(candidate_guidance, str) or not candidate_guidance.strip():
        raise EvalError("A/B candidate requires explicit reviewed Guardian guidance for live runs")
    _safe_summary(candidate_guidance)
    guidance_hash = hashlib.sha256(candidate_guidance.encode("utf-8")).hexdigest()
    codex = codex_binary or shutil.which("codex")
    if not codex or not Path(codex).is_file():
        raise EvalError("Authenticated local Codex CLI is required")
    if output.exists() and any(output.iterdir()):
        raise EvalError("Use a fresh empty output directory")
    output.mkdir(parents=True, exist_ok=True)
    template = {"model": model, "effort": effort, "sandbox": "workspace-write",
                "machine_class": os.name, "seed": seed,
                "config_sha256": _sha(isolated_config / "config.toml"),
                "model_version": model, "model_version_verified": False, "dataset_label": dataset.get("dataset_version"),
                "split": dataset.get("split"), "checker_sha256": checksum, "dataset_version": hashlib.sha256(json.dumps(dataset,sort_keys=True).encode()).hexdigest()}
    reports = {k: {"schema_version": 1, "group": k, "environment": template.copy(), "samples": []} for k in ("baseline", "candidate")}
    cases = list(dataset["cases"])
    random.Random(seed).shuffle(cases)
    sequence = 0
    for case in cases:
        for repeat in range(repeats):
            order = ("baseline", "candidate") if (sequence + seed) % 2 == 0 else ("candidate", "baseline")
            sequence += 1
            for group in order:
                target = safe(output / "worktrees" / f"{group}-{case['case_id']}-{repeat}")
                target.parent.mkdir(parents=True, exist_ok=True)
                _git(root, "worktree", "add", "--detach", str(target), base)
                try:
                    prompt = case["prompt"]
                    if group == "candidate":
                        prompt += "\nReviewed Guardian policy for this experiment:\n" + candidate_guidance
                        prompt += "\nOnly use agents actually available, never simulate delegation."
                    else:
                        prompt += "\nSolve directly with normal Codex behavior. Do not explicitly invoke Guardian workflows."
                    prompt += "\nLocal-only workspace. Do not deploy, fetch network data, change global settings or alter test harness. Show evidence."
                    start = time.monotonic()
                    events = safe(output / "events" / f"{group}-{case['case_id']}-{repeat}.jsonl")
                    config_run = output / "configurations" / f"{group}-{case['case_id']}-{repeat}" / ".codex"
                    config_run.mkdir(parents=True)
                    shutil.copyfile(isolated_config / "config.toml", config_run / "config.toml")
                    if _sha(config_run / "config.toml") != template["config_sha256"]:
                        raise EvalError("Reviewed configuration changed during experiment")
                    rc, completed, tokens = _codex(codex, target, prompt, model, effort, timeout, events, config_run)
                    elapsed = round(time.monotonic() - start, 4)
                    if _sha(checker) != checksum:
                        raise EvalError("Trusted checker changed during experiments")
                    grading = ({"passed":False,"status":"NOT EXECUTED","checks":[]} if rc != 0 or not completed else
                               grade_oracle(checker, case["case_id"], target, case["checks"], timeout=min(120, timeout)))
                    passed = grading["passed"]
                    # Token accounting is optional; omit comparisons if native usage is missing.
                    reports[group]["samples"].append({"case_id": case["case_id"], "repeat": repeat,
                        "passed": bool(passed), "duration_seconds": elapsed, "token_count": tokens,
                        "token_count_verified": tokens is not None, "turn_completed": completed,
                        "exit_code": rc, "event_sha256": _sha(events), "grading": grading})
                finally:
                    _git(root, "worktree", "remove", "--force", str(target))
    for group, report in reports.items():
        (output / f"{group}.json").write_text(json.dumps(report, indent=2))
    analyzed = compare(reports["baseline"], reports["candidate"])
    analyzed["native_codex_run"] = True
    analyzed["test_checker_hash"] = checksum
    analyzed["all_token_counts_verified"] = all(x["token_count_verified"] for r in reports.values() for x in r["samples"])
    analyzed["candidate_guidance_sha256"] = guidance_hash
    analyzed["candidate_guidance_length"] = len(candidate_guidance)
    analyzed["experiment_confounded"] = True
    analyzed["order"] = "seeded cases, counterbalanced AB/BA pairs"
    analyzed["seed"] = seed
    analyzed["config_isolated"] = True
    analyzed["model_version_verified"] = False
    analyzed["monetary_cost_verified"] = False
    analyzed["warning"] = ("Global Codex setup, prompt variants and harness environment can differ; "
                          "this A/B report is not a controlled proof that Guardian improves outcomes.")
    (output / "comparison.json").write_text(json.dumps(analyzed, indent=2))
    return analyzed


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--project", type=Path, required=True)
    p.add_argument("--checker", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--effort", choices=("low", "medium", "high", "xhigh"), default="medium")
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--timeout", type=int, default=1200)
    p.add_argument("--candidate-guide", type=Path, help="Reviewed Guardian guidance file used ONLY in the candidate prompt; mandatory for --run")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--isolated-config", type=Path)
    p.add_argument("--run", action="store_true", help="Explicitly consume Codex quota")
    a = p.parse_args()
    try:
        outcome = run(json.loads(safe(a.dataset).read_text(encoding="utf-8")),
                      a.project, a.checker, a.out, a.model, a.effort,
                      a.repeats, a.timeout, apply=a.run,
                      seed=a.seed, isolated_config=a.isolated_config,
                      candidate_guidance=safe(a.candidate_guide).read_text(encoding="utf-8") if a.candidate_guide else None)
        print(json.dumps(outcome, ensure_ascii=False, indent=2))
        return 0
    except (EvalError, ExecutionError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
