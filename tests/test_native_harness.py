import json, subprocess, sys, tempfile, unittest
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]

class NativeHarnessTests(unittest.TestCase):
    def test_check_instruction_is_carried_by_each_forwarded_case_task(self):
        from tools.test_native_agents import with_check_instruction
        from tools.native_check_evidence import specifications
        original={'id':'A00','task':'Read the case','case_directory':'C:/controlled/A00'}
        case=with_check_instruction(original)
        code=case['task'].split('standalone source: ',1)[1].split(' Use separate',1)[0]
        self.assertEqual(specifications(code),[{'cmd':'python -B check.py','workdir':'C:/controlled/A00','max_output_tokens':2000}])
        self.assertEqual(original['task'],'Read the case')
    def test_empty_native_inventory_and_boolean_exit_cannot_pass(self):
        from tools.native_public_summary import public_summary
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'summary.json'
            p.write_text(json.dumps({'expected':0,'verified':0,'exit_code':0,'protected_fixtures_unchanged':True}))
            with self.assertRaises(ValueError):public_summary(p)
            p.write_text(json.dumps({'expected':39,'verified':39,'exit_code':False,'protected_fixtures_unchanged':True}))
            self.assertFalse(public_summary(p,39)['all_native_roles_verified'])
            with self.assertRaises(ValueError):public_summary(p,29)
            p.write_text(json.dumps({'expected':39,'verified':39,'exit_code':0,'protected_fixtures_unchanged':True,'source_revision_unchanged':False}))
            self.assertFalse(public_summary(p,39)['all_native_roles_verified'])
    def test_default_is_quota_free_plan(self):
        p=subprocess.run([sys.executable,str(BASE/'tools/test_native_agents.py')],capture_output=True,text=True,encoding='utf8')
        self.assertEqual(p.returncode,0,p.stderr)
        result=json.loads(p.stdout);self.assertFalse(result['quota_consumed']);self.assertEqual(len(result['native_types']),4)
    def test_all_plan_has_every_native_type(self):
        p=subprocess.run([sys.executable,str(BASE/'tools/test_native_agents.py'),'--all'],capture_output=True,text=True,encoding='utf8')
        self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout);self.assertEqual(len(set(r['native_types'])),29)
    def test_focused_retry_plan(self):
        p=subprocess.run([sys.executable,str(BASE/'tools/test_native_agents.py'),'--agents','A00'],capture_output=True,text=True,encoding='utf8')
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout)['native_types'],['guardian_engineering_orchestrator'])
    def test_cases_are_portable_and_complete(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve()
            p=subprocess.run([sys.executable,str(BASE/'tools/native_cases.py'),str(root),str(BASE/'core/agents.json')],capture_output=True,text=True,encoding='utf8')
            self.assertEqual(p.returncode,0,p.stderr)
            cases=json.loads((root/'project/cases.json').read_text(encoding='utf8'));self.assertEqual(len(cases),29)
            for c in cases:self.assertTrue((Path(c['case_directory'])/'check.py').is_file())
            auth=next(c for c in cases if c['id']=='S14')
            failed=subprocess.run([sys.executable,'-B',str(Path(auth['case_directory'])/'check.py')],cwd=auth['case_directory'],capture_output=True,text=True)
            self.assertEqual(failed.returncode,1);self.assertIn('Bob accessed Alice',failed.stderr)


class OptionalNativeHarnessTests(unittest.TestCase):
    def test_optional_plan_has_39_unique_roles_and_no_quota(self):
        p=subprocess.run([sys.executable,'-B',str(BASE/'tools/test_native_agents.py'),'--all','--include-packs'],capture_output=True,text=True,encoding='utf8')
        self.assertEqual(p.returncode,0,p.stderr)
        result=json.loads(p.stdout)
        self.assertFalse(result['quota_consumed'])
        self.assertEqual(len(set(result['native_types'])),39)

    def test_optional_cases_are_seeded_readonly_domain_checks(self):
        from tools.native_pack_cases import create
        with tempfile.TemporaryDirectory() as t:
            project=Path(t).resolve()
            cases=create(project,BASE/'packs')
            self.assertEqual(len(cases),10)
            for c in cases:
                self.assertEqual(c['mode'],'AUDIT')
                p=subprocess.run([sys.executable,'-B',str(Path(c['case_directory'])/'check.py')],capture_output=True,text=True)
                self.assertEqual(p.returncode,1,(c['id'],p.stdout,p.stderr))
                self.assertIn('AssertionError',p.stderr)
