"""Adversarial consistency checks; fixture transcripts are synthetic unit data."""
import copy
import contextlib
import hashlib
import json
import subprocess
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import guardian_local_acceptance as local
from tools import guardian_release_gate as gate

REV='a'*40
DIGEST='b'*64


def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data),encoding='utf8')


def write_session(path,identity,role,parent,payloads):
    rows=[{'type':'session_meta','payload':{'id':identity,'agent_role':role,
           'source':{'subagent':{'thread_spawn':{'parent_thread_id':parent}}}}}]
    rows += [{'type':'response_item','payload':p} for p in payloads]
    rows.append({'type':'event_msg','payload':{'type':'task_complete'}})
    path.write_text('\n'.join(json.dumps(r) for r in rows)+'\n',encoding='utf8')


def final(text='Completed controlled synthetic check'):
    return {'type':'message','role':'assistant','phase':'final_answer','content':[{'text':text}]}


class AutonomousLocalAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        self.roles={f'role{i}' for i in range(39)}
        self.sessions=[];cases=[];rules=[];protected={}
        for i,role in enumerate(sorted(self.roles)):
            case=self.root/'project'/str(i);case.mkdir(parents=True)
            check=case/'check.py';check.write_text('assert True\n')
            protected[str(check.relative_to(self.root/'project'))]=hashlib.sha256(check.read_bytes()).hexdigest()
            cases.append({'id':str(i),'agent_type':role,'case_directory':str(case)})
            rules.append({'id':str(i),'schema_version':2,'seeded_failure':False})
            record=self.root/f'session{i}.jsonl'
            write_session(record,str(i),role,'parent',[
                {'type':'function_call','name':'exec_command','call_id':'c','arguments':json.dumps({'cmd':'python -B check.py','workdir':str(case)})},
                {'type':'function_call_output','call_id':'c','output':json.dumps({'exit_code':0,'output':'controlled check'})},final()])
            self.sessions.append(record)
        self.summary={'revision':REV,'source_revision_unchanged':True,'protected_fixtures_unchanged':True,
                      'fixture_drift':[],'missing':[],'exit_code':0,'expected':39,'verified':39,'root_session':'parent'}
        write_json(self.root/'summary.json',self.summary)
        write_json(self.root/'project/selected-cases.json',cases)
        write_json(self.root/'all-agents-criteria.json',rules)
        write_json(self.root/'protected-fixtures.json',protected)

    def verify(self):return local.verify_local_native(self.root,REV,self.roles,self.sessions)

    def test_corroborates_all_39_unique_roles_and_real_tool_pair_shapes(self):
        report=self.verify()
        self.assertEqual(report['verified'],39)
        self.assertFalse(report['remote_native_test_performed'])
        self.assertEqual(len(report['session_sha256']),39)

    def test_refuses_summary_alone_and_duplicate_or_missing_roles(self):
        for records in ([],self.sessions[:-1],self.sessions[:-1]+[self.sessions[0]]):
            with self.subTest(records=len(records)),self.assertRaises(ValueError):
                local.verify_local_native(self.root,REV,self.roles,records)

    def test_refuses_stale_revision_source_change_and_fixture_claims(self):
        for key,value in [('revision','c'*40),('source_revision_unchanged',False),('source_revision_unchanged',None),
                          ('fixture_drift',['0/check.py']),('protected_fixtures_unchanged',False),('verified',38),('exit_code',True)]:
            data=copy.deepcopy(self.summary);data[key]=value
            write_json(self.root/'summary.json',data)
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.verify()

    def test_refuses_actual_protected_fixture_drift(self):
        (self.root/'project/0/check.py').write_text('assert False\n')
        with self.assertRaisesRegex(ValueError,'fixture drift'):self.verify()

    def test_refuses_unpaired_failed_or_manipulated_command(self):
        original=self.sessions[0].read_text()
        for before,after in [('python -B check.py','python -B check.py; exit 0'),('"call_id": "c"','"call_id": "not-paired"'),
                             ('"task_complete"','"not_complete"'),('"parent_thread_id": "parent"','"parent_thread_id": "other"')]:
            text=original.replace(before,after,1)
            self.sessions[0].write_text(text)
            with self.subTest(before=before),self.assertRaises(ValueError):self.verify()

    def test_refuses_missing_case_inventory_and_unsafe_protected_path(self):
        cases=local.read_json(self.root/'project/selected-cases.json')
        write_json(self.root/'project/selected-cases.json',cases[:-1])
        with self.assertRaises(ValueError):self.verify()
        write_json(self.root/'project/selected-cases.json',cases)
        manifest=local.read_json(self.root/'protected-fixtures.json');manifest['../../outside']='a'*64
        write_json(self.root/'protected-fixtures.json',manifest)
        with self.assertRaises(ValueError):self.verify()

    def reviews(self):
        paths=[]
        for name,role in [('G01','guardian_independent_auditor'),('G02','guardian_release_auditor')]:
            record=self.root/(name+'.jsonl')
            report={'gate':name,'revision':REV,'artifact_sha256':DIGEST,'kind':'AI_ADVISORY','decision':'ACCEPTED_WITH_LIMITATIONS',
                    'findings_unresolved':0,'limitations':['Local mutable host evidence; no external qualification'],
                    'session_record':str(record),
                    'implementation_session':'implementer'}
            write_session(record,name,role,'implementer',[final(REV+' '+DIGEST+' ACCEPTED_WITH_LIMITATIONS\nGUARDIAN_RELEASE_REVIEW '+local.review_claim_digest(report))])
            report['session_sha256']=hashlib.sha256(record.read_bytes()).hexdigest()
            path=self.root/(name+'.json');write_json(path,report);paths.append(path)
        return paths

    def test_advisory_reviews_are_distinct_pinned_native_children(self):
        report=local.verify_local_reviews(self.reviews(),REV,DIGEST)
        self.assertEqual(report['gates'],['G01','G02']);self.assertFalse(report['human_review_recorded_by_github'])

    def test_refuses_review_json_only_wrong_digest_kind_role_or_unbound_final(self):
        paths=self.reviews();original=local.read_json(paths[0])
        for key,value in [('artifact_sha256','c'*64),('kind','HUMAN_APPROVED'),('findings_unresolved',1),
                          ('session_sha256','0'*64),('implementation_session','other'),('limitations',[])]:
            changed=copy.deepcopy(original);changed[key]=value;write_json(paths[0],changed)
            with self.subTest(key=key),self.assertRaises(ValueError):local.verify_local_reviews(paths,REV,DIGEST)
        write_json(paths[0],original)
        record=Path(original['session_record']);record.write_text(record.read_text().replace(REV,'c'*40))
        original['session_sha256']=hashlib.sha256(record.read_bytes()).hexdigest();write_json(paths[0],original)
        with self.assertRaisesRegex(ValueError,'final lacks'):local.verify_local_reviews(paths,REV,DIGEST)

    def test_review_claim_change_cannot_reuse_completed_reviewer_final(self):
        paths=self.reviews();report=local.read_json(paths[0]);report['limitations']=['Invented new unreviewed scope']
        write_json(paths[0],report)
        with self.assertRaisesRegex(ValueError,'exact review claims'):local.verify_local_reviews(paths,REV,DIGEST)

    def test_duplicate_keys_and_linked_parent_refused(self):
        duplicate=self.root/'duplicate.json';duplicate.write_text('{"a":1,"a":2}')
        with self.assertRaises(ValueError):local.read_json(duplicate)
        with patch.object(Path,'is_symlink',return_value=True):
            with self.assertRaises(ValueError):local.read_json(self.root/'summary.json')

    def test_nonfinite_json_and_malformed_session_shapes_fail_with_valueerror(self):
        original=self.sessions[0].read_text()
        rows=[json.loads(line) for line in original.splitlines()]
        malformed=['not JSON','[]','null','{"type":"x","type":"y"}',
                   '{"type":"event_msg","payload":{"number":NaN}}',
                   '{"type":"event_msg","payload":{"number":Infinity}}']
        for replacement in ('string',[],None):
            changed=copy.deepcopy(rows);changed[0]['payload']['source']=replacement
            malformed.append('\n'.join(json.dumps(r) for r in changed))
            changed=copy.deepcopy(rows);changed[1]['payload']=replacement
            malformed.append('\n'.join(json.dumps(r) for r in changed))
        for value in malformed:
            self.sessions[0].write_text(value)
            with self.subTest(value=value[:90]),self.assertRaises(ValueError):local.session(self.sessions[0])
        self.sessions[0].write_text(original)
        for value in ('NaN','Infinity','-Infinity','{"nested":{"x":NaN}}'):
            target=self.root/'malformed.json';target.write_text(value)
            with self.subTest(value=value),self.assertRaises(ValueError):local.read_json(target)

    def test_invalid_source_roots_fail_with_valueerror(self):
        for value in (None,[],self.root/'missing-root',self.root/'summary.json'):
            with self.subTest(value=str(value)),self.assertRaises(ValueError):local.check_source(value,REV)

    def test_session_shape_boundaries_fail_closed_without_executing_evidence(self):
        rows=[json.loads(line) for line in self.sessions[0].read_text().splitlines()]
        invalid=[]
        for value in (None,[],False,0,'', '   ',{}):
            changed=copy.deepcopy(rows);changed[1]['type']=value;invalid.append(changed)
            changed=copy.deepcopy(rows);changed[1]['payload']['type']=value;invalid.append(changed)
        for value in (None,[],False,0,'text'):
            changed=copy.deepcopy(rows);changed[0]['payload']['source']['subagent']=value;invalid.append(changed)
            changed=copy.deepcopy(rows);changed[0]['payload']['source']['subagent']['thread_spawn']=value;invalid.append(changed)
            changed=copy.deepcopy(rows);changed[1]=value;invalid.append(changed)
        for missing in ('type','payload'):
            changed=copy.deepcopy(rows);del changed[1][missing];invalid.append(changed)
        changed=copy.deepcopy(rows);del changed[1]['payload']['type'];invalid.append(changed)
        changed=copy.deepcopy(rows);changed[3]['payload']['content']=[{'text':[]}];invalid.append(changed)
        for number,changed in enumerate(invalid):
            self.sessions[0].write_text('\n'.join(json.dumps(r) for r in changed),encoding='utf8')
            with self.subTest(boundary=number),patch.object(local.subprocess,'run') as execute,self.assertRaises(ValueError):
                local.session(self.sessions[0])
            execute.assert_not_called()

    def test_strict_json_rejects_overflow_nonfinite_and_nested_duplicates(self):
        for value in ('1e999','-1e999','{"nested":[1e999]}','{"nested":{"x":1,"x":2}}',
                      '{"nested":{"x":-Infinity}}'):
            with self.subTest(value=value),self.assertRaises(ValueError):local.strict_json(value)
        self.assertEqual(local.strict_json('{"finite":1.25e2,"tiny":1e-999}'),{'finite':125.0,'tiny':0.0})

    def test_native_session_unknown_record_extensions_remain_supported(self):
        # Native transcripts evolve; unrelated well-formed records have no
        # bearing on the required child identity/completion/tool evidence.
        rows=self.sessions[0].read_text().splitlines()
        rows.insert(1,json.dumps({'type':'future_context','payload':{'structured':[]}}))
        self.sessions[0].write_text('\n'.join(rows),encoding='utf8')
        self.assertEqual(local.session(self.sessions[0])[2],sorted(self.roles)[0])

    def test_source_requires_exact_clean_commit(self):
        ok=subprocess.CompletedProcess([],0,REV+'\n','')
        dirty=subprocess.CompletedProcess([],0,' M tools/example.py\n','')
        with patch.object(local.subprocess,'run',side_effect=[ok,dirty]):
            with self.assertRaisesRegex(ValueError,'not clean'):local.check_source(self.root,REV)
        with patch.object(local.subprocess,'run',side_effect=[subprocess.CompletedProcess([],0,'c'*40,''),subprocess.CompletedProcess([],0,'','')]):
            with self.assertRaises(ValueError):local.check_source(self.root,REV)


