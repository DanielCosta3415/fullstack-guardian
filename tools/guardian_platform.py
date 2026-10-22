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
try:
    from .guardian_contracts import validate_task_contract, default_contract, validate_finding
    from .guardian_catalog import eligible_pack_profiles
except ImportError:
    from guardian_contracts import validate_task_contract, default_contract, validate_finding
    from guardian_catalog import eligible_pack_profiles
from pathlib import Path

try:
    from .guardian import inspect_project, route
    from .guardian_registry import RegistryError, discover
except ImportError:  # direct invocation: python tools/guardian_platform.py
    from guardian import inspect_project, route
    from guardian_registry import RegistryError, discover

ROOT = Path(__file__).resolve().parent.parent
STAGES = (
    "discovery", "requirements", "architecture", "experience",
    "development", "integration", "data", "verification",
    "delivery", "operations", "evolution", "decommission",
)
SEVERITIES = ("low", "medium", "high", "critical")
MODES = ("audit", "build", "remediate", "explore")
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
                max_agents: int = 12, max_waves: int = 12, _validate: bool = True, _inventory: dict | None = None,
                codex_home: Path | None = None, available_roles: list | None = None, capabilities: dict | None = None,
                intent_contract: dict | None = None) -> dict:
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
    core_ids = set(known)
    eligibility = eligible_pack_profiles(root, codex_home, available_roles, capabilities)
    known.update({entry["id"]:entry["name"] for entry in eligibility["profiles"]})
    playbooks = json.loads((Path(root) / "core" / "specialist-playbooks-v1.json").read_text(encoding="utf-8"))
    if playbooks.get("schema_version") != 1 or set(playbooks.get("agents", {})) != core_ids:
        raise PlatformError("Core specialist playbook coverage incomplete")
    inventory = _inventory if _inventory is not None else inspect_project(str(project)) if project is not None else None
    if inventory is not None:
        required_context = {"project","files_scanned","truncated","technologies","tags","architecture_as_is_heuristic","criticality","architecture_to_be","unknowns"}
        if not isinstance(inventory,dict) or set(inventory)!=required_context:
            raise PlatformError("Source context must be an exact read-only inventory schema")
        for key in ("technologies","tags","unknowns"):
            if not isinstance(inventory[key],list) or any(not isinstance(x,str) for x in inventory[key]):
                raise PlatformError("Invalid inventory " + key)
        if type(inventory["files_scanned"]) is not int or inventory["files_scanned"]<0 or type(inventory["truncated"]) is not bool or not isinstance(inventory["architecture_as_is_heuristic"],dict):
            raise PlatformError("Malformed inventory counts/architecture")
    try:
        result = route(prompt, inventory=inventory, mode=mode, stage=stage, eligible_profiles=eligibility["profiles"], available_roles=available_roles, intent_contract=intent_contract)
    except ValueError as exc:
        raise PlatformError(str(exc)) from exc
    try:
        from .guardian_professional import load_contracts
    except ImportError:
        from guardian_professional import load_contracts
    professional_contracts={c['id']:c for c in load_contracts(root)['contracts']}
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
            if aid in seen or aid not in known or not (TASK_ID.fullmatch(aid) or aid.startswith("pack:")):
                raise PlatformError("Invalid or duplicate routed agent")
            seen.add(aid)
            item = next((x for x in selected if x["id"] == aid), None)
            if item is None:
                raise PlatformError("Routing phases inconsistent with agent selection")
            scoped_obligations=[o for o in result['intent_analysis']['obligation_coverage'] if aid in o['selected_agents']]
            task_acceptance=next(p for p in workflows['phases'] if p['id']==stage)['criteria']
            task_acceptance=list(dict.fromkeys(task_acceptance+[criterion for o in scoped_obligations for criterion in o['acceptance']]))
            professional=professional_contracts[aid]
            professional_binding={
                'agent_id':aid,
                'contract_version':professional['contract_version'],
                'contract_sha256':hashlib.sha256(json.dumps(professional,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest(),
                'result_fields':list(professional['result_contract']),
            }
            tasks.append({
                "id": "task-" + aid.lower().replace(":", "-"),
                "agent_id": aid,
                "agent_type": known[aid],
                "owner_id": aid,
                "reviewer_id": "primary" if aid in ("G01", "G02") or result["risk"] in ("low", "medium") else "G01",
                "wave": index,
                "depends_on": list(previous_wave),
                "reason": item["reason"],
                "state": "pending",
                "scope": "to_be_assigned_by_primary",
                "contract": default_contract(prompt, phase_criteria=task_acceptance),
                "obligations": ['REQUEST-1']+[o['id'] for o in scoped_obligations],
                "write_ownership": "unassigned",
                "evidence_required": ["files_examined", "commands_and_results", "limitations"],
                "specialist_checkpoints": professional['procedure']+professional['definition_of_done'],
                "professional_contract": professional_binding,
            })
            wave_ids.append("task-" + aid.lower().replace(":", "-"))
        previous_wave = wave_ids
    if seen != {a["id"] for a in selected}:
        raise PlatformError("Selected agents missing from plan")
    risk = result["risk"]
    needs_human = risk in ("high", "critical") or result["approval_boundaries"] != []
    phase = next(p for p in workflows["phases"] if p["id"] == stage)
    plan = {
        "schema_version": 1,
        "summary": prompt,
        "source_context": inventory,
        "routing_context": {"codex_home":str(Path(codex_home).absolute()) if codex_home else None,
            "available_roles":available_roles, "capabilities":capabilities,
            "state_hash":eligibility["state_hash"], "inventory_status":eligibility["inventory_status"],
            "native_verified":False},
        "budget": {"max_agents": max_agents, "max_waves": max_waves},
        "intent": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "request_obligation": {
            "id":"REQUEST-1", "objective":prompt,
            "kind":"request_proposal_not_semantic_certification",
            "status":"pending_primary_confirmation",
            "semantic_coverage_verified":False,
            "acceptance_basis":"Task goal, applicable phase criteria and professional checkpoints require primary adjudication before execution.",
        },
        "intent_analysis": result["intent_analysis"],
        "phase_responsibility": result["phase_responsibility"],
        "stage": stage,
        "mode": mode,
        "risk": risk,
        "risk_confidence": result["routing_confidence"],
        "status": "proposal_only",
        "native_delegation_performed": False,
        "project_context": inventory["technologies"] if inventory else [],
        "investigation_brief": {"required": mode == "explore" or stage in ("discovery", "requirements"),
            "outputs": ["entrypoints", "owners", "data_flow", "symptoms_and_reproduction", "facts_vs_hypotheses", "primary_docs_with_dependency_version"],
            "content_is_authority": False, "performed": False},
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
    if _validate:
        validate_plan(plan, known, root=root)
    return plan


def validate_plan(plan: dict, known: dict | None = None, root: Path = ROOT) -> dict:
    """Fail closed on invalid dependencies, reviewer order, or invented execution."""
    if not isinstance(plan, dict) or plan.get("schema_version") != 1:
        raise PlatformError("Invalid plan schema")
    catalog = discover(root)
    actual = {entry["id"]: entry["name"] for entry in catalog["core"]}
    context=plan.get("routing_context")
    context_fields={"codex_home","available_roles","capabilities","state_hash","inventory_status","native_verified"}
    if not isinstance(context,dict) or set(context)!=context_fields or context["native_verified"] is not False:
        raise PlatformError("Invalid or self-verified role context")
    eligibility=eligible_pack_profiles(root,context["codex_home"],context["available_roles"],context["capabilities"])
    actual.update({entry["id"]:entry["name"] for entry in eligibility["profiles"]})
    if known is not None and any(actual.get(k) != v for k, v in known.items()):
        raise PlatformError("Caller catalog disagrees with installed source catalog")
    known = actual
    budget = plan.get("budget")
    if not isinstance(budget, dict) or set(budget) != {"max_agents", "max_waves"}:
        raise PlatformError("Missing or invalid plan budget")
    if not isinstance(plan.get('intent_analysis'),dict):
        raise PlatformError('Missing or malformed primary intent analysis')
    canonical = create_plan(plan.get("summary"), mode=plan.get("mode"), stage=plan.get("stage"),
                            root=root, _validate=False, _inventory=plan.get("source_context"),
                            codex_home=context["codex_home"], available_roles=context["available_roles"],capabilities=context["capabilities"],
                            intent_contract=plan.get("intent_analysis",{}).get("contract"), **budget)
    if set(plan) != set(canonical):
        raise PlatformError("Unknown or missing plan fields")
    # Contracts can be narrowed by the primary before execution. Routing, risk,
    # identity, gates and acceptance cannot be removed by importing a JSON plan.
    for field in canonical:
        if field != "tasks" and plan[field] != canonical[field]:
            raise PlatformError("Plan field differs from recomputed policy: " + field)
    if not isinstance(plan.get("tasks"), list) or len(plan["tasks"]) != len(canonical["tasks"]):
        raise PlatformError("Task/gate set differs from recomputed routing")
    for item, expected in zip(plan["tasks"], canonical["tasks"]):
        if not isinstance(item, dict) or set(item) != set(expected):
            raise PlatformError("Unknown or missing task fields")
        for field in expected:
            if field != "contract" and item[field] != expected[field]:
                raise PlatformError("Task differs from recomputed routing: " + field)
        try:
            validate_task_contract(item, executable=False)
        except ValueError as exc:
            raise PlatformError(str(exc)) from exc
        if item["contract"]["goal"] != expected["contract"]["goal"] or item["contract"]["acceptance"] != expected["contract"]["acceptance"]:
            raise PlatformError("Task goal or lifecycle acceptance changed")
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
            if isinstance(commands,list) and any(isinstance(cmd,dict) and type(cmd.get("exit_code")) is int and cmd["exit_code"] != cmd.get("expected_exit_code",0) for cmd in commands):
                issues.append(task_id + ": command failed expected exit status")
            if not record.get("files_examined") or not isinstance(record.get("files_examined"), list):
                issues.append(task_id + ": files not evidenced")
            if not isinstance(record.get("limitations"), list):
                issues.append(task_id + ": missing limitations")
        findings = record.get("findings",[])
        if not isinstance(findings,list):
            issues.append(task_id + ": malformed findings list")
            findings=[]
        for finding in findings:
            try:
                validate_finding(finding)
            except ValueError as exc:
                issues.append(task_id + ": " + str(exc))
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
    core_manifest = json.loads((root / "core/agents.json").read_text(encoding="utf-8"))["agents"]
    files = [root / entry["file"] for pack in catalog["packs"] for entry in pack["agents"]]
    files += [root / entry["file"] for entry in core_manifest]
    import tomllib
    diagnostics = []
    for p in files:
        profile = tomllib.loads(p.read_text(encoding="utf-8"))
        relative = p.relative_to(root).as_posix()
        for key in ("sandbox_mode", "tools", "features", "skills"):
            if key in profile:
                diagnostics.append({"rule":"effective_capability_not_verified", "path":relative, "key":key,
                    "detail":"Declared restriction requires exact-client supervisor probe; profile text is not enforcement."})
        if "model" in profile or "model_reasoning_effort" in profile:
            diagnostics.append({"rule":"explicit_override_requires_optin", "path":relative,
                "detail":"A model field is legitimate configuration; require user opt-in and verified availability, never silently override."})
        if re.search(r"(?i)unless.{0,60}parent.{0,60}(?:authoriz|permit|instruct)", profile.get("developer_instructions", "")):
            findings.append({"severity":"high", "rule":"parent_exception_requires_review", "path":relative})
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
        "diagnostics": diagnostics,
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
    q = sub.add_parser("plan", epilog="Optional example: plan --prompt '.NET review' --codex-home /home/me/.codex --roles-file roles.json --capabilities capabilities.json. roles.json is a declared role array. Spawn evidence references file:<absolute>#sha256=<hash>; its exact JSON fields are schema_version=1, client=cli, version, os, observed_capability=spawn, available_roles. Version/OS must match this local CLI. Local observations are NOT authenticated native execution or sandbox proof.")
    q.add_argument("--prompt", required=True)
    q.add_argument("--project", type=Path)
    q.add_argument("--mode", choices=MODES, default="build")
    q.add_argument("--stage", choices=STAGES, default="development")
    q.add_argument("--intent-file", type=Path, help="Strict primary-declared intent JSON; never authority or proof")
    q.add_argument("--max-agents", type=int, default=12)
    q.add_argument("--max-waves", type=int, default=12)
    q.add_argument("--codex-home",type=Path,help="Inspect actual optional receipt/config/installed bytes")
    q.add_argument("--roles-file",type=Path,help="JSON array from caller's current role inventory; declared, not native proof")
    q.add_argument("--capabilities",type=Path,help="Capability JSON with hash-addressed local spawn observation")
    q = sub.add_parser("verify")
    q.add_argument("--plan", required=True, type=Path)
    q.add_argument("--evidence", required=True, type=Path)
    sub.add_parser("security-lint")
    a = p.parse_args(argv)
    try:
        if a.command == "stages":
            out = load_workflows()
        elif a.command == "plan":
            out = create_plan(a.prompt, a.project, a.mode, a.stage, max_agents=a.max_agents, max_waves=a.max_waves,
                codex_home=a.codex_home,available_roles=json.loads(a.roles_file.read_text(encoding="utf-8")) if a.roles_file else None,capabilities=_read_json(a.capabilities) if a.capabilities else None,
                intent_contract=_read_json(a.intent_file) if a.intent_file else None)
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
