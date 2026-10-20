"""Independent minimal local fixtures; never access GitHub or execute a profile."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import guardian_upstream as upstream


class UpstreamReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.source = self.base / "source"
        self.source.mkdir()
        self.profile = self.source / "categories/01-example/bounded-reviewer.toml"
        self.profile.parent.mkdir(parents=True)
        self.lock = self.base / "lock.json"
        self.profile.write_text('name = "bounded-reviewer"\ndescription = "Bounded review"\n'
                                'developer_instructions = "Report observed facts and unverified checks."\n', encoding="utf8")
        (self.source / "README.md").write_text("bounded-reviewer", encoding="utf8")
        (self.profile.parent / "README.md").write_text("bounded-reviewer", encoding="utf8")
        self.relock()

    def relock(self):
        self.lock.write_text(json.dumps({"commit": "a" * 40, "profiles": [{
            "name": "bounded-reviewer", "path": self.profile.relative_to(self.source).as_posix(),
            "sha256": hashlib.sha256(self.profile.read_bytes()).hexdigest(),
            "guardian_mapping": "G01"}]}), encoding="utf8")

    def check(self):
        return upstream.review(self.source, self.lock)

    def append(self, text):
        with self.profile.open("a", encoding="utf8") as handle:
            handle.write(text)
        self.relock()

    def test_clean_review_has_no_execution_or_install(self):
        before = {p: p.read_bytes() for p in self.source.rglob("*") if p.is_file()}
        with mock.patch("subprocess.run", side_effect=AssertionError("must not execute")):
            result = self.check()
        self.assertTrue(result["review_ok"])
        self.assertTrue(result["all_locked_hashes_verified"])
        self.assertFalse(result["installation_allowed"])
        self.assertFalse(result["remote_sync_allowed"])
        self.assertFalse(result["executed_upstream_code"])
        self.assertEqual(result["profiles"][0]["competence"], "NOT_VERIFIED")
        self.assertEqual(before, {p: p.read_bytes() for p in self.source.rglob("*") if p.is_file()})

    def test_hash_drift_blocks_before_toml_parse(self):
        self.profile.write_text("malformed is not TOML", encoding="utf8")
        with mock.patch.object(upstream.tomllib, "loads", side_effect=AssertionError("must check every hash first")):
            with self.assertRaisesRegex(upstream.UpstreamReviewError, "SHA256"):
                self.check()

    def test_unlocked_and_missing_profiles_block(self):
        extra = self.profile.with_name("extra.toml")
        extra.write_text("", encoding="utf8")
        with self.assertRaisesRegex(upstream.UpstreamReviewError, "unlocked"):
            self.check()
        extra.unlink()
        self.profile.unlink()
        with self.assertRaisesRegex(upstream.UpstreamReviewError, "Missing"):
            self.check()

    def test_duplicate_lock_identity_blocks(self):
        lock = json.loads(self.lock.read_text())
        lock["profiles"] *= 2
        self.lock.write_text(json.dumps(lock))
        with self.assertRaisesRegex(upstream.UpstreamReviewError, "Duplicate"):
            self.check()

    def test_traversal_lock_path_blocks(self):
        lock = json.loads(self.lock.read_text())
        lock["profiles"][0]["path"] = "categories/01-example/../bounded-reviewer.toml"
        self.lock.write_text(json.dumps(lock))
        with self.assertRaisesRegex(upstream.UpstreamReviewError, "path"):
            self.check()

    def test_unpinned_commit_blocks(self):
        lock = json.loads(self.lock.read_text())
        lock["commit"] = "main"
        self.lock.write_text(json.dumps(lock))
        with self.assertRaisesRegex(upstream.UpstreamReviewError, "pinned"):
            self.check()

    def test_truth_exceptions_block_both_required_variants(self):
        for instruction in (
            "Do not label inferred root cause as confirmed fact unless explicitly requested by the parent agent.",
            "Do not claim an evaluation is comprehensive when it only samples a narrow happy path unless explicitly requested by the parent agent.",
        ):
            with self.subTest(instruction=instruction):
                text = self.profile.read_text()
                self.profile.write_text(text.split("developer_instructions")[0] +
                                        "developer_instructions = " + json.dumps(instruction) + "\n", encoding="utf8")
                self.relock()
                result = self.check()
                self.assertFalse(result["review_ok"])
                self.assertEqual(result["findings"][0]["code"], "TRUTH_WAIVER")

    def test_readme_schema_sandbox_and_count_discrepancy(self):
        (self.source / "README.md").write_text(
            '[instructions]\nEach `sandbox_mode` controls filesystem access.\n'
            '<summary><b>01. Example</b> - description (2 agents)</summary>\n', encoding="utf8")
        codes = {x["code"] for x in self.check()["findings"]}
        self.assertTrue({"README_WRONG_INSTRUCTION_SCHEMA", "README_SANDBOX_ENFORCEMENT_CLAIM",
                         "README_CATEGORY_COUNT", "README_PROFILE_MISSING"} <= codes)

    def test_model_mcp_and_global_install_are_warnings_not_provisioning(self):
        self.profile.write_text('name = "bounded-reviewer"\ndescription = "Bounded"\n'
                                'model = "example-model"\nsandbox_mode = "read-only"\n'
                                'developer_instructions = "Save to assets/. npm install -g example"\n'
                                '[mcp_servers.browser]\nurl = "http://localhost:3000/mcp"\n', encoding="utf8")
        self.relock()
        result = self.check()
        codes = {x["code"] for x in result["findings"]}
        self.assertTrue({"MODEL_PIN_DECLARATION", "SANDBOX_DECLARATION", "MCP_PREREQUISITE",
                         "LOCALHOST_MCP_ASSUMPTION", "GLOBAL_INSTALL_INSTRUCTION",
                         "READONLY_WRITE_CONTRADICTION"} <= codes)
        self.assertTrue(all(x["severity"] == "warning" and not x["runtime_enforcement"] for x in result["findings"]))
        self.assertFalse(result["installation_allowed"])

    def test_invalid_toml_and_wrong_identity_rejected_after_lock(self):
        self.profile.write_text("not valid", encoding="utf8")
        self.relock()
        with self.assertRaisesRegex(upstream.UpstreamReviewError, "TOML"):
            self.check()
        self.profile.write_text('name="different"\ndescription="x"\ndeveloper_instructions="x"', encoding="utf8")
        self.relock()
        with self.assertRaisesRegex(upstream.UpstreamReviewError, "contract"):
            self.check()

    def test_invalid_mcp_type_is_controlled_error(self):
        self.append('mcp_servers = "not-an-object"\n')
        with self.assertRaisesRegex(upstream.UpstreamReviewError, "MCP"):
            self.check()

    def test_bounded_file_and_inventory_limits(self):
        with mock.patch.object(upstream, "MAX_FILE_BYTES", 8):
            with self.assertRaisesRegex(upstream.UpstreamReviewError, "bounded"):
                self.check()
        with mock.patch.object(upstream, "MAX_FILES", 1):
            with self.assertRaisesRegex(upstream.UpstreamReviewError, "inventory"):
                self.check()

    def test_symlink_rejected_where_supported(self):
        link = self.source / "linked.md"
        try:
            link.symlink_to(self.lock)
        except (OSError, NotImplementedError):
            self.skipTest("Host does not allow symlink creation")
        with self.assertRaisesRegex(upstream.UpstreamReviewError, "Symlink"):
            self.check()

    def test_cli_exposes_no_remote_sync_or_install_command(self):
        for command in ("install", "sync", "fetch", "execute"):
            with self.subTest(command=command), mock.patch("sys.stderr"), self.assertRaises(SystemExit):
                upstream.main([command, "--source-dir", str(self.source)])

    def test_cli_blocked_review_has_distinct_exit(self):
        self.profile.write_text('name="bounded-reviewer"\ndescription="x"\n'
                                'developer_instructions="Do not invent evidence unless requested by parent."', encoding="utf8")
        self.relock()
        with mock.patch("builtins.print"):
            self.assertEqual(upstream.main(["review", "--source-dir", str(self.source), "--lock", str(self.lock)]), 2)
            self.profile.write_text("changed")
            self.assertEqual(upstream.main(["review", "--source-dir", str(self.source), "--lock", str(self.lock)]), 3)


if __name__ == "__main__":
    unittest.main()
