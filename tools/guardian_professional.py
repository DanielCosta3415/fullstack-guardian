"""Versioned professional contracts: declarative requirements, never tool grants.

Availability, native smoke execution and professional qualification are distinct.
This module does not run agents or infer competence from profile prose.
"""
from __future__ import annotations
import copy
import json
import re
import unicodedata
from pathlib import Path
try:
    from .guardian_registry import _contained
except ImportError:
    from guardian_registry import _contained
ROOT = Path(__file__).resolve().parents[1]
FIELDS = {"id", "name", "contract_version", "mission", "scope", "non_goals", "modes", "capabilities", "routing_terms", "inputs", "procedure", "artifacts", "definition_of_done", "tool_policy", "handoffs", "review", "stop_conditions", "result_contract", "qualification", "overlays"}
RESULT_FIELDS = ["task_id", "agent_id", "contract_version", "obligations", "artifacts", "facts", "assumptions", "decisions", "checks", "not_verified", "residual_risks", "handoff"]


def _read(root, name):
    path = _contained(root / "core" / name, root)
    if path.stat().st_size > 2_000_000:
        raise ValueError("Professional metadata exceeds size limit")
    return json.loads(path.read_text(encoding="utf8"))


def _strings(value, label, minimum=1):
    if not isinstance(value, list) or len(value) < minimum or any(not isinstance(v, str) or not v.strip() or len(v) > 8000 for v in value):
        raise ValueError("Invalid professional " + label)
    if len(set(value)) != len(value):
        raise ValueError("Duplicate professional " + label)


