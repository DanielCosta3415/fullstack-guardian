"""Explicit supervisor acceptance, separate from model-produced task results.

Commands and reviews come from the trusted caller, never from imported task JSON.
Hashes detect local drift, not a hostile writer that can replace all local state.
Checks run with inherited host permissions; this API is not a command sandbox.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import threading

try:
    from .guardian_policy import authorize_action
    from .guardian_runtime import inventory, terminate_tree
except ImportError:
    from guardian_policy import authorize_action
    from guardian_runtime import inventory, terminate_tree


class WorkflowError(ValueError):
    pass


def _executor():
    try:
        from . import guardian_executor
    except ImportError:
        import guardian_executor
    return guardian_executor


def _digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _context(home):
    ex = _executor()
    home = ex.safe(Path(home))
    state, plan = ex._load(home)
    if not all(r['state'] == 'produced' for r in state['tasks'].values()):
        raise WorkflowError('All tasks must have produced scope-checked artifacts')
    current = {}
    for ident, record in state['tasks'].items():
        slot = ex.safe(Path(record['worktree']))
        if slot != home / 'worktree' and slot != home / 'audit-worktrees' / ident:
            raise WorkflowError('Unexpected task checkout')
        current[ident] = ex._plan_hash(inventory(slot))
    # Sequential tasks share one checkout: only the final serialized artifact
    # describes it. Parallel audit tasks each seal their own private checkout.
    last = max(state['tasks'], key=lambda k: state['tasks'][k].get('started_at_ns', 0))
    for ident, record in state['tasks'].items():
        if record['worktree'] != str(home / 'worktree') or ident == last:
            if current[ident] != record.get('artifact_sha256'):
                raise WorkflowError('Artifact changed after production')
    seal = _digest({'run_id': state['run_id'], 'plan_hash': state['plan_hash'],
                    'artifacts': current, 'events': {k:r['events_sha256'] for k,r in state['tasks'].items()}})
    return ex, home, state, plan, seal


def _load(home, state, seal):
    path = home / 'workflow.json'
    if not path.exists():
        return {'schema_version': 1, 'run_id': state['run_id'], 'seal': seal, 'state': 'produced'}
    record = json.loads(_executor().safe(path).read_text(encoding='utf-8'))
    if record.get('run_id') != state['run_id'] or record.get('seal') != seal:
        raise WorkflowError('Workflow evidence belongs to another artifact/run')
    if record.get('state')=='produced':
        raise WorkflowError('Persisted workflow cannot reset to produced; use a fresh reviewed run')
    return record


def _persist(ex, home, record):
    ex.atomic_json(home / 'workflow.json', record)
    try:
        from .guardian_trace import append
    except ImportError:
        from guardian_trace import append
    append(home / 'journal.jsonl', 'verification', {'workflow_state': record['state'],
           'artifact_seal': record['seal'], 'record_sha256': _digest(record), 'authenticated': False})
    return record


def _professional_evidence(ex, home, state, plan, workflow):
    """Corroborate specialist output against the actual stream, files and checks.

    This is scoped artifact verification, not an authenticated SME credential.
    The producer cannot waive an obligation or accept its own handoff.
    """
    seals = {}
    for task in plan['tasks']:
        ident = task['id']; produced = state['tasks'][ident]
        log = ex.safe(home/'events'/(ident+'-attempt-'+str(produced['attempts'])+'.jsonl'))
        output = ex.professional_output(log, task)
        path = ex.safe(home/'results'/(ident+'.professional.json'))
        if output is None or not path.is_file() or path.stat().st_size > 65536:
            raise WorkflowError('Missing valid professional result for '+ident)
        if (hashlib.sha256(path.read_bytes()).hexdigest() != produced.get('professional_output_sha256')
                or json.loads(path.read_text(encoding='utf8')) != output):
            raise WorkflowError('Professional result differs from produced CLI evidence')
        if any(x['status'] != 'produced' for x in output['obligations']) or output['handoff']['status'] != 'pending_consumer_acceptance':
            raise WorkflowError('Professional obligations/handoff remain blocked or not verified')
        if any(r['severity'] in ('high', 'critical') for r in output['residual_risks']):
            raise WorkflowError('New material professional risk requires re-planning and review')
        cwd = ex.safe(Path(produced['worktree']))
        current = inventory(cwd)
        for artifact in output['artifacts']:
            if current.get(artifact['path']) != artifact['sha256']:
                raise WorkflowError('Professional artifact changed or missing')
        approved = {ident+':'+str(i): argv for i, argv in enumerate(task['contract']['checks'])}
        actual = {ident+':'+str(i): c for i, c in enumerate(c for c in workflow['checks'] if c['task_id'] == ident)}
        for claim in output['checks']:
            cid = claim['id']
            if (cid not in approved or claim['argv'] != approved[cid] or ex.safe(cwd / claim['cwd']) != cwd
                    or cid not in actual or claim['status'] != 'passed' or claim['exit_code'] != actual[cid]['exit_code']):
                raise WorkflowError('Professional check claim lacks matching supervisor observation')
        seals[ident] = hashlib.sha256(path.read_bytes()).hexdigest()
    return seals


def inspect(home):
    ex, home, state, plan, seal = _context(home)
    record = _load(home, state, seal)
    if record['state'] == 'produced': return record
    if record['state'] not in ('checking','blocked','checked','reviewed','verified','integrated'):
        raise WorkflowError('Unknown workflow state')
    try:
        from .guardian_trace import verify as verify_trace
    except ImportError:
        from guardian_trace import verify as verify_trace
    verify_trace(home/'journal.jsonl')
    observations=[json.loads(line)['data'] for line in (home/'journal.jsonl').read_text(encoding='utf-8').splitlines()
                  if json.loads(line)['event']=='verification' and json.loads(line)['data'].get('artifact_seal')==seal]
    if not observations or observations[-1].get('record_sha256') != _digest(record):
        raise WorkflowError('Workflow checkpoint not corroborated by local supervisor journal')
    expected=[(t['id'], index, _digest(argv)) for t in plan['tasks'] for index,argv in enumerate(t['contract']['checks'])]
    checks=record.get('checks', [])
    if record['state'] in ('checked','reviewed','verified','integrated') and (not expected or len(checks)!=len(expected)):
        raise WorkflowError('Incomplete check evidence')
    for check, (ident,index,argv_sha) in zip(checks,expected):
        if (check.get('task_id')!=ident or check.get('argv_sha256')!=argv_sha or check.get('exit_code')!=0
            or check.get('log')!='checks/'+ident+'-'+str(index)+'.log'):
            raise WorkflowError('Check identity/result does not match approved contract')
        path = ex.safe(home / check['log'])
        if home not in path.parents or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != check['output_sha256']:
            raise WorkflowError('Supervisor check evidence changed/missing')
    if record['state'] in ('reviewed','verified','integrated'):
        review=record.get('review',{}); path=ex.safe(home/review.get('path',''))
        if (not review.get('producer') or not review.get('reviewer') or review['producer']==review['reviewer']
            or home not in path.parents or not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest()!=review.get('sha256')):
            raise WorkflowError('Independent review evidence changed/missing')
    if record['state'] in ('verified', 'integrated'):
        if record.get('professional_outputs') != _professional_evidence(ex, home, state, plan, record):
            raise WorkflowError('Professional output verification changed/missing')
    if record['state']=='integrated':
        receipt=json.loads(ex.safe(home/'integration-result.json').read_text(encoding='utf-8'))
        if receipt.get('state')!='applied_uncommitted' or receipt.get('patch_sha256')!=record.get('patch_sha256'):
            raise WorkflowError('Integration receipt changed/missing')
    return record


def _run(argv, cwd, log, timeout, max_bytes):
    if (not isinstance(argv, list) or not argv or len(argv)>100 or
        any(not isinstance(x,str) or not x or len(x)>4000 or '\x00' in x for x in argv)):
        raise WorkflowError('Checks require bounded nonempty argv arrays')
    # A direct executable is required: never an implicit shell or PATH alias.
    binary = Path(argv[0])
    if not binary.is_absolute() or not binary.is_file() or binary.suffix.lower() in ('.bat','.cmd','.ps1'):
        raise WorkflowError('Check executable must be an explicit existing executable path')
    log.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with log.open('xb') as out:
        os.chmod(log,0o600)
        kwargs = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name=='nt' else {'start_new_session':True}
        proc = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, **kwargs)
        exceeded=threading.Event()
        def drain():
            total=0
            while True:
                block=proc.stdout.read(4096)
                if not block: break
                remaining=max_bytes-total
                if remaining>0:
                    out.write(block[:remaining]); total+=min(remaining,len(block)); out.flush()
                if len(block)>remaining:
                    exceeded.set()
                    break
        reader=threading.Thread(target=drain,daemon=True); reader.start()
        try:
            while proc.poll() is None:
                if time.monotonic()-started >= timeout or exceeded.is_set():
                    terminate_tree(proc)
                    raise WorkflowError('Check timeout/output budget exceeded; no automatic retry')
                time.sleep(.02)
            reader.join(timeout=2)
            if reader.is_alive():
                terminate_tree(proc)
                raise WorkflowError('Check output stream did not close; descendants uncertain')
            if exceeded.is_set():
                raise WorkflowError('Check output budget exceeded')
            return proc.returncode
        finally:
            if proc.poll() is None:
                terminate_tree(proc)
            reader.join(timeout=2)
            if not reader.is_alive(): proc.stdout.close()


def check(home, *, approved_checks, grant, timeout=120, max_output_bytes=65536):
    """Execute explicitly selected checks; listing a contract check grants nothing.

    A check grant is consent to arbitrary local executable effects within inherited
    permissions, not proof of containment. A changed checkout fails acceptance.
    """
    ex, home, state, plan, seal = _context(home)
    if type(timeout) is not int or not 1<=timeout<=600 or type(max_output_bytes) is not int or not 1<=max_output_bytes<=1048576:
        raise WorkflowError('Invalid check budget')
    if not isinstance(approved_checks, dict) or set(approved_checks) != set(state['tasks']):
        raise WorkflowError('Explicit approved checks must cover every task')
    for ident, task in ((t['id'], t) for t in plan['tasks']):
        checks = approved_checks[ident]
        if not isinstance(checks,list) or not checks or len(checks)>20 or checks != task['contract']['checks']:
            raise WorkflowError('Operator checks must exactly match nonempty contract checks')
        if not authorize_action('local_check', state['project'], state['tasks'][ident]['worktree'], grant)['allowed']:
            raise WorkflowError('Check execution requires a trusted scoped local_check grant')
    lock = ex._locked(home)
    record = None
    try:
        ex,home,state,plan,seal=_context(home)
        record = _load(home, state, seal)
        if record['state'] != 'produced':
            raise WorkflowError('Checks require a fresh produced workflow')
        record.update(state='checking', checks=[])
        _persist(ex,home,record)
        for task in plan['tasks']:
            ident=task['id']
            commands=approved_checks[ident]
            cwd = ex.safe(Path(state['tasks'][ident]['worktree']))
            before = inventory(cwd)
            for index, argv in enumerate(commands):
                if not authorize_action('local_check',state['project'],cwd,grant)['allowed']:
                    raise WorkflowError('Check grant expired')
                relative = 'checks/'+ident+'-'+str(index)+'.log'
                log = ex.safe(home / relative)
                code = _run(argv,cwd,log,timeout,max_output_bytes)
                record['checks'].append({'task_id':ident,'argv_sha256':_digest(argv),'exit_code':code,
                    'log':relative,'output_sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
                if code != 0 or inventory(cwd) != before:
                    raise WorkflowError('Check failed or changed checkout; fresh production required')
        _context(home)
        record['state']='checked'
        return _persist(ex,home,record)
    except BaseException:
        if record is not None and record['state']=='checking':
            record['state']='blocked'
            _persist(ex,home,record)
        raise
    finally:
        lock.unlink(missing_ok=True)


def review(home, *, reviewer, producer, evidence, grant):
    """Record independently supplied review evidence; no model claim promotes it.

    Identity is operator supplied, not an authenticated identity provider.
    """
    ex, home, state, _, seal = _context(home)
    if not authorize_action('review',state['project'],home,grant)['allowed']:
        raise WorkflowError('Independent review requires a scoped trusted review grant')
    if any(not isinstance(x,str) or not x.strip() or len(x)>100 for x in (reviewer,producer)) or reviewer==producer:
        raise WorkflowError('Distinct explicit producer and reviewer identities required')
    evidence=ex.safe(Path(evidence))
    if home not in evidence.parents or not evidence.is_file() or not 1<=evidence.stat().st_size<=1048576:
        raise WorkflowError('Review evidence must be a nonempty bounded file within the run')
    lock=ex._locked(home)
    try:
        record=inspect(home)
        if record['state']!='checked': raise WorkflowError('Independent review requires successful checked state')
        record.update(state='reviewed',review={'reviewer':reviewer,'producer':producer,
            'path':evidence.relative_to(home).as_posix(),'sha256':hashlib.sha256(evidence.read_bytes()).hexdigest(),
            'identity_authenticated':False})
        return _persist(ex,home,record)
    finally: lock.unlink(missing_ok=True)


def verify(home):
    ex,home,state,plan,seal=_context(home)
    lock=ex._locked(home)
    try:
        record=inspect(home)
        if record['state']!='reviewed': raise WorkflowError('Verification requires checked and independently reviewed evidence')
        review=record['review']; path=ex.safe(home/review['path'])
        if home not in path.parents or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=review['sha256']:
            raise WorkflowError('Independent review evidence changed/missing')
        professional = _professional_evidence(ex, home, state, plan, record)
        record.update(state='verified', professional_outputs=professional,
                      verification_scope='bound professional outputs/artifacts, approved local checks and operator-supplied independent review; not SME qualification or release readiness')
        return _persist(ex,home,record)
    finally: lock.unlink(missing_ok=True)


def record_integrated(home, patch_sha256):
    """Internal integration hook, called only after the integrator applied its patch.

    The integration receipt must already exist. Never accepts a model result.
    """
    ex=_executor(); home=ex.safe(Path(home))
    path=ex.safe(home/'workflow.json')
    if not path.exists(): return None # legacy explicit manual integration remains supported
    record=inspect(home)
    if record['state']!='verified': raise WorkflowError('Workflow integration requires verified state')
    receipt=json.loads(ex.safe(home/'integration-result.json').read_text(encoding='utf-8'))
    if receipt.get('patch_sha256')!=patch_sha256 or receipt.get('state')!='applied_uncommitted':
        raise WorkflowError('Applied integration receipt missing/mismatched')
    record.update(state='integrated',patch_sha256=patch_sha256)
    return _persist(ex,home,record)


def main():
    import argparse
    try:
        from .guardian_policy import Grant
    except ImportError:
        from guardian_policy import Grant
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',type=Path,required=True)
    sub=parser.add_subparsers(dest='action',required=True)
    checks=sub.add_parser('check'); checks.add_argument('--checks',type=Path,required=True)
    checks.add_argument('--authorize-checks',action='store_true',help='Explicit consent to these host executable argv checks under inherited permissions; no sandbox implied')
    checks.add_argument('--timeout',type=int,default=120)
    reviewed=sub.add_parser('review'); reviewed.add_argument('--reviewer',required=True)
    reviewed.add_argument('--producer',required=True); reviewed.add_argument('--evidence',type=Path,required=True)
    reviewed.add_argument('--authorize-review',action='store_true')
    sub.add_parser('inspect'); sub.add_parser('verify')
    args=parser.parse_args()
    try:
        if args.action=='inspect': result=inspect(args.home)
        elif args.action=='verify': result=verify(args.home)
        else:
            _,home,state,_,_=_context(args.home)
            authorized=args.authorize_checks if args.action=='check' else args.authorize_review
            if not authorized: raise WorkflowError('Explicit operator authorization flag is required')
            action='local_check' if args.action=='check' else 'review'
            grant=Grant(state['project'],frozenset({action}),(str(home),),time.time()+18000,'trusted_supervisor')
            if args.action=='check':
                source=_executor().safe(args.checks)
                if source.stat().st_size>1048576: raise WorkflowError('Approved-check file exceeds budget')
                result=check(home,approved_checks=json.loads(source.read_text(encoding='utf-8')),grant=grant,timeout=args.timeout)
            else:
                result=review(home,reviewer=args.reviewer,producer=args.producer,evidence=args.evidence,grant=grant)
        print(json.dumps(result,indent=2)); return 0
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)})); return 2


if __name__=='__main__': raise SystemExit(main())
