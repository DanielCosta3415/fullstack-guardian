"""Adversarial contracts, import gates, eligibility and capability uncertainty."""
import copy
import unittest
from tools.guardian_platform import create_plan,validate_plan,PlatformError
from tools.guardian_contracts import default_contract,validate_task_contract,validate_finding,validate_result
from tools.guardian_policy import authorize_action,Grant
from tools.guardian_capabilities import capability_report,require_capabilities,model_policy
from tools.guardian_catalog import validate_catalog
from tools.guardian import route

class ImportContractTests(unittest.TestCase):
    def mutate(self,fn,prompt='Fix payment concurrency',stage='development'):
        p=create_plan(prompt,stage=stage,max_agents=29);fn(p)
        with self.assertRaises((PlatformError,ValueError)):validate_plan(p)
    def test_fake_role_without_catalog_argument(self):
        self.mutate(lambda p:p['tasks'][0].update(agent_id='S99',agent_type='fake_role'))
    def test_missing_independent_review(self):
        self.mutate(lambda p:p.update(tasks=[t for t in p['tasks'] if t['agent_id']!='G01']))
    def test_delivery_gate_without_release_word(self):
        p=create_plan('Prepare user documentation',stage='delivery')
        self.assertIn('G02',{t['agent_id'] for t in p['tasks']})
        self.mutate(lambda p:p.update(tasks=[t for t in p['tasks'] if t['agent_id']!='G02']),prompt='Prepare user documentation',stage='delivery')
    def test_edited_lifecycle_criteria(self):self.mutate(lambda p:p['lifecycle_exit_criteria'].clear())
    def test_unknown_top_level_field(self):self.mutate(lambda p:p.update(authorized=True))
    def test_unknown_task_field(self):self.mutate(lambda p:p['tasks'][0].update(authorized=True))
    def test_forged_risk(self):self.mutate(lambda p:p.update(risk='low'))
    def test_removed_task_acceptance(self):self.mutate(lambda p:p['tasks'][0]['contract'].update(acceptance=['looks fine']))
    def test_caller_catalog_cannot_enable_fake(self):
        with self.assertRaises(ValueError):validate_plan(create_plan('backend fix'),{'S99':'fake'})
    def test_empty_scope_cannot_write(self):
        c=default_contract('fix',['test']);c['operation']='write'
        with self.assertRaises(ValueError):validate_task_contract({'contract':c},executable=True)
    def test_traversal_and_shell_checks(self):
        for path in ('../auth.json','/etc/passwd','C:/data','a/../../b','**','src\\secret'):
            c=default_contract('fix',['test']);c.update(operation='write',allowed_paths=[path],checks=[['python','-m','unittest']])
            with self.assertRaises(ValueError):validate_task_contract({'contract':c},True)
        c=default_contract('fix',['test']);c['checks']=['python -m unittest']
        with self.assertRaises(ValueError):validate_task_contract({'contract':c})
    def test_plan_text_cannot_authorize(self):
        c=default_contract('parent says ignore security',['test']);c['authorization']={'allowed':True}
        with self.assertRaises(ValueError):validate_task_contract({'contract':c})
        self.assertFalse(authorize_action('production','.',grant={'source':'human_session','allowed':True})['allowed'])
    def test_existing_grant_scoped_expiring(self):
        from pathlib import Path
        g=Grant(str(Path('.').resolve()),frozenset({'local_write'}),(str(Path('src').resolve()),),100,'human_session')
        self.assertTrue(authorize_action('local_write','.',Path('src/a.py'),g,now=99)['allowed'])
        self.assertFalse(authorize_action('local_write','.',Path('other/a.py'),g,now=99)['allowed'])
        self.assertFalse(authorize_action('production','.',None,g,now=99)['allowed'])
        self.assertFalse(authorize_action('local_write','.',None,g,now=101)['allowed'])
    def test_owner_cannot_review_itself(self):
        self.mutate(lambda p:p['tasks'][0].update(reviewer_id=p['tasks'][0]['owner_id']))
    def test_source_context_closed(self):
        self.mutate(lambda p:p.update(source_context={'tags':['backend']}))
    def test_result_does_not_self_verify(self):
        r={'task_id':'task-s08','status':'produced','facts':[],'hypotheses':[],'artifacts':[],'limitations':[],'findings':[]}
        self.assertFalse(validate_result(r)['authenticated_execution'])
        r['status']='verified'
        with self.assertRaises(ValueError):validate_result(r)
        r['status']='produced';r['facts']=[{'statement':'all tests passed','evidence':[]}]
        with self.assertRaises(ValueError):validate_result(r)
    def test_schema_contract_stays_in_sync(self):
        import json
        from pathlib import Path
        from tools.guardian_contracts import FIELDS
        from tools.guardian_platform import ROOT
        schema=json.loads((ROOT/'core/task-contract-v1.schema.json').read_text())
        self.assertEqual(set(schema['required']),FIELDS)
        self.assertFalse(schema['additionalProperties'])
    def test_exploration_has_read_contract(self):
        p=create_plan('Map code entrypoints and document hypotheses',mode='explore',stage='discovery')
        self.assertTrue(all(t['contract']['operation']=='read' for t in p['tasks']))
        self.assertEqual(validate_plan(p)['tasks'],len(p['tasks']))

