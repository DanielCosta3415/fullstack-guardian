import subprocess
import tempfile
import unittest
import importlib.util
from pathlib import Path
from unittest.mock import patch

from tools import guardian_fingerprint as f


class FingerprintTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        # Canonicalize macOS /var -> /private/var in the trusted fixture creator;
        # production link rejection remains unchanged.
        self.root = Path(self.temp.name).resolve()
        for name, content in {
            'VERSION': '2.2.1\n', 'core/contracts-catalog-v1.json': '{}',
            'core/professional-contracts-v1.json': '{}',
            'global/agents/guardian_test.toml': 'name="guardian_test"\n',
            'tools/example.py': '# synthetic\n',
        }.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf8')

    def test_deterministic_identity_is_not_native_acceptance(self):
        first = f.fingerprint(self.root)
        self.assertEqual(first, f.fingerprint(self.root))
        self.assertEqual(first['version'], '2.2.1')
        self.assertEqual(first['profile_count'], 1)
        self.assertEqual(first['native_loading'], 'NOT_VERIFIED')
        self.assertFalse(first['authenticated'])

    def test_same_version_different_bytes_and_profile_presentation_expire_evidence(self):
        before = f.fingerprint(self.root)
        evidence = {'runtime_binding': {key: before[key] for key in f.BINDINGS}}
        (self.root / 'global/agents/guardian_test.toml').write_text('name="guardian_test"\ndescription="New display"\n', encoding='utf8')
        after = f.fingerprint(self.root)
        self.assertEqual(before['version'], after['version'])
        self.assertNotEqual(before['runtime_sha256'], after['runtime_sha256'])
        binding = f.assess_evidence_binding(evidence, after)
        self.assertEqual(binding['status'], 'STALE')
        self.assertIn('profiles_sha256', binding['mismatches'])
        self.assertFalse(binding['native_verified'])

    def test_contract_change_expires_binding(self):
        before = f.fingerprint(self.root)
        evidence = {'runtime_binding': {key: before[key] for key in f.BINDINGS}}
        (self.root / 'core/professional-contracts-v1.json').write_text('{"changed":true}', encoding='utf8')
        self.assertIn('contracts_sha256', f.assess_evidence_binding(evidence, f.fingerprint(self.root))['mismatches'])

    def test_old_native39_report_cannot_be_reclassified(self):
        old = {'revision': 'a' * 40, 'expected': 39, 'verified': 39,
               'all_native_roles_verified': True}
        self.assertEqual(f.assess_evidence_binding(old, f.fingerprint(self.root))['status'], 'NOT_VERIFIED')

    def test_matching_binding_remains_not_authenticated(self):
        observed = f.fingerprint(self.root)
        evidence = {'runtime_binding': {key: observed[key] for key in f.BINDINGS}}
        result = f.assess_evidence_binding(evidence, observed)
        self.assertEqual(result['status'], 'MATCHED_NOT_AUTHENTICATED')
        self.assertFalse(result['native_verified'])
        evidence['runtime_binding']['runtime_sha256'] = True
        with self.assertRaises(ValueError):
            f.assess_evidence_binding(evidence, observed)

    def test_installed_runtime_never_inherits_ancestor_repository_identity(self):
        with patch.object(f.subprocess, 'run', side_effect=AssertionError('Git must not run')):
            observed = f.fingerprint(self.root)
        self.assertIsNone(observed['revision'])
        self.assertEqual(observed['git_status'], 'NOT_OBSERVED')

    def test_git_root_revision_and_dirty_state_are_reported_separately_from_digest(self):
        (self.root / '.git').write_text('gitdir: synthetic', encoding='utf8')
        with patch.object(f.subprocess, 'run', side_effect=[
            subprocess.CompletedProcess([], 0, 'a' * 40 + '\n', ''),
            subprocess.CompletedProcess([], 0, b' M tools/example.py\n', b'')]):
            observed = f.fingerprint(self.root)
        self.assertEqual(observed['revision'], 'a' * 40)
        self.assertTrue(observed['tracked_changes'])

    def test_workspace_evidence_and_credentials_are_not_fingerprinted(self):
        before = f.fingerprint(self.root)
        for name in ('work/evidence.json', '.guardian-state/current.json',
                     '.codex/auth.json', '.env'):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('synthetic secret must not be read', encoding='utf8')
        self.assertEqual(before, f.fingerprint(self.root))

    def test_missing_identity_and_sensitive_file_in_managed_scope_fail_closed(self):
        path = self.root / 'tools/auth.json'
        path.write_text('synthetic', encoding='utf8')
        with self.assertRaisesRegex(ValueError, 'sensitive'):
            f.fingerprint(self.root)
        path.unlink()
        (self.root / 'core/professional-contracts-v1.json').unlink()
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            f.fingerprint(self.root)

    def test_symlink_is_rejected_before_read(self):
        target = self.root / 'tools/link.py'
        try:
            target.symlink_to(self.root / 'tools/example.py')
        except OSError:
            self.skipTest('Symlink creation unavailable in this environment')
        with self.assertRaises(ValueError):
            f.fingerprint(self.root)

    def test_oversize_packaged_content_is_rejected(self):
        with patch.object(f, 'MAX_FILE_BYTES', 4):
            with self.assertRaisesRegex(ValueError, 'bound'):
                f.fingerprint(self.root)

    def test_installer_doctor_reports_target_identity_without_changing_configuration(self):
        spec = importlib.util.spec_from_file_location('fingerprint_installer', f.ROOT / 'install.py')
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        home = self.root / 'isolated-home'
        home.mkdir()
        installer.lifecycle('user', home, apply=True)
        config = home / '.codex/config.toml'
        before = config.read_bytes()
        result = installer.lifecycle('user', home, 'doctor')
        self.assertEqual(result['runtime_identity']['profile_count'], 39)
        self.assertIsNone(result['runtime_identity']['revision'])
        self.assertEqual(result['native_loading'], 'NOT_VERIFIED')
        self.assertFalse(result['permissions_changed'])
        self.assertEqual(before, config.read_bytes())


if __name__ == '__main__':
    unittest.main()
