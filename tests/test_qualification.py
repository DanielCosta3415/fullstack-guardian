import copy
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from tools import guardian_qualification as q
from tools.native_check_evidence import fixture_passed,paired_outcomes

class QualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus=q.load_json(q.ROOT/'core/qualification-cases-v1.json')

    def setup_observation(self):
        corpus=copy.deepcopy(self.corpus)
        case=next(c for c in corpus['cases'] if c['oracle']['kind']=='structured_exact')
        bindings={k:'a'*64 for k in q.BINDINGS}
        bindings.update(revision='b'*40,model='model-snapshot',corpus_sha256=q.digest(corpus))
        artifact=copy.deepcopy(case['oracle']['expected'])
        obs={'case_id':case['id'],'agent_id':case['agent_id'],'agent_type':case['agent_type'],
             'run_id':'run-1','bindings':bindings.copy(),'artifact':artifact,'artifact_sha256':q.digest(artifact),
             'captured_at':'2026-10-20T00:00:00Z','valid_until':'2026-10-21T00:00:00Z',
             'unsafe_outcome_observed':False,'cost_usd':0.01}
        context={'profiles':{case['agent_id']:bindings},'minimum_repetitions':2}
        return corpus,obs,context

    def evaluate(self,corpus,obs,context):
        return q.evaluate(corpus,obs,context,trust_observations=True,now=dt.datetime(2026,10,20,1,tzinfo=dt.timezone.utc))

    def test_all_39_have_vocational_and_typed_cases(self):
        result=q.validate(self.corpus)
        self.assertEqual((result['case_count'],result['agent_count']),(142,39))
        ids={c['agent_id'] for c in self.corpus['cases']}
        for aid in ids:
            cases=[c for c in self.corpus['cases'] if c['agent_id']==aid]
            self.assertGreaterEqual(sum(c['oracle']['kind']=='independent_sme' for c in cases),2)
            self.assertEqual(sum(c['oracle']['kind']=='structured_exact' for c in cases),1)
            self.assertTrue(all(c['execution_status']=='NOT_EXECUTED' for c in cases))

    def test_every_vocation_rejects_check_ok_and_every_open_case_requires_sme(self):
        now=dt.datetime(2026,10,20,1,tzinfo=dt.timezone.utc)
        profiles={};observations=[]
        for case in self.corpus['cases']:
            binding={k:'a'*64 for k in q.BINDINGS}
            binding.update(revision='b'*40,model='fixture-only',corpus_sha256=q.digest(self.corpus))
            profiles[case['agent_id']]=binding
            artifact={'check':'OK','sme_approved':True}
            observations.append({'case_id':case['id'],'agent_id':case['agent_id'],'agent_type':case['agent_type'],
                'run_id':'fixture-'+case['id'],'bindings':binding,'artifact':artifact,'artifact_sha256':q.digest(artifact),
                'captured_at':'2026-10-20T00:00:00Z','valid_until':'2026-10-21T00:00:00Z','unsafe_outcome_observed':False})
        report=q.evaluate(self.corpus,observations,{'profiles':profiles},trust_observations=True,now=now)
        self.assertEqual(sum(row['state']=='FAIL' for row in report['rows']),39)
        self.assertEqual(sum(row['state']=='REQUIRES_SME' for row in report['rows']),103)
        self.assertEqual(report['cases_observed_repeated_pass'],0)
        self.assertFalse(report['cost_complete'])

    def test_boolean_integer_type_confusion_does_not_pass(self):
        corpus,obs,context=self.setup_observation()
        key=next(k for k,v in obs['artifact'].items() if type(v) is bool)
        obs['artifact'][key]=int(obs['artifact'][key]);obs['artifact_sha256']=q.digest(obs['artifact'])
        self.assertEqual(self.evaluate(corpus,[obs],context)['rows'][0]['state'],'FAIL')

    def test_preview_does_not_expose_oracle_but_cannot_claim_holdout(self):
        self.assertTrue(all('oracle' not in c for c in q.preview(self.corpus)))
        altered=copy.deepcopy(self.corpus);altered['cases'][0]['split']='holdout'
        with self.assertRaisesRegex(ValueError,'Public corpus'):q.validate(altered)

    def test_json_check_ok_does_not_pass_wrong_domain_answer(self):
        corpus,obs,context=self.setup_observation()
        obs['artifact']={'check':'OK','integrate':True};obs['artifact_sha256']=q.digest(obs['artifact'])
        self.assertEqual(self.evaluate(corpus,[obs],context)['rows'][0]['state'],'FAIL')

    def test_exact_typed_artifact_repetitions_do_not_certify_provenance(self):
        corpus,obs,context=self.setup_observation();other=copy.deepcopy(obs);other['run_id']='run-2'
        report=self.evaluate(corpus,[obs,other],context)
        self.assertEqual(report['cases_observed_repeated_pass'],1)
        self.assertEqual(report['qualification'],'OBSERVED_NOT_CERTIFIED')
        self.assertFalse(report['provenance_authenticated']);self.assertFalse(report['private_holdout_validated'])
        self.assertEqual(report['cost_usd_reported'],0.02)

    def test_duplicate_run_cannot_inflate_repetitions(self):
        corpus,obs,context=self.setup_observation();report=self.evaluate(corpus,[obs,obs],context)
        self.assertEqual(report['rows'][1]['state'],'INVALID');self.assertEqual(report['cases_observed_repeated_pass'],0)

    def test_forged_profile_and_artifact_rejected(self):
        for field,value in [('agent_type','guardian_fake'),('artifact_sha256','0'*64)]:
            corpus,obs,context=self.setup_observation();obs[field]=value
            self.assertEqual(self.evaluate(corpus,[obs],context)['rows'][0]['state'],'INVALID')

    def test_all_revision_binding_changes_stale(self):
        for field in q.BINDINGS:
            corpus,obs,context=self.setup_observation();obs['bindings'][field]='changed'
            self.assertEqual(self.evaluate(corpus,[obs],context)['rows'][0]['state'],'STALE',field)

    def test_oracle_mutation_rejected_by_expected_corpus_digest(self):
        corpus,obs,context=self.setup_observation()
        case=next(c for c in corpus['cases'] if c['id']==obs['case_id'])
        case['oracle']['expected']={'integrate':True}
        obs['artifact']={'integrate':True};obs['artifact_sha256']=q.digest(obs['artifact'])
        self.assertEqual(self.evaluate(corpus,[obs],context)['rows'][0]['state'],'STALE')

    def test_open_artifact_cannot_self_approve_sme(self):
        corpus,obs,context=self.setup_observation();case=corpus['cases'][0]
        obs.update(case_id=case['id'],agent_id=case['agent_id'],agent_type=case['agent_type'],sme_approved=True)
        # First profile owns both cases, so binding is intentionally unchanged.
        self.assertEqual(self.evaluate(corpus,[obs],context)['rows'][0]['state'],'REQUIRES_SME')

    def test_expiry_future_and_excessive_validity_rejected(self):
        for key,value in [('valid_until','2026-10-19T00:00:00Z'),('captured_at','2026-10-21T00:00:00Z'),('valid_until','2027-10-20T00:00:00Z')]:
            corpus,obs,context=self.setup_observation();obs[key]=value
            self.assertEqual(self.evaluate(corpus,[obs],context)['rows'][0]['state'],'STALE')

    def test_abstention_and_missing_safety_observation_not_coverage(self):
        corpus,obs,context=self.setup_observation();obs['abstained']=True
        self.assertEqual(self.evaluate(corpus,[obs],context)['rows'][0]['state'],'ABSTAINED')
        obs.pop('abstained');obs.pop('unsafe_outcome_observed')
        self.assertEqual(self.evaluate(corpus,[obs],context)['rows'][0]['state'],'BLOCKED')

    def test_explicit_trust_and_two_repetitions_required(self):
        corpus,obs,context=self.setup_observation()
        with self.assertRaises(ValueError):q.evaluate(corpus,[obs],context)
        context['minimum_repetitions']=1
        with self.assertRaises(ValueError):self.evaluate(corpus,[obs],context)

    def test_duplicate_json_keys_non_finite_and_symlink_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'case.json'
            for content in ['{"a":1,"a":2}','{"a":NaN}']:
                path.write_text(content)
                with self.assertRaises(ValueError):q.load_json(path)
            link=Path(directory)/'link.json'
            try:link.symlink_to(path)
            except OSError:pass
            else:
                with self.assertRaises(ValueError):q.load_json(link)

    def test_native_incidental_exit_one_never_matches_seeded_invariant(self):
        rule={'schema_version':2,'build':False,'seeded_failure':True,'expected_assertions':['Bob accessed Alice invoice']}
        for error in ['NameError: Bob accessed Alice invoice','ImportError: cannot import auth','AssertionError: unrelated']:
            self.assertFalse(fixture_passed([{'exit_code':1,'output':error}],rule))
        self.assertFalse(fixture_passed([1],rule))
        self.assertTrue(fixture_passed([{'exit_code':1,'output':'Traceback...\nAssertionError: Bob accessed Alice invoice\n'}],rule))
        self.assertFalse(fixture_passed([{'exit_code':1,'output':'AssertionError: Bob accessed Alice invoice\nNameError: incidental'}],rule))

    def test_native_build_requires_expected_first_failure_and_final_success(self):
        rule={'schema_version':2,'build':True,'seeded_failure':True,'expected_assertions':['Negative amount accepted']}
        good={'exit_code':1,'output':'AssertionError: Negative amount accepted'}
        ok={'exit_code':0,'output':'passed'}
        self.assertTrue(fixture_passed([good,ok],rule))
        self.assertFalse(fixture_passed([dict(good,output='NameError: missing'),ok],rule))
        self.assertFalse(fixture_passed([ok,good,ok],rule))

    def test_native_detailed_evidence_keeps_command_cwd_and_call_id_binding(self):
        case={'case_directory':'/fixtures/S14'}
        call={'type':'function_call','name':'exec_command','call_id':'c1','arguments':json.dumps({'cmd':'python -B check.py','workdir':'/fixtures/S14'})}
        result={'type':'function_call_output','call_id':'c1','output':json.dumps({'exit_code':1,'output':'AssertionError: Bob accessed Alice invoice'})}
        self.assertEqual(paired_outcomes([call,result],case,details=True)[0]['call_id'],'c1')
        self.assertEqual(paired_outcomes([call,dict(result,call_id='c2')],case,details=True),[])
        self.assertEqual(paired_outcomes([call,result],{'case_directory':'/fixtures/S13'},details=True),[])
        self.assertEqual(paired_outcomes([call,result,result],case,details=True),[])

if __name__=='__main__':unittest.main()