def validate_document(doc, catalog, taxonomy):
    """Strict schema plus cross-document invariants; useful for offline reviews."""
    if not isinstance(doc, dict) or set(doc) != {"schema_version", "qualification_policy", "contracts"} or doc["schema_version"] != 1:
        raise ValueError("Unsupported professional contracts schema")
    if doc["qualification_policy"] != "DECLARED_CONTRACT_NOT_PROFESSIONAL_CERTIFICATION":
        raise ValueError("Professional qualification policy missing")
    records = catalog.get("records", [])
    if not isinstance(records, list) or any(not isinstance(r, dict) or not isinstance(r.get("id"), str) or not isinstance(r.get("name"), str) for r in records):
        raise ValueError("Invalid canonical identity inventory")
    expected = {r["id"]: r for r in records}
    core_ids = {"A00", "G01", "G02"} | {"S%02d" % i for i in range(1, 27)}
    if len(records) != 39 or {aid for aid in expected if not aid.startswith("pack:")} != core_ids or sum(aid.startswith("pack:") for aid in expected) != 10:
        raise ValueError("Professional v1 requires all 29 core and ten optional contracts")
    known_caps = {c["id"] for c in taxonomy["capabilities"]}
    contracts = doc["contracts"]
    if not isinstance(contracts, list) or len(contracts) != len(expected) or {c.get("id") for c in contracts if isinstance(c, dict)} != set(expected):
        raise ValueError("Professional coverage missing, duplicate or unknown ID")
    for c in contracts:
        if not isinstance(c, dict) or set(c) != FIELDS:
            raise ValueError("Unknown/missing professional contract field")
        if c["name"] != expected[c["id"]]["name"] or c["contract_version"] != "1.0.0":
            raise ValueError("Professional identity/version mismatch")
        for key in ("mission", "scope"):
            if not isinstance(c[key], str) or not c[key].strip():
                raise ValueError("Missing professional " + key)
        for key in ("non_goals", "inputs", "procedure", "artifacts", "definition_of_done", "stop_conditions"):
            _strings(c[key], key, 3 if key in ("procedure", "definition_of_done") else 1)
        _strings(c["routing_terms"], "routing terms", 0)
        _strings(c["modes"], "modes")
        if not set(c["modes"]) <= {"audit", "explore", "build", "remediate"}:
            raise ValueError("Unknown professional mode")
        if c["id"] in ("G01", "G02") and set(c["modes"]) != {"audit", "explore"}:
            raise ValueError("Independent reviewers cannot implement")
        if not isinstance(c["capabilities"], list):
            raise ValueError("Typed capabilities required")
        seen = set()
        for cap in c["capabilities"]:
            if not isinstance(cap, dict) or set(cap) != {"id", "role"} or cap["id"] not in known_caps or cap["role"] not in ("primary", "review", "extension") or cap["id"] in seen:
                raise ValueError("Unknown/duplicate typed capability")
            seen.add(cap["id"])
        if not c["id"].startswith("pack:"):
            actual_primary = {v["id"] for v in c["capabilities"] if v["role"] == "primary"}
            actual_review = {v["id"] for v in c["capabilities"] if v["role"] == "review"}
            expected_primary = {v["id"] for v in taxonomy["capabilities"] if v["primary"] == c["id"]}
            expected_review = {v["id"] for v in taxonomy["capabilities"] if c["id"] in v["reviewers"]} - expected_primary
            if actual_primary != expected_primary or actual_review != expected_review or any(v["role"] == "extension" for v in c["capabilities"]):
                raise ValueError("Professional taxonomy ownership drift")
        elif any(v["role"] != "extension" for v in c["capabilities"]):
            raise ValueError("Optional specialist cannot claim canonical primary ownership")
        tools = c["tool_policy"]
        if not isinstance(tools, dict) or set(tools) != {"required", "conditional", "optional", "empty_required_reason", "observation"} or tools["observation"] != "NOT_OBSERVED_BY_CONTRACT":
            raise ValueError("Tool declaration cannot assert availability")
        if not isinstance(tools["empty_required_reason"], str) or (not tools["required"] and not tools["empty_required_reason"].strip()):
            raise ValueError("Missing rationale for absent essential tools")
        for category in ("required", "conditional", "optional"):
            if not isinstance(tools[category], list):
                raise ValueError("Invalid tool policy")
            for tool in tools[category]:
                if not isinstance(tool, dict) or set(tool) != {"capability", "when", "purpose", "safe_alternative"} or any(not isinstance(v, str) or not v.strip() for v in tool.values()):
                    raise ValueError("Invalid conditional tool contract")
        handoffs = c["handoffs"]
        if not isinstance(handoffs, list) or not handoffs:
            raise ValueError("Missing handoff contract")
        for h in handoffs:
            if not isinstance(h, dict) or set(h) != {"to", "when", "deliver", "acceptance"} or h["to"] not in expected or h["to"] == c["id"] or any(not isinstance(v, str) or not v.strip() for v in h.values()):
                raise ValueError("Invalid professional handoff")
        review = c["review"]
        if not isinstance(review, dict) or set(review) != {"reviewer", "trigger", "independence", "dependency_kind"} or review["reviewer"] not in expected or review["reviewer"] == c["id"] or review["dependency_kind"] != "review_responsibility_not_execution_dependency" or any(not isinstance(v, str) or not v.strip() for v in review.values()):
            raise ValueError("Invalid independent review contract")
        if c["result_contract"] != RESULT_FIELDS:
            raise ValueError("Professional result fields changed without migration")
        q = c["qualification"]
        if not isinstance(q, dict) or set(q) != {"status", "scope", "scenarios", "evidence", "model", "harness_version", "evaluated_at", "expires_on_change"} or q["status"] != "NOT_EVALUATED" or q["evidence"] != [] or not isinstance(q["evidence"], list) or any(q[k] is not None for k in ("model", "harness_version", "evaluated_at")) or q["expires_on_change"] != ["contract", "model", "harness", "tools", "environment"]:
            raise ValueError("Qualification must reference separate measured evidence")
        _strings(q["scenarios"], "qualification scenarios")
        _strings(q["scope"], "qualification scope")
        if not isinstance(c["overlays"], list):
            raise ValueError("Invalid professional overlays")
        for overlay in c["overlays"]:
            if not isinstance(overlay, dict) or set(overlay) != {"id", "when", "procedure", "acceptance", "handoff"} or not isinstance(overlay["id"], str) or not overlay["id"] or not isinstance(overlay["when"], str) or not overlay["when"] or overlay["handoff"] not in expected:
                raise ValueError("Invalid overlay contract")
            _strings(overlay["procedure"], "overlay procedure")
            _strings(overlay["acceptance"], "overlay acceptance")
    return doc


def load_contracts(root=ROOT):
    root = Path(root).absolute()
    return validate_document(_read(root, "professional-contracts-v1.json"), _read(root, "contracts-catalog-v1.json"), _read(root, "taxonomy-v3.json"))


def get_contract(agent_id, root=ROOT):
    for contract in load_contracts(root)["contracts"]:
        if agent_id in (contract["id"], contract["name"]):
            return copy.deepcopy(contract)
    raise ValueError("Unknown specialist contract: " + str(agent_id))


def checkpoints_for(agent_id, root=ROOT):
    c = get_contract(agent_id, root)
    return c["procedure"] + c["definition_of_done"]


