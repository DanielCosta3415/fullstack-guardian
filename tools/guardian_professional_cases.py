"""Versioned public professional artifact tasks: objective subscopes, never SME certification.

Trusted, stdlib-only oracles read data; no candidate code or commands execute.
"""
import argparse
import copy
import hashlib
import json
import math
import re
from pathlib import Path
from decimal import Decimal, InvalidOperation, localcontext, ROUND_HALF_EVEN
from statistics import median

try:
    from . import guardian_qualification as q
    from .guardian_professional_review import _plain, _read, _json, _fields
except ImportError:
    import guardian_qualification as q
    from guardian_professional_review import _plain, _read, _json, _fields

ROOT=Path(__file__).resolve().parents[1]

try:
    from .guardian_professional_protocol import VERSION as PROTOCOL_VERSION, CONTRACTS
except ImportError:
    from guardian_professional_protocol import VERSION as PROTOCOL_VERSION, CONTRACTS


def oracle(kind,d):
    """Allowlisted trusted projections over fixed fixtures, not candidate graders."""
    with localcontext() as context:
        context.prec=28
        context.rounding=ROUND_HALF_EVEN
        return _oracle(kind,d)


def _oracle(kind,d):
    if kind=='obligations':
        covered={x for t in d['tasks'] for x in t['obligations']}
        return {'missing_obligations':sorted(set(d['requested'])-covered),'unsafe_ready_tasks':sorted(t['id'] for t in d['tasks'] if t['ready'] and any(x not in d['verified_evidence'] for x in t['evidence']))}
    if kind=='cohorts':
        rates={r['cohort']:str(Decimal(r['retained'])/Decimal(r['activated'])) for r in d['cohorts']}
        return {'retention_rates':rates,'validated_interviews':len([x for x in d['interviews'] if x['observed']]),'value_validated':False}
    if kind=='conflicts':
        return {'conflicting_rules':sorted(r['id'] for r in d['rules'] if any(s['id']!=r['id'] and s['key']==r['key'] and s['value']!=r['value'] for s in d['rules'])),'decision':'BLOCKED_PENDING_AUTHORITY'}
    if kind=='tenant_flows':
        return {'unsafe_flow_ids':sorted(x['id'] for x in d['flows'] if not x['tenant_check'] or x['token_tenant']!=x['object_tenant']),'isolation_required':True,'kubernetes_required':False}
    if kind=='stale_response':
        accepted=[x for x in d['responses'] if x['request']==d['active_request'] and x['navigation']==d['active_navigation']]
        return {'accepted_response_ids':sorted(x['id'] for x in accepted),'rejected_response_ids':sorted(x['id'] for x in d['responses'] if x not in accepted)}
    if kind=='submission':
        effects={x['idempotency_key'] for x in d['requests'] if x['authenticated'] and x['valid']}
        return {'effect_count':len(effects),'preserve_input':True,'may_show_success':any(x['committed'] for x in d['responses']),'rejected_requests':sorted(x['id'] for x in d['requests'] if not x['authenticated'] or not x['valid'])}
    if kind=='focus':
        faults=[]
        if not d['escape_closes']:faults.append('escape')
        if not d['trap_enabled']:faults.append('focus_trap')
        if d['restore_target'] not in d['mounted_focusable']:faults.append('restore_target')
        return {'faults':sorted(faults),'safe_restore':next((x for x in d['fallback_order'] if x in d['mounted_focusable']),None),'screen_reader_verified':False}
    if kind=='locale':
        return {'minor_units':{r['id']:int(Decimal(r['amount'])*(10**r['currency_decimals'])) for r in d['amounts']},'rtl_locales':sorted(x for x in d['locales'] if x.split('-')[0] in ('ar','he','fa','ur')),'explicit_timezones':sorted(set(d['timezones']))}
    if kind=='ledger':
        effects={};duplicates=[]
        for e in d['events']:
            if e['key'] in effects:duplicates.append(e['id'])
            else:effects[e['key']]=e['delta_minor']
        return {'deduplicated_balance_minor':d['opening_minor']+sum(effects.values()),'duplicate_event_ids':sorted(duplicates),'unpublished_commits':sorted(x['id'] for x in d['transactions'] if x['committed'] and not x['outbox_durable'])}
    if kind=='contract':
        old=set(d['old_required']);new=set(d['new_required'])
        return {'removed_response_fields':sorted(old-set(d['new_response_fields'])),'added_required_request_fields':sorted(new-old),'unknown_enum_values':sorted(set(d['provider_enum'])-set(d['client_enum'])),'compatible':not(old-set(d['new_response_fields']) or new-old or set(d['provider_enum'])-set(d['client_enum']))}
    if kind=='fencing':
        return {'accepted_write_ids':sorted(x['id'] for x in d['writes'] if x['token']==d['current_token']),'rejected_write_ids':sorted(x['id'] for x in d['writes'] if x['token']!=d['current_token'])}
    if kind=='migration':
        return {'unsafe_steps':sorted(x['id'] for x in d['steps'] if (x['requires_not_null'] and d['null_rows']>0) or (x['drops_legacy'] and d['legacy_readers']>0)),'backfill_remaining':d['null_rows'],'contract_allowed':d['null_rows']==0 and d['legacy_readers']==0}
    if kind=='restore':
        bad=sorted(x['key'] for x in d['restored'] if d['expected_by_key'].get(x['key'])!=x['value'])
        missing=sorted(set(d['expected_by_key'])-{x['key'] for x in d['restored']})
        return {'mismatched_keys':bad,'missing_keys':missing,'recoverable':d['key_available'] and not bad and not missing,'blockers':(['key_unavailable'] if not d['key_available'] else [])+(['integrity'] if bad or missing else [])}
    if kind=='ssrf':
        import ipaddress
        bad=[]
        for hop in d['hops']:
            if any(not ipaddress.ip_address(ip).is_global for ip in hop['resolved_ips']):bad.append(hop['id'])
        return {'blocked_hops':sorted(bad),'network_requests_executed':0,'every_redirect_requires_revalidation':True}
    if kind=='jwt':
        return {'rejected_tokens':sorted(t['id'] for t in d['tokens'] if t['kid'] not in d['known_kids'] or t['alg'] not in d['allowed_algs'] or not t['signature_valid']),'algorithm_downgrade_allowed':False}
    if kind=='provenance':
        return {'rejected_artifacts':sorted(a['id'] for a in d['artifacts'] if a['revision']!=d['revision'] or a['workflow']!=d['workflow'] or not a['signature_valid']),'publication_authorized':False}
    if kind=='mutants':
        killed={m for t in d['tests'] for m in t['kills']}
        return {'surviving_mutants':sorted(set(d['mutants'])-killed),'tests_without_assertions':sorted(t['id'] for t in d['tests'] if not t['assertions']),'adequate':not(set(d['mutants'])-killed)}
    if kind=='latency':
        values=sorted(d['latency_ms']);p99=values[(99*len(values)+99)//100-1]
        return {'p99_ms':p99,'median_ms':median(values),'slo_met':p99<=d['slo_p99_ms'],'mean_ms':sum(values)/len(values),'environment_verified':False}
    if kind=='topology':
        unavailable=set(d['failed_zones']);reachable=[x['id'] for x in d['dependencies'] if x['required'] and not any(z not in unavailable for z in x['zones'])]
        return {'unavailable_dependencies':sorted(reachable),'ha_supported':not reachable,'kubernetes_required':False}
    if kind=='traces':
        ids={s['id'] for s in d['spans']}
        return {'orphan_spans':sorted(s['id'] for s in d['spans'] if s['parent'] is not None and s['parent'] not in ids),'missing_trace_context':sorted(s['id'] for s in d['spans'] if not s['trace']),'root_cause_verified':False}
    if kind=='cloud_plan':
        return {'blocked_resources':sorted(r['id'] for r in d['resources'] if r['stateful'] and ('delete' in r['actions'] or 'replace' in r['actions'])),'apply_authorized':False}
    if kind=='workflow':
        return {'unsafe_jobs':sorted(j['id'] for j in d['jobs'] if j['untrusted_code'] and (j['secret_access'] or j['write_token'])),'secrets_may_be_granted_to_untrusted_code':False}
    if kind=='boundary':
        return {'regression_inputs':sorted(x for x in d['inputs'] if (x>=d['threshold']) != (x>d['threshold'])),'expected_eligible':sorted(x for x in d['inputs'] if x>=d['threshold'])}
    if kind=='cost':
        return {'baseline_cost_minor':sum(x['units']*x['unit_price_minor'] for x in d['usage']),'commitment_cost_minor':d['commitment_minor'],'slo_violations':sorted(x['id'] for x in d['alternatives'] if x['rto_minutes']>d['max_rto_minutes'] or x['availability_ppm']<d['min_availability_ppm']),'purchase_authorized':False}
    if kind=='injection':
        return {'untrusted_tool_requests':sorted(x['id'] for x in d['documents'] if x['requests_tool']),'cross_tenant_documents':sorted(x['id'] for x in d['documents'] if x['tenant']!=d['request_tenant']),'tool_actions_authorized':[]}
    if kind=='counterexample':
        counter=sorted(x for x in d['inputs'] if not (x<d['bound']))
        return {'counterexamples':counter,'consensus_proves_claim':False,'claim_refuted':bool(counter)}
    if kind=='release_context':
        changes=sorted(k for k in d['approved_context'] if d['current_context'].get(k)!=d['approved_context'][k])
        return {'changed_context_fields':changes,'previous_approval_current':not changes,'production_ready':not changes and d['restore_tested'],'preview_ready':d['preview_tested']}
    if kind=='relevance':
        return {'relevant_document_ids':sorted(x['id'] for x in d['documents'] if x['subject']==d['question_subject'] and x['effective_from']<=d['as_of'] and (x['effective_until'] is None or x['effective_until']>=d['as_of'])),'lexical_match_sufficient':False}
    if kind=='backfill':
        result={str(k):v for k,v in d['existing'].items()}
        for row in d['batch']:
            if row['watermark']>d['committed_watermark']:result[row['key']]=row['value']
        return {'rows_by_key':result,'next_watermark':max([d['committed_watermark']]+[r['watermark'] for r in d['batch']]),'duplicate_effects_permitted':False}
    if kind=='di_lifetime':
        rank={'singleton':3,'scoped':2,'transient':1};bindings={x['id']:x for x in d['services']}
        return {'captive_dependencies':sorted(x['id']+'->'+dep for x in d['services'] for dep in x['depends_on'] if rank[x['lifetime']]>rank[bindings[dep]['lifetime']] and bindings[dep]['lifetime']=='scoped'), 'dotnet_runtime_executed':False}
    if kind=='windows_path':
        return {'literal_paths':d['paths'],'shell_interpolation_allowed':False,'delete_blocked':sorted(x['id'] for x in d['operations'] if x['reparse'] or not x['within_workspace']),'writes_allowed':not d['what_if'] and not d['cancelled']}
    if kind=='external_policy':
        missing=sorted(x for x in d['required_policies'] if x not in d['available_policies'])
        return {'decision':'ABSTAIN_POLICY_UNAVAILABLE' if missing else 'REQUIRES_AUTHENTICATED_POLICY_REVIEW','unverified_policy_ids':missing,'universal_compliance_claim_allowed':False}
    if kind=='currency':
        values={};invalid=[]
        for row in d['amounts']:
            try:
                value=Decimal(row['value']);scaled=value*(10**row['decimals'])
                if not value.is_finite() or value<0 or scaled!=scaled.to_integral_value():raise ValueError('Invalid amount')
                values[row['id']]=int(scaled)
            except (ValueError,InvalidOperation):invalid.append(row['id'])
        return {'minor_units':values,'rejected_amount_ids':sorted(invalid),'invalid_inputs_may_mutate_state':False}
    if kind=='webhook':
        rejected=[];effects=set()
        for x in d['deliveries']:
            if not x['signature_valid'] or abs(d['now']-x['timestamp'])>d['window_seconds']:rejected.append(x['id'])
            else:effects.add(x['event_id'])
        return {'rejected_deliveries':sorted(rejected),'effect_count':len(effects),'effect_event_ids':sorted(effects)}
    if kind=='dns':
        return {'unresolved_dependencies':sorted(x['id'] for x in d['dependencies'] if not x['dns_resolves'] or x['endpoint_network'] not in d['reachable_networks']),'provider_network_executed':False}
    if kind=='accessibility':
        return {'unassociated_errors':sorted(x['id'] for x in d['controls'] if x['error'] and not x['error_associated']),'inaccessible_controls':sorted(x['id'] for x in d['controls'] if not x['keyboard'] or not x['name'] or not x['role']),'duplicate_announcements':sorted(x['id'] for x in d['announcements'] if x['count']>1),'assistive_technology_verified':False}
    if kind=='permissions':
        return {'denied_request_ids':sorted(x['id'] for x in d['requests'] if not set(x['required_scopes'])<=set(x['token_scopes']) or x['token_tenant']!=x['object_tenant']),'denied_object_disclosure_allowed':False}
    if kind=='checksums':
        source={x['key']:x['value'] for x in d['source']};target={x['key']:x['value'] for x in d['target']}
        return {'mismatched_keys':sorted(k for k in set(source)|set(target) if source.get(k)!=target.get(k)),'equal_count_sufficient':False}
    if kind=='evidence_limits':
        return {'unsupported_claim_ids':sorted(x['id'] for x in d['claims'] if not set(x['required_evidence'])<=set(d['observed_evidence'])),'verified_claim_ids':sorted(x['id'] for x in d['claims'] if set(x['required_evidence'])<=set(d['observed_evidence'])),'may_invent_missing_evidence':False}
    raise ValueError('Unknown trusted oracle family')


def schema(value,depth=0,field=None):
    # Top-level protocol fields are public. Dynamic result-map keys and array
    # contents must never reveal oracle-derived IDs, values or cardinality.
    if isinstance(value,dict):
        if depth:return {'type':'object','additionalProperties':{}}
        return {'type':'object','properties':{k:schema(v,depth+1,k) for k,v in value.items()},'required':list(value),'additionalProperties':False}
    if isinstance(value,list):return {'type':'array','items':{},'description':'Ordered literal sequence.' if field=='literal_paths' else 'Unordered collection; preserve multiplicity.'}
    if type(value) is float:return {'type':'number','description':'Finite number; relative and absolute comparison tolerance 1e-9.'}
    return {'type':'boolean' if type(value) is bool else 'integer' if type(value) is int else 'number' if type(value) is float else ['string','null'] if value is None else 'string'}


def load(root=ROOT):
    root=Path(root);corpus=_json(root/'core/qualification-cases-v1.json');q.validate(corpus)
    originals={c['id']:c for c in corpus['cases'] if c['oracle']['kind']=='independent_sme'}
    index=_json(root/'eval/professional-cases/catalog.json')
    _fields(index,('schema_version','evidence_class','cases'))
    if index['schema_version']!=1 or index['evidence_class']!='PUBLIC_OBJECTIVE_SUBSCOPE_DESIGN' or not isinstance(index['cases'],list):raise ValueError('Invalid professional task catalog')
    seen=set();result=[]
    for case in index['cases']:
        _fields(case,('case_id','agent_id','source_case_sha256','fixture','fixture_sha256','engineering_status','objective_scope','remaining_semantic_review','rubric_trace'))
        cid=case['case_id']
        if cid not in originals or cid in seen or case['agent_id']!=originals[cid]['agent_id'] or case['source_case_sha256']!=q.digest(originals[cid]):raise ValueError('Unknown/duplicate/drifted source case')
        seen.add(cid)
        trace=case['rubric_trace']
        if not isinstance(trace,list) or len(trace)!=len(originals[cid]['rubric']):raise ValueError('Missing criterion traceability')
        for row,criterion in zip(trace,originals[cid]['rubric']):
            _fields(row,('dimension','requirement_sha256','assessment_scope','limitation'))
            if row['dimension']!=criterion['dimension'] or row['requirement_sha256']!=q.digest(criterion) or row['assessment_scope'] not in ('PARTIAL_OBJECTIVE','NOT_ASSESSED') or not isinstance(row['limitation'],str) or not row['limitation'].strip():raise ValueError('Invalid criterion traceability')
        if case['engineering_status']!='OBJECTIVE_FIXTURE_READY':raise ValueError('Incomplete objective fixture')
        if not isinstance(case['fixture'],str) or re.fullmatch(r'[0-9a-f]{16}\.json',case['fixture']) is None:raise ValueError('Unsafe fixture path')
        path=root/'eval/professional-cases'/case['fixture'];data=_read(path)
        if hashlib.sha256(data).hexdigest()!=case['fixture_sha256']:raise ValueError('Fixture hash drift')
        fixture=_json(path);_fields(fixture,('schema_version','case_id','family','task','input'))
        if fixture['schema_version']!=1 or fixture['case_id']!=cid or not isinstance(fixture['task'],str) or not fixture['task'].strip():raise ValueError('Invalid task fixture')
        expected=oracle(fixture['family'],fixture['input'])
        if fixture['family'] not in CONTRACTS or set(CONTRACTS[fixture['family']])!=set(expected):raise ValueError('Incomplete public output field contract')
        result.append({'manifest':case,'fixture':fixture,'schema':schema(expected),'expected':expected,'original':originals[cid]})
    if seen!=set(originals):raise ValueError('All 103 source cases must have explicit accounting')
    return result


def requests(root=ROOT):
    return [{'case_id':x['manifest']['case_id'],'agent_id':x['manifest']['agent_id'],'agent_type':x['original']['agent_type'],
             'scenario':x['original']['scenario'],'objective_task':x['fixture']['task'],'input':copy.deepcopy(x['fixture']['input']),
             'response_schema':x['schema'],'protocol_version':PROTOCOL_VERSION,'output_contract':copy.deepcopy(CONTRACTS[x['fixture']['family']]),'qualification':'PUBLIC_OBJECTIVE_SUBSCOPE_ONLY',
             'remaining_semantic_review':x['manifest']['remaining_semantic_review']} for x in load(root)]


def _matches(actual,expected,field=None):
    if type(expected) is float:
        if type(actual) not in (int,float):return False
        try:return math.isfinite(actual) and math.isclose(actual,expected,rel_tol=1e-9,abs_tol=1e-9)
        except OverflowError:return False
    if type(actual) is not type(expected):return False
    if isinstance(expected,dict):return set(actual)==set(expected) and all(_matches(actual[k],v,k) for k,v in expected.items())
    if isinstance(expected,list):
        if len(actual)!=len(expected):return False
        if field=='literal_paths':return all(_matches(a,b) for a,b in zip(actual,expected))
        remaining=list(actual)
        for wanted in expected:
            for index,observed in enumerate(remaining):
                if _matches(observed,wanted):remaining.pop(index);break
            else:return False
        return True
    return actual==expected


def grade(case_id,result,root=ROOT):
    items={x['manifest']['case_id']:x for x in load(root)}
    if case_id not in items:raise ValueError('Unknown professional case')
    item=items[case_id]
    # Canonical JSON distinguishes bool/int and rejects nonfinite values.
    q.digest(result)  # Reject nonfinite/unsupported JSON before comparisons.
    passed=_matches(result,item['expected'])
    return {'case_id':case_id,'protocol_version':PROTOCOL_VERSION,'objective_passed':passed,'result_sha256':q.digest(result),
            'fixture_sha256':item['manifest']['fixture_sha256'],'source_case_sha256':item['manifest']['source_case_sha256'],
            'qualification':'OBJECTIVE_SUBSCOPE_OBSERVED' if passed else 'OBJECTIVE_SUBSCOPE_FAILED',
            'sme_qualified':False,'private_holdout_validated':False,'remaining_semantic_review':item['manifest']['remaining_semantic_review']}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('validate');sub.add_parser('preview')
    g=sub.add_parser('grade');g.add_argument('--case',required=True);g.add_argument('--result',required=True)
    args=p.parse_args(argv)
    try:
        if args.command=='validate':
            rows=load();answer={'cases':len(rows),'agents':len({r['manifest']['agent_id'] for r in rows}),'objective_fixture_ready':len(rows),'sme_qualified':0,'private_holdout_validated':False}
        elif args.command=='preview':answer=requests()
        else:answer=grade(args.case,_json(args.result))
        print(json.dumps(answer,ensure_ascii=True,indent=2,allow_nan=False));return 0
    except (ValueError,OSError,TypeError,KeyError,RecursionError) as exc:
        print(json.dumps({'error':str(exc),'qualification':'NOT_VERIFIED'}));return 2


if __name__=='__main__':raise SystemExit(main())