class AutonomousGatePolicyTests(unittest.TestCase):
    def test_regenerated_source_baseline_rejects_json_rebaselining(self):
        from tools.native_pack_cases import create
        source=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            evidence=Path(folder).resolve()
            subprocess.run([sys.executable,'-B',str(source/'tools/native_cases.py'),str(evidence),str(source/'core/agents.json')],
                           check=True,capture_output=True,text=True,timeout=30)
            cases=local.read_json(evidence/'project/cases.json')+create(evidence/'project',source/'packs')
            write_json(evidence/'project/selected-cases.json',cases)
            mutable={'S05/index.html','S08/domain.py','S24/domain.py'}
            protected={str(p.relative_to(evidence/'project')):hashlib.sha256(p.read_bytes()).hexdigest()
                       for case in cases for p in Path(case['case_directory']).rglob('*') if p.is_file()
                       and p.relative_to(evidence/'project').as_posix() not in mutable}
            write_json(evidence/'protected-fixtures.json',protected)
            self.assertTrue(local.verify_native_baseline(source,evidence)['source_baseline_corroborated'])
            canonical_temp=evidence/'canonical-os-temp';canonical_temp.mkdir()
            os_alias=evidence/'os-temp-alias'
            original_resolve=Path.resolve;original_safe=local.safe
            def resolve_owned_alias(path,*args,**kwargs):
                return canonical_temp if path==os_alias else original_resolve(path,*args,**kwargs)
            def refuse_unresolved_alias(path):
                if Path(path)==os_alias:raise ValueError('Unresolved OS temp alias')
                return original_safe(path)
            with patch.object(local.tempfile,'TemporaryDirectory',return_value=contextlib.nullcontext(str(os_alias))),\
                 patch.object(Path,'resolve',new=resolve_owned_alias),patch.object(local,'safe',side_effect=refuse_unresolved_alias):
                self.assertTrue(local.verify_native_baseline(source,evidence)['source_baseline_corroborated'])
            original=local.read_json(evidence/'all-agents-criteria.json');changed=copy.deepcopy(original)
            build=next(r for r in changed if r['id']=='S08');build['build']=False;build['seeded_failure']=False
            write_json(evidence/'all-agents-criteria.json',changed)
            with self.assertRaisesRegex(ValueError,'criteria differ'):local.verify_native_baseline(source,evidence)
            write_json(evidence/'all-agents-criteria.json',original)
            changed=copy.deepcopy(cases);next(c for c in changed if c['id']=='S08')['mode']='AUDIT'
            write_json(evidence/'project/selected-cases.json',changed)
            with self.assertRaisesRegex(ValueError,'mode/role/rule differs'):local.verify_native_baseline(source,evidence)
            write_json(evidence/'project/selected-cases.json',cases)
            key=next(iter(protected));protected[key]='0'*64;write_json(evidence/'protected-fixtures.json',protected)
            with self.assertRaisesRegex(ValueError,'manifest differs'):local.verify_native_baseline(source,evidence)

    def test_actual_source_runtime_and_all_pack_profiles_are_bound(self):
        source=Path(__file__).resolve().parents[1]
        if not (source/'global/agents').is_dir():self.skipTest('Source profiles not present in this installed layout')
        with tempfile.TemporaryDirectory() as folder:
            evidence=Path(folder).resolve();project=evidence/'project'
            for directory in ('global','core','tools','packs','eval'):
                shutil.copytree(source/directory,project/'.guardian'/directory,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            native=project/'.codex/agents';native.mkdir(parents=True)
            profiles=list((source/'global/agents').glob('*.toml'))
            for manifest in (source/'packs').glob('*/manifest.json'):
                profiles.extend(manifest.parent/a['file'] for a in local.read_json(manifest)['agents'])
            self.assertEqual(len(profiles),39)
            for profile in profiles:shutil.copyfile(profile,native/profile.name)
            result=local.verify_runtime(source,evidence)
            self.assertEqual(result['profiles_verified'],39)
            (native/profiles[-1].name).write_text('modified native profile')
            with self.assertRaisesRegex(ValueError,'native profile differs'):local.verify_runtime(source,evidence)
            shutil.copyfile(profiles[-1],native/profiles[-1].name)
            (project/'.guardian/tools/test_native_agents.py').write_text('modified harness')
            with self.assertRaisesRegex(ValueError,'runtime differs'):local.verify_runtime(source,evidence)

    def test_no_implicit_policy_downgrade(self):
        for kwargs in ({'policy':'unknown'},{'local_native':'untrusted'},{'native_sessions':['untrusted']}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError),patch.object(gate,'_api') as api:
                gate.verify_external('owner/repo',REV,'missing.zip',1,None,2,3,**kwargs)
            api.assert_not_called()

    def test_strict_default_still_requires_native_run(self):
        with self.assertRaisesRegex(ValueError,'Positive external evidence IDs'):
            gate.verify_external('owner/repo',REV,'missing.zip',1,None,2,3)

    def test_autonomous_never_accepts_remote_or_human_substitute_parameters(self):
        with tempfile.TemporaryDirectory() as folder:
            artifact=Path(folder)/'a.zip';artifact.write_bytes(b'unit ZIP stub, never published')
            for native,trusted in [(5,()),(None,('reviewer',))]:
                with self.subTest(native=native),self.assertRaises(ValueError):
                    gate.verify_external('owner/repo',REV,artifact,1,native,2,3,policy='operator-autonomous',trusted_reviewers=trusted)

    def test_external_checks_and_provenance_remain_mandatory(self):
        with tempfile.TemporaryDirectory() as folder:
            artifact=Path(folder)/'a.zip';artifact.write_bytes(b'unit ZIP stub, never published')
            native={'revision':REV,'expected':39,'verified':39,'all_native_roles_verified':True,'protected_fixtures_unchanged':True}
            grader={'revision':REV,'passed':True,'tests':14,'skipped':0,'failures':0,'errors':0}
            def api(path):
                if path.endswith('/jobs?per_page=100'):return {'jobs':[{'conclusion':'success'} for _ in range(9)]}
                if path.endswith('/pulls/3'):return {'head':{'sha':REV},'draft':False,'user':{'login':'author'}}
                return {'head_sha':REV,'status':'completed','conclusion':'success','path':'.github/workflows/ci.yml' if path.endswith('/1') else '.github/workflows/grader-acceptance.yml'}
            kwargs=dict(policy='operator-autonomous',local_native=folder,native_sessions=['unit'],advisory_reviews=['unit'])
            with patch.object(local,'check_source'),patch.object(local,'verify_runtime'),patch.object(local,'verify_native_baseline'),patch.object(local,'expected_roles'),\
                 patch.object(local,'verify_local_native',return_value=native),patch.object(local,'verify_local_reviews',return_value={'gates':['G01','G02']}),\
                 patch.object(gate,'_api',side_effect=api),patch.object(gate,'_acceptance_artifact',return_value=grader),\
                 patch.object(gate.subprocess,'run',return_value=subprocess.CompletedProcess([],1,'','bad signature')):
                with self.assertRaisesRegex(ValueError,'provenance'):gate.verify_external('owner/repo',REV,artifact,1,None,2,3,**kwargs)
            with patch.object(local,'check_source'),patch.object(local,'verify_runtime'),patch.object(local,'verify_native_baseline'),patch.object(local,'expected_roles'),\
                 patch.object(local,'verify_local_native',return_value=native),patch.object(local,'verify_local_reviews',return_value={'gates':['G01','G02']}),\
                 patch.object(gate,'_api',side_effect=api) as api_mock,patch.object(gate,'_acceptance_artifact',return_value=grader),\
                 patch.object(gate.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'[{"unit_mock":true}]','')):
                result=gate.verify_external('owner/repo',REV,artifact,1,None,2,3,**kwargs)
                self.assertTrue(result['policy_acceptance_passed'])
                self.assertFalse(result['human_review_recorded_by_github']);self.assertFalse(result['remote_native_test_performed'])
                self.assertFalse(result['publication_authorized'])
                self.assertEqual(result['policy'],'operator-autonomous')
                self.assertFalse(any('/reviews?' in str(call) for call in api_mock.call_args_list))
            with patch.object(local,'check_source'),patch.object(local,'verify_runtime'),patch.object(local,'verify_native_baseline'),patch.object(local,'expected_roles'),\
                 patch.object(local,'verify_local_native',return_value=native),patch.object(local,'verify_local_reviews',return_value={}),\
                 patch.object(gate,'_api',return_value={'head_sha':'c'*40}):
                with self.assertRaisesRegex(ValueError,'wrong revision'):gate.verify_external('owner/repo',REV,artifact,1,None,2,3,**kwargs)
