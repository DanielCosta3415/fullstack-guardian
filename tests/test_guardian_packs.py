"""Non-destructive optional-pack installation tests on isolated temporary Codex homes."""
import json
import tempfile
import unittest
from pathlib import Path

from tools.guardian_packs import PackInstallError, operation
from tools.guardian_registry import ROOT


class PackLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.codex = Path(self.tmp.name) / ".codex"

    def test_dry_run_does_not_create_files(self):
        result = operation("dotnet", self.codex, ROOT)
        self.assertEqual(result["changes"], 1)
        self.assertFalse(self.codex.exists())

    def test_install_then_uninstall(self):
        result = operation("dotnet", self.codex, ROOT, apply=True)
        self.assertTrue(result["apply"])
        agents = list((self.codex / "agents").glob("*.toml"))
        self.assertEqual(len(agents), 1)
        receipt = json.loads((self.codex / "guardian-packs.json").read_text())
        self.assertIn("dotnet", receipt["packs"])
        operation("dotnet", self.codex, ROOT, action="uninstall", apply=True)
        self.assertFalse(agents[0].exists())

    def test_duplicate_install_requires_explicit_update(self):
        operation("dotnet", self.codex, ROOT, apply=True)
        with self.assertRaises(PackInstallError):
            operation("dotnet", self.codex, ROOT, apply=True)
        report = operation("dotnet", self.codex, ROOT, action="update")
        self.assertEqual(report["changes"], 0)

    def test_reject_modified_owned_agent(self):
        operation("dotnet", self.codex, ROOT, apply=True)
        path = next((self.codex / "agents").glob("*.toml"))
        with path.open("a") as stream:
            stream.write("\n# local user edit\n")
        with self.assertRaises(PackInstallError):
            operation("dotnet", self.codex, ROOT, action="uninstall", apply=True)
        self.assertTrue(path.exists())

    def test_reject_conflicting_unmanaged_agent(self):
        path = self.codex / "agents" / "guardian_dotnet_runtime_specialist.toml"
        path.parent.mkdir(parents=True)
        path.write_text('name="user_owned"')
        with self.assertRaises(PackInstallError):
            operation("dotnet", self.codex, ROOT, apply=True)
        self.assertEqual(path.read_text(), 'name="user_owned"')

    def test_reject_malicious_receipt(self):
        self.codex.mkdir()
        (self.codex / "guardian-packs.json").write_text(json.dumps(
            {"schema_version": 1, "packs": {"dotnet": {"files": {"../../escape.toml": "0"*64}}}}))
        with self.assertRaises(PackInstallError):
            operation("dotnet", self.codex, ROOT, action="uninstall")

    def test_destination_symlink_rejected(self):
        self.codex.mkdir()
        somewhere = Path(self.tmp.name) / "outside"
        somewhere.mkdir()
        try:
            (self.codex / "agents").symlink_to(somewhere, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable in this environment")
        with self.assertRaises(PackInstallError):
            operation("dotnet", self.codex, ROOT, apply=True)


if __name__ == "__main__":
    unittest.main()
