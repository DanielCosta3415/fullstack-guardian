"""Opt-in trusted local service checks, not candidate execution or certification.

Only the fixed stdlib fixtures below run. HTTP binds numeric loopback addresses
and ephemeral ports; no proxy, outside address, package install or global setting.
Faults must produce their specified observable violation: an arbitrary exception
is ERROR, never a killed mutant. Actual fixture results are not agent evaluation.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
import datetime as dt
import hashlib
import hmac
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import platform
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT/'eval/service-fixtures/scenarios.json'


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _data():
    value = json.loads(FIXTURE.read_text(encoding='utf8'))
    if value['schema_version'] != 1:
        raise ValueError('Unsupported trusted fixture')
    return value


def _connect(path):
    return sqlite3.connect(path, timeout=.05, isolation_level=None)


def _durable(path, query):
    db = _connect(path)
    try:
        return db.execute(query).fetchall()
    finally:
        db.close()


class _Cancel(Exception):
    pass


def transaction(broken, folder, data):
    path = folder/'transaction.sqlite'
    db = _connect(path)
    try:
        db.executescript('CREATE TABLE account(balance INTEGER NOT NULL);'
                         'CREATE TABLE outbox(id TEXT PRIMARY KEY, amount INTEGER NOT NULL);')
        db.execute('INSERT INTO account VALUES (?)', (data['account_balance'],))
        def transfer(amount, command, cancel=None):
            if type(amount) is not int or amount <= 0:
                return 'invalid'
            db.execute('BEGIN IMMEDIATE')
            try:
                db.execute('UPDATE account SET balance=balance-?', (amount,))
                db.execute('INSERT INTO outbox VALUES (?,?)', (command, amount))
                if cancel == 'before_commit':
                    raise _Cancel()
                db.commit()
                return 'timeout_after_commit' if cancel == 'after_commit' else 'committed'
            except _Cancel:
                # Deliberate faulty implementation: commits instead of rollback.
                db.commit() if broken else db.rollback()
                return 'cancelled'
        transfer(data['committed_debit'], 'first')
        before_invalid = db.execute('SELECT balance FROM account').fetchone()[0]
        invalid = transfer(-1, 'invalid')
        after_invalid = db.execute('SELECT balance FROM account').fetchone()[0]
        transfer(data['cancelled_debit'], 'cancelled', 'before_commit')
        timeout = transfer(data['timeout_after_commit_debit'], 'timed', 'after_commit')
    finally:
        db.close()
    balance = _durable(path, 'SELECT balance FROM account')[0][0]
    rows = _durable(path, 'SELECT id,amount FROM outbox ORDER BY id')
    return {'balance': balance, 'outbox_ids': [r[0] for r in rows],
            'invalid_no_effect': invalid == 'invalid' and before_invalid == after_invalid,
            'timeout_result': timeout, 'reopened': True}


def fencing(broken, folder, data):
    path = folder/'fencing.sqlite'
    db = _connect(path)
    db.executescript('CREATE TABLE resource(epoch INTEGER NOT NULL,value INTEGER NOT NULL);'
                     'INSERT INTO resource VALUES(1,0);CREATE TABLE effects(id TEXT PRIMARY KEY);')
    db.close()
    go = threading.Event()
    waiting = threading.Event()
    result, errors = [], []
    def apply(epoch, job):
        db = _connect(path)
        try:
            db.execute('BEGIN IMMEDIATE')
            changed = db.execute('UPDATE resource SET value=value+1'+('' if broken else ' WHERE epoch=?'),
                                 () if broken else (epoch,)).rowcount
            if changed != 1:
                db.rollback()
                return False
            try:
                db.execute('INSERT INTO effects VALUES (?)', (job,))
            except sqlite3.IntegrityError as exc:
                if exc.sqlite_errorcode not in (sqlite3.SQLITE_CONSTRAINT_PRIMARYKEY, sqlite3.SQLITE_CONSTRAINT_UNIQUE):
                    raise
                db.rollback()
                return False
            db.commit()
            return True
        finally:
            db.close()
    def stale_worker():
        try:
            waiting.set()
            if not go.wait(5):
                raise TimeoutError('Barrier not released')
            result.append(apply(1, 'stale'))
        except BaseException as exc:
            errors.append(exc)
    worker = threading.Thread(target=stale_worker)
    worker.start()
    try:
        if not waiting.wait(5):
            raise TimeoutError('Worker not waiting')
        db = _connect(path)
        db.execute('BEGIN IMMEDIATE')
        db.execute('UPDATE resource SET epoch=2')
        db.commit()
        db.close()
    finally:
        go.set()
        worker.join(5)
    if worker.is_alive() or errors:
        raise RuntimeError('Fencing worker failed') from (errors[0] if errors else None)
    current = apply(2, 'current')
    duplicate_after_reopen = apply(2, 'current')
    return {'stale_rejected': result == [False], 'current_applied': current,
            'duplicate_after_reopen_rejected': not duplicate_after_reopen,
            'value': _durable(path, 'SELECT value FROM resource')[0][0],
            'effects': _durable(path, 'SELECT COUNT(*) FROM effects')[0][0]}


def migration(broken, folder, data):
    path = folder/'migration.sqlite'
    db = _connect(path)
    db.execute('CREATE TABLE orders(id INTEGER PRIMARY KEY,value INTEGER NOT NULL)')
    db.executemany('INSERT INTO orders VALUES (?,?)', data['migration_rows'])
    db.execute('BEGIN IMMEDIATE')
    other = _connect(path)
    started = time.monotonic()
    try:
        try:
            other.execute('BEGIN IMMEDIATE')
            busy = False
        except sqlite3.OperationalError as exc:
            if exc.sqlite_errorcode != sqlite3.SQLITE_BUSY:
                raise
            busy = True
    finally:
        lock_wait_ms = (time.monotonic()-started)*1000
        db.rollback()
        db.close()
        other.close()
    (folder/'lock.json').write_text(json.dumps({'wait_ms': lock_wait_ms,
        'busy_error_code': sqlite3.SQLITE_BUSY if busy else None,
        'configured_timeout_seconds': .05, 'engine': sqlite3.sqlite_version})+'\n', encoding='utf8')
    db = _connect(path)
    try:
        db.execute('BEGIN IMMEDIATE')
        try:
            db.execute('ALTER TABLE orders ADD COLUMN derived INTEGER')
            db.execute('UPDATE orders SET derived=value+1 WHERE id=1')
            raise _Cancel('Seeded mid-migration failure')
        except _Cancel:
            db.commit() if broken else db.rollback()
        columns = [r[1] for r in db.execute('PRAGMA table_info(orders)')]
        restored = columns == ['id', 'value']
        db.execute('BEGIN IMMEDIATE')
        if 'derived' not in columns:
            db.execute('ALTER TABLE orders ADD COLUMN derived INTEGER')
        db.execute('UPDATE orders SET derived=value+1')
        db.commit()
    finally:
        db.close()
    rows = _durable(path, 'SELECT id,value,derived FROM orders ORDER BY id')
    return {'busy_rejected': busy, 'lock_wait_observed': lock_wait_ms > 0,
            'failed_migration_restored_schema': restored,
            'forward_retry_rows': [list(r) for r in rows], 'reopened': True}


@contextmanager
def _server(handler):
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    # server_close waits for request threads; each connection has a bounded
    # socket timeout, so cleanup is not an unsupported daemon-thread claim.
    server.daemon_threads = False
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)
        if thread.is_alive():
            raise RuntimeError('HTTP server did not stop')


class _Handler(BaseHTTPRequestHandler):
    timeout = 3

    def log_message(self, *_):
        pass

    def reply(self, status, payload, headers=None):
        content = _json(payload)
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(content)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(content)


def _request(port, path='/', method='GET', body=None, headers=None):
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
    try:
        connection.request(method, path, body, headers or {})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def wire(broken, folder, data):
    key = data['wire_key'].encode()
    seen = {}
    effects = []
    class Handler(_Handler):
        def do_POST(self):
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 <= length <= 4096:
                return self.reply(413, {'error': 'fixture_body_bound'})
            raw = self.rfile.read(length)
            parsed = json.loads(raw)
            signed = _json(parsed) if broken else raw
            signature = hmac.new(key, signed, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, self.headers.get('X-Signature', '')):
                return self.reply(401, {'error': 'signature'})
            request_id = self.headers['Idempotency-Key']
            digest = hashlib.sha256(raw).hexdigest()
            if request_id in seen:
                return self.reply(200 if seen[request_id] == digest else 409, {'effects': len(effects)})
            seen[request_id] = digest
            effects.append(parsed)
            self.reply(201, {'effects': len(effects)})
    compact = _json({'amount': 17})
    headers = {'Idempotency-Key': 'first', 'X-Signature': hmac.new(key, compact, hashlib.sha256).hexdigest()}
    with _server(Handler) as server:
        port = server.server_port
        first = _request(port, '/event', 'POST', compact, headers)[0]
        retry = _request(port, '/event', 'POST', compact, headers)[0]
        altered_bytes = _request(port, '/event', 'POST', b'{ "amount" : 17 }', headers)[0]
        different = _json({'amount': 18})
        changed_headers = dict(headers, **{'X-Signature': hmac.new(key, different, hashlib.sha256).hexdigest()})
        replay = _request(port, '/event', 'POST', different, changed_headers)[0]
    return {'first': first, 'valid_retry': retry, 'changed_wire_bytes': altered_bytes,
            'different_payload_replay': replay, 'effects': len(effects)}


def consumer(broken, folder, data):
    class Handler(_Handler):
        def do_GET(self):
            self.reply(200, {'count': True, 'status': 'future_value'})
    with _server(Handler) as server:
        status, _, raw = _request(server.server_port)
    value = json.loads(raw)
    # bool is a Python int subclass; the fixture rejects that wire-type change.
    count_valid = isinstance(value['count'], int) if broken else type(value['count']) is int
    strict_enum_rejected = value['status'] not in {'ready', 'pending'}
    tolerant = value['status'] if value['status'] in {'ready', 'pending'} else {'unknown': value['status']}
    return {'http_status': status, 'old_integer_consumer_rejected': not count_valid,
            'strict_enum_rejected': strict_enum_rejected, 'tolerant_unknown': tolerant}


def resource_auth(broken, folder, data):
    class Handler(_Handler):
        def do_GET(self):
            tenant = self.headers.get('X-Fixture-Tenant')
            if not broken and tenant != 'owner-a':
                return self.reply(403, {'error': 'resource_authorization'})
            self.reply(200, {'private': 'owner-a-data'})
    with _server(Handler) as server:
        own = _request(server.server_port, '/resource', headers={'X-Fixture-Tenant': 'owner-a'})
        foreign = _request(server.server_port, '/resource', headers={'X-Fixture-Tenant': 'tenant-b'})
    return {'owner_status': own[0], 'foreign_status': foreign[0],
            'foreign_exposure': b'owner-a-data' in foreign[2]}


def destinations(broken, folder, data):
    hits = {'allowed': 0, 'forbidden': 0}
    class Forbidden(_Handler):
        def do_GET(self):
            hits['forbidden'] += 1
            self.reply(200, {'secret': 'forbidden-fixture'})
    with _server(Forbidden) as forbidden:
        class Allowed(_Handler):
            def do_GET(self):
                hits['allowed'] += 1
                if self.path == '/redirect':
                    return self.reply(302, {}, {'Location': 'http://forbidden.fixture.test/secret'})
                self.reply(200, {'ok': True})
        with _server(Allowed) as allowed:
            permitted = allowed.server_port
            denied = forbidden.server_port
            def fetch(path, rebind=False):
                url = 'http://allowed.fixture.test'+path
                resolutions = 0
                def resolve(host):
                    nonlocal resolutions
                    resolutions += 1
                    if host == 'forbidden.fixture.test' or rebind and resolutions > 1:
                        return denied
                    return permitted
                for hop in range(3):
                    parsed = urlsplit(url)
                    port = resolve(parsed.hostname)
                    # Correct implementation validates every hop and pins the
                    # observed numeric endpoint; mutant resolves again and only
                    # validates its first hop, exposing the controlled stub.
                    if (not broken or hop == 0) and port != permitted:
                        return 'denied'
                    if broken and rebind:
                        port = resolve(parsed.hostname)
                    status, headers, _ = _request(port, parsed.path)
                    if status == 302:
                        url = headers['Location']
                    else:
                        return 'ok'
                raise RuntimeError('Fixture exceeded redirect bound')
            direct = fetch('/ok')
            redirect = fetch('/redirect')
            rebind = fetch('/ok', rebind=True)
    return {'direct': direct, 'redirect': redirect, 'rebind_pinned': rebind,
            'forbidden_hits': hits['forbidden'], 'allowed_hits': hits['allowed']}


def _b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=')


def token_rotation(broken, folder, data):
    keys = {name: value.encode() for name, value in data['token_keys'].items()}
    now = data['token_now']
    def encode(kid, alg='HS256', key=None, subject='fixture-user'):
        parts = [_b64(_json({'alg': alg, 'kid': kid, 'typ': 'JWT'})),
                 _b64(_json({'sub': subject, 'exp': now+60, 'iss': 'fixture-issuer', 'aud': 'fixture-audience'}))]
        signed = b'.'.join(parts)
        signature = hmac.new(key or keys.get(kid, b'unknown-fixture-key'), signed, hashlib.sha256).digest()
        return b'.'.join([*parts, _b64(signature)])
    cache = {'current': keys['current']}
    refreshes = 0
    def verify(token, issuer_available=True):
        nonlocal refreshes
        head, payload, signature = token.split(b'.')
        decode = lambda x: json.loads(base64.urlsafe_b64decode(x+b'='*((-len(x)) % 4)))
        header, claims = decode(head), decode(payload)
        if header['alg'] != 'HS256' and not broken:
            return False
        kid = header['kid']
        if kid not in cache:
            refreshes += 1
            if issuer_available:
                cache.update(keys)
        if kid not in cache:
            return False
        expected = _b64(hmac.new(cache[kid], head+b'.'+payload, hashlib.sha256).digest())
        return (hmac.compare_digest(expected, signature) and claims['exp'] > now
                and claims['iss'] == 'fixture-issuer' and claims['aud'] == 'fixture-audience')
    current = verify(encode('current'))
    unknown = verify(encode('unknown'))
    downgrade = verify(encode('current', alg='none'))
    rotated = verify(encode('next'))
    invalid_during_failure = verify(encode('current', key=b'invalid-fixture-key'), issuer_available=False)
    known_during_failure = verify(encode('current'), issuer_available=False)
    return {'current_valid': current, 'unknown_rejected': not unknown,
            'algorithm_downgrade_rejected': not downgrade, 'new_authorized_key_valid': rotated,
            'invalid_during_issuer_failure_rejected': not invalid_during_failure,
            'known_cached_valid_during_failure': known_during_failure, 'refreshes': refreshes}


CASES = [
    ('transaction', ['S08-P1'], transaction,
     {'balance': 65, 'outbox_ids': ['first', 'timed'], 'invalid_no_effect': True,
      'timeout_result': 'timeout_after_commit', 'reopened': True}, 'balance'),
    ('fencing', ['S10-P1'], fencing,
     {'stale_rejected': True, 'current_applied': True, 'duplicate_after_reopen_rejected': True,
      'value': 1, 'effects': 1}, 'stale_rejected'),
    ('migration', ['S11-P1'], migration,
     {'busy_rejected': True, 'lock_wait_observed': True, 'failed_migration_restored_schema': True,
      'forward_retry_rows': [[1, 10, 11], [2, 20, 21], [3, 30, 31]], 'reopened': True},
     'failed_migration_restored_schema'),
    ('wire', ['S09-P1'], wire,
     {'first': 201, 'valid_retry': 200, 'changed_wire_bytes': 401,
      'different_payload_replay': 409, 'effects': 1}, 'changed_wire_bytes'),
    ('consumer', ['S09-P1'], consumer,
     {'http_status': 200, 'old_integer_consumer_rejected': True, 'strict_enum_rejected': True,
      'tolerant_unknown': {'unknown': 'future_value'}}, 'old_integer_consumer_rejected'),
    ('resource_auth', ['RB-S13-2'], resource_auth,
     {'owner_status': 200, 'foreign_status': 403, 'foreign_exposure': False}, 'foreign_exposure'),
    ('destinations', ['RB-S13-1'], destinations,
     {'direct': 'ok', 'redirect': 'denied', 'rebind_pinned': 'ok',
      'forbidden_hits': 0, 'allowed_hits': 3}, 'forbidden_hits'),
    ('token_rotation', ['RB-S14-1'], token_rotation,
     {'current_valid': True, 'unknown_rejected': True, 'algorithm_downgrade_rejected': True,
      'new_authorized_key_valid': True, 'invalid_during_issuer_failure_rejected': True,
      'known_cached_valid_during_failure': True, 'refreshes': 1}, 'algorithm_downgrade_rejected'),
]


LIMITATIONS = [
    'Trusted fixture implementation checks only; no candidate/agent performance or certification.',
    'SQLite engine observed, not application PostgreSQL/SQLServer or distributed datastore proof.',
    'Three migration rows are a declared tiny dataset, not production capacity or general lock scheduling.',
    'Loopback ephemeral-port policy and injected resolver changes, not general OS DNS/network SSRF isolation.',
    'HS256 compact JWT fixture uses actual HMAC; no OIDC discovery, RS256/JWKS vendor or live issuer proof.',
    'Fixture tenant header is a supplied trusted identity for resource authorization, not authentication proof.',
    'No provider, production, browser/assistive technology, SME/private holdout or complete professional qualification.',
]


def preview():
    return {'schema_version': 1, 'execution_requested': False,
            'cases': [{'id': name, 'items': items, 'positive_and_faulty_variants': 2}
                      for name, items, _, _, _ in CASES], 'limitations': LIMITATIONS}


def run(destination, invocation=None):
    destination = Path(destination).absolute()
    # Output is new; reject existing links/reparse ancestors before any mutation.
    for parent in [destination, *destination.parents]:
        if parent.exists():
            metadata = parent.lstat()
            if parent.is_symlink() or getattr(metadata, 'st_file_attributes', 0) & 0x400:
                raise ValueError('Output path cannot traverse a link/reparse point')
    if destination.exists() or destination == ROOT or ROOT in destination.parents:
        raise ValueError('Use a new output directory outside source checkout')
    destination.mkdir(parents=True)
    data = _data()
    receipts = []
    started = time.monotonic()
    for name, items, function, expected, discriminator in CASES:
        receipt = {'id': name, 'items': items, 'status': 'ERROR', 'checks': []}
        for broken in (False, True):
            variant = 'faulty' if broken else 'positive'
            begin = time.monotonic()
            try:
                with tempfile.TemporaryDirectory(prefix=name+'-', dir=destination) as scratch:
                    folder = Path(scratch)
                    actual = function(broken, folder, data)
                    for db in folder.glob('*.sqlite'):
                        shutil.copyfile(db, destination/(name+'-'+variant+'.sqlite'))
                    for measurement in folder.glob('*.json'):
                        shutil.copyfile(measurement, destination/(name+'-'+variant+'-'+measurement.name))
                passed = actual == expected if not broken else actual[discriminator] != expected[discriminator]
                row = {'variant': variant, 'status': 'PASSED' if passed else 'FAILED',
                       'observed': actual, 'expected_positive': expected,
                       'specific_discriminator': discriminator, 'exception': None}
            except Exception as exc:
                row = {'variant': variant, 'status': 'ERROR', 'error_type': type(exc).__name__,
                       'reason': str(exc), 'exception': True}
            row['elapsed_ms'] = (time.monotonic()-begin)*1000
            receipt['checks'].append(row)
        receipt['status'] = 'PASSED' if all(r['status'] == 'PASSED' for r in receipt['checks']) else 'FAILED'
        receipts.append(receipt)
    artifacts = {p.name: _sha(p) for p in destination.iterdir() if p.is_file()}
    report = {'schema_version': 1, 'evidence_class': 'TRUSTED_LOCAL_SERVICE_SUBSCOPES',
              'execution_requested': True, 'created_at': dt.datetime.now(dt.timezone.utc).isoformat(),
              'invocation_argv': invocation,
              'execution_method': 'Trusted in-process stdlib functions; no candidate code or subprocesses.',
              'environment': {'python': platform.python_version(), 'sqlite': sqlite3.sqlite_version,
                              'sqlite_isolation': 'explicit BEGIN IMMEDIATE; transactional rollback/commit',
                              'os': platform.system(), 'http': 'stdlib http.server/http.client; numeric loopback only'},
              'harness_sha256': _sha(Path(__file__)), 'fixture_sha256': _sha(FIXTURE),
              'elapsed_seconds': time.monotonic()-started, 'cases': receipts,
              'all_passed': all(r['status'] == 'PASSED' for r in receipts),
              'artifact_sha256': artifacts, 'cleanup': 'Scratch directories removed and servers/threads joined before report.',
              'professional_qualification': 'NOT_EVALUATED', 'limitations': LIMITATIONS}
    (destination/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args(argv)
    if args.run and args.out is None:
        parser.error('--run requires a new --out directory outside source checkout')
    report = run(args.out, invocation=list(sys.orig_argv)) if args.run else preview()
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if not args.run or report['all_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
