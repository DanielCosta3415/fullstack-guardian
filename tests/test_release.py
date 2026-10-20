import hashlib, importlib.util, json, tempfile, unittest, zipfile
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('guardian_release_builder',BASE/'tools/build_release.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

class ReleaseTests(unittest.TestCase):
    def test_plugin_onboarding_and_marketplace(self):
        if not (BASE/'plugin.json').exists():self.skipTest('Source-package metadata only')
        m=json.loads((BASE/'plugin.json').read_text(encoding='utf8'))
        self.assertEqual(m['version'],(BASE/'VERSION').read_text().strip())
        fallback=json.loads((BASE/'.codex-plugin/plugin.json').read_text(encoding='utf8'))
        self.assertEqual(fallback['version'],m['version'])
        setup=m['extensions']['com.openai']['onboardingSkill']
        self.assertTrue((BASE/setup.removeprefix('./')).is_file())
        market=json.loads((BASE/'.agents/plugins/marketplace.json').read_text())
        self.assertEqual(market['plugins'][0]['source']['path'],'./')
        self.assertEqual(len(list((BASE/'skills').glob('*/SKILL.md'))),1)
    def test_archive_integrity_and_reproducibility(self):
        if not (BASE/'plugin.json').exists():self.skipTest('Source-package metadata only')
        with tempfile.TemporaryDirectory() as t:
            first=builder.build(Path(t)/'a');second=builder.build(Path(t)/'b')
            self.assertEqual(first['sha256'],second['sha256'])
            with zipfile.ZipFile(first['archive']) as z:
                manifest=json.loads(z.read('fullstack-guardian-'+first['version']+'/MANIFEST.sha256.json'))
                for entry in manifest['files']:
                    data=z.read('fullstack-guardian-'+first['version']+'/'+entry['path'])
                    self.assertEqual(hashlib.sha256(data).hexdigest(),entry['sha256'])
                self.assertFalse(any('__pycache__' in x or '/.git/' in x for x in z.namelist()))
    def test_platform_preview_is_not_mislabeled_stable_release(self):
        if not (BASE/'plugin.json').exists():self.skipTest('Source-package metadata only')
        version=(BASE/'VERSION').read_text(encoding='utf8').strip()
        self.assertNotEqual(version,'2.1.0','Experimental platform must not reuse stable release version')
        self.assertIn('-dev.',version)
        manifest=json.loads((BASE/'plugin.json').read_text(encoding='utf8'))
        self.assertEqual(manifest['version'],version)

    def test_release_attestation_is_pinned_and_fail_closed(self):
        if not (BASE/'.github/workflows/release.yml').exists():self.skipTest('Source-package metadata only')
        workflow=(BASE/'.github/workflows/release.yml').read_text(encoding='utf8')
        self.assertIn('id-token: write',workflow)
        self.assertIn('attestations: write',workflow)
        self.assertRegex(workflow,r'actions/attest-build-provenance@[0-9a-f]{40}')
        self.assertIn('gh attestation verify',workflow)
        self.assertLess(workflow.index('gh attestation verify'),
                        workflow.index('actions/upload-artifact'))

    def test_portability_no_personal_home_in_distribution(self):
        for p in builder.source_files():
            if p.suffix in ('.md','.py','.json','.toml','.ps1','.sh','.yml'):
                text=p.read_text(encoding='utf8')
                self.assertNotRegex(text,r'(?i)[A-Z]:[/\\]+Users[/\\]+[a-z0-9_-]+')
