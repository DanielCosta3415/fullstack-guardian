"""Campaign orchestration controls; no native models or candidate code run."""
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from tools import test_native_professional as n


class ProfessionalBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.selected=n.plan();cls.groups=n.batches(cls.selected)
        cls.fixture_rows=n.cases.load()
        cls.expected={r['manifest']['case_id']:r['expected'] for r in cls.fixture_rows}

    def record(self,group):
        return {'batch_id':group['batch_id'],'assigned_task_names':[x['task_name'] for x in group['selected']],
                'state':'COLLECTED','exit_code':0,'native_parent_observed':True,'quota_error_observed':False,
                'parent_session_id_sha256':hashlib.sha256(group['batch_id'].encode()).hexdigest(),
                'parent_record_sha256':hashlib.sha256(('record-'+group['batch_id']).encode()).hexdigest(),
                'source_unchanged':True,'installed_fixtures_unchanged':True,
                'rows':[dict({k:item[k] for k in ('task_name','agent_id','agent_type')},state='CORROBORATED',model='inherited-model',
                             cases=[{'case_id':c['case_id'],'objective_passed':True} for c in item['cases']]) for item in group['selected']]}

    def records(self):return [self.record(group) for group in self.groups]

    def test_partition_preserves_all39_unique_roles_and103_cases_for_every_size(self):
        for size in range(1,6):
            groups=n.batches(self.selected,size)
            self.assertEqual([x for g in groups for x in g['selected']],self.selected)
            self.assertTrue(all(1<=len(g['selected'])<=size for g in groups))
            self.assertEqual(len({g['batch_id'] for g in groups}),len(groups))
            self.assertEqual(len({x['task_name'] for g in groups for x in g['selected']}),39)
            self.assertEqual(len({c['case_id'] for g in groups for x in g['selected'] for c in x['cases']}),103)
        self.assertEqual(len(self.groups),13)
        for size in (0,6,True):
            with self.assertRaises(ValueError):n.batches(self.selected,size)
        for mutation in ('missing','duplicate-role','duplicate-case'):
            bad=copy.deepcopy(self.selected)
            if mutation=='missing':bad.pop()
            elif mutation=='duplicate-role':bad[-1]['agent_type']=bad[0]['agent_type']
            else:bad[-1]['cases'][0]['case_id']=bad[0]['cases'][0]['case_id']
            with self.assertRaises(ValueError):n.batches(bad)

    def test_small_prompts_forward_exact_group_only_and_external_host_owns_files(self):
        for group in self.groups:
            text=n.prompt(group['selected'],batch=True)
            public=json.loads(text.split('BEGIN_PUBLIC_PROFESSIONAL_TASKS\n')[1].split('\nEND_PUBLIC_PROFESSIONAL_TASKS')[0])
            self.assertEqual({x['task_name'] for x in public},{x['task_name'] for x in group['selected']})
            self.assertLessEqual(len(public),3)
            self.assertIn('ONLY IF A00 is in this batch',text)
            self.assertIn('OUTSIDE your agent persists',text)
            self.assertIn('must NOT persist artifacts',text)
            self.assertNotIn('Finish only after all39',text)
        selected=copy.deepcopy(self.groups[1]['selected']);selected[0]['oracle']='HOST_ONLY';selected[0]['cases'][0]['expected']='HOST_ONLY'
        self.assertNotIn('HOST_ONLY',n.prompt(selected,batch=True))
        self.assertNotIn('"oracle"',n.prompt(selected,batch=True))
        with self.assertRaises(ValueError):n.prompt([],batch=True)
        with self.assertRaises(ValueError):n.prompt(self.selected[:6],batch=True)
        # Existing full-inventory callers retain their contract.
        self.assertIn('at most three',n.prompt(self.selected))
        with self.assertRaises(ValueError):n.prompt(self.selected[:-1])

    def test_preview_reports_real_structural_budget_without_models(self):
        with patch.object(n.subprocess,'Popen',side_effect=AssertionError('No models permitted')),patch('sys.stdout',new_callable=io.StringIO) as output:
            self.assertEqual(n.main([]),0)
        data=json.loads(output.getvalue())
        self.assertEqual((data['native_children_expected'],data['artifact_tasks_expected'],data['parent_processes_expected']),(39,103,13))
        self.assertFalse(data['quota_consumed']);self.assertEqual(data['automatic_retries'],0)
        self.assertEqual(sum(g['case_count'] for g in data['batch_plan']),103)

    def test_complete_aggregation_requires_all_groups_exits_roles_and_cases(self):
        good=n.aggregate(self.selected,self.groups,self.records())
        self.assertTrue(good['campaign_complete'])
        self.assertEqual((good['native_children_corroborated'],good['objective_tasks_observed'],good['objective_tasks_passed']),(39,103,103))
        mutations=('missing-batch','duplicate-batch','missing-role','duplicate-role','wrong-role','wrong-case','failed-case','missing-case','duplicate-case','process-failure','bool-exit','no-parent','same-parent','source-drift','fixture-drift','quota','wrong-assignment','not-run')
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                records=self.records()
                if mutation=='missing-batch':records.pop()
                elif mutation=='duplicate-batch':records.append(copy.deepcopy(records[0]))
                elif mutation=='missing-role':records[0]['rows'].pop()
                elif mutation=='duplicate-role':records[0]['rows'][1]=copy.deepcopy(records[0]['rows'][0])
                elif mutation=='wrong-role':records[0]['rows'][0]['agent_type']='generic-impostor'
                elif mutation=='wrong-case':records[0]['rows'][0]['cases'][0]['case_id']='unknown'
                elif mutation=='failed-case':records[0]['rows'][0]['cases'][0]['objective_passed']=False
                elif mutation=='missing-case':records[0]['rows'][0]['cases'].pop()
                elif mutation=='duplicate-case':records[0]['rows'][0]['cases'][1]=copy.deepcopy(records[0]['rows'][0]['cases'][0])
                elif mutation=='process-failure':records[0]['exit_code']=1
                elif mutation=='bool-exit':records[0]['exit_code']=False
                elif mutation=='no-parent':records[0]['native_parent_observed']=False
                elif mutation=='same-parent':records[1]['parent_session_id_sha256']=records[0]['parent_session_id_sha256']
                elif mutation=='source-drift':records[0]['source_unchanged']=False
                elif mutation=='fixture-drift':records[0]['installed_fixtures_unchanged']=False
                elif mutation=='quota':records[0]['quota_error_observed']=True
                elif mutation=='wrong-assignment':records[0]['assigned_task_names'].reverse()
                elif mutation=='not-run':records[0]['state']='NOT_RUN'
                self.assertFalse(n.aggregate(self.selected,self.groups,records)['campaign_complete'])

    def execute(self,folder,side_effect,guard=lambda:(True,True)):
        with patch.object(n,'run_batch',side_effect=side_effect) as run:
            records=n.execute_batches('codex',Path(folder),Path(folder),self.groups,Path(folder),3600,guard)
        return records,run

    def test_partial_exit0_group_preserved_without_retry_and_other_groups_execute(self):
        def run(*args):
            record=self.record(args[3])
            if record['batch_id']==self.groups[0]['batch_id']:record['rows'].pop()
            return record
        with tempfile.TemporaryDirectory() as folder:records,run=self.execute(folder,run)
        self.assertEqual(run.call_count,13)
        self.assertEqual([call.args[3]['batch_id'] for call in run.call_args_list],[g['batch_id'] for g in self.groups])
        result=n.aggregate(self.selected,self.groups,records)
        self.assertFalse(result['campaign_complete']);self.assertEqual(result['native_children_corroborated'],38)

    def test_quota_stops_new_parents_and_preserves_all_planned_missing_groups(self):
        first=self.record(self.groups[0]);first['quota_error_observed']=True
        with tempfile.TemporaryDirectory() as folder:
            records,run=self.execute(folder,lambda *_:first)
            persisted=[json.loads((Path(folder)/g['batch_id']/'result.json').read_text()) for g in self.groups]
            self.assertEqual(persisted,records)
        self.assertEqual(run.call_count,1);self.assertEqual(len(records),13)
        self.assertTrue(all(r['state']=='NOT_RUN' and r['reason']=='OBSERVED_QUOTA_STOP' for r in records[1:]))
        self.assertFalse(n.aggregate(self.selected,self.groups,records)['campaign_complete'])

    def test_campaign_time_budget_and_source_guard_stop_new_processes(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(n.time,'monotonic',side_effect=[0]+[3601]*13):records,run=self.execute(folder,lambda *_:self.fail('No parent after deadline'))
            self.assertEqual(run.call_count,0)
            self.assertTrue(all(r['reason']=='CAMPAIGN_TIME_BUDGET_EXHAUSTED' for r in records))
        with tempfile.TemporaryDirectory() as folder:
            records,run=self.execute(folder,lambda *_:self.fail('No parent after source drift'),lambda:(False,True))
            self.assertEqual(run.call_count,0)
            self.assertTrue(all(r['state']=='NOT_RUN' for r in records))

    def test_guard_errors_keep_host_paths_private_and_fail_closed(self):
        sensitive='C:/private/account/fixture'
        with tempfile.TemporaryDirectory() as folder:
            def guard():raise OSError(sensitive)
            records,run=self.execute(folder,lambda *_:self.fail('No parent with unavailable guard'),guard)
            self.assertEqual(run.call_count,0)
            self.assertNotIn(sensitive,json.dumps(records))
            self.assertIn(sensitive,(Path(folder)/'guard-00-before-error.txt').read_text())

    def synthetic_sessions(self,folder,*,effort_override=False,wrong_role=False,missing_completion=False,parent_tool=False,child_tool=False):
        item=self.selected[0];name='/root/'+item['task_name'];role='impostor' if wrong_role else item['agent_type']
        args={'task_name':item['task_name'],'agent_type':item['agent_type'],'fork_turns':'none'}
        if effort_override:args['reasoning_effort']='low'
        parent=[{'type':'session_meta','payload':{'id':'parent'}},
                {'type':'turn_context','payload':{'model':'inherited-model','effort':'high'}},
                {'type':'response_item','payload':{'type':'function_call','namespace':'collaboration','name':'spawn_agent','call_id':'c','arguments':json.dumps(args)}},
                {'type':'response_item','payload':{'type':'function_call_output','call_id':'c','output':json.dumps({'task_name':name})}}]
        artifact={'case_results':[{'case_id':c['case_id'],'result':self.expected[c['case_id']]} for c in item['cases']]}
        child=[{'type':'session_meta','payload':{'id':'child','agent_role':role,'agent_path':name,'source':{'subagent':{'thread_spawn':{'parent_thread_id':'parent','agent_role':role,'agent_path':name}}}}},
               {'type':'turn_context','payload':{'model':'inherited-model','effort':'high'}},
               {'type':'response_item','payload':{'type':'message','role':'assistant','phase':'final_answer','content':[{'type':'output_text','text':json.dumps(artifact)}]}}]
        if not missing_completion:child.append({'type':'event_msg','payload':{'type':'task_complete'}})
        tool={'type':'response_item','payload':{'type':'function_call','namespace':'functions','name':'exec','arguments':'{}'}}
        if parent_tool:parent.append(tool)
        if child_tool:child.append(tool)
        for stem,rows in [('parent',parent),('child',child)]:
            (Path(folder)/(stem+'.jsonl')).write_text('\n'.join(json.dumps(r) for r in rows),encoding='utf8')
        return item

    def test_batch_collector_reuses_strict_native_identity_completion_and_inheritance(self):
        for flag in (None,'effort_override','wrong_role','missing_completion','child_tool'):
            with self.subTest(flag=flag),tempfile.TemporaryDirectory() as folder:
                item=self.synthetic_sessions(folder,**({flag:True} if flag else {}))
                observation={}
                with patch.object(n.cases,'load',return_value=self.fixture_rows):rows,_=n.collect(folder,'parent',[item],parent_observation=observation)
                self.assertEqual(rows[0]['state'],'INVALID' if flag else 'CORROBORATED')
                self.assertEqual(observation['parent_record_sha256'],n.native.sha(Path(folder)/'parent.jsonl'))
        with tempfile.TemporaryDirectory() as folder:
            item=self.synthetic_sessions(folder,parent_tool=True)
            with self.assertRaisesRegex(ValueError,'unauthorized tool'):n.collect(folder,'parent',[item])

    def test_collector_oserror_is_closed_public_code_with_private_diagnostic(self):
        sensitive='C:/private/account/session.jsonl'
        with tempfile.TemporaryDirectory() as folder:
            item=self.synthetic_sessions(folder);diagnostics=[]
            with patch.object(n.native,'inspect_child',side_effect=OSError(sensitive)):
                rows,_=n.collect(folder,'parent',[item],diagnostics=diagnostics)
        self.assertNotIn(sensitive,json.dumps(rows))
        self.assertEqual(rows[0]['reason'],'NATIVE_CHILD_VALIDATION_FAILED')
        self.assertIn(sensitive,diagnostics[0]['private_error'])

    def test_host_process_failure_keeps_private_error_and_never_exposes_path(self):
        sensitive='C:/private/identity/executable'
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(n.subprocess,'Popen',side_effect=OSError(sensitive)):
                result=n.run_batch('codex',Path(folder),Path(folder),self.groups[0],Path(folder),60)
            self.assertNotIn(sensitive,json.dumps(result))
            self.assertEqual(result['reason'],'BATCH_EXECUTION_OR_CORROBORATION_FAILED')
            self.assertIn(sensitive,(Path(folder)/self.groups[0]['batch_id']/'host-error.txt').read_text())

    def test_run_batch_persists_child_outputs_and_parent_metadata_privately(self):
        parent_id='synthetic-private-parent-identity'
        group=self.groups[0]
        fake_records=self.record(group)['rows'];artifacts={'professional_00':{'case_results':[]}}
        def spawn(*args,**kwargs):
            kwargs['stdout'].write(json.dumps({'type':'thread.started','thread_id':parent_id})+'\n')
            return Mock(wait=Mock(return_value=0))
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            with patch.object(n.subprocess,'Popen',side_effect=spawn),patch.object(n,'collect',return_value=(fake_records,artifacts)):
                result=n.run_batch('codex',path,path,group,path,60)
            private=path/group['batch_id']
            self.assertEqual(json.loads((private/'observed-artifacts.json').read_text()),artifacts)
            self.assertEqual(json.loads((private/'parent-metadata.json').read_text())['parent_session_id'],parent_id)
            self.assertNotIn(parent_id,json.dumps(result))
            self.assertEqual(result['parent_session_id_sha256'],hashlib.sha256(parent_id.encode()).hexdigest())
            self.assertEqual(result['state'],'COLLECTED')

    def test_quota_detection_accepts_real_error_shapes_not_assistant_prose(self):
        for kind in ('error','turn.failed'):
            for message in ('Usage limit reached','rate_limit_exceeded','insufficient_quota','billing_hard_limit_reached'):
                with self.subTest(kind=kind,message=message),tempfile.TemporaryDirectory() as folder:
                    path=Path(folder)/'events.jsonl'
                    path.write_text(json.dumps({'type':kind,'error':{'message':message}}),encoding='utf8')
                    self.assertTrue(n._events(path)[1])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'events.jsonl'
            path.write_text(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'No quota error was observed'}}),encoding='utf8')
            self.assertFalse(n._events(path)[1])

    def test_observed_model_and_effort_must_match_across_entire_campaign(self):
        records=self.records()
        self.assertFalse(n.aggregate(self.selected,self.groups,records)['all_parent_child_effort_observed'])
        for record in records:
            record.update(observed_parent_model='inherited-model',observed_parent_effort='high')
            for row in record['rows']:row['observed_effort']='high'
        self.assertTrue(n.aggregate(self.selected,self.groups,records)['campaign_complete'])
        for field,value in [('observed_parent_model','other-model'),('observed_parent_effort','low')]:
            changed=copy.deepcopy(records);changed[-1][field]=value
            self.assertFalse(n.aggregate(self.selected,self.groups,changed)['campaign_complete'])
        changed=copy.deepcopy(records);changed[-1]['rows'][0]['observed_effort']='low'
        self.assertFalse(n.aggregate(self.selected,self.groups,changed)['campaign_complete'])

    def test_slow_guard_cannot_start_parent_after_campaign_deadline(self):
        clock={'now':0}
        def slow_guard():clock['now']=3601;return True,True
        with tempfile.TemporaryDirectory() as folder,patch.object(n.time,'monotonic',side_effect=lambda:clock['now']):
            records,run=self.execute(folder,lambda *_:self.fail('Deadline elapsed during guard'),slow_guard)
        self.assertEqual(run.call_count,0)
        self.assertTrue(all(r['reason']=='CAMPAIGN_TIME_BUDGET_EXHAUSTED' for r in records))


if __name__=='__main__':unittest.main()

