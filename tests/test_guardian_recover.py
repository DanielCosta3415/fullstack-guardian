"""Interrupted-installer recovery tests; all changes stay under a temp directory."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.guardian_recover import RecoveryError, inspect, restore


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve() / ".codex"
        self.home.mkdir()
        self.backup_id = "a" * 32
        self.backup = self.home / "guardian-backups" / self.backup_id
        self.backup.mkdir(parents=True)
        self.target = self.home / "agents" / "engineering_orchestrator.toml"
        self.target.parent.mkdir()
        self.before = b"preexisting-agent\n"
        self.after = b"guardian-installed-agent\n"
        (self.backup / "0.bin").write_bytes(self.before)
        self.target.write_bytes(self.after)
        self.write_manifest(self.target, before="0.bin", after=self.after)

    def write_manifest(self, target, before, after):
        payload = {"changes": [{"path": str(target), "before": before,
                               "after": hashlib.sha256(after).hexdigest() if after is not None else None}]}
        (self.backup / "transaction.json").write_text(json.dumps(payload))

    def test_dry_run_only(self):
        result = restore(self.home, self.backup_id, "user")
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["files_to_restore"], 1)
        self.assertEqual(self.target.read_bytes(), self.after)

    def test_restore_interrupted_operation(self):
        result = restore(self.home, self.backup_id, "user", apply=True)
        self.assertTrue(result["restored_to_pre_transaction"])
        self.assertEqual(self.target.read_bytes(), self.before)
        self.assertEqual(inspect(self.home, self.backup_id, "user")["restore_count"], 0)

    def test_user_modified_file_is_preserved(self):
        self.target.write_bytes(b"edited-by-user\n")
        with self.assertRaises(RecoveryError):
            restore(self.home, self.backup_id, "user", apply=True)
        self.assertEqual(self.target.read_bytes(), b"edited-by-user\n")

    def test_receipt_change_blocks(self):
        (self.home / "guardian-install.json").write_text('{"different":"receipt"}')
        with self.assertRaises(RecoveryError):
            restore(self.home, self.backup_id, "user")

    def test_outside_scope_blocks(self):
        outside = self.home.parent / "outside.txt"
        outside.write_bytes(self.after)
        self.write_manifest(outside, before="0.bin", after=self.after)
        with self.assertRaises(RecoveryError):
            restore(self.home, self.backup_id, "user", apply=True)

    def test_missing_original_fails(self):
        (self.backup / "0.bin").unlink()
        with self.assertRaises(RecoveryError):
            restore(self.home, self.backup_id, "user", apply=True)

    def test_invalid_backup_id_fails(self):
        with self.assertRaises(RecoveryError):
            restore(self.home, "../../secrets", "user")

    def test_newly_created_file_is_removed(self):
        (self.backup / "0.bin").unlink()
        self.write_manifest(self.target, before=None, after=self.after)
        restore(self.home, self.backup_id, "user", apply=True)
        self.assertFalse(self.target.exists())


if __name__ == "__main__":
    unittest.main()
