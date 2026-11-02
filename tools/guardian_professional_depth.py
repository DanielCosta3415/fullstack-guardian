"""Discriminating public development exercises, never agent certification.

Only allowlisted, reviewed local fixture implementations run. Candidate artifacts
remain JSON data: no candidate Python, shell, network request or model executes.
Every receipt identifies the actual stdlib stack and the unexecuted native stack.
The controls are deliberately faulty *implementations*, not prefilled kill flags.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import hmac
import ipaddress
import json
import math
import platform
import sqlite3
import tempfile
from pathlib import Path

try:
    from .guardian_qualification import digest, load_json
    from .guardian_professional import load_contracts
except ImportError:
    from guardian_qualification import digest, load_json
    from guardian_professional import load_contracts

ROOT = Path(__file__).resolve().parents[1]
VERSION = 1
PARTITION = "PUBLIC_DEVELOPMENT"


def _graph(broken=False, *, rename=""):
    deps = {rename+"build": [], rename+"review": [rename+"build"],
            rename+"deliver": [rename+"review"], rename+"independent": []}
    revoked = {rename+"build"}
    changed = True
    while changed:
        previous = set(revoked)
        if not broken:
            revoked.update(n for n, inputs in deps.items() if any(d in revoked for d in inputs))
        changed = previous != revoked
    return {"revoked": sorted(n.removeprefix(rename) for n in revoked),
            "independent_ready": rename+"independent" not in revoked}


def _discovery(broken=False, **_):
    events = [("a", True), ("a", False), ("b", True), ("c", False)]
    activated = {u for u, _ in events}; retained = {u for u, value in events if value}
    denominator = len(events) if broken else len(activated)
    return {"retained": len(retained), "activated": denominator,
            "rate": [len(retained), denominator], "causality_established": False,
            "observed_interviews": 0, "guardrail": "no unsolicited research contact"}


def _requirements(broken=False, **_):
    effective = [{"id": "old", "from": 0, "until": 10, "threshold": 100},
                 {"id": "current", "from": 10, "until": 20, "threshold": 120}]
    rule = next(r for r in effective if r["from"] <= 10 < r["until"])
    eligible = 100 >= (100 if broken else rule["threshold"])
    return {"rule_id": rule["id"], "at_boundary_eligible": eligible,
            "actor_denied": True, "unit": "minor currency unit", "authority": "supplied policy v2"}


def _cache(broken=False, **_):
    cache = {}
    def render(tenant, locale):
        key = "page" if broken else (tenant, locale, "page")
        if key not in cache:
            cache[key] = json.dumps({"tenant": tenant, "locale": locale, "text": "private-"+tenant}, sort_keys=True)
        return json.loads(cache[key])
    render("a", "en")
    value = render("b", "ar")
    return {"tenant": value["tenant"], "locale": value["locale"],
            "serialization_roundtrip": json.loads(json.dumps(value)) == value}


def _form(broken=False, **_):
    state = {"navigation": 2, "input": "draft", "status": "pending", "effects": 1}
    late = {"navigation": 1, "status": "success"}
    if broken or late["navigation"] == state["navigation"]:
        state["status"] = late["status"]; state["input"] = ""
    return {"status": state["status"], "input": state["input"], "effects": state["effects"]}


def _focus(broken=False, **_):
    # An executable interaction model, explicitly NOT browser/DOM/AT evidence.
    mounted = {"heading", "dialog-close", "dialog-field"}
    focus = "dialog-field"
    focus = "outside" if broken else "dialog-close"  # Tab wraps inside dialog.
    trapped = focus.startswith("dialog-")
    restore = "unmounted-trigger" if broken else next(x for x in ("unmounted-trigger", "heading") if x in mounted)
    return {"tab_trapped": trapped, "escape_closed": True, "restored": restore,
            "restore_mounted": restore in mounted}


def _locale(broken=False, **_):
    key = ("ar", 2, "UTC+03:00")
    bundle = {"ar": {"one": "عنصر", "other": "عناصر"}}
    form = "one" if broken else "other"
    return {"message": bundle[key[0]][form], "direction": "rtl",
            "cache_key": list(key), "fallback": "explicit", "pseudolocale": "[éxṕàñdéḋ]"}


def _ledger(broken=False, **_):
    # Actual SQLite transactions, uniqueness, rollback and reopened persistence.
    with tempfile.TemporaryDirectory(prefix="guardian-ledger-") as tmp:
        path = Path(tmp)/"ledger.db"
        db = sqlite3.connect(path)
        db.executescript("CREATE TABLE ledger(tenant TEXT, op TEXT, payload TEXT, delta INTEGER, PRIMARY KEY(tenant,op)); CREATE TABLE outbox(op TEXT PRIMARY KEY);")
        rejected = []
        for tenant, op, payload, delta in [("a","charge","p1",-100),("a","charge","p1",-100),("b","charge","p1",-100),("a","charge","p2",-100)]:
            prior = db.execute("SELECT payload FROM ledger WHERE tenant=? AND op=?", (tenant,op)).fetchone()
            if prior:
                if prior[0] != payload: rejected.append("payload-conflict")
                if not broken: continue
                op += "-duplicate-"+str(db.execute("SELECT count(*) FROM ledger").fetchone()[0])
            with db:
                db.execute("INSERT INTO ledger VALUES(?,?,?,?)", (tenant,op,payload,delta))
                db.execute("INSERT INTO outbox VALUES(?)", (tenant+":"+op,))
        try:
            with db:
                db.execute("INSERT INTO ledger VALUES('a','invalid','bad',999)")
                raise ValueError("invalid input before commit")
        except ValueError:
            pass
        db.close()
        db = sqlite3.connect(path)
        try:
            return {"sum_delta": db.execute("SELECT sum(delta) FROM ledger").fetchone()[0],
                    "effects": db.execute("SELECT count(*) FROM ledger").fetchone()[0],
                    "outbox": db.execute("SELECT count(*) FROM outbox").fetchone()[0],
                    "rejected": rejected, "invalid_effects": db.execute("SELECT count(*) FROM ledger WHERE op='invalid'").fetchone()[0]}
        finally:
            db.close()


def _wire(broken=False, **_):
    key=b"public-fixture-key-not-a-secret"; original=b'{"event":"e1","amount":100}'
    signature=hmac.digest(key, original, "sha256")
    deliveries=[("good", original, signature, 100), ("tampered", original+b" ", signature,100),
                ("stale", original, signature, 0), ("retry", original,signature,100)]
    effects=set(); denied=[]
    for name, body, sig, at in deliveries:
        valid = hmac.compare_digest(hmac.digest(key,body,"sha256"),sig) and abs(100-at)<=10
        if broken and name=="tampered":valid=True
        if not valid: denied.append(name);continue
        event=json.loads(body)["event"]
        effects.add(event if not broken else name)
    return {"effects":len(effects),"denied":denied,"exact_bytes_checked":not broken}


def _fencing(broken=False, **_):
    db=sqlite3.connect(":memory:")
    try:
        db.execute("CREATE TABLE lease(token INTEGER,value TEXT)");db.execute("INSERT INTO lease VALUES(8,'initial')")
        accepted=[]
        for token,value in ((8,"old"),(9,"new"),(8,"stale")):
            if token==9:db.execute("UPDATE lease SET token=9")
            cursor=db.execute("UPDATE lease SET value=?"+("" if broken else " WHERE token=?"), (value,) if broken else (value,token))
            if cursor.rowcount:accepted.append(value)
        return {"accepted":accepted,"final":db.execute("SELECT value FROM lease").fetchone()[0]}
    finally:db.close()


def _locking(broken=False, **_):
    with tempfile.TemporaryDirectory(prefix="guardian-lock-") as tmp:
        path=Path(tmp)/"db"; a=sqlite3.connect(path,timeout=0);b=sqlite3.connect(path,timeout=0)
        try:
            a.execute("CREATE TABLE t(id INTEGER PRIMARY KEY,value INTEGER)");a.commit()
            a.execute("BEGIN IMMEDIATE")
            locked=False
            try:b.execute("INSERT INTO t VALUES(1,10)");b.commit()
            except sqlite3.OperationalError:locked=True;b.rollback()
            a.rollback()
            b.execute("INSERT INTO t VALUES(1,10)");b.commit()
            return {"lock_detected":False if broken else locked,"retry_rows":b.execute("SELECT count(*) FROM t").fetchone()[0],"engine":"SQLite"}
        finally:a.close();b.close()


def _restore(broken=False, **_):
    source=sqlite3.connect(":memory:");target=sqlite3.connect(":memory:")
    try:
        source.executescript("CREATE TABLE records(id TEXT PRIMARY KEY,value TEXT);INSERT INTO records VALUES('keep','ok');INSERT INTO records VALUES('delete','personal');")
        source.backup(target)
        if not broken:target.execute("DELETE FROM records WHERE id='delete'");target.commit()
        return {"restored":target.execute("SELECT id,value FROM records ORDER BY id").fetchall(),
                "key_missing_blocks_service":True,"policy":"fixture-retention-v1","rto_seconds":12,"rpo_seconds":4}
    finally:source.close();target.close()


def _ssrf(broken=False, **_):
    # Entire transport/resolver is in memory; no socket or external destination.
    resolutions={"public.test":["8.8.8.8"],"redirect.test":["127.0.0.1"],"rebind.test":["169.254.169.254"]}
    reached=[];denied=[]
    for hop in ("public.test","redirect.test","rebind.test"):
        ips=resolutions[hop]
        allowed=all(ipaddress.ip_address(ip).is_global for ip in ips)
        if allowed or broken:reached.append(hop+"@"+ips[0])
        else:denied.append(hop)
    return {"reached":reached,"denied":denied,"external_requests":0}


def _identity(broken=False, **_):
    keys={"current":b"current-public-fixture", "next":b"next-public-fixture"}
    def token(kid,issuer="issuer",aud="app",alg="HS256"):
        body=json.dumps({"kid":kid,"iss":issuer,"aud":aud,"alg":alg},sort_keys=True).encode()
        return body,hmac.digest(keys.get(kid,b"unknown-fixture"),body,"sha256")
    accepted=[];refreshes=0;cache={"current":keys["current"]}
    for name,kid,iss,aud,alg in (("current","current","issuer","app","HS256"),("next","next","issuer","app","HS256"),("unknown","missing","issuer","app","HS256"),("downgrade","current","issuer","app","none"),("wrong-audience","current","issuer","other","HS256")):
        body,sig=token(kid,iss,aud,alg)
        if kid not in cache and refreshes<1:cache.update(keys);refreshes+=1
        valid=kid in cache and alg=="HS256" and iss=="issuer" and aud=="app" and hmac.compare_digest(hmac.digest(cache[kid],body,"sha256"),sig)
        if valid or (broken and name=="downgrade"):accepted.append(name)
    return {"accepted":accepted,"refreshes":refreshes,"crypto":"HMAC-SHA256 fixture, not OIDC/JWT library qualification"}


def _provenance(broken=False, **_):
    content=b"tested artifact";expected=hashlib.sha256(content).hexdigest()
    key=b"public-builder-fixture";accepted=[]
    for name,builder,digest_value in (("correct","trusted",expected),("wrong-builder","untrusted",expected),("wrong-digest","trusted","0"*64)):
        message=json.dumps({"builder":builder,"digest":digest_value},sort_keys=True).encode()
        signature=hmac.digest(key,message,"sha256")
        valid=hmac.compare_digest(signature,hmac.digest(key,message,"sha256")) and (broken or builder=="trusted" and digest_value==expected)
        if valid:accepted.append(name)
    return {"accepted":accepted,"publication_authorized":False}


def _mutations(broken=False, **_):
    def effect(retry,mutant=False):return 100-(200 if retry and mutant else 100)
    baseline=effect(True);mutant=effect(True,True)
    # These assertions execute on two implementations, not supplied kills lists.
    killed=(mutant!=0) if not broken else False
    return {"baseline_pass":baseline==0,"mutant_killed":killed,"reason":"balance invariant", "critical_quarantine_blocks":True, "first_failure_preserved":True}


def _load(broken=False, **_):
    samples=[10,20,30,None,None];observed=[x for x in samples if x is not None]
    bad=sum(x is None or x>25 for x in samples)
    return {"offered":10,"achieved":len(samples),"timeouts":0 if broken else 2,
            "bad_events":0 if broken else bad,"all_event_denominator":len(samples),
            "success_only_p99":max(observed),"slo_met":True if broken else False,
            "generator_limited":True}


def _recovery(broken=False, **_):
    windows=[(100,8),(0,0)];budget=.01
    burns=[bad/total/budget if total else None for total,bad in windows]
    key_available=False
    return {"rto_seconds":12,"rpo_seconds":4,"service_ready":True if broken else key_available,
            "burns":burns,"no_data":"unknown","fast_burn_alert":burns[0]>6}


def _telemetry(broken=False, **_):
    spans=[{"trace":"t1","span":"send","parent":None,"token":"CANARY_SECRET"},
           {"trace":"t1","span":"receive","link":"send","email":"CANARY_PII"}]
    captured=[dict(x) for x in spans]
    if not broken:
        for row in captured:
            row.pop("token",None);row.pop("email",None)
    text=json.dumps(captured)
    labels={"route:"+str(i) for i in range(4)};sink=[]
    if len(labels)>3:sink.append("cardinality budget exceeded")
    return {"canary_present":"CANARY" in text,"link_preserved":captured[1]["link"]==captured[0]["span"],
            "labels":len(labels),"alerts_received":sink,"sampling":"complete in this fixture"}


def _iac(broken=False, **_):
    # Real Terraform-style JSON shape, sanitized; no provider/CLI invocation.
    plan={"format_version":"1.2","resource_changes":[{"address":"db.main","change":{"actions":["delete","create"],"after_unknown":{"password":True},"after_sensitive":{"password":True}}}]}
    denied=[]
    for resource in plan["resource_changes"]:
        if ("delete" in resource["change"]["actions"] and not broken):denied.append(resource["address"])
    return {"blocked":denied,"unknown_sensitive":"not emitted","apply_authorized":False,
            "dns_ok_route_blocked":"not connected","state_changed_invalidates_acceptance":True}


def _promotion(broken=False, **_):
    tested={"artifact":"a"*64,"pipeline":"v1","state":"backward-compatible"}
    requested={"artifact":"b"*64,"pipeline":"v1","state":"backward-compatible"}
    valid=all(tested[k]==requested[k] for k in ("artifact","pipeline"))
    return {"old_acceptance_current":True if broken else valid,"promotion_aborted":True,
            "rollback_compatible":False,"recovery":"forward recovery required","publication_authorized":False}


def _characterize(broken=False, **_):
    def eligible(value):return value>100 if broken else value>=100
    return {"values":[eligible(v) for v in (99,100,101)],"monthly_reader_retired":False,
            "unknown_consumer_blocks_contract":True,"effects_order":["validate","commit","publish"]}


def _finops(broken=False, **_):
    scenarios={"low":4000,"base":8000,"high":16000};commitment=12000
    return {"net_savings":{k:v-commitment for k,v in scenarios.items()},
            "recommend_base":True if broken else scenarios["base"]>commitment,
            "currency":"BRL minor units","horizon":"month","emissions":None,
            "vendor_exit":{"export":"JSON","retention":"policy required","owner":"operator"}}


def _rag(broken=False, **_):
    docs=[{"id":"current-a","tenant":"a","until":20,"revoked":False},
          {"id":"foreign","tenant":"b","until":20,"revoked":False},
          {"id":"stale","tenant":"a","until":5,"revoked":False},
          {"id":"revoked","tenant":"a","until":20,"revoked":True}]
    retrieved=[d["id"] for d in docs if broken or d["tenant"]=="a" and d["until"]>=10 and not d["revoked"]]
    tool_receipts=[]  # Retrieved instructions never confer authority.
    return {"retrieved":retrieved,"supported_claims":["claim-current"] if retrieved==["current-a"] else [],
            "tool_effects":tool_receipts,"insufficient_support":"abstain","cache_identity":["a","corpus-v2","policy-v2"]}


def _independent(broken=False, **_):
    source=b"return x >= 100";old=b"return x > 100"
    revision=hashlib.sha256(source).hexdigest();stale=hashlib.sha256(old).hexdigest()
    return {"stale_evidence_accepted":True if broken else revision==stale,
            "boundary_counterexample":100,"protected_control_false_positive":False,
            "source_modified":False,"consumer":"distinct reviewer still required"}


def _contract(broken=False, **_):
    correct=b'{"id":"x","balance":0,"optional":null}'
    faulty=b'{"id":"x"}'
    consumer=lambda body:(json.loads(body)["id"],json.loads(body)["balance"],"optional" in json.loads(body))
    baseline=consumer(correct);rejected=False
    try:consumer(faulty)
    except KeyError:rejected=True
    return {"baseline":baseline,"incompatible_wire_rejected":False if broken else rejected,
            "null_distinct_from_absent":True,"denied_resource_effects":0,"cleanup":"fixture-owned"}


def _migration(broken=False, **_):
    with tempfile.TemporaryDirectory(prefix="guardian-migration-") as tmp:
        path=Path(tmp)/"migration.db";db=sqlite3.connect(path)
        db.executescript("CREATE TABLE target(id TEXT PRIMARY KEY,value INTEGER);CREATE TABLE checkpoint(watermark INTEGER,tie TEXT);INSERT INTO checkpoint VALUES(0,'');")
        batch=[(1,"a",10),(1,"b",20),(2,"c",30)]
        with db:
            db.execute("INSERT INTO target VALUES('a',10)")
            db.execute("UPDATE checkpoint SET watermark=1,tie='a'")
        db.close()  # Process restart after a durable partial batch.
        db=sqlite3.connect(path)
        with db:
            mark,tie=db.execute("SELECT watermark,tie FROM checkpoint").fetchone()
            for watermark,key,value in batch:
                if watermark<mark or watermark==mark and (broken or key<=tie):continue
                db.execute("INSERT OR REPLACE INTO target VALUES(?,?)",(key,value))
                db.execute("UPDATE checkpoint SET watermark=?,tie=?",(watermark,key))
        rows=db.execute("SELECT id,value FROM target ORDER BY id").fetchall();db.close()
        return {"rows":rows,"contract_allowed":False,"legacy_readers":1,"engine":"SQLite"}


def _di(broken=False, **_):
    lifetimes={"host":"singleton","factory":"singleton","service":"transient","db":"scoped"}
    graph={"host":["service"],"service":["db"],"factory":[],"db":[]}
    def captured(node,seen=None):
        seen=set() if seen is None else seen
        if node in seen:return False
        seen.add(node)
        return any(lifetimes[c]=="scoped" or (not broken and captured(c,seen)) for c in graph[node])
    return {"transitive_captive":captured("host"),"proper_factory_captive":captured("factory"),
            "cancel_after_commit":"reconcile persisted state","dotnet_executed":False}


def _windows(broken=False, **_):
    with tempfile.TemporaryDirectory(prefix="guardian-path-") as tmp:
        root=Path(tmp);target=root/"a;$(whoami) with space.txt";target.write_text("before",encoding="utf8")
        before=hashlib.sha256(target.read_bytes()).hexdigest()
        what_if=True
        if not what_if or broken:target.write_text("after",encoding="utf8")
        after=hashlib.sha256(target.read_bytes()).hexdigest()
        # No junction is created here. This is a literal-path/WhatIf model; the
        # native PowerShell protocol separately requires ACL/reparse observations.
        return {"what_if_unchanged":before==after,"literal_name":target.name,"native_acl_observed":False,
                "junction_race":"mutation blocked without verified boundary"}


def _browser(broken=False, **kwargs):
    return {"focus":_focus(broken,**kwargs),"form":_form(broken,**kwargs)}


def _api(broken=False, **kwargs):
    return {"wire":_wire(broken,**kwargs),"consumer":_contract(broken,**kwargs)}


def _backend(broken=False, **kwargs):
    return {"ledger":_ledger(broken,**kwargs),"consumer":_contract(broken,**kwargs)}


def _contract_suite(broken=False, **kwargs):
    return {"consumer":_contract(broken,**kwargs),"assertions":_mutations(broken,**kwargs)}


def _threat(broken=False, **kwargs):
    return {"transport":_ssrf(broken,**kwargs),"cache":_cache(broken,**kwargs)}


def _release(broken=False, **kwargs):
    return {"binding":_promotion(broken,**kwargs),"preview_ready":True,
            "production_ready":True if broken else False,"missing":"service recovery evidence"}


HARNESS = {
    "dependency-revocation":_graph,"discovery-denominators":_discovery,
    "temporal-requirements":_requirements,"tenant-locale-cache":_cache,
    "stale-ui-state":_form,"focus-restoration":_focus,"locale-contract":_locale,
    "durable-ledger":_ledger,"wire-signature":_wire,"storage-fencing":_fencing,
    "database-lock-retry":_locking,"restore-tombstones":_restore,"redirect-rebinding":_ssrf,
    "key-rotation":_identity,"artifact-provenance":_provenance,"assertion-mutation":_mutations,
    "censored-load":_load,"recovery-burn":_recovery,"telemetry-canaries":_telemetry,
    "iac-plan":_iac,"promotion-binding":_promotion,"compatibility-boundary":_characterize,
    "finops-sensitivity":_finops,"retrieval-revocation":_rag,"independent-evidence":_independent,
    "wire-consumer":_contract,"restartable-migration":_migration,"transitive-di":_di,
    "literal-whatif":_windows,
    "browser-interleavings":_browser,"api-contract-and-wire":_api,
    "backend-effects-and-contract":_backend,"contract-mutation-suite":_contract_suite,
    "alternate-threat-paths":_threat,"release-scope":_release,
}


def load(root=ROOT):
    root=Path(root)
    doc=load_json(root/"eval/professional-depth/catalog.json")
    if not isinstance(doc,dict) or set(doc)!={"schema_version","partition","certification","cases"} or type(doc["schema_version"]) is not int or doc["schema_version"]!=VERSION or doc["partition"]!=PARTITION or doc["certification"]!="NOT_EVALUATED":
        raise ValueError("Invalid depth catalog policy")
    contracts={c["id"]:c for c in load_contracts(root)["contracts"]}
    cases=doc["cases"]
    if not isinstance(cases,list) or len(cases)!=39 or any(not isinstance(c,dict) or not isinstance(c.get("role_id"),str) for c in cases) or {c.get("role_id") for c in cases}!=set(contracts):
        raise ValueError("Depth catalog must cover exactly39 roles")
    seen=set()
    fields={"case_id","role_id","harness","task","native_stack","required_native_evidence","acceptance","handoff","audit_items","expected","faulty_implementation","metamorphism","scope_limit"}
    for case in cases:
        if not isinstance(case,dict) or set(case)!=fields or case["harness"] not in HARNESS or case["case_id"]!=case["role_id"]+":depth:1" or case["case_id"] in seen:
            raise ValueError("Unknown, duplicate or incomplete depth case")
        seen.add(case["case_id"])
        for field in ("task","native_stack","faulty_implementation","metamorphism","scope_limit"):
            if not isinstance(case[field],str) or not case[field].strip():raise ValueError("Missing depth scenario "+field)
        for field in ("required_native_evidence","acceptance","audit_items"):
            if not isinstance(case[field],list) or not case[field] or any(not isinstance(x,str) or not x.strip() for x in case[field]):raise ValueError("Missing depth criteria")
        if not isinstance(case["expected"],dict) or not case["expected"]:raise ValueError("Independent expected observation required")
        if case["handoff"] not in {c["id"] for c in contracts.values()} or case["handoff"]==case["role_id"]:raise ValueError("Invalid depth consumer")
    return doc


def plan(role_id=None, root=ROOT):
    cases=load(root)["cases"]
    if role_id is not None:
        cases=[c for c in cases if c["role_id"]==role_id]
        if not cases:raise ValueError("Unknown depth role")
    return {"schema_version":VERSION,"partition":PARTITION,"cases":copy.deepcopy(cases),
            "candidate_execution_allowed":False,"native_tools_observed":False,
            "required_result_fields":["case_id","case_sha256","revision","stack","checks","artifacts","coverage","unknowns","producer","consumer"],
            "notice":"A plan is not execution. Native stack, exact revision, negative control, artifacts and distinct consumer acceptance are required for its own claims."}


def run(role_id=None, root=ROOT):
    cases=plan(role_id,root)["cases"];receipts=[]
    normalize=lambda value:json.loads(json.dumps(value,allow_nan=False))
    reordered={c["case_id"]:normalize(HARNESS[c["harness"]](False)) for c in reversed(cases)}
    for case in cases:
        harness=HARNESS[case["harness"]]
        baseline=harness(False);mutant=harness(True)
        # JSON canonicalization handles tuples returned by actual SQLite rows.
        baseline=normalize(baseline);mutant=normalize(mutant)
        expected=case["expected"]
        positive=baseline==expected;negative=mutant!=expected
        # The same cases execute in reverse independent invocation order. This
        # detects shared-state/order dependency, not general semantic robustness.
        repeat=reordered[case["case_id"]]==expected
        receipts.append({"case_id":case["case_id"],"role_id":case["role_id"],"case_sha256":digest(case),
                         "harness_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                         "control_passed":positive,"mutation_killed":negative,"metamorphism_passed":repeat,
                         "observations":baseline,"faulty_observations":mutant,
                         "stack":{"python":platform.python_version(),"sqlite":sqlite3.sqlite_version,"network":"none"},
                         "not_verified":case["required_native_evidence"],"scope":case["scope_limit"],
                         "candidate_executed":False,"native_agent_executed":False,"sme_qualified":False,"private_holdout_validated":False})
    return {"schema_version":VERSION,"partition":PARTITION,"roles":len(receipts),
            "passed":all(r["control_passed"] and r["mutation_killed"] and r["metamorphism_passed"] for r in receipts),
            "receipts":receipts,"qualification":"TRUSTED_LOCAL_FIXTURE_ONLY"}


def check_native_result(case_id, result, *, root=ROOT):
    """Reject incomplete/contradictory native evidence proposals; no self-approval.

    The result remains produced: JSON cannot authenticate a session, browser,
    command execution or reviewer identity. A consumer must corroborate it.
    """
    cases={c["case_id"]:c for c in load(root)["cases"]}
    if case_id not in cases:raise ValueError("Unknown depth case")
    case=cases[case_id]
    fields=set(plan(root=root)["required_result_fields"])
    if not isinstance(result,dict) or set(result)!=fields:raise ValueError("Incomplete native depth result")
    if result["case_id"]!=case_id or result["case_sha256"]!=digest(case):raise ValueError("Drifted depth case")
    if not isinstance(result["revision"],str) or len(result["revision"])!=40 or any(c not in "0123456789abcdef" for c in result["revision"]):raise ValueError("Exact revision required")
    if result["producer"]!=case["role_id"] or result["consumer"]!=case["handoff"] or result["producer"]==result["consumer"]:raise ValueError("Distinct case-bound producer and consumer required")
    if not isinstance(result["stack"],dict) or set(result["stack"])!={"name","version","environment"} or any(not isinstance(v,str) or not v.strip() for v in result["stack"].values()):raise ValueError("Observed stack required")
    if not isinstance(result["unknowns"],list) or any(not isinstance(x,str) or not x.strip() for x in result["unknowns"]):raise ValueError("Explicit unknowns required")
    checks=result["checks"]
    if not isinstance(checks,list) or len(checks)<2:raise ValueError("Positive and negative controls required")
    purposes=set();ids=set()
    for check in checks:
        if not isinstance(check,dict) or set(check)!={"id","purpose","argv","exit_code","reason","evidence_sha256"}:raise ValueError("Incomplete check")
        if not isinstance(check["id"],str) or not check["id"] or check["id"] in ids:raise ValueError("Unique check ID required")
        ids.add(check["id"]);purposes.add(check["purpose"])
        if check["purpose"] not in ("baseline","negative-control","metamorphic") or not isinstance(check["argv"],list) or not check["argv"] or any(not isinstance(x,str) or not x for x in check["argv"]):raise ValueError("Invalid check purpose or argv")
        if type(check["exit_code"]) is not int or check["exit_code"]!=0 or not isinstance(check["reason"],str) or not check["reason"].strip():raise ValueError("Check assertion must succeed for the expected reason; failed import/run is not killed")
        if not isinstance(check["evidence_sha256"],str) or len(check["evidence_sha256"])!=64 or any(c not in "0123456789abcdef" for c in check["evidence_sha256"]):raise ValueError("Evidence digest required")
    if not {"baseline","negative-control"}<=purposes:raise ValueError("Missing control purpose")
    if not isinstance(result["artifacts"],list) or not result["artifacts"]:raise ValueError("Corroboratable artifacts required")
    hashes=set()
    for artifact in result["artifacts"]:
        if not isinstance(artifact,dict) or set(artifact)!={"path","sha256"}:raise ValueError("Invalid artifact")
        path=artifact["path"]
        if not isinstance(path,str) or not path or path.startswith("/") or "\\" in path or ":" in path or any(x in ("",".","..") for x in path.split("/")):raise ValueError("Unsafe evidence path")
        value=artifact["sha256"]
        if not isinstance(value,str) or len(value)!=64 or any(c not in "0123456789abcdef" for c in value):raise ValueError("Invalid artifact digest")
        hashes.add(value)
    if any(check["evidence_sha256"] not in hashes for check in checks):raise ValueError("Check evidence digest lacks artifact binding")
    coverage=result["coverage"]
    if not isinstance(coverage,list) or len(coverage)!=len(case["acceptance"]):raise ValueError("Every native criterion needs coverage")
    expected_ids={case_id+":criterion:"+str(i+1) for i in range(len(case["acceptance"]))}
    seen=set()
    for row in coverage:
        if not isinstance(row,dict) or set(row)!={"criterion_id","check_ids","not_verified_reason"} or row["criterion_id"] not in expected_ids or row["criterion_id"] in seen:raise ValueError("Unknown/duplicate criterion coverage")
        seen.add(row["criterion_id"])
        if not isinstance(row["check_ids"],list) or len(row["check_ids"])!=len(set(row["check_ids"])) or not set(row["check_ids"])<=ids:raise ValueError("Unknown criterion check")
        if not isinstance(row["not_verified_reason"],str) or (bool(row["check_ids"])==bool(row["not_verified_reason"].strip())):raise ValueError("Each criterion needs checks OR explicit not-verified reason")
    return {"case_id":case_id,"status":"produced_pending_independent_corroboration","native_verified":False,
            "sme_qualified":False,"private_holdout_validated":False,"unknowns":list(result["unknowns"]),
            "not_verified_criteria":[r["criterion_id"] for r in coverage if r["not_verified_reason"].strip()],
            "stack_claim_complete":all(v not in ("NOT_VERIFIED","unknown") for v in result["stack"].values())}


def native_template(role_id, root=ROOT):
    case=plan(role_id,root)["cases"][0];cid=case["case_id"]
    return {"case_id":cid,"case_sha256":digest(case),"revision":"REPLACE_WITH_EXACT_40_HEX_REVISION",
            "stack":{"name":case["native_stack"],"version":"NOT_VERIFIED","environment":"NOT_VERIFIED"},
            "checks":[],"artifacts":[],
            "coverage":[{"criterion_id":cid+":criterion:"+str(i+1),"check_ids":[],
                         "not_verified_reason":criterion} for i,criterion in enumerate(case["acceptance"])],
            "unknowns":list(case["required_native_evidence"]),"producer":role_id,"consumer":case["handoff"]}


def calibrate(records, policy, root=ROOT):
    """Bounded matched-context observation summary; no benchmark certification.

    Thresholds are supplied and digest-bound before trials, never fitted to the
    answers. Wilson intervals summarize supplied binary observations only. Trial
    authenticity, independence and private holdout are not inferred from JSON.
    """
    fields={"schema_version","partition","binding","families"}
    if not isinstance(policy,dict) or set(policy)!=fields or type(policy["schema_version"]) is not int or policy["schema_version"]!=1 or policy["partition"]!=PARTITION:
        raise ValueError("Calibration supports explicit public development policy only")
    binding=policy["binding"]
    if not isinstance(binding,dict) or set(binding)!={"model","effort","environment_sha256","dataset_sha256","cost_unit"} or any(not isinstance(v,str) or not v.strip() for v in binding.values()):raise ValueError("Matched model, effort, environment, dataset and cost unit required")
    for key in ("environment_sha256","dataset_sha256"):
        if len(binding[key])!=64 or any(c not in "0123456789abcdef" for c in binding[key]):raise ValueError("Invalid calibration context digest")
    families=policy["families"]
    catalog=load(root)
    if binding["dataset_sha256"]!=digest(catalog):raise ValueError("Drifted calibration dataset")
    known={c["case_id"]:c for c in catalog["cases"]}
    if not isinstance(families,dict) or not families or not set(families)<={c["harness"] for c in known.values()}:raise ValueError("Unknown calibration family")
    for family,limits in families.items():
        if not isinstance(limits,dict) or set(limits)!={"min_observations","max_error_rate"}:raise ValueError("Incomplete predeclared threshold")
        if type(limits["min_observations"]) is not int or not 1<=limits["min_observations"]<=100000:raise ValueError("Invalid observation minimum")
        rate=limits["max_error_rate"]
        if type(rate) not in (int,float) or not math.isfinite(rate) or not 0<=rate<=1:raise ValueError("Invalid maximum error rate")
    if not isinstance(records,list) or len(records)>100000:raise ValueError("Bounded trial list required")
    buckets={family:{"passed":0,"failed":0,"not_run":0,"inconclusive":0,"latency_ms":[],"cost_estimated":0.0,"cost_measured":0.0,"cost_unknown":0} for family in families}
    seen=set();policy_sha=digest(policy)
    for row in records:
        if not isinstance(row,dict) or set(row)!={"case_id","attempt","outcome","latency_ms","cost","policy_sha256","binding"}:raise ValueError("Incomplete calibration trial")
        cid=row["case_id"]
        if cid not in known or known[cid]["harness"] not in families:raise ValueError("Unknown trial case/family")
        if row["binding"]!=binding or row["policy_sha256"]!=policy_sha:raise ValueError("Unmatched or post-hoc trial policy/context")
        if type(row["attempt"]) is not int or not 1<=row["attempt"]<=100000 or (cid,row["attempt"]) in seen:raise ValueError("Invalid/duplicate trial identity")
        seen.add((cid,row["attempt"]))
        if row["outcome"] not in ("passed","failed","not_run","inconclusive"):raise ValueError("Unknown trial outcome")
        latency=row["latency_ms"]
        if latency is not None and (type(latency) not in (int,float) or not math.isfinite(latency) or latency<0):raise ValueError("Invalid trial latency")
        cost=row["cost"]
        if not isinstance(cost,dict) or set(cost)!={"kind","amount"} or cost["kind"] not in ("estimated","measured","unknown"):raise ValueError("Explicit cost evidence class required")
        if cost["kind"]=="unknown":
            if cost["amount"] is not None:raise ValueError("Unknown cost cannot carry amount")
        elif type(cost["amount"]) not in (int,float) or not math.isfinite(cost["amount"]) or cost["amount"]<0:raise ValueError("Invalid trial cost")
        b=buckets[known[cid]["harness"]];b[row["outcome"]]+=1
        if latency is not None:b["latency_ms"].append(latency)
        if cost["kind"]=="unknown":b["cost_unknown"]+=1
        else:b["cost_"+cost["kind"]]+=cost["amount"]
    rows=[];z=1.959963984540054
    for family,b in buckets.items():
        n=b["passed"]+b["failed"];k=b["failed"];limits=families[family]
        if n:
            rate=k/n;den=1+z*z/n;center=(rate+z*z/(2*n))/den
            margin=z*math.sqrt((rate*(1-rate)+z*z/(4*n))/n)/den
            interval=[max(0,center-margin),min(1,center+margin)]
        else:rate=None;interval=[0.0,1.0]
        enough=n>=limits["min_observations"] and not b["not_run"] and not b["inconclusive"]
        conclusion="threshold_met" if enough and interval[1]<=limits["max_error_rate"] else "threshold_failed" if enough and interval[0]>limits["max_error_rate"] else "inconclusive"
        rows.append({"family":family,"numerator_errors":k,"denominator_binary_observations":n,
                     "attempts_including_unknown":sum(b[x] for x in ("passed","failed","not_run","inconclusive")),
                     "not_run":b["not_run"],"inconclusive":b["inconclusive"],"error_rate":rate,
                     "wilson95_error_interval":interval,"conclusion":conclusion,
                     "latency_samples":len(b["latency_ms"]),"latency_max_ms":max(b["latency_ms"],default=None),
                     "cost_estimated":b["cost_estimated"],"cost_measured":b["cost_measured"],"cost_unknown_trials":b["cost_unknown"]})
    return {"schema_version":1,"partition":PARTITION,"policy_sha256":policy_sha,"families":rows,"cost_unit":binding["cost_unit"],
            "private_holdout_validated":False,"sme_qualified":False,"observations_authenticated":False,
            "notice":"Public matched-context supplied observations; thresholds do not authorize promotion or establish general superiority, trial independence, or agent qualification."}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=("validate","plan","run","template","check","calibrate"));parser.add_argument("--role")
    parser.add_argument("--case");parser.add_argument("--result")
    parser.add_argument("--policy")
    args=parser.parse_args(argv)
    try:
        if args.command=="validate":result={"valid":True,"roles":len(load()["cases"])}
        elif args.command=="plan":result=plan(args.role)
        elif args.command=="run":result=run(args.role)
        elif args.command=="template":
            if not args.role:raise ValueError("Template requires --role")
            result=native_template(args.role)
        elif args.command=="check":
            if not args.case or not args.result:raise ValueError("Check requires --case and --result")
            result=check_native_result(args.case,load_json(args.result))
        else:
            if not args.result or not args.policy:raise ValueError("Calibrate requires --result and --policy")
            result=calibrate(load_json(args.result),load_json(args.policy))
        print(json.dumps(result,ensure_ascii=True,indent=2,allow_nan=False))
        return 0 if result.get("passed",True) else 1
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print(json.dumps({"error":str(exc),"qualification":"NOT_VERIFIED"}));return 2


if __name__=="__main__":raise SystemExit(main())
