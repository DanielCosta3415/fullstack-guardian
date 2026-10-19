import json
from pathlib import Path
import tempfile
import tomllib
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from tools import guardian_client_probe as probe


class ClientProbeTests(unittest.TestCase):
    def test_profile_has_documented_toml_with_strict_synthetic_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            outside, runtime = Path(temp) / 'outside', Path(temp) / 'python'
            setting = tomllib.loads(probe.profile_override(outside, runtime))['permissions'][probe.PROFILE_NAME]
        self.assertEqual(setting['extends'], ':workspace')
        self.assertEqual(setting['filesystem'][':root'], 'deny')
        self.assertEqual(setting['filesystem'][':minimal'], 'read')
        self.assertEqual(setting['filesystem'][':workspace_roots'], {'.': 'write'})
        self.assertEqual(setting['filesystem'][str(outside.resolve())], 'deny')
        self.assertEqual(setting['network'], {'enabled': False})

    def test_no_opaque_state_or_bypass_and_managed_config_active(self):
        command = probe.sandbox_command('codex', Path('workspace'), Path('outside'), 1234)
        self.assertIn('--include-managed-config', command)
        self.assertEqual(command[command.index('-P') + 1], probe.PROFILE_NAME)
        self.assertNotIn('--sandbox-state-json', command)
        self.assertFalse(any('bypass' in value or 'danger-full-access' in value for value in command))
        self.assertNotIn('exec', command)

    def test_runtime_overlap_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                probe.profile_override(Path(temp) / 'nested', temp)

    def test_observations_are_closed_typed_schema(self):
        valid = {key: 'denied' for key in probe.OBSERVATIONS}
        self.assertEqual(probe.parse_observations(json.dumps(valid)), valid)
        for invalid in (dict(valid, admin=True), {}, [], dict(valid, workspace_write=True)):
            self.assertIsNone(probe.parse_observations(json.dumps(invalid)))

    def test_public_diagnostic_never_echoes_private_stderr(self):
        for stderr in ('CreateDesktopW failed path PRIVATE', 'permission profile PRIVATE invalid', 'PRIVATE secret=sample'):
            self.assertNotIn('PRIVATE', probe.diagnostic(stderr))

    def test_existing_directory_preserved(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(probe.platform, 'system', return_value='Windows'):
            path = Path(temp) / 'sentinel'
            path.write_text('preserved')
            with self.assertRaises(ValueError):
                probe.run(temp)
            self.assertEqual(path.read_text(), 'preserved')

    def test_non_windows_is_explicitly_unsupported(self):
        with patch.object(probe.platform, 'system', return_value='Linux'):
            with self.assertRaisesRegex(ValueError, 'Windows'):
                probe.run('unused')

    def test_native_backend_rejection_is_unsupported_and_logs_stay_private(self):
        class Listener:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def bind(self, *args): pass
            def listen(self, *args): pass
            def settimeout(self, *args): pass
            def getsockname(self): return ('127.0.0.1', 1234)
            def accept(self): raise probe.socket.timeout()
        completed = SimpleNamespace(stdout='', stderr='Restricted read-only access requires the elevated Windows sandbox backend PRIVATE', returncode=1)
        with tempfile.TemporaryDirectory() as temp, patch.object(probe.platform, 'system', return_value='Windows'), patch.object(probe, 'probe_version', return_value='test'), patch.object(probe.socket, 'socket', return_value=Listener()), patch.object(probe.subprocess, 'run', return_value=completed):
            out = Path(temp).resolve() / 'probe'
            report = probe.run(out, 'codex')
            self.assertEqual(report['probe_status'], 'UNSUPPORTED')
            self.assertFalse(report['probe_completed'])
            self.assertEqual(report['capabilities']['filesystem_isolation']['status'], 'unsupported')
            self.assertEqual(report['capabilities']['network_isolation']['status'], 'unknown')
            self.assertNotIn('PRIVATE', json.dumps(report))
            self.assertIn('PRIVATE', (out / 'private/stderr.txt').read_text())


if __name__ == '__main__':
    unittest.main()
