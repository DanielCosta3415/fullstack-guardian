#!/usr/bin/env python3
"""Run stdlib tests with a workspace-owned temporary root (also works in Codex sandboxes)."""
import argparse, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--temp-dir',type=Path,default=Path.cwd()/'work/guardian-test-temp')
    args=parser.parse_args()
    temp=args.temp_dir.expanduser().resolve();temp.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy();env['TEMP']=env['TMP']=str(temp);env['PYTHONUTF8']='1'
    return subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(ROOT/'tests'),'-v'],env=env).returncode
if __name__=='__main__':sys.exit(main())
