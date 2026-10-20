"""Version-aware client capability evidence. No version implies a security proof."""
from __future__ import annotations
import argparse, json, platform, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
FEATURES=('spawn','native_logs','filesystem_isolation','network_isolation','tool_restrictions','skill_restrictions','model_override','effort_override')

def capability_report(version=None,client='cli',os_name=None,observations=None):
    os_name=os_name or platform.system()
    observations=observations or {}
    if set(observations)-set(FEATURES): raise ValueError('Unknown capability observation')
    manifest=json.loads((ROOT/'core'/'codex-compatibility-v1.json').read_text(encoding='utf-8'))
    match=next((p for p in manifest['profiles'] if p['version']==version and p['client']==client and p['os']==os_name),None)
    capabilities={key:{'status':'unknown','evidence':None} for key in FEATURES}
    for key,value in observations.items():
        if not isinstance(value,dict) or set(value)!={'status','evidence'} or value['status'] not in ('verified','unsupported','unknown'):
            raise ValueError('Invalid capability evidence')
        if value['status']!='unknown' and (not isinstance(value['evidence'],str) or not value['evidence'].strip()):
            raise ValueError('Nonunknown capability requires probe evidence')
        capabilities[key]=dict(value)
    return {'schema_version':1,'client':client,'version':version,'os':os_name,'compatibility':'known' if match else 'unknown',
            'capabilities':capabilities,'policy':'inherit_parent','sandbox_verified':False,
            'notice':'Evidence input is a supervisor observation, not authenticated by this static reporter. Unknown restriction requirements block restricted operations.'}

def probe_version(executable='codex'):
    # Only a non-mutating version probe. Never launch a model or access credentials.
    try:
        p=subprocess.run([executable,'--version'],capture_output=True,text=True,timeout=10,check=False)
    except (OSError,subprocess.TimeoutExpired): return None
    match=re.fullmatch(r'codex(?:-cli)?\s+(\S+)\s*',p.stdout)
    return match.group(1) if p.returncode==0 and match else None

def require_capabilities(report,required):
    unknown=[key for key in required if report.get('capabilities',{}).get(key,{}).get('status')!='verified']
    return {'allowed':not unknown,'blocked_capabilities':unknown}

def model_policy(override=None, *, authorized=False,available_models=None,available_efforts=None):
    if override is None:return {'mode':'inherit','model':None,'effort':None}
    if not authorized or not isinstance(override,dict) or set(override)-{'model','effort'} or not override:
        raise ValueError('Model override requires explicit supervisor opt-in')
    if 'model' in override and override['model'] not in (available_models or []):
        raise ValueError('Model availability not verified; no silent fallback')
    if 'effort' in override and override['effort'] not in (available_efforts or []):
        raise ValueError('Reasoning effort not supported by verified client/model')
    return {'mode':'explicit_override','model':override.get('model'),'effort':override.get('effort')}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--version');p.add_argument('--probe',action='store_true');a=p.parse_args()
    print(json.dumps(capability_report(probe_version() if a.probe else a.version),indent=2))
if __name__=='__main__':main()
