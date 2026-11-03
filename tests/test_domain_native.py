"""Real reviewed-fixture adapters; missing OS/runtime boundaries are explicit skips.

Use guardian_domain_native.py for the complete acceptance record: its exit code
is nonzero for any blocked adapter, whereas portable unittest permits skips.
"""
from pathlib import Path
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from tools import guardian_domain_native as native


class DomainNativeTests(unittest.TestCase):
    def test_ui_job_assignment_failure_never_releases_fixture_gate(self):
        process = Mock(); process.poll.return_value = None
        with patch.dict(os.environ, {'NODE_OPTIONS':'--require=untrusted.js', 'NODE_PATH':'untrusted',
                                   'NODE_V8_COVERAGE':'outside', 'NODE_COMPILE_CACHE':'outside-cache'}), \
             patch.object(native, '_WINDOWS', True), \
             patch.object(native.subprocess, 'CREATE_NEW_PROCESS_GROUP', 512, create=True), \
             patch.object(native.subprocess, 'Popen', return_value=process) as launch, \
             patch.object(native, '_BrowserJob', side_effect=PermissionError('Job assignment denied')):
            with self.assertRaises(PermissionError): native._ui_process(['node', 'fixture.cjs'], Path('.'))
        process.communicate.assert_not_called()
        process.kill.assert_called_once()
        process.wait.assert_called_once_with(timeout=5)
        self.assertTrue(all(name not in launch.call_args.kwargs['env'] for name in
                            ('NODE_OPTIONS', 'NODE_PATH', 'NODE_V8_COVERAGE', 'NODE_COMPILE_CACHE')))

    def test_profile_cleanup_retries_only_transient_sharing_violation(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp).resolve(); profile = work/'profile'; profile.mkdir()
            (profile/'owned').write_text('fixture')
            failure = PermissionError('owned file still closing'); failure.winerror = 32
            real_remove = native.shutil.rmtree; attempts = []
            def remove(target):
                attempts.append(target)
                if len(attempts) <= 2:
                    failure.winerror = 32 if len(attempts) == 1 else 33
                    raise failure
                return real_remove(target)
            with patch.object(native, '_WINDOWS', True), patch.object(native.shutil, 'rmtree', side_effect=remove), \
                 patch.object(native.time, 'sleep'):
                native._remove_owned_profile(profile, work)
            self.assertEqual(len(attempts), 3)
            self.assertFalse(profile.exists())

    def test_profile_cleanup_does_not_hide_exhausted_or_unrelated_error(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp).resolve(); profile = work/'profile'; profile.mkdir()
            sentinel = profile/'owned'; sentinel.write_text('keep')
            for code in (32, 5):
                failure = PermissionError('still locked or denied'); failure.winerror = code
                with patch.object(native, '_WINDOWS', True), \
                     patch.object(native.shutil, 'rmtree', side_effect=failure) as remove, \
                     patch.object(native.time, 'monotonic', side_effect=[0, 6]):
                    with self.assertRaises(PermissionError): native._remove_owned_profile(profile, work)
                remove.assert_called_once_with(profile)
                self.assertEqual(sentinel.read_text(), 'keep')

    def test_profile_cleanup_rejects_other_path_and_reparse_ancestor(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp).resolve(); other = work/'outside'; other.mkdir()
            sentinel = other/'keep'; sentinel.write_text('original')
            with self.assertRaises(ValueError): native._remove_owned_profile(other, work)
            profile = work/'profile'; profile.mkdir()
            original = Path.is_symlink
            with patch.object(Path, 'is_symlink', lambda path: path == work or original(path)), \
                 patch.object(native.shutil, 'rmtree') as remove:
                with self.assertRaises(ValueError): native._remove_owned_profile(profile, work)
            remove.assert_not_called()
            self.assertEqual(sentinel.read_text(), 'original')

    @unittest.skipUnless(os.name == 'nt', 'Windows Job Object lifecycle requires Windows')
    def test_real_ui_job_stops_descendant_after_node_exit_without_killing_other_process(self):
        node = native.shutil.which('node')
        if not node: self.skipTest('Node unavailable')
        # Use the adapter's actual startup budget, not a shorter CI-only limit.
        # The control must outlive startup plus bounded job teardown so that its
        # natural exit cannot be confused with termination by the adapter.
        unrelated = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(120)'],
                                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            with tempfile.TemporaryDirectory() as temp:
                work = Path(temp).resolve(); script = work/'owned.cjs'
                script.write_text("const {spawn}=require('node:child_process');"
                    "const c=spawn(process.execPath,['-e',\"process.stdout.write('ready');setInterval(()=>{},1000)\"],{detached:true,windowsHide:true,stdio:['ignore','pipe','ignore']});"
                    "c.stdout.once('data',()=>{process.stdout.write(JSON.stringify({child:c.pid,ready:true}));c.stdout.destroy();c.unref()});", encoding='utf8')
                completed = native._ui_process([node, str(script)], work, timeout=45)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertTrue(json.loads(completed.stdout)['ready'])
                child_pid = json.loads(completed.stdout)['child']
                import ctypes
                from ctypes import wintypes
                kernel = ctypes.WinDLL('kernel32', use_last_error=True)
                kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
                kernel.OpenProcess.restype = wintypes.HANDLE
                kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
                kernel.CloseHandle.argtypes = [wintypes.HANDLE]
                handle = kernel.OpenProcess(0x00100000, False, child_pid)
                if handle:
                    try: self.assertEqual(kernel.WaitForSingleObject(handle, 5000), 0)
                    finally: kernel.CloseHandle(handle)
                else: self.assertEqual(ctypes.get_last_error(), 87)
                self.assertIsNone(unrelated.poll(), 'A different owned test process must remain alive')
        finally:
            if unrelated.poll() is None: unrelated.kill()
            unrelated.wait(timeout=5)

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
