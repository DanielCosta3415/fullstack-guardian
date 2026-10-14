#!/usr/bin/env python3
"""Build a deterministic self-contained release; stdlib only, no user files."""
import argparse
import hashlib
import json
import os
import stat
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = {'global', 'core', 'tools', 'tests', 'docs', 'project-template', 'skills', '.agents', '.codex-plugin', 'assets', 'installer', '.github'}
FILES = {'README.md', 'RELEASE_NOTES.md', 'LICENSE', 'VERSION', 'install.py', 'install.sh', 'plugin.json', '.gitignore', '.gitattributes', 'SECURITY.md'}
EXCLUDED = {'__pycache__', '.git', 'dist', '.pytest_cache'}

def source_files(root=ROOT):
    result = []
    for base, dirs, files in os.walk(root, followlinks=False):
        current = Path(base)
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED and (current != root or d in DIRECTORIES))
        for name in dirs + files:
            p = current / name
            s = p.lstat()
            if stat.S_ISLNK(s.st_mode) or getattr(s, 'st_file_attributes', 0) & 0x400:
                raise ValueError('Source symlink/reparse point rejected: ' + str(p))
        for name in sorted(files):
            p = current / name
            if current == root and name not in FILES:
                continue
            if p.suffix in ('.pyc', '.pyo'):
                continue
            result.append(p)
    return sorted(result, key=lambda p: p.relative_to(root).as_posix())

def build(destination, root=ROOT):
    version = (root / 'VERSION').read_text(encoding='utf8').strip()
    import re
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Invalid stable VERSION')
    files = source_files(root)
    paths = {p.relative_to(root).as_posix() for p in files}
    for required in ('install.py', 'plugin.json', 'skills/setup/SKILL.md', '.agents/plugins/marketplace.json'):
        if required not in paths:raise ValueError('Incomplete release: ' + required)
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / f'fullstack-guardian-{version}.zip'
    manifest = {'version':version,'algorithm':'SHA-256','files':[{'path':p.relative_to(root).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in files]}
    manifest_bytes = (json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf8')
    prefix = f'fullstack-guardian-{version}/'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files:
            info = zipfile.ZipInfo(prefix+p.relative_to(root).as_posix(),(2026,1,1,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100755 if p.name=='install.sh' else 0o100644) << 16
            z.writestr(info,p.read_bytes())
        info=zipfile.ZipInfo(prefix+'MANIFEST.sha256.json',(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
        z.writestr(info,manifest_bytes)
    (destination/'MANIFEST.sha256.json').write_bytes(manifest_bytes)
    hashes=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in (archive,destination/'MANIFEST.sha256.json'))
    (destination/'SHA256SUMS.txt').write_text(hashes,encoding='ascii',newline='\n')
    return {'version':version,'files':len(files),'archive':str(archive),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=ROOT/'dist');args=parser.parse_args()
    print(json.dumps(build(args.out),indent=2))
if __name__=='__main__':main()
