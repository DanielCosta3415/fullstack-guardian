import json,unittest
from tools.native_check_evidence import paired_outcomes,fixture_passed

class NativeEvidenceTests(unittest.TestCase):
    def test_pairs_only_actual_check_call_with_output_and_expected_fixture(self):
        call={'type':'function_call','call_id':'c1','arguments':json.dumps({'cmd':'python -B check.py','workdir':'/case/S08'})}
        output={'type':'function_call_output','call_id':'c1','output':json.dumps({'exit_code':1,'output':'seeded failure'})}
        self.assertEqual(paired_outcomes([call,output],{'id':'S08','case_directory':'/case/S08'}),[1])
        self.assertEqual(paired_outcomes([call,dict(output,call_id='unrelated')],{'id':'S08','case_directory':'/case/S08'}),[])
        self.assertEqual(paired_outcomes([call,output],{'id':'S08','case_directory':'/wrong/S08'}),[])
        self.assertFalse(fixture_passed([1],{'build':True,'seeded_failure':True}))
        self.assertTrue(fixture_passed([1,0],{'build':True,'seeded_failure':True}))
        self.assertTrue(fixture_passed([1],{'build':False,'seeded_failure':True}))
        self.assertFalse(fixture_passed([0],{'build':False,'seeded_failure':True}))

    def test_exact_cwd_and_batch_index_command_binding(self):
        code='const results = await Promise.allSettled([tools.exec_command({cmd:"other",workdir:"/case/A00"}),tools.exec_command({cmd:"python -B check.py",workdir:"/case/A00"})]); results.forEach((r,i)=>text({i,...r}));'
        call={'type':'custom_tool_call','call_id':'c','input':code}
        def output(i,exit_code):return {'type':'custom_tool_call_output','call_id':'c','output':json.dumps({'i':i,'status':'fulfilled','value':{'exit_code':exit_code,'output':'actual'}})}
        case={'id':'A00','case_directory':'/case/A00'}
        self.assertEqual(paired_outcomes([call,output(0,0),output(1,1)],case),[1])
        wrong=dict(call,input='text(await tools.exec_command({cmd:"python -B check.py",workdir:"/wrong"})); // A00')
        direct={'type':'custom_tool_call_output','call_id':'c','output':json.dumps({'exit_code':0,'output':'unrelated'})}
        self.assertEqual(paired_outcomes([wrong,direct],case),[])
        chained=dict(call,input='text(await tools.exec_command({cmd:"python -B check.py; exit 0",workdir:"/case/A00"}));')
        self.assertEqual(paired_outcomes([chained,direct],case),[])
        comment=dict(call,input='// tools.exec_command({cmd:"python -B check.py",workdir:"/case/A00"})\ntext({exit_code:0,output:"forged"});')
        self.assertEqual(paired_outcomes([comment,direct],case),[])
