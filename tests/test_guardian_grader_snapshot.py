"""Per-vector target snapshots: real AST validation, no host target execution."""
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools import guardian_grader_sandbox as sandbox


class Input(io.BytesIO):
    def close(self): pass


class Process:
    def __init__(self, timeout=False):
        self.stdin=Input(); self.stdout=io.BytesIO(b'{"kind":"value","value":1}')
        self.returncode=0; self.timeout=timeout
    def wait(self,**kwargs):
        if self.timeout:
            self.timeout=False
            raise subprocess.TimeoutExpired('docker',1)
        return self.returncode
    def poll(self): return self.returncode
    def kill(self): self.returncode=-9


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.workspace=Path(self.tmp.name).resolve()/'workspace'; self.workspace.mkdir(mode=0o700)
        self.target=self.workspace/'private_module.py'; self.target.write_bytes(b'def answer():\n    return 1\n')
        os.chmod(self.target,0o600)
        (self.workspace/'secret.txt').write_text('synthetic-do-not-mount')
        (self.workspace/'oracle.json').write_text('{"expected":99}')
        self.vector={'file':'private_module.py','function':'answer','args':[],
                     'expected':{'kind':'value','value':1}}
        self.backend={'binary':'docker-snapshot-test','image':'reviewed@sha256:'+'a'*64}

    def run_fake(self, *, during_start=None, validator=None, cleanup_fails=False, timeout=False):
        real_popen=subprocess.Popen; real_run=subprocess.run
        captured={}; process=Process(timeout=timeout)
        def popen(command,*args,**kwargs):
            if command[0]==sys.executable:
                return real_popen(command,*args,**kwargs) # isolated bounded AST helper only
            mount=command[command.index('--mount')+1]
            snapshot=Path(mount.removeprefix('type=bind,src=').removesuffix(',dst=/workspace,readonly'))
            captured.update(snapshot=snapshot,wrapper=snapshot.parent,mount=mount)
            self.assertEqual(list(snapshot.iterdir()),[snapshot/'target.py'])
            self.assertNotEqual(snapshot,self.workspace)
            self.assertEqual((snapshot/'target.py').read_bytes(),b'def answer():\n    return 1\n')
            if os.name!='nt':
                self.assertEqual(stat.S_IMODE(snapshot.stat().st_mode),0o555)
                self.assertEqual(stat.S_IMODE(snapshot.parent.stat().st_mode),0o700)
                self.assertEqual(stat.S_IMODE((snapshot/'target.py').stat().st_mode),0o444)
            if during_start: during_start(snapshot)
            return process
        def run(command,*args,**kwargs):
            if command[0]==sys.executable:
                return real_run(command,*args,**kwargs)
            self.assertEqual(command[1:3],['rm','--force'])
            self.assertTrue(captured['snapshot'].is_dir(),'Snapshot must remain until server cleanup')
            captured['cleanup_observed']=True
            return subprocess.CompletedProcess(command,1 if cleanup_fails else 0,'','cleanup refused' if cleanup_fails else '')
        with patch.object(sandbox.subprocess,'Popen',side_effect=popen),patch.object(sandbox.subprocess,'run',side_effect=run):
            if validator:
                with patch.object(sandbox,'validate_pure_target',side_effect=validator):
                    result=sandbox.execute_vector(self.workspace,self.vector,1,self.backend)
            else:
                result=sandbox.execute_vector(self.workspace,self.vector,1,self.backend)
        captured['request']=json.loads(process.stdin.getvalue())
        return result,captured

    def test_only_target_snapshot_is_mounted_and_original_hash_modes_preserved(self):
        original=self.target.read_bytes(); mode=stat.S_IMODE(self.target.stat().st_mode)
        workspace_mode=stat.S_IMODE(self.workspace.stat().st_mode)
        result,captured=self.run_fake()
        self.assertTrue(result); self.assertTrue(captured['cleanup_observed'])
        self.assertEqual(captured['request']['file'],'target.py')
        self.assertNotIn('expected',captured['request'])
        self.assertEqual(hashlib.sha256(self.target.read_bytes()).digest(),hashlib.sha256(original).digest())
        self.assertEqual(stat.S_IMODE(self.target.stat().st_mode),mode)
        self.assertEqual(stat.S_IMODE(self.workspace.stat().st_mode),workspace_mode)
        self.assertFalse(captured['wrapper'].exists())
        self.assertTrue((self.workspace/'secret.txt').is_file())

    def test_original_mutation_after_copy_cannot_replace_validated_mounted_bytes(self):
        validate=sandbox.validate_pure_target; validated=[]
        def validator(path):
            self.target.write_text('import os\nos._exit(0)\n')
            validate(path); validated.append(path)
        result,captured=self.run_fake(validator=validator)
        self.assertTrue(result); self.assertEqual(validated,[captured['snapshot']/'target.py'])
        self.assertEqual(self.target.read_text(),'import os\nos._exit(0)\n')

    def test_timeout_cleans_server_before_snapshot(self):
        result,captured=self.run_fake(timeout=True)
        self.assertFalse(result); self.assertTrue(captured['cleanup_observed'])
        self.assertFalse(captured['wrapper'].exists())

    def test_uncertain_server_cleanup_stops_and_preserves_private_snapshot(self):
        # Record just this owned test snapshot so the test can remove it after
        # asserting production code correctly refuses deletion on uncertainty.
        staged=[]; original=sandbox._stage_target
        def stage(*args):
            result=original(*args); staged.append(result[0]); return result
        try:
            with patch.object(sandbox,'_stage_target',side_effect=stage):
                with self.assertRaises(sandbox.SandboxUnavailable): self.run_fake(cleanup_fails=True)
            self.assertEqual(len(staged),1); self.assertTrue(staged[0].is_dir())
        finally:
            for root in staged:
                if root.exists(): sandbox._remove_snapshot(root)

    def test_oversize_invalid_paths_and_nonregular_targets_fail_before_container(self):
        with patch.object(sandbox,'container_command') as docker:
            for name in ('../secret.py','/secret.py','folder/file.py','C:secret.py','bad\\file.py'):
                self.assertFalse(sandbox.execute_vector(self.workspace,self.vector|{'file':name},1,self.backend))
            self.target.write_bytes(b'#'*(sandbox.MAX_SOURCE_BYTES+1))
            self.assertFalse(sandbox.execute_vector(self.workspace,self.vector,1,self.backend))
            self.target.unlink(); self.target.mkdir()
            self.assertFalse(sandbox.execute_vector(self.workspace,self.vector,1,self.backend))
            docker.assert_not_called()

    def test_invalid_ast_snapshot_is_cleaned_without_mounting(self):
        self.target.write_text('import os\nos._exit(0)\n')
        roots=[]; original=tempfile.mkdtemp
        def temp(*args,**kwargs):
            result=original(*args,**kwargs); roots.append(Path(result)); return result
        with patch.object(tempfile,'mkdtemp',side_effect=temp),patch.object(sandbox,'container_command') as docker:
            self.assertFalse(sandbox.execute_vector(self.workspace,self.vector,1,self.backend))
            docker.assert_not_called()
        self.assertTrue(roots); self.assertTrue(all(not root.exists() for root in roots))

    def test_linked_target_is_not_followed(self):
        self.target.unlink()
        try: self.target.symlink_to(self.workspace/'secret.txt')
        except OSError: self.skipTest('Symlinks unavailable')
        with patch.object(sandbox,'container_command') as docker:
            self.assertFalse(sandbox.execute_vector(self.workspace,self.vector,1,self.backend)); docker.assert_not_called()

    def test_real_backend_reads_target_from_private_posix_workspace(self):
        if os.name=='nt': self.skipTest('Native POSIX permissions acceptance requires Linux rootless backend')
        backend=sandbox.probe()
        if not backend['available']: self.skipTest('NOT VERIFIED: rootless digest-pinned backend unavailable')
        before=self.target.read_bytes(); mode=stat.S_IMODE(self.workspace.stat().st_mode)
        self.assertEqual(mode,0o700)
        self.assertTrue(sandbox.execute_vector(self.workspace,self.vector,5,backend))
        self.assertEqual(before,self.target.read_bytes()); self.assertEqual(stat.S_IMODE(self.workspace.stat().st_mode),mode)


if __name__=='__main__': unittest.main()
