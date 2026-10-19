import copy,unittest
from tools.guardian_release_gate import verify_acceptance_reports

class ExternalAcceptanceTests(unittest.TestCase):
    def test_requires_exact_revision_and_executed_39_plus_no_skipped_grader(self):
        revision='a'*40
        native={'revision':revision,'expected':39,'verified':39,'all_native_roles_verified':True,'protected_fixtures_unchanged':True}
        grader={'revision':revision,'passed':True,'tests':14,'skipped':0,'failures':0,'errors':0}
        verify_acceptance_reports(native,grader,revision)
        for field,value in [('expected',0),('verified',38),('verified',True),('revision','b'*40),('protected_fixtures_unchanged',False)]:
            item=copy.deepcopy(native);item[field]=value
            with self.assertRaises(ValueError):verify_acceptance_reports(item,grader,revision)
        for field,value in [('skipped',1),('tests',0),('passed',False),('errors',1),('failures',True),('revision','b'*40)]:
            item=copy.deepcopy(grader);item[field]=value
            with self.assertRaises(ValueError):verify_acceptance_reports(native,item,revision)
