"""Release policy boundary tests; remote answers/transcripts are unit fixtures.

No network, native Codex execution, publication or installation is performed.
"""
import copy
import contextlib
import hashlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import guardian_local_acceptance as local
from tools import guardian_release_gate as gate

REV='a'*40


class PolicyMatrixTests(unittest.TestCase):
    def test_receipts_share_closed_requirements_for_both_policies(self):
        for policy in ('strict','operator-autonomous'):
            receipt=gate.policy_receipt(policy)
            rows={r['id']:r for r in receipt['requirements']}
            self.assertEqual(set(rows),set(gate._POLICY_BASELINES))
            self.assertFalse(receipt['verifier_policy_checks_passed'])
            self.assertFalse(receipt['complete_release_acceptance_passed'])
            self.assertEqual(rows['independent_G01_G02']['status'],'not_verified')
            self.assertTrue(rows['independent_G01_G02']['required'])
            self.assertEqual(rows['remote_asset_install_and_recovery']['status'],'manual')
            self.assertFalse(rows['remote_asset_install_and_recovery']['verified'])
            self.assertEqual(rows['independent_human_pr_review']['required'],policy=='strict')

    def test_inspect_and_receipts_share_closed_requirements_for_both_policies(self):
        # Distribution manifests are intentionally absent from installed runtime
        # layouts. Only source-package identity inspection is source-specific;
        # the policy matrix and fail-closed receipt tests above run everywhere.
        if not (gate.ROOT/'plugin.json').is_file():
            self.skipTest('Source-package manifest inspection only')
        for policy in ('strict','operator-autonomous'):
            report=gate.inspect(policy=policy)
            self.assertEqual(report['requirement_receipt'],gate.policy_receipt(policy))
            rows=report['requirement_receipt']['requirements']
            self.assertEqual(set(report['requirements']),{r['id'] for r in rows if r['required']})

    def test_matrix_omission_duplicate_unknown_and_downgrade_rejected(self):
        matrix=gate.policy_matrix()
        malformed=[]
        rowless=copy.deepcopy(matrix);rowless['requirements'].pop();malformed.append(rowless)
        duplicate=copy.deepcopy(matrix);duplicate['requirements'].append(duplicate['requirements'][0]);malformed.append(duplicate)
        downgrade=copy.deepcopy(matrix);downgrade['requirements'][5]['strict']='not_applicable';malformed.append(downgrade)
        unknown=copy.deepcopy(matrix);unknown['requirements'][0]['id']='looks_safe';malformed.append(unknown)
        boolean=copy.deepcopy(matrix);boolean['schema_version']=True;malformed.append(boolean)
        extra=copy.deepcopy(matrix);extra['approved']=True;malformed.append(extra)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();(root/'core').mkdir()
            path=root/'core/release-policy-matrix-v1.json'
            for data in malformed:
                path.write_text(json.dumps(data),encoding='utf8')
                with self.subTest(data=data),self.assertRaises(ValueError):gate.policy_matrix(root)
            path.write_text('{"schema_version":1,"schema_version":1}',encoding='utf8')
            with self.assertRaisesRegex(ValueError,'Duplicate'):gate.policy_matrix(root)

    def test_no_manual_or_excluded_check_can_be_fabricated_as_verified(self):
        for policy,item in [('strict','remote_asset_install_and_recovery'),
                            ('strict','operator_release_decision'),
                            ('operator-autonomous','independent_human_pr_review')]:
            with self.subTest(item=item),self.assertRaises(ValueError):
                gate.policy_receipt(policy,{item:{'model_claim':'approved'}})
        for observed in ({'unknown':{'ok':True}},{'signed_build_provenance':{}},[]):
            with self.subTest(observed=observed),self.assertRaises(ValueError):gate.policy_receipt('strict',observed)
        with self.assertRaisesRegex(ValueError,'Unknown release policy'):gate.policy_receipt('automatic-fallback')

    def test_incomplete_strict_receipt_cannot_exit_zero_at_cli(self):
        report={'external_checks_passed':True,'policy_acceptance_passed':False,
                'publication_authorized':False,'requirement_receipt':gate.policy_receipt('strict')}
        output=io.StringIO();errors=io.StringIO()
        with patch.object(gate,'verify_external',return_value=report) as verify,\
             contextlib.redirect_stdout(output),contextlib.redirect_stderr(errors):
            with self.assertRaises(SystemExit) as result:gate.main(['--verify-external'])
        self.assertEqual(result.exception.code,2)
        self.assertFalse(json.loads(output.getvalue())['policy_acceptance_passed'])
        self.assertIn('NOT VERIFIED',errors.getvalue())
        self.assertEqual(verify.call_args.kwargs['policy'],'strict')


class StrictReviewConsumptionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        self.artifact=self.root/'fixture.zip';self.artifact.write_bytes(b'unit fixture, never published')
        self.digest=hashlib.sha256(self.artifact.read_bytes()).hexdigest()
        self.acceptance={'revision':REV,'expected':39,'verified':39,'all_native_roles_verified':True,
                         'protected_fixtures_unchanged':True,'passed':True,'tests':23,
                         'skipped':0,'failures':0,'errors':0}

    def reviews(self):
        paths=[]
        for name,role in [('G01','guardian_independent_auditor'),('G02','guardian_release_auditor')]:
            session=self.root/(name+'.jsonl')
            report={'gate':name,'revision':REV,'artifact_sha256':self.digest,'kind':'AI_ADVISORY',
                    'decision':'ACCEPTED_WITH_LIMITATIONS','findings_unresolved':0,
                    'limitations':['Synthetic unit data, not a real native review'],
                    'implementation_session':'implementer','session_record':str(session)}
            final=(REV+' '+self.digest+' ACCEPTED_WITH_LIMITATIONS\nGUARDIAN_RELEASE_REVIEW '+local.review_claim_digest(report))
            records=[{'type':'session_meta','payload':{'id':name,'agent_role':role,
                       'source':{'subagent':{'thread_spawn':{'parent_thread_id':'implementer'}}}}},
                     {'type':'response_item','payload':{'type':'message','role':'assistant','phase':'final_answer',
                       'content':[{'text':final}]}},
                     {'type':'event_msg','payload':{'type':'task_complete'}}]
            session.write_text('\n'.join(json.dumps(r) for r in records)+'\n',encoding='utf8')
            report['session_sha256']=hashlib.sha256(session.read_bytes()).hexdigest()
            path=self.root/(name+'.json');path.write_text(json.dumps(report),encoding='utf8');paths.append(path)
        return paths

    def api(self,path):
        if '/reviews?' in path:
            return [{'commit_id':REV,'author_association':'MEMBER','user':{'type':'User','login':'human'},'state':'APPROVED'}]
        if '/pulls/' in path:return {'head':{'sha':REV},'draft':False,'user':{'login':'implementer'}}
        if '/jobs?' in path:return {'jobs':[{'conclusion':'success'}]*9}
        workflow={1:'ci',2:'native-acceptance',3:'grader-acceptance'}[int(path.rsplit('/',1)[1])]
        return {'head_sha':REV,'status':'completed','conclusion':'success','path':'.github/workflows/'+workflow+'.yml'}

    def verify(self,reviews=()):
        with patch.object(gate,'_api',side_effect=self.api),\
             patch.object(gate,'_acceptance_artifact',return_value=self.acceptance),\
             patch.object(gate.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'[{"unit_mock":true}]','')):
            return gate.verify_external('owner/repo',REV,self.artifact,1,2,3,4,advisory_reviews=reviews)

    def test_human_and_remote_success_cannot_silently_replace_specialist_reviews(self):
        result=self.verify()
        self.assertTrue(result['external_checks_passed'])
        self.assertTrue(result['human_review_recorded_by_github'])
        self.assertTrue(result['remote_native_test_performed'])
        self.assertFalse(result['policy_acceptance_passed'])
        self.assertEqual(result['requirement_receipt']['pending_verifier_checks'],['independent_G01_G02'])
        self.assertFalse(result['publication_authorized'])

    def test_strict_verifies_actual_pinned_advisory_records_and_retains_manual_unknowns(self):
        result=self.verify(self.reviews())
        self.assertTrue(result['policy_acceptance_passed'])
        self.assertFalse(result['complete_release_acceptance_passed'])
        receipt=result['requirement_receipt']
        rows={r['id']:r for r in receipt['requirements']}
        self.assertEqual(rows['independent_G01_G02']['status'],'verified_local')
        self.assertEqual(rows['independent_human_pr_review']['status'],'verified_external')
        self.assertEqual(result['advisory_reviews']['gates'],['G01','G02'])
        self.assertEqual(receipt['pending_verifier_checks'],[])
        self.assertEqual(set(receipt['pending_required']),{'local_native_preliminary_smoke','remote_asset_install_and_recovery','operator_release_decision'})

    def test_strict_refuses_partial_duplicate_stale_or_wrong_digest_review(self):
        paths=self.reviews()
        for records in ([paths[0]],paths[:1]*2):
            with self.subTest(records=records),self.assertRaises(ValueError):self.verify(records)
        original=json.loads(paths[0].read_text())
        for key,value in [('revision','b'*40),('artifact_sha256','b'*64),('gate','G02'),
                          ('implementation_session','G01'),('session_sha256','0'*64),('findings_unresolved',1)]:
            report=dict(original);report[key]=value;paths[0].write_text(json.dumps(report),encoding='utf8')
            with self.subTest(key=key),self.assertRaises(ValueError):self.verify(paths)
        paths[0].write_text(json.dumps(original),encoding='utf8')
        self.assertTrue(self.verify(paths)['policy_acceptance_passed'])


if __name__=='__main__':unittest.main()
