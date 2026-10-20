"""Opt-in worktree integration tests; local mock Codex, no quota or GitHub operations."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.guardian_platform import create_plan
from tools.guardian_executor import execute, initialize
from tools.guardian_integrate import IntegrationError, inspect, integrate


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        folder = Path(tmp.name).resolve()
        self.repo = folder / "project"
        self.repo.mkdir()
        self.home = folder / "state"
        def git(*args):
            subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True)
        git("init", "-q")
        (self.repo / "service.py").write_text("BASELINE = True\n")
        (self.repo / "AGENTS.md").write_text("Code review required.\n")
        git("add", ".")
        git("-c", "user.name=Guardian Tests", "-c", "user.email=ci@example.invalid", "commit", "-q", "-m", "Base")
        self.plan = create_plan("Implement safe ASP.NET Core validation in service")
        for task in self.plan["tasks"]:
            task["contract"].update(operation="write", allowed_paths=["service.py", "AGENTS.md", "new-unknown.txt"], checks=[[sys.executable, "-V"]], idempotent=False)
        self.briefs = {task["id"]: "Apply only a minimal mock service change to the tracked test file, with no other modifications." for task in self.plan["tasks"]}
        initialize(self.plan, self.repo, self.home, briefs=self.briefs)

    def finish(self, *, protected=False, untracked=False):
        def mock_run(codex, worktree, prompt, timeout, logs, mode):
            logs.parent.mkdir(parents=True, exist_ok=True)
            logs.write_text('{"type":"thread.started","thread_id":"mock"}\n{"type":"turn.completed"}\n')
            if protected:
                (worktree / "AGENTS.md").write_text("Changes without approval!\n")
            elif untracked:
                (worktree / "new-unknown.txt").write_text("unknown")
            else:
                (worktree / "service.py").write_text("BASELINE = False\n")
            return 0, True, "mock"
        with patch("tools.guardian_executor._process", side_effect=mock_run):
            result = execute(self.home, apply=True, codex_binary=sys.executable, authorize_writes=True)
        self.assertEqual(result["overall"], "blocked" if protected else "produced")

    def test_preview_cannot_touch_base_repository(self):
        self.finish()
        result, patch = inspect(self.home)
        self.assertTrue(result["git_apply_check"])
        self.assertEqual(result["files_changed"], 1)
        self.assertFalse(result["applied"])
        self.assertTrue(patch)
        self.assertEqual((self.repo / "service.py").read_text(), "BASELINE = True\n")

    def test_explicit_hash_confirmed_integration(self):
        self.finish()
        report = integrate(self.home)
        with self.assertRaises(IntegrationError):
            integrate(self.home, apply=True, confirm_sha256="0"*64)
        result = integrate(self.home, apply=True, confirm_sha256=report["patch_sha256"])
        self.assertTrue(result["applied"])
        self.assertFalse(result["committed"])
        self.assertEqual((self.repo / "service.py").read_text(), "BASELINE = False\n")
        with self.assertRaises(IntegrationError):
            integrate(self.home)  # original source now intentionally dirty

    def test_untracked_changes_require_manual_integration(self):
        self.finish(untracked=True)
        with self.assertRaises(IntegrationError):
            integrate(self.home)

    def test_policy_file_changes_require_manual_integration(self):
        self.finish(protected=True)
        with self.assertRaises(IntegrationError):
            integrate(self.home)

    def test_worktree_drift_after_execution_invalidates_review(self):
        self.finish()
        (self.home/'worktree'/'service.py').write_text('UNREVIEWED = True\n')
        with self.assertRaisesRegex(IntegrationError,'changed after'):
            integrate(self.home)

    def test_protected_source_rename_cannot_hide_behind_safe_destination(self):
        import json
        from tools.guardian_executor import _plan_hash, atomic_json
        from tools.guardian_runtime import inventory
        self.finish()
        worktree=self.home/'worktree'
        subprocess.run(['git','-C',str(worktree),'mv','AGENTS.md','ordinary.txt'],check=True,capture_output=True)
        # Refresh only the artifact seal to isolate the protected-path check;
        # a normal post-run modification is already rejected by the drift gate.
        path=self.home/'state.json'; state=json.loads(path.read_text())
        last=max(state['tasks'].values(),key=lambda r:r['started_at_ns'])
        last['artifact_sha256']=_plan_hash(inventory(worktree));atomic_json(path,state)
        with self.assertRaisesRegex(IntegrationError,'Protected'):
            integrate(self.home)



if __name__ == "__main__":
    unittest.main()