def _object(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError("Unknown/missing result " + label + " field")


def _text(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 16000 or any(ord(ch) < 32 and ch not in "\n\t" for ch in value):
        raise ValueError("Invalid result " + label)


def _relative(value, label, allow_dot=False):
    _text(value, label)
    if allow_dot and value == ".":
        return value
    if len(value) > 1024 or "\\" in value or ":" in value or value.startswith("/") or any(part in ("", ".", "..") for part in value.split("/")):
        raise ValueError("Unsafe result " + label + " path")
    # Unicode normalization must not introduce separators, drive syntax or traversal.
    normal = unicodedata.normalize("NFKC", value)
    if normal != value:
        _relative(normal, label, allow_dot)
    return value


def _identifier(value, label):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", value):
        raise ValueError("Invalid result " + label + " identifier")


def result_template(agent_id, *, task_id, obligation_ids, root=ROOT):
    """An honest blocked proposal; filling this template does not create evidence."""
    c = get_contract(agent_id, root)
    ids = list(obligation_ids)
    result = {"task_id": task_id, "agent_id": c["id"], "contract_version": c["contract_version"],
              "obligations": [{"id": oid, "status": "not_verified", "evidence": []} for oid in ids],
              "artifacts": [], "facts": [], "assumptions": [], "decisions": [], "checks": [],
              "not_verified": [{"scope": oid, "reason": "No independent result evidence supplied yet."} for oid in ids],
              "residual_risks": [], "handoff": {"to": c["handoffs"][0]["to"], "obligations": ids, "artifacts": [],
              "acceptance": ["Consumer must corroborate artifacts, checks and obligation coverage independently."], "status": "blocked"}}
    return validate_result(result, c["id"], task_id=task_id, obligation_ids=ids, root=root)


def validate_result(result, agent_id, *, task_id, obligation_ids, root=ROOT):
    """Validate a specialist's untrusted proposal and exact task/contract bindings.

    This is schema/consistency validation ONLY. Artifact hashes, tool execution,
    reviewer identity and semantic correctness need independent supervisor checks.
    No status here promotes a producer claim to verified or consumer-accepted.
    """
    c = get_contract(agent_id, root)
    _object(result, RESULT_FIELDS, "root")
    _identifier(task_id, "task")
    if result["task_id"] != task_id or result["agent_id"] != c["id"] or result["contract_version"] != c["contract_version"]:
        raise ValueError("Result identity/task/contract version mismatch")
    if not isinstance(obligation_ids, (list, tuple)) or not obligation_ids:
        raise ValueError("Expected obligation IDs must be a nonempty unique sequence")
    for oid in obligation_ids:
        _identifier(oid, "obligation")
    if len(set(obligation_ids)) != len(obligation_ids):
        raise ValueError("Expected obligation IDs must be unique")
    for key in ("obligations", "artifacts", "facts", "assumptions", "decisions", "checks", "not_verified", "residual_risks"):
        if not isinstance(result[key], list) or len(result[key]) > 1000:
            raise ValueError("Invalid result " + key + " list")
    paths = set(); normalized_paths = set()
    for artifact in result["artifacts"]:
        _object(artifact, {"path", "sha256"}, "artifact")
        path = _relative(artifact["path"], "artifact")
        normalized = unicodedata.normalize("NFKC", path).casefold()
        if normalized in normalized_paths or not isinstance(artifact["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]):
            raise ValueError("Duplicate artifact or invalid artifact hash")
        paths.add(path); normalized_paths.add(normalized)
    check_ids = set()
    for check in result["checks"]:
        _object(check, {"id", "argv", "cwd", "exit_code", "status", "evidence"}, "check")
        _identifier(check["id"], "check")
        if check["id"] in check_ids:
            raise ValueError("Duplicate result check")
        check_ids.add(check["id"])
        if not isinstance(check["argv"], list) or not check["argv"] or len(check["argv"]) > 256 or any(not isinstance(arg, str) or len(arg) > 16000 or "\x00" in arg for arg in check["argv"]) or not check["argv"][0]:
            raise ValueError("Invalid result check argv")
        _relative(check["cwd"], "check cwd", allow_dot=True)
        code, status = check["exit_code"], check["status"]
        if status not in ("passed", "failed", "not_run") or (code is not None and (not isinstance(code, int) or isinstance(code, bool))):
            raise ValueError("Invalid check outcome")
        if (status == "passed" and code != 0) or (status == "failed" and (code is None or code == 0)) or (status == "not_run" and code is not None):
            raise ValueError("Check status contradicts exit code")
        _strings(check["evidence"], "check evidence", 0)
        if any(ref not in {"artifact:" + p for p in paths} for ref in check["evidence"]):
            raise ValueError("Check evidence must reference a declared artifact")
    references = {"artifact:" + path for path in paths} | {"check:" + cid for cid in check_ids}
    failed_checks = {"check:" + check["id"] for check in result["checks"] if check["status"] != "passed"}
    seen = set(); incomplete = set()
    for obligation in result["obligations"]:
        _object(obligation, {"id", "status", "evidence"}, "obligation")
        oid = obligation["id"]
        _identifier(oid, "obligation")
        if oid in seen or oid not in obligation_ids or obligation["status"] not in ("produced", "blocked", "not_verified"):
            raise ValueError("Duplicate/unknown obligation or forbidden producer status")
        seen.add(oid)
        _strings(obligation["evidence"], "obligation evidence", 0)
        if not set(obligation["evidence"]) <= references:
            raise ValueError("Unknown obligation evidence reference")
        if obligation["status"] == "produced" and (not obligation["evidence"] or set(obligation["evidence"]) & failed_checks):
            raise ValueError("Produced obligation lacks consistent evidence")
        if obligation["status"] != "produced":
            incomplete.add(oid)
    if seen != set(obligation_ids):
        raise ValueError("Result obligation coverage mismatch")
    for fact in result["facts"]:
        _object(fact, {"statement", "evidence"}, "fact")
        _text(fact["statement"], "fact")
        _strings(fact["evidence"], "fact evidence")
        if not set(fact["evidence"]) <= references:
            raise ValueError("Fact evidence reference is unknown")
    _strings(result["assumptions"], "assumptions", 0)
    for decision in result["decisions"]:
        _object(decision, {"decision", "alternatives", "rationale"}, "decision")
        _text(decision["decision"], "decision"); _text(decision["rationale"], "decision rationale")
        _strings(decision["alternatives"], "decision alternatives")
    unknown_scopes = set()
    for item in result["not_verified"]:
        _object(item, {"scope", "reason"}, "not_verified")
        _text(item["scope"], "not_verified scope"); _text(item["reason"], "not_verified reason")
        unknown_scopes.add(item["scope"])
    if not incomplete <= unknown_scopes:
        raise ValueError("Incomplete obligations need explicit not_verified reasons")
    if (seen - incomplete) & unknown_scopes:
        raise ValueError("Produced obligation contradicts not_verified scope")
    for risk in result["residual_risks"]:
        _object(risk, {"risk", "severity", "mitigation"}, "risk")
        _text(risk["risk"], "risk"); _text(risk["mitigation"], "mitigation")
        if risk["severity"] not in ("low", "medium", "high", "critical", "unknown"):
            raise ValueError("Invalid result risk severity")
    handoff = result["handoff"]
    _object(handoff, {"to", "obligations", "artifacts", "acceptance", "status"}, "handoff")
    destinations = {h["to"] for h in c["handoffs"]} | {"A00"}
    if handoff["to"] not in destinations or handoff["to"] == c["id"] or handoff["status"] not in ("pending_consumer_acceptance", "blocked"):
        raise ValueError("Unknown/self handoff or forbidden producer acceptance")
    _strings(handoff["obligations"], "handoff obligations")
    _strings(handoff["artifacts"], "handoff artifacts", 0)
    _strings(handoff["acceptance"], "handoff acceptance")
    if not set(handoff["obligations"]) <= seen or not set(handoff["artifacts"]) <= paths:
        raise ValueError("Handoff references undeclared obligations/artifacts")
    if handoff["status"] == "pending_consumer_acceptance" and set(handoff["obligations"]) & incomplete:
        raise ValueError("Incomplete obligation cannot be handed off as produced")
    return copy.deepcopy(result)


def render_contract(contract):
    """Small generated prompt; full contract is loaded only for assigned work."""
    c = contract
    lines = ["", "Contrato profissional " + c["contract_version"] + " (" + c["id"] + ").", "Modos permitidos: " + ", ".join(c["modes"]) + ".", "Entradas: " + "; ".join(c["inputs"]), "Método proporcional:"]
    lines += ["- " + item for item in c["procedure"]]
    lines += ["Entregáveis: " + "; ".join(c["artifacts"]), "Conclua somente quando:"]
    lines += ["- " + item for item in c["definition_of_done"]]
    lines += ["Limites: " + "; ".join(c["non_goals"]), "Ferramentas são necessidades declaradas, não disponibilidade ou permissões; observar a capacidade real antes do uso. Dependência essencial indisponível bloqueia o check correspondente.", "Handoff: fornecer tarefa/obrigações, artefatos/hashes, fatos/hipóteses, decisões, checks/resultados, não verificados, riscos e aceite pelo consumidor.", "Consultar core/professional-contracts-v1.json dentro do runtime Guardian indicado pelo AGENTS.md instalado, sob demanda para ferramentas, handoffs, overlays e cenários. Qualificação profissional: NOT_EVALUATED; smoke de execução não certifica competência."]
    for overlay in c["overlays"]:
        lines += ["Overlay " + overlay["id"] + " quando " + overlay["when"] + ": " + "; ".join(overlay["procedure"]) + ". Aceite: " + "; ".join(overlay["acceptance"])]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("agent", nargs="?")
    args = parser.parse_args()
    value = get_contract(args.agent) if args.agent else {"valid": True, "contracts": len(load_contracts()["contracts"]), "qualification": "NOT_EVALUATED"}
    print(json.dumps(value, ensure_ascii=True, indent=2))
