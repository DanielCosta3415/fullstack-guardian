import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

from tools.guardian_handoff import inspect_handoff, consume_handoff, invalidated_tasks


class NativeHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name).resolve()
        (self.project / 'result.txt').write_text('observed artifact', encoding='utf8')
        sha = hashlib.sha256((self.project / 'result.txt').read_bytes()).hexdigest()
        self.handoff = {'schema_version': 1, 'run': 'synthetic-run', 'task': 'task-fix',
            'revision': 'a' * 40, 'contract_sha256': 'b' * 64, 'producer': 'S08', 'consumer': 'G01',
            'obligations': ['fix'], 'artifacts': [{'path': 'result.txt', 'sha256': sha, 'obligations': ['fix']}],
            'checks': [{'id': 'regression', 'artifact_sha256': sha, 'obligations': ['fix']}],
            'unknowns': [], 'status': 'produced'}
        self.context = {'run': 'synthetic-run', 'task': 'task-fix', 'expected_producer': 'S08', 'expected_consumer': 'G01',
            'revision': 'a' * 40, 'contract_sha256': 'b' * 64, 'required_checks': copy.deepcopy(self.handoff['checks']),
            'obligations': ['fix'], 'observations': [{'id': 'regression', 'run': 'synthetic-run', 'task': 'task-fix', 'revision': 'a' * 40,
                'artifact_sha256': sha, 'passed': True, 'observer': 'primary'}]}

    def inspect(self):
        return inspect_handoff(self.project, self.handoff, **self.context)

    def test_checked_is_not_consumer_accepted_or_authenticated(self):
        result = self.inspect()
        self.assertEqual(result['status'], 'checked'); self.assertFalse(result['authenticated'])
        self.assertFalse(result['native_interception']); self.assertFalse(result['authorization_granted'])

    def test_distinct_consumer_accepts_then_content_drift_blocks(self):
        accepted = consume_handoff(self.project, self.handoff, consumer='G01', decision='accept', reason='checks-reviewed', **self.context)
        self.assertEqual(accepted['status'], 'accepted')
        (self.project / 'result.txt').write_text('changed', encoding='utf8')
        with self.assertRaises(ValueError):
            consume_handoff(self.project, self.handoff, consumer='G01', decision='accept', reason='checks-reviewed', **self.context)

    def test_missing_failed_or_self_observed_check_stays_produced(self):
        for mutate in (lambda c: c.update(observations=[]),
                       lambda c: c['observations'][0].update(passed=False),
                       lambda c: c['observations'][0].update(observer='S08'),
                       lambda c: c['observations'][0].update(run='other-run'),
                       lambda c: c['observations'][0].update(revision='c' * 40)):
            with self.subTest(mutate=mutate):
                context = copy.deepcopy(self.context); mutate(context)
                self.assertEqual(inspect_handoff(self.project, self.handoff, **context)['status'], 'produced')

    def test_mismatch_obligation_context_and_unknowns(self):
        for field, value in (('run', 'different-run'), ('revision', 'c' * 40), ('contract_sha256', 'd' * 64), ('obligations', ['other'])):
            context = copy.deepcopy(self.context); context[field] = value
            self.assertTrue(inspect_handoff(self.project, self.handoff, **context)['issues'])
        self.handoff['unknowns'] = ['essential-runtime-unobserved']
        self.assertEqual(self.inspect()['status'], 'produced')

    def test_claim_cannot_self_verify_or_self_accept(self):
        self.handoff['status'] = 'verified'
        with self.assertRaises(ValueError): self.inspect()
        self.handoff['status'] = 'produced'
        with self.assertRaises(ValueError):
            consume_handoff(self.project, self.handoff, consumer='S08', decision='accept', reason='looks-good', **self.context)

    def test_reject_incomplete_proposal(self):
        self.context['observations'] = []
        result = consume_handoff(self.project, self.handoff, consumer='G01', decision='reject', reason='missing-check', **self.context)
        self.assertEqual(result['status'], 'rejected'); self.assertTrue(result['issues'])

    def test_paths_cannot_escape_or_read_credentials(self):
        for path in ('../outside', '.codex/auth.json', '.env', 'C:/private.txt'):
            self.handoff['artifacts'][0]['path'] = path
            with self.assertRaises(ValueError): self.inspect()

    def test_check_cannot_cover_unrelated_artifact_obligations(self):
        self.handoff['obligations'].append('other'); self.context['obligations'].append('other')
        self.handoff['checks'][0]['obligations'].append('other')
        self.assertIn('unchecked_obligations', self.inspect()['issues'])

    def test_producer_cannot_omit_failed_required_check_or_replay_another_task(self):
        required = dict(self.context['required_checks'][0], id='functional')
        self.context['required_checks'].append(required)
        self.context['observations'].append(dict(self.context['observations'][0], id='functional', passed=False))
        result = self.inspect()
        self.assertIn('required_check_set_mismatch', result['issues'])
        self.assertIn('check_not_independently_observed:functional', result['issues'])
        self.context['required_checks'].pop(); self.context['observations'].pop()
        self.handoff['task'] = 'task-unrelated'
        self.assertIn('context:task', self.inspect()['issues'])

    def test_revocation_invalidates_transitive_dependents_only(self):
        graph = [{'id': 'extract', 'depends_on': [], 'evidence': ['input']},
                 {'id': 'build', 'depends_on': ['extract'], 'evidence': ['code']},
                 {'id': 'review', 'depends_on': ['build'], 'evidence': ['tests']},
                 {'id': 'docs', 'depends_on': [], 'evidence': ['manual']}]
        self.assertEqual(invalidated_tasks(graph, ['input'])['invalidated'], ['build', 'extract', 'review'])
        self.assertEqual(invalidated_tasks(graph, [])['invalidated'], [])
        graph[0]['depends_on'] = ['review']
        with self.assertRaises(ValueError): invalidated_tasks(graph, ['input'])
        graph[0]['depends_on'] = ['missing']
        with self.assertRaises(ValueError): invalidated_tasks(graph, ['input'])
