"""Professional names remain presentation-only and consistent across outputs."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.generate_catalog_docs import ROOT, render, role_display_names


class RoleDisplayNamesTests(unittest.TestCase):
    def setUp(self):
        self.records=json.loads((ROOT/'core/contracts-catalog-v1.json').read_text(encoding='utf8'))['records']
        self.metadata=json.loads((ROOT/'core/agents.json').read_text(encoding='utf8'))
        self.names=json.loads((ROOT/'core/role-display-names-v1.json').read_text(encoding='utf8'))

    def fixture(self, document):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        (root/'core').mkdir()
        (root/'core/role-display-names-v1.json').write_text(json.dumps(document),encoding='utf8')
        (root/'core/agents.json').write_text(json.dumps(self.metadata),encoding='utf8')
        return root

    def test_all_39_titles_match_core_and_optional_profiles(self):
        names=role_display_names(self.records)
        self.assertEqual(len(names),39)
        self.assertEqual(sum(r['kind']=='core' for r in self.records),29)
        self.assertEqual(sum(r['kind']=='optional' for r in self.records),10)
        self.assertEqual(names['guardian_engineering_orchestrator'],'Orquestrador de Engenharia')
        self.assertEqual(names['guardian_independent_auditor'],'Auditor Independente')

    def test_generated_catalog_includes_each_professional_name(self):
        text=render()
        for name,title in self.names['roles'].items():
            self.assertIn('| '+name+' | '+title+' |',text)

    def test_missing_or_unknown_role_cannot_silently_drop_a_title(self):
        document=copy.deepcopy(self.names)
        document['roles']['guardian_unknown']='Papel desconhecido'
        with self.assertRaisesRegex(ValueError,'canonical identities'):
            role_display_names(self.records,self.fixture(document))
        missing=copy.deepcopy(self.names)
        del missing['roles']['guardian_backend_domain']
        with self.assertRaisesRegex(ValueError,'canonical identities'):
            role_display_names(self.records,self.fixture(missing))

    def test_empty_multiline_or_table_title_is_rejected(self):
        for invalid in ('','  ','Nome\nOutro','Nome|Outro',None):
            with self.subTest(title=invalid):
                document=copy.deepcopy(self.names)
                document['roles']['guardian_backend_domain']=invalid
                with self.assertRaisesRegex(ValueError,'professional role title'):
                    role_display_names(self.records,self.fixture(document))

    def test_profile_title_drift_is_rejected(self):
        records=copy.deepcopy(self.records)
        records[0]['profile']['description']='Nome divergente'
        with self.assertRaisesRegex(ValueError,'presentation drift'):
            role_display_names(records)

    def test_core_metadata_title_drift_is_rejected(self):
        root=self.fixture(self.names)
        metadata=copy.deepcopy(self.metadata)
        metadata['agents'][0]['title']='Título divergente'
        (root/'core/agents.json').write_text(json.dumps(metadata),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'Core professional title drift'):
            role_display_names(self.records,root)

    def test_schema_and_locale_are_explicit(self):
        for field,value in (('schema_version',2),('locale','en-US'),('unknown',True)):
            document=copy.deepcopy(self.names)
            document[field]=value
            with self.assertRaisesRegex(ValueError,'display names document'):
                role_display_names(self.records,self.fixture(document))


if __name__=='__main__':
    unittest.main()
