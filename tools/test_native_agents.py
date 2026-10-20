#!/usr/bin/env python3
"""Opt-in native Codex checks in an isolated project. Uses account quota only with --run."""
import argparse, datetime, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
try:from .native_check_evidence import paired_outcomes,fixture_passed
except ImportError:from native_check_evidence import paired_outcomes,fixture_passed

def with_check_instruction(case):
    case=dict(case)
    command={'cmd':'python -B check.py','workdir':str(case['case_directory']).replace('\\','/'),'max_output_tokens':2000}
    code='text(await tools.exec_command('+json.dumps(command,separators=(',',':'))+'));'
    case['task']+=' Mandatory check evidence: for EACH required before/after check invoke the exec code tool with EXACTLY this standalone source: '+code+' Use separate tool calls for reads/edits; never chain commands, capture/override exit codes or batch checks.'
    return case


def build_prompt(plan,project):
    """Inline the public task inventory; children still execute real fixture checks.

    Do not inline fixture assertions or host evidence criteria. Stdin transports
    the inventory without depending on the model shell cwd or Windows argv size.
    """
    public=[{key:case[key] for key in ('id','agent_type','case_directory','mode','task')} for case in plan]
    if not public or len({c['id'] for c in public})!=len(public) or len({c['agent_type'] for c in public})!=len(public):
        raise ValueError('Expected nonempty unique native case inventory')
    prompt='''Authorized bounded local validation. The complete task inventory is supplied inline below; the parent need not read selected-cases.json or search for it. For EACH case invoke native collaboration.spawn_agent with agent_type exactly equal to its agent_type. The primary does not count. Every chosen profile must execute individually. At most three active children; A00 first. Close each completed native child before opening another if the session thread limit requires it. Each child must read only its case_directory inputs, execute python -B check.py from that directory, and provide actual output, diagnosis or authorized fix, file evidence and limitations. No child may delegate further. P01-P10 are AUDIT-only optional roles: reproduce their seeded assertion and report domain limitations; never claim framework/browser/cloud execution. AUDIT cases do not edit files; S05 may edit only index.html, S08/S24 only domain.py in their own directory and must rerun unchanged check.py before/after. A00 must additionally run the project-installed router at the absolute runtime path shown below; other findings are synthetic and intentionally fail in AUDIT. Do not deploy, use external connectors/network, read credentials, modify global configuration, install dependencies or create other sessions. The test is explicitly authorized, so no redundant approval question. Wait until ALL selected native children finish, do not substitute copied personas or generic types. Return compact results.
MANDATORY evidence shape: every check must be a separate tools.exec_command call with cmd exactly python -B check.py and workdir exactly the absolute case_directory. Do not chain reads, other commands, exit manipulation or batch check calls; use separate calls for those actions. Always specify explicit absolute workdir for filesystem commands; never rely on the shell default directory. If the sandbox denies a fixture path, record the denial and stop that case; do not request bypass or modify host ACLs.
In every child message include the exact case task and mode from the inline inventory. A00 must read and route the exact request in A00/case.json and verify specialist IDs against the installed core/agents.json catalog. Do not replace the case request with a generic evaluation summary.
'''
    prompt+='Router: '+str(project/'.guardian/tools/guardian.py')+'\n'
    return prompt+'BEGIN_PUBLIC_NATIVE_TASKS\n'+json.dumps(public,ensure_ascii=False,separators=(',',':'))+'\nEND_PUBLIC_NATIVE_TASKS\n'


def codex_command(executable,project):
    trust='projects.'+json.dumps(project.as_posix())+'.trust_level="trusted"'
    return [executable,'exec','--skip-git-repo-check','--sandbox','workspace-write','-c',
            'agents.max_concurrent_threads_per_session=3','-c',trust,'--json','-C',str(project),'-']

