"""Exercise the actual ZIP's account/project lifecycle in disposable roots."""
import argparse,json,os,subprocess,sys,tempfile,zipfile
from pathlib import Path
try:from .build_release import build
except ImportError:from build_release import build
ROOT=Path(__file__).resolve().parents[1]

def verify(root=ROOT, temp_dir=None):
    root=Path(root)
    if not (root/'plugin.json').is_file():raise ValueError('Distribution verification needs source package metadata')
    reports=[]
    if temp_dir is not None:
        temp_dir=Path(temp_dir).resolve();temp_dir.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='gd-',dir=temp_dir) as folder:
        temp=Path(folder).resolve();result=build(temp/'dist',root)
        extracted=temp/'x'
        if os.name=='nt' and len(str(extracted))+150>255:
            raise ValueError('Windows temporary path is too long for package paths. Pass --temp-dir with a shorter writable workspace directory; no OS settings were changed.')
        with zipfile.ZipFile(result['archive']) as archive:
            for name in archive.namelist():
                target=(extracted/name).resolve()
                if not target.is_relative_to(extracted.resolve()):raise ValueError('Archive traversal')
            archive.extractall(extracted)
        source=extracted/('fullstack-guardian-'+result['version'])
        for mode in ('user','project'):
            destination=temp/mode;destination.mkdir();codex=destination/'.codex';codex.mkdir()
            original=b'model = "PRESERVED_USER_MODEL"\n[agents]\nenabled = true\nmax_threads = 2\n'
            policy=codex/'AGENTS.md' if mode=='user' else destination/'AGENTS.md'
            policy.write_bytes(b'# Preserved user instructions\n')
            (codex/'config.toml').write_bytes(original)
            (codex/'agents').mkdir();(codex/'agents/user_owned.toml').write_text('name = "user-owned"\n')
            args=['--user','--home',str(destination)] if mode=='user' else ['--project',str(destination)]
            commands=[[],['--apply'],['--doctor'],['--update'],['--update','--apply'],['--doctor'],['--rollback'],['--rollback','--apply'],['--doctor'],['--uninstall','--apply']]
            for operation in commands:
                p=subprocess.run([sys.executable,'-B',str(source/'install.py'),*args,*operation],capture_output=True,text=True,timeout=180)
                if p.returncode:raise ValueError(mode+' lifecycle failed: '+p.stderr)
                report=json.loads(p.stdout)
                if operation==['--doctor'] and report.get('warnings'):raise ValueError('Unexpected doctor warnings')
            assert (codex/'config.toml').read_bytes()==original
            assert policy.read_bytes()==b'# Preserved user instructions\n'
            assert (codex/'agents/user_owned.toml').read_text()=='name = "user-owned"\n'
            reports.append({'mode':mode,'commands':len(commands),'configuration_preserved':True,'unowned_profile_preserved':True})
    return {'ok':True,'version':result['version'],'archive_sha256':result['sha256'],'scopes':reports,
            'native_models_executed':False,'global_user_configuration_changed':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--temp-dir',type=Path);args=parser.parse_args()
    print(json.dumps(verify(temp_dir=args.temp_dir),indent=2))
