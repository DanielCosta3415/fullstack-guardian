"""Real local supervisor checks/integration; mock only model CLI, no quota/network."""
import json
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from tools.guardian_executor import initialize, execute, status, _read_retry_delay
from tools.guardian_platform import create_plan
from tools.guardian_policy import Grant, authorize_action
from tools.guardian_trace import init, append, verify as trace_verify, expire, privacy_acl, TraceError
from tools.guardian_workflow import check, review, verify, inspect, WorkflowError, _run
from tools.guardian_integrate import integrate, IntegrationError


def git(root,*args):
    subprocess.run(['git','-C',str(root),*args],capture_output=True,check=True,timeout=20)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name).resolve(); self.repo=self.root/'repo'; self.home=self.root/'state'
        self.repo.mkdir(); git(self.repo,'init','-q')
        (self.repo/'value.txt').write_text('before\n'); git(self.repo,'add','.')
        git(self.repo,'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-q','-m','base')
        self.plan=create_plan('Corrigir service ASP.NET Core do backend')
        for task in self.plan['tasks']:
            task['contract'].update(operation='write',allowed_paths=['value.txt'],checks=[[sys.executable,'-B','-c',"from pathlib import Path; assert Path('value.txt').read_text() == 'after\\n'"]],idempotent=False)
        initialize(self.plan,self.repo,self.home,briefs={t['id']:'Perform only the bounded explicit local fixture change and retain evidence.' for t in self.plan['tasks']})
        def fake(codex,slot,prompt,timeout,logs,mode):
            logs.parent.mkdir(parents=True,exist_ok=True); logs.write_text('{"type":"turn.completed"}\n')
            (slot/'value.txt').write_text('after\n'); return 0,True,None
        with patch('tools.guardian_executor._process',side_effect=fake):
            execute(self.home,apply=True,codex_binary=sys.executable,authorize_writes=True)
        self.grant=Grant(str(self.repo),frozenset({'local_check','review'}),(str(self.home),),time.time()+120,'human_session')
        self.checks={t['id']:t['contract']['checks'] for t in self.plan['tasks']}

    def checked(self):
        return check(self.home,approved_checks=self.checks,grant=self.grant)

    def reviewed(self):
        self.checked(); evidence=self.home/'independent-review.txt'; evidence.write_text('Reviewer inspected fixture diff and trusted check output; accepts this bounded change.')
        return review(self.home,reviewer='reviewer',producer='implementer',evidence=evidence,grant=self.grant)

    def test_real_checks_review_verify_and_exact_patch_integration(self):
        self.assertEqual(self.reviewed()['state'],'reviewed')
        self.assertEqual(verify(self.home)['state'],'verified')
        self.assertEqual(status(self.home)['supervisor_acceptance'],'verified')
        report=integrate(self.home)
        result=integrate(self.home,apply=True,confirm_sha256=report['patch_sha256'])
        self.assertTrue(result['applied']); self.assertEqual(inspect(self.home)['state'],'integrated')
        self.assertEqual((self.repo/'value.txt').read_text(),'after\n')
        self.assertFalse(inspect(self.home)['review']['identity_authenticated'])

    def test_contract_commands_never_authorize_execution(self):
        with self.assertRaisesRegex(WorkflowError,'trusted scoped'):
            check(self.home,approved_checks=self.checks,grant={'actions':['local_check']})
        self.assertFalse((self.home/'workflow.json').exists())

    def test_missing_or_changed_operator_approved_checks_rejected(self):
        with self.assertRaises(WorkflowError): check(self.home,approved_checks={},grant=self.grant)
        checks={k:[[sys.executable,'-V']] for k in self.checks}
        with self.assertRaises(WorkflowError): check(self.home,approved_checks=checks,grant=self.grant)

    def test_verified_cannot_be_claimed_without_review(self):
        self.checked()
        with self.assertRaises(WorkflowError): verify(self.home)
        with self.assertRaises(IntegrationError): integrate(self.home)

    def test_changed_check_output_and_forged_workflow_rejected(self):
        self.checked(); record=inspect(self.home)
        (self.home/record['checks'][0]['log']).write_text('tampered')
        with self.assertRaises(WorkflowError): inspect(self.home)
        path=self.home/'workflow.json'; content=json.loads(path.read_text()); content['state']='verified'; path.write_text(json.dumps(content))
        with self.assertRaisesRegex(WorkflowError,'checkpoint'): inspect(self.home)

    def test_same_reviewer_and_modified_review_rejected(self):
        self.checked(); evidence=self.home/'review.txt'; evidence.write_text('review')
        with self.assertRaises(WorkflowError): review(self.home,reviewer='same',producer='same',evidence=evidence,grant=self.grant)
        review(self.home,reviewer='other',producer='same',evidence=evidence,grant=self.grant)
        evidence.write_text('changed')
        with self.assertRaises(WorkflowError): verify(self.home)

    def test_expired_cross_action_grants_fail(self):
        grant=Grant(str(self.repo),frozenset({'local_write'}),(str(self.home),),time.time()+60,'human_session')
        self.assertFalse(authorize_action('local_check',self.repo,self.home,grant)['allowed'])
        expired=Grant(str(self.repo),frozenset({'local_check'}),(str(self.home),),1,'human_session')
        with self.assertRaises(WorkflowError): check(self.home,approved_checks=self.checks,grant=expired)

    def test_check_mutation_blocks_without_automatic_replay(self):
        def mutate(argv,cwd,log,timeout,max_bytes):
            log.parent.mkdir(parents=True,exist_ok=True); log.write_text('mock check')
            (cwd/'value.txt').write_text('unapproved mutation'); return 0
        with patch('tools.guardian_workflow._run',side_effect=mutate),self.assertRaises(WorkflowError): self.checked()
        self.assertEqual(json.loads((self.home/'workflow.json').read_text())['state'],'blocked')

    def test_checkpoint_journal_has_no_prompts_paths_or_thread_identifiers(self):
        lines=(self.home/'journal.jsonl').read_text(); self.assertNotIn(str(self.repo),lines)
        self.assertNotIn('task brief',lines); self.assertNotIn('thread_id',lines)
        self.assertGreater(trace_verify(self.home/'journal.jsonl')['events'],2)

    def test_malformed_workflow_load_releases_execution_lock(self):
        (self.home/'workflow.json').write_text('{')
        with self.assertRaises(ValueError): self.checked()
        self.assertFalse((self.home/'.lock').exists())
        (self.home/'workflow.json').unlink()
        self.assertEqual(self.checked()['state'],'checked')


