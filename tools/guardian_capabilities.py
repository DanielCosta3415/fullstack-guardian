"""Version-aware client capability evidence. No version implies a security proof."""
from __future__ import annotations
import argparse, hashlib, json, math, platform, re, subprocess, time
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


def runtime_context(*, client, version, os_name, profiles, tools, configuration_sha256):
    """Bind observations to the ACTUAL caller inventory, never installed intent.

    profiles maps stable native role names to observed profile digests. tools is
    the currently exposed tool-ID list, not a list promised in instructions.
    A caller declaration remains unauthenticated; this helper cannot interrogate
    another Codex thread or prove permissions by reading its TOML files.
    """
    for value in (client, version, os_name):
        if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.+-]{1,128}', value):
            raise ValueError('Bounded client/version/OS required')
    if not isinstance(profiles, dict) or not profiles or len(profiles) > 256:
        raise ValueError('Observed role inventory required')
    for name, sha in profiles.items():
        if not isinstance(name, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,127}', name) or not isinstance(sha, str) or not re.fullmatch('[a-f0-9]{64}', sha):
            raise ValueError('Invalid role/profile digest')
    if not isinstance(tools, list) or len(tools) > 2048 or len(set(tools)) != len(tools) or any(not isinstance(t, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{0,255}', t) for t in tools):
        raise ValueError('Unique observed tool IDs required')
    if not isinstance(configuration_sha256, str) or not re.fullmatch('[a-f0-9]{64}', configuration_sha256):
        raise ValueError('Effective configuration digest required')
    value = {'client': client, 'version': version, 'os': os_name,
             'profiles': dict(sorted(profiles.items())), 'tools': sorted(tools),
             'configuration_sha256': configuration_sha256}
    value['sha256'] = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return value


def _validate_context(context):
    if not isinstance(context, dict) or set(context) != {'client', 'version', 'os', 'profiles', 'tools', 'configuration_sha256', 'sha256'}:
        raise ValueError('Closed observed runtime context required')
    expected = runtime_context(client=context['client'], version=context['version'], os_name=context['os'],
                               profiles=context['profiles'], tools=context['tools'], configuration_sha256=context['configuration_sha256'])
    if expected != context:
        raise ValueError('Runtime context digest drift')


def bind_observation(context, observations, *, observed_at=None, ttl_seconds=3600):
    """Short-lived supervisor observation; flags are NOT OS isolation proof."""
    _validate_context(context)
    if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= 86400:
        raise ValueError('Capability observation lifetime must be 1..86400 seconds')
    timestamp = time.time() if observed_at is None else observed_at
    if type(timestamp) not in (int, float) or not math.isfinite(timestamp) or timestamp < 0:
        raise ValueError('Finite observation time required')
    report = capability_report(context['version'], client=context['client'], os_name=context['os'], observations=observations)
    return {'schema_version': 2, 'context': context, 'observed_at': timestamp,
            'expires_at': timestamp + ttl_seconds, 'report': report,
            'authenticated': False, 'native_execution_verified': False}


def require_runtime_dependencies(observation, current_context, *, roles=(), tools=(), features=(), now=None):
    """Unknown/expired/missing dependencies block only their dependent action."""
    _validate_context(current_context)
    if not isinstance(observation, dict) or set(observation) != {'schema_version', 'context', 'observed_at', 'expires_at', 'report', 'authenticated', 'native_execution_verified'} or type(observation['schema_version']) is not int or observation['schema_version'] != 2 or observation['authenticated'] is not False or observation['native_execution_verified'] is not False:
        raise ValueError('Closed bound observation required')
    _validate_context(observation['context'])
    start, end = observation['observed_at'], observation['expires_at']
    clock = time.time() if now is None else now
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in (start, end, clock)) or not 0 < end - start <= 86400:
        raise ValueError('Invalid observation lifetime')
    for values in (roles, tools, features):
        if not isinstance(values, (tuple, list)) or any(not isinstance(v, str) or not v for v in values):
            raise ValueError('Invalid dependency IDs')
    report = observation['report']
    original = observation['context']
    if not isinstance(report, dict) or any(report.get(k) != original[k] for k in ('client', 'version', 'os')):
        raise ValueError('Report does not match observed runtime')
    # Revalidate evidence fields; a JSON edit cannot turn a string into a bool.
    checked = capability_report(original['version'], client=original['client'], os_name=original['os'], observations=report.get('capabilities'))
    if report != checked:
        raise ValueError('Capability report field drift')
    blocked = []
    if original != current_context:
        blocked.append('runtime_context_changed')
    if not start <= clock < end:
        blocked.append('observation_expired_or_future')
    blocked += ['role:' + role for role in roles if role not in current_context['profiles']]
    blocked += ['tool:' + tool for tool in tools if tool not in current_context['tools']]
    blocked += ['feature:' + f for f in features if checked['capabilities'].get(f, {}).get('status') != 'verified']
    return {'allowed': not blocked, 'blocked_dependencies': sorted(set(blocked)),
            'context_sha256': current_context['sha256'], 'authenticated': False,
            'sandbox_verified': False, 'model_policy': 'inherit'}

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
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version');p.add_argument('--probe',action='store_true')
    p.add_argument('--context',type=Path,help='Current independently observed client/profile/tool context')
    p.add_argument('--observations',type=Path,help='Feature evidence to bind, or bound observation to check')
    p.add_argument('--check-bound',action='store_true')
    p.add_argument('--require-role',action='append',default=[])
    p.add_argument('--require-tool',action='append',default=[])
    p.add_argument('--require-feature',action='append',default=[])
    a=p.parse_args()
    try:
        if a.context or a.observations or a.check_bound:
            if not a.context or not a.observations:
                raise ValueError('Both context and observations are required')
            try:
                from .guardian_checkpoint import read_json
            except ImportError:
                from guardian_checkpoint import read_json
            context, observed = read_json(a.context), read_json(a.observations)
            if a.check_bound:
                result = require_runtime_dependencies(observed, context, roles=a.require_role, tools=a.require_tool, features=a.require_feature)
            else:
                if a.require_role or a.require_tool or a.require_feature:
                    raise ValueError('Requirements apply to --check-bound only')
                result = bind_observation(context, observed)
        else:
            if a.require_role or a.require_tool or a.require_feature:
                raise ValueError('Requirements need --check-bound and context')
            result = capability_report(probe_version() if a.probe else a.version)
        print(json.dumps(result,indent=2))
        return 0 if result.get('allowed',True) else 2
    except (ValueError,OSError,TypeError,KeyError) as exc:
        print(json.dumps({'error':str(exc)}))
        return 2
if __name__=='__main__':raise SystemExit(main())
