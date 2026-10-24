"""A single bounded DB thread; never owns network sockets or activates grants."""
import concurrent.futures
import json
import math
import queue
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from .protocol import Refused, encode

STATES = ('PENDING', 'ACTIVE', 'DENIED', 'CANCELLED', 'EXPIRED', 'REVOKED', 'INVALIDATED')

def clock():
    return time.clock_gettime(time.CLOCK_BOOTTIME) if hasattr(time, 'CLOCK_BOOTTIME') else time.monotonic()

class Store:
    def __init__(self, path, cfg, barriers=None):
        self.path, self.cfg = path, cfg
        self.barriers = Path(barriers) if barriers else None
        self.queue = queue.Queue(cfg['db_queue'])
        self.thread = threading.Thread(target=self.run, name='grantweft-db', daemon=False)
        self.thread.start()

    def submit(self, principal, op):
        f = concurrent.futures.Future()
        try:
            self.queue.put_nowait((principal, op, f))
        except queue.Full:
            raise Refused('DB_QUEUE_FULL')
        return f

    def hold(self, name):
        if not self.barriers:
            return
        marker = self.barriers / ('hold-' + name)
        if marker.exists():
            (self.barriers / ('entered-' + name)).write_text('entered')
            until = time.monotonic() + 15
            while marker.exists():
                if time.monotonic() > until:
                    raise OSError('TEST_BARRIER_TIMEOUT')
                time.sleep(.01)
        if (self.barriers / ('fail-' + name)).exists():
            raise sqlite3.OperationalError('injected storage write failure')

    def run(self):
        db = None
        try:
            while True:
                item = self.queue.get()
                if item is None:
                    break
                principal, op, f = item
                try:
                    if db is None:
                        db = sqlite3.connect(self.path, timeout=.2)
                        db.row_factory = sqlite3.Row
                        db.execute('pragma journal_mode=DELETE')
                        db.execute('pragma synchronous=FULL')
                        db.execute('pragma foreign_keys=ON')
                        db.executescript('''
                        create table if not exists meta(epoch integer not null);
                        create table if not exists grants(id text primary key, owner text not null,
                         service text not null, state text not null, duration real not null,
                         deadline real not null, revision integer not null, epoch integer not null);
                        create table if not exists ops(principal text not null, id text not null,
                         payload text not null, result text not null, primary key(principal,id));
                        create table if not exists events(seq integer primary key, value text not null);
                        ''')
                    result = self.execute(db, principal, op)
                    f.set_result(result)
                except BaseException as exc:
                    if db is not None:
                        db.rollback()
                    f.set_exception(exc)
        finally:
            if db is not None:
                db.close()

    def execute(self, db, principal, op):
        if op.get('action') == '_boot':
            if db.execute('pragma quick_check').fetchall()[0][0] != 'ok':
                raise Refused('JOURNAL_INVALID')
            rows = db.execute('select * from grants').fetchall()
            for r in rows:
                if (r['state'] not in STATES or r['owner'] not in self.cfg['principals']
                    or r['service'] != self.cfg['service']['id'] or not math.isfinite(r['deadline'])
                    or not 0 < r['duration'] <= 900 or r['revision'] < 1):
                    raise Refused('JOURNAL_INVALID')
            epochs = db.execute('select epoch from meta').fetchall()
            if len(epochs) > 1 or (epochs and (type(epochs[0][0]) is not int or epochs[0][0] < 1)):
                raise Refused('JOURNAL_INVALID')
            epoch = epochs[0][0] + 1 if epochs else 1
            with db:
                db.execute('delete from meta')
                db.execute('insert into meta values (?)', (epoch,))
                db.execute("update grants set state='INVALIDATED',revision=revision+1 where state in ('PENDING','ACTIVE')")
            return {'epoch': epoch, 'grants': [dict(r) for r in db.execute('select * from grants')], 'ops': [dict(r) for r in db.execute('select * from ops')]}
        if op.get('action') == '_mark':
            self.hold('mark')
            with db:
                changed = db.execute('update grants set state=?,revision=revision+1 where id=? and epoch=? and revision=?',
                           (op['state'], op['grant'], op['epoch'], op['revision']))
                if changed.rowcount!=1:raise Refused('STALE_MARK')
            return True
        payload = encode(op['payload']).decode()
        prior = db.execute('select payload,result from ops where principal=? and id=?', (principal, op['id'])).fetchone()
        if prior:
            if prior['payload'] != payload:
                raise Refused('OP_CONFLICT')
            return {'historical': True, 'result': json.loads(prior['result'])}
        p = op['payload']; action = p['action']
        epoch = db.execute('select epoch from meta').fetchone()[0]
        if p.get('epoch') != epoch:
            raise Refused('STALE_EPOCH')
        for table, limit in [('ops', self.cfg['max_ops']), ('events', self.cfg['max_events'])]:
            if db.execute('select count(*) from ' + table).fetchone()[0] >= limit:
                raise Refused('CATALOG_FULL')
        row = None
        if action != 'request':
            r = db.execute('select * from grants where id=?', (p['grant'],)).fetchone()
            if r is None:
                raise Refused('NOT_FOUND')
            row = dict(r)
            if p.get('revision') != row['revision']:
                raise Refused('STALE_REVISION')
        role = self.cfg['principals'][principal]['role']
        if action == 'request':
            if role != 'requester' or p['service'] != self.cfg['service']['id']:
                raise Refused('FORBIDDEN')
            if db.execute('select count(*) from grants').fetchone()[0] >= self.cfg['max_grants']:
                raise Refused('GRANT_FULL')
            if type(p['duration']) not in (int, float) or not math.isfinite(p['duration']) or not .2 <= p['duration'] <= 900:
                raise Refused('DURATION')
            row = dict(id=op['new_grant'], owner=principal, service=p['service'], state='PENDING',
                       duration=p['duration'], deadline=op['deadline'], revision=1, epoch=epoch)
        elif action in ('approve', 'deny'):
            if role != 'approver' or row['owner'] == principal:
                raise Refused('FORBIDDEN')
            if row['state'] != 'PENDING' or clock() >= row['deadline']:
                raise Refused('STATE_OR_EXPIRED')
            row.update(state='ACTIVE' if action == 'approve' else 'DENIED', revision=row['revision']+1)
            if action == 'approve':
                row['deadline'] = op['deadline']
        elif action in ('revoke', 'cancel'):
            if action == 'revoke' and role != 'approver':
                raise Refused('FORBIDDEN')
            if action == 'cancel' and row['owner'] != principal:
                raise Refused('FORBIDDEN')
            if row['state'] not in ('PENDING', 'ACTIVE'):
                raise Refused('STATE')
            row.update(state='REVOKED' if action == 'revoke' else 'CANCELLED', revision=row['revision']+1)
        else:
            raise Refused('ACTION')
        self.hold(action)
        result = {'grant': row, 'epoch': epoch}
        with db:
            columns = ('id','owner','service','state','duration','deadline','revision','epoch')
            db.execute('insert or replace into grants values (?,?,?,?,?,?,?,?)', tuple(row[k] for k in columns))
            db.execute('insert into ops values (?,?,?,?)', (principal, op['id'], payload, encode(result).decode()))
            db.execute('insert into events(value) values (?)', (encode({'principal':principal,'operation':op['id'],'action':action,'grant':row}).decode(),))
        return {'historical': False, 'result': result}

    def close(self):
        self.queue.put(None)
        self.thread.join()
