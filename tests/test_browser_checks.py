import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools import guardian_browser_checks as b


def observation():
    return {'protocol_version': 1, 'stack': 'real-browser', 'browser_version': 'test',
            'variants': [{'variant': v, 'errors': [], 'checks': [
                {'id': c, 'status': 'FAILED' if c in expected else 'PASSED', 'observed': {}}
                for c in sorted(b.CHECKS)]} for v, expected in b.CASES.items()]}


class BrowserChecksTests(unittest.TestCase):
    def test_preview_does_not_execute_tools_or_claim_browser(self):
        with patch.object(b, 'execute', side_effect=AssertionError('No processes')):
            result = b.preview()
        self.assertFalse(result['browser_verified'])
        self.assertEqual(result['execution'], 'NOT_RUN')
        self.assertEqual(len(result['cases']), 10)

    def test_every_variant_requires_its_specific_assertion(self):
        result = b.assess(observation())
        self.assertTrue(all(r['status'] == 'PASSED' for r in result))
        document = observation()
        next(c for c in document['variants'][1]['checks'] if c['id'] == 'stale_navigation_rejected')['status'] = 'FAILED'
        self.assertTrue(any(r['status'] == 'FAILED' for r in b.assess(document)))

    def test_wrong_failure_and_false_negative_do_not_pass(self):
        document = observation()
        for check in document['variants'][1]['checks']: check['status'] = 'PASSED'
        self.assertEqual(b.assess(document)[1]['status'], 'FAILED')
        for check in document['variants'][1]['checks']:
            if check['id'] == 'stale_navigation_rejected': check['status'] = 'FAILED'
        self.assertEqual(b.assess(document)[1]['status'], 'FAILED')

    def test_infrastructure_error_and_missing_browser_fail_closed(self):
        for change in ({'infrastructure_error': 'Launch failed'}, {'browser_version': ''}):
            document = observation(); document.update(change)
            with self.assertRaises(ValueError): b.assess(document)
        document = observation(); document['variants'][0]['errors'] = ['TypeError']
        with self.assertRaises(ValueError): b.assess(document)

    def test_inventory_cannot_omit_duplicate_or_unknown_case_or_check(self):
        base = observation()
        altered = []
        d = copy.deepcopy(base); d['variants'].pop(); altered.append(d)
        d = copy.deepcopy(base); d['variants'][1] = d['variants'][0]; altered.append(d)
        d = copy.deepcopy(base); d['variants'][0]['checks'].pop(); altered.append(d)
        d = copy.deepcopy(base); d['variants'][0]['checks'][1] = d['variants'][0]['checks'][0]; altered.append(d)
        for document in altered:
            with self.assertRaises(ValueError): b.assess(document)

    def test_duplicate_json_and_nonfinite_values_rejected(self):
        for value in ('{"id":1,"id":2}', '{"id":NaN}'):
            with self.assertRaises(ValueError): b.strict_json(value)

    def test_missing_dependency_stays_blocked(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(b, 'dependency', return_value=None), \
             patch.object(b, 'execute', side_effect=AssertionError('Cannot execute unavailable runtime')):
            report = b.run(Path(temp).resolve()/'new')
        self.assertEqual(report['execution'], 'BLOCKED')
        self.assertFalse(report['browser_verified'])
        self.assertNotIn('passed', report)

    def test_arbitrary_process_failure_never_accepts_mutants(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(b, 'dependency', return_value={'node':'node','module':'module','channel':'chrome'}), \
             patch.object(b, 'execute', return_value={'exit_code': 1, 'stdout': b'{}', 'stderr': b'ImportError'}):
            report = b.run(Path(temp).resolve()/'new')
        self.assertEqual(report['execution'], 'BLOCKED')
        self.assertFalse(report['browser_verified'])

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp).resolve(); sentinel = folder/'keep.txt'; sentinel.write_text('original')
            with self.assertRaises(ValueError): b.run(folder)
            self.assertEqual(sentinel.read_text(), 'original')

    def test_timeout_terminates_the_fixture_process_tree(self):
        timeout = b.subprocess.TimeoutExpired(['node'], 120)
        process = type('Process', (), {})()
        from unittest.mock import Mock
        process.communicate = Mock(side_effect=[timeout, (b'', b'')])
        with patch.object(b.subprocess, 'Popen', return_value=process), patch.object(b, 'terminate_tree') as terminate:
            with self.assertRaises(b.subprocess.TimeoutExpired): b.execute(['node'], Path('.'), {})
        terminate.assert_called_once_with(process)


if __name__ == '__main__': unittest.main()
