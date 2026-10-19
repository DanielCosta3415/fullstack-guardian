"""Prepare artifacts while refusing a mislabeled stable release.

This local gate authenticates no human and never publishes. Stable promotion
requires actual external evidence and provenance verification, not model claims.
"""
import argparse,hashlib,json,re,subprocess
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


def verify_external(repo,revision,artifact,ci_run,native_run,grader_run,pr_number):
    """Read actual GitHub checks/reviews and cryptographic provenance. No publish.

    Network access is explicit at the CLI. Hash-linked local JSON and a model's
    READY response cannot replace the remote evidence required here.
    """
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo) or not re.fullmatch(r'[0-9a-f]{40}',revision):
        raise ValueError('Invalid repository/revision')
    ids=(ci_run,native_run,grader_run,pr_number)
    if any(type(value) is not int or value<1 for value in ids):raise ValueError('Positive external evidence IDs required')
    artifact=Path(artifact).resolve()
    if not artifact.is_file() or artifact.suffix!='.zip':raise ValueError('Actual built ZIP required')
    workflows=((ci_run,'.github/workflows/ci.yml',9),
               (native_run,'.github/workflows/native-acceptance.yml',1),
               (grader_run,'.github/workflows/grader-acceptance.yml',1))
    for run_id,path,minimum in workflows:
        run=_api(f'repos/{repo}/actions/runs/{run_id}')
        if run.get('head_sha')!=revision or run.get('status')!='completed' or run.get('conclusion')!='success' or run.get('path','').split('@',1)[0]!=path:
            raise ValueError('External gate has wrong revision, workflow or result')
        jobs=_api(f'repos/{repo}/actions/runs/{run_id}/jobs?per_page=100').get('jobs',[])
        if len(jobs)<minimum or len(jobs)>100 or any(job.get('conclusion')!='success' for job in jobs):
            raise ValueError('Required external jobs missing or failed')
    pr=_api(f'repos/{repo}/pulls/{pr_number}')
    if pr.get('head',{}).get('sha')!=revision or pr.get('draft') is not False:
        raise ValueError('Release PR revision/draft gate not satisfied')
    author=pr.get('user',{}).get('login')
    if not isinstance(author,str) or not author:raise ValueError('PR author identity unavailable')
    reviews=[]
    for page in range(1,11):
        batch=_api(f'repos/{repo}/pulls/{pr_number}/reviews?per_page=100&page={page}')
        if not isinstance(batch,list):raise ValueError('Invalid review inventory')
        reviews.extend(batch)
        if len(batch)<100:break
    else:raise ValueError('Review inventory exceeds bounded pagination')
    latest={}
    for review in reviews:
        if review.get('state') not in ('APPROVED','CHANGES_REQUESTED','DISMISSED'):continue
        if review.get('author_association') in ('OWNER','MEMBER','COLLABORATOR') and review.get('user',{}).get('type')=='User' and review['user'].get('login')!=author:
            latest[review['user']['login']]=(review.get('state'),review.get('commit_id'))
    if any(state=='CHANGES_REQUESTED' for state,commit in latest.values()) or ('APPROVED',revision) not in latest.values():
        raise ValueError('Current revision lacks independent authorized human review')
    command=['gh','attestation','verify',str(artifact),'--repo',repo,'--source-digest',revision,
             '--signer-workflow',repo+'/.github/workflows/release.yml','--format','json']
    verified=subprocess.run(command,capture_output=True,text=True,timeout=90)
    if verified.returncode or not json.loads(verified.stdout):raise ValueError('Signed artifact provenance did not verify')
    return {'external_checks_passed':True,'revision':revision,'artifact_sha256':hashlib.sha256(artifact.read_bytes()).hexdigest(),
            'human_review_recorded_by_github':True,'provenance_verified':True,'publication_authorized':False,
            'notice':'Evidence gates passed; publication still requires the operator action authorized for this release. No claim of exhaustive correctness.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-external',action='store_true',help='Explicit read-only network verification; never publishes')
    parser.add_argument('--repo');parser.add_argument('--revision');parser.add_argument('--artifact',type=Path)
    for name in ('ci-run','native-run','grader-run','pr-number'):parser.add_argument('--'+name,type=int)
    args=parser.parse_args()
    if args.verify_external:
        result=verify_external(args.repo,args.revision,args.artifact,args.ci_run,args.native_run,args.grader_run,args.pr_number)
    else:result=inspect()
    print(json.dumps(result,indent=2))
