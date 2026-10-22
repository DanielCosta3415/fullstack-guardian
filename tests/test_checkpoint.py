import copy
import json
import os
from pathlib import Path
import subprocess
import stat
import tempfile
import unittest
from unittest.mock import patch

from tools import guardian_checkpoint as c


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        self.artifact = self.root / 'evidence.txt'
        self.artifact.write_text('check: passed', encoding='utf-8')
        self.git('add', 'evidence.txt')
        self.git('commit', '-qm', 'fixture')
        self.out = self.root / '.guardian-state' / 'continuation.json'
        self.plan = {'tasks': [{'id': 'N01', 'status': 'validated'}, {'id': 'N02', 'status': 'pending'}],
                     'next_actions': ['Implement the next bounded adapter']}

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True)

    def create(self):
        return c.save(self.root, self.out, self.plan, ['evidence.txt'])

    def test_create_resume_binds_source_evidence_without_self_drift(self):
        saved = self.create()
        result = c.inspect(self.root, self.out)
        self.assertFalse(result['reinspection_required'])
        self.assertFalse(result['completion_certified'])
        self.assertEqual(result['tasks']['validated'], 1)
        self.assertEqual(saved['payload']['evidence'][0]['sha256'], c.digest(self.artifact.read_bytes()))
        self.assertNotIn('next_actions', result)

    def test_update_chain_preserves_previous_checksum(self):
        first = self.create()
        value = c.save(self.root, self.out, self.plan, signal='quota_weekly', update=True)
        self.assertEqual(value['payload']['sequence'], 2)
        self.assertEqual(value['payload']['previous_sha256'], first['sha256'])
        self.assertEqual(c.inspect(self.root, self.out)['signal'], 'quota_weekly')

    def test_owner_release_policy_requires_explicit_selection(self):
        value = self.create()
        self.assertEqual(value['payload']['constraints']['remote_testing'], 'unspecified')
        value = c.save(self.root, self.out, self.plan, update=True, release_policy='operator-autonomous')
        self.assertEqual(value['payload']['constraints']['human_approval'], 'not_required_by_owner')
        self.assertFalse(value['payload']['constraints']['permission_bypass'])
        self.assertFalse(c.inspect(self.root, self.out)['completion_certified'])
        value = c.save(self.root, self.out, self.plan, update=True, release_policy='strict')
        self.assertEqual(value['payload']['constraints']['remote_testing'], 'required')
        with self.assertRaises(ValueError):
            c.save(self.root, self.out, self.plan, update=True, release_policy='silently-bypass')

    def test_create_cannot_overwrite_and_update_cannot_create(self):
        with self.assertRaises(ValueError):
            c.save(self.root, self.out, self.plan, update=True)
        self.create()
        before = self.out.read_bytes()
        with self.assertRaises(ValueError):
            self.create()
        self.assertEqual(before, self.out.read_bytes())

    def test_omitted_update_preserves_selected_policy_and_explicit_change_is_allowed(self):
        for policy in ('strict', 'operator-autonomous'):
            with self.subTest(policy=policy):
                if self.out.exists():self.out.unlink()
                c.save(self.root, self.out, self.plan, release_policy=policy)
                value=c.save(self.root, self.out, self.plan, update=True)
                self.assertEqual(value['payload']['constraints']['release_policy'],policy)
                value=c.save(self.root, self.out, self.plan, update=True, release_policy='unspecified')
                self.assertEqual(value['payload']['constraints']['release_policy'],'unspecified')
    def test_crash_before_replace_leaves_original_and_no_temp_lock(self):
        self.create()
        before = self.out.read_bytes()
        with patch.object(c.os, 'replace', side_effect=OSError('simulated interruption')):
            with self.assertRaises(OSError):
                c.save(self.root, self.out, self.plan, update=True)
        self.assertEqual(before, self.out.read_bytes())
        self.assertEqual(list(self.out.parent.iterdir()), [self.out])

    def test_busy_lock_fails_without_deleting_other_owner_lock(self):
        self.create()
        lock = self.out.with_suffix('.lock')
        lock.write_text('another writer', encoding='utf-8')
        with self.assertRaises(FileExistsError):
            c.save(self.root, self.out, self.plan, update=True)
        self.assertTrue(lock.exists())

    def test_stale_revision_requires_reinspection_and_explicit_acceptance(self):
        self.create()
        self.artifact.write_text('new committed evidence', encoding='utf-8')
        self.git('add', '.')
        # Exclude local checkpoint data from fixture commits.
        self.git('reset', '-q', '--', '.guardian-state')
        self.git('commit', '-qm', 'next revision')
        self.assertTrue(c.inspect(self.root, self.out)['revision_changed'])
        with self.assertRaises(ValueError):
            c.save(self.root, self.out, self.plan, update=True)
        c.save(self.root, self.out, self.plan, ['evidence.txt'], update=True, accept_revision_change=True)
        self.assertFalse(c.inspect(self.root, self.out)['reinspection_required'])

    def test_dirty_drift_and_missing_evidence_are_not_completion(self):
        self.create()
        self.artifact.unlink()
        result = c.inspect(self.root, self.out)
        self.assertTrue(result['workspace_changed'])
        self.assertEqual(result['evidence_failures'], 1)
        self.assertTrue(result['reinspection_required'])
        self.assertFalse(result['completion_certified'])

    def test_changed_evidence_detected_even_with_mocked_identical_git_status(self):
        self.create()
        source = c.load_checkpoint(self.out)['payload']['source']
        self.artifact.write_text('drift', encoding='utf-8')
        with patch.object(c, 'git_snapshot', return_value=source):
            self.assertEqual(c.inspect(self.root, self.out)['evidence_failures'], 1)

    def test_dirty_tracked_content_drift_even_when_status_is_identical(self):
        self.artifact.write_text('first uncommitted edit', encoding='utf-8')
        c.save(self.root, self.out, self.plan)
        saved = c.load_checkpoint(self.out)['payload']['source']
        self.artifact.write_text('second uncommitted edit', encoding='utf-8')
        current = c.git_snapshot(self.root)
        self.assertEqual(saved['status_sha256'], current['status_sha256'])
        self.assertNotEqual(saved['content_sha256'], current['content_sha256'])
        self.assertTrue(c.inspect(self.root, self.out)['workspace_changed'])

    def test_staged_blob_drift_even_when_status_and_worktree_contents_identical(self):
        self.artifact.write_text('staged first', encoding='utf-8')
        self.git('add', 'evidence.txt')
        self.artifact.write_text('same working copy', encoding='utf-8')
        c.save(self.root, self.out, self.plan)
        saved = c.load_checkpoint(self.out)['payload']['source']
        self.artifact.write_text('staged second', encoding='utf-8')
        self.git('add', 'evidence.txt')
        self.artifact.write_text('same working copy', encoding='utf-8')
        current = c.git_snapshot(self.root)
        self.assertEqual(saved['status_sha256'], current['status_sha256'])
        self.assertEqual(saved['content_sha256'], current['content_sha256'])
        self.assertNotEqual(saved['index_sha256'], current['index_sha256'])
        self.assertTrue(c.inspect(self.root, self.out)['workspace_changed'])

    def test_subdirectory_project_rejected_instead_of_misbinding_root_paths(self):
        sub = self.root / 'sub'
        sub.mkdir()
        with self.assertRaises(ValueError):
            c.git_snapshot(sub)

    def test_untracked_nested_content_drift_even_when_status_is_identical(self):
        directory = self.root / 'untracked'
        directory.mkdir()
        path = directory / 'sample.txt'
        path.write_text('first', encoding='utf-8')
        c.save(self.root, self.out, self.plan)
        saved = c.load_checkpoint(self.out)['payload']['source']
        path.write_text('other', encoding='utf-8')
        current = c.git_snapshot(self.root)
        self.assertEqual(saved['status_sha256'], current['status_sha256'])
        self.assertNotEqual(saved['content_sha256'], current['content_sha256'])
        self.assertTrue(c.inspect(self.root, self.out)['reinspection_required'])

    def test_renamed_tracked_content_is_bound_and_source_missing_supported(self):
        self.git('mv', 'evidence.txt', 'renamed.txt')
        c.save(self.root, self.out, self.plan)
        self.assertFalse(c.inspect(self.root, self.out)['reinspection_required'])
        (self.root / 'renamed.txt').write_text('rename then edit', encoding='utf-8')
        self.assertTrue(c.inspect(self.root, self.out)['workspace_changed'])

    def test_sensitive_paths_never_read_and_always_require_inspection(self):
        path = self.root / '.env.local'
        path.write_text('SECRET_SENTINEL', encoding='utf-8')
        original = Path.open
        def safe_open(candidate, *args, **kwargs):
            if candidate == path:
                raise AssertionError('Sensitive source content must never be opened')
            return original(candidate, *args, **kwargs)
        with patch.object(Path, 'open', safe_open):
            c.save(self.root, self.out, self.plan)
            result = c.inspect(self.root, self.out)
        self.assertTrue(result['source_inspection_required'])
        self.assertTrue(result['reinspection_required'])
        self.assertNotIn('SECRET_SENTINEL', self.out.read_text(encoding='utf-8'))
        self.assertNotIn('.env.local', self.out.read_text(encoding='utf-8'))

    def test_source_content_and_path_limits_fail_closed(self):
        self.artifact.write_text('dirty bytes over tiny limit', encoding='utf-8')
        with patch.object(c, 'MAX_SOURCE_BYTES', 2), self.assertRaises(ValueError):
            c.save(self.root, self.out, self.plan)
        self.assertFalse(self.out.exists())
        with patch.object(c, 'MAX_SOURCE_PATHS', 0), self.assertRaises(ValueError):
            c.save(self.root, self.out, self.plan)

    def test_schema_checksum_and_unknown_nested_fields_rejected(self):
        self.create()
        original = c.read_json(self.out)
        for mutation in ('schema', 'checksum', 'field', 'status'):
            value = copy.deepcopy(original)
            if mutation == 'schema':
                value['payload']['schema_version'] = 1
            elif mutation == 'checksum':
                value['sha256'] = '0' * 64
            elif mutation == 'field':
                value['payload']['plan']['tasks'][0]['hidden'] = 'data'
            else:
                value['payload']['plan']['tasks'][0]['status'] = 'complete'
            if mutation != 'checksum':
                value['sha256'] = c.digest(c.encode(value['payload']))
            self.out.write_bytes(c.encode(value))
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                c.load_checkpoint(self.out)

    def test_duplicate_keys_nonfinite_oversize_json_rejected(self):
        path = self.root / 'invalid.json'
        for data in (b'{"a":1,"a":2}', b'{"a":NaN}', b' ' * (c.MAX_BYTES + 1)):
            path.write_bytes(data)
            with self.assertRaises(ValueError):
                c.read_json(path)

    def test_scoped_paths_and_sensitive_evidence_rejected(self):
        for value in ('../outside', 'C:/outside', 'a\\b', '.git/config', '.codex/auth.json', '.env', 'auth.json', 'CON.txt', 'a//b'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                c.relative(value)
        with self.assertRaises(ValueError):
            c.save(self.root, self.root / 'outside.json', self.plan)

    def test_symlink_evidence_or_state_rejected_when_supported(self):
        link = self.root / 'linked.txt'
        try:
            link.symlink_to(self.artifact)
        except OSError:
            self.skipTest('Native symlink creation unavailable for current user')
        with self.assertRaises(ValueError):
            c.save(self.root, self.out, self.plan, ['linked.txt'])
        link.unlink()
        state = self.root / '.guardian-state'
        if state.exists():
            state.rmdir()
        other = self.root / 'other'
        other.mkdir()
        state.symlink_to(other, target_is_directory=True)
        with self.assertRaises(ValueError):
            c.save(self.root, self.out, self.plan)

    def test_error_classifier_never_echoes_input_and_does_not_claim_telemetry(self):
        self.assertEqual(c.classify_error('SECRET quota exceeded weekly'), 'quota_weekly')
        self.assertEqual(c.classify_error('usage limit 5 hours'), 'quota_5h')
        self.assertEqual(c.classify_error('rate limit reached'), 'quota_unspecified')
        self.assertEqual(c.classify_error('connection error SECRET'), 'manual_pause')

    def test_reparse_and_link_metadata_rejected_without_platform_privilege(self):
        from types import SimpleNamespace
        for meta in (SimpleNamespace(st_mode=stat.S_IFLNK, st_file_attributes=0),
                     SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)):
            with patch.object(Path, 'lstat', return_value=meta), self.assertRaises(ValueError):
                c.plain(self.root)

    def test_cli_resume_nonzero_on_drift_and_redacts_action_text(self):
        self.create()
        self.artifact.write_text('drift', encoding='utf-8')
        result = subprocess.run([os.sys.executable, '-B', str(Path(c.__file__)), 'resume',
                                 '--project', str(self.root), '--out', str(self.out)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(self.plan['next_actions'][0], result.stdout)
        self.assertTrue(json.loads(result.stdout)['reinspection_required'])


if __name__ == '__main__':
    unittest.main()
