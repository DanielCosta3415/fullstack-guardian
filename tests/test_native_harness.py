import json, subprocess, sys, tempfile, unittest
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]

class NativeHarnessTests(unittest.TestCase):
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
