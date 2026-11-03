"""Artifact identity includes Git metadata; real local Git, no model/network."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import sys
from unittest.mock import patch

from tools.guardian_runtime import (artifact_snapshot, artifact_scope_delta,
                                    canonical_patch, inventory, RuntimeError)


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True,
                          check=True, timeout=20)


class ArtifactSealTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name).resolve()
        git(self.repo, 'init', '-q')
        git(self.repo, 'config', 'core.filemode', 'false')
        (self.repo/'value.txt').write_text('before\n')
        (self.repo/'AGENTS.md').write_text('policy\n')
        git(self.repo, 'add', '.')
        git(self.repo, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
            'commit', '-q', '-m', 'base')

    def test_pristine_snapshot_stable_and_no_scope_delta(self):
        before = artifact_snapshot(self.repo)
        self.assertEqual(before, artifact_snapshot(self.repo))
        self.assertEqual(artifact_scope_delta(before, artifact_snapshot(self.repo), [], read_only=True), [])

    def test_mode_only_index_change_is_visible_and_scoped(self):
        before = artifact_snapshot(self.repo); content = inventory(self.repo)
        git(self.repo, 'update-index', '--chmod=+x', 'value.txt')
        after = artifact_snapshot(self.repo)
        self.assertEqual(content, inventory(self.repo))
        self.assertNotEqual(before['git']['patch_sha256'], after['git']['patch_sha256'])
        self.assertIn(b'new mode 100755', canonical_patch(self.repo))
        with self.assertRaisesRegex(RuntimeError, 'Read-only'):
            artifact_scope_delta(before, after, [], read_only=True)
        with self.assertRaisesRegex(RuntimeError, 'outside task ownership'):
            artifact_scope_delta(before, after, ['other.txt'], read_only=False)
        self.assertEqual(artifact_scope_delta(before, after, ['value.txt'], read_only=False), ['value.txt'])

    def test_protected_mode_change_cannot_be_authorized_by_path(self):
        before = artifact_snapshot(self.repo)
        git(self.repo, 'update-index', '--chmod=+x', 'AGENTS.md')
        with self.assertRaisesRegex(RuntimeError, 'Protected'):
            artifact_scope_delta(before, artifact_snapshot(self.repo), ['AGENTS.md'], read_only=False)

    @unittest.skipIf(os.name == 'nt', 'POSIX executable filesystem mode required')
    def test_filesystem_chmod_detected_even_when_git_filemode_disabled(self):
        before = artifact_snapshot(self.repo)
        (self.repo/'value.txt').chmod(0o755)
        after = artifact_snapshot(self.repo)
        self.assertEqual(before['files'], after['files'])
        with self.assertRaisesRegex(RuntimeError, 'Read-only'):
            artifact_scope_delta(before, after, [], read_only=True)

    def test_semantic_index_blob_change_is_detected_without_byte_change(self):
        before = artifact_snapshot(self.repo)
        blob = git(self.repo, 'hash-object', '-w', '--stdin').stdout.decode().strip()
        git(self.repo, 'update-index', '--cacheinfo', '100644', blob, 'value.txt')
        after = artifact_snapshot(self.repo)
        self.assertEqual(before['files'], after['files'])
        with self.assertRaisesRegex(RuntimeError, 'Read-only'):
            artifact_scope_delta(before, after, [], read_only=True)

    def test_index_type_change_is_rejected_without_creating_host_symlink(self):
        blob = git(self.repo, 'hash-object', 'value.txt').stdout.decode().strip()
        git(self.repo, 'update-index', '--cacheinfo', '120000', blob, 'value.txt')
        with self.assertRaisesRegex(RuntimeError, 'index type'):
            artifact_snapshot(self.repo)

    def test_new_base_is_rejected_even_when_working_bytes_are_identical(self):
        before = artifact_snapshot(self.repo)
        git(self.repo, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
            'commit', '--allow-empty', '-q', '-m', 'different base')
        after = artifact_snapshot(self.repo)
        self.assertEqual(before['files'], after['files'])
        with self.assertRaisesRegex(RuntimeError, 'base revision'):
            artifact_scope_delta(before, after, ['value.txt'], read_only=False)

    def test_cosmetic_git_diff_config_does_not_change_canonical_patch(self):
        (self.repo/'value.txt').write_text('after\n')
        expected = canonical_patch(self.repo)
        git(self.repo, 'config', 'diff.noprefix', 'true')
        git(self.repo, 'config', 'diff.context', '9')
        git(self.repo, 'config', 'color.ui', 'always')
        self.assertEqual(expected, canonical_patch(self.repo))

    def test_volatile_git_metadata_does_not_change_snapshot(self):
        before = artifact_snapshot(self.repo)
        (self.repo/'.git'/'description').write_text('new description, not an artifact change\n')
        git(self.repo, 'update-index', '--refresh')
        self.assertEqual(before, artifact_snapshot(self.repo))

    def test_executor_rejects_read_only_index_chmod(self):
        from tools.guardian_executor import execute, initialize
        from tools.guardian_platform import create_plan
        plan = create_plan('Auditar backend ASP.NET Core')
        state_tmp = tempfile.TemporaryDirectory(); self.addCleanup(state_tmp.cleanup)
        home = Path(state_tmp.name).resolve()/'state'
        initialize(plan, self.repo, home, briefs={t['id']: 'Read only this bounded local fixture; do not mutate any file or Git mode.' for t in plan['tasks']})
        def fake(codex, slot, prompt, timeout, logs, mode):
            logs.parent.mkdir(parents=True, exist_ok=True)
            logs.write_text('{"type":"turn.completed"}\n')
            git(slot, 'config', 'core.filemode', 'false')
            git(slot, 'update-index', '--chmod=+x', 'value.txt')
            return 0, True, None
        with patch('tools.guardian_executor._process', side_effect=fake):
            result = execute(home, apply=True, codex_binary=sys.executable, max_tasks=1)
        self.assertEqual(result['overall'], 'blocked')

    def test_executor_rejects_mode_change_outside_write_ownership(self):
        from tools.guardian_executor import execute, initialize
        from tools.guardian_platform import create_plan
        plan = create_plan('Corrigir backend ASP.NET Core')
        for task in plan['tasks']:
            task['contract'].update(operation='write', allowed_paths=['other.txt'],
                                    checks=[[sys.executable, '-V']], idempotent=False)
        state_tmp = tempfile.TemporaryDirectory(); self.addCleanup(state_tmp.cleanup)
        home = Path(state_tmp.name).resolve()/'state'
        initialize(plan, self.repo, home, briefs={t['id']: 'Write only the explicitly assigned other.txt; preserve all other files and modes.' for t in plan['tasks']})
        def fake(codex, slot, prompt, timeout, logs, mode):
            logs.parent.mkdir(parents=True, exist_ok=True)
            logs.write_text('{"type":"turn.completed"}\n')
            git(slot, 'config', 'core.filemode', 'false')
            git(slot, 'update-index', '--chmod=+x', 'value.txt')
            return 0, True, None
        with patch('tools.guardian_executor._process', side_effect=fake):
            result = execute(home, apply=True, codex_binary=sys.executable,
                             authorize_writes=True, max_tasks=1)
        self.assertEqual(result['overall'], 'blocked')


if __name__ == '__main__':
    unittest.main()
