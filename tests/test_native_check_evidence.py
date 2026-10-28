import json,traceback,unittest
from tools.native_check_evidence import paired_outcomes,fixture_passed

class NativeEvidenceTests(unittest.TestCase):
    def test_schema2_stream_order_and_defensive_failures(self):
        reason='Bob accessed Alice invoice'
        rule={'schema_version':2,'seeded_failure':True,'expected_assertions':[reason]}
        trace='Traceback (most recent call last):\n  File "check.py", line 4, in <module>\n    assert allowed, "'+reason+'"\nAssertionError: '+reason
        metadata=json.dumps({'result':reason,'ok':False})
        def passed(text,code=1):return fixture_passed([{'exit_code':code,'output':text}],rule)
        for prefix,suffix in [('',metadata),(metadata,''),(metadata,metadata),('',json.dumps({'nested':[1,2]},indent=2)),('[]\n{}','{}\n[]')]:
            with self.subTest(prefix=prefix,suffix=suffix):
                self.assertTrue(passed(prefix+'\n'+trace+'\n'+suffix))
        for text in [metadata,json.dumps({'output':trace}),
                     trace.replace('AssertionError: '+reason,'NameError: '+reason),
                     trace.replace('AssertionError: '+reason,'SyntaxError: '+reason),
                     trace.replace('AssertionError: '+reason,'AssertionError: wrong'),
                     trace+'\nNameError: incidental',
                     'ValueError: incidental\n\nDuring handling of the above exception, another exception occurred:\n\n'+trace,
                     trace+'\n{"broken":',trace+'\n"AssertionError: '+reason+'"']:
            with self.subTest(text=text):self.assertFalse(passed(text))
        for code in [0,2,-1,True]:self.assertFalse(passed(trace+'\n'+metadata,code))
        # Use Python's actual formatter: ExceptionGroup summaries are indented
        # tree nodes, including when chained into the expected assertion.
        try:
            try:raise ExceptionGroup('incidental',[NameError('missing')])
            except ExceptionGroup:raise AssertionError(reason)
        except AssertionError:
            grouped=traceback.format_exc()
        self.assertFalse(passed(grouped+'\n'+metadata))

    def test_schema2_build_and_correlated_streams(self):
        case={'case_directory':'/case/S18'}
        rule={'schema_version':2,'seeded_failure':True,'build':True,'expected_assertions':['Bob accessed Alice invoice']}
        call={'type':'function_call','name':'exec_command','call_id':'before','arguments':json.dumps({'cmd':'python -B check.py','workdir':case['case_directory']})}
        after=dict(call,call_id='after')
        failure={'exit_code':1,'output':'Traceback (most recent call last):\nAssertionError: Bob accessed Alice invoice\n{"ok":false}'}
        def output(identity,result):return {'type':'function_call_output','call_id':identity,'output':json.dumps(result)}
        before_result=output('before',failure)
        after_result=output('after',{'exit_code':0,'output':'{"ok":true}'})
        def passed(payloads):return fixture_passed(paired_outcomes(payloads,case,details=True),rule)
        self.assertTrue(passed([call,before_result,after,after_result]))
        for payloads in [[call,before_result],[after,after_result],
                         [call,dict(before_result,call_id='wrong'),after,after_result],
                         [call,before_result,after,output('after',failure)],
                         [after,after_result,call,before_result],
                         [dict(call,arguments=json.dumps({'cmd':'python check.py','workdir':case['case_directory']})),before_result,after,after_result],
                         [dict(call,arguments=json.dumps({'cmd':'python -B check.py','workdir':'/wrong'})),before_result,after,after_result]]:
            with self.subTest(payloads=payloads):self.assertFalse(passed(payloads))

    def test_pairs_only_actual_check_call_with_output_and_expected_fixture(self):
        call={'type':'function_call','name':'exec_command','call_id':'c1','arguments':json.dumps({'cmd':'python -B check.py','workdir':'/case/S08'})}
        output={'type':'function_call_output','call_id':'c1','output':json.dumps({'exit_code':1,'output':'seeded failure'})}
        self.assertEqual(paired_outcomes([call,output],{'id':'S08','case_directory':'/case/S08'}),[1])
        self.assertEqual(paired_outcomes([call,dict(output,call_id='unrelated')],{'id':'S08','case_directory':'/case/S08'}),[])
        self.assertEqual(paired_outcomes([call,output],{'id':'S08','case_directory':'/wrong/S08'}),[])
        self.assertEqual(paired_outcomes([dict(call,name='unrelated'),output],{'id':'S08','case_directory':'/case/S08'}),[])
        self.assertFalse(fixture_passed([1],{'build':True,'seeded_failure':True}))
        self.assertTrue(fixture_passed([1,0],{'build':True,'seeded_failure':True}))
        self.assertTrue(fixture_passed([1],{'build':False,'seeded_failure':True}))
        self.assertFalse(fixture_passed([0],{'build':False,'seeded_failure':True}))

    def test_exact_cwd_and_batch_index_command_binding(self):
        code='const results = await Promise.allSettled([tools.exec_command({cmd:"other",workdir:"/case/A00"}),tools.exec_command({cmd:"python -B check.py",workdir:"/case/A00"})]); results.forEach((r,i)=>text({i,...r}));'
        call={'type':'custom_tool_call','name':'exec','call_id':'c','input':code}
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
