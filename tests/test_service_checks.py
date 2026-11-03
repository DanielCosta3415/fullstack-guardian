"""Observe meaningful effects, not merely a fixture's declared success flag."""
import hashlib
import json
from pathlib import Path
import sqlite3
import socket
import tempfile
import unittest
from unittest.mock import patch

from tools import guardian_service_checks as service


def loopback_available():
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        client.settimeout(2)
        client.connect(listener.getsockname())
    except PermissionError as exc:
        raise unittest.SkipTest('Local socket permission unavailable: HTTP service checks NOT VERIFIED') from exc
    finally:
        client.close()
        listener.close()


class ServiceChecks(unittest.TestCase):
    def test_preview_does_not_bind_ports_or_open_database(self):
        with patch.object(service, '_server', side_effect=AssertionError('No network in preview')):
            with patch.object(service, '_connect', side_effect=AssertionError('No database in preview')):
                plan = service.preview()
        self.assertFalse(plan['execution_requested'])
        self.assertEqual(len(plan['cases']), 8)
        self.assertIn('NOT', service.__doc__.upper())

    def test_actual_services_database_and_specific_faults(self):
        loopback_available()
        with tempfile.TemporaryDirectory(prefix='guardian-service-tests-') as temporary:
            out = Path(temporary).resolve()/'evidence'
            result = service.run(out)
            self.assertTrue(result['all_passed'], result)
            self.assertEqual(len(result['cases']), 8)
            self.assertEqual(len(result['artifact_sha256']), 8)
            self.assertEqual(result['professional_qualification'], 'NOT_EVALUATED')
            for case in result['cases']:
                positive, faulty = case['checks']
                self.assertEqual(positive['status'], 'PASSED', case)
                self.assertEqual(faulty['status'], 'PASSED', case)
                self.assertNotEqual(positive['observed'][positive['specific_discriminator']],
                                    faulty['observed'][faulty['specific_discriminator']], case)
                self.assertIsNone(positive['exception'])
                self.assertIsNone(faulty['exception'])
            for name, digest in result['artifact_sha256'].items():
                self.assertEqual(hashlib.sha256((out/name).read_bytes()).hexdigest(), digest)
            db = sqlite3.connect(out/'transaction-positive.sqlite')
            try:
                self.assertEqual(db.execute('SELECT balance FROM account').fetchone(), (65,))
                self.assertEqual(db.execute('SELECT COUNT(*) FROM outbox').fetchone(), (2,))
            finally:
                db.close()
            lock = json.loads((out/'migration-positive-lock.json').read_text(encoding='utf8'))
            self.assertEqual(lock['busy_error_code'], sqlite3.SQLITE_BUSY)
            self.assertGreater(lock['wait_ms'], 0)
            self.assertFalse(any(p.is_dir() for p in out.iterdir()))

    def test_arbitrary_failure_cannot_kill_faulty_implementation(self):
        def crash(*_):
            raise ImportError('Unavailable fixture dependency')
        altered = [('crash', ['S08-P1'], crash, {'ok': True}, 'ok')]
        with tempfile.TemporaryDirectory(prefix='guardian-service-errors-') as temporary:
            with patch.object(service, 'CASES', altered):
                report = service.run(Path(temporary).resolve()/'evidence')
        self.assertFalse(report['all_passed'])
        self.assertEqual([x['status'] for x in report['cases'][0]['checks']], ['ERROR', 'ERROR'])

    def test_existing_output_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory(prefix='guardian-service-preserve-') as temporary:
            out = Path(temporary).resolve()
            marker = out/'user.txt'
            marker.write_text('preserved', encoding='utf8')
            with self.assertRaises(ValueError):
                service.run(out)
            self.assertEqual(marker.read_text(encoding='utf8'), 'preserved')

    def test_signature_fixture_checks_raw_wire_bytes(self):
        loopback_available()
        with tempfile.TemporaryDirectory(prefix='guardian-service-wire-') as temporary:
            positive = service.wire(False, Path(temporary), service._data())
            faulty = service.wire(True, Path(temporary), service._data())
        self.assertEqual(positive['changed_wire_bytes'], 401)
        self.assertEqual(faulty['changed_wire_bytes'], 409)
        self.assertEqual(positive['valid_retry'], 200)
        self.assertEqual(positive['effects'], 1)

    def test_forbidden_stub_is_observed_only_with_specific_mutant(self):
        loopback_available()
        with tempfile.TemporaryDirectory(prefix='guardian-service-routing-') as temporary:
            positive = service.destinations(False, Path(temporary), {})
            faulty = service.destinations(True, Path(temporary), {})
        self.assertEqual(positive['forbidden_hits'], 0)
        self.assertEqual(faulty['forbidden_hits'], 2)
        self.assertEqual(positive['redirect'], 'denied')
        self.assertEqual(faulty['redirect'], 'ok')

    def test_sqlite_and_hmac_checks_do_not_require_network(self):
        with tempfile.TemporaryDirectory(prefix='guardian-service-local-') as temporary:
            for name, _, function, expected, discriminator in service.CASES:
                if name not in {'transaction', 'fencing', 'migration', 'token_rotation'}:
                    continue
                positive_folder = Path(temporary)/(name+'-positive')
                faulty_folder = Path(temporary)/(name+'-faulty')
                positive_folder.mkdir()
                faulty_folder.mkdir()
                positive = function(False, positive_folder, service._data())
                faulty = function(True, faulty_folder, service._data())
                self.assertEqual(positive, expected, name)
                self.assertNotEqual(faulty[discriminator], expected[discriminator], name)


if __name__ == '__main__':
    unittest.main()
