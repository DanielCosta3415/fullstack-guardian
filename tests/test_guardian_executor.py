"""Isolated executor tests: real local git, mocked Codex CLI, no network or quota."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.guardian_executor import (
    ExecutionError, execute, initialize, preflight, safe, status,
)
from tools.guardian_platform import create_plan


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, timeout=20)


class ExecutorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parent = Path(self.tmp.name).resolve()
        self.repo = parent / "repo"
        self.repo.mkdir()
        self.home = parent / "state"
        git(self.repo, "init", "-q")
        (self.repo / "example.txt").write_text("baseline\n")
        git(self.repo, "add", "example.txt")
        git(self.repo, "-c", "user.name=CI Test", "-c", "user.email=test@example.invalid", "commit", "-q", "-m", "test base")
        self.plan = create_plan("Corrigir service ASP.NET Core do backend")
        self.briefs = {t["id"]: "Review the ASP.NET Core service test boundary and implement a minimal testable change." for t in self.plan["tasks"]}

    def test_execution_requires_explicit_briefs(self):
        initialize(self.plan, self.repo, self.home)
        with self.assertRaises(ExecutionError):
            execute(self.home, apply=True, codex_binary=sys.executable)

    def test_brief_tampering_is_rejected(self):
        initialize(self.plan, self.repo, self.home, briefs=self.briefs)
        path = self.home / "briefs.json"
        content = json.loads(path.read_text())
        key = next(iter(content))
        content[key] = "A different request with no authorization and too much scope"
        path.write_text(json.dumps(content))
        with self.assertRaises(ExecutionError):
            execute(self.home, apply=True, codex_binary=sys.executable)

    def test_init_creates_state_but_not_git_worktree(self):
        result = initialize(self.plan, self.repo, self.home, briefs=self.briefs)
        self.assertEqual(result["overall"], "initialized")
        self.assertFalse((self.home / "worktree").exists())
        self.assertTrue((self.home / "state.json").exists())

    def test_dry_run_does_not_consume_codex(self):
        initialize(self.plan, self.repo, self.home)
        result = execute(self.home, apply=False)
        self.assertTrue(result["dry_run"])
        self.assertFalse((self.home / "worktree").exists())

    def test_clean_repo_required(self):
        (self.repo / "untracked.txt").write_text("uncommitted")
        with self.assertRaises(ExecutionError):
            initialize(self.plan, self.repo, self.home)

    def test_high_risk_plan_is_rejected_before_execution(self):
        high = create_plan("Corrigir transferências PIX simultâneas e saldo incorreto", max_agents=29)
        with self.assertRaises(ExecutionError):
            initialize(high, self.repo, self.home)
        self.assertFalse(self.home.exists())

    def test_successful_mock_codex_turns_share_isolated_worktree(self):
        initialize(self.plan, self.repo, self.home, briefs=self.briefs)
        seen = []
        def fake_process(codex, worktree, prompt, timeout, logs, mode):
            seen.append(worktree)
            logs.parent.mkdir(parents=True, exist_ok=True)
            logs.write_text('{"type":"thread.started","thread_id":"fake-test"}\n{"type":"turn.completed"}\n')
            with (worktree / "example.txt").open("a") as f:
                f.write("synthetic changed\n")
            return 0, True, "fake-test"
        with patch("tools.guardian_executor._process", side_effect=fake_process):
            result = execute(self.home, apply=True, codex_binary=sys.executable, max_tasks=29)
        self.assertEqual(result["overall"], "completed")
        self.assertEqual(len(set(seen)), 1)
        self.assertEqual((self.repo / "example.txt").read_text(), "baseline\n")
        self.assertIn("synthetic changed", (self.home / "worktree" / "example.txt").read_text())
        self.assertFalse(status(self.home)["native_subagents_verified"])

    def test_missing_completed_event_is_failure_and_resume_is_explicit(self):
        initialize(self.plan, self.repo, self.home, briefs=self.briefs)
        def bad(codex, worktree, prompt, timeout, logs, mode):
            logs.parent.mkdir(parents=True, exist_ok=True)
            logs.write_text('{"type":"turn.failed"}\n')
            return 1, False, None
        with patch("tools.guardian_executor._process", side_effect=bad):
            result = execute(self.home, apply=True, codex_binary=sys.executable)
        self.assertEqual(result["overall"], "blocked")
        self.assertEqual(result["completed"], 0)
        with patch("tools.guardian_executor._process", side_effect=bad):
            again = execute(self.home, apply=True, codex_binary=sys.executable)
        self.assertEqual(again["executed_this_run"], 0)

    def test_plan_modification_detected(self):
        initialize(self.plan, self.repo, self.home)
        p = self.home / "plan.json"
        content = json.loads(p.read_text())
        content["stage"] = "operations"
        p.write_text(json.dumps(content))
        with self.assertRaises(ExecutionError):
            status(self.home)

    def test_repository_changes_after_init_block_execution(self):
        initialize(self.plan, self.repo, self.home)
        (self.repo / "dirty.txt").write_text("dirty")
        with self.assertRaises(ExecutionError):
            execute(self.home, apply=True, codex_binary=sys.executable)

    def test_unsafe_path_components_rejected(self):
        real = self.home.parent / "actual"
        real.mkdir()
        link = self.home.parent / "linked"
        try:
            link.symlink_to(real, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable")
        with self.assertRaises(ExecutionError):
            safe(link / "entry.json")


if __name__ == "__main__":
    unittest.main()
