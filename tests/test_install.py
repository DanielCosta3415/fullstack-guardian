import importlib.util,tempfile,unittest
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('install',BASE/'install.py')
inst=importlib.util.module_from_spec(spec);spec.loader.exec_module(inst)
class InstallTests(unittest.TestCase):
 def test_safe_project_plan(self):
  with tempfile.TemporaryDirectory() as t:
   jobs,policy,piece=inst.proposal('project',Path(t).resolve())
   self.assertGreater(len(jobs),40)
   self.assertEqual(policy,Path(t).resolve()/'AGENTS.md')
   self.assertFalse(policy.exists())
 def test_marker_idempotence(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t).resolve()/'AGENTS.md';p.write_text('Regra existente\n')
   src=BASE/'project-template'/'AGENTS.md'
   inst.append_instruction(p,src,True)
   inst.append_instruction(p,src,True)
   self.assertIn('Regra existente',p.read_text(encoding='utf8'))
   self.assertEqual(p.read_text(encoding='utf8').count(inst.START),1)
if __name__=='__main__':unittest.main()
