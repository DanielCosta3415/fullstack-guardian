"""Artifact identity and actual Windows interpreter fallback regressions."""
import json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from tools import build_release
BASE=Path(__file__).resolve().parents[1]

class DistributionHardeningTests(unittest.TestCase):
    def test_all_manifests_have_one_identity(self):
        if not (BASE/'plugin.json').exists():self.skipTest('source only')
        version=(BASE/'VERSION').read_text().strip()
        for name in ('plugin.json','.codex-plugin/plugin.json'):
            self.assertEqual(json.loads((BASE/name).read_text(encoding='utf8'))['version'],version)

    def test_build_refuses_mislabeled_version(self):
        if not (BASE/'plugin.json').exists():self.skipTest('source only')
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve();(root/'.codex-plugin').mkdir()
            (root/'VERSION').write_text('2.2.0-dev.2')
            (root/'plugin.json').write_text('{"version":"2.1.0"}')
            (root/'.codex-plugin/plugin.json').write_text('{"version":"2.2.0-dev.2"}')
            with self.assertRaisesRegex(ValueError,'mismatch'):build_release.build(root/'out',root)

    def test_175_reviewed_references_are_pinned_not_executable(self):
        lock=json.loads((BASE/'docs/upstream/voltagent-source-lock.json').read_text(encoding='utf8'))
        self.assertEqual(len(lock['profiles']),175)
        self.assertEqual(len({x['name'] for x in lock['profiles']}),175)
        self.assertEqual(lock['license'],'MIT')
        self.assertRegex(lock['commit'],r'^[0-9a-f]{40}$')
        for x in lock['profiles']:self.assertRegex(x['sha256'],r'^[0-9a-f]{64}$')

    @unittest.skipUnless(os.name=='nt' and shutil.which('powershell'),'Windows PowerShell required')
    def test_invalid_py_launcher_falls_back_to_existing_python(self):
        with tempfile.TemporaryDirectory() as t:
            folder=Path(t).resolve();(folder/'py.cmd').write_text('@exit /b 7\n')
            env=os.environ.copy();env['PATH']=str(folder)+os.pathsep+str(Path(sys.executable).parent)+os.pathsep+env.get('PATH','')
            helper=BASE/'scripts/Find-GuardianPython.ps1'
            command=". '"+str(helper).replace("'","''")+"'; $p=Find-GuardianPython; & $p.Executable @($p.Prefix) -c 'import sys;print(sys.version_info.major)'"
            p=subprocess.run(['powershell','-NoProfile','-Command',command],capture_output=True,text=True,env=env,timeout=30)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertEqual(p.stdout.strip(),'3')

    def test_release_package_includes_shared_launcher_and_notices(self):
        if not (BASE/'plugin.json').exists():self.skipTest('source only')
        names={x.relative_to(BASE).as_posix() for x in build_release.source_files()}
        self.assertTrue({'scripts/Find-GuardianPython.ps1','THIRD_PARTY_NOTICES.md','SUPPORT.md','SECURITY.md','tools/native_pack_cases.py'}<=names)


class ReleaseGateTests(unittest.TestCase):
    def test_stable_claim_cannot_be_authorized_by_json(self):
        from tools.guardian_release_gate import inspect
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'.codex-plugin').mkdir()
            (root/'VERSION').write_text('2.2.0')
            for f in ('plugin.json','.codex-plugin/plugin.json'):(root/f).write_text('{"version":"2.2.0"}')
            with self.assertRaisesRegex(ValueError,'Stable promotion'):
                inspect(root,stable_record={'approved':True,'model_claim':'all gates passed'})

    def test_public_summary_drops_sessions_prompts_and_paths(self):
        from tools.native_public_summary import public_summary
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'summary.json'
            path.write_text(json.dumps({'expected':39,'verified':39,'exit_code':0,'protected_fixtures_unchanged':True,'root_session':'PRIVATE','final':'SECRET'}))
            public=public_summary(path)
            self.assertTrue(public['all_native_roles_verified'])
            self.assertNotIn('PRIVATE',json.dumps(public));self.assertNotIn('SECRET',json.dumps(public))


class ExternalReleaseGateTests(unittest.TestCase):
    def test_forged_successful_checks_on_different_revision_are_rejected(self):
        from tools.guardian_release_gate import verify_external
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as t:
            artifact=Path(t)/'artifact.zip';artifact.write_bytes(b'zip')
            with patch('tools.guardian_release_gate._api',return_value={'head_sha':'b'*40,'status':'completed','conclusion':'success','path':'.github/workflows/ci.yml'}):
                with self.assertRaisesRegex(ValueError,'wrong revision'):
                    verify_external('owner/repo','a'*40,artifact,1,2,3,4)

    def test_matching_external_jobs_human_review_and_attestation_all_required(self):
        from tools.guardian_release_gate import verify_external
        from unittest.mock import patch
        import subprocess
        sha='a'*40
        def api(path):
            if '/reviews?per_page=100&page=' in path:
                return [{'commit_id':sha,'author_association':'MEMBER','user':{'type':'User','login':'human-reviewer'},'state':'APPROVED'}]
            if '/pulls/' in path:return {'head':{'sha':sha},'draft':False,'user':{'login':'pr-author'}}
            if '/jobs?' in path:return {'jobs':[{'conclusion':'success'}]*9}
            workflow={1:'ci',2:'native-acceptance',3:'grader-acceptance'}[int(path.rsplit('/',1)[1])]
            return {'head_sha':sha,'status':'completed','conclusion':'success','path':'.github/workflows/'+workflow+'.yml'}
        with tempfile.TemporaryDirectory() as t:
            artifact=Path(t)/'artifact.zip';artifact.write_bytes(b'zip')
            with patch('tools.guardian_release_gate._api',side_effect=api),patch('tools.guardian_release_gate.subprocess.run',return_value=subprocess.CompletedProcess([],0,'[{"verified":true}]','')) as process:
                result=verify_external('owner/repo',sha,artifact,1,2,3,4)
            for reviews in (
                [{'commit_id':sha,'author_association':'OWNER','user':{'type':'User','login':'pr-author'},'state':'APPROVED'}],
                [{'commit_id':sha,'author_association':'MEMBER','user':{'type':'User','login':'human-reviewer'},'state':state} for state in ('CHANGES_REQUESTED','COMMENTED')],
                [{'commit_id':'b'*40,'author_association':'MEMBER','user':{'type':'User','login':'human-reviewer'},'state':'APPROVED'}],
            ):
                def rejected_api(path):
                    return reviews if '/reviews?' in path else api(path)
                with patch('tools.guardian_release_gate._api',side_effect=rejected_api):
                    with self.assertRaisesRegex(ValueError,'independent authorized human'):
                        verify_external('owner/repo',sha,artifact,1,2,3,4)
            self.assertTrue(result['external_checks_passed']);self.assertFalse(result['publication_authorized'])
            self.assertIn('--source-digest',process.call_args.args[0]);self.assertIn('--signer-workflow',process.call_args.args[0])
