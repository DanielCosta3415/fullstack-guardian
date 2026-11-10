"""Explicit native checks of fixed reviewed fixtures; never a candidate-code runner.

Default CLI is a non-executing preview. --run writes only a new dedicated output
directory and launches fixed argv, without shell, npm/NuGet downloads, profiles
or model calls. This is not OS network isolation or professional certification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

try:
    from .guardian_runtime import terminate_tree
except ImportError:
    from guardian_runtime import terminate_tree

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'eval/stack-fixtures'
CASES = {
    'node': {'baseline': [], 'absent-null': ['absence_null_distinct'],
             'enum-strict': ['strict_enum_rejects_unknown'],
             'form-loss': ['navigation_preserves_input'],
             'form-navigation': ['invalid_form_blocks_navigation']},
    'dotnet': {'baseline': [], 'di-transitive-unchecked': ['transitive_scoped_capture_rejected'],
               'factory-capture': ['factory_owns_distinct_disposed_scopes'],
               'cancel-before': ['cancellation_before_commit_has_no_effect'],
               'cancel-after': ['cancellation_after_commit_preserves_acknowledgment']},
    'powershell': {'baseline': [], 'whatif-bypass': ['whatif_no_mutation'],
                   'wildcard-path': ['literal_path_preserves_brackets'],
                   'parent-reparse-unchecked': ['parent_reparse_component_rejected'],
                   'cancellation-ignored': ['cancelled_write_has_no_effect']},
}
CHECKS = {
    'node': {'absence_null_distinct', 'strict_enum_rejects_unknown', 'tolerant_enum_preserves_unknown',
             'invalid_form_blocks_navigation', 'navigation_preserves_input'},
    'dotnet': {'transitive_scoped_capture_rejected', 'factory_owns_distinct_disposed_scopes',
               'cancellation_before_commit_has_no_effect', 'cancellation_after_commit_preserves_acknowledgment'},
    'powershell': {'whatif_no_mutation', 'literal_path_preserves_brackets',
                  'cancelled_write_has_no_effect', 'parent_reparse_component_rejected'},
}
FILES = {'node': ['check.cjs'], 'dotnet': ['GuardianStack.csproj', 'Program.cs', 'NuGet.Config'],
         'powershell': ['Check-Stack.ps1']}
LIMIT = 65536


def plain(path):
    path = Path(path).absolute()
    for item in (path, *path.parents):
        if item.is_symlink() or (item.exists() and getattr(item.lstat(), 'st_file_attributes', 0) & 0x400):
            raise ValueError('Fixture/output links are not allowed')
    return path


def fixture_bytes(stack, name):
    if stack not in FILES or name not in FILES[stack]:
        raise ValueError('Only fixed reviewed fixtures may execute')
    path = plain(FIXTURES / stack / name)
    if not path.is_file() or path.stat().st_size > LIMIT:
        raise ValueError('Missing/oversized trusted fixture')
    with path.open('rb') as file:
        data = file.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ValueError('Fixture exceeds bound')
    return data


def process(argv, folder, env, timeout=30):
    if not isinstance(argv, list) or not argv or any(not isinstance(x, str) for x in argv):
        raise ValueError('argv list required')
    proc = subprocess.Popen(argv, cwd=folder, env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            start_new_session=os.name != 'nt',
                            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        terminate_tree(proc)
        stdout, stderr = proc.communicate(timeout=5)
        return {'exit_code': proc.returncode, 'timed_out': True, 'stdout': stdout[-LIMIT:], 'stderr': stderr[-LIMIT:]}
    if len(stdout) + len(stderr) > LIMIT:
        raise ValueError('Trusted fixture exceeded output bound')
    return {'exit_code': proc.returncode, 'timed_out': False, 'stdout': stdout, 'stderr': stderr}


def assess(stack, variant, observed):
    """An expected negative must exit1 for its specific assertion, not any error."""
    if stack not in CASES or variant not in CASES[stack]:
        raise ValueError('Unknown fixed stack/variant')
    if observed['timed_out']:
        return {'status': 'BLOCKED', 'reason': 'fixture_timeout', 'failed_checks': [], 'unavailable_checks': []}
    def unique(pairs):
        values = {}
        for key, value in pairs:
            if key in values:
                raise ValueError('Duplicate fixture protocol key')
            values[key] = value
        return values
    try:
        # ShouldProcess can emit its built-in WhatIf message before the JSON line.
        lines = observed['stdout'].decode('utf-8-sig').strip().splitlines()
        document = json.loads(lines[-1], object_pairs_hook=unique)
        if not isinstance(document, dict) or set(document) != {'stack', 'variant', 'checks'} or document['stack'] != stack or document['variant'] != variant:
            raise ValueError('Fixture identity mismatch')
        checks = document['checks']
        if not isinstance(checks, list) or len(checks) != len(CHECKS[stack]):
            raise ValueError('Incomplete fixture checks')
        ids = []
        for check in checks:
            if not isinstance(check, dict) or set(check) != {'id', 'status'} or not isinstance(check['id'], str) or check['status'] not in ('PASSED', 'FAILED', 'NOT_AVAILABLE'):
                raise ValueError('Malformed fixture check')
            ids.append(check['id'])
        if set(ids) != CHECKS[stack] or len(set(ids)) != len(ids):
            raise ValueError('Check identity mismatch')
        failed = sorted(check['id'] for check in checks if check['status'] == 'FAILED')
        unavailable = sorted(check['id'] for check in checks if check['status'] == 'NOT_AVAILABLE')
        if unavailable and (stack != 'powershell' or unavailable != ['parent_reparse_component_rejected']):
            raise ValueError('Unexpected unavailable check')
    except (ValueError, UnicodeError, TypeError, IndexError):
        dependency_error = any(token in observed['stderr'] for token in
                               (b'ImportError', b'ModuleNotFoundError', b'Cannot find module', b'Could not load file or assembly'))
        return {'status': 'BLOCKED', 'reason': 'dependency_import_unavailable' if dependency_error else 'invalid_or_missing_fixture_protocol',
                'failed_checks': [], 'unavailable_checks': []}
    expected = sorted(CASES[stack][variant])
    if unavailable and set(expected) & set(unavailable) and observed['exit_code'] == 3 and not failed:
        return {'status': 'BLOCKED', 'reason': 'native_reparse_creation_unavailable', 'failed_checks': failed, 'unavailable_checks': unavailable}
    expected_exit = 1 if expected else 0
    matched = failed == expected and observed['exit_code'] == expected_exit
    return {'status': ('PASSED_WITH_LIMITATIONS' if unavailable else 'PASSED') if matched else 'FAILED',
            'reason': 'baseline_passed' if matched and not expected else 'specific_fault_rejected' if matched else 'assertion_or_exit_mismatch',
            'failed_checks': failed, 'unavailable_checks': unavailable}


def _tool(stack):
    return shutil.which('pwsh') if stack == 'powershell' else shutil.which(stack)


def preview(stacks=None):
    selected = list(CASES) if stacks is None else list(stacks)
    if not selected or len(set(selected)) != len(selected) or any(s not in CASES for s in selected):
        raise ValueError('Unique known stacks required')
    return {'execution': 'NOT_RUN', 'stacks': [{'stack': s, 'tool_available': bool(_tool(s)), 'variants': list(CASES[s])} for s in selected],
            'native_models_executed': False, 'browser_verified': False, 'production_verified': False}


def run(out, stacks=None):
    selected = [item['stack'] for item in preview(stacks)['stacks']]
    out = plain(out)
    if out.exists():
        raise ValueError('A new dedicated output directory is required')
    # All fixtures are bounded and checked before the first native command.
    contents = {(s, name): fixture_bytes(s, name) for s in selected for name in FILES[s]}
    harness_path = plain(__file__)
    if harness_path.stat().st_size > LIMIT:
        raise ValueError('Harness exceeds source bound')
    harness_before = harness_path.read_bytes()
    out.mkdir(parents=True)
    reports = []
    for stack in selected:
        folder = out / stack
        folder.mkdir()
        executable = _tool(stack)
        if not executable:
            reports.append({'stack': stack, 'status': 'BLOCKED', 'reason': 'tool_unavailable', 'tool_version': None, 'variants': []})
            continue
        env = os.environ.copy()
        for key in ('NODE_OPTIONS', 'NODE_PATH', 'DOTNET_STARTUP_HOOKS', 'DOTNET_ADDITIONAL_DEPS', 'DOTNET_SHARED_STORE'):
            env.pop(key, None)
        env.update(TEMP=str(folder), TMP=str(folder), DOTNET_CLI_TELEMETRY_OPTOUT='1',
                   DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1', DOTNET_NOLOGO='1',
                   DOTNET_ADD_GLOBAL_TOOLS_TO_PATH='false', DOTNET_GENERATE_ASPNET_CERTIFICATE='false',
                   DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE='true', MSBuildEnableWorkloadResolver='false',
                   DOTNET_CLI_HOME=str(folder / 'cli-home'), NUGET_PACKAGES=str(folder / 'packages'),
                   NUGET_HTTP_CACHE_PATH=str(folder / 'cache'))
        version_argv = [executable, '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', '$PSVersionTable.PSVersion.ToString()'] if stack == 'powershell' else [executable, '--version']
        try:
            version = process(version_argv, folder, env)
        except OSError:
            reports.append({'stack': stack, 'status': 'BLOCKED', 'reason': 'tool_launch_unavailable', 'tool_version': None, 'variants': []})
            continue
        _logs(folder, 'version', version)
        preparation = [{'stage': 'version', 'exit_code': version['exit_code'], 'timed_out': version['timed_out']}]
        version_text = version['stdout'].decode('utf-8-sig', errors='replace').strip()
        if version['timed_out'] or version['exit_code'] != 0 or not re.fullmatch(r'v?\d+\.\d+\.\d+(?:[-+][\w.-]+)?', version_text):
            reports.append({'stack': stack, 'status': 'BLOCKED', 'reason': 'version_probe_failed', 'tool_version': None,
                            'version_exit_code': version['exit_code'], 'preparation': preparation, 'variants': []})
            continue
        for name in FILES[stack]:
            (folder / name).write_bytes(contents[stack, name])
        if stack == 'dotnet':
            properties = ['-p:NuGetAudit=false', '-p:ImportDirectoryBuildProps=false', '-p:ImportDirectoryBuildTargets=false']
            restore = process([executable, 'restore', 'GuardianStack.csproj', '--configfile', 'NuGet.Config', *properties], folder, env, 120)
            _logs(folder, 'restore', restore)
            preparation.append({'stage': 'restore', 'exit_code': restore['exit_code'], 'timed_out': restore['timed_out']})
            build = process([executable, 'build', 'GuardianStack.csproj', '--no-restore', '--disable-build-servers',
                             '--nologo', '-v:q', '-m:1', '-nodeReuse:false', '-p:UseSharedCompilation=false', *properties], folder, env, 120) if restore['exit_code'] == 0 and not restore['timed_out'] else None
            if build is not None:
                _logs(folder, 'build', build)
                preparation.append({'stage': 'build', 'exit_code': build['exit_code'], 'timed_out': build['timed_out']})
            if build is None or build['exit_code'] != 0 or build['timed_out']:
                reports.append({'stack': stack, 'status': 'BLOCKED', 'reason': 'offline_restore_or_build_unavailable',
                                'tool_version': version_text, 'restore_exit_code': restore['exit_code'],
                                'build_exit_code': build['exit_code'] if build else None, 'preparation': preparation, 'variants': []})
                continue
        variants = []
        for variant in CASES[stack]:
            case = folder / variant
            case.mkdir()
            if stack == 'node':
                argv = [executable, str(folder / 'check.cjs'), variant]
            elif stack == 'dotnet':
                argv = [executable, str(folder / 'bin/Debug/net8.0/GuardianStack.dll'), variant]
            else:
                argv = [executable, '-NoLogo', '-NoProfile', '-NonInteractive', '-File',
                        str(folder / 'Check-Stack.ps1'), '-Root', str(case), '-Variant', variant]
            observed = process(argv, case, env)
            _logs(case, 'run', observed)
            variants.append({'variant': variant, 'exit_code': observed['exit_code'], 'timed_out': observed['timed_out'], **assess(stack, variant, observed)})
        status = 'FAILED' if any(v['status'] == 'FAILED' for v in variants) else 'BLOCKED' if any(v['status'] == 'BLOCKED' for v in variants) else 'PASSED_WITH_LIMITATIONS' if any(v['status'] == 'PASSED_WITH_LIMITATIONS' for v in variants) else 'PASSED'
        reports.append({'stack': stack, 'status': status, 'tool_version': version_text,
                        'version_exit_code': version['exit_code'], 'preparation': preparation, 'variants': variants})
    for key, before in contents.items():
        if fixture_bytes(*key) != before:
            raise ValueError('Reviewed source fixture drifted during run')
    if harness_path.read_bytes() != harness_before:
        raise ValueError('Harness source drifted during run')
    report = {'schema_version': 1, 'execution': 'EXECUTED', 'stacks': reports,
              'harness_sha256': hashlib.sha256(harness_before).hexdigest(),
              'fixture_sha256': {s + '/' + n: hashlib.sha256(data).hexdigest() for (s, n), data in contents.items()},
              'fixture_only': True, 'native_models_executed': False, 'browser_verified': False,
              'production_verified': False, 'os_network_isolation_verified': False,
              'notice': 'Trusted synthetic fixtures only. No candidate code, npm install, package source, browser, cloud or production action.'}
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    return report


def _logs(folder, prefix, observed):
    for field in ('stdout', 'stderr'):
        (folder / (prefix + '.' + field + '.txt')).write_bytes(observed[field])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--stack', choices=list(CASES), action='append')
    args = parser.parse_args()
    if args.run and args.out is None:
        parser.error('--run requires a new --out directory')
    if args.out is not None and not args.run:
        parser.error('--out requires explicit --run')
    result = run(args.out, args.stack) if args.run else preview(args.stack)
    print(json.dumps(result, indent=2))
    return 0 if not args.run or all(item['status'] in ('PASSED', 'PASSED_WITH_LIMITATIONS') for item in result['stacks']) else 2


if __name__ == '__main__':
    raise SystemExit(main())
