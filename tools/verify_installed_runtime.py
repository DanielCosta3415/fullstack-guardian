"""Functional acceptance of an extracted package or installed runtime, without native model calls."""
from __future__ import annotations
import argparse, json, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def verify(root=ROOT, temp_dir=None, suite=False):
    root=Path(root).resolve()
    required=('tools/guardian.py','core/contracts-catalog-v1.json','global/agents','tests')
    if any(not (root/name).exists() for name in required):raise ValueError('Incomplete Guardian runtime')
    temp=Path(temp_dir).resolve() if temp_dir else root/'work/acceptance-temp'
    temp.mkdir(parents=True,exist_ok=True)
    if os.name=='nt' and len(str(temp))>160:raise ValueError('Use a shorter writable --temp-dir on Windows')
    env=os.environ.copy();env.update(TEMP=str(temp),TMP=str(temp),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(root))
    commands=[['tools/guardian.py','validate'],['tools/guardian.py','eval'],['tools/guardian_catalog.py'],['tools/generate_catalog_docs.py','--check'],['tools/guardian_domain_checks.py','--self-test']]
    checks=[]
    for args in commands:
        completed=subprocess.run([sys.executable,'-B',*args],cwd=root,env=env,capture_output=True,text=True,timeout=180)
        if completed.returncode:raise ValueError('Runtime check failed '+args[0]+': '+completed.stderr[-4000:])
        checks.append({'command':args,'exit_code':0})
    tests=None
    if suite:
        # No custom filtering: existing individual tests explicitly identify source-only metadata.
        completed=subprocess.run([sys.executable,'-B','tools/verify_installed_runtime.py','--internal-suite'],cwd=root,env=env,capture_output=True,text=True,timeout=2400)
        if completed.returncode:raise ValueError('Runtime unittest suite failed: '+completed.stdout[-12000:]+completed.stderr[-4000:])
        tests=json.loads(completed.stdout)
    return {'ok':True,'layout':'source_or_zip' if (root/'plugin.json').exists() else 'installed_runtime', 'checks':checks,'unit_tests':tests,'native_models_executed':False,'source_only_policy':'individual unittest skips; no broad filtering'}


def internal_suite():
    import unittest
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    result=unittest.TestResult();suite.run(result)
    report={'run':result.testsRun,'passed':result.testsRun-len(result.skipped)-len(result.failures)-len(result.errors),'skipped':[{'test':test.id(),'reason':reason} for test,reason in result.skipped],'failures':[{'test':test.id(),'detail':detail} for test,detail in result.failures+result.errors]}
    print(json.dumps(report));return 0 if result.wasSuccessful() else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--temp-dir',type=Path);parser.add_argument('--suite',action='store_true');parser.add_argument('--internal-suite',action='store_true',help=argparse.SUPPRESS);args=parser.parse_args()
    if args.internal_suite:raise SystemExit(internal_suite())
    print(json.dumps(verify(args.root,args.temp_dir,args.suite),indent=2))
