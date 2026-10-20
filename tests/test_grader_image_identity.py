import unittest
import subprocess
from unittest.mock import patch
from tools.guardian_grader_sandbox import image_identity

class ImageIdentityTests(unittest.TestCase):
    def test_rootless_without_builtin_seccomp_cannot_start_preflight(self):
        from tools.guardian_grader_sandbox import probe
        for options in ('["name=rootless"]', '["name=rootless","name=seccomp,profile=unconfined"]'):
            with patch('tools.guardian_grader_sandbox.shutil.which',return_value='docker'), patch(
                'tools.guardian_grader_sandbox.subprocess.run',return_value=subprocess.CompletedProcess([],0,options,'')) as run:
                self.assertFalse(probe('python@sha256:'+'a'*64)['available'])
                self.assertEqual(run.call_count,1)

    def test_docker_short_repo_digest_keeps_exact_content_and_registry(self):
        digest='@sha256:'+'a'*64
        expected='docker.io/library/python'+digest
        for name in ('python','library/python','docker.io/library/python','index.docker.io/library/python','python:3.12'):
            self.assertEqual(image_identity(name+digest),expected)
        self.assertNotEqual(image_identity('other.registry/python'+digest),expected)
        self.assertNotEqual(image_identity('python@sha256:'+'b'*64),expected)
        for invalid in ('python:latest','--privileged'+digest,'python@sha256:'+'z'*64):
            self.assertIsNone(image_identity(invalid))
