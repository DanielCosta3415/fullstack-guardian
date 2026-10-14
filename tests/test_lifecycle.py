import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from test_install import inst

class LifecycleTests(unittest.TestCase):
    def test_install_dry_run_and_lifecycle(self):
        with tempfile.TemporaryDirectory() as t:
            home=Path(t).resolve()
            c=home/'.codex'; c.mkdir()
            config=c/'config.toml'
            original=b'# personal\nmodel = "personal"\n[agents]\nmax_concurrent_threads_per_session = 2\n'
            config.write_bytes(original)
            (c/'AGENTS.md').write_bytes(b'Personal rules\n')
            result=inst.lifecycle('user',home)
            self.assertGreater(result['changes'],40)
            self.assertFalse((c/'guardian-install.json').exists())
            inst.lifecycle('user',home,apply=True)
            self.assertIn(b'max_concurrent_threads_per_session = 2',config.read_bytes())
            self.assertIn(b'enabled = true',config.read_bytes())
            inst.lifecycle('user',home,'doctor')
            inst.lifecycle('user',home,'update',True)
            inst.lifecycle('user',home,'uninstall',True)
            self.assertEqual(config.read_bytes(),original)
            self.assertEqual((c/'AGENTS.md').read_bytes(),b'Personal rules\n')
            self.assertFalse((c/'guardian-install.json').exists())
    def test_rollback_initial_install(self):
        with tempfile.TemporaryDirectory() as t:
            home=Path(t).resolve()
            inst.lifecycle('user',home,apply=True)
            inst.lifecycle('user',home,'rollback',True)
            self.assertFalse((home/'.codex/config.toml').exists())
            self.assertFalse((home/'.codex/guardian-install.json').exists())
    def test_divergent_file_blocks_all_changes(self):
        with tempfile.TemporaryDirectory() as t:
            home=Path(t).resolve()
            inst.lifecycle('user',home,apply=True)
            jobs,_,_=inst.proposal('user',home)
            jobs[0][1].write_bytes(b'user change')
            before=(home/'.codex/guardian-install.json').read_bytes()
            for op in ('update','uninstall','rollback','doctor'):
                with self.assertRaises(ValueError): inst.lifecycle('user',home,op,True)
            self.assertEqual((home/'.codex/guardian-install.json').read_bytes(),before)
    def test_config_preserves_existing_false(self):
        old=b'[agents]\nenabled = false\nmax_concurrent_threads_per_session = 8\n'
        self.assertEqual(inst.config_bytes(old),(old,b''))
    def test_legacy_concurrency_alias_preserved(self):
        old=b'[agents]\nenabled = true\nmax_threads = 8\n'
        self.assertEqual(inst.config_bytes(old),(old,b''))
        with tempfile.TemporaryDirectory() as t:
            home=Path(t).resolve(); c=home/'.codex'; c.mkdir()
            (c/'config.toml').write_bytes(old)
            inst.lifecycle('user',home,apply=True)
            self.assertEqual((c/'config.toml').read_bytes(),old)
            self.assertEqual(inst.lifecycle('user',home,'doctor')['warnings'],[])
    def test_empty_or_list_receipt_rejected(self):
        for content in (b'{}',b'[]',b'null',b''):
            with tempfile.TemporaryDirectory() as t:
                home=Path(t).resolve(); c=home/'.codex'; c.mkdir()
                (c/'guardian-install.json').write_bytes(content)
                with self.assertRaises(ValueError): inst.lifecycle('user',home,apply=True)
                self.assertFalse((c/'guardian-system').exists())
    def test_bad_config_and_markers(self):
        with self.assertRaises(Exception): inst.config_bytes(b'[broken')
        with self.assertRaises(ValueError): inst.config_bytes(b'agents.enabled = true\n')
        with self.assertRaises(ValueError): inst.policy_bytes(inst.START.encode(),inst.SOURCE/'global/AGENTS.md')
    def test_codex_home_and_explicit_home(self):
        with tempfile.TemporaryDirectory() as t:
            with patch.dict('os.environ',{'CODEX_HOME':str(Path(t).resolve()/'custom')}):
                self.assertEqual(inst.locations('user',None)[0],Path(t).resolve()/'custom')
                self.assertEqual(inst.locations('user',Path(t).resolve())[0],Path(t).resolve()/'.codex')
    def test_path_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve(); link=root/'linked'
            try: link.symlink_to(root,target_is_directory=True)
            except OSError: self.skipTest('OS lacks symlink privilege')
            with self.assertRaises(ValueError): inst.safe(link/'config.toml')
    def test_uninstall_preserves_unrelated_append(self):
        with tempfile.TemporaryDirectory() as t:
            home=Path(t).resolve(); inst.lifecycle('user',home,apply=True)
            policy=home/'.codex/AGENTS.md'
            policy.write_bytes(policy.read_bytes()+b'Later personal policy\n')
            inst.lifecycle('user',home,'uninstall',True)
            self.assertEqual(policy.read_bytes(),b'Later personal policy\n')
    def test_explicit_adoption_required(self):
        with tempfile.TemporaryDirectory() as t:
            home=Path(t).resolve(); jobs,_,_=inst.proposal('user',home)
            src,dst=jobs[0]; dst.parent.mkdir(parents=True); dst.write_bytes(src.read_bytes())
            with self.assertRaises(ValueError): inst.lifecycle('user',home,apply=True)
            inst.lifecycle('user',home,apply=True,adopt=True)
            inst.lifecycle('user',home,'uninstall',True)
            self.assertTrue(dst.exists())
    def test_update_changed_owned_source_and_rollback(self):
        with tempfile.TemporaryDirectory() as t:
            import shutil
            root=Path(t).resolve(); source=root/'source'; home=root/'home'
            shutil.copytree(inst.SOURCE,source,ignore=shutil.ignore_patterns('__pycache__','.git','work','dist'))
            with patch.object(inst,'SOURCE',source):
                inst.lifecycle('user',home,apply=True)
                src=source/'README.md'; previous=src.read_bytes(); src.write_bytes(previous+b'\nrelease update\n')
                inst.lifecycle('user',home,'update',True)
                deployed=home/'.codex/guardian-system/README.md'
                self.assertEqual(deployed.read_bytes(),src.read_bytes())
                inst.lifecycle('user',home,'rollback',True)
                self.assertEqual(deployed.read_bytes(),previous)
                inst.lifecycle('user',home,'doctor')
    def test_transaction_failure_restores_previous_files(self):
        with tempfile.TemporaryDirectory() as t:
            home=Path(t).resolve(); c=home/'.codex'; c.mkdir()
            original=b'Existing personal instructions\n'; (c/'AGENTS.md').write_bytes(original)
            write=Path.write_bytes
            def fail_policy(path,data):
                if path==c/'AGENTS.md' and data!=original:
                    raise OSError('injected controlled write failure')
                return write(path,data)
            with patch.object(Path,'write_bytes',fail_policy):
                with self.assertRaises(OSError): inst.lifecycle('user',home,apply=True)
            self.assertEqual((c/'AGENTS.md').read_bytes(),original)
            self.assertFalse((c/'guardian-install.json').exists())
            self.assertFalse((c/'guardian-system/README.md').exists())
    def test_added_agent_keys_retain_table_meaning(self):
        import tomllib
        for operation in ('update','uninstall'):
            with tempfile.TemporaryDirectory() as t:
                home=Path(t).resolve(); inst.lifecycle('user',home,apply=True)
                config=home/'.codex/config.toml'
                config.write_bytes(config.read_bytes()+b'max_depth = 9\n')
                self.assertEqual(inst.lifecycle('user',home,'doctor')['warnings'],[])
                inst.lifecycle('user',home,operation,True)
                parsed=tomllib.loads(config.read_text())
                self.assertEqual(parsed['agents']['max_depth'],9)
                self.assertNotIn('max_depth',parsed)
                if operation == 'update':
                    inst.lifecycle('user',home,'uninstall',True)
                    self.assertEqual(tomllib.loads(config.read_text())['agents']['max_depth'],9)
    def test_forged_receipt_credentials_rejected(self):
        import json
        with tempfile.TemporaryDirectory() as t:
            home=Path(t).resolve(); inst.lifecycle('user',home,apply=True)
            receipt=home/'.codex/guardian-install.json'; auth=home/'.codex/auth.json'
            auth.write_bytes(b'private credential')
            data=json.loads(receipt.read_text()); data['files'].append({'path':str(auth),'hash':inst.sha(auth)})
            receipt.write_text(json.dumps(data))
            with self.assertRaises(ValueError): inst.lifecycle('user',home,'uninstall',True)
            self.assertEqual(auth.read_bytes(),b'private credential')
    def test_receipt_wrong_home_rejected(self):
        import json
        with tempfile.TemporaryDirectory() as t:
            home=Path(t).resolve(); inst.lifecycle('user',home,apply=True)
            receipt=home/'.codex/guardian-install.json'; data=json.loads(receipt.read_text())
            data['identity']['codex']=str(home/'another')
            receipt.write_text(json.dumps(data))
            with self.assertRaises(ValueError): inst.lifecycle('user',home,'doctor')
    def test_doctor_unrelated_policy_and_disabled_warning(self):
        with tempfile.TemporaryDirectory() as t:
            home=Path(t).resolve(); c=home/'.codex'; c.mkdir()
            (c/'config.toml').write_bytes(b'[agents]\nenabled=false\nmax_concurrent_threads_per_session=2\n')
            inst.lifecycle('user',home,apply=True)
            policy=c/'AGENTS.md'; policy.write_bytes(policy.read_bytes()+b'Personal rule\n')
            self.assertEqual(len(inst.lifecycle('user',home,'doctor')['warnings']),1)

if __name__=='__main__': unittest.main()
