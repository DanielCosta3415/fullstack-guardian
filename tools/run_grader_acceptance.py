"""A required real grader gate refuses skips and reports exact source identity."""
import argparse,hashlib,json,subprocess,unittest
from pathlib import Path
from guardian_grader_sandbox import probe

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    backend=probe()
    if not backend['available']:raise SystemExit('Verified rootless backend required; skips cannot satisfy acceptance')
    suite=unittest.TestSuite()
    for name in ('test_guardian_grader_sandbox.py','test_guardian_benchmark_fixture.py'):
        suite.addTests(unittest.defaultTestLoader.discover('tests',pattern=name))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={'schema_version':1,'revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            'image':backend['image'],'tests':result.testsRun,'skipped':len(result.skipped),
            'failures':len(result.failures),'errors':len(result.errors),
            'passed':result.wasSuccessful() and not result.skipped and result.testsRun>=14,
            'grader_sha256':hashlib.sha256(Path('tools/guardian_grader_sandbox.py').read_bytes()).hexdigest()}
    args.out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
