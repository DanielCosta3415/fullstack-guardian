"""Prepare artifacts while refusing a mislabeled stable release.

This local gate authenticates no human and never publishes. Stable promotion
requires actual external evidence and provenance verification, not model claims.
"""
import argparse,hashlib,json,re,subprocess,io,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def inspect(root=ROOT, *, stable_record=None):
    root=Path(root);version=(root/'VERSION').read_text().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-(?:dev|rc)\.\d+)?',version):raise ValueError('Invalid version')
    for file in ('plugin.json','.codex-plugin/plugin.json'):
        if json.loads((root/file).read_text(encoding='utf8'))['version']!=version:raise ValueError('Manifest identity mismatch')
    preview='-' in version
    if stable_record is not None:
        raise ValueError('Stable promotion cannot be authorized by an imported JSON/model claim; use verified external gates')
    return {'version':version,'artifact_preparation_allowed':True,'preview':preview,'stable_promotion_allowed':False,
            'publication_authorized':False,'evidence_authenticated':False,
            'requirements':['unit_and_adversarial_tests','installed_distribution_tests','native_core_and_promoted_optional_acceptance','independent_G01_G02','signed_build_provenance','remote_asset_install_and_recovery'],
            'notice':'Preparation is not stable release authorization. External evidence is not inferred from this configuration.'}


def _api(path):
    p=subprocess.run(['gh','api',path],capture_output=True,text=True,timeout=30)
    if p.returncode or len(p.stdout)>2_000_000:raise ValueError('External GitHub gate unavailable')
    return json.loads(p.stdout)

def _acceptance_artifact(repo,run_id,name,filename,revision):
    inventory=_api(f'repos/{repo}/actions/runs/{run_id}/artifacts?per_page=100')
    items=inventory.get('artifacts',[])
    if inventory.get('total_count',len(items))>100:raise ValueError('Artifact inventory exceeds bound')
    matches=[a for a in items if a.get('name')==name and a.get('expired') is False]
    if len(matches)!=1:raise ValueError('Required unique acceptance artifact missing')
    item=matches[0]
    if type(item.get('id')) is not int or type(item.get('size_in_bytes')) is not int or not 0<item['size_in_bytes']<1_000_000:
        raise ValueError('Invalid acceptance artifact identity/size')
    p=subprocess.run(['gh','api',f'repos/{repo}/actions/artifacts/{item["id"]}/zip'],capture_output=True,timeout=30)
    if p.returncode or len(p.stdout)>1_000_000:raise ValueError('Acceptance artifact unavailable or oversized')
    with zipfile.ZipFile(io.BytesIO(p.stdout)) as archive:
        members=archive.infolist()
        if len(members)!=1 or members[0].filename!=filename or members[0].file_size>100_000:
            raise ValueError('Unexpected acceptance artifact content')
        report=json.loads(archive.read(filename))
    if report.get('revision')!=revision:raise ValueError('Acceptance summary revision mismatch')
    return report

def verify_acceptance_reports(native,grader,revision):
    if any(r.get('revision')!=revision for r in (native,grader)):raise ValueError('Acceptance summary revision mismatch')
    if not (type(native.get('expected')) is int and native['expected']==39 and type(native.get('verified')) is int and native['verified']==39
            and native.get('all_native_roles_verified') is True and native.get('protected_fixtures_unchanged') is True):
        raise ValueError('Individual 39-profile native acceptance not satisfied')
    if not (grader.get('passed') is True and type(grader.get('tests')) is int and grader['tests']>=14
            and all(type(grader.get(k)) is int and grader[k]==0 for k in ('skipped','failures','errors'))):
        raise ValueError('Executed grader gate must pass without skips')


def _trusted_logins(values):
    # Explicit operator allowlist, never inferred from chat, artifact or PR text.
    if not isinstance(values, (list, tuple)):
        raise ValueError('Trusted reviewers must be an explicit list of GitHub logins')
    result=set()
    for value in values:
        if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?',value) or '--' in value:
            raise ValueError('Invalid trusted GitHub reviewer login')
        result.add(value.casefold())
    return result


