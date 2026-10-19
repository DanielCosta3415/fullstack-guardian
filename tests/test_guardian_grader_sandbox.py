"""Adversarial grading regressions; native tests explicitly require real sandbox."""
import json
from pathlib import Path
import tempfile
import unittest
import io
import subprocess
from unittest.mock import patch
from tools.guardian_grader_sandbox import (probe, strict_json, validate_oracle,
    grade_oracle, SandboxUnavailable, container_command, execute_vector, _same, validate_pure_target)


class GraderBoundaryTests(unittest.TestCase):
    def test_legacy_python_grader_never_runs_on_host(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sentinel = root / "escaped"
            checker = root / "grader.py"
            checker.write_text("from pathlib import Path\nPath(" + repr(str(sentinel)) + ").touch()\n")
            with self.assertRaises(ValueError):
                grade_oracle(checker, "case", root, ["main"], 1)
            self.assertFalse(sentinel.exists())

    def test_output_rejects_duplicate_keys_extra_content_and_nonfinite(self):
        for forged in ('{"kind":"exception","kind":"value"}', '{}\n{}', 'NaN'):
            with self.assertRaises(ValueError):
                strict_json(forged)
        self.assertFalse(_same({"kind":"value","value":True}, {"kind":"value","value":1}))

    def test_no_backend_fails_closed_and_missing_checks_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            checker = root / "oracle.json"
            checker.write_text(json.dumps(oracle()))
            with patch("tools.guardian_grader_sandbox.probe", return_value={"available":False,"reason":"Unavailable"}):
                with self.assertRaises(SandboxUnavailable):
                    grade_oracle(checker, "case", root, ["main"], 1)
                with self.assertRaises(ValueError):
                    grade_oracle(checker, "case", root, [], 1)

    def test_effective_limit_arguments(self):
        command = container_command("docker", "image@sha256:" + "a"*64, "test", Path("/workspace"))
        for flag in ("--read-only", "--network=none", "--memory=128m", "--cpus=0.5",
                     "--pids-limit=32", "--cap-drop=ALL", "--user=65534:65534", "--pull=never"):
            self.assertIn(flag, command)
        self.assertIn("/tmp:rw,noexec,nosuid,size=8m,mode=1777", command)
        self.assertIn("type=bind,src=" + str(Path("/workspace")) + ",dst=/workspace,readonly", command)

    def test_unsafe_oracle_paths_blocked(self):
        payload = oracle()
        payload["cases"]["case"]["checks"]["main"][0]["file"] = "../secret.py"
        with self.assertRaises(ValueError):
            validate_oracle(payload)

    def test_target_cannot_forge_completion_or_monkeypatch_checker(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "target.py"
            for source in ("import os; os._exit(0)", "raise SystemExit(0)",
                           "print('{\"kind\":\"value\",\"value\":1}')",
                           "def answer():\n return globals()\n",
                           "def answer():\n return (1).__class__\n"):
                target.write_text(source)
                with self.assertRaises(ValueError):
                    validate_pure_target(target)
            target.write_text("def answer(value):\n    if type(value) is not int: raise TypeError()\n    return value + 1\n")
            validate_pure_target(target)

    def test_source_byte_limit_precedes_parser_or_process_start(self):
        from tools.guardian_grader_sandbox import MAX_SOURCE_BYTES
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "target.py"
            target.write_bytes(b"#" * (MAX_SOURCE_BYTES + 1))
            with patch("tools.guardian_grader_sandbox.subprocess.run") as helper:
                with self.assertRaises(ValueError):
                    validate_pure_target(target)
                helper.assert_not_called()

    def test_parser_limits_nodes_depth_and_runtime_without_executing_source(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "target.py"
            target.write_text("def answer():\n    return " + "1+" * 1000 + "1\n")
            with self.assertRaises(ValueError):
                validate_pure_target(target)
            target.write_text("def answer():\n    return 1\n")
            with patch("tools.guardian_grader_sandbox.subprocess.run", side_effect=subprocess.TimeoutExpired("parser",3)):
                with self.assertRaises(ValueError):
                    validate_pure_target(target)
            target.write_text("def answer():\n    while True: pass\n")
            validate_pure_target(target)  # Parse only; the infinite loop is never executed here.

    def test_domain_oracles_are_explicitly_unverified(self):
        root = Path(__file__).resolve().parents[1] / "eval" / "domain-fixtures"
        if not root.exists():
            self.skipTest("Optional domain corpus omitted from installed runtime")
        catalog = json.loads((root / "catalog.json").read_text())
        self.assertEqual(len(catalog["domains"]), 8)
        for domain in catalog["domains"]:
            oracle_path = root / domain["path"] / domain["oracle"]
            oracle_data = json.loads(oracle_path.read_text())
            self.assertEqual(oracle_data["status"], "NOT VERIFIED")
            self.assertTrue(oracle_data["expected_contract"])

    def test_real_backend_readonly_escape_probe(self):
        # This is a trusted, private container probe, independent of the AST
        # rejection tests. It actually attempts a forbidden write in the OS sandbox.
        backend = probe()
        if not backend["available"]:
            self.skipTest("NOT VERIFIED: requires digest-pinned image and rootless Docker")
        import uuid
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            name = "guardian-grade-probe-" + uuid.uuid4().hex
            command = container_command(backend["binary"], backend["image"], name, root)
            try:
                result = subprocess.run(command + ["-I", "-B", "-c",
                    "from pathlib import Path; Path('/workspace/escaped').touch()"],
                    capture_output=True, timeout=5)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((root / "escaped").exists())
            finally:
                subprocess.run([backend["binary"], "rm", "--force", name], capture_output=True, timeout=10)

    def test_real_backend_timeout_cleans_container(self):
        backend = probe()
        if not backend["available"]:
            self.skipTest("NOT VERIFIED: requires digest-pinned image and rootless Docker")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "target.py").write_text("def answer():\n    while True: pass\n")
            self.assertFalse(execute_vector(root, oracle()["cases"]["case"]["checks"]["main"][0], 1, backend))

    def test_cancellation_removes_server_container_even_without_client_completion(self):
        class Process:
            stdin = io.BytesIO()
            stdout = io.BytesIO()
            returncode = 0
            def wait(self, **kwargs):
                raise KeyboardInterrupt()
            def poll(self):
                return 0
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "target.py").write_text("def answer():\n    return 1\n")
            backend = {"binary":"docker","image":"reviewed@sha256:"+"a"*64}
            with patch("tools.guardian_grader_sandbox.validate_pure_target"), patch("tools.guardian_grader_sandbox.subprocess.Popen", return_value=Process()), patch(
                    "tools.guardian_grader_sandbox.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", "")) as cleanup:
                with self.assertRaises(KeyboardInterrupt):
                    execute_vector(root, oracle()["cases"]["case"]["checks"]["main"][0], 1, backend)
                self.assertIn("--force", cleanup.call_args.args[0])


def oracle():
    return {"schema_version":2,"cases":{"case":{"checks":{"main":[
        {"file":"target.py","function":"answer","args":[],"expected":{"kind":"value","value":1}}
    ]}}}}
