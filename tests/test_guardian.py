import importlib.util, tempfile, json, unittest
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('guardian',BASE/'tools'/'guardian.py')
guardian=importlib.util.module_from_spec(spec);spec.loader.exec_module(guardian)
class GuardianTests(unittest.TestCase):
    def test_catalog(self):
        result=guardian.validate();self.assertTrue(result['ok'],result['errors']);self.assertEqual(result['capabilities'],132)
    def test_golden_routing(self):
        result=guardian.evals();self.assertEqual(result['passed'],result['total'],result['failed'])
    def test_financial_concurrency(self):
        result=guardian.route('Corrigir transferências Pix simultâneas');ids={r['id'] for r in result['agents']}
        self.assertTrue({'S08','S10','S11','S18','G01'}<=ids);self.assertEqual(result['risk'],'high')
    def test_frontend_no_release(self):
        r=guardian.route('Corrigir interface CSS da tela');ids={x['id'] for x in r['agents']}
        self.assertIn('S05',ids);self.assertNotIn('G02',ids)
    def test_destructive_prod(self):
        r=guardian.route('Deletar dados em produção do banco');self.assertEqual(r['risk'],'critical');self.assertIn('G02',{x['id'] for x in r['agents']})
    def test_audit_template_defaults_unknown(self):
        r=guardian.audit_template('.');self.assertEqual(len(r['capabilities']),132)
        self.assertEqual(guardian.gate(r)['decision'],'UNKNOWN')
    def test_gate_refuses_unproven_attendance(self):
        r=guardian.audit_template('.');r['capabilities'][0]['status']='atendido';r['capabilities'][0]['evidence']=[]
        self.assertEqual(guardian.gate(r)['decision'],'BLOCKED')
    def test_gate_rejects_missing_capability(self):
        r=guardian.audit_template('.');r['capabilities'].pop();self.assertEqual(guardian.gate(r)['decision'],'BLOCKED')
    def test_static_inventory_no_execution(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'server.csproj').write_text('<Project/>');(p/'App.razor').write_text('hi');(p/'Dockerfile').write_text('FROM base')
            r=guardian.inspect_project(p);self.assertTrue({'backend','frontend','container'}<=set(r['tags']))
            self.assertEqual(r['criticality'],'unknown')
    def test_auditors_run_after_workers(self):
        r=guardian.route('Auditar completamente a segurança da API em produção')
        phases=[p['phase'] for p in r['phases']]
        self.assertTrue(phases.index('domain_audit') < phases.index('independent_review') < phases.index('production_readiness_gate'))
    def test_architecture_needs_evidence(self):
        with tempfile.TemporaryDirectory() as t:
            profile={'dimensions':{}}
            r=guardian.assess(t,profile)
            self.assertEqual(r['to_be_preliminary'],'undetermined')
            self.assertEqual(len(r['dimensions_missing']),8)
    def test_criticality_does_not_force_microservices(self):
        with tempfile.TemporaryDirectory() as t:
            fields=guardian.load('architecture-dimensions.json')['fields']
            data={'dimensions':{k:{'score':0,'evidence':'Requisito registrado e aprovado'} for k in fields}}
            data['dimensions']['business_criticality']['score']=3
            r=guardian.assess(t,data)
            self.assertTrue(r['critical_control_override'])
            self.assertNotEqual(r['to_be_preliminary'],'robust')
    def test_nonexistent_inventory(self):
        with self.assertRaises(ValueError):guardian.inspect_project('/not-a-real-guardian-project-1426')
if __name__=='__main__':unittest.main()
