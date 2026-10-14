import tempfile, unittest
from unittest.mock import patch
from test_guardian import guardian as g

class RoutingReleaseTests(unittest.TestCase):
    def test_english_sensitive_task(self):
        r=g.route('Implement account balance transfer transaction with authorization and duplicate retries')
        self.assertEqual(r['risk'],'high')
        self.assertTrue({'S10','S11','S14','G01'}<={a['id'] for a in r['agents']})
    def test_explicit_no_release_excludes_release_workers(self):
        r=g.route('Audit invoice authorization and concurrent duplicate charges; no release or production actions')
        ids={a['id'] for a in r['agents']}
        self.assertTrue({'S10','S14','G01'}<=ids);self.assertNotIn('G02',ids)
    def test_malformed_architecture_profile(self):
        with tempfile.TemporaryDirectory() as t:
            for p in ([],{'dimensions':[]},{'dimensions':{'business_criticality':None}}):
                with self.assertRaises(ValueError):g.assess(t,p)
    def test_invalid_capability_severity_blocks(self):
        r=g.audit_template('.');r['capabilities'][0]['severity']='invalid'
        self.assertEqual(g.gate(r)['decision'],'BLOCKED')
    def test_no_taxonomy_self_review(self):
        for c in g.load('taxonomy-v3.json')['capabilities']:self.assertNotIn(c['primary'],c['reviewers'])
    def test_inventory_reparse_filter(self):
        import stat
        from types import SimpleNamespace
        with patch('pathlib.Path.lstat',return_value=SimpleNamespace(st_mode=stat.S_IFDIR,st_file_attributes=0x400)):
            self.assertTrue(g.is_link_or_reparse('synthetic-path'))
