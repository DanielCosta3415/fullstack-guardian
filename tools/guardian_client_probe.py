"""Quota-free synthetic Windows CLI observations; never a general sandbox proof.

The named profile exists only in command-line TOML overrides documented by
OpenAI. No opaque sandbox state, model invocation or bypass flags are used.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys

try:
    from .guardian_capabilities import capability_report, probe_version
except ImportError:
    from guardian_capabilities import capability_report, probe_version

PROFILE_NAME = 'guardian-synthetic-probe'
PROFILE_REFERENCE = 'https://learn.chatgpt.com/docs/permissions'
SCHEMA_REFERENCE = 'https://learn.chatgpt.com/docs/config-schema.json'
OBSERVATIONS = {'workspace_write', 'outside_write', 'outside_read', 'loopback_connect'}
PROBE = r'''import json,socket,sys
from pathlib import Path
outside=Path(sys.argv[1]);port=int(sys.argv[2]);r={}
for name,fn in [('workspace_write',lambda:Path('allowed.txt').write_text('synthetic')),('outside_write',lambda:(outside/'forbidden.txt').write_text('synthetic')),('outside_read',lambda:(outside/'canary.txt').read_text())]:
 try:fn();r[name]='allowed'
 except OSError:r[name]='denied'
try:
 with socket.create_connection(('127.0.0.1',port),timeout=2):r['loopback_connect']='allowed'
except OSError:r['loopback_connect']='denied'
print(json.dumps(r))
'''


def profile_override(outside, python_root=None):
    """Exact runtime and synthetic paths, no inherited broad filesystem grant."""
    runtime = Path(python_root or sys.base_prefix).resolve()
    outside = Path(outside).resolve()
    if outside == runtime or runtime in outside.parents:
        raise ValueError('Synthetic outside directory must not be inside the Python runtime')
    quote = lambda value: json.dumps(str(value), ensure_ascii=True)
    filesystem = '{":root"="deny",":minimal"="read",":workspace_roots"={"."="write"},' + quote(runtime) + '="read",' + quote(outside) + '="deny"}'
    return 'permissions.' + PROFILE_NAME + '={extends=":workspace",filesystem=' + filesystem + ',network={enabled=false}}'


def sandbox_command(codex, workspace, outside, port):
    return [str(codex), 'sandbox', '--include-managed-config', '-P', PROFILE_NAME,
            '-c', profile_override(outside), '-C', str(workspace),
            sys.executable, '-B', str(workspace / 'probe.py'), str(outside), str(port)]


def parse_observations(raw):
    try:
        observed = json.loads(raw.strip())
    except (ValueError, TypeError):
        return None
    if not isinstance(observed, dict) or set(observed) != OBSERVATIONS or any(value not in ('allowed', 'denied') for value in observed.values()):
        return None
    return observed


def diagnostic(stderr):
    text = stderr.lower()
    if 'requires the elevated windows sandbox backend' in text:
        return 'Restricted filesystem reads are unsupported by the active Windows sandbox backend; elevated backend provisioning was not attempted'
    if 'permission profile' in text or 'permission-profile' in text or 'unknown field' in text:
        return 'Named synthetic permission profile unsupported or rejected by this CLI/configuration'
    if 'createdesktop' in text or 'access is denied' in text or 'acesso negado' in text:
        return 'Windows sandbox startup denied by the execution environment; no unsafe fallback'
    return 'Sandbox command did not produce a valid bounded observation; inspect private diagnostics locally'


def run(out, codex=None):
    if platform.system() != 'Windows':
        raise ValueError('This reviewed probe targets the Windows CLI only')
    out = Path(out).absolute()
    if any(path.is_symlink() or (path.exists() and getattr(path.lstat(), 'st_file_attributes', 0) & 0x400) for path in (out, *out.parents)):
        raise ValueError('Probe directory links are not allowed')
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ValueError('New empty probe directory required')
    out.mkdir(parents=True, exist_ok=True)
    out = out.resolve()
    workspace, outside, private = out / 'workspace', out / 'outside', out / 'private'
    for folder in (workspace, outside, private):
        folder.mkdir()
    (outside / 'canary.txt').write_text('synthetic-canary', encoding='utf8')
    (workspace / 'probe.py').write_text(PROBE, encoding='utf8')
    codex = codex or shutil.which('codex')
    if not codex:
        raise ValueError('Codex CLI unavailable')
    report = capability_report(probe_version(codex))
    accepted = False
    try:
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen(2)
            listener.settimeout(0.1)
            command = sandbox_command(codex, workspace, outside, listener.getsockname()[1])
            (private / 'command.json').write_text(json.dumps(command, indent=2), encoding='utf8')
            completed = subprocess.run(command, cwd=workspace, capture_output=True, text=True, timeout=45, check=False)
            try:
                connection, _ = listener.accept()
                connection.close()
                accepted = True
            except socket.timeout:
                pass
        stderr, stdout, exit_code = completed.stderr, completed.stdout, completed.returncode
    except (OSError, subprocess.TimeoutExpired) as error:
        stderr, stdout, exit_code = type(error).__name__, '', None
    # Private diagnostics can contain local paths; public report never echoes them.
    (private / 'stderr.txt').write_text(stderr, encoding='utf8')
    (private / 'stdout.txt').write_text(stdout, encoding='utf8')
    observed = parse_observations(stdout) if exit_code == 0 and len(stdout) <= 4096 else None
    report.update(probe_scope='Synthetic point observations only; no general filesystem/network/tool-isolation attestation',
                  quota_consumed=False, probe_completed=observed is not None, observations=observed, exit_code=exit_code,
                  profile_scope='Ephemeral CLI override; global configuration unchanged',
                  profile_reference=PROFILE_REFERENCE, schema_reference=SCHEMA_REFERENCE,
                  probe_source_sha256=hashlib.sha256(PROBE.encode()).hexdigest(),
                  profile_sha256=hashlib.sha256(profile_override(outside).encode()).hexdigest(),
                  actual_outside_file_created=(outside / 'forbidden.txt').exists(),
                  actual_workspace_file_created=(workspace / 'allowed.txt').exists(),
                  actual_loopback_accepted=accepted,
                  stderr_sha256=hashlib.sha256(stderr.encode()).hexdigest(),
                  diagnostic=None if observed else diagnostic(stderr))
    report['probe_status'] = 'OBSERVED' if observed else 'UNSUPPORTED' if 'requires the elevated windows sandbox backend' in stderr.lower() else 'BLOCKED'
    if report['probe_status'] == 'UNSUPPORTED':
        report['capabilities']['filesystem_isolation'] = {'status': 'unsupported', 'evidence': 'Native CLI rejected restricted reads with the active Windows sandbox backend; synthetic child did not execute'}
    if observed and (observed['outside_read'] == 'allowed' or observed['outside_write'] == 'allowed'):
        report['capabilities']['filesystem_isolation'] = {'status': 'unsupported', 'evidence': 'Explicit synthetic outside deny was not enforced in this point probe'}
    # Point denials never promote an entire restriction capability to verified.
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = run(args.out)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['probe_completed'] else 2)
