import concurrent.futures
import contextlib
import json
from pathlib import Path
import os
import signal
import socket
import sqlite3
import ssl
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from grantweft.client import send,receive,connect
from grantweft.protocol import DATA,EOF,CLOSE,OPEN,HEADER,Refused,encode
from support import Harness,Backend,certs

class GatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='gw-pki-');cls.pki=certs(cls.tmp.name)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def setUp(self):self.items=[]
    def tearDown(self):
        for h in reversed(self.items):h.close()
    def h(self,**kw):
        h=Harness(self.pki,**kw);self.items.append(h);return h
    def denied(self,h,g,who='a'):
        with self.assertRaisesRegex(Refused,'NO_ACCESS'):h.access(g,who)
    def ended(self,s):
        s.settimeout(1)
        try:
            while True:
                k,b=receive(s)
                self.assertNotEqual(k,DATA)
        except TimeoutError:
            self.fail('CLOSE_NOT_OBSERVED: socket timeout is not termination')
        except (EOFError,ConnectionResetError,ssl.SSLEOFError,ssl.SSLZeroReturnError):pass
        finally:s.close()
    def test_real_mtls_approval_payload_and_identity(self):
        h=self.h();g=h.request();self.denied(h,g)
        with self.assertRaisesRegex(Refused,'FORBIDDEN'):h.mutate('a','approve',g)
        g=h.approve(g);self.denied(h,g,'b')
        with h.access(g) as s:
            payload=b'ordered-real-payload'*400
            send(s,DATA,payload);k,b=receive(s);self.assertEqual((k,b),(DATA,payload))
        self.assertEqual(bytes(h.backend.received),payload)
    def test_unknown_and_missing_client_certificate(self):
        h=self.h()
        with self.assertRaisesRegex(Refused,'IDENTITY'):h.call('unknown',{'action':'status'})
        ctx=ssl.create_default_context(cafile=str(self.pki/'ca.pem'))
        with socket.create_connection(('127.0.0.1',h.ready['ports']['control'])) as raw:
            with self.assertRaises((ssl.SSLError,EOFError,ConnectionResetError)):
                with ctx.wrap_socket(raw,server_hostname='127.0.0.1') as s:
                    s.sendall(HEADER.pack(OPEN,2)+b'{}')
                    if not s.recv(10):raise EOFError('TLS rejected without client certificate')
    def test_revoke_closes_live_and_idle_and_new_sessions(self):
        h=self.h();g=h.approve(h.request());a=h.access(g);b=h.access(g)
        send(a,DATA,b'before');self.assertEqual(receive(a),(DATA,b'before'))
        result=h.mutate('approver','revoke',g);self.assertEqual(result['cleanup'],'COMPLETE')
        self.ended(a);self.ended(b);self.denied(h,g)
        self.assertEqual(h.status()['sessions'],0)
    def test_expiry_closes_session_and_prevents_reconnect(self):
        h=self.h();g=h.approve(h.request(duration=.4));s=h.access(g)
        time.sleep(.5);self.ended(s);self.denied(h,g)
        self.assertEqual(h.status()['grants'][0]['access'],'DENIED')
    def test_application_half_close_preserves_reply(self):
        backend=Backend(mode='half');h=self.h(backend=backend)
        try:
            g=h.approve(h.request())
            with h.access(g) as s:
                send(s,DATA,b'half-close');send(s,EOF)
                self.assertEqual(receive(s),(DATA,b'after-eof:half-close'))
                self.assertEqual(receive(s),(EOF,b''));send(s,CLOSE)
            h.wait(lambda:h.status()['sessions']==0)
        finally:backend.close()
    def test_malformed_frame_and_data_after_eof(self):
        h=self.h();g=h.approve(h.request())
        for blob in [HEADER.pack(DATA,16385),HEADER.pack(99,0),HEADER.pack(EOF,1)+b'x',HEADER.pack(EOF,0)+HEADER.pack(DATA,1)+b'x']:
            with h.access(g) as s:
                s.sendall(blob);self.ended(s)
        self.assertEqual(bytes(h.backend.received),b'')
    def test_idempotent_history_after_revoke_and_restart(self):
        h=self.h();g=h.request()
        p={'action':'approve','operation':str(uuid.uuid4()),'epoch':h.ready['epoch'],'grant':g['id'],'revision':g['revision']}
        result=h.call('approver',p);g=result['original_result']['grant']
        h.mutate('approver','revoke',g);h.stop(kill=True);h.start()
        retry=h.call('approver',p);self.assertTrue(retry['historical']);self.denied(h,g)
        self.assertEqual(retry['original_result'],result['original_result'])
        with self.assertRaises(Refused):h.call('approver',p|{'revision':99})
        with self.assertRaises(Refused):h.call('b',p)
    def test_crash_restart_invalidates_old_grants_and_fences_operations(self):
        h=self.h();pending=h.request('b');active=h.approve(h.request());s=h.access(active)
        h.stop(kill=True)
        before=(h.store/'catalog.sqlite').read_bytes()
        self.assertTrue(before)
        h.start();self.ended(s)
        self.assertGreater(h.ready['epoch'],active['epoch'])
        states={g['id']:g['state'] for g in h.status()['grants']}
        self.assertEqual(states[active['id']],'INVALIDATED');self.assertEqual(states[pending['id']],'INVALIDATED')
        self.denied(h,active)
        with self.assertRaises(Refused):h.mutate('approver','revoke',active,epoch=active['epoch'])
        new=h.approve(h.request())
        with h.access(new) as s:send(s,DATA,b'fresh');self.assertEqual(receive(s),(DATA,b'fresh'))
    def test_old_revision_cannot_revoke_new_state(self):
        h=self.h();old=h.request();new=h.approve(old)
        with self.assertRaisesRegex(Refused,'STALE_REVISION'):h.mutate('approver','revoke',old)
        with h.access(new) as s:send(s,DATA,b'ok');self.assertEqual(receive(s),(DATA,b'ok'))
    def test_slow_commit_does_not_start_new_ttl(self):
        h=self.h();g=h.request(duration=.3);hold=h.barriers/'hold-approve';hold.touch()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future=pool.submit(h.mutate,'approver','approve',g)
            h.wait(lambda:(h.barriers/'entered-approve').exists());self.denied(h,g)
            time.sleep(.45);hold.unlink();result=future.result(timeout=3)
        self.assertFalse(result['ok']);self.denied(h,g)
        self.assertEqual(h.status()['grants'][0]['state'],'EXPIRED')
    def test_revoke_during_delayed_approval_cannot_reopen(self):
        h=self.h();g=h.request();hold=h.barriers/'hold-approve';hold.touch()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            approval=pool.submit(h.mutate,'approver','approve',g)
            h.wait(lambda:(h.barriers/'entered-approve').exists())
            revoke=pool.submit(h.mutate,'approver','revoke',g)
            h.wait(lambda:h.status()['grants'][0]['access']=='DENIED' and h.status()['grants'][0]['persistence']=='PENDING')
            hold.unlink()
            for f in (approval,revoke):
                with contextlib.suppress(Refused):f.result(timeout=4)
        self.denied(h,g)
        # A revision conflict in this narrow exploration conservatively retires authority.
        self.assertTrue(h.status()['degraded'])
    def test_storage_failure_stops_existing_and_never_approves(self):
        h=self.h();live=h.approve(h.request());s=h.access(live);g=h.request('b')
        (h.barriers/'fail-approve').touch()
        with self.assertRaisesRegex(Refused,'STORAGE_FAILED'):h.mutate('approver','approve',g)
        self.ended(s);self.denied(h,live);self.assertTrue(h.status()['degraded'])
    def test_session_capacity_preserves_control_revoke(self):
        h=self.h(max_sessions=2,per_principal=2);g=h.approve(h.request());a=h.access(g);b=h.access(g)
        with self.assertRaisesRegex(Refused,'SESSION_FULL'):h.access(g)
        start=time.monotonic();r=h.mutate('approver','revoke',g)
        self.assertEqual(r['cleanup'],'COMPLETE');self.assertLess(time.monotonic()-start,2)
        self.ended(a);self.ended(b)
    def test_raw_handshake_capacity_preserves_control(self):
        h=self.h(data_connections=2);sockets=[socket.create_connection(('127.0.0.1',h.ready['ports']['data'])) for _ in range(5)]
        try:
            self.assertTrue(h.status()['ok']);time.sleep(2.4)
            self.assertEqual(h.status()['sessions'],0)
        finally:
            for s in sockets:s.close()
    def test_catalog_capacity_does_not_delete_old_grants(self):
        h=self.h(max_grants=2);a=h.request();b=h.request('b')
        with self.assertRaisesRegex(Refused,'GRANT_FULL'):h.request()
        self.assertEqual({g['id'] for g in h.status()['grants']},{a['id'],b['id']})
        self.assertFalse(h.status()['degraded'])
    def test_process_pause_crosses_ttl_no_fresh_transfer_after_resume(self):
        h=self.h();g=h.approve(h.request(duration=.35));s=h.access(g)
        os.kill(h.proc.pid,signal.SIGSTOP);time.sleep(.5);os.kill(h.proc.pid,signal.SIGCONT)
        with contextlib.suppress(OSError):send(s,DATA,b'must-not-forward')
        self.ended(s);self.assertNotIn(b'must-not-forward',bytes(h.backend.received))
    def test_second_process_cannot_take_lock_or_recover(self):
        h=self.h();before=(h.store/'catalog.sqlite').read_bytes()
        p=subprocess.run([sys.executable,'-m','grantweft.gateway','--config',str(h.config),'--root',str(h.store)],capture_output=True,timeout=4)
        self.assertNotEqual(p.returncode,0);self.assertEqual(before,(h.store/'catalog.sqlite').read_bytes());self.assertTrue(h.status()['ok'])
    def test_truncated_frame_is_not_payload(self):
        h=self.h();g=h.approve(h.request())
        with h.access(g) as s:s.sendall(HEADER.pack(DATA,10)+b'few')
        time.sleep(.1);self.assertEqual(bytes(h.backend.received),b'')
    def test_slow_db_does_not_block_live_expiry(self):
        h=self.h();g=h.approve(h.request(duration=.35));s=h.access(g)
        hold=h.barriers/'hold-request';hold.touch()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            other=pool.submit(h.request,'b')
            h.wait(lambda:(h.barriers/'entered-request').exists())
            time.sleep(.5);self.ended(s)
            self.assertEqual(next(x for x in h.status()['grants'] if x['id']==g['id'])['access'],'DENIED')
            hold.unlink();other.result(timeout=3)
    def test_bounded_db_queue_does_not_block_revoke_fence(self):
        h=self.h(db_queue=1,control_connections=12);g=h.approve(h.request());s=h.access(g)
        hold=h.barriers/'hold-request';hold.touch()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            first=pool.submit(h.request,'b');h.wait(lambda:(h.barriers/'entered-request').exists())
            second=pool.submit(h.request,'a');h.wait(lambda:h.status()['db_queued']==1)
            with self.assertRaisesRegex(Refused,'DB_QUEUE_FULL'):h.request()
            with self.assertRaisesRegex(Refused,'DB_QUEUE_FULL'):h.mutate('approver','revoke',g)
            self.ended(s);self.assertTrue(h.status()['degraded']);hold.unlink()
            for f in (first,second):
                with contextlib.suppress(Refused):f.result(timeout=4)
        self.denied(h,g)
    def test_db_timeout_late_completion_cannot_reactivate(self):
        h=self.h(db_seconds=.3);g=h.request();hold=h.barriers/'hold-approve';hold.touch()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            f=pool.submit(h.mutate,'approver','approve',g)
            h.wait(lambda:(h.barriers/'entered-approve').exists())
            with self.assertRaisesRegex(Refused,'STORAGE_FAILED'):f.result(timeout=2)
            self.assertTrue(h.status()['degraded']);hold.unlink();time.sleep(.15);self.denied(h,g)
        h.stop(kill=True);h.start();self.denied(h,g)
    def test_slow_consumer_revoke_discards_unsent_data(self):
        backend=Backend(mode='slow');h=self.h(backend=backend)
        try:
            g=h.approve(h.request());s=h.access(g)
            for _ in range(12):send(s,DATA,b'x'*16384)
            r=h.mutate('approver','revoke',g);self.assertEqual(r['cleanup'],'COMPLETE')
            with contextlib.suppress(OSError):send(s,DATA,b'AFTER-REVOKE-NONCE')
            self.ended(s);time.sleep(.15)
            self.assertNotIn(b'AFTER-REVOKE-NONCE',bytes(backend.received))
        finally:backend.close()
    def test_deny_cancel_and_request_expiry(self):
        h=self.h(pending_seconds=.3);a=h.request();b=h.request('b')
        h.mutate('approver','deny',a);h.mutate('b','cancel',b)
        c=h.request();time.sleep(.4)
        with self.assertRaises(Refused):h.approve(c)
        self.assertEqual({g['state'] for g in h.status()['grants']},{'DENIED','CANCELLED','EXPIRED'})
    def test_invalid_duration_and_duplicate_json_are_rejected(self):
        h=self.h()
        for value in (True,0,901,float('inf')):
            with self.assertRaises((Refused,ValueError)):h.request(duration=value)
        with connect('127.0.0.1',h.ready['ports']['control'],*h.credentials()) as s:
            send(s,OPEN,b'{"action":"status","action":"request"}')
            k,b=receive(s);self.assertEqual(k,6);self.assertIn(b'DUPLICATE_KEY',b)
    def test_delayed_connected_session_cannot_survive_revoke(self):
        h=self.h();g=h.approve(h.request());hold=h.barriers/'hold-connect';hold.touch()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            f=pool.submit(h.access,g);h.wait(lambda:(h.barriers/'entered-connect').exists())
            self.assertEqual(h.status()['sessions'],1)
            h.mutate('approver','revoke',g);hold.unlink()
            with self.assertRaises((Refused,EOFError,ConnectionResetError,ssl.SSLError)):f.result(timeout=3)
        self.assertEqual(h.status()['sessions'],0);self.assertEqual(bytes(h.backend.received),b'')
        fresh=h.approve(h.request())
        with h.access(fresh) as s:send(s,DATA,b'new-session');self.assertEqual(receive(s),(DATA,b'new-session'))
    def test_history_result_is_stable_after_expiry_and_restart(self):
        h=self.h();g=h.request(duration=.25)
        p={'action':'approve','operation':str(uuid.uuid4()),'epoch':h.ready['epoch'],'grant':g['id'],'revision':g['revision']}
        initial=h.call('approver',p)['original_result']
        time.sleep(.4)
        self.assertEqual(h.call('approver',p)['original_result'],initial)
        h.stop(kill=True);h.start()
        self.assertEqual(h.call('approver',p)['original_result'],initial)
    def test_observed_backpressure_then_revoke_stops_transfer(self):
        backend=Backend(mode='blocked');h=self.h(backend=backend)
        try:
            g=h.approve(h.request(duration=10));s=h.access(g)
            def flood():
                s.settimeout(2)
                try:
                    for _ in range(1024):send(s,DATA,b'x'*16384)
                except OSError:pass
            with concurrent.futures.ThreadPoolExecutor() as pool:
                upload=pool.submit(flood)
                h.wait(lambda:h.status()['facts']['backpressure_events']>0,seconds=3)
                r=h.mutate('approver','revoke',g)
                self.assertEqual(r['cleanup'],'COMPLETE')
                self.ended(s);upload.result(timeout=3)
            self.assertEqual(h.status()['sessions'],0)
        finally:backend.close()
    def test_slow_approval_history_retains_original_commit(self):
        h=self.h();g=h.request(duration=.25);hold=h.barriers/'hold-approve';hold.touch()
        p={'action':'approve','operation':str(uuid.uuid4()),'epoch':h.ready['epoch'],'grant':g['id'],'revision':g['revision']}
        with concurrent.futures.ThreadPoolExecutor() as pool:
            f=pool.submit(h.call,'approver',p);h.wait(lambda:(h.barriers/'entered-approve').exists())
            time.sleep(.4);hold.unlink();result=f.result(timeout=3)
        self.assertFalse(result['ok']);original=result['original_result']
        self.assertEqual(original['grant']['state'],'ACTIVE')
        self.assertEqual(h.call('approver',p)['original_result'],original)
        h.stop(kill=True);h.start()
        self.assertEqual(h.call('approver',p)['original_result'],original)
    def test_full_ops_and_events_still_stop_access_and_recover_with_limits(self):
        for limit in ('max_ops','max_events'):
            with self.subTest(limit=limit):
                h=self.h(**{limit:2});g=h.approve(h.request());s=h.access(g)
                snapshot=(h.store/'catalog.sqlite').read_bytes()
                with self.assertRaisesRegex(Refused,'CATALOG_FULL'):h.request('b')
                self.assertEqual(snapshot,(h.store/'catalog.sqlite').read_bytes())
                self.assertTrue(h.status()['capacity'][limit[4:]]['full'])
                with self.assertRaisesRegex(Refused,'CATALOG_FULL'):h.mutate('approver','revoke',g)
                self.ended(s);self.denied(h,g)
                status=h.status();self.assertTrue(status['degraded'])
                self.assertEqual(status['failure']['code'],'CATALOG_FULL')
                self.assertEqual(status['recovery']['method'],'REPAIR_THEN_RESTART')
                self.assertFalse(status['capacity']['ops']['exact'])
                h.stop();h.cfg[limit]=8;h.config.write_text(json.dumps(h.cfg));h.start()
                self.denied(h,g)
                with self.assertRaisesRegex(Refused,'STALE_EPOCH'):h.mutate('approver','revoke',g,epoch=g['epoch'])
                fresh=h.approve(h.request())
                with h.access(fresh) as session:
                    send(session,DATA,b'repaired');self.assertEqual(receive(session),(DATA,b'repaired'))
                self.assertEqual(h.status()['capacity']['grants']['used'],2)
    def test_grant_full_preserves_revoke_and_expiry_without_gc(self):
        h=self.h(max_grants=1);g=h.approve(h.request(duration=.3));s=h.access(g)
        with self.assertRaisesRegex(Refused,'GRANT_FULL'):h.request('b')
        time.sleep(.4);self.ended(s);self.denied(h,g)
        self.assertFalse(h.status()['degraded'])
        self.assertEqual(h.status()['capacity']['grants']['used'],1)
        with self.assertRaisesRegex(Refused,'GRANT_FULL'):h.request()
        h2=self.h(max_grants=1);g2=h2.approve(h2.request());s2=h2.access(g2)
        self.assertEqual(h2.mutate('approver','revoke',g2)['cleanup'],'COMPLETE');self.ended(s2)
    def test_catalog_full_expiry_does_not_need_new_audit_slot(self):
        h=self.h(max_ops=2,max_events=2);g=h.approve(h.request(duration=.25));s=h.access(g)
        time.sleep(.4);self.ended(s);self.denied(h,g)
        state=h.status();self.assertFalse(state['degraded'])
        self.assertEqual(state['grants'][0]['state'],'EXPIRED')
        self.assertEqual(state['capacity']['events']['used'],2)
    def test_storage_repair_requires_restart_and_preserves_history(self):
        h=self.h();g=h.request()
        approval={'action':'approve','operation':str(uuid.uuid4()),'epoch':h.ready['epoch'],'grant':g['id'],'revision':g['revision']}
        original=h.call('approver',approval)['original_result'];live=original['grant'];s=h.access(live)
        fail=h.barriers/'fail-revoke';fail.touch()
        with self.assertRaisesRegex(Refused,'STORAGE_FAILED'):h.mutate('approver','revoke',live)
        self.ended(s);fail.unlink()
        self.assertEqual(h.status()['failure']['action'],'revoke')
        with self.assertRaisesRegex(Refused,'DEGRADED'):h.request()
        self.denied(h,live);h.stop();h.start();self.denied(h,live)
        replay=h.call('approver',approval)
        self.assertTrue(replay['historical']);self.assertEqual(replay['original_result'],original)
        self.assertEqual(replay['current']['grants'][0]['access'],'DENIED')
        with self.assertRaisesRegex(Refused,'STALE_EPOCH'):h.call('approver',approval|{'operation':str(uuid.uuid4())})
        self.assertFalse(h.status()['degraded'])
    def test_slow_commit_after_retirement_stays_denied_through_repair(self):
        h=self.h(db_seconds=.3);live=h.approve(h.request());s=h.access(live);pending=h.request('b')
        hold=h.barriers/'hold-approve';hold.touch()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            approval={'action':'approve','operation':str(uuid.uuid4()),'epoch':h.ready['epoch'],'grant':pending['id'],'revision':pending['revision']}
            f=pool.submit(h.call,'approver',approval)
            h.wait(lambda:(h.barriers/'entered-approve').exists())
            with self.assertRaisesRegex(Refused,'STORAGE_FAILED'):f.result(timeout=2)
            self.ended(s);self.denied(h,pending,'b');hold.unlink()
            def committed():
                with sqlite3.connect(h.store/'catalog.sqlite') as db:
                    return db.execute('select state from grants where id=?',(pending['id'],)).fetchone()[0]=='ACTIVE'
            h.wait(committed)
        self.denied(h,pending,'b');self.denied(h,live)
        with self.assertRaisesRegex(Refused,'DEGRADED'):h.request()
        h.stop();h.start();self.denied(h,pending,'b');self.denied(h,live)
        self.assertTrue(all(g['state']=='INVALIDATED' for g in h.status()['grants']))
        replay=h.call('approver',approval);self.assertTrue(replay['historical'])
        self.assertEqual(replay['original_result']['grant']['state'],'ACTIVE')
        self.denied(h,pending,'b')
    def test_expiry_write_failure_degrades_and_repair_does_not_revive(self):
        h=self.h();g=h.approve(h.request(duration=.25));s=h.access(g)
        fail=h.barriers/'fail-mark';fail.touch()
        h.wait(lambda:h.status()['degraded']);self.ended(s);self.denied(h,g)
        self.assertEqual(h.status()['failure']['code'],'EXPIRY_PERSIST_FAILED')
        fail.unlink();h.stop();h.start();self.denied(h,g)
        self.assertEqual(h.status()['grants'][0]['state'],'INVALIDATED')
    def test_sqlite_full_closes_live_access_and_recovers_with_page_budget(self):
        h=self.h(max_store_pages=8);g=h.approve(h.request(duration=20));s=h.access(g)
        for _ in range(64):
            try:h.request('b')
            except Refused as exc:
                self.assertEqual(str(exc),'STORAGE_FAILED');break
        else:self.fail('SQLite page budget was not exercised')
        self.ended(s);self.denied(h,g)
        state=h.status();self.assertTrue(state['degraded'])
        self.assertEqual(state['failure']['sqlite_code'],'SQLITE_FULL')
        h.stop();h.cfg['max_store_pages']=64;h.config.write_text(json.dumps(h.cfg));h.start()
        self.denied(h,g);fresh=h.approve(h.request())
        with h.access(fresh) as session:
            send(session,DATA,b'new-page-budget');self.assertEqual(receive(session),(DATA,b'new-page-budget'))
    def test_duplicate_identity_exits_before_creating_store_or_worker(self):
        with tempfile.TemporaryDirectory(prefix='gw-invalid-config-') as base:
            root=Path(base)/'store';config=Path(base)/'config.json'
            config.write_text(json.dumps({'service':{'id':'demo','host':'127.0.0.1','port':9000},
                'principals':{'a':{'sha256':'a'*64,'role':'requester'},
                              'approver':{'sha256':'a'*64,'role':'approver'}}}))
            p=subprocess.run([sys.executable,'-m','grantweft.gateway','--config',str(config),'--root',str(root)],capture_output=True,text=True,timeout=2)
            self.assertNotEqual(p.returncode,0);self.assertIn('DUPLICATE_IDENTITY',p.stderr)
            self.assertFalse(root.exists(),'Invalid config must not create state/worker')
