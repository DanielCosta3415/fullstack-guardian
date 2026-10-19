"""Attack and injected-failure regression tests; isolated temporary roots only."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.guardian_maintenance import maintenance_lock, maintenance_locks
from tools import guardian_packs as packs, guardian_recover as recovery, guardian_trace as trace
from tools.guardian_registry import ROOT, RegistryError, discover
from test_install import inst


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.home = self.base / '.codex'

    def fixture(self, target, *, mode='user', before=b'original', after=b'changed'):
        backup_id = 'b' * 32
        backup = self.home / 'guardian-backups' / backup_id
        backup.mkdir(parents=True, exist_ok=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(after)
        (backup / '0.bin').write_bytes(before)
        manifest = {'changes': [{'path': str(target), 'before': '0.bin',
                               'after': hashlib.sha256(after).hexdigest()}]}
        (backup / 'transaction.json').write_text(json.dumps(manifest))
        return backup_id, backup

    def test_recovery_rejects_credentials_sessions_and_unowned_agents(self):
        for suffix in ('auth.json', 'sessions/private.json', 'agents/foreign.toml', 'guardian-packs.json'):
            with self.subTest(suffix=suffix):
                target = self.home / suffix
                backup_id, _ = self.fixture(target)
                with self.assertRaises(recovery.RecoveryError):
                    recovery.restore(self.home, backup_id, 'user', apply=True)
                self.assertEqual(target.read_bytes(), b'changed')

    def test_project_runtime_and_policy_recover(self):
        for target in (self.base / '.guardian/tools/guardian.py', self.base / 'AGENTS.md'):
            with self.subTest(target=target):
                backup_id, _ = self.fixture(target)
                recovery.restore(self.home, backup_id, 'project', apply=True)
                self.assertEqual(target.read_bytes(), b'original')

    def test_recovery_blocks_identity_forgery(self):
        target = self.home / 'config.toml'
        backup_id, backup = self.fixture(target)
        manifest = json.loads((backup / 'transaction.json').read_text())
        manifest.update(mode='user', identity={'codex': str(self.base / 'foreign')})
        (backup / 'transaction.json').write_text(json.dumps(manifest))
        with self.assertRaises(recovery.RecoveryError):
            recovery.restore(self.home, backup_id, 'user')

    def test_shared_lock_blocks_all_three_maintenance_apis(self):
        backup_id, _ = self.fixture(self.home / 'config.toml')
        with maintenance_lock(self.home, 'test'):
            for call in (lambda: inst.lifecycle('user', self.base, apply=True),
                         lambda: packs.operation('dotnet', self.home, apply=True),
                         lambda: recovery.restore(self.home, backup_id, 'user', apply=True)):
                with self.assertRaises(ValueError):
                    call()
        self.assertFalse((self.home / '.guardian-maintenance.lock').exists())

    def test_lock_blocks_separate_process(self):
        with maintenance_lock(self.home, 'test'):
            result = subprocess.run([sys.executable, '-B', '-c',
                'from pathlib import Path; from tools.guardian_maintenance import maintenance_lock; '
                'ctx=maintenance_lock(Path(__import__("sys").argv[1])); ctx.__enter__()', str(self.home)],
                cwd=ROOT, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
        with maintenance_lock(self.home):
            pass

    def test_different_codex_homes_cannot_mutate_shared_user_skills(self):
        first, second = self.base / 'codex-one', self.base / 'codex-two'
        shared = self.base / '.agents/skills'
        with patch.object(Path, 'home', return_value=self.base):
            with patch.dict(os.environ, {'CODEX_HOME': str(first)}):
                c, skills, runtime, instruction, _ = inst.locations('user', None)
            self.assertEqual(skills, shared)
            with maintenance_locks((c, skills, runtime, instruction.parent), 'first-install'):
                with patch.dict(os.environ, {'CODEX_HOME': str(second)}):
                    with self.assertRaises(ValueError):
                        inst.lifecycle('user', None, apply=True)
                self.assertFalse((second / 'guardian-install.json').exists())
                with self.assertRaises(recovery.RecoveryError):
                    recovery.restore(second, 'b' * 32, 'user', skills_root=shared, apply=True)
        # Failed partial acquisition cleans its locks; unrelated scopes are not stuck.
        with maintenance_locks((second, shared, second / 'guardian-system')):
            pass
        self.assertFalse((shared / '.guardian-maintenance.lock').exists())

    def test_shared_skills_lock_blocks_other_process_home(self):
        first, second = self.base / 'first', self.base / 'second'
        shared = self.base / 'shared-skills'
        with maintenance_locks((first, shared)):
            result = subprocess.run([sys.executable, '-B', '-c',
                'from pathlib import Path; from tools.guardian_maintenance import maintenance_locks; '
                'import sys; ctx=maintenance_locks([Path(sys.argv[1]), Path(sys.argv[2])]); ctx.__enter__()',
                str(second), str(shared)], cwd=ROOT, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
        with maintenance_locks((second, shared)):
            pass

    def test_failed_operation_releases_lock(self):
        with self.assertRaises(RuntimeError):
            with maintenance_lock(self.home):
                raise RuntimeError('injected failure')
        with maintenance_lock(self.home):
            pass

    def test_legacy_lock_is_not_bypassed(self):
        self.home.mkdir()
        (self.home / '.guardian-packs.lock').write_bytes(b'interrupted')
        with self.assertRaises(ValueError):
            with maintenance_lock(self.home):
                pass

    def test_forged_pack_receipt_cannot_delete_core_agent(self):
        target = self.home / 'agents/engineering_orchestrator.toml'
        target.parent.mkdir(parents=True)
        target.write_bytes(b'core synthetic')
        (self.home / 'guardian-packs.json').write_text(json.dumps({'schema_version': 1,
            'packs': {'dotnet': {'files': {target.name: hashlib.sha256(target.read_bytes()).hexdigest()}}}}))
        with self.assertRaises(packs.PackInstallError):
            packs.operation('dotnet', self.home, action='uninstall', apply=True)
        self.assertEqual(target.read_bytes(), b'core synthetic')

    def test_failed_pack_receipt_write_restores_agent_and_receipt(self):
        original_write = packs._write_atomic
        def fail_receipt(path, data):
            if path.name == 'guardian-packs.json':
                raise OSError('injected receipt failure')
            original_write(path, data)
        with patch.object(packs, '_write_atomic', side_effect=fail_receipt):
            with self.assertRaises(OSError):
                packs.operation('dotnet', self.home, apply=True)
        self.assertFalse((self.home / 'guardian-packs.json').exists())
        self.assertEqual(list((self.home / 'agents').glob('*.toml')), [])

    def test_aggregate_and_unicode_payload_rejected_without_mutation(self):
        path = self.base / 'events.jsonl'
        trace.init(path)
        original = path.read_bytes()
        for value in ('x' * 1900, '\u6f22' * 1000):
            with self.assertRaises(trace.TraceError):
                trace.append(path, 'verification', {str(i): value for i in range(20)})
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(trace.verify(path)['events'], 1)

    def test_nan_rejected_without_mutation(self):
        path = self.base / 'events.jsonl'
        trace.init(path)
        original = path.read_bytes()
        with self.assertRaises(ValueError):
            trace.append(path, 'verification', {'duration': float('nan')})
        self.assertEqual(path.read_bytes(), original)

    def test_private_payload_rejected_and_public_summary_omits_contents(self):
        path = self.base / 'events.jsonl'
        trace.init(path)
        for content in ('person@example.test', 'C:' + '/Users/' + 'synthetic/project', '/home/synthetic/project'):
            with self.assertRaises(trace.TraceError):
                trace.append(path, 'verification', {'comment': content})
        summary = trace.public_summary(path)
        self.assertFalse(summary['raw_events_included'])
        self.assertFalse(summary['host_acl_verified'])
        self.assertEqual(summary['events'], 1)

    def test_exit_zero_is_never_correctness_proof(self):
        path = self.base / 'events.jsonl'
        trace.init(path)
        trace.record_process_result(path, check_id='test-check', tool='python', tool_version='3.11', exit_code=0)
        data = json.loads(path.read_text().splitlines()[-1])['data']
        self.assertEqual(data['execution_status'], 'EXIT_ZERO')
        self.assertEqual(data['correctness_status'], 'NOT_VERIFIED')
        self.assertFalse(data['authenticated'])

    def test_failed_journal_replace_preserves_valid_boundary(self):
        path = self.base / 'events.jsonl'
        trace.init(path)
        original = path.read_bytes()
        with patch('tools.guardian_maintenance.os.replace', side_effect=OSError('injected')):
            with self.assertRaises(OSError):
                trace.append(path, 'finish', {'result': 'not verified'})
        self.assertEqual(path.read_bytes(), original)
        self.assertTrue(trace.verify(path)['ok'])

    def test_registry_distinguishes_catalog_install_and_native_load(self):
        before = discover(ROOT, codex_home=self.home)
        optional = next(p for p in before['packs'] if p['name'] == 'dotnet')['agents'][0]
        self.assertFalse(optional['eligible'])
        packs.operation('dotnet', self.home, apply=True)
        after = discover(ROOT, codex_home=self.home)
        optional = next(p for p in after['packs'] if p['name'] == 'dotnet')['agents'][0]
        self.assertTrue(optional['eligible'])
        self.assertEqual(optional['state'], 'installed_not_loaded')
        self.assertIsNone(optional['loaded'])
        self.assertFalse(optional['native_verified'])
        self.assertEqual(len(optional['sha256']), 64)


if __name__ == '__main__':
    unittest.main()
