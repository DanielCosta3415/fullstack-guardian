import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.guardian import inspect_project, route
from tools.guardian_platform import create_plan


class InventoryResponsibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'main.py').write_text('print("stdlib only")\n', encoding='utf8')

    def add(self, name):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('synthetic', encoding='utf8')

    def test_stdlib_python_without_manifest(self):
        result = inspect_project(self.root)
        self.assertIn('Python', result['technologies'])
        self.assertIn('backend', result['tags'])
        self.assertEqual(result['architecture_as_is_heuristic']['confidence'], 'low')
        self.assertEqual(result['criticality'], 'unknown')

    def test_dotnet_fixture_does_not_change_product_technology_or_worker_choice(self):
        before = inspect_project(self.root)
        workers_before = [a['id'] for a in route('Corrigir comportamento local', before)['agents']]
        self.add('tests/fixtures/dotnet/demo.csproj')
        after = inspect_project(self.root)
        self.assertNotIn('.NET / C#', after['technologies'])
        self.assertEqual(workers_before, [a['id'] for a in route('Corrigir comportamento local', after)['agents']])
        self.assertEqual(after['architecture_as_is_heuristic']['inventory_responsibilities']['fixtures'], 1)
        self.assertIn('.csproj', after['architecture_as_is_heuristic']['excluded_stack_signals'])

    def test_examples_docs_and_generated_do_not_promote_stack_or_complexity(self):
        before = inspect_project(self.root)
        for name in ('examples/web/App.tsx', 'samples/cloud/main.tf',
                     'docs/sdk/service.csproj', 'generated/Model.g.cs',
                     'tests/frontend/widget.test.ts', 'test_entry.py'):
            self.add(name)
        after = inspect_project(self.root)
        self.assertEqual(after['architecture_as_is_heuristic']['score'], before['architecture_as_is_heuristic']['score'])
        self.assertFalse({'frontend', 'cloud'} & set(after['tags']))
        self.assertIn('Test artifacts', after['technologies'])

    def test_real_multistack_product_is_retained_with_uncertainty(self):
        self.add('server/app.csproj')
        self.add('web/App.tsx')
        result = inspect_project(self.root)
        self.assertTrue({'Python', '.NET / C#', 'JSX/React compatible'} <= set(result['technologies']))
        self.assertEqual(result['architecture_as_is_heuristic']['confidence'], 'low')
        self.assertTrue(result['unknowns'])

    def test_hyphenated_evaluation_fixture_roots_do_not_promote_dotnet(self):
        for name in ('eval/domain-fixtures/dotnet/Fixture.csproj',
                     'eval/stack-fixtures/dotnet/GuardianStack.csproj',
                     'eval/stack-fixtures/node/package.json'):
            self.add(name)
        result = inspect_project(self.root)
        self.assertIn('Python', result['technologies'])
        self.assertNotIn('.NET / C#', result['technologies'])
        self.assertNotIn('Node.js ecosystem', result['technologies'])
        self.assertEqual(result['architecture_as_is_heuristic']['inventory_responsibilities']['fixtures'], 3)

    def test_disposable_work_is_generated_and_checkpoint_is_not_scanned(self):
        self.add('work/stack-run/dotnet/GuardianStack.csproj')
        self.add('work/stack-run/node/package.json')
        self.add('.guardian-state/private-evidence/DoNotScan.csproj')
        result = inspect_project(self.root)
        self.assertEqual(result['files_scanned'], 3)
        self.assertNotIn('.NET / C#', result['technologies'])
        self.assertNotIn('Node.js ecosystem', result['technologies'])
        self.assertEqual(result['architecture_as_is_heuristic']['inventory_responsibilities']['generated'], 2)

    def test_platform_exact_inventory_schema_remains_compatible(self):
        inventory = inspect_project(self.root)
        result = create_plan('Correct a local behavior', project=self.root,
                             mode='build', _inventory=inventory)
        self.assertTrue(result['tasks'])

    def test_fixture_payload_is_not_read_or_executed(self):
        marker = self.root / 'should-not-exist'
        path = self.root / 'tests/fixtures/exploit.py'
        path.parent.mkdir(parents=True)
        path.write_text('raise RuntimeError("scanner must never execute")', encoding='utf8')
        with patch.object(Path, 'read_text', side_effect=AssertionError('Filename discovery must not read payloads')), \
             patch.object(Path, 'read_bytes', side_effect=AssertionError('Filename discovery must not read payloads')):
            inspect_project(self.root)
        self.assertFalse(marker.exists())


if __name__ == '__main__':
    unittest.main()
