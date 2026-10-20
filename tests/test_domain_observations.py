import unittest,tempfile,json
from pathlib import Path
from tools.guardian_domain_checks import audit,fixture_suite,read_bounded

class DomainObservationTests(unittest.TestCase):
    def test_cancel_reset_or_disabled_button_is_not_a_submit(self):
        for button in ('<button type="button">Cancel</button>','<button type="reset">Reset</button>','<button disabled>Save</button>'):
            result=audit('ui',{'html':'<label for="x">X</label><input id="x">'+button,'browser_executed':False})
            self.assertEqual(result['status'],'STATIC_REJECTED')
    def test_all_eight_domains_have_success_and_failure_regressions(self):
        result=fixture_suite();self.assertTrue(result['ok']);self.assertEqual(result['scenarios'],16);self.assertEqual(result['domains'],8);self.assertFalse(result['native_execution'])
    def test_unknown_fields_or_domain_cannot_silently_pass(self):
        with self.assertRaises(ValueError):audit('api',{'passed':True})
        with self.assertRaises(ValueError):audit('unknown',{})
    def test_huge_observations_are_rejected_before_parse(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'input.json';path.write_bytes(b' '*1000001)
            with self.assertRaises(ValueError):read_bounded(path)
    def test_boolean_currency_is_not_an_integer(self):
        result=audit('financial',{'initial_total':100,'final_total':100,'minor_units':[True],'effects_for_idempotency_key':1})
        self.assertEqual(result['status'],'STATIC_REJECTED')
    def test_ai_unknown_citations_cannot_pass(self):
        result=audit('ai',{'answer':'A','canary':'X','citations':['invented'],'known_document_ids':['d1'],'retrieval_instruction_followed':False})
        self.assertEqual(result['status'],'STATIC_REJECTED');self.assertFalse(result['authenticated_observations'])
