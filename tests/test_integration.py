import importlib.util, unittest
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('integration_guardian',BASE/'tools/guardian.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
class IntegrationTests(unittest.TestCase):
    def ready(self):
        r=g.audit_template('.')
        for c in r['capabilities']:
            c.update(status='atendido',evidence=['Local test log: assertion passed'])
        return r
    def test_critical_finding_blocks(self):
        r=self.ready();r['findings']=[{'id':'F1','severity':'critical','status':'open'}]
        self.assertEqual(g.gate(r)['decision'],'BLOCKED')
    def test_duplicate_capability_blocks(self):
        r=self.ready();r['capabilities'].append(dict(r['capabilities'][0]))
        self.assertEqual(g.gate(r)['decision'],'BLOCKED')
    def test_blank_evidence_blocks(self):
        r=self.ready();r['capabilities'][0]['evidence']=[' ']
        self.assertEqual(g.gate(r)['decision'],'BLOCKED')
    def test_high_partial_blocks(self):
        r=self.ready();r['capabilities'][0].update(status='parcial',severity='high')
        self.assertEqual(g.gate(r)['decision'],'BLOCKED')
    def test_complete_evidence_requires_human_review(self):
        self.assertEqual(g.gate(self.ready())['decision'],'READY_FOR_HUMAN_REVIEW')
    def test_malformed_report_blocks(self):
        for r in (None,[],{}, {'capabilities':[None]}, {'capabilities':[{'id':[], 'status':'atendido'}]}):
            self.assertEqual(g.gate(r)['decision'],'BLOCKED')
    def test_unknown_finding_severity_blocks(self):
        r=self.ready();r['findings']=[{'severity':'unclassified'}]
        self.assertEqual(g.gate(r)['decision'],'BLOCKED')
    def test_runtime_contains_installer(self):
        spec=importlib.util.spec_from_file_location('integration_install',BASE/'install.py')
        i=importlib.util.module_from_spec(spec);spec.loader.exec_module(i)
        jobs,_,_=i.proposal('user',BASE/'fake-home')
        self.assertTrue(any(dst.name=='install.py' for _,dst in jobs))
