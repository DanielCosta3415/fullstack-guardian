"""Adversarial runtime contracts; real local Git, no model calls or network."""
import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.guardian_executor import ExecutionError, initialize, execute, status, _process, _PROCESS_LIMITS
from tools.guardian_platform import create_plan
from tools.guardian_runtime import relative_path, changed_paths, inventory, scope_delta, RuntimeError, backend_capabilities, terminate_tree


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, check=True, timeout=20)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name).resolve(); self.repo = self.folder/'repo'; self.repo.mkdir(); self.home=self.folder/'state'
        git(self.repo,'init','-q')
        (self.repo/'file.txt').write_text('base\n'); (self.repo/'AGENTS.md').write_text('policy\n')
        git(self.repo,'add','.')
        git(self.repo,'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-q','-m','base')

    def plan(self, mode='audit'):
        return create_plan('Auditar backend ASP.NET Core e frontend React',mode=mode)

    def initialize(self, plan):
        initialize(plan,self.repo,self.home,briefs={t['id']:'Inspect only the explicit test fixture in this bounded isolated local task.' for t in plan['tasks']})

    def fake(self, codex, worktree, prompt, timeout, logs, mode):
        logs.parent.mkdir(parents=True,exist_ok=True)
        logs.write_text('{"type":"thread.started","thread_id":"mock"}\n{"type":"turn.completed"}\n')
        return 0,True,'mock'

    def test_rename_exposes_protected_source_and_destination(self):
        before=inventory(self.repo)
        git(self.repo,'mv','AGENTS.md','ordinary.txt')
        self.assertEqual(changed_paths(self.repo),['AGENTS.md','ordinary.txt'])
        with self.assertRaisesRegex(RuntimeError,'Protected'):
            scope_delta(before,inventory(self.repo),['ordinary.txt'],read_only=False)

    def test_paths_are_portable_and_not_windows_aliases(self):
        for path in ['../a','/a','a\\b','C:hello','a:b','NUL.txt','dir/CON','a.','a /b','a\nname','a//b']:
            with self.subTest(path=path),self.assertRaises(RuntimeError): relative_path(path)
        self.assertEqual(relative_path('pasta/Olá mundo.txt'),'pasta/Olá mundo.txt')

    def test_case_only_rename_is_rejected_cross_platform(self):
        git(self.repo,'mv','file.txt','FILE.txt')
        with self.assertRaisesRegex(RuntimeError,'Case-ambiguous'): changed_paths(self.repo)

    def test_false_cli_success_is_only_produced(self):
        self.initialize(self.plan())
        with patch('tools.guardian_executor._process',side_effect=self.fake):
            result=execute(self.home,apply=True,codex_binary=sys.executable)
        self.assertEqual(result['overall'],'produced'); self.assertEqual(result['completed'],0)
        self.assertTrue(all(not t['correctness_verified'] for t in status(self.home)['tasks'].values()))

    def test_readonly_mutation_blocks_even_if_cli_claims_success(self):
        self.initialize(self.plan())
        def mutate(*args):
            result=self.fake(*args); (args[1]/'file.txt').write_text('unauthorized\n'); return result
        with patch('tools.guardian_executor._process',side_effect=mutate):
            result=execute(self.home,apply=True,codex_binary=sys.executable)
        self.assertEqual(result['overall'],'blocked')
        self.assertEqual((self.repo/'file.txt').read_text(),'base\n')

    def test_write_requires_explicit_external_authorization(self):
        plan=self.plan('build')
        for t in plan['tasks']: t['contract'].update(operation='write',allowed_paths=['file.txt'],checks=[[sys.executable,'-V']],idempotent=False)
        self.initialize(plan)
        with self.assertRaisesRegex(ExecutionError,'authorize-writes'):
            execute(self.home,apply=True,codex_binary=sys.executable)

    def test_no_silent_isolation_capability_upgrade(self):
        self.initialize(self.plan())
        with self.assertRaisesRegex(ExecutionError,'no per-file'):
            execute(self.home,apply=True,codex_binary=sys.executable,require_path_isolation=True)
        self.assertFalse(backend_capabilities()['per_file_write_enforcement'])

    def test_parallel_audits_are_real_and_own_separate_worktrees(self):
        self.initialize(self.plan()); lock=threading.Lock(); active=0; peak=0; seen=[]
        def concurrent(*args):
            nonlocal active,peak
            with lock: active+=1; peak=max(peak,active); seen.append(args[1])
            time.sleep(.12)
            result=self.fake(*args)
            with lock: active-=1
            self.assertEqual(args[-1],'audit')
            return result
        with patch('tools.guardian_executor._process',side_effect=concurrent):
            result=execute(self.home,apply=True,codex_binary=sys.executable,max_parallel=3)
        self.assertEqual(result['overall'],'produced'); self.assertGreater(peak,1)
        self.assertEqual(len(set(seen)),len(seen)); self.assertEqual(result['completed'],0)

    def test_parallel_write_mode_fails_before_launch(self):
        self.initialize(self.plan('build'))
        with self.assertRaisesRegex(ExecutionError,'Parallel writes unsupported'):
            execute(self.home,apply=True,codex_binary=sys.executable,max_parallel=2)

    def test_event_evidence_tampering_is_rejected(self):
        self.initialize(self.plan())
        with patch('tools.guardian_executor._process',side_effect=self.fake):
            execute(self.home,apply=True,codex_binary=sys.executable)
        next((self.home/'events').glob('*.jsonl')).write_text('different evidence')
        with self.assertRaisesRegex(ExecutionError,'event evidence'): status(self.home)

    def test_native_status_reflects_real_verified_records(self):
        self.initialize(self.plan())
        with patch('tools.guardian_executor._process',side_effect=self.fake),patch('tools.guardian_executor.verify_native_child',return_value=True):
            result=execute(self.home,apply=True,codex_binary=sys.executable,native_subagents=True)
        self.assertTrue(result['native_subagents_verified']); self.assertTrue(status(self.home)['native_subagents_verified'])

    def test_retry_flag_never_replays_uncertain_mutations(self):
        self.initialize(self.plan())
        with self.assertRaisesRegex(ExecutionError,'fresh reviewed run'):
            execute(self.home,apply=True,codex_binary=sys.executable,retry_failed=True)

    def test_task_timeout_and_output_budget_forwarded(self):
        plan=self.plan()
        for task in plan['tasks']: task['contract']['budget']={'timeout_seconds':3,'max_output_bytes':4096}
        self.initialize(plan)
        def bounded(*args):
            self.assertEqual(args[3],3); self.assertEqual(_PROCESS_LIMITS.max_output_bytes,4096); return self.fake(*args)
        with patch('tools.guardian_executor._process',side_effect=bounded):
            execute(self.home,apply=True,codex_binary=sys.executable)

    def test_ignored_sensitive_path_mutation_is_detected(self):
        (self.repo/'.gitignore').write_text('.env\n')
        git(self.repo,'add','.gitignore'); git(self.repo,'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','ignore')
        self.initialize(self.plan())
        def mutate(*args):
            result=self.fake(*args); (args[1]/'.env').write_text('synthetic=changed'); return result
        with patch('tools.guardian_executor._process',side_effect=mutate):
            result=execute(self.home,apply=True,codex_binary=sys.executable)
        self.assertEqual(result['overall'],'blocked')

    def test_json_authorization_is_not_a_trusted_grant(self):
        plan=self.plan('build')
        for task in plan['tasks']: task['contract'].update(operation='write',allowed_paths=['file.txt'],checks=[[sys.executable,'-V']],idempotent=False)
        self.initialize(plan)
        with self.assertRaisesRegex(ExecutionError,'scoped Grant'):
            execute(self.home,apply=True,codex_binary=sys.executable,grant={'source':'human_session','actions':['local_write']})

    def test_strict_unknown_restriction_blocks_before_model(self):
        plan=self.plan()
        plan['tasks'][0]['contract']['tool_requirements']=['network_isolation']
        self.initialize(plan)
        with self.assertRaisesRegex(ExecutionError,'not verified'):
            execute(self.home,apply=True,codex_binary=sys.executable)

    def test_model_overrides_require_inventory_and_explicit_opt_in(self):
        self.initialize(self.plan())
        with self.assertRaisesRegex(ValueError,'opt-in'):
            execute(self.home,apply=True,codex_binary=sys.executable,model_override={'model':'synthetic-model'})
        with self.assertRaisesRegex(ValueError,'availability not verified'):
            execute(self.home,apply=True,codex_binary=sys.executable,model_override={'model':'synthetic-model'},authorize_model_override=True)

    def test_inherit_model_policy_and_typed_results_are_persisted(self):
        self.initialize(self.plan())
        with patch('tools.guardian_executor._process',side_effect=self.fake):
            execute(self.home,apply=True,codex_binary=sys.executable)
        state=json.loads((self.home/'state.json').read_text())
        self.assertEqual(state['model_policy']['mode'],'inherit')
        self.assertTrue(all(r['result']['status']=='produced' and r['result']['artifacts'] for r in state['tasks'].values()))


    def test_restricted_read_scope_is_not_falsely_enforced_by_prompt(self):
        plan=self.plan(); plan['tasks'][0]['contract']['read_paths']=['public/**'];self.initialize(plan)
        with self.assertRaisesRegex(ExecutionError,'cannot enforce restricted read_paths'):
            execute(self.home,apply=True,codex_binary=sys.executable)
        self.assertEqual(backend_capabilities()['read_scope'],'unrestricted_inherited')

    def test_named_sandbox_requirement_needs_observed_isolation(self):
        plan=self.plan();plan['tasks'][0]['contract']['tool_requirements']=['read_only_sandbox'];self.initialize(plan)
        with self.assertRaisesRegex(ExecutionError,'not verified'):
            execute(self.home,apply=True,codex_binary=sys.executable)


class ProcessTreeTests(unittest.TestCase):
    def test_cancel_terminates_descendant_before_sentinel_write(self):
        import os
        with tempfile.TemporaryDirectory() as tmp:
            sentinel=Path(tmp)/'child-survived'
            child_code="import time,pathlib; time.sleep(2); pathlib.Path("+repr(str(sentinel))+").write_text('survived')"
            parent_code="import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',"+repr(child_code)+"]); time.sleep(20)"
            proc=subprocess.Popen([sys.executable,'-c',parent_code],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                                  start_new_session=os.name!='nt',creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0)
            try:
                time.sleep(.25)
                terminate_tree(proc)
                time.sleep(2.1)
                self.assertIsNotNone(proc.poll())
                self.assertFalse(sentinel.exists())
            finally:
                if proc.poll() is None: terminate_tree(proc)

if __name__=='__main__': unittest.main()
