"""Opt-in real-browser checks of reviewed fixtures, never candidate code or AT certification."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
try:
    from .guardian_runtime import terminate_tree
except ImportError:
    from guardian_runtime import terminate_tree

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'eval/browser-fixtures'
FILES = ('index.html', 'app.js', 'check.cjs')
CHECKS = {'single_enter_and_click', 'composition_guard', 'error_preserves_draft_focus',
          'error_associated', 'stale_navigation_rejected', 'dialog_keyboard_trapped',
          'escape_restores_mounted_fallback', 'tenant_locale_cache_separated',
          'plural_rtl_timezone', 'no_runtime_errors_or_external_requests'}
CASES = {'baseline': [], 'double-submit': ['single_enter_and_click', 'composition_guard'],
         'composition-unchecked': ['composition_guard'], 'error-clears': ['error_preserves_draft_focus'],
         'error-unassociated': ['error_associated'], 'stale-applies': ['stale_navigation_rejected'],
         'focus-leak': ['dialog_keyboard_trapped'], 'restore-lost': ['escape_restores_mounted_fallback'],
         'cache-unscoped': ['tenant_locale_cache_separated'], 'plural-wrong': ['plural_rtl_timezone']}
LIMIT = 200_000


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def plain(path):
    path = Path(path).absolute()
    for item in (path, *path.parents):
        if item.is_symlink() or (item.exists() and getattr(item.lstat(), 'st_file_attributes', 0) & 0x400):
            raise ValueError('Output/fixture symlinks and reparse ancestors are rejected')
    return path


def fixtures():
    result = {}
    for name in FILES:
        path = plain(FIXTURES/name)
        if not path.is_file() or path.stat().st_size > LIMIT:
            raise ValueError('Missing/oversized reviewed fixture')
        result[name] = sha(path)
    return result


def preview():
    return {'schema_version': 1, 'execution': 'NOT_RUN', 'cases': CASES,
            'checks': sorted(CHECKS), 'fixture_sha256': fixtures(),
            'native_models_executed': False, 'browser_verified': False,
            'at': 'NOT_VERIFIED', 'operating_system_ime': 'NOT_VERIFIED',
            'requirement': 'Installed Node and trusted runtime Playwright; no automatic downloads.'}


def dependency():
    node = shutil.which('node')
    module = Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
    if not node or not (module/'package.json').is_file() or not (module/'index.js').is_file():
        return None
    channel = 'bundled'
    if os.name == 'nt':
        chrome = Path(os.environ.get('PROGRAMFILES', 'C:/Program Files'))/'Google/Chrome/Application/chrome.exe'
        edge = Path(os.environ.get('PROGRAMFILES(X86)', 'C:/Program Files (x86)'))/'Microsoft/Edge/Application/msedge.exe'
        if chrome.is_file(): channel = 'chrome'
        elif edge.is_file(): channel = 'msedge'
    return {'node': node, 'module': str(module), 'channel': channel,
            'package_sha256': sha(module/'package.json'), 'entry_sha256': sha(module/'index.js')}


def strict_json(value):
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result: raise ValueError('Duplicate JSON field')
            result[key] = item
        return result
    return json.loads(value, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def execute(argv, out, env):
    process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               stdin=subprocess.DEVNULL, cwd=out, env=env,
                               start_new_session=os.name != 'nt',
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0)
    try:
        stdout, stderr = process.communicate(timeout=120)
    except subprocess.TimeoutExpired:
        terminate_tree(process)
        process.communicate(timeout=5)
        raise
    return {'exit_code': process.returncode, 'stdout': stdout, 'stderr': stderr}


def assess(document):
    """Specific failed assertions are required; an import/launch/test error never kills a mutant."""
    if (not isinstance(document, dict) or document.get('protocol_version') != 1 or
            document.get('stack') != 'real-browser' or document.get('infrastructure_error') or
            not isinstance(document.get('browser_version'), str) or not document['browser_version']):
        raise ValueError('Missing real browser protocol or infrastructure failure')
    rows = document.get('variants')
    if not isinstance(rows, list) or len(rows) != len(CASES):
        raise ValueError('Incomplete variant inventory')
    seen = set(); receipts = []
    for row in rows:
        if not isinstance(row, dict) or row.get('variant') not in CASES or row['variant'] in seen:
            raise ValueError('Unknown/duplicate variant')
        variant = row['variant']; seen.add(variant)
        if row.get('infrastructure_error') or row.get('errors') != []:
            raise ValueError('Fixture runtime error is not an expected negative')
        checks = row.get('checks')
        if (not isinstance(checks, list) or len(checks) != len(CHECKS) or
                any(not isinstance(c, dict) or c.get('id') not in CHECKS or c.get('status') not in ('PASSED', 'FAILED') for c in checks) or
                {c['id'] for c in checks} != CHECKS):
            raise ValueError('Missing, duplicate or invalid check')
        failed = sorted(c['id'] for c in checks if c['status'] == 'FAILED')
        accepted = failed == sorted(CASES[variant])
        receipts.append({'variant': variant, 'status': 'PASSED' if accepted else 'FAILED',
                         'reason': ('baseline_passed' if variant == 'baseline' else 'specific_fault_rejected') if accepted else 'unexpected_assertion_outcome',
                         'failed_checks': failed, 'checks': checks})
    return receipts


def run(out):
    out = plain(out)
    if out.exists(): raise ValueError('A new output directory is required')
    report = preview(); out.mkdir(parents=True)
    report.update(execution='BLOCKED', harness_sha256=sha(__file__),
                  environment={'os_name': os.name, 'python_version': platform.python_version()})
    dep = dependency()
    if dep is None:
        report['reason'] = 'Installed Node/Playwright unavailable; browser NOT_VERIFIED'
    else:
        argv = [dep['node'], str(FIXTURES/'check.cjs'), dep['module'], dep['channel']]
        report['argv'] = argv; report['dependency'] = dep
        env = dict(os.environ)
        for key in ('NODE_OPTIONS', 'NODE_PATH', 'PWDEBUG', 'PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD'):
            env.pop(key, None)
        try:
            process = execute(argv, out, env)
            report['exit_code'] = process['exit_code']
            if len(process['stdout']) + len(process['stderr']) > LIMIT: raise ValueError('Output exceeds bound')
            (out/'stdout.json').write_bytes(process['stdout']); (out/'stderr.txt').write_bytes(process['stderr'])
            if process['exit_code'] != 0: raise ValueError('Browser launch/runtime process failed')
            document = strict_json(process['stdout'].decode('utf8'))
            receipts = assess(document)
            report.update(execution='COMPLETED', browser_verified=True,
                          browser_version=document['browser_version'], playwright_version=document.get('playwright_version'),
                          variants=receipts, passed=all(r['status'] == 'PASSED' for r in receipts),
                          stdout_sha256=sha(out/'stdout.json'))
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            report['reason'] = type(exc).__name__ + ': ' + str(exc)
    report['limitations'] = ['Trusted local fixtures only; no generated candidate code execution.',
        'Synthetic CompositionEvent plus browser keyboard is not operating-system IME execution.',
        'No screen reader/assistive technology, general WCAG conformance or professional certification.',
        'Fresh browser context and request interception are not OS/network isolation.',
        'No real frontend framework hydration, mobile browser matrix, backend exactly-once or load/SLO claim.',
        'Chrome/Edge channel compatibility is observed only for the recorded installed version.']
    (out/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true'); parser.add_argument('--out', type=Path)
    args = parser.parse_args(argv)
    if args.run and args.out is None: parser.error('--run requires a new --out directory')
    report = run(args.out) if args.run else preview()
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if not args.run or report.get('passed') else 2


if __name__ == '__main__':
    raise SystemExit(main())
