"""Read-only Guardian doctor identity; checksums are not execution attestations.

Only packaged Guardian paths are read. No Codex credentials/configuration, model
calls, network or permissions changes are involved. Revision is reported only
for a Git checkout rooted here, never an ancestor project of an installation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
from pathlib import Path

try:
    from .build_release import source_files
except ImportError:
    from build_release import source_files

ROOT = Path(__file__).resolve().parents[1]
MAX_FILES = 10000
MAX_FILE_BYTES = 20_000_000
MAX_TOTAL_BYTES = 100_000_000
BINDINGS = ('runtime_sha256', 'profiles_sha256', 'contracts_sha256', 'revision')


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('utf8')


def _plain(path):
    path = Path(path).absolute()
    for item in (path, *path.parents):
        if item.is_symlink() or (item.exists() and getattr(item.lstat(), 'st_file_attributes', 0) & 0x400):
            raise ValueError('Fingerprint symlink/reparse path rejected')
    return path


def fingerprint(root=ROOT):
    """Return exact managed-content identity, with no assertion of native loading.

    Actual bytes are intentionally used, including checkout newline differences.
    Work/checkpoints, caches, Git internals, account/config and auth files are
    excluded. Missing identity files fail closed; this is not a general scanner.
    """
    root = _plain(root)
    if not root.is_dir():
        raise ValueError('Guardian root is not a directory')
    required = ('VERSION', 'core/contracts-catalog-v1.json', 'core/professional-contracts-v1.json')
    if any(not _plain(root / name).is_file() for name in required):
        raise ValueError('Incomplete Guardian identity files')
    paths = source_files(root)
    if not paths or len(paths) > MAX_FILES:
        raise ValueError('Fingerprint file-count bound exceeded')
    inventory = []
    total = 0
    for path in paths:
        _plain(path)
        if re.fullmatch(r'(?i)(?:\.env(?:\..*)?|auth\.json|credentials(?:\.json)?|id_(?:rsa|ed25519)|.*\.(?:pem|key|pfx|p12))', path.name):
            raise ValueError('Unexpected sensitive file in packaged scope')
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('Expected regular packaged file')
        size = info.st_size
        total += size
        if size > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
            raise ValueError('Fingerprint byte bound exceeded')
        descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0))
        with os.fdopen(descriptor, 'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError('Expected regular packaged file')
            data = stream.read(MAX_FILE_BYTES + 1)
        if len(data) != size:
            raise ValueError('File changed during fingerprint')
        inventory.append({'path': path.relative_to(root).as_posix(),
                          'sha256': hashlib.sha256(data).hexdigest(), 'bytes': size})
    # No Git invocation in installed runtimes nested in unrelated repositories.
    revision, dirty, git_status = None, None, 'NOT_OBSERVED'
    git_marker = _plain(root / '.git')
    if git_marker.exists():
        try:
            opts = ['git', '-c', 'core.fsmonitor=false', '-C', str(root)]
            result = subprocess.run(opts + ['rev-parse', 'HEAD'], capture_output=True,
                                    text=True, timeout=10, check=False)
            candidate = result.stdout.strip()
            if result.returncode == 0 and re.fullmatch(r'[0-9a-f]{40,64}', candidate):
                revision = candidate
            status = subprocess.run(opts + ['status', '--porcelain', '--untracked-files=no'],
                                    capture_output=True, timeout=10, check=False)
            if revision is not None and status.returncode == 0:
                dirty, git_status = bool(status.stdout), 'OBSERVED'
        except (OSError, subprocess.TimeoutExpired):
            pass
    version = (root / 'VERSION').read_text(encoding='utf8').strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-(?:dev|rc)\.\d+)?', version):
        raise ValueError('Invalid Guardian version')
    profile_inventory = [entry for entry in inventory
                         if entry['path'].endswith('.toml') and '/agents/' in entry['path']]
    contract_inventory = [entry for entry in inventory if entry['path'] in required[1:]]
    return {'schema_version': 1, 'version': version, 'revision': revision,
            'git_status': git_status, 'tracked_changes': dirty,
            'runtime_sha256': hashlib.sha256(_canonical(inventory)).hexdigest(),
            'profiles_sha256': hashlib.sha256(_canonical(profile_inventory)).hexdigest(),
            'contracts_sha256': hashlib.sha256(_canonical(contract_inventory)).hexdigest(),
            'file_count': len(inventory), 'profile_count': len(profile_inventory),
            'scope': 'packaged Guardian assets; actual bytes; no Git internals or user configuration',
            'native_loading': 'NOT_VERIFIED', 'authenticated': False,
            'notice': 'Version, revision and digests identify observed files; no native/model/SME acceptance is inferred.'}


def assess_evidence_binding(evidence, observed):
    """Compare a new explicit runtime binding, never upgrade historical native39.

    Exact binding only proves equality of supplied references, not the truth of
    model/session/test claims. Old evidence without all bindings stays unknown.
    """
    if not isinstance(evidence, dict) or not isinstance(observed, dict):
        raise ValueError('Expected evidence and fingerprint objects')
    binding = evidence.get('runtime_binding')
    if not isinstance(binding, dict) or set(binding) != set(BINDINGS):
        return {'status': 'NOT_VERIFIED', 'mismatches': [], 'native_verified': False,
                'reason': 'Missing closed current-runtime binding; historical results are not current acceptance.'}
    if any(not isinstance(binding[key], str) or not re.fullmatch(r'[a-f0-9]{64}', binding[key])
           for key in BINDINGS if key != 'revision'):
        raise ValueError('Invalid runtime binding digest')
    if binding['revision'] is not None and (not isinstance(binding['revision'], str) or not re.fullmatch(r'[a-f0-9]{40,64}', binding['revision'])):
        raise ValueError('Invalid runtime binding revision')
    mismatch = [key for key in BINDINGS if key not in observed or binding[key] != observed[key]]
    return {'status': 'STALE' if mismatch else 'MATCHED_NOT_AUTHENTICATED',
            'mismatches': mismatch, 'native_verified': False,
            'reason': 'File/reference correspondence only; verify execution, model, stack, dataset and consumer independently.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['doctor'])
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--evidence-file', type=Path)
    args = parser.parse_args()
    result = fingerprint(args.root)
    if args.evidence_file:
        evidence_file = _plain(args.evidence_file)
        if not evidence_file.is_file() or evidence_file.stat().st_size > 1_000_000:
            raise ValueError('Expected bounded evidence JSON')
        result['evidence_binding'] = assess_evidence_binding(json.loads(evidence_file.read_text(encoding='utf8')), result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
