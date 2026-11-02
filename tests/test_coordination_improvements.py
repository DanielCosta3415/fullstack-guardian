import copy
from pathlib import Path
import unittest

from tools.guardian_policy import Grant, assess_action
from tools.guardian_platform import create_plan, validate_plan
from tools.guardian_contracts import default_contract
from tools.guardian_coordination import recommend_team, execution_waves, summarize_metrics
from tools.guardian_capabilities import runtime_context, bind_observation, require_runtime_dependencies


def current_profiles(plan):
    from tools.guardian_catalog import catalog_document
    expected = {r['name']: r['sha256'] for r in catalog_document()['records']}
    return {t['agent_type']: expected[t['agent_type']] for t in plan['tasks']}


class ProportionalActionTests(unittest.TestCase):
    def test_high_risk_read_proceeds_with_review_without_new_approval(self):
        result = assess_action('read', '.', domain_risk='high')
        self.assertTrue(result['allowed']); self.assertTrue(result['independent_review_required'])
        self.assertFalse(result['new_authorization_required']); self.assertFalse(result['correctness_verified'])
        plan = create_plan('Audit security authorization', mode='audit')
        self.assertFalse(plan['human_authorization_required'])
        self.assertTrue(plan['effect_assessment']['independent_review_required'])
        self.assertIn('G01', [t['agent_id'] for t in plan['tasks']])
        self.assertTrue(validate_plan(plan)['valid'])

    def test_existing_scoped_grant_and_actual_permission_required_for_mutations(self):
        root = Path('.').resolve()
        grant = Grant(str(root), frozenset({'local_write'}), (str(root / 'src'),), 100, 'human_session')
        result = assess_action('local_write', root, domain_risk='high', path=root / 'src/a.py', grant=grant, now=50)
        self.assertFalse(result['allowed']); self.assertFalse(result['new_authorization_required'])
        self.assertTrue(assess_action('local_write', root, domain_risk='high', path=root / 'src/a.py', grant=grant, permission_observed=True, now=50)['allowed'])
        for action in ('privileged', 'production', 'external_write'):
            self.assertFalse(assess_action(action, root, domain_risk='low', grant=grant, permission_observed=True, now=50)['allowed'])
        self.assertFalse(assess_action('read', root, domain_risk='low', permission_observed=False)['allowed'])
        self.assertFalse(assess_action('local_write', root, domain_risk='low', grant={'allowed': True}, permission_observed=True)['allowed'])


class RuntimeObservationTests(unittest.TestCase):
    def setUp(self):
        self.context = runtime_context(client='desktop', version='synthetic-v1', os_name='Windows',
            profiles={'guardian_backend_domain': 'a' * 64}, tools=['exec_command'], configuration_sha256='b' * 64)
        self.observation = bind_observation(self.context, {'spawn': {'status': 'verified', 'evidence': 'controlled-smoke-artifact'}}, observed_at=100, ttl_seconds=60)

    def test_dependencies_block_absent_roles_tools_and_unknown_features(self):
        self.assertTrue(require_runtime_dependencies(self.observation, self.context, roles=['guardian_backend_domain'], tools=['exec_command'], features=['spawn'], now=101)['allowed'])
        for kw in ({'roles': ['missing']}, {'tools': ['browser']}, {'features': ['tool_restrictions']}, {'features': ['invented']}):
            self.assertFalse(require_runtime_dependencies(self.observation, self.context, now=101, **kw)['allowed'])

    def test_profile_client_tools_or_configuration_drift_expires_observation(self):
        changes = [{'profiles': {'guardian_backend_domain': 'c' * 64}}, {'tools': ['exec_command', 'browser']},
                   {'client': 'cli'}, {'version': 'new-version'}, {'configuration_sha256': 'd' * 64}]
        args = {'client': 'desktop', 'version': 'synthetic-v1', 'os_name': 'Windows', 'profiles': {'guardian_backend_domain': 'a' * 64}, 'tools': ['exec_command'], 'configuration_sha256': 'b' * 64}
        for change in changes:
            current = runtime_context(**(args | change))
            result = require_runtime_dependencies(self.observation, current, now=101)
            self.assertIn('runtime_context_changed', result['blocked_dependencies'])

    def test_clock_expiry_and_tamper(self):
        for now in (99, 160, 200):
            self.assertFalse(require_runtime_dependencies(self.observation, self.context, now=now)['allowed'])
        self.context['profiles']['guardian_backend_domain'] = 'c' * 64
        with self.assertRaises(ValueError): require_runtime_dependencies(self.observation, self.context, now=101)

    def test_no_isolation_or_native_execution_inferred(self):
        result = require_runtime_dependencies(self.observation, self.context, now=101)
        self.assertFalse(result['sandbox_verified']); self.assertFalse(result['authenticated'])
        self.assertFalse(self.observation['native_execution_verified'])
        with self.assertRaises(ValueError): bind_observation(self.context, {}, ttl_seconds=0)

    def test_platform_preflight_blocks_only_missing_role_tool_dependencies(self):
        from tools.guardian_platform import execution_readiness
        plan = create_plan('Fix backend service')
        args = dict(client='desktop', version='synthetic-v1', os_name='Windows',
                    profiles=current_profiles(plan),
                    tools=['exec_command'], configuration_sha256='b' * 64)
        context = runtime_context(**args)
        observation = bind_observation(context, {'spawn': {'status': 'verified', 'evidence': 'controlled-run'}})
        bindings = {'project_artifact_reader': ['exec_command']}
        report = execution_readiness(plan, observation, context, bindings)
        self.assertTrue(report['ok']); self.assertFalse(report['authorization_granted'])
        self.assertFalse(execution_readiness(plan, observation, context, {})['ok'])
        stale_profiles = dict(args['profiles']); stale_profiles[plan['tasks'][0]['agent_type']] = 'a' * 64
        stale = runtime_context(**(args | {'profiles': stale_profiles}))
        stale_observation = bind_observation(stale, {'spawn': {'status': 'verified', 'evidence': 'new-observation-old-profile'}})
        self.assertFalse(execution_readiness(plan, stale_observation, stale, bindings)['ok'])
        missing_role = dict(args['profiles']); missing_role.pop(plan['tasks'][0]['agent_type'])
        # Keep a nonempty observed inventory for the other tasks.
        if missing_role:
            changed = runtime_context(**(args | {'profiles': missing_role}))
            newer = bind_observation(changed, {'spawn': {'status': 'verified', 'evidence': 'controlled-run'}})
            result = execution_readiness(plan, newer, changed, bindings)
            self.assertFalse(result['ok'])
            self.assertTrue(any(t['dependencies_observed'] for t in result['tasks']))

    def test_tool_binding_cannot_waive_a_required_restriction_feature(self):
        from tools.guardian_platform import execution_readiness
        plan = create_plan('Fix backend service')
        context = runtime_context(client='desktop', version='synthetic-v1', os_name='Windows',
            profiles=current_profiles(plan), tools=['exec_command'], configuration_sha256='b' * 64)
        for required, feature in (('network_isolation', 'network_isolation'), ('read_only_sandbox', 'filesystem_isolation'), ('workspace_write_sandbox', 'filesystem_isolation'), ('workspace_sandbox', 'filesystem_isolation')):
            plan['tasks'][0]['contract']['tool_requirements'] = [required]
            bindings = {'project_artifact_reader': ['exec_command'], required: ['exec_command']}
            for status in ('unknown', 'unsupported', 'verified'):
                observed = bind_observation(context, {'spawn': {'status': 'verified', 'evidence': 'controlled-run'},
                    feature: {'status': status, 'evidence': None if status == 'unknown' else 'synthetic-boundary-probe'}})
                report = execution_readiness(plan, observed, context, bindings)
                self.assertEqual(report['ok'], status == 'verified', (required, status))


