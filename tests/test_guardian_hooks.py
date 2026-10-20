"""Advisory adapter boundary tests; no models, hook trust bypass or user config."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from tools import guardian_hooks as h


class HookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()/'codex'

    def test_preview_writes_nothing(self):
        self.assertTrue(h.manage(self.home)['dry_run'])
        self.assertFalse(self.home.exists())

    def test_stop_does_not_configure_unsupported_context(self):
        self.assertNotIn('additionalContextLimit',h.groups()['SubagentStop']['hooks'][0])
        self.assertIn('additionalContextLimit',h.groups()['SessionStart']['hooks'][0])

    def test_running_interpreter_symlink_resolves_before_strict_path_check(self):
        link = self.home.parent/'python-link'
        try:
            link.symlink_to(Path(sys.executable).resolve(strict=True))
        except OSError:
            self.skipTest('Symlink creation unavailable')
        with self.assertRaises(ValueError):
            h.safe(link)
        with patch.object(h.sys,'executable',str(link)):
            self.assertIn(str(Path(sys.executable).resolve(strict=True)),h._command())

    def test_legacy_stop_definition_can_be_explicitly_removed(self):
        h.manage(self.home,apply=True)
        config=self.home/'hooks.json';receipt=self.home/'guardian-hooks.json'
        d=json.loads(config.read_text());r=json.loads(receipt.read_text())
        d['hooks']['SubagentStop'][0]['hooks'][0]['additionalContextLimit']=4096
        r['groups']['SubagentStop']['hooks'][0]['additionalContextLimit']=4096
        config.write_text(json.dumps(d));receipt.write_text(json.dumps(r))
        self.assertFalse(h.manage(self.home,'uninstall',apply=True)['registered'])

    def test_foreign_handlers_and_config_preserved_during_lifecycle(self):
        self.home.mkdir()
        original = {'description': 'User settings', 'custom': {'opaque': [42, 'ação']},
                    'hooks': {'UserPromptSubmit': [{'matcher': 'x', 'hooks': [{'type': 'command', 'command': 'echo foreign'}]}]}}
        (self.home/'hooks.json').write_text(json.dumps(original), encoding='utf8')
        self.assertTrue(h.manage(self.home, apply=True)['registered'])
        installed = json.loads((self.home/'hooks.json').read_text(encoding='utf8'))
        self.assertEqual(installed['custom'], original['custom'])
        self.assertEqual(installed['hooks']['UserPromptSubmit'][0], original['hooks']['UserPromptSubmit'][0])
        self.assertTrue(h.manage(self.home, apply=True)['unchanged'])
        self.assertFalse(h.manage(self.home, 'uninstall', apply=True)['registered'])
        self.assertEqual(json.loads((self.home/'hooks.json').read_text(encoding='utf8')), original)

    def test_receipt_is_not_adoption_authority(self):
        self.home.mkdir()
        (self.home/'hooks.json').write_text(json.dumps({'hooks': {e:[g] for e,g in h.groups().items()}}))
        with self.assertRaisesRegex(ValueError, 'Unmanaged'):
            h.manage(self.home, apply=True)

    def test_modified_owned_handler_blocks_without_overwrite(self):
        h.manage(self.home, apply=True)
        p=self.home/'hooks.json';d=json.loads(p.read_text());d['hooks']['SessionStart'][0]['hooks'][0]['command']='foreign change'
        p.write_text(json.dumps(d));before=p.read_bytes()
        with self.assertRaisesRegex(ValueError, 'changed or missing'):
            h.manage(self.home, 'uninstall', apply=True)
        self.assertEqual(p.read_bytes(), before)

    def test_interrupted_install_can_be_explicitly_undone(self):
        original=h.atomic_write
        def fail_config(path,data):
            if Path(path).name=='hooks.json': raise OSError('fixture interrupted')
            return original(path,data)
        with patch.object(h,'atomic_write',side_effect=fail_config):
            with self.assertRaises(OSError):h.manage(self.home,apply=True)
        self.assertTrue(h.manage(self.home,'doctor')['interrupted'])
        self.assertTrue(h.manage(self.home,'uninstall',apply=True)['recovered'])
        self.assertFalse((self.home/'guardian-hooks.json').exists())

    def test_duplicate_json_and_bounded_events_rejected(self):
        with self.assertRaises(ValueError):h._decode(b'{"hooks":{},"hooks":{}}')
        with self.assertRaises(ValueError):h._decode(b' '* (h.MAX_BYTES+1))
        with self.assertRaises(ValueError):h.handle({'hook_event_name':'UserPromptSubmit','prompt':'x'*8001})
        with self.assertRaises(ValueError):h.handle({'hook_event_name':'PreToolUse'})

    def test_foreign_role_and_stop_do_not_claim_verification(self):
        self.assertEqual(h.handle({'hook_event_name':'SubagentStop','last_assistant_message':'approved100%'}),{})
        self.assertEqual(h.handle({'hook_event_name':'SubagentStart','agent_type':'foreign_role'}),{})

    def test_real_handler_process_never_echoes_prompt_or_executes_text(self):
        marker=self.home.parent/'must-not-exist'
        prompt='Uma pessoa consegue entrar na conta de outra empresa; investigue. SECRET_CANARY_X; '+str(marker)
        result=subprocess.run([sys.executable,'-B',str(h.ROOT/'tools/guardian_hooks.py'),'handle'],
                              input=json.dumps({'hook_event_name':'UserPromptSubmit','prompt':prompt,'transcript_path':'nonexistent-private-file'}),
                              capture_output=True,text=True,encoding='utf8',timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        d=json.loads(result.stdout)
        self.assertEqual(d['hookSpecificOutput']['hookEventName'],'UserPromptSubmit')
        self.assertIn('S14',d['hookSpecificOutput']['additionalContext'])
        self.assertNotIn('SECRET_CANARY_X',result.stdout)
        self.assertNotIn(str(marker),result.stdout)
        self.assertFalse(marker.exists())

    def test_invalid_input_failure_is_sanitized(self):
        result=subprocess.run([sys.executable,'-B',str(h.ROOT/'tools/guardian_hooks.py'),'handle'],
                              input='SECRET_CANARY_X',capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,1)
        self.assertNotIn('SECRET_CANARY_X',result.stdout+result.stderr)


if __name__=='__main__':unittest.main()