def extract(root_session, destination, expected):
    cases=json.loads((destination/'project/selected-cases.json').read_text(encoding='utf8'))
    criteria={r['id']:r for r in json.loads((destination/'all-agents-criteria.json').read_text(encoding='utf8'))}
    sessions=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex'))).expanduser()/'sessions'
    rows=[]
    for index,p in enumerate(sessions.rglob('*.jsonl')):
        if index >= 10000:break
        if p.stat().st_size > 20000000:continue
        try:
            with p.open(encoding='utf8') as f:meta=json.loads(f.readline()).get('payload',{})
        except (OSError,ValueError):continue
        source=meta.get('source',{});spawn=source.get('subagent',{}).get('thread_spawn',{}) if isinstance(source,dict) else {}
        if spawn.get('parent_thread_id')!=root_session:continue
        role=meta.get('agent_role') or spawn.get('agent_role')
        if role not in expected:continue
        commands=[];finals=[];completed=False; outputs=[];payloads=[]
        for line in p.read_text(encoding='utf8').splitlines():
            try:d=json.loads(line)
            except ValueError:continue
            a=d.get('payload',{})
            if d.get('type')=='response_item':payloads.append(a)
            if d.get('type')=='response_item' and a.get('type') in ('function_call','custom_tool_call'):
                code=a.get('arguments',a.get('input',''))
                if 'check.py' in str(code):commands.append({'name':a.get('name'),'input':code})
            if d.get('type')=='response_item' and a.get('type') in ('function_call_output','custom_tool_call_output'):
                outputs.append(str(a.get('output','')))
            if d.get('type')=='response_item' and a.get('type')=='message' and a.get('role')=='assistant' and a.get('phase')=='final_answer':
                finals.append('\n'.join(c.get('text','') for c in a.get('content',[]) if isinstance(c,dict)))
            if d.get('type')=='event_msg' and a.get('type')=='task_complete':completed=True
        case=next(c for c in cases if c['agent_type']==role)
        rule=criteria.get(case['id'],case.get('evidence_rule',{}))
        outcomes=paired_outcomes(payloads,case,details=rule.get('schema_version')==2)
        accepted=bool(rule) and fixture_passed(outcomes,rule)
        record={'agent_type':role,'session_id':meta.get('id'),'completed':completed,'check_command_recorded':bool(commands),'tool_output_recorded':bool(outputs),'paired_check_exit_codes':[o['exit_code'] if isinstance(o,dict) else o for o in outcomes],'evidence_schema_version':rule.get('schema_version',1),'evidence_class':'NATIVE_SMOKE_ONLY','professional_qualification':'NOT_EVALUATED','fixture_outcome_verified':accepted,'final':finals[-1] if finals else None}
        rows.append(record)
    (destination/'native-results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
    verified={r['agent_type'] for r in rows if r['completed'] and r['check_command_recorded'] and r.get('fixture_outcome_verified') and r['final'] and sum(x['agent_type']==r['agent_type'] for x in rows)==1}
    return {'evidence_class':'NATIVE_SMOKE_ONLY','professional_qualification':'NOT_EVALUATED','expected':len(expected),'verified':len(verified),'missing':sorted(set(expected)-verified)}

def main():
    revision_start=subprocess.run(['git','-C',str(ROOT),'rev-parse','HEAD'],capture_output=True,text=True,timeout=10)
    source_revision=revision_start.stdout.strip() if revision_start.returncode==0 else None
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',action='store_true',help='Explicitly authorize local model runs and quota consumption')
    ap.add_argument('--include-packs',action='store_true',help='Include ten explicitly installed optional profiles in the isolated native test project')
    ap.add_argument('--all',action='store_true',help='Run every one of the 29 native types')
    ap.add_argument('--agents',help='Optional comma-separated case IDs for a focused retry, e.g. A00,S14')
    ap.add_argument('--out',type=Path,help='New empty evidence directory, outside source recommended')
    ap.add_argument('--timeout',type=int,default=1800)
    args=ap.parse_args()
    if not 60<=args.timeout<=7200:raise ValueError('--timeout must be 60..7200 seconds')
    catalog=json.loads((ROOT/'core/agents.json').read_text(encoding='utf8'))['agents']
    if args.include_packs:
        for index,p in enumerate(sorted((ROOT/'packs').glob('*/manifest.json')),1):
            m=json.loads(p.read_text(encoding='utf8'));catalog.append({'id':f'P{index:02d}','name':m['agents'][0]['name'],'pack':m['name']})
    ids={'A00','S14','G01','G02'}
    if args.agents:
        if args.all:raise ValueError('--agents and --all are mutually exclusive')
        ids=set(args.agents.split(','))
        if not ids or not ids<={a['id'] for a in catalog}:raise ValueError('Unknown case ID')
    chosen=[a for a in catalog if args.all or a['id'] in ids or (args.include_packs and a.get('pack') and not args.agents)]
    if not args.run:
        print(json.dumps({'dry_run':True,'native_types':[a['name'] for a in chosen],'quota_consumed':False,'acceptance_scope':'Individual native role load/completion and controlled synthetic check; not exhaustive domain certification'},indent=2));return 0
    codex=shutil.which('codex')
    if not codex:raise ValueError('Codex CLI not found; install/sign in to a compatible Codex first')
    if not args.out:raise ValueError('--out required with --run')
    destination=args.out.expanduser().resolve()
    if destination==ROOT or ROOT in destination.parents:raise ValueError('--out must be outside source checkout')
    if destination.exists() and any(destination.iterdir()):raise ValueError('Evidence directory must be new/empty')
    destination.mkdir(parents=True,exist_ok=True)
    subprocess.run([sys.executable,str(ROOT/'tools/native_cases.py'),str(destination),str(ROOT/'core/agents.json')],check=True)
    project=destination/'project'
    subprocess.run([sys.executable,str(ROOT/'install.py'),'--project',str(project),'--apply'],check=True)
    plan=json.loads((project/'cases.json').read_text(encoding='utf8'))
    if args.include_packs:
        try:from .native_pack_cases import create
        except ImportError:from native_pack_cases import create
        plan += create(project,ROOT/'packs')
        for a in chosen:
            if a.get('pack'):
                subprocess.run([sys.executable,'-B',str(ROOT/'tools/guardian_packs.py'),'install','--pack',a['pack'],'--project',str(project),'--apply'],check=True)
    plan=[with_check_instruction(c) for c in plan if c['id'] in {a['id'] for a in chosen}]
    (project/'selected-cases.json').write_text(json.dumps(plan,indent=2),encoding='utf8')
    prompt=build_prompt(plan,project)
    prompt_file=destination/'prompt-private.txt'
    fd=os.open(prompt_file,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w',encoding='utf8') as stream:stream.write(prompt)
    cmd=codex_command(codex,project)
    mutable={'S05/index.html','S08/domain.py','S24/domain.py'}
    protected={str(p.relative_to(project)):hashlib.sha256(p.read_bytes()).hexdigest() for c in plan for p in Path(c['case_directory']).rglob('*') if p.is_file() and str(p.relative_to(project)).replace('\\','/') not in mutable}
    (destination/'protected-fixtures.json').write_text(json.dumps(protected,sort_keys=True,indent=2),encoding='utf8')
    started=time.monotonic()
    with (destination/'events.jsonl').open('w',encoding='utf8') as output,(destination/'stderr.log').open('w',encoding='utf8') as error,prompt_file.open('rb') as prompt_input:
        p=subprocess.Popen(cmd,stdout=output,stderr=error,stdin=prompt_input,text=True,encoding='utf8',cwd=project)
        try:code=p.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            p.terminate()
            try:p.wait(timeout=15)
            except subprocess.TimeoutExpired:p.kill();p.wait(timeout=15)
            code='timeout_descendants_not_verified'
    events=[]
    for line in (destination/'events.jsonl').read_text(encoding='utf8').splitlines():
        try:events.append(json.loads(line))
        except ValueError:pass
    tid=next((e.get('thread_id') for e in events if e.get('type')=='thread.started'),None)
    result=extract(tid,destination,[a['name'] for a in chosen]) if tid else {'expected':len(chosen),'verified':0,'missing':[a['name'] for a in chosen]}
    changed=[rel for rel,digest in protected.items() if not (project/rel).is_file() or hashlib.sha256((project/rel).read_bytes()).hexdigest()!=digest]
    result['protected_fixtures_unchanged']=not changed
    result['fixture_drift']=changed
    revision=subprocess.run(['git','-C',str(ROOT),'rev-parse','HEAD'],capture_output=True,text=True,timeout=10)
    result['revision']=source_revision
    result['input_delivery']='PUBLIC_TASKS_INLINE_UTF8_STDIN'
    result['model_parent_filesystem_read_required']=False
    result['source_revision_unchanged']=None if source_revision is None else revision.returncode==0 and revision.stdout.strip()==source_revision
    result.update(acceptance_scope='Native type, parent, completion, recorded check and tool output; not domain certification',exit_code=code,elapsed_seconds=round(time.monotonic()-started,2),root_session=tid)
    (destination/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result,indent=2))
    return 0 if code==0 and not result['missing'] and not changed and result['source_revision_unchanged'] is not False else 1
if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,OSError,subprocess.SubprocessError) as exc:print(str(exc),file=sys.stderr);sys.exit(2)
