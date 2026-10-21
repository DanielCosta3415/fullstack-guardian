"""Global scope verification uses synthetic installations, never live credentials/models."""
import hashlib,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tools import test_native_agents as harness

class GlobalNativeScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve();self.root=self.base/'source';self.home=self.base/'home'
        self.project=self.base/'evidence/project';self.project.mkdir(parents=True)
        # Keep synthetic tests inside their fixture ancestor boundary; do not
        # inspect the operator's actual ancestor profiles/configuration.
        ancestors=patch.object(harness,'ancestor_directories',side_effect=lambda p:(p,p.parent))
        ancestors.start();self.addCleanup(ancestors.stop)
        for directory in ('global','core','tools','tests','project-template','docs','packs','scripts','eval'):
            (self.root/directory).mkdir(parents=True)
        shutil.copytree(harness.ROOT/'global/agents',self.root/'global/agents')
        shutil.copyfile(harness.ROOT/'core/agents.json',self.root/'core/agents.json')
        for manifest in (harness.ROOT/'packs').glob('*/manifest.json'):
            pack=json.loads(manifest.read_text(encoding='utf8'))
            target=self.root/'packs'/manifest.parent.name;target.mkdir()
            shutil.copyfile(manifest,target/'manifest.json')
            for agent in pack['agents']:
                dest=target/agent['file'];dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(manifest.parent/agent['file'],dest)
        for name in ('install.py','README.md','RELEASE_NOTES.md','VERSION','LICENSE','NOTICE.md','THIRD_PARTY_NOTICES.md','SECURITY.md','SUPPORT.md'):
            (self.root/name).write_text('2.2.0' if name=='VERSION' else 'synthetic '+name,encoding='utf8')
        self.runtime=self.home/'guardian-system';shutil.copytree(self.root,self.runtime)
        (self.home/'agents').mkdir()
        for p in (self.root/'global/agents').glob('*.toml'):shutil.copyfile(p,self.home/'agents'/p.name)
        packs={}
        for manifest in (self.root/'packs').glob('*/manifest.json'):
            pack=json.loads(manifest.read_text(encoding='utf8'));files={}
            for agent in pack['agents']:
                p=manifest.parent/agent['file'];shutil.copyfile(p,self.home/'agents'/p.name)
                files[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
            packs[pack['name']]={'files':files}
        (self.home/'guardian-packs.json').write_text(json.dumps({'schema_version':1,'packs':packs}))
        receipt={'schema':1,'mode':'user','version':'2.2.0','identity':{'codex':str(self.home),'runtime':str(self.runtime)},
                 'files':[{'path':str(p),'hash':hashlib.sha256(p.read_bytes()).hexdigest()} for p in self.runtime.rglob('*') if p.is_file()]}
        receipt['files'] += [{'path':str(self.home/'agents'/p.name),'hash':hashlib.sha256(p.read_bytes()).hexdigest()}
                            for p in (self.root/'global/agents').glob('*.toml')]
        (self.home/'guardian-install.json').write_text(json.dumps(receipt))
        (self.home/'config.toml').write_text('[agents]\nenabled=true\n')
        (self.home/'AGENTS.md').write_text('Synthetic global policy')
        (self.home/'auth.json').write_text('NEVER_READ_PRIVATE_CANARY')

    def verify(self):return harness.preflight_global(self.home,self.project,self.root)

    def test_exact_global_readonly_binding_and_no_credentials_or_local_install(self):
        before=harness.global_snapshot(self.home)
        read=Path.read_bytes
        def bounded(path,*a,**kw):
            self.assertNotEqual(path.name,'auth.json')
            return read(path,*a,**kw)
        with patch.object(Path,'read_bytes',new=bounded),patch.object(harness.subprocess,'Popen') as models:
            result=self.verify()
        self.assertEqual(result['profiles_verified'],39)
        self.assertEqual(result['runtime_scope'],'global-existing')
        self.assertEqual(before,harness.global_snapshot(self.home))
        self.assertFalse((self.project/'.codex').exists());self.assertFalse((self.project/'.guardian').exists())
        self.assertNotIn('auth.json',result['snapshot']);models.assert_not_called()

    def test_missing_profile_wrong_version_and_runtime_drift_fail(self):
        profile=next((self.home/'agents').glob('*.toml'));data=profile.read_bytes();profile.unlink()
        with self.assertRaises((ValueError,OSError)):self.verify()
        profile.write_bytes(data)
        (self.runtime/'VERSION').write_text('2.1.0')
        with self.assertRaisesRegex(ValueError,'version'):self.verify()
        (self.runtime/'VERSION').write_text('2.2.0')
        (self.runtime/'README.md').write_text('drift')
        with self.assertRaisesRegex(ValueError,'drift'):self.verify()

    def test_ancestor_alias_profile_and_agent_config_override_refused(self):
        local=self.project.parent/'.codex';(local/'agents').mkdir(parents=True)
        shutil.copyfile(next((self.home/'agents').glob('*.toml')),local/'agents/alias.toml')
        with self.assertRaisesRegex(ValueError,'override'):self.verify()
        (local/'agents/alias.toml').unlink()
        (local/'config.toml').write_text('[agents.guardian_engineering_orchestrator]\nconfig_file="untrusted.toml"\n')
        with self.assertRaisesRegex(ValueError,'configuration'):self.verify()

    def test_disabled_agents_and_pack_receipt_drift_refused(self):
        (self.home/'config.toml').write_text('[agents]\nenabled=false\n')
        with self.assertRaisesRegex(ValueError,'enabled'):self.verify()
        (self.home/'config.toml').write_text('[agents]\nenabled=true\n')
        (self.home/'guardian-packs.json').write_text('{"schema_version":1,"packs":{}}')
        with self.assertRaisesRegex(ValueError,'receipt/profile'):self.verify()

    def test_snapshot_detects_configuration_profile_and_runtime_changes(self):
        before=harness.global_snapshot(self.home)
        (self.home/'config.toml').write_text('[agents]\nenabled=true\n# changed\n')
        self.assertNotEqual(before,harness.global_snapshot(self.home))
        profile=next((self.home/'agents').glob('*.toml'));profile.write_text('name="guardian_new_override"\n')
        with self.assertRaisesRegex(ValueError,'Missing global Guardian native profile'):self.verify()

    def test_global_guardian_config_mapping_refused_without_reading_target(self):
        outside=self.base/'unreviewed.toml';outside.write_text('PRIVATE_CANARY_NOT_TO_READ')
        (self.home/'config.toml').write_text('[agents]\nenabled=true\n[agents.guardian_engineering_orchestrator]\nconfig_file='+json.dumps(str(outside))+'\n')
        before=(self.home/'config.toml').read_bytes()
        original=Path.read_text
        def permitted(path,*args,**kwargs):
            self.assertNotEqual(path,outside)
            return original(path,*args,**kwargs)
        with patch.object(Path,'read_text',new=permitted),self.assertRaisesRegex(ValueError,'global Guardian agent configuration'):
            self.verify()
        self.assertEqual((self.home/'config.toml').read_bytes(),before)

    def test_global_guardian_alias_duplicate_refused_without_removal(self):
        alias=self.home/'agents/other-name.toml'
        original=next((self.home/'agents').glob('*.toml'))
        shutil.copyfile(original,alias)
        before=alias.read_bytes()
        with self.assertRaisesRegex(ValueError,'alias or duplicate'):self.verify()
        self.assertEqual(alias.read_bytes(),before)

    def test_unrelated_custom_profile_and_configuration_remain_accepted_and_untouched(self):
        custom=self.home/'agents/my_custom_agent.toml';custom.write_text('name="my_custom_agent"\ndescription="User customization"\n')
        config=self.home/'config.toml'
        config.write_text('[agents]\nenabled=true\n[agents.my_custom_agent]\nconfig_file="never-follow-this-file.toml"\n')
        before={p:p.read_bytes() for p in (custom,config)}
        self.assertEqual(self.verify()['profiles_verified'],39)
        self.assertEqual({p:p.read_bytes() for p in before},before)

    def test_native_profile_discovery_is_bounded(self):
        alias=self.home/'agents/oversized.toml';alias.write_bytes(b'#'+b'x'*2_000_000)
        with self.assertRaisesRegex(ValueError,'oversized'):self.verify()

    def test_explicit_router_does_not_change_default_prompt_or_command_permissions(self):
        case={'id':'A00','agent_type':'guardian_engineering_orchestrator','case_directory':str(self.project/'A00'),'mode':'AUDIT','task':'Read case'}
        default=harness.build_prompt([case],self.project)
        global_prompt=harness.build_prompt([case],self.project,self.runtime/'tools/guardian.py')
        self.assertIn(str(self.project/'.guardian/tools/guardian.py'),default)
        self.assertIn('Router: '+str(self.runtime/'tools/guardian.py'),global_prompt)
        self.assertNotIn('project-installed router',global_prompt)
        command=harness.codex_command('codex',self.project)
        self.assertEqual(command[command.index('--sandbox')+1],'workspace-write')
        self.assertNotIn('--model',command)
