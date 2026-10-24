"""Socket authority owns every transport; DB completion is never authority."""
import argparse
import asyncio
import contextlib
import copy
import fcntl
import hashlib
import json
import math
import os
import signal
import socket
import ssl
import time
import uuid
from pathlib import Path
from .protocol import DATA, EOF, CLOSE, OPEN, OK, ERROR, MAX_FRAME, Refused, abort, decode, encode, frame, read_frame
from .store import Store, clock

DEFAULTS = dict(db_queue=8, max_ops=256, max_events=256, max_grants=64,
                max_store_pages=1024, max_sessions=16, per_principal=4, data_connections=20,
                control_connections=8, handshake_seconds=2, db_seconds=2,
                pending_seconds=60, frame_seconds=10)

class Gateway:
    def __init__(self, cfg, root, barriers=None):
        self.cfg = DEFAULTS | cfg
        for key,value in self.cfg.items():
            if key in DEFAULTS and (type(value) not in (int,float) or not math.isfinite(value) or value<=0):
                raise Refused('CONFIG_LIMIT')
        for key in ('db_queue','max_ops','max_events','max_grants','max_store_pages','max_sessions','per_principal','data_connections','control_connections'):
            if type(self.cfg[key]) is not int or self.cfg[key]>4096:raise Refused('CONFIG_LIMIT')
        if self.cfg['max_store_pages']<8:raise Refused('CONFIG_LIMIT')
        service=self.cfg['service']
        import ipaddress
        ipaddress.ip_address(service['host'])
        if not isinstance(service['id'],str) or not 1<=len(service['id'])<=64 or type(service['port']) is not int or not 1<=service['port']<=65535:raise Refused('CONFIG_SERVICE')
        for name,identity in self.cfg['principals'].items():
            if not 1<=len(name)<=64 or identity['role'] not in ('requester','approver') or len(identity['sha256'])!=64:raise Refused('CONFIG_IDENTITY')
        self.root = Path(root).resolve(); self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.root.stat().st_mode & 0o077:
            raise Refused('STORE_PERMISSIONS')
        self.lock = os.open(self.root/'writer.lock', os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            os.close(self.lock); raise
        self.barriers=Path(barriers) if barriers else None
        self.store = Store(str(self.root/'catalog.sqlite'), self.cfg, barriers)
        self.grants = {}; self.ops = {}; self.inflight = {}; self.denied = set()
        self.sessions = {}; self.connections = {'data':set(), 'control':set()}
        self.degraded = False; self.failure = None; self.catalog = {}; self.generation = 1; self.ready = False
        self.servers = []; self.tasks = set(); self.facts = {'admitted':0,'refused':0,'closed':0,'forwarded_bytes':0,'backpressure_events':0}
        self.fingerprint = {v['sha256']:k for k,v in self.cfg['principals'].items()}
        if len(self.fingerprint) != len(self.cfg['principals']):
            raise Refused('DUPLICATE_IDENTITY')

    def ssl_context(self):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(self.cfg['cert'], self.cfg['key'])
        ctx.load_verify_locations(self.cfg['ca']); ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.options |= ssl.OP_NO_TICKET
        if hasattr(ctx, 'num_tickets'):
            ctx.num_tickets = 0
        return ctx

    def track(self, coro):
        t = asyncio.create_task(coro); self.tasks.add(t); t.add_done_callback(self.tasks.discard)
        return t

    async def db(self, principal, op):
        f = self.store.submit(principal, op)
        af = asyncio.wrap_future(f)
        # Retrieving a late failure does not make the result authoritative.
        af.add_done_callback(lambda x: None if x.cancelled() else x.exception())
        return await asyncio.wait_for(asyncio.shield(af), self.cfg['db_seconds'])

    async def start(self):
        state = await self.db('', {'action':'_boot'})
        self.catalog = state['counts']
        self.epoch = state['epoch']; self.grants = {r['id']:r for r in state['grants']}
        self.ops = {(r['principal'],r['id']):(r['payload'],json.loads(r['result'])) for r in state['ops']}
        ctx = self.ssl_context()
        for kind in ('control','data'):
            spec = self.cfg[kind]
            # Count raw accepts before TLS; start_server(ssl=...) callbacks alone
            # do not bound handshakes in progress.
            srv = await asyncio.start_server(lambda r,w,k=kind:self.accept(r,w,k,ctx), spec['host'], spec['port'], limit=MAX_FRAME)
            self.servers.append(srv)
        self.ready = True
        self.track(self.expirer())
        ports = {k:s.sockets[0].getsockname()[1] for k,s in zip(('control','data'),self.servers)}
        (self.root/'ready.json').write_text(json.dumps({'epoch':self.epoch,'ports':ports,'pid':os.getpid()}))

    def accept(self, reader, writer, kind, ctx):
        if len(self.connections[kind]) >= self.cfg[kind+'_connections'] or not self.ready:
            self.facts['refused'] += 1; abort(writer); return
        self.connections[kind].add(writer)
        self.track(self.serve(reader,writer,kind,ctx))

    async def serve(self, reader, writer, kind, ctx):
        try:
            await asyncio.wait_for(writer.start_tls(ctx,ssl_handshake_timeout=self.cfg['handshake_seconds']),self.cfg['handshake_seconds']+.2)
            cert = writer.get_extra_info('ssl_object').getpeercert(binary_form=True)
            principal = self.fingerprint.get(hashlib.sha256(cert).hexdigest())
            if principal is None:
                raise Refused('IDENTITY')
            if kind == 'control':
                k,b = await read_frame(reader)
                if k != OPEN:
                    raise Refused('CONTROL_FRAME')
                request = decode(b)
                result = await self.command(principal,request)
                frame(writer,OK,encode(result)); await asyncio.wait_for(writer.drain(),1)
            else:
                await self.tunnel(principal, reader, writer)
        except (Exception, asyncio.CancelledError) as exc:
            self.facts['refused'] += 1
            if not isinstance(exc,asyncio.CancelledError):
                with contextlib.suppress(Exception):
                    frame(writer,ERROR,encode({'ok':False,'code':str(exc) if isinstance(exc,Refused) else type(exc).__name__}))
                    await asyncio.wait_for(writer.drain(),.1)
        finally:
            self.connections[kind].discard(writer); abort(writer)

    def visible(self, principal, grant):
        return self.cfg['principals'][principal]['role']=='approver' or grant['owner']==principal

    def active(self, grant):
        return (self.ready and not self.degraded and grant['epoch']==self.epoch and grant['state']=='ACTIVE'
                and grant['id'] not in self.denied and clock()<grant['deadline'])

    def status(self, principal, after=''):
        grants = []
        for g in sorted(self.grants.values(),key=lambda row:row['id']):
            if g['id']>after and self.visible(principal,g):
                grants.append(g | {'access':'ALLOWED' if self.active(g) else 'DENIED',
                                  'persistence':g.get('persistence','COMMITTED'),
                                  'sessions':sum(s['grant']==g['id'] for s in self.sessions.values())})
        total=len(grants);grants=grants[:16]
        return {'ok':True,'epoch':self.epoch,'degraded':self.degraded,'grants':grants,'remaining_after_cursor':total-len(grants),'next_cursor':grants[-1]['id'] if total>len(grants) else None,
                'sessions':sum(self.grants[s['grant']]['owner']==principal or self.cfg['principals'][principal]['role']=='approver' for s in self.sessions.values()),
                'facts':dict(self.facts),'db_queued':self.store.queue.qsize(),
                'health':'DEGRADED' if self.degraded else 'READY',
                'failure':copy.deepcopy(self.failure),
                'recovery':{'required':self.degraded,'method':'REPAIR_THEN_RESTART',
                            'old_grants_survive':False,'online_reset_supported':False},
                'capacity':{name:{'used':self.catalog.get(name,0),'limit':self.cfg['max_'+name],
                                  'full':self.catalog.get(name,0)>=self.cfg['max_'+name],
                                  'exact':not (self.degraded or self.inflight)}
                            for name in ('ops','events','grants')}}

    def fence(self, grant):
        self.denied.add(grant)
        for s in list(self.sessions.values()):
            if s['grant']==grant:
                s['stopped']=True
                abort(s.get('backend')); abort(s['client'])
                task = s.get('task')
                if task is not None and task is not asyncio.current_task():
                    task.cancel()

    def retire(self, code='AUTHORITY_RETIRED', action=None, exc=None):
        if self.failure is None:
            self.failure={'code':code,'action':action,'observed_boottime':clock(),
                          'sqlite_code':getattr(exc,'sqlite_errorname',None)}
        self.degraded = True; self.generation += 1
        for gid in self.grants:
            self.fence(gid)

    async def command(self, principal, req):
        if type(req) is not dict:
            raise Refused('FORMAT')
        action = req.get('action')
        if action=='status':
            if set(req) not in ({'action'},{'action','after'}) or not isinstance(req.get('after',''),str) or len(req.get('after',''))>64:raise Refused('FIELDS')
            return self.status(principal,req.get('after',''))
        keys = {'action','operation','epoch','service','duration'} if action=='request' else {'action','operation','epoch','grant','revision'}
        if set(req)!=keys or action not in ('request','approve','deny','revoke','cancel'):
            raise Refused('FIELDS')
        if not isinstance(req['operation'],str) or len(req['operation'])>64:
            raise Refused('OPERATION')
        uuid.UUID(req['operation'])
        if type(req['epoch']) is not int or (action!='request' and type(req['revision']) is not int):
            raise Refused('AUTHORITY_FORMAT')
        p = {k:v for k,v in req.items() if k!='operation'}
        key = (principal,req['operation']); canonical=encode(p).decode()
        if key in self.ops:
            prior,result = self.ops[key]
            if prior!=canonical:raise Refused('OP_CONFLICT')
            return {'ok':True,'historical':True,'original_result':result,'current':self.status(principal)}
        if key in self.inflight:
            if self.inflight[key]!=canonical: raise Refused('OP_CONFLICT')
            raise Refused('IN_PROGRESS')
        if self.degraded or req['epoch']!=self.epoch:
            raise Refused('DEGRADED' if self.degraded else 'STALE_EPOCH')
        role=self.cfg['principals'][principal]['role']; g=None
        if action=='request':
            if role!='requester' or req['service']!=self.cfg['service']['id']:
                raise Refused('FORBIDDEN')
            d=req['duration']
            if type(d) not in (float,int) or not math.isfinite(d) or not .2<=d<=900:
                raise Refused('DURATION')
        else:
            g=self.grants.get(req['grant'])
            if g is None or not self.visible(principal,g):raise Refused('FORBIDDEN')
            if req['revision']!=g['revision']:raise Refused('STALE_REVISION')
            if action in ('approve','deny','revoke') and role!='approver':raise Refused('FORBIDDEN')
            if action=='cancel' and g['owner']!=principal:raise Refused('FORBIDDEN')
            if action in ('approve','deny') and (g['state']!='PENDING' or g['id'] in self.denied or clock()>=g['deadline']):raise Refused('STATE')
            if action=='cancel' and g['state']!='PENDING':raise Refused('STATE')
            if action=='revoke' and g['state'] not in ('PENDING','ACTIVE'):raise Refused('STATE')
        if action in ('revoke','cancel'):
            self.fence(g['id']); g['persistence']='PENDING'
        token=self.generation
        op={'id':req['operation'],'payload':p,'new_grant':str(uuid.uuid4()),
            'deadline':clock()+(g['duration'] if action=='approve' else self.cfg['pending_seconds'])}
        self.inflight[key]=canonical
        try:
            result=await self.db(principal,op)
            row=copy.deepcopy(result['result']['grant']); self.ops[key]=(canonical,copy.deepcopy(result['result']))
            if not result['historical']:
                self.catalog['ops']+=1; self.catalog['events']+=1
                if action=='request':self.catalog['grants']+=1
            if token!=self.generation or self.degraded:
                raise Refused('RETIRED_COMPLETION')
            # No approval completion can clear a prior expiry/revocation fence.
            if action=='approve' and (row['id'] in self.denied or clock()>=row['deadline']):
                self.fence(row['id']); row['persistence']='PENDING'
                self.grants[row['id']]=row
                await self.mark(row,'EXPIRED' if clock()>=row['deadline'] else 'REVOKED')
                return {'ok':False,'code':'APPROVAL_NOT_ACTIVATED','original_result':result['result'],'current':self.status(principal)}
            self.grants[row['id']]=row
            if action in ('revoke','cancel'):
                # Give cancelled transfer tasks a chance to release owned state.
                for _ in range(20):
                    if not any(s['grant']==row['id'] for s in self.sessions.values()):break
                    await asyncio.sleep(.01)
            return {'ok':True,'historical':result['historical'],'original_result':result['result'],
                    'cleanup':'PENDING' if any(s['grant']==row['id'] for s in self.sessions.values()) else 'COMPLETE',
                    'current':self.status(principal)}
        except Refused as exc:
            if action in ('revoke','cancel'):
                self.retire(str(exc),action); g['persistence']='FAILED'
            raise
        except BaseException as exc:
            self.retire('STORAGE_FAILED',action,exc)
            if g:g['persistence']='FAILED'
            if isinstance(exc,asyncio.CancelledError):raise
            raise Refused('STORAGE_FAILED') from exc
        finally:
            self.inflight.pop(key,None)

    async def mark(self,g,state):
        try:
            await self.db('',{'action':'_mark','grant':g['id'],'epoch':g['epoch'],'revision':g['revision'],'state':state})
            g['state']=state;g['revision']+=1;g['persistence']='COMMITTED'
        except Exception as exc:
            g['persistence']='FAILED';self.retire('EXPIRY_PERSIST_FAILED','expire',exc)

    async def expirer(self):
        marking=set()
        async def finish(g):
            try:await self.mark(g,'EXPIRED')
            finally:marking.discard(g['id'])
        while self.ready:
            for g in list(self.grants.values()):
                if g['state'] in ('PENDING','ACTIVE') and clock()>=g['deadline'] and g['id'] not in self.denied:
                    self.fence(g['id']);g['persistence']='PENDING'
                    if g['id'] not in marking:
                        marking.add(g['id']);self.track(finish(g))
            await asyncio.sleep(.02)

    def permitted(self,s):
        g=self.grants.get(s['grant'])
        return g is not None and not s['stopped'] and self.active(g) and g['revision']==s['revision']

    async def tunnel(self,principal,reader,writer):
        k,b=await read_frame(reader)
        p=decode(b)
        if k!=OPEN or type(p) is not dict or set(p)!={'grant','service'}:raise Refused('OPEN_FORMAT')
        g=self.grants.get(p['grant'])
        if g is None or g['owner']!=principal or p['service']!=g['service'] or not self.active(g):raise Refused('NO_ACCESS')
        if len(self.sessions)>=self.cfg['max_sessions'] or sum(s['owner']==principal for s in self.sessions.values())>=self.cfg['per_principal']:raise Refused('SESSION_FULL')
        sid=str(uuid.uuid4());s={'id':sid,'owner':principal,'grant':g['id'],'revision':g['revision'],'stopped':False,'client':writer,'backend':None,'task':asyncio.current_task()}
        self.sessions[sid]=s
        try:
            backend=self.cfg['service']
            br,bw=await asyncio.wait_for(asyncio.open_connection(backend['host'],backend['port'],limit=MAX_FRAME),1)
            s['backend']=bw
            if self.barriers and (self.barriers/'hold-connect').exists():
                (self.barriers/'entered-connect').write_text('entered')
                until=time.monotonic()+15
                while (self.barriers/'hold-connect').exists():
                    if time.monotonic()>until:raise Refused('TEST_CONNECT_TIMEOUT')
                    await asyncio.sleep(.01)
            bw.transport.set_write_buffer_limits(high=MAX_FRAME,low=4096)
            writer.transport.set_write_buffer_limits(high=MAX_FRAME,low=4096)
            if not self.permitted(s):raise Refused('ADMISSION_RETIRED')
            frame(writer,OK,encode({'session':sid}));await writer.drain();self.facts['admitted']+=1
            async def to_backend():
                eof=False
                while True:
                    k,b=await read_frame(reader,self.cfg['frame_seconds'])
                    if not self.permitted(s):raise Refused('STOPPED')
                    if k==EOF:
                        if eof:raise Refused('DUPLICATE_EOF')
                        eof=True;bw.write_eof();await bw.drain()
                    elif k==DATA and not eof:
                        bw.write(b);self.facts['forwarded_bytes']+=len(b)
                        if bw.transport.get_write_buffer_size()>MAX_FRAME:
                            self.facts['backpressure_events']+=1
                        await bw.drain()
                    elif k==CLOSE:return
                    else:raise Refused('FRAME_STATE')
            async def to_client():
                while True:
                    b=await asyncio.wait_for(br.read(MAX_FRAME),self.cfg['frame_seconds'])
                    if not self.permitted(s):raise Refused('STOPPED')
                    if not b:
                        frame(writer,EOF);await writer.drain();return
                    frame(writer,DATA,b);self.facts['forwarded_bytes']+=len(b);await writer.drain()
            a,b=asyncio.create_task(to_backend()),asyncio.create_task(to_client())
            try:
                done,_=await asyncio.wait((a,b),return_when=asyncio.FIRST_COMPLETED)
                for t in done:
                    if t.exception():raise t.exception()
                if b in done:
                    # Backend EOF is not a client->backend half-close.
                    await asyncio.wait_for(a,self.cfg['frame_seconds'])
                else:
                    # Explicit CLOSE terminates both directions.
                    return
            finally:
                a.cancel();b.cancel();await asyncio.gather(a,b,return_exceptions=True)
        finally:
            abort(s['backend']);abort(writer);self.sessions.pop(sid,None);self.facts['closed']+=1

    async def stop(self):
        self.ready=False;self.retire()
        for srv in self.servers:srv.close();await srv.wait_closed()
        for group in self.connections.values():
            for w in list(group):abort(w)
        current=asyncio.current_task()
        pending=[t for t in self.tasks if t is not current]
        for t in pending:t.cancel()
        await asyncio.gather(*pending,return_exceptions=True)
        # Retain the process lock until the sole DB worker is actually gone.
        await asyncio.to_thread(self.store.close)
        os.close(self.lock)

async def run(args):
    cfg=json.loads(Path(args.config).read_text());gw=Gateway(cfg,args.root,args.barriers)
    end=asyncio.Event();loop=asyncio.get_running_loop()
    for sig in (signal.SIGTERM,signal.SIGINT):loop.add_signal_handler(sig,end.set)
    try:
        await gw.start();await end.wait()
    finally:await gw.stop()

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--root',required=True)
    p.add_argument('--barriers',help='Explicit test-only storage barriers; never set for deployment')
    args=p.parse_args();asyncio.run(run(args))
if __name__=='__main__':main()
