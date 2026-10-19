"""Generate human catalog from reviewed canonical metadata; --check never writes."""
import argparse,json
from pathlib import Path
try:from .guardian_catalog import validate_catalog
except ImportError:from guardian_catalog import validate_catalog
ROOT=Path(__file__).resolve().parents[1]

def render(root=ROOT):
    root=Path(root);validate_catalog(root)
    doc=json.loads((root/'core/contracts-catalog-v1.json').read_text(encoding='utf8'))
    skills=sorted(p.parent.name for p in (root/'global/skills').glob('*/SKILL.md'))
    version=(root/'VERSION').read_text().strip()
    lines=['# Generated catalog', '', 'Version: '+version, '', 'Availability is not installation, native loading, or correctness. Model policy inherits by default.', '', 'Reviewed source of truth: `core/contracts-catalog-v1.json` contains typed instructions and metadata. `python -B tools/guardian_catalog.py --write` generates the 39 TOMLs, core metadata and pack manifests; it never imports profile edits or writes user configuration. Review canonical changes and expected SHA-256 values before generation.', '', '| ID | Role | Kind | Reviewer | Profile SHA-256 |','|---|---|---|---|---|']
    for record in doc['records']:
        lines.append('| '+ ' | '.join(str(record[k]) for k in ('id','name','kind','reviewer','sha256'))+' |')
    lines += ['', '## Operational skills ('+str(len(skills))+')','']+['- `'+name+'`' for name in skills]
    return '\n'.join(lines)+'\n'

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();target=ROOT/'docs/CATALOG.md';data=render()
    if a.check:
        if not target.exists() or target.read_text(encoding='utf8')!=data:raise SystemExit('Generated catalog documentation drift')
    else:target.write_text(data,encoding='utf8',newline='\n')
