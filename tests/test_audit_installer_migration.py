"""Pinned historical profile migration; fake homes, trusted current APIs only.

The fixture is data, not an executable previous runtime. These tests exercise
39-profile ownership/update/rollback compatibility, not Codex native loading.
They do not require Git history, network, account access or a global install.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import unittest
from unittest.mock import patch

import install
from tools.guardian_packs import operation, PackInstallError
from tools.guardian_registry import discover

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT/'tests/fixtures/installer-migration/historical-e476-profiles.json'


def snapshot(home):
    return {p.relative_to(home).as_posix(): p.read_bytes() for p in home.rglob('*')
            if p.is_file() and 'guardian-backups' not in p.relative_to(home).parts}


class HistoricalProfileMigrationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name).resolve()
        self.home = self.folder/'account'; self.home.mkdir()
        self.codex = self.home/'.codex'; self.codex.mkdir()
        self.config = b'model = "user-model"\n[agents]\nenabled = true\nmax_concurrent_threads_per_session = 3\n'
        (self.codex/'config.toml').write_bytes(self.config)
        (self.codex/'AGENTS.md').write_bytes(b'User-owned rules remain before the managed block.\n')
        (self.codex/'agents').mkdir()
        (self.codex/'agents'/'custom_user_agent.toml').write_bytes(b'name="custom_user_agent"\n')
        self.previous = self.folder/'historical-profile-source'
        # The historical-profile source image carries current surrounding data;
        # only pinned profile/policy bytes are older. No prior Python is run.
        for name in ('global', 'core', 'packs', 'project-template'):
            shutil.copytree(ROOT/name, self.previous/name)
        document = json.loads(FIXTURE.read_text(encoding='utf8'))
        self.assertEqual(document['schema_version'], 1)
        self.assertEqual(document['source_revision'], 'e476aee7398b60e5c1a086941891262abf55ed0e')
        self.assertEqual(document['profiles'], 39)
        self.profiles = {}
        for name, entry in document['files'].items():
            relative = PurePosixPath(name)
            self.assertFalse(relative.is_absolute() or '..' in relative.parts)
            data = entry['content'].encode('utf8')
            self.assertEqual(hashlib.sha256(data).hexdigest(), entry['sha256'])
            target = self.previous/name
            target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
            if name.endswith('.toml'):
                self.profiles[Path(name).name] = data
        self.assertEqual(len(self.profiles), 39)
        self.packs = sorted(p['name'] for p in discover(self.previous)['packs'])
        self.assertEqual(len(self.packs), 10)
        with patch.object(install, 'SOURCE', self.previous):
            install.lifecycle('user', self.home, apply=True)
        for name in self.packs:
            operation(name, self.codex, self.previous, apply=True)
        for name, expected in self.profiles.items():
            self.assertEqual((self.codex/'agents'/name).read_bytes(), expected)

    def test_all_39_historical_profiles_update_and_rollback_byte_exactly(self):
        before = snapshot(self.home)
        preview = install.lifecycle('user', self.home, operation='update')
        self.assertGreater(preview['changes'], 0)
        self.assertEqual(before, snapshot(self.home))
        install.lifecycle('user', self.home, operation='update', apply=True)
        for name in self.packs:
            preview = operation(name, self.codex, ROOT, action='update')
            self.assertEqual(preview['changes'], 1)
            operation(name, self.codex, ROOT, action='update', apply=True)
        catalog = json.loads((ROOT/'core/contracts-catalog-v1.json').read_text(encoding='utf8'))
        self.assertEqual(len(catalog['records']), 39)
        for record in catalog['records']:
            with self.subTest(role=record['id']):
                target = self.codex/'agents'/Path(record['file']).name
                self.assertEqual(target.read_bytes(), (ROOT/record['file']).read_bytes())
                self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), record['sha256'])
                self.assertNotEqual(target.read_bytes(), self.profiles[target.name])
        self.assertEqual((self.codex/'config.toml').read_bytes(), self.config)
        self.assertTrue((self.codex/'AGENTS.md').read_bytes().startswith(b'User-owned rules'))
        self.assertEqual((self.codex/'agents/custom_user_agent.toml').read_bytes(), b'name="custom_user_agent"\n')
        for name in self.packs:
            operation(name, self.codex, ROOT, action='rollback', apply=True)
        install.lifecycle('user', self.home, operation='rollback', apply=True)
        # Includes exact prior ownership receipt and pack receipt bytes, all
        # managed content, policy and user config. Transaction backups excluded.
        self.assertEqual(before, snapshot(self.home))

    def test_historical_core_user_edit_blocks_update_without_overwrite(self):
        catalog = json.loads((ROOT/'core/contracts-catalog-v1.json').read_text(encoding='utf8'))
        role = next(record for record in catalog['records'] if record['id'] == 'S08')
        target = self.codex/'agents'/Path(role['file']).name
        target.write_bytes(target.read_bytes()+b'\n# user customization\n')
        before = snapshot(self.home)
        with self.assertRaisesRegex(ValueError, 'Conflicting existing file'):
            install.lifecycle('user', self.home, operation='update', apply=True)
        self.assertEqual(before, snapshot(self.home))

    def test_historical_optional_user_edit_blocks_update_without_overwrite(self):
        target = self.codex/'agents/guardian_dotnet_runtime_specialist.toml'
        target.write_bytes(target.read_bytes()+b'\n# user customization\n')
        before = snapshot(self.home)
        with self.assertRaisesRegex(PackInstallError, 'Locally modified'):
            operation('dotnet', self.codex, ROOT, action='update', apply=True)
        self.assertEqual(before, snapshot(self.home))


if __name__ == '__main__':
    unittest.main()
