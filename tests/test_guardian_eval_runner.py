"""Offline A/B evaluation tests with locally mocked Codex and real isolated Git."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.guardian_eval_runner import EvalError, fixture, run
from tools.guardian_grader_sandbox import validate_oracle


class NativeBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name).resolve()
        self.project = root / "project"
        self.output = root / "runs"
        self.checker = root / "grader" / "trusted_checker.py"
        self.checker.parent.mkdir()
        self.checker.write_text(
            "import argparse\nfrom pathlib import Path\n"
            "p=argparse.ArgumentParser()\n"
            "p.add_argument('--workspace',required=True)\n"
            "p.add_argument('--case',required=True)\n"
            "p.add_argument('--checks',required=True)\n"
            "a=p.parse_args()\n"
            "assert (Path(a.workspace)/'answer.txt').read_text() == 'good\\n'\n",
            encoding="utf-8",
        )
        self.project.mkdir()
        def git(*args):
            subprocess.run(["git", "-C", str(self.project), *args], check=True, capture_output=True, timeout=20)
        git("init", "-q")
        (self.project / "answer.txt").write_text("bad\n")
        git("add", "answer.txt")
        git("-c", "user.email=ci@example.invalid", "-c", "user.name=CI", "commit", "-q", "-m", "baseline")
        self.dataset = {"schema_version": 1, "dataset_version":"test-v1", "split":"holdout", "cases": [
            {"case_id": "fix_answer", "prompt": "Fix answer.txt to contain the expected result", "checks": ["expected"]}
        ]}

    def test_preview_does_not_mutate(self):
        result = run(self.dataset, self.project, self.checker, self.output,
                     "test-model", "medium", 2, 120)
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["experiments"], 4)
        self.assertFalse(self.output.exists())

    def test_pairing_and_unavailable_token_count(self):
        calls = []
        self.checker.write_text(json.dumps({"schema_version":2,"cases":{"fix_answer":{"checks":{"expected":[{"file":"target.py","function":"answer","args":[],"expected":{"kind":"value","value":1}}]}}}}))
        config = self.project.parent / "config"
        config.mkdir()
        (config / "config.toml").write_text('model = "test-model"\n')
        def fake(codex, project, prompt, model, effort, timeout, event_path, config_home):
            calls.append((model, effort, prompt))
            (project / "answer.txt").write_text("good\n")
            event_path.parent.mkdir(parents=True, exist_ok=True)
            event_path.write_text('{"type":"turn.completed"}\n')
            return 0, True, None
        with patch("tools.guardian_eval_runner._codex", side_effect=fake), patch("tools.guardian_eval_runner.probe", return_value={"available":True}), patch("tools.guardian_eval_runner.grade_oracle", return_value={"passed":True,"checks":[{"check":"expected","vector":0,"passed":True}]}):
            result = run(self.dataset, self.project, self.checker, self.output,
                         "test-model", "medium", 1, 120, apply=True, codex_binary=sys.executable,
                         candidate_guidance="Guardian: verify contract invariants and error paths with actual tests.", isolated_config=config)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result["paired_samples"], 1)
        self.assertTrue(result["native_codex_run"])
        self.assertRegex(result["candidate_guidance_sha256"],r"^[0-9a-f]{64}$")
        self.assertFalse(result["all_token_counts_verified"])
        self.assertIsNone(result["baseline"]["mean_token_count"])
        self.assertFalse(result["sufficient_for_general_claim"])
        self.assertEqual((self.project / "answer.txt").read_text(), "bad\n")

    def test_missing_guardian_guidance_blocks_live_run(self):
        with self.assertRaises(EvalError):
            run(self.dataset, self.project, self.checker, self.output,
                "test-model", "medium", 1, 120, apply=True,
                codex_binary=sys.executable)

    def test_checker_inside_repo_rejected(self):
        unsafe = self.project / "checker.py"
        unsafe.write_text("print(1)\n")
        with self.assertRaises(EvalError):
            run(self.dataset, self.project, unsafe, self.output, "test-model", "medium", 1, 120)

    def test_bad_dataset_rejected(self):
        with self.assertRaises(EvalError):
            fixture({"schema_version": 1, "cases": [
                {"case_id": "../test", "prompt": "test", "checks": ["expected"]}
            ]})

    def test_mismatched_run_budgets_rejected(self):
        with self.assertRaises(EvalError):
            run(self.dataset, self.project, self.checker, self.output,
                "test-model", "medium", 50, 120)


if __name__ == "__main__":
    unittest.main()
