"""Synthetic benchmark fixture generation: offline, reproducible logic and external grading."""
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from tools.guardian_benchmark_fixture import create
from tools.guardian_eval_runner import fixture, grade, run


class BenchmarkFixtureTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.path = Path(t.name).resolve() / "fixture"

    def test_fixture_isolated_and_baseline_has_expected_failures(self):
        result = create(self.path)
        self.assertTrue(result["created"])
        project = Path(result["project"])
        checker = Path(result["checker"])
        self.assertNotIn(project, checker.parents)
        cases = fixture(json.loads(Path(result["dataset"]).read_text(encoding="utf-8")))
        self.assertEqual(len(cases["cases"]), 3)
        from tools.guardian_grader_sandbox import validate_oracle
        self.assertEqual(len(validate_oracle(json.loads(checker.read_text()))["cases"]), 3)
        with patch("tools.guardian_grader_sandbox.probe", return_value={"available":False,"reason":"No backend"}):
            for case in cases["cases"]:
                with self.assertRaises(ValueError):
                    grade(checker, case["case_id"], project, case["checks"], 10)
        preview = run(cases, project, checker, self.path / "results",
                      "placeholder-model", "medium", 2, 60,
                      candidate_guidance=Path(result["candidate_guide"]).read_text())
        self.assertTrue(preview["dry_run"])
        self.assertEqual(preview["experiments"], 12)
        self.assertFalse((self.path / "results").exists())

    def test_no_replacement_of_existing_evaluation_data(self):
        create(self.path)
        with self.assertRaises(ValueError):
            create(self.path)

    def test_grader_accepts_correct_small_fix(self):
        result = create(self.path)
        project = Path(result["project"])
        (project / "money.py").write_text(
            "def sum_minor_units(amount, fee):\n"
            "    if type(amount) is not int or type(fee) is not int: raise TypeError()\n"
            "    if amount < 0 or fee < 0: raise ValueError()\n"
            "    return amount + fee\n", encoding="utf-8")
        from tools.guardian_grader_sandbox import probe
        if not probe()["available"]:
            self.skipTest("Real sandbox backend unavailable: native grading NOT VERIFIED")
        self.assertTrue(grade(Path(result["checker"]), "money", project, ["main"], 10))


if __name__ == "__main__":
    unittest.main()
