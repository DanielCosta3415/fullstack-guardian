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
        self.codex = Path(self.tmp.name).resolve() / ".codex"

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

    def test_update_rollback_restores_prior_profile_and_receipt(self):
        import shutil
        operation('dotnet', self.codex, ROOT, apply=True)
        profile=self.codex/'agents/guardian_dotnet_runtime_specialist.toml'
        original=profile.read_bytes()
        prior=json.loads((self.codex/'guardian-packs.json').read_text())
        source=Path(self.tmp.name).resolve()/'source'
        shutil.copytree(ROOT/'global',source/'global');shutil.copytree(ROOT/'core',source/'core');shutil.copytree(ROOT/'packs',source/'packs')
        changed=source/'packs/dotnet/agents/guardian_dotnet_runtime_specialist.toml'
        changed.write_bytes(changed.read_bytes()+b'\n# reviewed synthetic update\n')
        operation('dotnet',self.codex,source,action='update',apply=True)
        self.assertNotEqual(profile.read_bytes(),original)
        self.assertEqual(operation('dotnet',self.codex,source,action='rollback')['changes'],1)
        operation('dotnet',self.codex,source,action='rollback',apply=True)
        self.assertEqual(profile.read_bytes(),original)
        self.assertEqual(json.loads((self.codex/'guardian-packs.json').read_text()),prior)

    def test_rollback_refuses_modified_agent_and_forged_identity(self):
        operation('dotnet',self.codex,ROOT,apply=True)
        with self.assertRaises(PackInstallError):operation('dotnet',self.codex,ROOT,action='rollback')
        operation('dotnet',self.codex,ROOT,action='update',apply=True)
        path=self.codex/'agents/guardian_dotnet_runtime_specialist.toml'
        path.write_bytes(path.read_bytes()+b'\n# user edit\n')
        with self.assertRaises(PackInstallError):operation('dotnet',self.codex,ROOT,action='rollback',apply=True)

    def test_forged_rollback_profile_cannot_add_configuration_fields(self):
        import base64,hashlib
        operation('dotnet',self.codex,ROOT,apply=True)
        operation('dotnet',self.codex,ROOT,action='update',apply=True)
        receipt_path=self.codex/'guardian-packs.json';receipt=json.loads(receipt_path.read_text())
        snapshot=receipt['packs']['dotnet']['rollback'];filename=next(iter(snapshot['files']))
        data=base64.b64decode(snapshot['files'][filename])+b'\nsandbox_mode="danger-full-access"\n'
        snapshot['files'][filename]=base64.b64encode(data).decode()
        snapshot['receipt']['files'][filename]=hashlib.sha256(data).hexdigest()
        receipt_path.write_text(json.dumps(receipt))
        before=(self.codex/'agents'/filename).read_bytes()
        with self.assertRaises(PackInstallError):operation('dotnet',self.codex,ROOT,action='rollback',apply=True)
        self.assertEqual((self.codex/'agents'/filename).read_bytes(),before)

    def test_all_ten_packs_update_rollback_and_uninstall_independently(self):
        from tools.guardian_registry import discover
        names=sorted(pack['name'] for pack in discover(ROOT)['packs'])
        self.assertEqual(len(names),10)
        for name in names:operation(name,self.codex,ROOT,apply=True)
        before={path.name:path.read_bytes() for path in (self.codex/'agents').glob('*.toml')}
        for name in names:
            with self.subTest(pack=name):
                operation(name,self.codex,ROOT,action='update',apply=True)
                operation(name,self.codex,ROOT,action='rollback',apply=True)
                self.assertEqual({path.name:path.read_bytes() for path in (self.codex/'agents').glob('*.toml')},before)
        for name in names:operation(name,self.codex,ROOT,action='uninstall',apply=True)
        self.assertEqual(json.loads((self.codex/'guardian-packs.json').read_text())['packs'],{})
        self.assertEqual(list((self.codex/'agents').glob('*.toml')),[])

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
