import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools import guardian_transfer_cases as transfer
from tools import test_native_transfer as runner


class TransferCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus=transfer.corpus()
        cls.plan=runner.plan(cls.corpus)

    def observations(self):
        return [dict({k:item[k] for k in ('task_name','agent_id','agent_type','trial')},
                     state='CORROBORATED',model='inherited-model',
                     cases=[{'case_id':case['id'],'passed':True} for case in item['cases']])
                for item in self.plan]

    def test_all39_roles_have_different_semantic_variants_and_deterministic_seeds(self):
        self.assertEqual(len(self.corpus['cases']),78)
        self.assertEqual(len({c['agent_type'] for c in self.corpus['cases']}),39)
        self.assertEqual(self.corpus,transfer.corpus())
        other=transfer.corpus(seed=20261103)
        self.assertNotEqual(transfer.q.digest(self.corpus),transfer.q.digest(other))
        for role in {c['agent_type'] for c in self.corpus['cases']}:
            cases=[c for c in self.corpus['cases'] if c['agent_type']==role]
            self.assertNotEqual(cases[0]['scenario'],cases[1]['scenario'],role)
            self.assertNotEqual(cases[0]['oracle']['expected'],cases[1]['oracle']['expected'],role)

    def test_every_oracle_passes_and_a_semantically_changed_output_fails(self):
        for case in self.corpus['cases']:
            expected=case['oracle']['expected']
            self.assertTrue(transfer.grade(case,expected)['passed'])
            changed=copy.deepcopy(expected);key=next(iter(changed));value=changed[key]
            if type(value) is bool: changed[key]=not value
            elif type(value) is int: changed[key]=value+1
            elif isinstance(value,str): changed[key]=value+'-wrong'
            elif isinstance(value,list): changed[key]=value+['unexpected']
            else: self.fail('Unhandled oracle control')
            self.assertFalse(transfer.grade(case,changed)['passed'],case['id'])

    def test_cross_variant_answers_do_not_satisfy_other_variant(self):
        for role in {c['agent_type'] for c in self.corpus['cases']}:
            first,second=[c for c in self.corpus['cases'] if c['agent_type']==role]
            self.assertFalse(transfer.grade(second,first['oracle']['expected'])['passed'],role)

    def test_preview_has_no_oracles_and_trials_are_fresh_independent_children(self):
        self.assertEqual(len(self.plan),78)
        self.assertEqual(len({p['task_name'] for p in self.plan}),78)
        self.assertEqual({p['trial'] for p in self.plan},{1,2})
        text=runner.prompt(self.plan)
        self.assertNotIn('"oracle"',text)
        self.assertNotIn('"expected"',text)
        self.assertIn('fork_turns="none"',text)
        self.assertIn('Never retry failed trials',text)
        parsed=json.loads(text.split('BEGIN_PUBLIC_TRANSFER_TASKS\n')[1].split('\nEND_PUBLIC_TRANSFER_TASKS')[0])
        self.assertEqual(len(parsed),78)
        injected=copy.deepcopy(self.plan);injected[0]['oracle']='HOST_ONLY';injected[0]['cases'][0]['oracle']='HOST_ONLY'
        self.assertNotIn('HOST_ONLY',runner.prompt(injected))

    def test_result_closed_schema_unknown_duplicate_missing_and_wrong_types_fail(self):
        item=self.plan[0];lookup={c['id']:c for c in self.corpus['cases']}
        artifact={'case_results':[{'case_id':c['id'],'result':lookup[c['id']]['oracle']['expected']} for c in item['cases']]}
        self.assertTrue(all(r['passed'] for r in runner.grade_child(item,artifact,lookup)))
        wrong=copy.deepcopy(artifact);wrong['case_results'][0]['case_id']='unknown'
        with self.assertRaises(ValueError): runner.grade_child(item,wrong,lookup)
        duplicate=copy.deepcopy(artifact);duplicate['case_results'][1]=duplicate['case_results'][0]
        with self.assertRaises(ValueError): runner.grade_child(item,duplicate,lookup)
        with self.assertRaises(ValueError): runner.grade_child(item,{'case_results':[]},lookup)
        with self.assertRaises(ValueError): runner.grade_child(item,dict(artifact,approved=True),lookup)
        integer=next(c for c in self.corpus['cases'] if any(type(v) is int for v in c['oracle']['expected'].values()))
        changed=copy.deepcopy(integer['oracle']['expected']);key=next(k for k,v in changed.items() if type(v) is int);changed[key]=True
        self.assertFalse(transfer.grade(integer,changed)['passed'])

    def test_failure_missing_duplicate_unknown_or_model_drift_never_passes(self):
        rows=self.observations();good=runner.assess(rows,self.plan)
        self.assertTrue(good['all_planned_observations_passed'])
        self.assertEqual((good['expected_judgments'],good['passed_judgments']),(156,156))
        failed=copy.deepcopy(rows);failed[0]['cases'][0]['passed']=False
        result=runner.assess(failed,self.plan)
        self.assertFalse(result['all_planned_observations_passed'])
        self.assertEqual(result['failed_or_missing_judgments'],1)
        self.assertFalse(runner.assess(rows[:-1],self.plan)['all_planned_observations_passed'])
        self.assertFalse(runner.assess(rows+[rows[0]],self.plan)['all_planned_observations_passed'])
        self.assertFalse(runner.assess(rows+[{'state':'UNEXPECTED_CHILD'}],self.plan)['all_planned_observations_passed'])
        drift=copy.deepcopy(rows);drift[-1]['model']='different-model'
        self.assertFalse(runner.assess(drift,self.plan)['all_planned_observations_passed'])

    def test_metrics_preserve_unknowns_and_small_sample_uncertainty(self):
        result=runner.assess(self.observations()[:-1],self.plan)
        self.assertEqual(len(result['per_role']),39)
        self.assertEqual(result['cost'],{'kind':'unknown','amount':None})
        perfect=runner.wilson(0,4)
        self.assertGreater(perfect[1],0.45)
        self.assertIsNone(runner.wilson(0,0))
        role=result['per_role'][self.plan[-1]['agent_type']]
        self.assertEqual(role['missing_judgments'],2)
        self.assertEqual(role['failed_observed_judgments'],0)

    def test_seed_repetition_bounds_reject_unbounded_or_bool_requests(self):
        for seed in (-1,True,2**31):
            with self.assertRaises(ValueError): transfer.corpus(seed)
        for variants in (1,5,True):
            with self.assertRaises(ValueError): transfer.corpus(variants=variants)
        for repetitions in (1,6,True):
            with self.assertRaises(ValueError): runner.plan(self.corpus,repetitions)

    def test_malformed_result_cannot_be_accepted_by_omitting_or_duplicating_checks(self):
        rows=self.observations()
        missing=copy.deepcopy(rows);missing[0]['cases']=missing[0]['cases'][:1]
        self.assertFalse(runner.assess(missing,self.plan)['all_planned_observations_passed'])
        duplicate=copy.deepcopy(rows);duplicate[0]['cases'][1]=duplicate[0]['cases'][0]
        self.assertFalse(runner.assess(duplicate,self.plan)['all_planned_observations_passed'])
        wrong_role=copy.deepcopy(rows);wrong_role[0]['agent_type']='impostor'
        self.assertFalse(runner.assess(wrong_role,self.plan)['all_planned_observations_passed'])

    def synthetic_sessions(self, folder, *, effort_override=False, parent_tool=False, child_tool=False, wrong_role=False, effort_drift=False, parent_model_mismatch=False, parent_effort_mismatch=False):
        item=self.plan[0];path='/root/'+item['task_name']
        args={'task_name':item['task_name'],'agent_type':item['agent_type'],'fork_turns':'none'}
        if effort_override: args['reasoning_effort']='low'
        parent=[{'type':'session_meta','payload':{'id':'parent'}},
                {'type':'turn_context','payload':{'model':'different-parent-model' if parent_model_mismatch else 'inherited-model','effort':'low' if parent_effort_mismatch else 'high'}},
                {'type':'response_item','payload':{'type':'function_call','namespace':'collaboration','name':'spawn_agent','call_id':'call-1','arguments':json.dumps(args)}},
                {'type':'response_item','payload':{'type':'function_call_output','call_id':'call-1','output':json.dumps({'task_name':path})}}]
        if parent_tool: parent.append({'type':'response_item','payload':{'type':'function_call','namespace':'functions','name':'exec','arguments':'{}'}})
        lookup={c['id']:c for c in self.corpus['cases']}
        artifact={'case_results':[{'case_id':c['id'],'result':lookup[c['id']]['oracle']['expected']} for c in item['cases']]}
        role='generic-impostor' if wrong_role else item['agent_type']
        child=[{'type':'session_meta','payload':{'id':'child','agent_path':path,'agent_role':role,'source':{'subagent':{'thread_spawn':{'parent_thread_id':'parent','agent_path':path,'agent_role':role}}}}},
               {'type':'turn_context','payload':{'model':'inherited-model','effort':'high'}},
               {'type':'response_item','payload':{'type':'message','role':'assistant','phase':'final_answer','content':[{'type':'output_text','text':json.dumps(artifact)}]}},
               {'type':'event_msg','payload':{'type':'task_complete'}}]
        if effort_drift: child.append({'type':'turn_context','payload':{'model':'inherited-model','effort':'low'}})
        if child_tool: child.append({'type':'response_item','payload':{'type':'function_call','namespace':'functions','name':'exec','arguments':'{}'}})
        for name,rows in [('parent',parent),('child',child)]:
            (Path(folder)/(name+'.jsonl')).write_text('\n'.join(json.dumps(r) for r in rows)+'\n',encoding='utf8')
        return item

    def test_collect_corroborates_native_parent_role_completion_and_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            item=self.synthetic_sessions(tmp)
            rows,artifacts=runner.collect(tmp,'parent',[item],self.corpus)
        self.assertEqual(rows[0]['state'],'CORROBORATED')
        self.assertEqual(rows[0]['observed_effort'],'high')
        self.assertTrue(all(c['passed'] for c in rows[0]['cases']))
        self.assertEqual(set(artifacts),{item['task_name']})

    def test_collect_rejects_actual_effort_override_tools_impostor_and_effort_drift(self):
        for flag in ('effort_override','child_tool','wrong_role','effort_drift','parent_model_mismatch','parent_effort_mismatch'):
            with self.subTest(flag=flag),tempfile.TemporaryDirectory() as tmp:
                item=self.synthetic_sessions(tmp,**{flag:True})
                rows,_=runner.collect(tmp,'parent',[item],self.corpus)
                self.assertEqual(rows[0]['state'],'INVALID')
        with tempfile.TemporaryDirectory() as tmp:
            item=self.synthetic_sessions(tmp,parent_tool=True)
            with self.assertRaises(ValueError): runner.collect(tmp,'parent',[item],self.corpus)

    def test_cross_trial_effort_drift_blocks_success_and_missing_effort_stays_unknown(self):
        rows=self.observations()
        self.assertFalse(runner.assess(rows,self.plan)['all_role_effort_observed'])
        for row in rows: row['observed_effort']='high'
        self.assertTrue(runner.assess(rows,self.plan)['all_role_effort_observed'])
        rows[-1]['observed_effort']='low'
        result=runner.assess(rows,self.plan)
        self.assertTrue(result['observed_effort_drift'])
        self.assertFalse(result['all_planned_observations_passed'])


if __name__=='__main__': unittest.main()
