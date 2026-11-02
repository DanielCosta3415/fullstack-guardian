"""Opt-in repeated native role-specific public transfer evaluation.

No candidate code executes. Native role/session/parent/tool observations are
corroborated locally; this remains public development evidence, not certification.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

try:
    from . import guardian_transfer_cases as transfer
    from . import test_native_qualification as native
    from .guardian_professional_review import _plain
except ImportError:
    import guardian_transfer_cases as transfer
    import test_native_qualification as native
    from guardian_professional_review import _plain

ROOT=Path(__file__).resolve().parents[1]
q=transfer.q


def plan(corpus, repetitions=2):
    q.validate(corpus)
    if type(repetitions) is not int or not 2<=repetitions<=5: raise ValueError('Repetitions must be2..5')
    grouped={}
    for case in corpus['cases']:
        group=grouped.setdefault(case['agent_type'],{'agent_id':case['agent_id'],'agent_type':case['agent_type'],'cases':[]})
        group['cases'].append(transfer.public(case))
    if len(grouped)!=39: raise ValueError('Expected39native roles')
    return [dict(group,task_name=f'transfer_{index:02d}_trial_{trial}',trial=trial)
            for trial in range(1,repetitions+1) for index,group in enumerate(grouped.values())]


def prompt(selected):
    if not 78<=len(selected)<=195 or len({x['task_name'] for x in selected})!=len(selected): raise ValueError('Incomplete or duplicate transfer inventory')
    # Rebuild allowlist even if a caller accidentally supplies host-only fields.
    public=[{key:item[key] for key in ('task_name','trial','agent_id','agent_type')} |
            {'cases':[{key:case[key] for key in ('id','agent_id','agent_type','scenario','artifacts')} for case in item['cases']]}
            for item in selected]
    return '''Authorized bounded PUBLIC_TRANSFER_DEVELOPMENT evaluation. Use only native collaboration spawn/wait/close/list operations. No shell, filesystem, network, connectors or credentials. Execute EVERY inventory entry exactly once using its exact agent_type and task_name, fork_turns="none", without model or reasoning overrides. Start A00 first. At most three active children. Each trial must be a fresh native child, with no prior answers, no substitutions or extra children. Never retry failed trials to select favorable results. Give each child only its own cases. It must independently compute supplied data/specification outputs and return one pure JSON object {"case_results":[{"case_id":"exact supplied id","result":{...typed output...}},...]}, no Markdown or tools. Preserve every exact case ID once. Array order is significant unless the task explicitly requests sorted output. All required object fields must occur with exact types; integers never accept booleans. These are synthetic data-only public transfer tasks, not real stack execution, private holdout or professional certification. Do not access source oracles. Do not claim any unperformed execution. The supervisor corroborates native session/model/role/tool metadata and grades outputs independently. Complete all entries or report quota/failure honestly.
BEGIN_PUBLIC_TRANSFER_TASKS
'''+json.dumps(public,ensure_ascii=False,separators=(',',':'))+'\nEND_PUBLIC_TRANSFER_TASKS\n'


def grade_child(item,artifact,case_map):
    if not isinstance(artifact,dict) or set(artifact)!={'case_results'}: raise ValueError('Closed result object required')
    rows=artifact['case_results'];wanted={c['id'] for c in item['cases']}
    if not isinstance(rows,list) or len(rows)!=len(wanted): raise ValueError('Incomplete case results')
    seen=set();graded=[]
    for row in rows:
        if not isinstance(row,dict) or set(row)!={'case_id','result'}: raise ValueError('Closed case row required')
        cid=row['case_id']
        if not isinstance(cid,str) or cid not in wanted or cid in seen: raise ValueError('Unknown or duplicate case')
        seen.add(cid);graded.append(transfer.grade(case_map[cid],row['result']))
    return graded


def collect(session_root,parent,selected,corpus):
    paths=list(Path(session_root).rglob('*.jsonl'))
    if len(paths)>20000: raise ValueError('Session inventory exceeds bound')
    parents=[];children=[]
    for path in paths:
        if path.is_symlink() or path.stat().st_size>native.LIMIT: continue
        try:
            with path.open(encoding='utf8') as stream: meta=json.loads(stream.readline()).get('payload',{})
        except (ValueError,OSError): continue
        if meta.get('id')==parent: parents=native.read_session(path)
        source=meta.get('source',{})
        spawn=source.get('subagent',{}).get('thread_spawn',{}) if isinstance(source,dict) else {}
        if spawn.get('parent_thread_id')==parent: children.append((meta,path,spawn))
    for event in parents:
        p=event.get('payload',{})
        if event.get('type')=='response_item' and p.get('type') in ('function_call','custom_tool_call'):
            if p.get('namespace')!='collaboration' or p.get('name') not in ('spawn_agent','wait','wait_agent','close_agent','list_agents'):
                raise ValueError('Unauthorized parent tool in data-only transfer evaluation')
    parent_models={e.get('payload',{}).get('model') for e in parents if e.get('type')=='turn_context' and e.get('payload',{}).get('model')}
    parent_efforts={e.get('payload',{}).get('effort',e.get('payload',{}).get('reasoning_effort')) for e in parents if e.get('type')=='turn_context' and e.get('payload',{}).get('effort',e.get('payload',{}).get('reasoning_effort')) is not None}
    if len(parent_models)>1 or len(parent_efforts)>1: raise ValueError('Actual parent model or effort changed')
    pairs=native.parent_pairs(parents);seen=set();rows=[];artifacts={}
    case_map={case['id']:case for case in corpus['cases']}
    known={'/root/'+item['task_name'] for item in selected}
    for meta,_,spawn in children:
        if (meta.get('agent_path') or spawn.get('agent_path')) not in known: rows.append({'state':'UNEXPECTED_CHILD'})
    for item in selected:
        path='/root/'+item['task_name']
        matches=[p for meta,p,s in children if (meta.get('agent_path') or s.get('agent_path'))==path]
        row={key:item[key] for key in ('task_name','agent_id','agent_type','trial')};row['state']='INVALID'
        try:
            if len(matches)!=1 or pairs.count((path,item['agent_type']))!=1: raise ValueError('Missing/duplicate child or paired spawn')
            child_rows=native.read_session(matches[0])
            child=native.inspect_child(child_rows,item,parent,set(pairs))
            if parent_models and child['model'] not in parent_models: raise ValueError('Actual child model differs from parent')
            efforts={p.get('effort',p.get('reasoning_effort')) for e in child_rows if e.get('type')=='turn_context' for p in [e.get('payload',{})] if p.get('effort',p.get('reasoning_effort')) is not None}
            if len(efforts)>1: raise ValueError('Actual child effort changed')
            if parent_efforts and efforts and efforts!=parent_efforts: raise ValueError('Actual child effort differs from parent')
            if child['session_id'] in seen: raise ValueError('Duplicate native child session')
            seen.add(child['session_id']);graded=grade_child(item,child['artifact'],case_map)
            artifacts[item['task_name']]=child['artifact']
            row.update(state='CORROBORATED',model=child['model'],observed_effort=next(iter(efforts)) if efforts else None,cases=graded,
                       parent_model_observed=bool(parent_models),parent_effort_observed=bool(parent_efforts),
                       session_sha256=native.sha(matches[0]))
        except (ValueError,OSError,TypeError,KeyError) as error: row['reason']=str(error)
        rows.append(row)
    return rows,artifacts


def assess(rows, selected):
    """Every planned observation counts; failures cannot disappear by omission."""
    wanted={item['task_name']:item for item in selected}
    known=[r.get('task_name') for r in rows]
    counts=Counter(known)
    complete=len(rows)==len(selected) and len(set(known))==len(selected) and set(known)==set(wanted)
    models={role:{r.get('model') for r in rows if r.get('agent_type')==role and r.get('state')=='CORROBORATED'} for role in {x['agent_type'] for x in selected}}
    matched=all(len(v)==1 and all(isinstance(model,str) and model for model in v) for v in models.values())
    efforts={role:{r.get('observed_effort') for r in rows if r.get('agent_type')==role and r.get('state')=='CORROBORATED'} for role in models}
    effort_drift=any(len(values-{None})>1 for values in efforts.values())
    effort_complete=all(len(values)==1 and None not in values for values in efforts.values())
    passed=0;observed=0
    def valid_cases(row,item):
        if item is None or counts[row.get('task_name')]!=1 or row.get('state')!='CORROBORATED': return None
        if any(row.get(k)!=item[k] for k in ('agent_id','agent_type','trial')): return None
        expected={c['id'] for c in item['cases']};cases=row.get('cases',[])
        if len(cases)!=len(expected) or {c.get('case_id') for c in cases}!=expected: return None
        return cases
    for row in rows:
        item=wanted.get(row.get('task_name'))
        cases=valid_cases(row,item)
        if cases is None: continue
        observed+=len(cases);passed+=sum(c.get('passed') is True for c in cases)
    total=sum(len(x['cases']) for x in selected)
    by_role={}
    for role in sorted(models):
        role_selected=[item for item in selected if item['agent_type']==role]
        role_rows=[row for row in rows if row.get('agent_type')==role]
        planned=sum(len(item['cases']) for item in role_selected)
        role_observed=0;role_passed=0
        for row in role_rows:
            item=wanted.get(row.get('task_name'))
            cases=valid_cases(row,item)
            if cases is None or item['agent_type']!=role: continue
            role_observed+=len(cases);role_passed+=sum(c.get('passed') is True for c in cases)
        by_role[role]={'planned_judgments':planned,'observed_judgments':role_observed,
                       'passed_judgments':role_passed,'failed_or_missing_judgments':planned-role_passed,
                       'planned_native_trials':len(role_selected),
                       'failed_observed_judgments':role_observed-role_passed,
                       'missing_judgments':planned-role_observed,
                       'observed_error_rate_wilson95':wilson(role_observed-role_passed,role_observed),
                       'false_positive_negative_rates':'NOT_DEFINED_FOR_MIXED_STRUCTURED_TASKS'}
    return {'expected_children':len(selected),'corroborated_children':sum(r.get('state')=='CORROBORATED' for r in rows),
            'expected_judgments':total,'observed_judgments':observed,'passed_judgments':passed,
            'failed_or_missing_judgments':total-passed,'same_actual_model_per_role':matched,
            'all_planned_observations_passed':complete and matched and not effort_drift and observed==passed==total,
            'observed_effort_drift':effort_drift,'all_role_effort_observed':effort_complete,
            'qualification':'OBSERVED_TRANSFER_NOT_CERTIFIED','private_holdout_validated':False,
            'per_role':by_role,'cost':{'kind':'unknown','amount':None},
            'statistical_limit':'Judgments within a child and repeated public inputs are correlated; Wilson95 is descriptive, not a calibrated independent-trial confidence guarantee.'}


def wilson(errors,total):
    if not total: return None
    z=1.959963984540054;rate=errors/total;den=1+z*z/total
    center=(rate+z*z/(2*total))/den
    radius=z*math.sqrt(rate*(1-rate)/total+z*z/(4*total*total))/den
    return [max(0.0,center-radius),min(1.0,center+radius)]


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true');parser.add_argument('--out',type=Path)
    parser.add_argument('--seed',type=int,default=20261102);parser.add_argument('--variants',type=int,default=2)
    parser.add_argument('--repetitions',type=int,default=2);parser.add_argument('--timeout',type=int,default=7200)
    args=parser.parse_args(argv)
    if not 60<=args.timeout<=7200: parser.error('Timeout must be60..7200seconds')
    corpus=transfer.corpus(args.seed,args.variants);selected=plan(corpus,args.repetitions)
    if not args.run:
        print(json.dumps({'quota_consumed':False,'partition':transfer.PARTITION,'native_children_expected':len(selected),
                          'judgments_expected':sum(len(x['cases']) for x in selected),'plan':selected},indent=2));return 0
    executable=shutil.which('codex')
    if not executable or args.out is None: raise ValueError('CodexCLI and --out required')
    destination=_plain(args.out)
    if destination==ROOT or ROOT in destination.parents or destination.exists(): raise ValueError('New output directory outside source required')
    destination.mkdir(mode=0o700);private=destination/'private';private.mkdir(mode=0o700)
    project=destination/'project';project.mkdir()
    revision=subprocess.run(['git','-C',str(ROOT),'rev-parse','HEAD'],check=True,capture_output=True,text=True,timeout=15).stdout.strip()
    before=native.snapshot(ROOT)
    subprocess.run([sys.executable,'-B',str(ROOT/'install.py'),'--project',str(project),'--apply'],check=True,capture_output=True,timeout=180)
    profiles={a['name']:ROOT/a['file'] for a in q.load_json(ROOT/'core/agents.json')['agents']}
    for manifest in sorted((ROOT/'packs').glob('*/manifest.json')):
        pack=q.load_json(manifest)
        subprocess.run([sys.executable,'-B',str(ROOT/'tools/guardian_packs.py'),'install','--pack',pack['name'],'--project',str(project),'--apply'],check=True,capture_output=True,timeout=120)
        for agent in pack['agents']: profiles[agent['name']]=manifest.parent/agent['file']
    installed={native.sha(p) for p in (project/'.codex/agents').glob('*.toml')}
    profile_hashes={item['agent_type']:native.sha(profiles[item['agent_type']]) for item in selected}
    if not all(digest in installed for digest in profile_hashes.values()): raise ValueError('Installed profile bytes differ')
    public_plan=project/'public-tasks.json';public_plan.write_text(json.dumps(selected,indent=2),encoding='utf8')
    protected={str(p.relative_to(project)):native.sha(p) for p in project.rglob('*') if p.is_file()}
    native.private_write(private/'prompt.txt',prompt(selected))
    native.private_write(private/'events.jsonl','');native.private_write(private/'stderr.log','')
    started=time.monotonic()
    with (private/'prompt.txt').open('rb') as stdin,(private/'events.jsonl').open('a',encoding='utf8') as stdout,(private/'stderr.log').open('a',encoding='utf8') as stderr:
        process=subprocess.Popen(native.codex_command(executable,project),stdin=stdin,stdout=stdout,stderr=stderr,cwd=project)
        try: exitcode=process.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            process.terminate()
            try: process.wait(timeout=15)
            except subprocess.TimeoutExpired: process.kill();process.wait(timeout=15)
            exitcode='TIMEOUT_DESCENDANT_CLEANUP_NOT_VERIFIED'
    parent=None;quota=False
    for line in (private/'events.jsonl').read_text(encoding='utf8').splitlines():
        try: event=json.loads(line)
        except ValueError: continue
        if event.get('type')=='thread.started': parent=event.get('thread_id')
        if event.get('type')=='error' and any(x in str(event).lower() for x in ('quota','usage limit','rate limit')): quota=True
    session_root=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))/'sessions'
    rows,artifacts=collect(session_root,parent,selected,corpus) if parent else ([],{})
    unchanged=before==native.snapshot(ROOT) and revision==subprocess.run(['git','-C',str(ROOT),'rev-parse','HEAD'],check=True,capture_output=True,text=True,timeout=15).stdout.strip()
    fixture_unchanged=all((project/p).is_file() and native.sha(project/p)==digest for p,digest in protected.items())
    native.private_write(private/'artifacts.json',json.dumps(artifacts,indent=2))
    result={'schema_version':1,'partition':transfer.PARTITION,'revision':revision,
            'profile_sha256':profile_hashes,'harness_sha256':native.sha(Path(__file__)),
            'generator_sha256':native.sha(Path(transfer.__file__)),'corpus_sha256':q.digest(corpus),
            'public_task_inventory_sha256':q.digest(selected),
            'stack':{'python':platform.python_version(),'platform':platform.platform(),'codex':subprocess.run([executable,'--version'],capture_output=True,text=True,check=True,timeout=15).stdout.strip()},
            'seed':args.seed,'variants_per_role':args.variants,'repetitions':args.repetitions,
            'budget':{'native_children':len(selected),'maximum_concurrency':3,'timeout_seconds':args.timeout,'automatic_retries':0,'cost_limit_observed':False},
            'source_unchanged':unchanged,'installed_fixtures_unchanged':fixture_unchanged,
            'exit_code':exitcode,'quota_error_observed':quota,'elapsed_seconds':round(time.monotonic()-started,2),
            **assess(rows,selected),'rows':rows,
            'limits':['Public developer-designed tasks; no private holdout or SME certification',
                      'No child tools/candidate code/real framework or cloud executed',
                      'Oracle separation/no-tools validated procedurally, not OS isolation',
                      'Local mutable session evidence, not remote attestation',
                      'Repeated small samples do not establish world-tier reliability',
                      'Inherited Windows log DACL and timeout descendant cleanup not verified']}
    (destination/'summary-public.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result,indent=2))
    return 0 if exitcode==0 and unchanged and fixture_unchanged and result['all_planned_observations_passed'] else 1


if __name__=='__main__':
    try: raise SystemExit(main())
    except (OSError,ValueError,subprocess.SubprocessError) as error: raise SystemExit(str(error))
