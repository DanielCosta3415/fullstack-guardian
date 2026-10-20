"""Checks installed acceptance never masks unit failures or creates native claims."""
import json, subprocess, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from tools.verify_installed_runtime import verify
ROOT=Path(__file__).resolve().parents[1]
class InstalledRuntimeTests(unittest.TestCase):
    def test_incomplete_layout_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError,'Incomplete'):verify(Path(t))
    def test_functional_commands_are_checked_and_native_not_claimed(self):
        with tempfile.TemporaryDirectory() as t, patch('tools.verify_installed_runtime.subprocess.run',return_value=subprocess.CompletedProcess([],0,'{}','')) as run:
            report=verify(ROOT,Path(t));self.assertEqual(len(report['checks']),5)
            self.assertFalse(report['native_models_executed']);self.assertEqual(run.call_count,5)
    def test_nonzero_command_is_never_skipped(self):
        with tempfile.TemporaryDirectory() as t, patch('tools.verify_installed_runtime.subprocess.run',return_value=subprocess.CompletedProcess([],1,'','broken')):
            with self.assertRaisesRegex(ValueError,'Runtime check failed'):verify(ROOT,Path(t))

    def test_unfiltered_suite_failure_is_never_hidden(self):
        calls=[subprocess.CompletedProcess([],0,'{}','') for _ in range(5)]+[subprocess.CompletedProcess([],1,'{"failures":["regression"]}','')]
        with tempfile.TemporaryDirectory() as t, patch('tools.verify_installed_runtime.subprocess.run',side_effect=calls):
            with self.assertRaisesRegex(ValueError,'Runtime unittest suite failed'):verify(ROOT,Path(t),suite=True)