def _verify_human_reviews(reviews,author,revision,trusted_reviewers=()):
    trusted=_trusted_logins(trusted_reviewers)
    if not isinstance(author,str) or not author:
        raise ValueError('PR author identity unavailable')
    latest={}
    # GitHub returns reviews chronologically; comments do not revoke a review.
    # A later dismissal or changes-requested state must invalidate approval.
    for review in reviews:
        if not isinstance(review,dict):raise ValueError('Invalid review record')
        if review.get('state') not in ('APPROVED','CHANGES_REQUESTED','DISMISSED'):continue
        user=review.get('user')
        if not isinstance(user,dict):raise ValueError('Invalid reviewer identity')
        login=user.get('login')
        if not isinstance(login,str) or not login:raise ValueError('Reviewer login unavailable')
        key=login.casefold()
        authorized=review.get('author_association') in ('OWNER','MEMBER','COLLABORATOR') or key in trusted
        if authorized and user.get('type')=='User' and key!=author.casefold():
            latest[key]=(review.get('state'),review.get('commit_id'))
    if any(state=='CHANGES_REQUESTED' for state,commit in latest.values()) or ('APPROVED',revision) not in latest.values():
        raise ValueError('Current revision lacks independent authorized human review')


def verify_external(repo,revision,artifact,ci_run,native_run,grader_run,pr_number,*,trusted_reviewers=(),
                    policy='strict',local_native=None,native_sessions=(),advisory_reviews=(),source_root=ROOT):
    """Read actual GitHub checks/reviews and cryptographic provenance. No publish.

    Network access is explicit at the CLI. Hash-linked local JSON and a model's
    READY response cannot replace the remote evidence required here.
    """
    if policy not in ('strict','operator-autonomous'):raise ValueError('Unknown release policy; no implicit downgrade')
    trusted_reviewers=sorted(_trusted_logins(trusted_reviewers))
    if policy=='strict' and (local_native is not None or native_sessions or advisory_reviews):
        raise ValueError('Local substitutes require explicit operator-autonomous policy')
    if not isinstance(repo,str) or not isinstance(revision,str) or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo) or not re.fullmatch(r'[0-9a-f]{40}',revision):
        raise ValueError('Invalid repository/revision')
    ids=(ci_run,native_run,grader_run,pr_number) if policy=='strict' else (ci_run,grader_run,pr_number)
    if any(type(value) is not int or value<1 for value in ids):raise ValueError('Positive external evidence IDs required')
    if artifact is None:raise ValueError('Actual built ZIP path required')
    artifact=Path(artifact).resolve()
    if not artifact.is_file() or artifact.suffix!='.zip':raise ValueError('Actual built ZIP required')
    digest=hashlib.sha256(artifact.read_bytes()).hexdigest()
    local_reviews=None
    if policy=='operator-autonomous':
        if native_run is not None or trusted_reviewers:raise ValueError('Autonomous policy does not consume human/remote-native substitutes')
        try:from .guardian_local_acceptance import check_source,expected_roles,verify_local_native,verify_local_reviews,verify_runtime,verify_native_baseline
        except ImportError:from guardian_local_acceptance import check_source,expected_roles,verify_local_native,verify_local_reviews,verify_runtime,verify_native_baseline
        if local_native is None:raise ValueError('Explicit local native evidence directory required')
        check_source(source_root,revision)
        verify_runtime(source_root,local_native)
        verify_native_baseline(source_root,local_native)
        native=verify_local_native(local_native,revision,expected_roles(source_root),native_sessions)
        local_reviews=verify_local_reviews(advisory_reviews,revision,digest)
    workflows=[(ci_run,'.github/workflows/ci.yml',9),
               (grader_run,'.github/workflows/grader-acceptance.yml',1)]
    if policy=='strict':workflows.insert(1,(native_run,'.github/workflows/native-acceptance.yml',1))
    for run_id,path,minimum in workflows:
        run=_api(f'repos/{repo}/actions/runs/{run_id}')
        if run.get('head_sha')!=revision or run.get('status')!='completed' or run.get('conclusion')!='success' or run.get('path','').split('@',1)[0]!=path:
            raise ValueError('External gate has wrong revision, workflow or result')
        jobs=_api(f'repos/{repo}/actions/runs/{run_id}/jobs?per_page=100').get('jobs',[])
        if len(jobs)<minimum or len(jobs)>100 or any(job.get('conclusion')!='success' for job in jobs):
            raise ValueError('Required external jobs missing or failed')
    if policy=='strict':native=_acceptance_artifact(repo,native_run,'native-public-summary','native-public-summary.json',revision)
    grader=_acceptance_artifact(repo,grader_run,'grader-acceptance','grader-acceptance.json',revision)
    verify_acceptance_reports(native,grader,revision)
    pr=_api(f'repos/{repo}/pulls/{pr_number}')
    if pr.get('head',{}).get('sha')!=revision or pr.get('draft') is not False:
        raise ValueError('Release PR revision/draft gate not satisfied')
    author=pr.get('user',{}).get('login')
    if not isinstance(author,str) or not author:raise ValueError('PR author identity unavailable')
    if policy=='strict':
        reviews=[]
        for page in range(1,11):
            batch=_api(f'repos/{repo}/pulls/{pr_number}/reviews?per_page=100&page={page}')
            if not isinstance(batch,list):raise ValueError('Invalid review inventory')
            reviews.extend(batch)
            if len(batch)<100:break
        else:raise ValueError('Review inventory exceeds bounded pagination')
        _verify_human_reviews(reviews,author,revision,trusted_reviewers)
    command=['gh','attestation','verify',str(artifact),'--repo',repo,'--source-digest',revision,
             '--signer-workflow',repo+'/.github/workflows/release.yml','--format','json']
    verified=subprocess.run(command,capture_output=True,text=True,timeout=90)
    if verified.returncode or not json.loads(verified.stdout):raise ValueError('Signed artifact provenance did not verify')
    if hashlib.sha256(artifact.read_bytes()).hexdigest()!=digest:raise ValueError('Artifact changed during verification')
    if policy=='operator-autonomous':check_source(source_root,revision)
    return {'external_checks_passed':True,'revision':revision,'artifact_sha256':digest,'policy':policy,
            'policy_acceptance_passed':True,'human_review_recorded_by_github':policy=='strict',
            'remote_native_test_performed':policy=='strict','local_native_acceptance':native if policy=='operator-autonomous' else None,
            'advisory_reviews':local_reviews,'operator_policy_exclusions':['human_pr_approval','dedicated_remote_native_execution'] if policy=='operator-autonomous' else [],
            'local_evidence_trust':'LOCAL_OPERATOR_OBSERVED_MUTABLE_HOST_RECORDS' if policy=='operator-autonomous' else None,
            'provenance_verified':True,'publication_authorized':False,
            'notice':'Evidence gates passed; publication still requires the operator action authorized for this release. No claim of exhaustive correctness.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-external',action='store_true',help='Explicit read-only network verification; never publishes')
    parser.add_argument('--policy',choices=('strict','operator-autonomous'),default='strict',help='Explicit operator release profile; strict remains the default')
    parser.add_argument('--local-native',type=Path,help='Existing complete local native harness evidence directory')
    parser.add_argument('--native-session',type=Path,action='append',default=[],help='Explicit raw child session record; repeat exactly 39 times')
    parser.add_argument('--advisory-review',type=Path,action='append',default=[],help='Pinned G01 or G02 AI advisory review; repeat twice')
    parser.add_argument('--source-root',type=Path,default=ROOT,help='Clean source checkout pinned to the requested revision')
    parser.add_argument('--trusted-reviewer',action='append',default=[],metavar='LOGIN',
                        help='Explicit trusted human GitHub reviewer; repeatable, grants no repository access')
    parser.add_argument('--repo');parser.add_argument('--revision');parser.add_argument('--artifact',type=Path)
    for name in ('ci-run','native-run','grader-run','pr-number'):parser.add_argument('--'+name,type=int)
    args=parser.parse_args()
    try:
        if args.verify_external:
            result=verify_external(args.repo,args.revision,args.artifact,args.ci_run,args.native_run,args.grader_run,args.pr_number,trusted_reviewers=args.trusted_reviewer,
                                   policy=args.policy,local_native=args.local_native,native_sessions=args.native_session,
                                   advisory_reviews=args.advisory_review,source_root=args.source_root)
        else:result=inspect()
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        parser.exit(2,'Guardian release gate rejected: '+str(exc)+'\n')
    print(json.dumps(result,indent=2))
