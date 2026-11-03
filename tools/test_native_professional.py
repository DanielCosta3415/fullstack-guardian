"""Opt-in native 39-role / 103-artifact public objective subscopes.

Default is preview; no native model calls unless --run is explicitly supplied.
Candidate code is never executed. All qualitative SME/holdout gates remain open.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

try:
    from . import guardian_professional_cases as cases
    from . import test_native_qualification as native
    from .guardian_professional_review import _plain, _fields
except ImportError:
    import guardian_professional_cases as cases
    import test_native_qualification as native
    from guardian_professional_review import _plain, _fields

ROOT=Path(__file__).resolve().parents[1]


def plan(root=ROOT):
    grouped={}
    for item in cases.requests(root):
        aid=item['agent_id']
        if aid not in grouped:
            grouped[aid]={'task_name':f'professional_{len(grouped):02d}','agent_id':aid,'agent_type':item['agent_type'],'cases':[]}
        grouped[aid]['cases'].append({k:v for k,v in item.items() if k not in ('agent_type','agent_id')})
    result=list(grouped.values())
    if len(result)!=39 or sum(len(x['cases']) for x in result)!=103 or any(not 2<=len(x['cases'])<=3 for x in result):raise ValueError('Expected 39 roles and 103 cases, two or three per child')
    return result


def batches(selected,batch_size=3):
    """Partition a single complete campaign; never retry or pool prior runs."""
    if type(batch_size) is not int or not 1<=batch_size<=5:raise ValueError('Batch size must be1..5')
    if len(selected)!=39 or len({x['task_name'] for x in selected})!=39 or len({x['agent_type'] for x in selected})!=39 or len({x['agent_id'] for x in selected})!=39:
        raise ValueError('Exact distinct39-role campaign required')
    identifiers=[case['case_id'] for item in selected for case in item['cases']]
    if len(identifiers)!=103 or len(set(identifiers))!=103 or any(not isinstance(cid,str) or not cid for cid in identifiers):
        raise ValueError('Exact distinct103-case campaign required')
    if any(not 2<=len(item['cases'])<=3 for item in selected):raise ValueError('Expected2..3cases per role')
    return [{'batch_id':f'batch_{index//batch_size:02d}','selected':selected[index:index+batch_size]}
            for index in range(0,len(selected),batch_size)]


def prompt(selected,*,batch=False):
    # Retain the existing full-inventory API for callers/tests. Actual execution
    # always supplies a small bounded batch, never the complete39-role prompt.
    expected=1<=len(selected)<=5 if batch else len(selected)==39
    if not expected or len({x['task_name'] for x in selected})!=len(selected):raise ValueError('Exact distinct 39-child inventory required; execution batch must be1..5')
    top=('task_name','agent_id','agent_type')
    public=[dict({k:x[k] for k in top},cases=[{k:c[k] for k in ('case_id','scenario','objective_task','input','response_schema','protocol_version','output_contract','qualification','remaining_semantic_review')} for c in x['cases']]) for x in selected]
    return '''Authorized public objective-subscope evaluation, ONE SMALL BATCH of a host-managed campaign. Your entire responsibility is spawning and waiting for the exact entries below. Use only collaboration spawn/wait/close/list operations; do not use shell, filesystem, network, connectors or credentials. For each inventory entry spawn its exact agent_type and task_name with fork_turns="none", without model/reasoning overrides. Start A00 first ONLY IF A00 is in this batch; never create an extra A00 or any other child. Keep at most three children active. Never substitute generic agents, share answers, retry failures to select favorable outcomes or execute candidate code. Forward each assigned public case object verbatim, including exact case_id, protocol_version and output_contract; never abbreviate or reconstruct identifiers. Each child gets only its own cases and computes outputs from the supplied artifacts and task, without reading oracles or any filesystem. Treat output_contract as the public definition of each response field, including its namespace and closed vocabulary. Return every assigned case_id exactly once, copied byte-for-byte. Result arrays are unordered collections preserving multiplicity, except literal_paths which preserves input order. Integer fields require exact integers (never booleans); number fields allow finite values with relative and absolute tolerance1e-9. The child must return one pure JSON object {"case_results":[{"case_id":"exact-case-id","result":{...computed schema fields...}},...]} covering all its two or three cases, no Markdown, no tools or further delegation. Explicitly tell each child this is public static-data artifact analysis, not real framework/browser/cloud/DB execution and not SME certification. Preserve failures and quota. A separate trusted Python process OUTSIDE your agent persists final outputs by reading actual native sessions after your completion. You must NOT persist artifacts, write files or use any filesystem tool. Your final response is only a brief batch completion/failure statement; do not repeat children outputs or the inventory. Do not attempt the other batches. Finish after all assigned children in THIS batch complete.
BEGIN_PUBLIC_PROFESSIONAL_TASKS
'''+json.dumps(public,ensure_ascii=False,separators=(',',':'))+'\nEND_PUBLIC_PROFESSIONAL_TASKS\n'


def grade_child(item,artifact,root=ROOT):
    _fields(artifact,('case_results',))
    rows=artifact['case_results']
    if not isinstance(rows,list) or len(rows)!=len(item['cases']):raise ValueError('Incomplete child case results')
    expected={x['case_id'] for x in item['cases']};seen=set();reports=[]
    for row in rows:
        _fields(row,('case_id','result'))
        cid=row['case_id']
        if not isinstance(cid,str) or cid not in expected or cid in seen:raise ValueError('Unknown or duplicate child case')
        seen.add(cid);reports.append(cases.grade(cid,row['result'],root))
    return reports


def collect(session_root,parent,selected,root=ROOT,*,diagnostics=None,parent_observation=None):
    paths=list(Path(session_root).rglob('*.jsonl'))
    if len(paths)>20000:raise ValueError('Session inventory exceeds bound')
    parent_rows=[];children=[]
    for path in paths:
        if path.is_symlink() or path.stat().st_size>native.LIMIT:continue
        try:
            with path.open(encoding='utf8') as stream:meta=json.loads(stream.readline()).get('payload',{})
        except (ValueError,OSError):continue
        if meta.get('id')==parent:
            if parent_rows:raise ValueError('Duplicate native parent record')
            parent_rows=native.read_session(path)
            if parent_observation is not None:parent_observation['parent_record_sha256']=native.sha(path)
        source=meta.get('source',{})
        spawn=source.get('subagent',{}).get('thread_spawn',{}) if isinstance(source,dict) else {}
        if spawn.get('parent_thread_id')==parent:children.append((meta,path,spawn))
    for event in parent_rows:
        payload=event.get('payload',{})
        if event.get('type')=='response_item' and payload.get('type') in ('function_call','custom_tool_call'):
            if payload.get('namespace')!='collaboration' or payload.get('name') not in ('spawn_agent','wait','wait_agent','close_agent','list_agents'):
                raise ValueError('Parent used an unauthorized tool in data-only evaluation')
    parent_models={e.get('payload',{}).get('model') for e in parent_rows if e.get('type')=='turn_context' and e.get('payload',{}).get('model')}
    parent_efforts={e.get('payload',{}).get('effort',e.get('payload',{}).get('reasoning_effort')) for e in parent_rows if e.get('type')=='turn_context' and e.get('payload',{}).get('effort',e.get('payload',{}).get('reasoning_effort')) is not None}
    if len(parent_models)>1 or len(parent_efforts)>1:raise ValueError('Actual parent model/effort drift')
    if parent_observation is not None:
        parent_observation.update(observed_parent_model=next(iter(parent_models)) if parent_models else None,
                                  observed_parent_effort=next(iter(parent_efforts)) if parent_efforts else None)
    pairs=native.parent_pairs(parent_rows);seen=set();reports=[];artifacts={}
    known={'/root/'+x['task_name'] for x in selected}
    for meta,path,spawn in children:
        if (meta.get('agent_path') or spawn.get('agent_path')) not in known:
            reports.append({'state':'UNEXPECTED_CHILD'})
    for item in selected:
        wanted='/root/'+item['task_name'];row={'task_name':item['task_name'],'agent_id':item['agent_id'],'agent_type':item['agent_type'],'state':'INVALID'}
        matches=[p for meta,p,s in children if (meta.get('agent_path') or s.get('agent_path'))==wanted]
        try:
            if len(matches)!=1 or pairs.count((wanted,item['agent_type']))!=1:raise ValueError('Missing/duplicate native child or paired spawn')
            child_rows=native.read_session(matches[0]);child=native.inspect_child(child_rows,item,parent,set(pairs))
            if parent_models and child['model'] not in parent_models:raise ValueError('Actual child model differs from parent')
            efforts={e.get('payload',{}).get('effort',e.get('payload',{}).get('reasoning_effort')) for e in child_rows if e.get('type')=='turn_context' and e.get('payload',{}).get('effort',e.get('payload',{}).get('reasoning_effort')) is not None}
            if len(efforts)>1 or parent_efforts and efforts and efforts!=parent_efforts:raise ValueError('Actual child effort differs or drifted')
            if child['session_id'] in seen:raise ValueError('Duplicate child session')
            seen.add(child['session_id'])
            artifacts[item['task_name']]=child['artifact']
            graded=grade_child(item,child['artifact'],root)
            row.update(state='CORROBORATED',model=child['model'],observed_effort=next(iter(efforts)) if efforts else None,
                       parent_model_observed=bool(parent_models),parent_effort_observed=bool(parent_efforts),
                       session_sha256=native.sha(matches[0]),cases=graded)
        except (ValueError,OSError,TypeError,KeyError) as exc:
            row.update(reason='NATIVE_CHILD_VALIDATION_FAILED',error_type=type(exc).__name__)
            if diagnostics is not None:diagnostics.append({'task_name':item['task_name'],'error_type':type(exc).__name__,'private_error':repr(exc)})
        reports.append(row)
    return reports,artifacts


def aggregate(selected,groups,records):
    """Fail closed on any missing/duplicate group, role, case, or process result."""
    expected={g['batch_id']:g for g in groups}
    ids=[r.get('batch_id') for r in records]
    complete=len(ids)==len(expected) and len(set(ids))==len(ids) and set(ids)==set(expected)
    if [item for group in groups for item in group['selected']]!=selected:complete=False
    parent_hashes=[r.get('parent_session_id_sha256') for r in records]
    if (len(set(parent_hashes))!=len(groups) or any(not isinstance(h,str) or len(h)!=64
            or any(c not in '0123456789abcdef' for c in h) for h in parent_hashes)):complete=False
    all_rows=[];ok=complete
    for record in records:
        group=expected.get(record.get('batch_id'))
        if group is None:ok=False;continue
        assigned=[x['task_name'] for x in group['selected']]
        rows=record.get('rows',[])
        actual=[r.get('task_name') for r in rows]
        group_ok=(record.get('state')=='COLLECTED' and type(record.get('exit_code')) is int and record['exit_code']==0
                  and record.get('native_parent_observed') is True and record.get('source_unchanged') is True
                  and record.get('installed_fixtures_unchanged') is True and record.get('quota_error_observed') is False
                  and record.get('assigned_task_names')==assigned and len(actual)==len(assigned)
                  and len(set(actual))==len(actual) and set(actual)==set(assigned))
        fingerprint=record.get('parent_record_sha256')
        if not isinstance(fingerprint,str) or len(fingerprint)!=64 or any(c not in '0123456789abcdef' for c in fingerprint):group_ok=False
        for row in rows:
            item=next((x for x in group['selected'] if x['task_name']==row.get('task_name')),None)
            checks=row.get('cases',[])
            wanted={c['case_id'] for c in item['cases']} if item else set()
            seen=[c.get('case_id') for c in checks]
            if (item is None or row.get('agent_id')!=item['agent_id'] or row.get('agent_type')!=item['agent_type']
                    or row.get('state')!='CORROBORATED' or len(seen)!=len(wanted) or len(set(seen))!=len(seen)
                    or set(seen)!=wanted or any(c.get('objective_passed') is not True for c in checks)):
                group_ok=False
        ok=ok and group_ok;all_rows.extend(rows)
    names=[r.get('task_name') for r in all_rows]
    names_expected={x['task_name'] for x in selected}
    if len(names)!=39 or len(set(names))!=39 or set(names)!=names_expected:ok=False
    checks=[c for row in all_rows for c in row.get('cases',[])]
    case_ids=[c.get('case_id') for c in checks]
    expected_cases={c['case_id'] for item in selected for c in item['cases']}
    if len(case_ids)!=103 or len(set(case_ids))!=103 or set(case_ids)!=expected_cases:ok=False
    models={row.get('model') for row in all_rows if row.get('state')=='CORROBORATED'}
    models.update(r['observed_parent_model'] for r in records if r.get('observed_parent_model') is not None)
    models_match=len(models)==1 and all(isinstance(model,str) and model for model in models)
    efforts={row.get('observed_effort') for row in all_rows if row.get('state')=='CORROBORATED' and row.get('observed_effort') is not None}
    efforts.update(r['observed_parent_effort'] for r in records if r.get('observed_parent_effort') is not None)
    effort_drift=len(efforts)>1
    effort_complete=(len(all_rows)==39 and all(row.get('observed_effort') is not None for row in all_rows)
                     and len(records)==len(groups) and all(r.get('observed_parent_effort') is not None for r in records))
    if not models_match or effort_drift:ok=False
    return {'campaign_complete':ok,'batches_expected':len(groups),'batches_recorded':len(records),
            'same_observed_model_campaign':models_match,'observed_effort_drift':effort_drift,'all_parent_child_effort_observed':effort_complete,
            'native_children_expected':39,'native_children_corroborated':sum(r.get('state')=='CORROBORATED' for r in all_rows),
            'objective_tasks_expected':103,'objective_tasks_observed':len(checks),
            'objective_tasks_passed':sum(c.get('objective_passed') is True for c in checks),'rows':all_rows}


def _events(path):
    parents=[];quota=False
    for line in path.read_text(encoding='utf8').splitlines():
        try:event=json.loads(line)
        except ValueError:continue
        if event.get('type')=='thread.started':parents.append(event.get('thread_id'))
        failure=str(event).lower().replace('_',' ').replace('-',' ')
        if event.get('type') in ('error','turn.failed') and any(s in failure for s in ('quota','usage limit','rate limit','billing hard limit reached')):quota=True
    parent=parents[0] if len(parents)==1 and isinstance(parents[0],str) and parents[0] else None
    return parent,quota


def run_batch(executable,project,private,group,session_root,timeout,root=ROOT):
    folder=private/group['batch_id'];folder.mkdir(mode=0o700)
    native.private_write(folder/'prompt.txt',prompt(group['selected'],batch=True))
    native.private_write(folder/'events.jsonl','');native.private_write(folder/'stderr.log','')
    result={'batch_id':group['batch_id'],'assigned_task_names':[x['task_name'] for x in group['selected']],
            'state':'INVALID','exit_code':None,'native_parent_observed':False,'quota_error_observed':False,'rows':[]}
    parent=None;started=time.monotonic()
    try:
        with (folder/'prompt.txt').open('rb') as stdin,(folder/'events.jsonl').open('a',encoding='utf8') as stdout,(folder/'stderr.log').open('a',encoding='utf8') as stderr:
            process=subprocess.Popen(native.codex_command(executable,project),stdin=stdin,stdout=stdout,stderr=stderr,cwd=project)
            try:result['exit_code']=process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:process.wait(timeout=15)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=15)
                result['exit_code']='TIMEOUT_DESCENDANT_CLEANUP_NOT_VERIFIED'
        parent,quota=_events(folder/'events.jsonl')
        result.update(native_parent_observed=bool(parent),quota_error_observed=quota)
        if parent:result['parent_session_id_sha256']=hashlib.sha256(parent.encode('utf8')).hexdigest()
        if parent:
            diagnostics=[];parent_observation={}
            rows,artifacts=collect(session_root,parent,group['selected'],root,diagnostics=diagnostics,parent_observation=parent_observation)
            result.update(state='COLLECTED',rows=rows)
            result.update(parent_observation)
            native.private_write(folder/'observed-artifacts.json',json.dumps(artifacts,ensure_ascii=True,indent=2))
            native.private_write(folder/'validation-errors.json',json.dumps(diagnostics,ensure_ascii=True,indent=2))
        else:result['reason']='NATIVE_PARENT_NOT_OBSERVED'
    except (OSError,ValueError,TypeError,KeyError,subprocess.SubprocessError) as error:
        # Raw exceptions may contain host paths or private metadata: retain only
        # in the private group directory, never in the public JSON summary.
        native.private_write(folder/'host-error.txt',repr(error))
        result.update(reason='BATCH_EXECUTION_OR_CORROBORATION_FAILED',error_type=type(error).__name__)
    native.private_write(folder/'parent-metadata.json',json.dumps({'parent_session_id':parent,'batch_id':group['batch_id']},indent=2))
    result.update(elapsed_seconds=round(time.monotonic()-started,2),events_sha256=native.sha(folder/'events.jsonl'))
    return result


def execute_batches(executable,project,private,groups,session_root,timeout,guard,root=ROOT):
    deadline=time.monotonic()+timeout;records=[];halt=None
    for index,group in enumerate(groups):
        source_ok,fixtures_ok=check_guard(guard,private,f'{index:02d}-before')
        remaining=deadline-time.monotonic()
        if not source_ok or not fixtures_ok:halt='SOURCE_OR_FIXTURE_NOT_VERIFIED'
        if remaining<=0:halt='CAMPAIGN_TIME_BUDGET_EXHAUSTED'
        if halt:
            record={'batch_id':group['batch_id'],'assigned_task_names':[x['task_name'] for x in group['selected']],
                    'state':'NOT_RUN','reason':halt,'exit_code':None,'native_parent_observed':False,'quota_error_observed':False,'rows':[]}
        else:
            record=run_batch(executable,project,private,group,session_root,remaining,root)
        source_ok,fixtures_ok=check_guard(guard,private,f'{index:02d}-after')
        record.update(source_unchanged=source_ok,installed_fixtures_unchanged=fixtures_ok)
        records.append(record)
        # Persist each completed/blocked batch before starting another CLI parent.
        # An interruption cannot erase already observed results from host memory.
        batch_folder=private/group['batch_id'];batch_folder.mkdir(mode=0o700,exist_ok=True)
        native.private_write(batch_folder/'result.json',json.dumps(record,ensure_ascii=True,indent=2))
        if record.get('quota_error_observed'):halt='OBSERVED_QUOTA_STOP'
        if isinstance(record.get('exit_code'),str) and record['exit_code'].startswith('TIMEOUT'):halt='CAMPAIGN_TIMEOUT_STOP'
        if record.get('reason')=='BATCH_EXECUTION_OR_CORROBORATION_FAILED':halt='ESSENTIAL_EXECUTION_OR_CORROBORATION_UNAVAILABLE'
    return records


def check_guard(guard,private,label):
    try:
        state=guard()
        if not isinstance(state,tuple) or len(state)!=2 or any(type(value) is not bool for value in state):
            raise ValueError('Malformed guard observation')
        return state
    except (OSError,ValueError,TypeError,subprocess.SubprocessError) as error:
        native.private_write(private/('guard-'+label+'-error.txt'),repr(error))
        return False,False


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true');p.add_argument('--out',type=Path);p.add_argument('--timeout',type=int,default=3600)
    p.add_argument('--batch-size',type=int,default=3)
    args=p.parse_args(argv)
    if not 60<=args.timeout<=7200:p.error('--timeout must be60..7200 seconds')
    selected=plan();groups=batches(selected,args.batch_size)
    if not args.run:
        print(json.dumps({'native_children_expected':39,'artifact_tasks_expected':103,'quota_consumed':False,'private_holdout':False,
                          'batch_size':args.batch_size,'parent_processes_expected':len(groups),'automatic_retries':0,
                          'batch_plan':[{'batch_id':g['batch_id'],'task_names':[x['task_name'] for x in g['selected']],
                                         'case_count':sum(len(x['cases']) for x in g['selected']),
                                         'prompt_utf8_bytes':len(prompt(g['selected'],batch=True).encode('utf8'))} for g in groups],
                          'plan':selected},ensure_ascii=True,indent=2));return 0
    executable=shutil.which('codex')
    if executable is None or args.out is None:raise ValueError('Codex CLI and a new --out directory required')
    destination=_plain(args.out)
    if destination==ROOT or ROOT in destination.parents or destination.exists():raise ValueError('Output must be new and outside source checkout')
    destination.mkdir(parents=False,mode=0o700);private=destination/'private';private.mkdir(mode=0o700)
    project=destination/'project';project.mkdir()
    before=native.snapshot(ROOT)
    revision=subprocess.run(['git','-C',str(ROOT),'rev-parse','HEAD'],capture_output=True,text=True,check=True,timeout=10).stdout.strip()
    subprocess.run([sys.executable,'-B',str(ROOT/'install.py'),'--project',str(project),'--apply'],check=True,capture_output=True,timeout=120)
    profiles={a['name']:ROOT/a['file'] for a in cases.q.load_json(ROOT/'core/agents.json')['agents']}
    for manifest in sorted((ROOT/'packs').glob('*/manifest.json')):
        pack=cases.q.load_json(manifest)
        subprocess.run([sys.executable,'-B',str(ROOT/'tools/guardian_packs.py'),'install','--pack',pack['name'],'--project',str(project),'--apply'],check=True,capture_output=True,timeout=120)
        for agent in pack['agents']:profiles[agent['name']]=manifest.parent/agent['file']
    installed={native.sha(f) for f in (project/'.codex/agents').glob('*.toml')}
    profile_hashes={x['agent_type']:native.sha(profiles[x['agent_type']]) for x in selected}
    if not all(h in installed for h in profile_hashes.values()):raise ValueError('Installed profile bytes differ')
    # Only public requests enter the model prompt. Installed package tools may
    # contain public oracles; no-tools enforcement is post-hoc/procedural, not OS secrecy.
    (project/'public-tasks.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2),encoding='utf8')
    def fixture_snapshot():
        return {str(f.relative_to(project)):native.sha(_plain(f)) for f in project.rglob('*') if f.is_file()}
    protected=fixture_snapshot()
    started=time.monotonic()
    sessions=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))/'sessions'
    def guard():
        current_revision=subprocess.run(['git','-C',str(ROOT),'rev-parse','HEAD'],capture_output=True,text=True,check=True,timeout=10).stdout.strip()
        return before==native.snapshot(ROOT) and current_revision==revision,fixture_snapshot()==protected
    records=execute_batches(executable,project,private,groups,sessions,args.timeout,guard)
    unchanged,fixtures_unchanged=check_guard(guard,private,'final')
    combined=aggregate(selected,groups,records)
    complete=combined['campaign_complete'] and unchanged and fixtures_unchanged
    summary={'schema_version':1,'evidence_class':'NATIVE_PUBLIC_PROFESSIONAL_OBJECTIVE_SUBSCOPES','revision':revision,'protocol_version':cases.PROTOCOL_VERSION,
             'source_unchanged':unchanged,'installed_fixtures_unchanged':fixtures_unchanged,'profile_sha256':profile_hashes,
             'public_task_inventory_sha256':cases.q.digest(selected),
             **combined,'batches':records,'batch_size':args.batch_size,
             'parent_processes_expected':len(groups),'automatic_retries':0,
             'sme_qualified_cases':0,'private_holdout_validated':False,'os_isolation':False,
             'artifact_origin':'Actual child final JSON persisted by external Python host per batch; no model filesystem write',
             'exit_code':0 if complete else 1,'elapsed_seconds':round(time.monotonic()-started,2),
             'quota_error_observed':any(r.get('quota_error_observed') for r in records),
             'cost':{'kind':'unknown','amount':None},
             'limits':['Public data; oracle separation is procedural, not OS enforced','No candidate code or real framework/provider executed','Single child per role; no repeated-run reliability claim','Timeout descendant cleanup and Windows private-log DACL not certified','103 qualitative SME rubrics remain unqualified'],
             'campaign_complete':complete}
    (destination/'summary-public.json').write_text(json.dumps(summary,ensure_ascii=True,indent=2),encoding='utf8')
    print(json.dumps(summary,ensure_ascii=True,indent=2))
    return 0 if complete else 1


if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        raise SystemExit(json.dumps({'ok':False,'reason':'NATIVE_PROFESSIONAL_CAMPAIGN_UNAVAILABLE','error_type':type(exc).__name__}))
