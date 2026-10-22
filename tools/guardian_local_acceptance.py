"""Corroborate operator-owned local evidence, never authenticate a human.

Native session records and workspace files are mutable by their OS account.
This verifier detects missing/inconsistent evidence, not a malicious host owner.
It reads only explicit evidence paths and matching native session transcripts;
credentials are neither needed nor opened. No code from evidence is executed.
"""
import hashlib
import json
import math
import re
import subprocess
import stat
import sys
import tempfile
from pathlib import Path

try:
    from .native_check_evidence import paired_outcomes, fixture_passed
except ImportError:
    from native_check_evidence import paired_outcomes, fixture_passed


def safe(path):
    try:
        path=Path(path).absolute()
        for item in (path,*path.parents):
            if item.is_symlink() or (item.exists() and getattr(item.stat(),'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT):
                raise ValueError('Linked/reparse evidence path rejected')
    except (TypeError,OSError) as exc:
        raise ValueError('Invalid or inaccessible evidence path') from exc
    return path


def strict_json(text):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate evidence JSON key')
            result[key]=value
        return result
    def finite(value):raise ValueError('Nonfinite evidence JSON number rejected')
    def finite_float(value):
        number=float(value)
        if not math.isfinite(number):raise ValueError('Nonfinite evidence JSON number rejected')
        return number
    try:
        return json.loads(text,object_pairs_hook=unique,parse_constant=finite,parse_float=finite_float)
    except (TypeError,RecursionError) as exc:
        raise ValueError('Malformed evidence JSON') from exc


def read_json(path, limit=2_000_000):
    path=safe(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>limit:
        raise ValueError('Evidence path unavailable, linked or oversized')
    return strict_json(path.read_text(encoding='utf8'))


def session(path):
    path=safe(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>20_000_000:
        raise ValueError('Native session unavailable, linked or oversized')
    records=[strict_json(line) for line in path.read_text(encoding='utf8').splitlines() if line.strip()]
    if any(not isinstance(r,dict) or not isinstance(r.get('payload'),dict) for r in records):
        raise ValueError('Native session records and payloads must be objects')
    if any(not isinstance(r.get('type'),str) or not r['type'].strip() for r in records):
        raise ValueError('Native session record types must be nonempty strings')
    if any(r['type'] in ('event_msg','response_item') and
           (not isinstance(r['payload'].get('type'),str) or not r['payload']['type'].strip()) for r in records):
        raise ValueError('Native event and response payload types must be nonempty strings')
    if not records or records[0].get('type')!='session_meta':raise ValueError('Native session metadata required')
    meta=records[0].get('payload',{})
    source=meta.get('source',{})
    if not isinstance(source,dict) or not isinstance(source.get('subagent',{}),dict):
        raise ValueError('Native child source and subagent metadata must be objects')
    spawn=source.get('subagent',{}).get('thread_spawn',{})
    if not isinstance(spawn,dict):raise ValueError('Native child spawn metadata must be an object')
    role=meta.get('agent_role') or spawn.get('agent_role')
    if any(not isinstance(v,str) or not v for v in (meta.get('id'),role,spawn.get('parent_thread_id'))):
        raise ValueError('Native child identity, role and parent must be strings')
    completed=any(r.get('type')=='event_msg' and r.get('payload',{}).get('type')=='task_complete' for r in records)
    payloads=[r.get('payload',{}) for r in records if r.get('type')=='response_item']
    for payload in payloads:
        if payload.get('type')=='message':
            content=payload.get('content',[])
            if (not isinstance(content,list) or any(not isinstance(c,dict) or
                    ('text' in c and not isinstance(c['text'],str)) for c in content)):
                raise ValueError('Native message content must contain structured text blocks')
    finals=[p for p in payloads if p.get('type')=='message' and p.get('role')=='assistant' and p.get('phase')=='final_answer' and any(c.get('text','').strip() for c in p.get('content',[]) if isinstance(c,dict))]
    if not completed or not finals:raise ValueError('Native child completion/final required')
    return meta,spawn,role,payloads


def check_source(root,revision):
    root=safe(root)
    if not root.is_dir():raise ValueError('Source root must be an existing directory')
    try:
        head=subprocess.run(['git','-C',str(root),'rev-parse','HEAD'],capture_output=True,text=True,timeout=15)
        dirty=subprocess.run(['git','-C',str(root),'status','--porcelain','--untracked-files=normal'],capture_output=True,text=True,timeout=15)
    except (OSError,subprocess.SubprocessError) as exc:
        raise ValueError('Source revision verification unavailable') from exc
    if head.returncode or head.stdout.strip()!=revision or dirty.returncode or dirty.stdout.strip():
        raise ValueError('Source revision changed or checkout is not clean')


def expected_roles(root):
    root=Path(root)
    roles={a['name'] for a in read_json(root/'core/agents.json')['agents']}
    for manifest in sorted((root/'packs').glob('*/manifest.json')):
        roles.update(a['name'] for a in read_json(manifest)['agents'])
    if len(roles)!=39:raise ValueError('Source must define exactly 39 distinct native roles')
    return roles


def verify_runtime(root,evidence):
    """Bind the actually installed harness, catalog and all profiles to source."""
    root=safe(root);project=safe(Path(evidence)/'project')
    count=0
    for directory in ('global','core','tools','packs','eval'):
        for source in (root/directory).rglob('*'):
            if not source.is_file() or '__pycache__' in source.parts or source.suffix=='.pyc':continue
            installed=safe(project/'.guardian'/source.relative_to(root))
            if not installed.is_file() or safe(source).read_bytes()!=installed.read_bytes():
                raise ValueError('Installed runtime differs from pinned source')
            count+=1
    profiles=list((root/'global/agents').glob('*.toml'))
    for manifest in sorted((root/'packs').glob('*/manifest.json')):
        for agent in read_json(manifest)['agents']:
            source=safe(manifest.parent/agent['file'])
            if manifest.parent.resolve() not in source.resolve().parents:raise ValueError('Pack profile escapes source pack')
            profiles.append(source)
    if len(profiles)!=39:raise ValueError('Native installed profile count mismatch')
    for source in profiles:
        installed=safe(project/'.codex/agents'/source.name)
        if not installed.is_file() or safe(source).read_bytes()!=installed.read_bytes():
            raise ValueError('Installed native profile differs from pinned source')
    return {'runtime_files_verified':count,'profiles_verified':39}


def verify_native_baseline(root,evidence):
    """Rebuild only trusted source fixtures, never execute candidate/evidence code.

    Local summaries/manifests cannot redefine BUILD or the expected assertion.
    The sole write is a TemporaryDirectory cleaned by its standard context.
    """
    root=safe(root);evidence=safe(evidence)
    actual_cases=read_json(evidence/'project/selected-cases.json')
    actual_rules=read_json(evidence/'all-agents-criteria.json')
    actual_protected=read_json(evidence/'protected-fixtures.json')
    with tempfile.TemporaryDirectory(prefix='guardian-release-baseline-') as folder:
        # Only this freshly created stdlib-owned root is canonicalized first:
        # macOS /var commonly resolves to /private/var. Submitted evidence still
        # passes safe() before resolution and cannot traverse a reparse link.
        baseline=safe(Path(folder).resolve(strict=True))
        command=[sys.executable,'-B',str(root/'tools/native_cases.py'),str(baseline),str(root/'core/agents.json')]
        process=subprocess.run(command,capture_output=True,text=True,timeout=30)
        if process.returncode:raise ValueError('Trusted native fixture generator failed')
        # Load only the pinned product module, not an evidence-provided path.
        code='import json,runpy,sys;from pathlib import Path;m=runpy.run_path(sys.argv[1]);p=Path(sys.argv[2]);print(json.dumps(m["create"](p,Path(sys.argv[3]))))'
        process=subprocess.run([sys.executable,'-B','-c',code,str(root/'tools/native_pack_cases.py'),str(baseline/'project'),str(root/'packs')],
                               capture_output=True,text=True,timeout=30)
        if process.returncode or len(process.stdout)>100_000:raise ValueError('Trusted optional native fixture generator failed')
        canonical=read_json(baseline/'project/cases.json')+json.loads(process.stdout)
        if actual_rules!=read_json(baseline/'all-agents-criteria.json'):
            raise ValueError('Native criteria differ from pinned source baseline')
        if not isinstance(actual_cases,list) or len(actual_cases)!=len(canonical):raise ValueError('Native selected inventory differs from pinned source baseline')
        selected={c['id']:c for c in actual_cases}
        if len(selected)!=len(canonical):raise ValueError('Duplicate selected native case')
        for case in canonical:
            actual=selected.get(case['id'],{})
            if any(actual.get(k)!=case.get(k) for k in ('agent_type','mode','pack','evidence_rule')):
                raise ValueError('Native case mode/role/rule differs from pinned source baseline')
            expected_directory=(evidence/'project'/case['id']).resolve()
            if safe(actual.get('case_directory','')).resolve()!=expected_directory:
                raise ValueError('Native case directory differs from pinned source baseline')
        mutable={'S05/index.html','S08/domain.py','S24/domain.py'}
        protected={str(p.relative_to(baseline/'project')):hashlib.sha256(p.read_bytes()).hexdigest()
                   for case in canonical for p in Path(case['case_directory']).rglob('*') if p.is_file()
                   and p.relative_to(baseline/'project').as_posix() not in mutable}
        # Native harness writes host-native relative separators; normalize those
        # keys only, so neither criteria nor fixture contents can be rebaselined.
        normalize=lambda manifest:{k.replace('\\','/'):v for k,v in manifest.items()}
        if not isinstance(actual_protected,dict) or normalize(actual_protected)!=normalize(protected):
            raise ValueError('Protected native fixture manifest differs from pinned source baseline')
    return {'source_baseline_corroborated':True,'cases':39}


def verify_local_native(evidence,revision,roles,session_records):
    evidence=safe(evidence).resolve()
    summary=read_json(evidence/'summary.json')
    if (summary.get('revision')!=revision or summary.get('source_revision_unchanged') is not True
            or summary.get('protected_fixtures_unchanged') is not True or summary.get('fixture_drift')!=[]
            or summary.get('missing')!=[] or type(summary.get('exit_code')) is not int or summary['exit_code']!=0
            or any(type(summary.get(k)) is not int or summary[k]!=39 for k in ('expected','verified'))):
        raise ValueError('Complete exact-revision native local acceptance required')
    root_session=summary.get('root_session')
    if not isinstance(root_session,str) or not root_session:raise ValueError('Native root session identity required')
    cases=read_json(evidence/'project/selected-cases.json')
    criteria=read_json(evidence/'all-agents-criteria.json')
    if not isinstance(cases,list) or len(cases)!=39 or {c['agent_type'] for c in cases}!=roles:
        raise ValueError('Native case inventory mismatch')
    rules={r['id']:r for r in criteria}
    if len(rules)!=len(criteria):raise ValueError('Duplicate native criteria')
    protected=read_json(evidence/'protected-fixtures.json')
    if not isinstance(protected,dict) or not 39<=len(protected)<=1000:raise ValueError('Protected fixture manifest required')
    project=(evidence/'project').resolve()
    for name,digest in protected.items():
        path=safe(project/name)
        resolved=path.resolve()
        if (path.is_symlink() or project not in resolved.parents or not path.is_file()
                or not isinstance(digest,str) or not re.fullmatch(r'[0-9a-f]{64}',digest)
                or path.stat().st_size>2_000_000 or hashlib.sha256(path.read_bytes()).hexdigest()!=digest):
            raise ValueError('Protected fixture drift or unsafe path')
    if not isinstance(session_records,(list,tuple)) or len(session_records)!=39:
        raise ValueError('Exactly 39 explicit native session records required; summary alone is insufficient')
    seen_roles=set();seen_ids=set(); hashes=[]
    by_role={c['agent_type']:c for c in cases}
    for path in session_records:
        meta,spawn,role,payloads=session(path)
        identity=meta.get('id')
        if (role not in roles or role in seen_roles or not isinstance(identity,str) or not identity
                or identity in seen_ids or spawn.get('parent_thread_id')!=root_session):
            raise ValueError('Native role, identity, parent or uniqueness mismatch')
        case=by_role[role]
        case_path=Path(case['case_directory']).resolve()
        if project not in case_path.parents:raise ValueError('Native case outside evidence project')
        rule=rules.get(case['id'],case.get('evidence_rule',{}))
        check_rel=str((case_path/'check.py').relative_to(project))
        if check_rel not in protected and check_rel.replace('\\','/') not in protected:
            raise ValueError('Every native check must be protected')
        if rule.get('schema_version')!=2 or not fixture_passed(paired_outcomes(payloads,case,details=True),rule):
            raise ValueError('Native tool check/output pair does not satisfy fixture criteria')
        seen_roles.add(role);seen_ids.add(identity)
        hashes.append(hashlib.sha256(Path(path).read_bytes()).hexdigest())
    return {'revision':revision,'expected':39,'verified':39,'all_native_roles_verified':True,
            'protected_fixtures_unchanged':True,'evidence_class':'CORROBORATED_LOCAL_NATIVE_SMOKE',
            'session_sha256':sorted(hashes),'remote_native_test_performed':False}


def review_claim_digest(report):
    """Stable binding for the review's semantic claims, excluding session wrapper.

    The reviewer can emit this digest in its final before that session is closed.
    The operator subsequently adds session path/hash without a hash cycle.
    """
    fields=('gate','revision','artifact_sha256','kind','decision','findings_unresolved','limitations','implementation_session')
    claim={key:report.get(key) for key in fields}
    return hashlib.sha256(json.dumps(claim,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf8')).hexdigest()


def verify_local_reviews(reports,revision,artifact_sha256):
    if not isinstance(reports,(list,tuple)) or len(reports)!=2:raise ValueError('Distinct G01/G02 advisory reviews required')
    seen=set();identities=set(); hashes=[];parents=set()
    roles={'G01':'guardian_independent_auditor','G02':'guardian_release_auditor'}
    for path in reports:
        report=read_json(path)
        gate=report.get('gate')
        if (gate not in roles or gate in seen or report.get('revision')!=revision or report.get('artifact_sha256')!=artifact_sha256
                or report.get('kind')!='AI_ADVISORY' or report.get('decision')!='ACCEPTED_WITH_LIMITATIONS'
                or type(report.get('findings_unresolved')) is not int or report['findings_unresolved']!=0
                or not isinstance(report.get('limitations'),list) or not report['limitations']
                or any(not isinstance(v,str) or not v.strip() for v in report['limitations'])):
            raise ValueError('Exact-revision bounded AI advisory review required')
        record=Path(report.get('session_record',''))
        meta,spawn,role,payloads=session(record)
        if (role!=roles[gate] or meta.get('id') in identities or not meta.get('id')
                or not spawn.get('parent_thread_id') or spawn['parent_thread_id']==meta['id']
                or report.get('implementation_session')!=spawn['parent_thread_id']
                or hashlib.sha256(record.read_bytes()).hexdigest()!=report.get('session_sha256')):
            raise ValueError('Distinct advisory native reviewer session/hash mismatch')
        # The native final itself must name the exact scope/digest and decision;
        # a JSON wrapper pointing to an unrelated completed review is insufficient.
        finals='\n'.join(c.get('text','') for p in payloads if p.get('type')=='message' and p.get('role')=='assistant' and p.get('phase')=='final_answer' for c in p.get('content',[]) if isinstance(c,dict))
        if revision not in finals or artifact_sha256 not in finals or 'ACCEPTED_WITH_LIMITATIONS' not in finals:
            raise ValueError('Advisory final lacks pinned revision, ZIP digest or decision')
        if 'GUARDIAN_RELEASE_REVIEW '+review_claim_digest(report) not in finals:
            raise ValueError('Advisory final does not bind exact review claims and limitations')
        seen.add(gate);identities.add(meta['id']);parents.add(spawn['parent_thread_id']);hashes.append(report['session_sha256'])
    if len(parents)!=1 or parents.intersection(identities):raise ValueError('Advisory reviewers must be distinct children of the implementation session')
    return {'review_class':'AI_ADVISORY_LOCAL_ONLY','gates':sorted(seen),'session_sha256':sorted(hashes),
            'human_review_recorded_by_github':False}
