import json,unittest
from tools.native_check_evidence import paired_outcomes,fixture_passed

class NativeEvidenceTests(unittest.TestCase):
    def test_pairs_only_actual_check_call_with_output_and_expected_fixture(self):
        call={'type':'function_call','call_id':'c1','arguments':'python -B check.py workdir=S08'}
        output={'type':'function_call_output','call_id':'c1','output':json.dumps({'exit_code':1,'output':'seeded failure'})}
        self.assertEqual(paired_outcomes([call,output],{'id':'S08'}),[1])
        self.assertEqual(paired_outcomes([call,dict(output,call_id='unrelated')],{'id':'S08'}),[])
        self.assertEqual(paired_outcomes([call,output],{'id':'S05'}),[])
        self.assertFalse(fixture_passed([1],{'build':True,'seeded_failure':True}))
        self.assertTrue(fixture_passed([1,0],{'build':True,'seeded_failure':True}))
        self.assertTrue(fixture_passed([1],{'build':False,'seeded_failure':True}))
        self.assertFalse(fixture_passed([0],{'build':False,'seeded_failure':True}))
