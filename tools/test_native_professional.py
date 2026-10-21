"""Opt-in native 39-role / 103-artifact public objective subscopes.

Default is preview; no native model calls unless --run is explicitly supplied.
Candidate code is never executed. All qualitative SME/holdout gates remain open.
"""
import argparse
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


def prompt(selected):
    if len(selected)!=39 or len({x['task_name'] for x in selected})!=39:raise ValueError('Exact distinct 39-child inventory required')
    top=('task_name','agent_id','agent_type')
    public=[dict({k:x[k] for k in top},cases=[{k:c[k] for k in ('case_id','scenario','objective_task','input','response_schema','protocol_version','output_contract','qualification','remaining_semantic_review')} for c in x['cases']]) for x in selected]
    return '''Authorized public objective-subscope evaluation. Use only collaboration spawn/wait/close operations; do not use shell, filesystem, network, connectors or credentials. For each inventory entry spawn its exact agent_type and task_name with fork_turns="none", without model/reasoning overrides. Start A00 first; at most three children active. Never substitute generic agents, share answers, retry failures to select favorable outcomes or execute candidate code. Forward each assigned public case object verbatim, including exact case_id, protocol_version and output_contract; never abbreviate or reconstruct identifiers. Each child gets only its own cases and computes outputs from the supplied artifacts and task, without reading oracles or any filesystem. Treat output_contract as the public definition of each response field, including its namespace and closed vocabulary. Return every assigned case_id exactly once, copied byte-for-byte. Result arrays are unordered collections preserving multiplicity, except literal_paths which preserves input order. Integer fields require exact integers (never booleans); number fields allow finite values with relative and absolute tolerance 1e-9. The child must return one pure JSON object {"case_results":[{"case_id":"exact-case-id","result":{...computed schema fields...}},...]} covering all its two or three cases, no Markdown, no tools or further delegation. Explicitly tell each child this is public static-data artifact analysis, not real framework/browser/cloud/DB execution and not SME certification. Preserve failures and quota. The supervisor writes the actual final JSON as an artifact after native session corroboration; do not fabricate completion or model identity. Finish only after all39 children complete.
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


def collect(session_root,parent,selected,root=ROOT):
    paths=list(Path(session_root).rglob('*.jsonl'))
    if len(paths)>20000:raise ValueError('Session inventory exceeds bound')
    parent_rows=[];children=[]
    for path in paths:
        if path.is_symlink() or path.stat().st_size>native.LIMIT:continue
        try:
            with path.open(encoding='utf8') as stream:meta=json.loads(stream.readline()).get('payload',{})
        except (ValueError,OSError):continue
        if meta.get('id')==parent:parent_rows=native.read_session(path)
        source=meta.get('source',{})
        spawn=source.get('subagent',{}).get('thread_spawn',{}) if isinstance(source,dict) else {}
        if spawn.get('parent_thread_id')==parent:children.append((meta,path,spawn))
    for event in parent_rows:
        payload=event.get('payload',{})
        if event.get('type')=='response_item' and payload.get('type') in ('function_call','custom_tool_call'):
            if payload.get('namespace')!='collaboration' or payload.get('name') not in ('spawn_agent','wait','wait_agent','close_agent','list_agents'):
                raise ValueError('Parent used an unauthorized tool in data-only evaluation')
    pairs=native.parent_pairs(parent_rows);seen=set();reports=[];artifacts={}
    known={'/root/'+x['task_name'] for x in selected}
    for meta,path,spawn in children:
        if (meta.get('agent_path') or spawn.get('agent_path')) not in known:
            reports.append({'state':'UNEXPECTED_CHILD'})
    for item in selected:
        wanted='/root/'+item['task_name'];row={'agent_id':item['agent_id'],'agent_type':item['agent_type'],'state':'INVALID'}
        matches=[p for meta,p,s in children if (meta.get('agent_path') or s.get('agent_path'))==wanted]
        try:
            if len(matches)!=1 or pairs.count((wanted,item['agent_type']))!=1:raise ValueError('Missing/duplicate native child or paired spawn')
            child=native.inspect_child(native.read_session(matches[0]),item,parent,set(pairs))
            if child['session_id'] in seen:raise ValueError('Duplicate child session')
            seen.add(child['session_id'])
            artifacts[item['task_name']]=child['artifact']
            graded=grade_child(item,child['artifact'],root)
            row.update(state='CORROBORATED',model=child['model'],cases=graded)
        except (ValueError,OSError,TypeError,KeyError) as exc:row['reason']=str(exc)
        reports.append(row)
    return reports,artifacts


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true');p.add_argument('--out',type=Path);p.add_argument('--timeout',type=int,default=3600)
    args=p.parse_args(argv)
    if not 60<=args.timeout<=7200:p.error('--timeout must be60..7200 seconds')
    selected=plan()
    if not args.run:
        print(json.dumps({'native_children_expected':39,'artifact_tasks_expected':103,'quota_consumed':False,'private_holdout':False,'plan':selected},ensure_ascii=True,indent=2));return 0
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
    protected={str(f.relative_to(project)):native.sha(f) for f in project.rglob('*') if f.is_file()}
    native.private_write(private/'prompt.txt',prompt(selected));native.private_write(private/'events.jsonl','');native.private_write(private/'stderr.log','')
    started=time.monotonic()
    with (private/'prompt.txt').open('rb') as stdin,(private/'events.jsonl').open('a',encoding='utf8') as stdout,(private/'stderr.log').open('a',encoding='utf8') as stderr:
        process=subprocess.Popen(native.codex_command(executable,project),stdin=stdin,stdout=stdout,stderr=stderr,cwd=project)
        try:exitcode=process.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=15)
            exitcode='TIMEOUT_DESCENDANT_CLEANUP_NOT_VERIFIED'
    parent=None
    for line in (private/'events.jsonl').read_text(encoding='utf8').splitlines():
        try:event=json.loads(line)
        except ValueError:continue
        if event.get('type')=='thread.started':parent=event.get('thread_id')
    sessions=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))/'sessions'
    rows,artifacts=collect(sessions,parent,selected) if parent else ([],{})
    unchanged=before==native.snapshot(ROOT)
    current_revision=subprocess.run(['git','-C',str(ROOT),'rev-parse','HEAD'],capture_output=True,text=True,check=True,timeout=10).stdout.strip()
    unchanged=unchanged and current_revision==revision
    fixtures_unchanged=all((project/f).is_file() and native.sha(project/f)==h for f,h in protected.items())
    artifact_dir=project/'observed-artifacts';artifact_dir.mkdir()
    for name,artifact in artifacts.items():native.private_write(artifact_dir/(name+'.json'),json.dumps(artifact,ensure_ascii=True,indent=2))
    reports=[r for row in rows for r in row.get('cases',[])]
    summary={'schema_version':1,'evidence_class':'NATIVE_PUBLIC_PROFESSIONAL_OBJECTIVE_SUBSCOPES','revision':revision,'protocol_version':cases.PROTOCOL_VERSION,
             'source_unchanged':unchanged,'installed_fixtures_unchanged':fixtures_unchanged,'profile_sha256':profile_hashes,
             'public_task_inventory_sha256':cases.q.digest(selected),
             'native_children_expected':39,'native_children_corroborated':sum(r['state']=='CORROBORATED' for r in rows),
             'objective_tasks_expected':103,'objective_tasks_observed':len(reports),'objective_tasks_passed':sum(r['objective_passed'] for r in reports),
             'sme_qualified_cases':0,'private_holdout_validated':False,'os_isolation':False,
             'artifact_origin':'Corroborated child final JSON persisted by supervisor, not a claimed model filesystem write',
             'exit_code':exitcode,'elapsed_seconds':round(time.monotonic()-started,2),
             'limits':['Public data; oracle separation is procedural, not OS enforced','No candidate code or real framework/provider executed','Single child per role; no repeated-run reliability claim','Timeout descendant cleanup and Windows private-log DACL not certified','103 qualitative SME rubrics remain unqualified'],
             'rows':rows}
    (destination/'summary-public.json').write_text(json.dumps(summary,ensure_ascii=True,indent=2),encoding='utf8')
    print(json.dumps(summary,ensure_ascii=True,indent=2))
    return 0 if exitcode==0 and unchanged and fixtures_unchanged and summary['native_children_corroborated']==39 and len(rows)==39 and summary['objective_tasks_passed']==103 else 1


if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError,subprocess.SubprocessError) as exc:raise SystemExit(str(exc))