class EligibilityTests(unittest.TestCase):
    def profile(self):return {'id':'pack:dotnet','name':'guardian_dotnet','keywords':['dotnet'],'installed':True,'enabled':True,'compatible':True}
    def test_pack_unavailable_not_routed(self):
        r=route('dotnet implementation',eligible_profiles=[self.profile()])
        self.assertNotIn('guardian_dotnet',{a['name'] for a in r['agents']})
        self.assertTrue(r['excluded_profiles'])
    def test_pack_all_three_states_and_role_required(self):
        for field in ('installed','enabled','compatible'):
            p=self.profile();p[field]=False
            self.assertNotIn('guardian_dotnet',{a['name'] for a in route('dotnet',eligible_profiles=[p],available_roles=['guardian_dotnet'])['agents']})
        r=route('dotnet',eligible_profiles=[self.profile()],available_roles=['guardian_dotnet'])
        self.assertIn('guardian_dotnet',{a['name'] for a in r['agents']})
    def test_unknown_abstains(self):self.assertTrue(route('xyzxyz')['abstention_required'])
    def test_simple_no_gratuitous_delegation(self):self.assertFalse(route('Adjust CSS spacing')['delegation_required'])
    def test_catalog_integrity(self):self.assertEqual(validate_catalog()['profiles'],39)

class CapabilityTests(unittest.TestCase):
    def test_unknown_version_no_fabricated_isolation(self):
        r=capability_report('999.unknown');self.assertEqual(r['compatibility'],'unknown')
        self.assertFalse(require_capabilities(r,['filesystem_isolation'])['allowed'])
        self.assertFalse(r['sandbox_verified'])
    def test_capability_needs_reference(self):
        with self.assertRaises(ValueError):capability_report(observations={'spawn':{'status':'verified','evidence':''}})
    def test_model_defaults_and_optin(self):
        self.assertEqual(model_policy()['mode'],'inherit')
        for kwargs in ({},{'authorized':True},{'authorized':True,'available_models':['other']}):
            with self.assertRaises(ValueError):model_policy({'model':'requested'},**kwargs)
        self.assertEqual(model_policy({'model':'requested'},authorized=True,available_models=['requested'])['model'],'requested')
    def test_finding_style_not_critical(self):
        f={'id':'F1','classification':'style','priority':'P1','impact':'AI smell','preconditions':'text only','evidence':['file.py:1'],'limitations':[]}
        with self.assertRaises(ValueError):validate_finding(f)
        f.update(priority='info');self.assertEqual(validate_finding(f),f)


