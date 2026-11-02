"""Audit regressions and trusted development controls, not native-agent runs."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from tools import guardian_professional as contracts
from tools import guardian_professional_cases as public
from tools import guardian_professional_depth as depth


class OracleBoundaryTests(unittest.TestCase):
    def data(self, evidence, verified=None, contradicted=None):
        return {"requested":["fix"],"tasks":[{"id":"fix","obligations":["fix"],"ready":True,"evidence":evidence}],
                "verified_evidence":[] if verified is None else verified,
                "contradicted_evidence":[] if contradicted is None else contradicted}

    def test_ready_without_evidence_rejected_even_if_no_missing_obligation(self):
        self.assertEqual(public.oracle("obligations",self.data([])),
                         {"missing_obligations":[],"unsafe_ready_tasks":["fix"]})

    def test_unknown_verified_and_contradictory_boundaries(self):
        for evidence, verified, contradicted, unsafe in [
            (["check"],[],[],["fix"]),(["check"],["check"],[],[]),
            (["check"],["check"],["check"],["fix"]),
            (["good","unknown"],["good"],[],["fix"]),
        ]:
            with self.subTest(evidence=evidence,verified=verified,contradicted=contradicted):
                self.assertEqual(public.oracle("obligations",self.data(evidence,verified,contradicted))["unsafe_ready_tasks"],unsafe)

    def test_not_ready_empty_and_empty_task_inventory_do_not_self_complete(self):
        data=self.data([]);data["tasks"][0]["ready"]=False
        self.assertEqual(public.oracle("obligations",data)["unsafe_ready_tasks"],[])
        data["tasks"]=[]
        self.assertEqual(public.oracle("obligations",data)["missing_obligations"],["fix"])

    def test_old_public_fixtures_keep_answers_under_versioned_new_policy(self):
        rows=[r for r in public.load() if r["fixture"]["family"]=="obligations"]
        self.assertEqual(len(rows),2)
        self.assertEqual(public.PROTOCOL_VERSION,3)
        for row in rows:
            d=row["fixture"]["input"]
            previous=sorted(t["id"] for t in d["tasks"] if t["ready"] and any(x not in d["verified_evidence"] for x in t["evidence"]))
            self.assertEqual(public.oracle("obligations",d)["unsafe_ready_tasks"],previous)


class CapabilitySourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc=contracts.load_contracts()
        cls.catalog=json.loads((depth.ROOT/"core/contracts-catalog-v1.json").read_text(encoding="utf8"))
        cls.taxonomy=json.loads((depth.ROOT/"core/taxonomy-v3.json").read_text(encoding="utf8"))

    def test_complete_s04_33_and_g01_132_review_ids_are_inline_and_typed(self):
        for aid,count in (("S04",33),("G01",132)):
            c=next(c for c in self.doc["contracts"] if c["id"]==aid)
            actual=[v["id"] for v in c["capabilities"] if v["role"]=="review"]
            self.assertEqual(len(actual),count)
            r=next(r for r in self.catalog["records"] if r["id"]==aid)
            self.assertIn(contracts.capability_summary(c),r["profile"]["developer_instructions"])
            self.assertNotIn("Capacidades para revisão:",r["profile"]["developer_instructions"])

    def test_s04_removal_4_13_or_10_6_fails_without_rebaseline(self):
        for missing in ("4.13","10.6"):
            catalog=copy.deepcopy(self.catalog)
            record=next(r for r in catalog["records"] if r["id"]=="S04")
            record["profile"]["developer_instructions"]=record["profile"]["developer_instructions"].replace(missing+", ","",1)
            with self.assertRaisesRegex(ValueError,"inline capability"):
                contracts.validate_document(self.doc,catalog,self.taxonomy)

    def test_competing_legacy_summary_cannot_return(self):
        catalog=copy.deepcopy(self.catalog);r=catalog["records"][0]
        r["profile"]["developer_instructions"]+="\nCapacidades para revisão: 4.1.\n"
        with self.assertRaisesRegex(ValueError,"legacy"):
            contracts.validate_document(self.doc,catalog,self.taxonomy)

    def test_contract_version_1_1_is_explicit_and_old_result_not_relabelled(self):
        self.assertEqual({c["contract_version"] for c in self.doc["contracts"]},{"1.1.0"})
        result=contracts.result_template("S08",task_id="task",obligation_ids=["O1"])
        result["contract_version"]="1.0.0"
        with self.assertRaisesRegex(ValueError,"version mismatch"):
            contracts.validate_result(result,"S08",task_id="task",obligation_ids=["O1"])


class ProfessionalDepthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=depth.load()
        cls.receipts=depth.run()

    def test_all_39_roles_execute_positive_faulty_and_order_controls(self):
        self.assertEqual(self.receipts["roles"],39)
        self.assertTrue(self.receipts["passed"])
        self.assertEqual(len({r["role_id"] for r in self.receipts["receipts"]}),39)
        for row in self.receipts["receipts"]:
            with self.subTest(role=row["role_id"]):
                self.assertTrue(row["control_passed"])
                self.assertTrue(row["mutation_killed"])
                self.assertTrue(row["metamorphism_passed"])
                self.assertNotEqual(row["observations"],row["faulty_observations"])
                self.assertFalse(row["candidate_executed"])
                self.assertFalse(row["native_agent_executed"])
                self.assertFalse(row["sme_qualified"])
                self.assertFalse(row["private_holdout_validated"])
                self.assertTrue(row["not_verified"])

    def test_67_unique_items_have_specialized_contracts_and_native_protocol(self):
        ledger=json.loads((depth.ROOT/"docs/audit-role-remediation.json").read_text(encoding="utf8"))
        ids={i for c in self.catalog["cases"] for i in c["audit_items"]}
        self.assertEqual(len(ids),67)
        self.assertEqual(len(ledger["items"]),67)
        self.assertEqual(ids,{r["item_id"] for r in ledger["items"]})
        methods={c["id"]:c for c in contracts.load_contracts()["contracts"]}
        for row in ledger["items"]:
            with self.subTest(item=row["item_id"]):
                c=methods[row["role_id"]];prefix="["+row["item_id"]+"] "
                self.assertTrue(any(s.startswith(prefix) for s in c["procedure"]))
                self.assertTrue(any(s.startswith(prefix) for s in c["definition_of_done"]))
                self.assertTrue(row["specific_checks"])
                self.assertTrue(row["remaining_native_scope"] or row["exact_acceptance_status"]=="VERIFIED_LOCAL_REGRESSION")
                for file in row["implementation_files"]:self.assertTrue((depth.ROOT/file).is_file(),file)

    def test_unknown_role_and_unexecuted_template_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"Unknown depth role"):depth.plan("imaginary")
        template=depth.native_template("S04")
        with self.assertRaisesRegex(ValueError,"revision"):
            depth.check_native_result(template["case_id"],template)

    def test_typed_native_protocol_requires_each_criterion_and_distinct_consumer(self):
        value=self.produced()
        answer=depth.check_native_result(value["case_id"],value)
        self.assertEqual(answer["status"],"produced_pending_independent_corroboration")
        self.assertFalse(answer["native_verified"])
        for mutator in (lambda r:r.__setitem__("consumer",r["producer"]),
                        lambda r:r.__setitem__("consumer","unknown-consumer"),
                        lambda r:r.__setitem__("producer","different-producer"),
                        lambda r:r["coverage"].pop(),
                        lambda r:r["checks"][1].__setitem__("purpose","baseline"),
                        lambda r:r["checks"][1].__setitem__("exit_code",1),
                        lambda r:r["checks"][1].__setitem__("evidence_sha256","b"*64),
                        lambda r:r.__setitem__("case_sha256","0"*64),
                        lambda r:r.__setitem__("accepted",True)):
            bad=copy.deepcopy(value);mutator(bad)
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):depth.check_native_result(bad["case_id"],bad)

    def produced(self):
        value=depth.native_template("S13")
        value["revision"]="a"*40
        value["stack"]={"name":"synthetic transport","version":"1","environment":"local reviewed fixture"}
        value["checks"]=[{"id":name,"purpose":purpose,"argv":["python","trusted_fixture.py"],"exit_code":0,
                          "reason":"expected destination assertion","evidence_sha256":"a"*64}
                         for name,purpose in (("positive","baseline"),("negative","negative-control"))]
        value["artifacts"]=[{"path":"evidence/transport.json","sha256":"a"*64}]
        for criterion in value["coverage"]:criterion.update({"check_ids":["positive","negative"],"not_verified_reason":""})
        return value

    def test_unknown_criterion_or_generic_import_failure_is_not_mutant_detection(self):
        for modifier in (lambda v:v["coverage"][0].__setitem__("criterion_id","other"),
                         lambda v:v["coverage"][0].__setitem__("check_ids",["not-executed"]),
                         lambda v:v["checks"][0].__setitem__("exit_code",True),
                         lambda v:v["checks"][0].__setitem__("reason",""),
                         lambda v:v["artifacts"][0].__setitem__("path","../outside.json")):
            value=self.produced();modifier(value)
            with self.assertRaises(ValueError):depth.check_native_result(value["case_id"],value)

    def test_sqlite_reopen_dedupe_conflict_and_rollback_are_observed(self):
        result=depth.HARNESS["durable-ledger"]()
        self.assertEqual(result,{"sum_delta":-200,"effects":2,"outbox":2,"rejected":["payload-conflict"],"invalid_effects":0})
        bad=depth.HARNESS["durable-ledger"](True)
        self.assertLess(bad["sum_delta"],-200)
        self.assertGreater(bad["effects"],2)

    def test_restart_watermark_tie_breaker_prevents_actual_lost_equal_watermark_key(self):
        good=depth.HARNESS["restartable-migration"]()
        bad=depth.HARNESS["restartable-migration"](True)
        self.assertEqual(good["rows"],[("a",10),("b",20),("c",30)])
        self.assertEqual(bad["rows"],[("a",10),("c",30)])
        self.assertFalse(good["contract_allowed"])

    def test_transport_mutation_reaches_forbidden_stub_without_network(self):
        good=depth.HARNESS["redirect-rebinding"]();bad=depth.HARNESS["redirect-rebinding"](True)
        self.assertEqual(good["reached"],["public.test@8.8.8.8"])
        self.assertIn("redirect.test@127.0.0.1",bad["reached"])
        self.assertEqual(good["external_requests"],0)

    def test_raw_wire_signature_and_bounded_key_refresh_are_computed(self):
        result=depth.HARNESS["wire-signature"]()
        self.assertEqual(result["denied"],["tampered","stale"])
        identity=depth.HARNESS["key-rotation"]()
        self.assertEqual(identity["accepted"],["current","next"])
        self.assertEqual(identity["refreshes"],1)

    def test_permutation_of_independent_invocation_order_preserves_case_receipts(self):
        expected={r["case_id"]:r["observations"] for r in self.receipts["receipts"]}
        for case in reversed(self.catalog["cases"]):
            actual=json.loads(json.dumps(depth.HARNESS[case["harness"]](False)))
            self.assertEqual(actual,expected[case["case_id"]])

    def test_graph_id_renaming_metamorphism_and_negative_control(self):
        harness=depth.HARNESS["dependency-revocation"]
        self.assertEqual(harness(rename="renamed:"),harness())
        self.assertNotEqual(harness(True,rename="renamed:"),harness())

    def test_observation_uncertainty_is_not_removed_by_green_fixture(self):
        for row in self.receipts["receipts"]:
            self.assertTrue(row["scope"])
            self.assertTrue(row["not_verified"])
        dotnet=next(r for r in self.receipts["receipts"] if r["role_id"]=="pack:dotnet:guardian_dotnet_runtime_specialist")
        self.assertFalse(dotnet["observations"]["dotnet_executed"])
        self.assertTrue(dotnet["observations"]["transitive_captive"])
        self.assertFalse(dotnet["observations"]["proper_factory_captive"])


class CalibrationTests(unittest.TestCase):
    def policy(self):
        return {"schema_version":1,"partition":"PUBLIC_DEVELOPMENT",
                "binding":{"model":"inherited-observed-model","effort":"inherited-observed-effort",
                           "environment_sha256":"e"*64,"dataset_sha256":depth.digest(depth.load()),"cost_unit":"USD"},
                "families":{"dependency-revocation":{"min_observations":10,"max_error_rate":.3}}}

    def trial(self, policy, attempt=1, outcome="passed", cost_kind="unknown"):
        return {"case_id":"A00:depth:1","attempt":attempt,"outcome":outcome,"latency_ms":10,
                "cost":{"kind":cost_kind,"amount":None if cost_kind=="unknown" else .1},
                "policy_sha256":depth.digest(policy),"binding":copy.deepcopy(policy["binding"])}

    def test_zero_observations_are_unknown_not_perfect(self):
        row=depth.calibrate([],self.policy())["families"][0]
        self.assertIsNone(row["error_rate"])
        self.assertEqual(row["wilson95_error_interval"],[0.,1.])
        self.assertEqual(row["conclusion"],"inconclusive")

    def test_predeclared_threshold_and_uncertainty_preserve_denominator(self):
        policy=self.policy();trials=[self.trial(policy,n) for n in range(1,11)]
        result=depth.calibrate(trials,policy);row=result["families"][0]
        self.assertEqual(row["numerator_errors"],0)
        self.assertEqual(row["denominator_binary_observations"],10)
        self.assertGreater(row["wilson95_error_interval"][1],.27)
        self.assertLess(row["wilson95_error_interval"][1],.29)
        self.assertEqual(row["conclusion"],"threshold_met")
        self.assertEqual(row["cost_unknown_trials"],10)
        self.assertFalse(result["private_holdout_validated"])
        self.assertFalse(result["observations_authenticated"])
        trials.append(self.trial(policy,11,"not_run"))
        self.assertEqual(depth.calibrate(trials,policy)["families"][0]["conclusion"],"inconclusive")

    def test_changed_context_threshold_dataset_or_private_partition_rejected(self):
        original=self.policy();trial=self.trial(original)
        for alter in (lambda p:p["binding"].__setitem__("model","different"),
                      lambda p:p["binding"].__setitem__("effort","different"),
                      lambda p:p["binding"].__setitem__("dataset_sha256","0"*64),
                      lambda p:p["families"]["dependency-revocation"].__setitem__("max_error_rate",1),
                      lambda p:p.__setitem__("partition","PRIVATE_HOLDOUT")):
            policy=copy.deepcopy(original);alter(policy)
            with self.assertRaises(ValueError):depth.calibrate([trial],policy)

    def test_duplicates_invalid_latency_cost_and_critical_unknown_do_not_disappear(self):
        policy=self.policy();trial=self.trial(policy)
        with self.assertRaises(ValueError):depth.calibrate([trial,trial],policy)
        for modify in (lambda r:r.__setitem__("latency_ms",float("nan")),
                       lambda r:r.__setitem__("latency_ms",True),
                       lambda r:r["cost"].__setitem__("amount",0),
                       lambda r:r.__setitem__("outcome","certified")):
            bad=copy.deepcopy(trial);modify(bad)
            with self.assertRaises(ValueError):depth.calibrate([bad],policy)
        trials=[self.trial(policy,1,cost_kind="estimated"),self.trial(policy,2,cost_kind="measured"),self.trial(policy,3,"inconclusive")]
        row=depth.calibrate(trials,policy)["families"][0]
        self.assertEqual(row["cost_estimated"],.1)
        self.assertEqual(row["cost_measured"],.1)
        self.assertEqual(row["inconclusive"],1)


if __name__=="__main__":unittest.main()
