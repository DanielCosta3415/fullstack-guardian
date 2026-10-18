"""Registry tests: isolated fixtures, no Codex quota, network or global state."""
import json
import tempfile
import unittest
from pathlib import Path
from tools.guardian_registry import RegistryError, discover

class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "core").mkdir()
        (self.root / "global" / "agents").mkdir(parents=True)
        (self.root / "global" / "agents" / "base.toml").write_text(
            'name="guardian_test_core"\\ndescription="test"\\ndeveloper_instructions="test"\\n'.replace('\\n','\n'),
            encoding="utf-8"
        )
        (self.root / "core" / "agents.json").write_text(json.dumps({"agents":[
            {"id":"S01","name":"guardian_test_core","group":"test","file":"global/agents/base.toml"}
        ]}), encoding="utf-8")

    def test_core_only(self):
        result=discover(self.root)
        self.assertEqual(result["available_total"],1)
        self.assertEqual(result["packs"],[])

    def add_pack(self, name="extra", agent="guardian_test_extra"):
        folder=self.root/"packs"/name
        (folder/"agents").mkdir(parents=True)
        (folder/"manifest.json").write_text(json.dumps({
            "schema_version":1,"name":name,
            "agents":[{"name":agent,"file":f"agents/{agent}.toml"}]
        }),encoding="utf-8")
        (folder/"agents"/f"{agent}.toml").write_text(
            f'name = "{agent}"\ndescription = "test"\ndeveloper_instructions = "test"\n',
            encoding="utf-8")
        return folder

    def test_valid_optional_pack(self):
        self.add_pack()
        result=discover(self.root)
        self.assertEqual(result["available_total"],2)
        self.assertTrue(result["packs"][0]["optional"])
        self.assertFalse(result["installed"])

    def test_duplicate_name_rejected(self):
        self.add_pack(agent="guardian_test_core")
        with self.assertRaises(RegistryError):
            discover(self.root)

    def test_invalid_manifest_rejected(self):
        folder=self.add_pack()
        (folder/"manifest.json").write_text('{"schema_version":999,"name":"extra","agents":[]}',encoding="utf-8")
        with self.assertRaises(RegistryError):
            discover(self.root)

    def test_model_override_rejected(self):
        folder=self.add_pack()
        with (folder/"agents"/"guardian_test_extra.toml").open("a",encoding="utf-8") as f:
            f.write('model="other-model"\n')
        with self.assertRaises(RegistryError):
            discover(self.root)

    def test_symlink_pack_rejected(self):
        outside=self.root/"outside"
        outside.mkdir()
        (self.root/"packs").mkdir()
        try:
            (self.root/"packs"/"extra").symlink_to(outside,target_is_directory=True)
        except (OSError,NotImplementedError):
            self.skipTest("Symlinks unavailable on this host")
        with self.assertRaises(RegistryError):
            discover(self.root)

if __name__=="__main__":
    unittest.main()
