"""Real reviewed-fixture adapters; missing OS/runtime boundaries are explicit skips.

Use guardian_domain_native.py for the complete acceptance record: its exit code
is nonzero for any blocked adapter, whereas portable unittest permits skips.
"""
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from tools import guardian_domain_native as native


class DomainNativeTests(unittest.TestCase):
    def adapter(self, domain):
        report = native.run_suite([domain])
        self.assertEqual(len(report["results"]), 1)
        result = report["results"][0]
        if result["status"] == "BLOCKED":
            self.skipTest(result["limitation"])
        self.assertEqual(result["status"], "PASSED", result)
        self.assertGreaterEqual(len(result["checks"]), 3)
        self.assertFalse(result["production_verified"])
        self.assertFalse(result["llm_verified"])
        return result

    def test_dotnet_native_checked_overflow_and_cancellation(self):
        self.adapter("dotnet")

    def test_api_real_http_positive_and_invalid_contracts(self):
        self.adapter("api")

    def test_financial_real_sqlite_replay_conflict_overdraft_and_rollback(self):
        report = self.adapter("financial")
        self.assertEqual(len(report["checks"]), 7)

    def test_data_real_sqlite_migration_reconciliation_and_rollback(self):
        self.adapter("data")

    def test_ui_real_browser_dom_keyboard_and_accessibility(self):
        self.adapter("ui")

    def test_powershell_native_whatif_apply_and_overwrite(self):
        self.adapter("powershell")

    def test_cloudplan_offline_policy_positive_and_denials(self):
        report = self.adapter("cloudplan")
        self.assertIn("no-deployment", report["execution_boundary"])

    def test_ai_extractive_retrieval_injection_and_canary_without_llm(self):
        report = self.adapter("ai")
        self.assertIn("no-llm", report["execution_boundary"])

    def test_unknown_and_duplicate_domain_rejected(self):
        for domains in (["unknown"], ["api", "api"]):
            with self.assertRaises(ValueError):
                native.run_suite(domains)

    def test_empty_checks_and_false_observations_cannot_pass(self):
        self.assertEqual(native.result("api", [], "fake")["status"], "FAILED")
        for observation in (False, "true", 1, {"passed": True}, None):
            self.assertFalse(native.check("untrusted", observation)["passed"])

    def test_missing_native_runtime_is_blocked_and_never_verified(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(native.shutil, "which", return_value=None):
            result = native.dotnet_adapter(Path(temp))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["production_verified"])

    def test_sandbox_denial_is_blocked_not_a_success_or_an_application_failure(self):
        def denied(work):
            raise PermissionError("fixture boundary denied")
        with patch.dict(native.ADAPTERS, {"api": denied}):
            report = native.run_suite(["api"])
        self.assertEqual(report["blocked"], 1)
        self.assertEqual(report["failed"], 0)
        self.assertFalse(report["all_fixture_adapters_passed"])

    def test_unexpected_runtime_failure_fails_acceptance(self):
        def failed(work):
            raise ValueError("malformed native result")
        with patch.dict(native.ADAPTERS, {"api": failed}):
            report = native.run_suite(["api"])
        self.assertEqual(report["failed"], 1)
        self.assertFalse(report["all_fixture_adapters_passed"])

    def test_policy_rejects_boolean_version_and_nested_wrong_types(self):
        base = {"version": 1, "statements": [{"effect": "Allow", "actions": ["storage:GetObject"],
                 "resources": ["synthetic-fixture-bucket"], "principal": "synthetic-worker"}]}
        self.assertTrue(native.evaluate_plan(base))
        base["statements"][0]["actions"] = [True]
        self.assertFalse(native.evaluate_plan(base))
        base["statements"][0]["actions"] = ["storage:GetObject"]
        base["version"] = True
        self.assertFalse(native.evaluate_plan(base))

    def test_money_transfer_rejects_fraction_and_replay_mismatch_without_mutation(self):
        with sqlite3.connect(":memory:") as db:
            db.executescript("CREATE TABLE account(id INTEGER PRIMARY KEY,units INTEGER NOT NULL);"
                             "CREATE TABLE transfer(key TEXT PRIMARY KEY,amount INTEGER NOT NULL);"
                             "INSERT INTO account VALUES(1,100),(2,0);")
            native.transfer(db, "id", 10)
            for value in (10.1, True, -1, 2**63, 11):
                with self.assertRaises(ValueError):
                    native.transfer(db, "id", value)
            self.assertEqual(db.execute("SELECT units FROM account ORDER BY id").fetchall(), [(90,), (10,)])
            self.assertEqual(db.execute("SELECT COUNT(*) FROM transfer").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
