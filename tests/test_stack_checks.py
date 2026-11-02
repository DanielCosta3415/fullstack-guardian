import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from tools import guardian_stack_checks as s


def observed(stack, variant, *, failed=None, unavailable=(), exit_code=None):
    failed = s.CASES[stack][variant] if failed is None else failed
    checks = [{'id': identifier, 'status': 'FAILED' if identifier in failed else 'NOT_AVAILABLE' if identifier in unavailable else 'PASSED'}
              for identifier in sorted(s.CHECKS[stack])]
    return {'stdout': json.dumps({'stack': stack, 'variant': variant, 'checks': checks}).encode(),
            'stderr': b'', 'timed_out': False, 'exit_code': (1 if failed else 0) if exit_code is None else exit_code}


class StackChecksTests(unittest.TestCase):
    def test_preview_never_launches_any_runtime(self):
        with patch.object(s.subprocess, 'Popen', side_effect=AssertionError('No subprocess in preview')):
            report = s.preview()
        self.assertEqual(report['execution'], 'NOT_RUN')
        self.assertFalse(report['browser_verified'])
        self.assertFalse(report['native_models_executed'])

    def test_every_baseline_and_exact_fault_protocol(self):
        for stack, variants in s.CASES.items():
            for variant in variants:
                with self.subTest(stack=stack, variant=variant):
                    actual = s.assess(stack, variant, observed(stack, variant))
                    self.assertEqual(actual['status'], 'PASSED')
                    self.assertEqual(actual['reason'], 'baseline_passed' if variant == 'baseline' else 'specific_fault_rejected')

    def test_arbitrary_process_failure_is_not_a_successful_negative(self):
        for code in (0, 2, 42):
            actual = s.assess('node', 'absent-null', observed('node', 'absent-null', exit_code=code))
            self.assertEqual(actual['status'], 'FAILED')
        actual = s.assess('node', 'absent-null', observed('node', 'absent-null', failed=['navigation_preserves_input']))
        self.assertEqual(actual['status'], 'FAILED')

    def test_import_error_and_timeout_remain_blocked(self):
        observation = {'stdout': b'', 'stderr': b'ImportError: missing fixture runtime', 'timed_out': False, 'exit_code': 1}
        self.assertEqual(s.assess('node', 'absent-null', observation)['reason'], 'dependency_import_unavailable')
        observation['timed_out'] = True
        self.assertEqual(s.assess('node', 'absent-null', observation)['reason'], 'fixture_timeout')

    def test_missing_check_forged_identity_and_duplicate_protocol_fail_closed(self):
        observation = observed('node', 'baseline')
        document = json.loads(observation['stdout'])
        document['checks'].pop()
        observation['stdout'] = json.dumps(document).encode()
        self.assertEqual(s.assess('node', 'baseline', observation)['status'], 'BLOCKED')
        observation['stdout'] = b'{"stack":"node","stack":"node","variant":"baseline","checks":[]}'
        self.assertEqual(s.assess('node', 'baseline', observation)['status'], 'BLOCKED')
        observation['stdout'] = observed('node', 'absent-null')['stdout']
        self.assertEqual(s.assess('node', 'baseline', observation)['status'], 'BLOCKED')

    def test_reparse_unavailable_is_reported_without_fabricated_pass(self):
        name = 'parent_reparse_component_rejected'
        baseline = observed('powershell', 'baseline', unavailable=[name])
        self.assertEqual(s.assess('powershell', 'baseline', baseline)['status'], 'PASSED_WITH_LIMITATIONS')
        faulty = observed('powershell', 'parent-reparse-unchecked', failed=[], unavailable=[name], exit_code=3)
        self.assertEqual(s.assess('powershell', 'parent-reparse-unchecked', faulty)['status'], 'BLOCKED')
        # Exit3 is not an accepted assertion failure when the assertion was available.
        available = observed('powershell', 'parent-reparse-unchecked', exit_code=3)
        self.assertEqual(s.assess('powershell', 'parent-reparse-unchecked', available)['status'], 'FAILED')

    def test_unknown_stack_and_arbitrary_source_paths_are_rejected(self):
        for stacks in ([], ['node', 'node'], ['arbitrary']):
            with self.assertRaises(ValueError):
                s.preview(stacks)
        with self.assertRaises(ValueError):
            s.fixture_bytes('node', '../../candidate.js')

    def test_tools_absent_do_not_execute_or_become_passed(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(s, '_tool', return_value=None), \
             patch.object(s, 'process', side_effect=AssertionError('Missing tools cannot run')):
            report = s.run(Path(temp) / 'new-output')
        self.assertTrue(all(item['status'] == 'BLOCKED' for item in report['stacks']))

    def test_existing_output_directory_is_never_reused(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, 'new dedicated'):
                s.run(temp, ['node'])

    def test_dotnet_uses_offline_config_no_implicit_restore_and_ephemeral_homes(self):
        config = ET.fromstring(s.fixture_bytes('dotnet', 'NuGet.Config'))
        self.assertEqual([child.tag for child in config.find('packageSources')], ['clear'])
        project = ET.fromstring(s.fixture_bytes('dotnet', 'GuardianStack.csproj'))
        self.assertEqual(project.findall('.//PackageReference'), [])
        calls = []
        def fake_process(argv, folder, env, timeout=30):
            calls.append((argv, env))
            if '--version' in argv:
                return {'exit_code': 0, 'stdout': b'10.0.403\n', 'stderr': b'', 'timed_out': False}
            if len(argv) > 1 and argv[1] in ('restore', 'build'):
                return {'exit_code': 0, 'stdout': b'', 'stderr': b'', 'timed_out': False}
            return observed('dotnet', argv[-1])
        with tempfile.TemporaryDirectory() as temp, patch.object(s, '_tool', return_value='trusted-dotnet'), \
             patch.object(s, 'process', side_effect=fake_process):
            report = s.run(Path(temp) / 'new-output', ['dotnet'])
        self.assertEqual(report['stacks'][0]['status'], 'PASSED')
        self.assertEqual(len(calls), 8)  # version + restore + build + five variants
        self.assertIn('--configfile', calls[1][0])
        self.assertIn('--no-restore', calls[2][0])
        self.assertIn('--disable-build-servers', calls[2][0])
        for argv, env in calls:
            self.assertIsInstance(argv, list)
            self.assertEqual(env['DOTNET_ADD_GLOBAL_TOOLS_TO_PATH'], 'false')
            self.assertEqual(env['DOTNET_GENERATE_ASPNET_CERTIFICATE'], 'false')
            self.assertNotIn('NODE_OPTIONS', env)


if __name__ == '__main__':
    unittest.main()
