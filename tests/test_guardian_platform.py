"""Tests for lifecycle, bounded routing, verification and comparable benchmarks.

These tests do not invoke Codex, external services or modify user files.
"""
import copy
import unittest
from pathlib import Path

from tools.guardian_benchmark import BenchmarkError, compare
from tools.guardian_platform import (
    ROOT, PlatformError, STAGES, create_plan, load_workflows,
    security_lint, validate_evidence, validate_plan,
)


class LifecycleTests(unittest.TestCase):
    def test_all_twelve_stages_exist(self):
        workflow = load_workflows()
        self.assertEqual(tuple(x["id"] for x in workflow["phases"]), STAGES)
        self.assertTrue(all(x["criteria"] for x in workflow["phases"]))

    def test_primary_agent_references_are_known(self):
        from tools.guardian_registry import discover
        known = {x["id"] for x in discover(ROOT)["core"]}
        for phase in load_workflows()["phases"]:
            self.assertTrue(set(phase["responsible"]) <= known)


class PlanningTests(unittest.TestCase):
    def test_simple_backend_plan_is_readonly(self):
        plan = create_plan("Corrigir service ASP.NET Core do backend")
        self.assertEqual(plan["status"], "proposal_only")
        self.assertFalse(plan["native_delegation_performed"])
        self.assertFalse(plan["human_authorization_required"])
        self.assertTrue(all(x["write_ownership"] == "unassigned" for x in plan["tasks"]))
        self.assertEqual(validate_plan(plan)["tasks"], len(plan["tasks"]))

    def test_audit_review_is_later_wave(self):
        plan = create_plan("Auditar completamente o projeto", mode="audit")
        reviews = [x for x in plan["tasks"] if x["agent_id"] == "G01"]
        workers = [x for x in plan["tasks"] if x["agent_id"] not in ("G01", "G02")]
        self.assertTrue(reviews)
        self.assertGreater(min(x["wave"] for x in reviews), max(x["wave"] for x in workers))

    def test_high_risk_requires_human(self):
        plan = create_plan("Corrigir transferências PIX simultâneas e saldo incorreto", max_agents=29)
        self.assertTrue(plan["human_authorization_required"])
        self.assertEqual(plan["risk"], "high")

    def test_invalid_secrets_rejected(self):
        with self.assertRaises(PlatformError):
            create_plan("debug api_key=abc123")

    def test_agent_budget_does_not_silently_drop_agents(self):
        with self.assertRaises(PlatformError):
            create_plan("Corrigir service ASP.NET Core do backend", max_agents=1)

    def test_proposal_must_not_claim_execution(self):
        plan = create_plan("Corrigir service ASP.NET Core do backend")
        plan["native_delegation_performed"] = True
        with self.assertRaises(PlatformError):
            validate_plan(plan)

    def test_cycle_or_invalid_wave_rejected(self):
        plan = create_plan("Auditar completamente o projeto", mode="audit")
        first = plan["tasks"][0]
        first["depends_on"] = [first["id"]]
        with self.assertRaises(PlatformError):
            validate_plan(plan)

    def test_evidence_is_not_authentication(self):
        plan = create_plan("Corrigir service ASP.NET Core do backend")
        report = {
            "schema_version": 1,
            "tasks": [
                {
                    "task_id": x["id"],
                    "status": "completed",
                    "files_examined": ["service.cs"],
                    "commands": [{"command": "dotnet test", "exit_code": 0}],
                    "limitations": ["No production access"],
                }
                for x in plan["tasks"]
            ],
        }
        result = validate_evidence(report, plan)
        self.assertTrue(result["complete_claims_with_required_fields"])
        self.assertFalse(result["authenticated_execution"])
        self.assertFalse(result["release_authorized"])

    def test_incomplete_evidence_is_detected(self):
        plan = create_plan("Corrigir service ASP.NET Core do backend")
        result = validate_evidence({"schema_version": 1, "tasks": []}, plan)
        self.assertFalse(result["complete_claims_with_required_fields"])
        self.assertTrue(result["missing"])

    def test_configuration_lint_scope_is_explicit(self):
        report = security_lint()
        self.assertTrue(report["ok"], report["findings"])
        self.assertFalse(report["security_certified"])


class BenchmarkTests(unittest.TestCase):
    def payload(self, group, outcomes=(True, False)):
        return {
            "schema_version": 1,
            "group": group,
            "environment": {
                "model": "same-model",
                "effort": "medium",
                "sandbox": "workspace-write",
                "machine_class": "runner-x64",
                "dataset_version": "v1",
            },
            "samples": [
                {
                    "case_id": "case-" + str(i),
                    "repeat": 0,
                    "passed": value,
                    "duration_seconds": 10 + i,
                    "token_count": 100 + i,
                }
                for i, value in enumerate(outcomes)
            ],
        }

    def test_paired_delta_and_limits(self):
        base = self.payload("baseline", (False, True))
        new = self.payload("candidate", (True, True))
        report = compare(base, new)
        self.assertEqual(report["paired_improvements"], 1)
        self.assertEqual(report["paired_regressions"], 0)
        self.assertEqual(report["pass_rate_delta"], .5)
        self.assertFalse(report["sufficient_for_general_claim"])

    def test_non_comparable_model_rejected(self):
        base = self.payload("baseline")
        new = self.payload("candidate")
        new["environment"]["model"] = "different"
        with self.assertRaises(BenchmarkError):
            compare(base, new)

    def test_missing_case_rejected(self):
        base = self.payload("baseline")
        new = self.payload("candidate")
        new["samples"].pop()
        with self.assertRaises(BenchmarkError):
            compare(base, new)

    def test_duplicate_sample_rejected(self):
        base = self.payload("baseline")
        base["samples"].append(copy.deepcopy(base["samples"][0]))
        with self.assertRaises(BenchmarkError):
            compare(base, self.payload("candidate"))


if __name__ == "__main__":
    unittest.main()
