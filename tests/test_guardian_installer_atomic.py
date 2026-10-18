"""Cross-platform installer safety checks without modifying user Codex configuration."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from install import atomic_write, safe


ROOT = Path(__file__).resolve().parents[1]


class InstallerAtomicTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve() / "account"
        self.home.mkdir()
        self.codex = self.home / ".codex"

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "install.py"), "--user",
                               "--home", str(self.home), *args],
                              stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, timeout=50)

    def test_atomic_replace(self):
        p = self.home / "file.toml"
        p.write_bytes(b"old\n")
        atomic_write(p, b"replacement\n")
        self.assertEqual(p.read_bytes(), b"replacement\n")
        self.assertEqual(list(self.home.glob(".guardian-write-*")), [])

    def test_exclusive_install_lock(self):
        self.codex.mkdir()
        (self.codex / ".guardian-install.lock").write_text("held")
        result = self.cli("--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.codex / "guardian-install.json").exists())

    def test_install_doctor_uninstall_smoke(self):
        preview = self.cli()
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertFalse((self.codex / "guardian-install.json").exists())
        installed = self.cli("--apply")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        self.assertFalse((self.codex / ".guardian-install.lock").exists())
        self.assertTrue((self.codex / "guardian-install.json").exists())
        doctor = self.cli("--doctor")
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        removed = self.cli("--uninstall", "--apply")
        self.assertEqual(removed.returncode, 0, removed.stderr)
        self.assertFalse((self.codex / "guardian-install.json").exists())


if __name__ == "__main__":
    unittest.main()
