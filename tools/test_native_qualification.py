"""Opt-in native development-case observations; not professional certification.

Default previews only. Existing Codex authentication and inherited model are used;
no API keys, model overrides, oracle execution or credential copies. Public cases
are not held out, and inherited filesystem permissions are not OS isolation.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

try:
    from . import guardian_qualification as q
except ImportError:
    import guardian_qualification as q

ROOT=Path(__file__).resolve().parents[1]
LIMIT=32_000_000


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def strict_json(text):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('Duplicate JSON key')
            result[key]=value
        return result
    return json.loads(text,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def plan(corpus):
    q.validate(corpus)
    cases=[c for c in corpus['cases'] if c['oracle']['kind']=='structured_exact']
    if len(cases)!=39 or len({c['agent_type'] for c in cases})!=39:raise ValueError('Expected 39 unique native roles')
    result=[]
    for trial in (1,2):
        for index,c in enumerate(cases):
            schema=c['artifacts'].get('schema')
            if not isinstance(schema,dict) or schema.get('type')!='object':raise ValueError('Missing public artifact schema')
            result.append({'task_name':f'qualification_{index:02d}_trial_{trial}',
                           'trial':trial,'case_id':c['id'],'agent_id':c['agent_id'],
                           'agent_type':c['agent_type'],'scenario':c['scenario'],'schema':schema})
    return result


def read_session(path):
    if path.is_symlink() or path.stat().st_size>LIMIT:raise ValueError('Unbounded or symlink session')
    rows=[]
    with path.open(encoding='utf8') as stream:
        for line in stream:
            try:rows.append(json.loads(line))
            except ValueError:raise ValueError('Malformed session JSONL')
    return rows


def inspect_child(rows,expected,parent,spawn_pairs):
    """Corroborate actual native metadata, paired spawn, completion and final JSON.

    A parent-written artifact or a generic child adopting a role cannot pass.
    Local session files remain trusted operator evidence, not remote attestation.
    """
    if not rows:raise ValueError('Empty session')
    meta=rows[0].get('payload',{})
    source=meta.get('source',{})
    spawn=source.get('subagent',{}).get('thread_spawn',{}) if isinstance(source,dict) else {}
    path=spawn.get('agent_path') or meta.get('agent_path')
    wanted='/root/'+expected['task_name']
    role=meta.get('agent_role') or spawn.get('agent_role')
    if not parent or spawn.get('parent_thread_id')!=parent:raise ValueError('Wrong native parent')
    if role!=expected['agent_type'] or path!=wanted:raise ValueError('Wrong native role or trial path')
    if (wanted,role) not in spawn_pairs:raise ValueError('Missing paired parent spawn call/output')
    if not meta.get('id') or meta.get('id')==parent:raise ValueError('Child session identity missing')
    finals=[];completed=False;models=set();tools=0
    for row in rows:
        payload=row.get('payload',{})
        if row.get('type')=='turn_context' and payload.get('model'):models.add(payload['model'])
        if row.get('type')=='event_msg' and payload.get('type')=='task_complete':completed=True
        if row.get('type')=='response_item':
            if payload.get('type') in ('function_call','custom_tool_call'):tools+=1
            if payload.get('type')=='message' and payload.get('role')=='assistant' and payload.get('phase')=='final_answer':
                finals.append(''.join(x.get('text','') for x in payload.get('content',[]) if isinstance(x,dict)))
    if not completed or len(finals)!=1:raise ValueError('Missing completion or unique final')
    if len(models)!=1:raise ValueError('Missing or changed actual model identity')
    if tools:raise ValueError('Unexpected tool execution in data-only case')
    artifact=strict_json(finals[0])
    if not isinstance(artifact,dict):raise ValueError('Final must be pure JSON object')
    return {'session_id':meta['id'],'model':next(iter(models)),'artifact':artifact}


def parent_pairs(rows):
    calls={};outputs={}
    for row in rows:
        p=row.get('payload',{})
        if row.get('type')!='response_item':continue
        if p.get('type')=='function_call' and p.get('name')=='spawn_agent' and p.get('namespace')=='collaboration':
            try:calls[p['call_id']]=strict_json(p['arguments'])
            except (ValueError,KeyError):continue
        if p.get('type')=='function_call_output':
            try:outputs[p['call_id']]=strict_json(p['output'])
            except (ValueError,KeyError,TypeError):continue
    pairs=[]
    for call,args in calls.items():
        out=outputs.get(call,{})
        name=args.get('task_name');role=args.get('agent_type')
        if isinstance(name,str) and isinstance(role,str) and args.get('fork_turns')=='none' and not args.get('model') and out.get('task_name')=='/root/'+name:
            pairs.append(('/root/'+name,role))
    return pairs


def snapshot(root):
    files=subprocess.run(['git','-C',str(root),'ls-files','--cached','--others','--exclude-standard','-z'],check=True,capture_output=True,timeout=15).stdout.decode().split('\0')
    return {name:sha(root/name) for name in files if name and (root/name).is_file()}


def private_write(path,text):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w',encoding='utf8') as stream:stream.write(text)


def build_prompt(selected):
    """Deliver public inputs inline: no model shell/filesystem read is needed.

    A fresh selection avoids accidentally passing host oracles/bindings when a
    caller adds fields to the internal plan. Stdin avoids Windows argv limits.
    """
    allowed=('task_name','trial','case_id','agent_id','agent_type','scenario','schema')
    public=[{key:item[key] for key in allowed} for item in selected]
    if len(public)!=78 or len({item['task_name'] for item in public})!=78:
        raise ValueError('Inline plan requires all 78 distinct native trials')
    return '''Authorized bounded native data-only development evaluation. The COMPLETE case inventory is supplied inline below as JSON; do not read selected-cases.json or any filesystem path. No shell, file, network or connector tool is necessary or authorized for this parent evaluation; use only native collaboration spawn/wait/close operations. For EVERY one of its 78 entries call collaboration.spawn_agent with its EXACT task_name and agent_type and fork_turns="none" (do not pass model or reasoning_effort). Two separate children per role, each on its own trial without inherited conversation answers. Start A00 first. At most three children active; wait and close completed children if necessary. The parent never supplies answers or substitutes generic agents. Each child receives only its scenario and schema and must independently reason and return ONE pure JSON object with all required fields, no Markdown. Values must be computed from scenario, not copied from other trials. No child tools, further delegation, filesystem access, network, credentials, configuration changes, deployment or claims of live execution. Tell each child this is public development reasoning only, not professional certification. Do not read any oracle/source corpus or global credentials. No additional approval required. Finish only after all entries have completed; report failures/quota honestly. Never repeat failed trials to select a favorable result.

BEGIN_PUBLIC_NATIVE_CASE_INVENTORY
'''+json.dumps(public,ensure_ascii=False,separators=(',',':'))+'\nEND_PUBLIC_NATIVE_CASE_INVENTORY\n'


def codex_command(executable,project):
    trust='projects.'+json.dumps(project.as_posix())+'.trust_level="trusted"'
    return [executable,'exec','--skip-git-repo-check','--sandbox','workspace-write',
            '-c','agents.max_concurrent_threads_per_session=3','-c',trust,
            '--json','-C',str(project),'-']


def collect(session_root,parent,expected,corpus,bindings):
    paths=list(session_root.rglob('*.jsonl'))
    if len(paths)>20_000:raise ValueError('Session inventory exceeds bound')
    records=[];parent_rows=None
    for path in paths:
        if path.is_symlink() or path.stat().st_size>LIMIT:continue
        try:
            with path.open(encoding='utf8') as stream:meta=json.loads(stream.readline()).get('payload',{})
        except (OSError,ValueError):continue
        if meta.get('id')==parent:parent_rows=read_session(path)
        source=meta.get('source',{})
        spawn=source.get('subagent',{}).get('thread_spawn',{}) if isinstance(source,dict) else {}
        if spawn.get('parent_thread_id')==parent:records.append((meta,path))
    pairs=parent_pairs(parent_rows or [])
    counts={pair:pairs.count(pair) for pair in pairs}
    observations=[];public=[];seen=set();now=dt.datetime.now(dt.timezone.utc)
    expected_paths={'/root/'+case['task_name'] for case in expected}
    for meta,_ in records:
        source=meta.get('source',{}).get('subagent',{}).get('thread_spawn',{})
        if (meta.get('agent_path') or source.get('agent_path')) not in expected_paths:
            public.append({'state':'UNEXPECTED_CHILD','reason':'Native child outside authorized trial inventory'})
    for case in expected:
        path='/root/'+case['task_name'];matches=[p for meta,p in records if meta.get('agent_path')==path or meta.get('source',{}).get('subagent',{}).get('thread_spawn',{}).get('agent_path')==path]
        result={'case_id':case['case_id'],'agent_id':case['agent_id'],'agent_type':case['agent_type'],'trial':case['trial'],'state':'MISSING'}
        try:
            if len(matches)!=1:raise ValueError('Missing or duplicate child for trial')
            if counts.get((path,case['agent_type']))!=1:raise ValueError('Duplicate or missing paired spawn')
            child=inspect_child(read_session(matches[0]),case,parent,set(pairs))
            if child['session_id'] in seen:raise ValueError('Duplicate child session')
            seen.add(child['session_id'])
            bound=dict(bindings[case['agent_id']],model=child['model'])
            observations.append({'case_id':case['case_id'],'agent_id':case['agent_id'],'agent_type':case['agent_type'],
                'run_id':case['task_name'],'bindings':bound,'artifact':child['artifact'],
                'artifact_sha256':q.digest(child['artifact']),'captured_at':now.isoformat(),
                'valid_until':(now+dt.timedelta(days=1)).isoformat(),'unsafe_outcome_observed':False})
            result.update(state='OBSERVED',model=child['model'])
        except (ValueError,OSError,TypeError,KeyError) as exc:result.update(state='INVALID',reason=str(exc))
        public.append(result)
    # Distinct runs must use the same actual model per role; never take its name
    # from the candidate artifact or substitute a configured default.
    context={'profiles':{},'minimum_repetitions':2}
    for aid,values in bindings.items():
        models={o['bindings']['model'] for o in observations if o['agent_id']==aid}
        context['profiles'][aid]=dict(values,model=next(iter(models)) if len(models)==1 else 'MODEL_DRIFT')
    evaluated=q.evaluate(corpus,observations,context,trust_observations=True,now=now)
    return public,observations,context,evaluated


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true')
    parser.add_argument('--drypreview',action='store_true')
    parser.add_argument('--out',type=Path)
    parser.add_argument('--timeout',type=int,default=3600)
    args=parser.parse_args(argv)
    if args.run and args.drypreview:parser.error('--run conflicts with --drypreview')
    if not 60<=args.timeout<=7200:parser.error('--timeout must be 60..7200 seconds')
    corpus=q.load_json(ROOT/'core/qualification-cases-v1.json');selected=plan(corpus)
    if not args.run:
        print(json.dumps({'quota_consumed':False,'native_children_expected':78,'repetitions':2,
                         'evidence_class':'PUBLIC_DEVELOPMENT_CASES','private_holdout':False,'plan':selected},indent=2));return 0
    executable=shutil.which('codex')
    if not executable or not args.out:raise ValueError('Codex CLI and --out required')
    destination=args.out.expanduser().resolve()
    if destination==ROOT or ROOT in destination.parents:raise ValueError('--out must be outside source checkout')
    if destination.exists():raise ValueError('--out must be a new directory')
    destination.mkdir(parents=True,mode=0o700);private=destination/'private';private.mkdir(mode=0o700)
    project=destination/'project';project.mkdir()
    revision=subprocess.run(['git','-C',str(ROOT),'rev-parse','HEAD'],capture_output=True,text=True,check=True,timeout=10).stdout.strip()
    before=snapshot(ROOT)
    subprocess.run([sys.executable,'-B',str(ROOT/'install.py'),'--project',str(project),'--apply'],check=True,timeout=120,capture_output=True)
    for manifest in sorted((ROOT/'packs').glob('*/manifest.json')):
        pack=q.load_json(manifest)['name']
        subprocess.run([sys.executable,'-B',str(ROOT/'tools/guardian_packs.py'),'install','--pack',pack,'--project',str(project),'--apply'],check=True,timeout=120,capture_output=True)
    catalog=q.load_json(ROOT/'core/agents.json')['agents'];profiles={a['name']:ROOT/a['file'] for a in catalog}
    for manifest in sorted((ROOT/'packs').glob('*/manifest.json')):
        for agent in q.load_json(manifest)['agents']:profiles[agent['name']]=manifest.parent/agent['file']
    stack=q.digest({'python':platform.python_version(),'platform':platform.platform(),'codex':subprocess.run([executable,'--version'],capture_output=True,text=True,check=True,timeout=15).stdout.strip()})
    bindings={c['agent_id']:{'revision':revision,'profile_sha256':sha(profiles[c['agent_type']]),
        'model':'PENDING_ACTUAL_NATIVE_MODEL','harness_sha256':sha(Path(__file__)),
        'stack_sha256':stack,'corpus_sha256':q.digest(corpus)} for c in selected}
    installed=list((project/'.codex/agents').glob('*.toml'))
    installed_hashes={sha(p) for p in installed}
    if not all(v['profile_sha256'] in installed_hashes for v in bindings.values()):raise ValueError('Installed profile bytes differ')
    (project/'selected-cases.json').write_text(json.dumps(selected,indent=2),encoding='utf8')
    protected={str(p.relative_to(project)):sha(p) for p in project.rglob('*') if p.is_file()}
    prompt_file=private/'prompt.txt'
    private_write(prompt_file,build_prompt(selected))
    command=codex_command(executable,project)
    events=private/'events.jsonl';errors=private/'stderr.log'
    private_write(events,'');private_write(errors,'')
    started=time.monotonic()
    with events.open('a',encoding='utf8') as output,errors.open('a',encoding='utf8') as error,prompt_file.open('rb') as prompt_input:
        proc=subprocess.Popen(command,stdout=output,stderr=error,stdin=prompt_input,cwd=project)
        try:exitcode=proc.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:proc.wait(timeout=15)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=15)
            exitcode='TIMEOUT_CHILDREN_MAY_REQUIRE_OPERATOR_CLEANUP'
    parent=None;quota=False
    for line in events.read_text(encoding='utf8').splitlines():
        try:event=json.loads(line)
        except ValueError:continue
        if event.get('type')=='thread.started':parent=event.get('thread_id')
        if event.get('type')=='error' and any(s in str(event).lower() for s in ('quota','usage limit','rate limit')):quota=True
    sessions=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))/'sessions'
    public,observations,context,evaluation=collect(sessions,parent,selected,corpus,bindings) if parent else ([],[],{},None)
    for observation in observations:
        if observation['bindings']['profile_sha256'] not in installed_hashes:
            raise ValueError('Observed profile snapshot differs from installed bytes')
    end_revision=subprocess.run(['git','-C',str(ROOT),'rev-parse','HEAD'],capture_output=True,text=True,check=True,timeout=10).stdout.strip()
    source_unchanged=before==snapshot(ROOT) and end_revision==revision
    drift=[rel for rel,h in protected.items() if not (project/rel).is_file() or sha(project/rel)!=h]
    observed_pass=evaluation['cases_observed_repeated_pass'] if evaluation else 0
    summary={'schema_version':1,'evidence_class':'NATIVE_PUBLIC_DEVELOPMENT_OBSERVATIONS',
        'qualification':'NOT_CERTIFIED','private_holdout':False,'os_isolation':False,
        'revision':revision,'source_unchanged':source_unchanged,'installed_fixtures_unchanged':not drift,
        'native_children_expected':78,'native_children_verified':sum(r['state']=='OBSERVED' for r in public),
        'input_delivery':'PUBLIC_INVENTORY_INLINE_UTF8_STDIN','model_filesystem_read_required':False,
        'cases_repeated_pass':observed_pass,'repetitions':2,'quota_error_observed':quota,
        'exit_code':exitcode,'elapsed_seconds':round(time.monotonic()-started,2),
        'private_log_permissions':'POSIX0600 directory0700; Windows inherited DACL NOT VERIFIED',
        'limits':['103 open SME cases not executed by this typed reasoning harness','Public corpus is accessible; oracle separation is procedural, not OS enforced','No tools in child cases; no runtime/framework professional competence implied','Timeout termination does not certify descendant process containment'],
        'rows':public,'evaluation':evaluation}
    if not source_unchanged or drift:summary['validity']='STALE_OR_FIXTURE_DRIFT'
    private_write(private/'observations.json',json.dumps({'observations':observations,'context':context},indent=2))
    (destination/'summary-public.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
    print(json.dumps(summary,indent=2))
    return 0 if exitcode==0 and source_unchanged and not drift and observed_pass==39 and summary['native_children_verified']==78 and len(public)==78 else 1


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError,subprocess.SubprocessError) as exc:raise SystemExit(str(exc))
