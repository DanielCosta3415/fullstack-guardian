"""Export only bounded native acceptance counters; never session IDs or raw logs."""
import argparse,json
from pathlib import Path

def public_summary(source,required_count=None):
    data=json.loads(Path(source).read_text(encoding='utf8'))
    if any(type(data.get(k)) is not int or data[k]<0 for k in ('expected','verified')):
        raise ValueError('Invalid native acceptance counters')
    if data['expected']==0 or data['verified']>data['expected']:raise ValueError('Invalid verified counter')
    if required_count is not None and (type(required_count) is not int or required_count<1 or data['expected']!=required_count):raise ValueError('Required profile inventory mismatch')
    return {'schema_version':1,'expected':data['expected'],'verified':data['verified'],
            'all_native_roles_verified':type(data.get('exit_code')) is int and data['exit_code']==0 and data['expected']==data['verified'] and data.get('protected_fixtures_unchanged') is True,
            'protected_fixtures_unchanged':data.get('protected_fixtures_unchanged') is True,
            'acceptance_scope':'Native role execution in synthetic cases; not exhaustive taxonomy or production certification'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--out',type=Path);p.add_argument('--require-count',type=int);a=p.parse_args()
    data=public_summary(a.source,a.require_count)
    result=json.dumps(data,indent=2)
    if a.out:a.out.write_text(result+'\n',encoding='utf8')
    else:print(result)
    raise SystemExit(0 if data['all_native_roles_verified'] else 1)
