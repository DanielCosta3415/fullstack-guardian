import unittest
from tools.guardian_grader_sandbox import image_identity

class ImageIdentityTests(unittest.TestCase):
    def test_docker_short_repo_digest_keeps_exact_content_and_registry(self):
        digest='@sha256:'+'a'*64
        expected='docker.io/library/python'+digest
        for name in ('python','library/python','docker.io/library/python','index.docker.io/library/python','python:3.12'):
            self.assertEqual(image_identity(name+digest),expected)
        self.assertNotEqual(image_identity('other.registry/python'+digest),expected)
        self.assertNotEqual(image_identity('python@sha256:'+'b'*64),expected)
        for invalid in ('python:latest','--privileged'+digest,'python@sha256:'+'z'*64):
            self.assertIsNone(image_identity(invalid))
