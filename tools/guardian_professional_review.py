"""Data-only blind review intake. Hashes bind bytes, never reviewer identity."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

try:
    from . import guardian_qualification as q
except ImportError:
    import guardian_qualification as q

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 4_000_000
MAX_ARTIFACTS = 256


def _fields(obj, names):
    if not isinstance(obj, dict) or set(obj) != set(names):
        raise ValueError('Unknown or missing fields: ' + ','.join(names))


def _text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 16000:
        raise ValueError('Expected bounded nonempty text')
    return value


def _hash(value):
    if not isinstance(value, str) or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('Expected SHA256')
    return value


def _plain(path):
    """Reject links/reparse points in every existing path component."""
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        if not part.exists() and not part.is_symlink():
            continue
        attrs = part.lstat()
        if stat.S_ISLNK(attrs.st_mode) or getattr(attrs, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Symlink/reparse path rejected')
    return path


def _relative(value):
    _text(value)
    path = PurePosixPath(value)
    if '\\' in value or ':' in value or path.is_absolute() or any(p in ('', '.', '..') for p in value.split('/')):
        raise ValueError('Expected normalized relative path')
    reserved = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}
    if any(p.endswith((' ', '.')) or p.split('.')[0].upper() in reserved or any(ord(c) < 32 for c in p) for p in path.parts):
        raise ValueError('Nonportable artifact path')
    return path


def _read(path):
    path = _plain(path)
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError('Expected bounded regular file')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0))
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('Expected regular file')
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('File exceeds bound')
    return data


def _json(path):
    # Qualification reader also rejects duplicate keys/nonfinite numbers.
    _read(path)
    return q.load_json(path)


def _write(path, value):
    data = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8') + b'\n'
    with path.open('xb') as stream:
        stream.write(data)


def cases(corpus):
    q.validate(corpus)
    return {c['id']: c for c in corpus['cases'] if c['oracle']['kind'] == 'independent_sme'}


def preview(corpus):
    # Explicit whitelist: oracle and any future private fields cannot leak.
    return [{'case_id': c['id'], 'agent_id': c['agent_id'], 'scenario': c['scenario'],
             'split': 'public_development', 'required_artifacts': c['artifacts']['required'],
             'criteria': [{'id': str(i + 1), 'dimension': r['dimension'], 'requirement': r['requirement']}
                          for i, r in enumerate(c['rubric'])]}
            for c in cases(corpus).values()]


def validate_manifest(corpus, manifest, artifact_root):
    _fields(manifest, ('schema_version', 'submissions'))
    if type(manifest['schema_version']) is not int or manifest['schema_version'] != 1 or not isinstance(manifest['submissions'], list):
        raise ValueError('Invalid submission manifest')
    if len(manifest['submissions']) > len(cases(corpus)):
        raise ValueError('Too many submissions')
    known = cases(corpus); seen = set(); paths = set(); buffers = {}; metadata = {}
    root = _plain(artifact_root)
    total_bytes = 0
    for submission in manifest['submissions']:
        _fields(submission, ('case_id', 'author_id', 'revision', 'model', 'artifacts'))
        cid = submission['case_id']
        if not isinstance(cid, str) or cid not in known or cid in seen:
            raise ValueError('Unknown or duplicate case')
        seen.add(cid)
        for key in ('author_id', 'revision', 'model'):
            _text(submission[key])
        artifacts = submission['artifacts']
        if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= MAX_ARTIFACTS:
            raise ValueError('Expected bounded nonempty artifacts')
        hashes = []
        for artifact in artifacts:
            _fields(artifact, ('path', 'sha256'))
            relative = _relative(artifact['path']); expected = _hash(artifact['sha256'])
            # Cross-platform casefold avoids Windows alias duplication.
            path_key = str(relative).casefold()
            if path_key in paths:
                raise ValueError('Duplicate artifact path')
            paths.add(path_key)
            data = _read(root.joinpath(*relative.parts))
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError('Artifact hash drift')
            if expected not in buffers:
                total_bytes += len(data)
                if total_bytes > 32_000_000 or len(buffers) >= 1024:
                    raise ValueError('Artifact bundle exceeds total bound')
                buffers[expected] = data
            if expected not in hashes:
                hashes.append(expected)
        metadata[cid] = {'submission_sha256': q.digest(submission), 'artifact_sha256': hashes}
    if sum(map(len, buffers.values())) > 32_000_000:
        raise ValueError('Artifact bundle exceeds total bound')
    return metadata, buffers


def export(corpus, out, manifest=None, artifact_root=None):
    metadata, buffers = ({}, {}) if manifest is None else validate_manifest(corpus, manifest, artifact_root)
    rows = preview(corpus)
    for row in rows:
        row.update(metadata.get(row['case_id'], {'submission_sha256': None, 'artifact_sha256': []}))
        row['candidate_evidence'] = 'HASH_BOUND_UNAUTHENTICATED' if row['artifact_sha256'] else 'NOT_VERIFIED'
    index = {'schema_version': 1, 'corpus_sha256': q.digest(corpus), 'cases': rows,
             'qualification': 'NOT_VERIFIED', 'private_holdout': 'BLOCKED_EXTERNAL_ISOLATION_REQUIRED'}
    # Validate all inputs before any destination mutation. Never overwrite.
    destination = _plain(out)
    destination.mkdir(parents=False, exist_ok=False)
    (destination / 'artifacts').mkdir()
    for sha, data in buffers.items():
        with (destination / 'artifacts' / (sha + '.bin')).open('xb') as stream:
            stream.write(data)
    _write(destination / 'index.json', index)
    template = {'schema_version': 1, 'bundle_sha256': q.digest(index), 'reviewer_id': 'UNASSIGNED',
                'review_kind': 'AI_ADVISORY', 'reviews': [
                    {'case_id': r['case_id'], 'criteria': [
                        {'id': c['id'], 'verdict': 'unknown', 'evidence_sha256': [], 'rationale': 'NOT_VERIFIED'}
                        for c in r['criteria']]} for r in rows]}
    _write(destination / 'review-template.json', template)
    return {'case_count': len(rows), 'artifact_count': len(buffers), 'bundle_sha256': q.digest(index),
            'qualification': 'NOT_VERIFIED'}


def ingest(corpus, bundle, review):
    index = _json(_plain(bundle) / 'index.json')
    _fields(index, ('schema_version', 'corpus_sha256', 'cases', 'qualification', 'private_holdout'))
    if type(index['schema_version']) is not int or index['schema_version'] != 1 or index['corpus_sha256'] != q.digest(corpus) or index['qualification'] != 'NOT_VERIFIED' or index['private_holdout'] != 'BLOCKED_EXTERNAL_ISOLATION_REQUIRED':
        raise ValueError('Bundle corpus/status drift')
    expected = preview(corpus)
    if not isinstance(index['cases'], list) or len(index['cases']) != len(expected):
        raise ValueError('Incomplete bundle')
    rows = {}
    for actual, source in zip(index['cases'], expected):
        _fields(actual, (*source.keys(), 'submission_sha256', 'artifact_sha256', 'candidate_evidence'))
        if any(actual[k] != v for k, v in source.items()):
            raise ValueError('Bundle case drift')
        hashes = actual['artifact_sha256']
        if not isinstance(hashes, list) or len(hashes) > MAX_ARTIFACTS or len(set(hashes)) != len(hashes):
            raise ValueError('Invalid artifact hashes')
        if actual['submission_sha256'] is not None:
            _hash(actual['submission_sha256'])
        if bool(hashes) != (actual['submission_sha256'] is not None) or actual['candidate_evidence'] != ('HASH_BOUND_UNAUTHENTICATED' if hashes else 'NOT_VERIFIED'):
            raise ValueError('Invalid evidence state')
        for sha in hashes:
            _hash(sha)
            if hashlib.sha256(_read(Path(bundle) / 'artifacts' / (sha + '.bin'))).hexdigest() != sha:
                raise ValueError('Exported artifact hash drift')
        rows[actual['case_id']] = actual
    _fields(review, ('schema_version', 'bundle_sha256', 'reviewer_id', 'review_kind', 'reviews'))
    if type(review['schema_version']) is not int or review['schema_version'] != 1 or review['bundle_sha256'] != q.digest(index):
        raise ValueError('Review binding drift')
    _text(review['reviewer_id'])
    if review['review_kind'] not in ('AI_ADVISORY', 'EXTERNAL_REVIEW_UNAUTHENTICATED'):
        raise ValueError('Unsupported reviewer class; no authenticated SME backend')
    if not isinstance(review['reviews'], list) or len(review['reviews']) != len(rows):
        raise ValueError('All case criteria must be explicit, including unknown')
    result = []; seen = set()
    for item in review['reviews']:
        _fields(item, ('case_id', 'criteria'))
        cid = item['case_id']
        if not isinstance(cid, str) or cid not in rows or cid in seen:
            raise ValueError('Unknown or duplicate reviewed case')
        seen.add(cid); row = rows[cid]
        criteria = item['criteria']
        if not isinstance(criteria, list) or len(criteria) != len(row['criteria']):
            raise ValueError('Missing review criteria')
        ids = set(); counters = dict(supported=0, contradicted=0, unknown=0); bilateral = []
        for criterion in criteria:
            _fields(criterion, ('id', 'verdict', 'evidence_sha256', 'rationale'))
            criterion_id = criterion['id']
            if not isinstance(criterion_id, str) or criterion_id not in {c['id'] for c in row['criteria']} or criterion_id in ids:
                raise ValueError('Unknown or duplicate criterion')
            ids.add(criterion_id); _text(criterion['rationale'])
            verdict = criterion['verdict']; evidence = criterion['evidence_sha256']
            if not isinstance(verdict, str) or verdict not in counters or not isinstance(evidence, list) or any(not isinstance(x, str) or x not in row['artifact_sha256'] for x in evidence) or len(set(evidence)) != len(evidence):
                raise ValueError('Invalid verdict/evidence')
            if verdict != 'unknown' and not evidence:
                raise ValueError('Conclusions require hash-bound evidence')
            counters[verdict] += 1
            bilateral.append({'criterion_id': criterion_id, 'candidate_claim_verified': False,
                              'reviewer_verdict': verdict, 'evidence_sha256': evidence})
        result.append({'case_id': cid, 'candidate_evidence': row['candidate_evidence'],
                       'review_class': review['review_kind'], 'criteria': counters, 'bilateral_criteria': bilateral,
                       'qualification': 'REQUIRES_AUTHENTICATED_SME'})
    return {'schema_version': 1, 'bundle_sha256': q.digest(index), 'review_sha256': q.digest(review),
            'reviewer_identity_authenticated': False, 'competence_verified': False,
            'qualified_cases': 0, 'private_holdout_validated': False, 'rows': result,
            'qualification': 'NOT_VERIFIED'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', default=str(ROOT / 'core/qualification-cases-v1.json'))
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('preview')
    validate = sub.add_parser('validate'); validate.add_argument('--manifest', required=True); validate.add_argument('--artifact-root', required=True)
    exp = sub.add_parser('review-export'); exp.add_argument('--out', required=True); exp.add_argument('--manifest'); exp.add_argument('--artifact-root')
    rev = sub.add_parser('review-ingest'); rev.add_argument('--bundle', required=True); rev.add_argument('--review', required=True)
    args = parser.parse_args(argv)
    try:
        corpus = _json(args.corpus)
        if args.command == 'preview':
            result = preview(corpus)
        elif args.command == 'validate':
            metadata, blobs = validate_manifest(corpus, _json(args.manifest), args.artifact_root)
            result = {'valid': True, 'submitted_cases': len(metadata), 'artifacts': len(blobs), 'qualification': 'NOT_VERIFIED'}
        elif args.command == 'review-export':
            if bool(args.manifest) != bool(args.artifact_root):
                raise ValueError('Manifest and artifact root must be supplied together')
            result = export(corpus, args.out, _json(args.manifest) if args.manifest else None, args.artifact_root)
        else:
            result = ingest(corpus, args.bundle, _json(args.review))
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        print(json.dumps({'error': str(exc), 'qualification': 'NOT_VERIFIED'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