class RetentionAndRetryTests(unittest.TestCase):
    def test_supervisor_check_real_output_and_timeout_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()
            with self.assertRaisesRegex(WorkflowError,'budget'):
                _run([sys.executable,'-B','-c',"print('x'*100000)"],root,root/'output.log',5,1024)
            self.assertLessEqual((root/'output.log').stat().st_size,1024)
            with self.assertRaisesRegex(WorkflowError,'timeout'):
                _run([sys.executable,'-B','-c','import time; time.sleep(30)'],root,root/'timeout.log',1,1024)

    def test_read_retry_is_bounded_backoff_and_uncertain_failures_never_replay(self):
        contract={'operation':'read','idempotent':True,'retry':2}
        self.assertEqual(_read_retry_delay(contract,1,False,0),.25)
        self.assertEqual(_read_retry_delay(contract,1,False,1),.5)
        for code in ['timeout','output_budget_exceeded',0]:
            self.assertIsNone(_read_retry_delay(contract,code,False,0))
        self.assertIsNone(_read_retry_delay(contract,1,False,2))
        self.assertIsNone(_read_retry_delay(contract|{'operation':'write'},1,False,0))

    def test_retention_requires_finished_expired_exact_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp).resolve()/'journal.jsonl'; init(path)
            later=datetime.now(timezone.utc)+timedelta(days=40)
            self.assertFalse(expire(path,retention_days=30,now=later)['eligible'])
            valid=append(path,'finish',{'status':'closed'})
            self.assertTrue(expire(path,retention_days=30,now=later)['eligible'])
            (path.parent/'.lock').write_text('running or uncertain')
            with self.assertRaisesRegex(TraceError,'Execution lock'): expire(path,retention_days=30,now=later)
            (path.parent/'.lock').unlink()
            with self.assertRaises(TraceError): expire(path,retention_days=30,now=later,apply=True,confirm_checksum='0'*64)
            self.assertTrue(path.exists())
            result=expire(path,retention_days=30,now=later,apply=True,confirm_checksum=valid['last_checksum'])
            self.assertTrue(result['deleted']); self.assertFalse(path.exists())

    def test_acl_probe_never_claims_authentication_or_changes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp).resolve()/'journal.jsonl'; init(path); before=path.read_bytes()
            result=privacy_acl(path)
            self.assertIs(type(result['verified']),bool); self.assertEqual(before,path.read_bytes())


if __name__=='__main__': unittest.main()
