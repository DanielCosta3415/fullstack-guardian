"""Offline, data-only professional qualification registry.

No model, generated grader, shell, provider, or Python expression is executed.
A JSON observation is not authenticated evidence: even successful checks are
OBSERVED_NOT_CERTIFIED until an independent authorized review authenticates runs.
Public corpus is DEVELOPMENT, never a private holdout.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
import stat
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BINDINGS=('revision','profile_sha256','model','harness_sha256','stack_sha256','corpus_sha256')
HASH_FIELDS=set(BINDINGS)-{'model','revision'}
MAX_BYTES=4_000_000


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def load_json(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>MAX_BYTES:
        raise ValueError('Expected bounded regular JSON file')
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate JSON key')
            result[key]=value
        return result
    descriptor=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_BINARY',0))
    with os.fdopen(descriptor,'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):raise ValueError('Expected regular JSON file')
        content=stream.read(MAX_BYTES+1)
    if len(content)>MAX_BYTES:raise ValueError('JSON file exceeds bound')
    return json.loads(content.decode('utf-8-sig'),object_pairs_hook=unique,
                      parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Non-finite number')))


def _typed_value(value, schema):
    """Validate the bounded schema subset used by public typed cases."""
    kind=schema['type']
    valid={'boolean':lambda:type(value) is bool,
           'integer':lambda:type(value) is int,
           'number':lambda:type(value) is int or type(value) is float and math.isfinite(value),
           'string':lambda:isinstance(value,str),
           'array':lambda:isinstance(value,list) and all(_typed_value(v,schema['items']) for v in value),
           'object':lambda:isinstance(value,dict) and set(value)==set(schema['properties']) and all(_typed_value(value[k],s) for k,s in schema['properties'].items())}[kind]()
    return valid and ('enum' not in schema or any(value==v for v in schema['enum']))


def _typed_schema(schema, depth=0):
    # Not a general JSON Schema implementation: unknown assertions fail closed.
    if depth>8 or not isinstance(schema,dict):raise ValueError('Invalid typed artifact schema')
    kind=schema.get('type')
    if kind not in ('boolean','integer','number','string','array','object'):raise ValueError('Unsupported typed artifact type')
    allowed={'type','description'}
    if kind=='object':
        allowed|={'properties','required','additionalProperties'}
        props=schema.get('properties');required=schema.get('required')
        if not isinstance(props,dict) or not 1<=len(props)<=100 or any(not isinstance(k,str) or not k for k in props):raise ValueError('Invalid typed object properties')
        if not isinstance(required,list) or any(not isinstance(k,str) for k in required) or len(required)!=len(set(required)) or set(required)!=set(props) or schema.get('additionalProperties') is not False:raise ValueError('Typed object requires every declared property exactly once')
        for child in props.values():_typed_schema(child,depth+1)
    elif kind=='array':
        allowed.add('items');_typed_schema(schema.get('items'),depth+1)
    else:
        allowed.add('enum')
    if set(schema)-allowed:raise ValueError('Unsupported typed schema assertion')
    if 'description' in schema and (not isinstance(schema['description'],str) or not schema['description'].strip()):raise ValueError('Invalid typed field description')
    if 'enum' in schema:
        values=schema['enum']
        base={k:v for k,v in schema.items() if k!='enum'}
        if not isinstance(values,list) or not 1<=len(values)<=1000 or any(not _typed_value(v,base) for v in values) or any(v in values[:i] for i,v in enumerate(values)):raise ValueError('Invalid typed enum')


def validate(corpus):
    if not isinstance(corpus,dict):raise ValueError('Expected corpus object')
    if corpus.get('schema_version')!=1 or corpus.get('evidence_class')!='PROFESSIONAL_CASE_DESIGN':
        raise ValueError('Unsupported qualification corpus')
    cases=corpus.get('cases',[])
    if not isinstance(cases,list) or not cases:raise ValueError('No qualification cases')
    ids=set();agents=set()
    for case in cases:
        if not isinstance(case,dict):raise ValueError('Expected case object')
        required=('id','agent_id','agent_type','scenario','family','split','artifacts','rubric','unsafe_outcomes','oracle')
        if any(not case.get(key) for key in required):raise ValueError('Incomplete professional case')
        if any(not isinstance(case[k],str) for k in ('id','agent_id','agent_type','scenario','family','split')):raise ValueError('Case identity and scenario must be strings')
        if not isinstance(case['artifacts'],dict) or not isinstance(case['rubric'],list) or not isinstance(case['unsafe_outcomes'],list):raise ValueError('Malformed artifact/rubric/safety contract')
        if case.get('execution_status')!='NOT_EXECUTED':raise ValueError('Design corpus cannot embed passed results')
        if case['id'] in ids:raise ValueError('Duplicate qualification case')
        ids.add(case['id']);agents.add(case['agent_id'])
        if case['split']!='development':raise ValueError('Public corpus must not claim private holdout')
        oracle=case['oracle']
        if not isinstance(oracle,dict) or oracle.get('candidate_may_edit_oracle') is not False:raise ValueError('Candidate cannot own oracle')
        if oracle.get('kind') not in ('structured_exact','independent_sme'):raise ValueError('Unknown oracle')
        if oracle['kind']=='structured_exact':
            if not isinstance(oracle.get('expected'),dict) or not oracle['expected']:raise ValueError('Missing deterministic postconditions')
            schema=case['artifacts'].get('schema')
            _typed_schema(schema)
            if schema['type']!='object' or not _typed_value(oracle['expected'],schema):raise ValueError('Oracle violates typed artifact schema')
        elif oracle.get('review_required') is not True:raise ValueError('Open artifacts require SME review')
    return {'valid':True,'case_count':len(cases),'agent_count':len(agents),
            'development_cases':len(cases),'private_holdout_cases':0,
            'corpus_sha256':digest(corpus),'qualification':'NOT_EVALUATED'}


def preview(corpus,agent=None):
    validate(corpus)
    # Oracle answers are not provided to candidate requests. This does not turn
    # a publicly distributed development set into secret holdout evidence.
    return [{'id':case['id'],'agent_id':case['agent_id'],'agent_type':case['agent_type'],
             'scenario':case['scenario'],'family':case['family'],'split':case['split'],
             'artifacts':case['artifacts'],'rubric':case['rubric'],'unsafe_outcomes':case['unsafe_outcomes']}
            for case in corpus['cases'] if agent is None or case['agent_id']==agent]


def _binding_valid(bindings):
    if not isinstance(bindings,dict) or any(not isinstance(bindings.get(k),str) or not bindings[k].strip() for k in BINDINGS):return False
    for key in HASH_FIELDS:
        if len(bindings[key])!=64 or any(c not in '0123456789abcdef' for c in bindings[key]):return False
    return len(bindings['revision'])==40 and all(c in '0123456789abcdef' for c in bindings['revision'])


def evaluate(corpus,observations,context,*,trust_observations=False,now=None):
    """Compare observed artifacts; never infer correctness from prose/check OK.

    Context is operator-supplied expected binding per profile, not authentication.
    Native/model execution stays a separate opt-in harness and must be reviewed.
    """
    validate(corpus)
    if not trust_observations:raise ValueError('Explicit --trust-observations required; does not certify provenance')
    if not isinstance(context,dict) or not isinstance(context.get('profiles'),dict):raise ValueError('Expected per-profile context')
    if type(context.get('minimum_repetitions',2)) is not int or context.get('minimum_repetitions',2)<2:raise ValueError('At least two repetitions required')
    if not isinstance(observations,list):raise ValueError('Observations must be a list')
    now=now or dt.datetime.now(dt.timezone.utc)
    cases={c['id']:c for c in corpus['cases']};rows=[];seen=set();coverage={};total_cost=0.0;cost_unknown=False
    for obs in observations:
        if not isinstance(obs,dict):raise ValueError('Invalid observation')
        case=cases.get(obs.get('case_id'));state='INVALID';reason='Unknown case';run=obs.get('run_id')
        if case:
            key=(case['id'],run)
            expected=context['profiles'].get(case['agent_id'])
            actual=obs.get('bindings')
            if not isinstance(run,str) or not run or key in seen:reason='Missing or duplicate run identity'
            elif not _binding_valid(expected) or actual!=expected or expected['corpus_sha256']!=digest(corpus):
                state='STALE';reason='Revision/profile/model/harness/stack/corpus binding differs or missing'
            elif obs.get('agent_type')!=case['agent_type'] or obs.get('agent_id')!=case['agent_id']:
                reason='Profile identity mismatch'
            elif obs.get('artifact_sha256')!=digest(obs.get('artifact')):
                reason='Artifact integrity mismatch'
            else:
                seen.add(key)
                try:
                    expires=dt.datetime.fromisoformat(obs['valid_until'].replace('Z','+00:00'))
                    captured=dt.datetime.fromisoformat(obs['captured_at'].replace('Z','+00:00'))
                    if expires.tzinfo is None or captured.tzinfo is None or not captured<=now<expires or (expires-captured).total_seconds()>30*86400:
                        raise ValueError('Invalid validity window')
                except (KeyError,ValueError,TypeError):
                    state='STALE';reason='Expired, future, missing or excessive validity window'
                else:
                    artifact=obs.get('artifact');oracle=case['oracle']
                    if obs.get('abstained') is True:
                        state='ABSTAINED';reason='Explicit abstention; not successful coverage'
                    elif obs.get('unsafe_outcome_observed') is not False:
                        state='BLOCKED';reason='Unsafe outcomes not explicitly excluded by observer'
                    elif oracle['kind']=='independent_sme':
                        state='REQUIRES_SME';reason='Domain correctness requires independent authenticated SME review; JSON approval is not certification'
                    elif _typed_value(artifact,case['artifacts']['schema']) and artifact==oracle['expected']:
                        state='OBSERVED_PASS';reason='All exact typed domain postconditions satisfied; provenance unauthenticated'
                    else:
                        state='FAIL';reason='Structured domain postconditions differ (check OK is irrelevant)'
            coverage.setdefault(case['agent_id'],{}).setdefault(case['id'],[]).append(state)
        cost=obs.get('cost_usd')
        if type(cost) in (int,float) and 0<=cost<=1_000_000:total_cost+=cost
        else:cost_unknown=True
        rows.append({'case_id':obs.get('case_id'),'run_id':run,'state':state,'reason':reason})
    repetitions=context.get('minimum_repetitions',2)
    covered=[case_id for per_agent in coverage.values() for case_id,states in per_agent.items() if states.count('OBSERVED_PASS')>=repetitions]
    return {'schema_version':1,'evidence_class':'PROFESSIONAL_OBSERVATIONS',
            'qualification':'OBSERVED_NOT_CERTIFIED','provenance_authenticated':False,
            'warning':'Operator JSON and hashes do not authenticate agent execution or SME competence.',
            'corpus_sha256':digest(corpus),'cases_total':len(cases),'agents_total':len({c['agent_id'] for c in cases.values()}),
            'agent_observations':{aid:{'cases_attempted':len(per_agent),'cases_repeated_pass':sum(states.count('OBSERVED_PASS')>=repetitions for states in per_agent.values()),'qualification':'NOT_CERTIFIED'} for aid,per_agent in sorted(coverage.items())},
            'cases_observed_repeated_pass':len(covered),'unobserved_or_unqualified_cases':sorted(set(cases)-set(covered)),
            'abstentions':sum(r['state']=='ABSTAINED' for r in rows),'cost_usd_reported':round(total_cost,6),
            'cost_complete':not cost_unknown,'private_holdout_validated':False,'minimum_repetitions':repetitions,
            'rows':rows}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['validate','preview','evaluate-ingest'])
    parser.add_argument('--corpus',type=Path,default=ROOT/'core/qualification-cases-v1.json')
    parser.add_argument('--agent');parser.add_argument('--observations',type=Path);parser.add_argument('--context',type=Path)
    parser.add_argument('--trust-observations',action='store_true')
    args=parser.parse_args(argv);corpus=load_json(args.corpus)
    if args.command=='validate':result=validate(corpus)
    elif args.command=='preview':result=preview(corpus,args.agent)
    else:
        if not args.observations or not args.context:parser.error('--observations and --context required')
        result=evaluate(corpus,load_json(args.observations),load_json(args.context),trust_observations=args.trust_observations)
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False));return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError,TypeError) as exc:raise SystemExit(str(exc))
