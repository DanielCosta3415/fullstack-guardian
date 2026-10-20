import copy
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest

from tools import guardian_qualification as q
from tools import test_native_qualification as n


class NativeQualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus=q.load_json(n.ROOT/'core/qualification-cases-v1.json')
        cls.plan=n.plan(cls.corpus)

    def rows(self,artifact=None):
        item=self.plan[0]
        meta={'id':'child-1','agent_role':item['agent_type'],'agent_path':'/root/'+item['task_name'],
              'source':{'subagent':{'thread_spawn':{'parent_thread_id':'parent','agent_role':item['agent_type'],'agent_path':'/root/'+item['task_name']}}}}
        artifact=artifact if artifact is not None else next(c['oracle']['expected'] for c in self.corpus['cases'] if c['id']==item['case_id'])
        return [{'type':'session_meta','payload':meta},
                {'type':'turn_context','payload':{'model':'actual-model'}},
                {'type':'response_item','payload':{'type':'message','role':'assistant','phase':'final_answer','content':[{'type':'output_text','text':json.dumps(artifact)}]}},
                {'type':'event_msg','payload':{'type':'task_complete'}}]

    def inspect(self,rows,pairs=None):
        return n.inspect_child(rows,self.plan[0],'parent',pairs if pairs is not None else {('/root/'+self.plan[0]['task_name'],self.plan[0]['agent_type'])})

    def test_preview_has_78_unique_trials_39_roles_no_oracle_answers(self):
        self.assertEqual(len(self.plan),78)
        self.assertEqual(len({p['task_name'] for p in self.plan}),78)
        self.assertEqual(len({p['agent_type'] for p in self.plan}),39)
        for p in self.plan:
            self.assertNotIn('oracle',p)
            self.assertNotIn('expected',p)
            self.assertEqual(p['schema']['type'],'object')
            self.assertFalse(p['schema']['additionalProperties'])
        self.assertEqual(sum(c['oracle']['kind']=='independent_sme' for c in self.corpus['cases']),103)

    def test_schema_has_fields_and_non_answer_enum_alternatives(self):
        for case in self.corpus['cases']:
            if case['oracle']['kind']!='structured_exact':continue
            schema=case['artifacts']['schema']
            self.assertEqual(set(schema['required']),set(case['oracle']['expected']))
            self.assertEqual(set(schema['properties']),set(case['oracle']['expected']))
            for key,value in case['oracle']['expected'].items():
                field=schema['properties'][key]
                self.assertNotIn('const',field)
                self.assertNotIn('default',field)
                if 'enum' in field:
                    self.assertIn(value,field['enum'])
                    self.assertGreaterEqual(len(field['enum']),2)

    def test_native_child_metadata_and_json_accept(self):
        child=self.inspect(self.rows())
        self.assertEqual(child['session_id'],'child-1')
        self.assertEqual(child['model'],'actual-model')

    def test_wrong_role_parent_or_trial_rejected(self):
        for mutate in ('role','parent','trial'):
            rows=self.rows();m=rows[0]['payload'];s=m['source']['subagent']['thread_spawn']
            if mutate=='role':m['agent_role']='default'
            elif mutate=='parent':s['parent_thread_id']='forged-parent'
            else:s['agent_path']='/root/forged_trial'
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):self.inspect(rows)

    def test_missing_completion_pair_and_model_or_tools_rejected(self):
        with self.assertRaises(ValueError):self.inspect(self.rows(),set())
        with self.assertRaises(ValueError):self.inspect(self.rows()[:-1])
        rows=self.rows();rows[1]['payload'].clear()
        with self.assertRaises(ValueError):self.inspect(rows)
        rows=self.rows()+[{'type':'response_item','payload':{'type':'function_call','name':'exec_command'}}]
        with self.assertRaises(ValueError):self.inspect(rows)

    def test_nonjson_duplicate_keys_and_nonfinite_rejected(self):
        for text in ('```json\n{}\n```','{"a":1,"a":2}','{"a":NaN}','[]'):
            rows=self.rows();rows[2]['payload']['content'][0]['text']=text
            with self.subTest(text=text),self.assertRaises(ValueError):self.inspect(rows)

    def test_parent_pairs_require_matching_call_and_output(self):
        case=self.plan[0]
        rows=[{'type':'response_item','payload':{'type':'function_call','namespace':'collaboration','name':'spawn_agent','call_id':'c1','arguments':json.dumps({'task_name':case['task_name'],'agent_type':case['agent_type'],'fork_turns':'none'})}},
              {'type':'response_item','payload':{'type':'function_call_output','call_id':'c1','output':json.dumps({'task_name':'/root/'+case['task_name']})}}]
        self.assertEqual(n.parent_pairs(rows),[('/root/'+case['task_name'],case['agent_type'])])
        rows[1]['payload']['call_id']='c2'
        self.assertEqual(n.parent_pairs(rows),[])

    def test_two_trials_wrong_answer_and_stale_binding(self):
        corpus=copy.deepcopy(self.corpus);case=next(c for c in corpus['cases'] if c['oracle']['kind']=='structured_exact')
        now=dt.datetime.now(dt.timezone.utc)
        binding={k:'a'*64 for k in q.BINDINGS};binding.update(revision='b'*40,model='actual',corpus_sha256=q.digest(corpus))
        def observation(run,artifact):
            return {'case_id':case['id'],'agent_id':case['agent_id'],'agent_type':case['agent_type'],'run_id':run,'bindings':binding.copy(),
                    'artifact':artifact,'artifact_sha256':q.digest(artifact),'captured_at':now.isoformat(),'valid_until':(now+dt.timedelta(days=1)).isoformat(),'unsafe_outcome_observed':False}
        one=observation('trial1',case['oracle']['expected']);two=observation('trial2',case['oracle']['expected'])
        context={'profiles':{case['agent_id']:binding},'minimum_repetitions':2}
        def evaluate(obs):return q.evaluate(corpus,obs,context,trust_observations=True,now=now)
        self.assertEqual(evaluate([one,two])['cases_observed_repeated_pass'],1)
        self.assertEqual(evaluate([one,one])['cases_observed_repeated_pass'],0)
        bad=observation('trial2',{'integrate':True})
        self.assertEqual(evaluate([one,bad])['rows'][1]['state'],'FAIL')
        two['bindings']['revision']='c'*40
        self.assertEqual(evaluate([one,two])['rows'][1]['state'],'STALE')

    def test_session_bound_rejects_symlink_and_malformed_json(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'bad.jsonl';p.write_text('not json',encoding='utf8')
            with self.assertRaises(ValueError):n.read_session(p)

    def test_collect_requires_unique_paired_sessions_per_trial(self):
        case=self.plan[0]
        binding={k:'a'*64 for k in q.BINDINGS};binding.update(revision='b'*40,model='PENDING',corpus_sha256=q.digest(self.corpus))
        parent=[{'type':'session_meta','payload':{'id':'parent'}},
            {'type':'response_item','payload':{'type':'function_call','namespace':'collaboration','name':'spawn_agent','call_id':'c1','arguments':json.dumps({'task_name':case['task_name'],'agent_type':case['agent_type'],'fork_turns':'none'})}},
            {'type':'response_item','payload':{'type':'function_call_output','call_id':'c1','output':json.dumps({'task_name':'/root/'+case['task_name']})}}]
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            def write(name,rows): (root/name).write_text('\n'.join(json.dumps(r) for r in rows)+'\n',encoding='utf8')
            write('parent.jsonl',parent);write('child.jsonl',self.rows())
            public,obs,context,result=n.collect(root,'parent',[case],self.corpus,{case['agent_id']:binding})
            self.assertEqual(public[0]['state'],'OBSERVED')
            self.assertEqual(result['cases_observed_repeated_pass'],0)
            self.assertEqual(context['profiles'][case['agent_id']]['model'],'actual-model')
            duplicate=self.rows();duplicate[0]['payload']['id']='child-2';write('duplicate.jsonl',duplicate)
            public,obs,_,_=n.collect(root,'parent',[case],self.corpus,{case['agent_id']:binding})
            self.assertEqual(public[0]['state'],'INVALID')
            self.assertIn('duplicate',public[0]['reason'])
            self.assertEqual(obs,[])


if __name__=='__main__':unittest.main()
