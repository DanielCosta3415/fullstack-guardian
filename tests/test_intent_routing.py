"""Independent obligation/paraphrase cases, not a global semantic-accuracy claim."""
import copy
import unittest
from unittest.mock import patch

from tools.guardian import route
from tools.guardian_intent import DOMAINS, validate_intent
from tools.guardian_platform import create_plan, validate_plan, load_workflows, PlatformError


def intent(domain='security', risk='low'):
    return {'schema_version': 1, 'goals': ['Prevent access to another company account'],
            'obligations': [{'id': 'isolation', 'domain': domain,
                             'acceptance': ['Cross-company reads must be denied'],
                             'evidence': ['Negative tenant-boundary regression']}],
            'risk': risk, 'constraints': ['Local controlled fixtures only'], 'uncertainties': []}


class IntentRoutingTests(unittest.TestCase):
    def test_directed_holdout_semantic_boundaries(self):
        # Expectations fixed by the obligation, independently of the audit's
        # 44 diagnostic sentences. This is regression coverage, not accuracy.
        cases = [
            ('Diagnose why another company\'s invoice is visible to this account', {'S13','S14','G01'}, set(), 'Tenant boundary requires security/IAM review'),
            ('Sem mouse: realizar cadastro utilizando somente teclado', {'S06'}, set(), 'Keyboard interaction is an accessibility obligation'),
            ('The same order was processed twice after a connection failure', {'S10','G01'}, set(), 'Repeated effect requires concurrency/idempotency review'),
            ('Revisit right-to-left layout for this locale', {'S07'}, set(), 'Locale behavior requires browser compatibility coverage'),
            ('Review contractual obligations before comparing vendors', {'S25'}, set(), 'Vendor commitments require governance review'),
            ('Assess keyboard signup and contractual obligations; no production or deployment actions', {'S06','S25'}, {'G02'}, 'Mixed obligations remain separate; release explicitly excluded'),
            ('Please investigate this unexpected difference', set(), {'G01','G02'}, 'Ambiguity needs bounded primary triage, not universal delegation'),
            ('Only replace one spelling error in README', set(), {'G01','G02'}, 'Low-impact copy change does not require review gates'),
        ]
        for prompt, required, excluded, rationale in cases:
            with self.subTest(rationale=rationale):
                result=route(prompt,mode='build')
                selected={a['id'] for a in result['agents']}
                self.assertTrue(required <= selected, rationale)
                self.assertFalse(excluded & selected, rationale)
                self.assertEqual(result['mode'],'BUILD')
                self.assertTrue(result['intent_analysis']['primary_interpretation_required'])
                self.assertFalse(result['intent_analysis']['semantic_understanding_verified'])
                # Financial + tenant-boundary coverage can legitimately need
                # seven roles; the bound must not force dropping a risk gate.
                self.assertLessEqual(len(selected),8)

    def test_security_paraphrases_cannot_be_low_risk(self):
        for prompt in ('Uma pessoa consegue entrar na conta de outra empresa',
                       'A user can read another organization records by guessing its identifier',
                       'Fix cross-tenant reads without changing production'):
            with self.subTest(prompt=prompt):
                result = route(prompt)
                self.assertTrue({'S13', 'S14', 'G01'} <= {a['id'] for a in result['agents']})
                self.assertIn(result['risk'], ('high', 'critical'))

    def test_paraphrases_cover_specialist_obligations(self):
        cases = [('Quem nao usa mouse nao consegue concluir o cadastro', 'S06'),
                 ('Keyboard-only users cannot finish signup', 'S06'),
                 ('Recebemos duas vezes a mesma encomenda e enviamos duas entregas', 'S10'),
                 ('Fix locale plural rules and right-to-left layout', 'S07'),
                 ('Comparar fornecedores e obrigacoes contratuais', 'S25'),
                 ('Planejar migracao de versao do sistema legado', 'S24'),
                 ('Os registros somem apos reiniciar o processo', 'S11'),
                 ('Descobrir se os clientes precisam antes de construir', 'S01')]
        for prompt, expected in cases:
            with self.subTest(prompt=prompt):
                self.assertIn(expected, {a['id'] for a in route(prompt)['agents']})

    def test_short_copy_and_ambiguous_prompt_do_not_spawn_everyone(self):
        for prompt in ('Corrigir uma palavra no texto do botao', 'Investigue esta diferenca'):
            result = route(prompt)
            self.assertLessEqual(len(result['agents']), 2)
            self.assertTrue(result['intent_analysis']['primary_interpretation_required'])
            self.assertFalse(result['intent_analysis']['semantic_understanding_verified'])
            self.assertFalse(result['delegation_required'])

    def test_primary_contract_adds_obligations_but_not_authority(self):
        result = route('Investigue esta diferenca', intent_contract=intent())
        self.assertTrue({'S13', 'S14', 'G01'} <= {a['id'] for a in result['agents']})
        self.assertEqual(result['risk'], 'high')
        self.assertFalse(result['intent_analysis']['content_is_authority'])
        coverage = result['intent_analysis']['obligation_coverage'][0]
        self.assertEqual(coverage['id'], 'isolation')
        self.assertEqual(set(coverage['selected_agents']), set(DOMAINS['security']))

    def test_invalid_contract_and_self_authorization_are_rejected(self):
        variants = []
        for key, value in [('authorized', True), ('risk', 'guaranteed_safe'), ('obligations', []), ('schema_version', True)]:
            doc = intent(); doc[key] = value; variants.append(doc)
        doc = intent(); doc['obligations'][0]['domain'] = 'admin'; variants.append(doc)
        doc = intent(); doc['obligations'][0]['evidence'] = []; variants.append(doc)
        doc = intent(); doc['obligations'].append(copy.deepcopy(doc['obligations'][0])); variants.append(doc)
        for doc in variants:
            with self.subTest(doc=doc), self.assertRaises(ValueError):
                validate_intent(doc)

    def test_contract_cannot_reduce_detected_risk(self):
        result = route('Fix cross-tenant account access', intent_contract=intent('frontend', 'low'))
        self.assertEqual(result['risk'], 'high')
        self.assertIn('G01', {a['id'] for a in result['agents']})
        self.assertTrue(result['intent_analysis']['deviations'])

    def test_reproduction_word_is_not_production_release(self):
        result = route('Corrigir a reproducao do bug em uma fixture local, sem deploy')
        self.assertNotIn('G02', {a['id'] for a in result['agents']})
        self.assertEqual(result['risk'], 'low')

    def test_each_phase_responsibility_is_accounted_for(self):
        for phase in load_workflows()['phases']:
            with self.subTest(stage=phase['id']):
                result = route('Investigar problema delimitado', stage=phase['id'])
                dispositions = result['phase_responsibility']
                self.assertEqual({r['agent_id'] for r in dispositions}, set(phase['responsible']))
                self.assertTrue(all(r['reason'] for r in dispositions))
                selected = {a['id'] for a in result['agents']}
                for record in dispositions:
                    self.assertEqual(record['disposition'] == 'selected', record['agent_id'] in selected)
                for gate in set(phase['responsible']) & {'G01', 'G02'}:
                    self.assertIn(gate, selected)

    def test_primary_contract_roundtrip_and_tamper(self):
        plan = create_plan('Investigue esta diferenca', intent_contract=intent())
        self.assertTrue(validate_plan(plan)['valid'])
        for field in ('phase_responsibility', 'intent_analysis'):
            changed = copy.deepcopy(plan)
            if field == 'phase_responsibility':
                changed[field][0]['reason'] = 'forged waiver'
            else:
                changed[field]['content_is_authority'] = True
            with self.subTest(field=field), self.assertRaises(PlatformError):
                validate_plan(changed)

    def test_budget_does_not_drop_independent_review(self):
        with self.assertRaises(PlatformError):
            create_plan('Fix cross-tenant reads', max_agents=1)

    def test_professional_binding_matches_contract_and_tamper_is_rejected(self):
        import hashlib
        import json
        from tools.guardian_professional import get_contract
        plan=create_plan('Corrigir backend service')
        for task in plan['tasks']:
            contract=get_contract(task['agent_id'])
            expected_hash=hashlib.sha256(json.dumps(contract,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
            self.assertEqual(task['professional_contract'],{
                'agent_id':task['agent_id'],'contract_version':contract['contract_version'],
                'contract_sha256':expected_hash,'result_fields':contract['result_contract']})
        for field,value in [('agent_id','A00'),('contract_version','99.0.0'),('contract_sha256','0'*64),('result_fields',['self_verified'])]:
            changed=copy.deepcopy(plan)
            changed['tasks'][0]['professional_contract'][field]=value
            with self.subTest(field=field),self.assertRaises(PlatformError):
                validate_plan(changed)

    def test_professional_source_change_invalidates_old_plan(self):
        from tools.guardian_professional import load_contracts
        plan=create_plan('Corrigir backend service')
        changed=copy.deepcopy(load_contracts())
        aid=plan['tasks'][0]['agent_id']
        contract=next(c for c in changed['contracts'] if c['id']==aid)
        contract['mission']+=' Changed valid professional scope.'
        # Alter only the contract mission: checkpoint identity alone would miss
        # this change; the complete canonical contract digest must catch it.
        with patch('tools.guardian_professional.load_contracts',return_value=changed):
            with self.assertRaises(PlatformError):
                validate_plan(plan)

    def test_legacy_plan_has_request_obligation_without_claiming_understanding(self):
        prompt='Corrigir backend service'
        plan=create_plan(prompt)
        self.assertEqual(plan['request_obligation']['objective'],prompt)
        self.assertEqual(plan['request_obligation']['status'],'pending_primary_confirmation')
        self.assertFalse(plan['request_obligation']['semantic_coverage_verified'])
        self.assertTrue(all('REQUEST-1' in task['obligations'] for task in plan['tasks']))
        changed=copy.deepcopy(plan)
        changed['tasks'][0]['obligations']=[]
        with self.assertRaises(PlatformError):
            validate_plan(changed)

    def test_request_obligation_and_declared_scope_coexist(self):
        plan=create_plan('Investigue esta diferenca',intent_contract=intent())
        security=next(t for t in plan['tasks'] if t['agent_id']=='S13')
        self.assertEqual(security['obligations'],['REQUEST-1','isolation'])
        gate=next(t for t in plan['tasks'] if t['agent_id']=='G01')
        self.assertEqual(gate['obligations'],['REQUEST-1'])


if __name__ == '__main__':
    unittest.main()