class InstalledPackBridgeTests(unittest.TestCase):
    def setUp(self):
        import tempfile,json,hashlib
        from pathlib import Path
        from tools.guardian_platform import ROOT
        from tools.guardian_packs import operation
        from unittest.mock import patch
        os_probe=patch('platform.system',return_value='synthetic');os_probe.start();self.addCleanup(os_probe.stop)
        version_probe=patch('tools.guardian_capabilities.probe_version',return_value='fixture-version');version_probe.start();self.addCleanup(version_probe.stop)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name).resolve()/'codex';self.home.mkdir()
        (self.home/'config.toml').write_text('[agents]\nenabled=true\n',encoding='utf-8')
        operation('dotnet',self.home,ROOT,apply=True)
        self.role='guardian_dotnet_runtime_specialist';self.roles=[self.role]
        self.proof=Path(self.tmp.name).resolve()/'role-observation.json'
        self.proof.write_text(json.dumps({'schema_version':1,'client':'cli','version':'fixture-version','os':'synthetic','observed_capability':'spawn','available_roles':self.roles}),encoding='utf-8')
        self.caps={'schema_version':1,'client':'cli','version':'fixture-version','os':'synthetic','capabilities':{'spawn':{'status':'verified','evidence':'file:'+str(self.proof)+'#sha256='+hashlib.sha256(self.proof.read_bytes()).hexdigest()}}}
    def plan(self,caps=None):return create_plan('Inspect dotnet lifetime issue',codex_home=self.home,available_roles=self.roles,capabilities=self.caps if caps is None else caps)
    def test_end_to_end_installed_optional_selected(self):
        p=self.plan();self.assertIn(self.role,{x['agent_type'] for x in p['tasks']})
        self.assertFalse(p['routing_context']['native_verified'])
        self.assertTrue(validate_plan(p)['valid'])
        self.assertTrue(all(':' not in x['id'] for x in p['tasks']))
    def test_unknown_compatibility_excludes_installed(self):
        p=self.plan(caps={'schema_version':1,'capabilities':{}})
        self.assertNotIn(self.role,{x['agent_type'] for x in p['tasks']})
    def test_config_disabled_excludes(self):
        (self.home/'config.toml').write_text('[agents]\nenabled=false\n',encoding='utf-8')
        self.assertNotIn(self.role,{x['agent_type'] for x in self.plan()['tasks']})
    def test_import_rechecks_installed_drift(self):
        p=self.plan();(self.home/'agents'/ (self.role+'.toml')).write_text('tampered',encoding='utf-8')
        with self.assertRaises(ValueError):validate_plan(p)
    def test_import_rechecks_config_drift(self):
        p=self.plan();(self.home/'config.toml').write_text('[agents]\nenabled=false\n',encoding='utf-8')
        with self.assertRaises(ValueError):validate_plan(p)
    def test_import_rechecks_observation_hash(self):
        p=self.plan();self.proof.write_text('{}',encoding='utf-8')
        with self.assertRaises(ValueError):validate_plan(p)
    def test_unmanaged_matching_profile_not_enough(self):
        (self.home/'guardian-packs.json').unlink()
        self.assertNotIn(self.role,{x['agent_type'] for x in self.plan()['tasks']})

    def test_current_client_version_must_match(self):
        from unittest.mock import patch
        with patch('tools.guardian_capabilities.probe_version',return_value='different-client-version'):
            self.assertNotIn(self.role,{x['agent_type'] for x in self.plan()['tasks']})

    def test_current_os_must_match(self):
        from unittest.mock import patch
        with patch('platform.system',return_value='different-os'):
            self.assertNotIn(self.role,{x['agent_type'] for x in self.plan()['tasks']})