class MinimalTeamTests(unittest.TestCase):
    def test_simple_task_uses_one_worker_and_keeps_mandatory_gate(self):
        candidates = [{'id': 'S05', 'covers': ['ui'], 'available': True}, {'id': 'S17', 'covers': ['ui'], 'available': True}, {'id': 'G01', 'covers': [], 'available': True}]
        self.assertEqual(recommend_team(['ui'], candidates)['selected'], ['S05'])
        self.assertEqual(recommend_team(['ui'], candidates, mandatory_roles=['G01'])['selected'], ['G01', 'S05'])
        result = recommend_team(['ui'], candidates, mandatory_roles=['G01'], max_agents=1)
        self.assertFalse(result['within_budget']); self.assertIn('G01', result['selected'])
        with self.assertRaises(ValueError):
            recommend_team(['ui'], candidates, mandatory_roles=(key for key in ['G01']))

    def test_unavailable_gate_or_uncovered_obligation_blocks(self):
        candidates = [{'id': 'S05', 'covers': ['ui'], 'available': True}]
        self.assertFalse(recommend_team(['ui'], candidates, mandatory_roles=['G01'])['within_budget'])
        self.assertEqual(recommend_team(['ui', 'data'], candidates)['uncovered'], ['data'])

    def test_wave_dependency_and_overlapping_casefold_write_scopes(self):
        def task(key, paths, deps=()):
            contract = default_contract('bounded task', ['check'])
            if paths: contract.update(operation='write', allowed_paths=paths)
            return {'id': key, 'depends_on': list(deps), 'contract': contract}
        tasks = [task('a', ['src/**']), task('b', ['SRC/file.py']), task('c', ['docs/file.md']), task('review', [], ['a', 'b', 'c'])]
        waves = execution_waves(tasks)['waves']
        self.assertEqual(waves[0], ['a', 'c']); self.assertEqual(waves[1], ['b']); self.assertEqual(waves[2], ['review'])
        self.assertEqual(execution_waves([task('directory', ['src/**']), task('parent', ['src'])])['waves'], [['directory'], ['parent']])
        tasks[0]['depends_on'] = ['review']
        with self.assertRaises(ValueError): execution_waves(tasks)

    def test_metrics_distinguish_unknown_estimate_billed_and_partial_acceptance(self):
        row = {'task': 'a', 'obligations': ['fix'], 'elapsed_seconds': 1.5, 'calls': 2, 'rework': 1, 'accepted': True,
               'tokens': None, 'cost_minor': None, 'cost_kind': 'unknown', 'currency': None}
        other = dict(row, task='b', accepted=False, cost_minor=20, cost_kind='estimate', currency='USD')
        report = summarize_metrics([row, other])
        self.assertEqual(report['accepted_obligations'], 0); self.assertIsNone(report['tokens'])
        self.assertEqual(report['unknown_cost_tasks'], 1); self.assertEqual(report['costs'][0]['kind'], 'estimate')
        with self.assertRaises(ValueError): summarize_metrics([row | {'prompt': 'private'}])
        with self.assertRaises(ValueError): summarize_metrics([row | {'elapsed_seconds': float('nan')}])
        with self.assertRaises(ValueError): summarize_metrics([row, row])
