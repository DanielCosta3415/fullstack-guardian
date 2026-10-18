#!/usr/bin/env python3
"""Guardian platform control plane. Offline, read-only, deterministic, stdlib-only.

The program produces plans and validates evidence; it NEVER spawns agents,
deploys software, changes user configuration, or treats an LLM claim as proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

from guardian import inspect_project, route
from guardian_registry import RegistryError, discover

ROOT = Path(__file__).resolve().parent.parent
STAGES = (
    "discovery", "requirements", "architecture", "experience",
    "development", "integration", "data", "verification",
    "delivery", "operations", "evolution", "decommission",
)
SEVERITIES = ("low", "medium", "high", "critical")
MODES = ("audit", "build", "remediate")
REDACT = re.compile(r"(?i)(?:api[_-]?key|password|passwd|secret|authorization|bearer|private[_-]?key)\s*[:=]\s*\S+")
SENSITIVE = re.compile(r"(?i)(?:^|[/\\])(?:\.env(?:\..*)?|.*\.(?:pem|pfx|key)|id_rsa|secrets?\.(?:json|ya?ml))$")
TASK_ID = re.compile(r"^[A-Z][0-9]{2}$")


class PlatformError(ValueError):
    """A safety, schema or planning invariant failed."""


def load_workflows(root: Path = ROOT) -> dict:
    doc = json.loads((Path(root) / "core" / "lifecycle-v1.json").read_text(encoding="utf-8"))
    phases = doc.get("phases")
    if doc.get("schema_version") != 1 or not isinstance(phases, list) or len(phases) != len(STAGES):
        raise PlatformError("Lifecycle schema or stage count invalid")
    if tuple(p.get("id") for p in phases) != STAGES:
        raise PlatformError("Lifecycle phases must follow explicit stage order")
    for phase in phases:
        if not isinstance(phase.get("purpose"), str) or not phase.get("purpose"):
            raise PlatformError("Missing phase purpose")
        if not isinstance(phase.get("criteria"), list) or not phase["criteria"] or any(not isinstance(x, str) or not x for x in phase["criteria"]):
            raise PlatformError("Missing phase evidence criteria")
        if not isinstance(phase.get("responsible"), list) or not phase["responsible"]:
            raise PlatformError("Missing phase specialists")
    return doc


def _safe_summary(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        raise PlatformError("A non-empty task summary is required")
    if len(text) > 8000:
        raise PlatformError("Task summary exceeds safe length")
    if REDACT.search(text):
        raise PlatformError("Secrets detected in summary: redact before planning")
    return text.strip()


def create_plan(prompt: str, project: Path | None = None, mode: str = "build",
                stage: str = "development", root: Path = ROOT,
                max_agents: int = 12, max_waves: int = 12) -> dict:
    """Build a bounded, non-executable plan; every delegation is pending."""
    prompt = _safe_summary(prompt)
    if mode not in MODES or stage not in STAGES:
        raise PlatformError("Unsupported operation mode or lifecycle stage")
    if type(max_agents) is not int or not 1 <= max_agents <= 29:
        raise PlatformError("max_agents must be an integer from 1 to 29")
    if type(max_waves) is not int or not 1 <= max_waves <= 29:
        raise PlatformError("max_waves must be an integer from 1 to 29")
    workflows = load_workflows(root)
    catalog = discover(root)
    known = {entry["id"]: entry["name"] for entry in catalog["core"]}
    inventory = inspect_project(str(project)) if project is not None else None
    result = route(prompt, inventory=inventory, mode=mode)
    selected = result["agents"]
    if len(selected) > max_agents:
        raise PlatformError("Routing exceeds agent budget; human must refine scope, no silent dropping")
    waves = result["execution_waves"]
    if len(waves) > max_waves:
        raise PlatformError("Routing exceeds wave budget")
    seen = set()
    tasks = []
    previous_wave = []
    for index, wave in enumerate(waves):
        wave_ids = []
        for aid in wave:
            if aid in seen or aid not in known or not TASK_ID.fullmatch(aid):
                raise PlatformError("Invalid or duplicate routed agent")
            seen.add(aid)
            item = next((x for x in selected if x["id"] == aid), None)
            if item is None:
                raise PlatformError("Routing phases inconsistent with agent selection")
            tasks.append({
                "id": "task-" + aid.lower(),
                "agent_id": aid,
                "agent_type": known[aid],
                "wave": index,
                "depends_on": list(previous_wave),
                "reason": item["reason"],
                "state": "pending",
                "scope": "to_be_assigned_by_primary",
                "write_ownership": "unassigned",
                "evidence_required": ["files_examined", "commands_and_results", "limitations"],
            })
            wave_ids.append("task-" + aid.lower())
        previous_wave = wave_ids
    if seen != {a["id"] for a in selected}:
        raise PlatformError("Selected agents missing from plan")
    risk = result["risk"]
    needs_human = risk in ("high", "critical") or result["approval_boundaries"] != []
    phase = next(p for p in workflows["phases"] if p["id"] == stage)
    plan = {
        "schema_version": 1,
        "intent": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "stage": stage,
        "mode": mode,
        "risk": risk,
        "risk_confidence": result["routing_confidence"],
        "status": "proposal_only",
        "native_delegation_performed": False,
        "project_context": inventory["technologies"] if inventory else [],
        "architecture": {"as_is": result["architecture_as_is_guess"], "to_be": result["architecture_to_be"]},
        "tasks": tasks,
        "lifecycle_exit_criteria": phase["criteria"],
        "human_authorization_required": needs_human,
        "approval_boundaries": result["approval_boundaries"],
        "runtime_permissions": "inherited_from_codex_session",
        "limitations": [
            "Static heuristics recommend roles, not native Codex delegation.",
            "No changes, tests or releases were executed by this plan.",
            "Evidence and approvals must be independently verified.",
        ],
    }
    validate_plan(plan, known)
    return plan


def validate_plan(plan: dict, known: dict | None = None) -> dict:
    """Fail closed on invalid dependencies, reviewer order, or invented execution."""
    if not isinstance(plan, dict) or plan.get("schema_version") != 1:
        raise PlatformError("Invalid plan schema")
    if plan.get("status") != "proposal_only" or plan.get("native_delegation_performed") is not False:
        raise PlatformError("Plans may not assert work was performed")
    if plan.get("stage") not in STAGES or plan.get("mode") not in MODES or plan.get("risk") not in SEVERITIES:
        raise PlatformError("Invalid stage, mode or risk")
    items = plan.get("tasks")
    if not isinstance(items, list) or not items:
        raise PlatformError("Empty task plan")
    byid = {}
    for item in items:
        if not isinstance(item, dict) or item.get("id") in byid or not isinstance(item.get("id"), str):
            raise PlatformError("Invalid or duplicate task ID")
        if known is not None and known.get(item.get("agent_id")) != item.get("agent_type"):
            raise PlatformError("Unknown or mismatched agent")
        if item.get("state") != "pending" or item.get("write_ownership") != "unassigned":
            raise PlatformError("Cannot claim execution or write ownership in proposed plan")
        if type(item.get("wave")) is not int or item["wave"] < 0:
            raise PlatformError("Invalid wave index")
        if not isinstance(item.get("depends_on"), list):
            raise PlatformError("Dependencies must be a list")
        byid[item["id"]] = item
    for key, item in byid.items():
        if key in item["depends_on"] or len(set(item["depends_on"])) != len(item["depends_on"]):
            raise PlatformError("Circular/self or repeated dependency")
        if any(dep not in byid or byid[dep]["wave"] >= item["wave"] for dep in item["depends_on"]):
            raise PlatformError("Dependency missing or not ordered before task")
    reviewers = [x for x in items if x["agent_id"] in ("G01", "G02")]
    if reviewers:
        max_worker = max((t["wave"] for t in items if t["agent_id"] not in ("G01", "G02")), default=-1)
        if any(t["wave"] <= max_worker for t in reviewers):
            raise PlatformError("Review must follow implementation/investigation")
    return {"valid": True, "tasks": len(items), "waves": len(set(x["wave"] for x in items))}


def validate_evidence(report: dict, plan: dict) -> dict:
    """Inspect evidence claims only. Never authenticate recorded tool execution."""
    validate_plan(plan)
    if not isinstance(report, dict) or report.get("schema_version") != 1:
        raise PlatformError("Invalid evidence schema")
    expected = {task["id"] for task in plan["tasks"]}
    records = report.get("tasks")
    if not isinstance(records, list):
        raise PlatformError("Evidence tasks missing")
    ids = [r.get("task_id") for r in records if isinstance(r, dict)]
    if len(ids) != len(records) or len(set(ids)) != len(ids) or set(ids) - expected:
        raise PlatformError("Evidence tasks malformed, duplicated or not in plan")
    issues = []
    for record in records:
        task_id = record["task_id"]
        if record.get("status") not in ("completed", "failed", "blocked", "not_verified"):
            issues.append(task_id + ": invalid status")
            continue
        if record["status"] == "completed":
            commands = record.get("commands")
            if not isinstance(commands, list) or not commands:
                issues.append(task_id + ": no command evidence")
            elif any(not isinstance(cmd, dict) or not isinstance(cmd.get("command"), str) or type(cmd.get("exit_code")) is not int for cmd in commands):
                issues.append(task_id + ": command evidence invalid")
            if not record.get("files_examined") or not isinstance(record.get("files_examined"), list):
                issues.append(task_id + ": files not evidenced")
            if not isinstance(record.get("limitations"), list):
                issues.append(task_id + ": missing limitations")
    missing = sorted(expected - set(ids))
    return {
        "schema_version": 1,
        "submitted": len(records),
        "expected": len(expected),
        "missing": missing,
        "issues": issues,
        "complete_claims_with_required_fields": not issues and not missing,
        "authenticated_execution": False,
        "release_authorized": False,
        "notice": "Schema checks do not prove commands actually ran. Independent logs and human authorization remain necessary.",
    }


def security_lint(root: Path = ROOT) -> dict:
    """Non-executing conservative static review of agent configuration only."""
    root = Path(root)
    findings = []
    try:
        catalog = discover(root)
    except (RegistryError, OSError, ValueError) as exc:
        return {"ok": False, "findings": [{"severity": "high", "rule": "invalid_registry", "detail": str(exc)}], "security_certified": False}
    files = [root / entry["file"] for pack in catalog["packs"] for entry in pack["agents"]]
    files += [root / "global" / "agents" / (entry["name"].replace("guardian_", "") + ".toml") for entry in []]
    for p in files:
        if SENSITIVE.search(p.name):
            findings.append({"severity": "high", "rule": "sensitive_extension_path", "path": str(p.relative_to(root))})
    # The registry parser has already rejected unexpected model/sandbox overrides,
    # malformed packs, duplicate identifiers and symlink entries.
    return {
        "ok": not findings,
        "files_validated": catalog["available_total"],
        "packs_checked": len(catalog["packs"]),
        "findings": findings,
        "security_certified": False,
        "scope": "Static configuration and paths only; not a security audit of project code or runtime.",
    }


def _read_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PlatformError("Invalid JSON input") from exc
    if not isinstance(payload, dict):
        raise PlatformError("Root JSON value must be an object")
    return payload


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("stages")
    q = sub.add_parser("plan")
    q.add_argument("--prompt", required=True)
    q.add_argument("--project", type=Path)
    q.add_argument("--mode", choices=MODES, default="build")
    q.add_argument("--stage", choices=STAGES, default="development")
    q.add_argument("--max-agents", type=int, default=12)
    q.add_argument("--max-waves", type=int, default=12)
    q = sub.add_parser("verify")
    q.add_argument("--plan", required=True, type=Path)
    q.add_argument("--evidence", required=True, type=Path)
    sub.add_parser("security-lint")
    a = p.parse_args(argv)
    try:
        if a.command == "stages":
            out = load_workflows()
        elif a.command == "plan":
            out = create_plan(a.prompt, a.project, a.mode, a.stage, max_agents=a.max_agents, max_waves=a.max_waves)
        elif a.command == "verify":
            out = validate_evidence(_read_json(a.evidence), _read_json(a.plan))
        else:
            out = security_lint()
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok", True) and not out.get("issues") and not out.get("missing") else 1
    except (PlatformError, RegistryError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