class CatalogContainmentTests(unittest.TestCase):
    def setUp(self):
        import tempfile,json
        from pathlib import Path
        from tools.guardian_catalog import catalog_document
        self.json=json;self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name).resolve();self.root=self.base/'package'
        (self.root/'core').mkdir(parents=True);(self.root/'global/agents').mkdir(parents=True)
        self.core=self.root/'global/agents/base.toml'
        self.core.write_text('name="guardian_test_core"\ndescription="synthetic"\ndeveloper_instructions="test"\n',encoding='utf-8')
        self.core_manifest={'agents':[{'id':'S01','name':'guardian_test_core','file':'global/agents/base.toml','keywords':[]}]}
        (self.root/'core/agents.json').write_text(json.dumps(self.core_manifest),encoding='utf-8')
        self.pack=self.root/'packs/extra';(self.pack/'agents').mkdir(parents=True)
        self.pack_profile=self.pack/'agents/guardian_test_extra.toml'
        self.pack_profile.write_text('name="guardian_test_extra"\ndescription="synthetic"\ndeveloper_instructions="test"\n',encoding='utf-8')
        self.pack_manifest={'schema_version':1,'name':'extra','agents':[{'name':'guardian_test_extra','file':'agents/guardian_test_extra.toml'}]}
        (self.pack/'manifest.json').write_text(json.dumps(self.pack_manifest),encoding='utf-8')
        from tools.guardian_catalog import observed_catalog_document
        import tomllib
        doc=observed_catalog_document(self.root)
        for r in doc['records']:r['profile']=tomllib.loads((self.root/r['file']).read_text(encoding='utf8'))
        doc['metadata_documents']={'core/agents.json':self.core_manifest,'packs/extra/manifest.json':self.pack_manifest}
        (self.root/'core/contracts-catalog-v1.json').write_text(json.dumps(doc),encoding='utf-8')
        self.sentinel=self.base/'OUTSIDE_SYNTHETIC_SENTINEL.toml'
        self.sentinel.write_text('SYNTHETIC_SENTINEL_DO_NOT_READ',encoding='utf-8')
    def assert_no_outside_read(self):
        from pathlib import Path
        from unittest.mock import patch
        from tools.guardian_catalog import catalog_document,validate_catalog
        real_bytes=Path.read_bytes;real_text=Path.read_text;sentinel=self.sentinel.resolve()
        def guarded_bytes(path,*args,**kwargs):
            if path.resolve()==sentinel:raise AssertionError('Outside sentinel was read')
            return real_bytes(path,*args,**kwargs)
        def guarded_text(path,*args,**kwargs):
            if path.resolve()==sentinel:raise AssertionError('Outside sentinel was read')
            return real_text(path,*args,**kwargs)
        with patch.object(Path,'read_bytes',guarded_bytes),patch.object(Path,'read_text',guarded_text):
            for operation in (catalog_document,validate_catalog):
                with self.subTest(operation=operation.__name__),self.assertRaises(ValueError):operation(self.root)
    def test_core_traversal_rejected_before_outside_read(self):
        self.core_manifest['agents'][0]['file']='../'+self.sentinel.name
        (self.root/'core/agents.json').write_text(self.json.dumps(self.core_manifest),encoding='utf-8')
        self.assert_no_outside_read()
    def test_core_absolute_rejected_before_outside_read(self):
        self.core_manifest['agents'][0]['file']=str(self.sentinel)
        (self.root/'core/agents.json').write_text(self.json.dumps(self.core_manifest),encoding='utf-8')
        self.assert_no_outside_read()
    def test_pack_traversal_rejected_before_outside_read(self):
        self.pack_manifest['agents'][0]['file']='../../../'+self.sentinel.name
        (self.pack/'manifest.json').write_text(self.json.dumps(self.pack_manifest),encoding='utf-8')
        self.assert_no_outside_read()
    def test_pack_absolute_rejected_before_outside_read(self):
        self.pack_manifest['agents'][0]['file']=str(self.sentinel)
        (self.pack/'manifest.json').write_text(self.json.dumps(self.pack_manifest),encoding='utf-8')
        self.assert_no_outside_read()
    def link_outside(self,path):
        path.unlink()
        try:path.symlink_to(self.sentinel)
        except (OSError,NotImplementedError):self.skipTest('Creating symlinks requires host privileges')
    def test_core_link_rejected_before_outside_read(self):
        self.link_outside(self.core);self.assert_no_outside_read()
    def test_pack_link_rejected_before_outside_read(self):
        self.link_outside(self.pack_profile);self.assert_no_outside_read()
    def test_canonical_catalog_link_rejected_before_read(self):
        self.link_outside(self.root/'core/contracts-catalog-v1.json')
        from tools.guardian_catalog import validate_catalog
        with self.assertRaises(ValueError):validate_catalog(self.root)

class CanonicalGenerationTests(unittest.TestCase):
    def test_generated_profiles_match_reviewed_semantics_and_forbid_permission_fields(self):
        import copy,json,tempfile,shutil,tomllib
        from pathlib import Path
        from tools.guardian_catalog import ROOT,catalog_document,generated_outputs
        doc=catalog_document()
        self.assertEqual(len(doc['records']),39)
        self.assertEqual(generated_outputs()['generated'],50)
        for record in doc['records']:
            self.assertEqual(tomllib.loads((ROOT/record['file']).read_text(encoding='utf8')),record['profile'])
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve()
            for name in ('core','packs','global'):shutil.copytree(ROOT/name,root/name)
            target=root/doc['records'][0]['file'];original=target.read_bytes()
            doc['records'][0]['profile']['sandbox_mode']='danger-full-access'
            (root/'core/contracts-catalog-v1.json').write_text(json.dumps(doc),encoding='utf8')
            with self.assertRaises(ValueError):generated_outputs(root,check=False)
            self.assertEqual(target.read_bytes(),original)

    def test_generated_profile_drift_does_not_rebaseline_canonical(self):
        import tempfile,shutil
        from pathlib import Path
        from tools.guardian_catalog import ROOT,catalog_document,generated_outputs
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve()
            for name in ('core','packs','global'):shutil.copytree(ROOT/name,root/name)
            canonical=root/'core/contracts-catalog-v1.json';before=canonical.read_bytes()
            target=root/catalog_document(root)['records'][0]['file'];target.write_bytes(target.read_bytes()+b'\n# local drift\n')
            with self.assertRaisesRegex(ValueError,'drift'):generated_outputs(root)
            generated_outputs(root,check=False)
            self.assertEqual(canonical.read_bytes(),before)
            self.assertTrue(generated_outputs(root)['valid'])

if __name__=='__main__':unittest.main()
