"""Root-only namespace fixture around the unprivileged installed gateway."""
import argparse,hashlib,json,os,signal,sqlite3,subprocess,sys,time,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from support import certs,fingerprint
BASE=Path('/opt/grantweft');LAB=BASE/'lab';PY=sys.executable
NS=('gw-client','gw-router','gw-backend')

def call(args,timeout=8,**kw):
    r=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=timeout,**kw)
    if r.returncode:
        exc=subprocess.CalledProcessError(r.returncode,args,r.stdout,r.stderr);exc.add_note(r.stderr.strip());raise exc
    return r.stdout

def ip(*args):return call(['ip',*args])
def save(name,data):
    (LAB/(name+'.json')).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
def wait(predicate,timeout=5):
    until=time.monotonic()+timeout
    while time.monotonic()<until:
        if predicate():return
        time.sleep(.02)
    raise TimeoutError('Fixture condition absent')
def topology(owned):
    for n in NS:
        ip('netns','add',n);owned.append(n);ip('-n',n,'link','set','lo','up')
    for first,second,ns1,ns2,addr1,addr2 in [('gc','gr','gw-client','gw-router','10.70.0.2/24','10.70.0.1/24'),('rb','br','gw-router','gw-backend','10.71.0.1/24','10.71.0.2/24')]:
        ip('link','add',first,'type','veth','peer','name',second)
        for dev,ns,addr in [(first,ns1,addr1),(second,ns2,addr2)]:
            ip('link','set','dev',dev,'netns',ns);ip('-n',ns,'addr','add',addr,'dev',dev);ip('-n',ns,'link','set','dev',dev,'up')
    ip('-n','gw-client','route','add','10.71.0.0/24','via','10.70.0.1')
    ip('-n','gw-backend','route','add','10.70.0.0/24','via','10.71.0.1')
    ip('netns','exec','gw-router','sysctl','-qw','net.ipv4.ip_forward=0')
    return {'namespaces':list(NS),'client':'10.70.0.2','gateway_front':'10.70.0.1','gateway_back':'10.71.0.1','backend':'10.71.0.2:9000','forwarding':False,'observed_ip_forward':int(ip('netns','exec','gw-router','sysctl','-n','net.ipv4.ip_forward').strip())}

def start_backend(procs):
    marker=LAB/'backend-ready'
    if marker.exists():marker.unlink()
    log=open(LAB/'backend.log','ab')
    p=subprocess.Popen(['ip','netns','exec','gw-backend',PY,'-m','tools.endpoint','--root',str(LAB)],stdout=log,stderr=log)
    procs.append((p,log));wait(lambda:marker.exists() or p.poll() is not None)
    if not marker.exists():raise RuntimeError('Backend failed startup')
    return p,log

def start_gateway(procs, root=None, config=None, barriers=None):
    root=Path(root) if root else LAB/'store'
    ready=root/'ready.json'
    if ready.exists():ready.unlink()
    log=open(LAB/'gateway.log','ab')
    p=subprocess.Popen(['ip','netns','exec','gw-router','runuser','-u','nobody','--',PY,'-m','grantweft.gateway','--config',str(config or LAB/'config.json'),'--root',str(root),*(['--barriers',str(barriers)] if barriers else [])],stdout=log,stderr=log)
    procs.append((p,log));wait(lambda:ready.exists() or p.poll() is not None)
    if not ready.exists():raise RuntimeError('Installed gateway failed startup')
    info=json.loads(ready.read_text());uid=[x for x in Path('/proc',str(info['pid']),'status').read_text().splitlines() if x.startswith('Uid:')][0]
    assert uid.split()[1:] == ['65534']*4
    return p,log,info

def rpc(who,req):return json.loads(call(['ip','netns','exec','gw-client',PY,'-m','tools.probe','--pki',str(LAB/'pki'),'--who',who,'--mode','control','--request',json.dumps(req)]))
def mutate(who,action,epoch,g=None,**kw):
    req={'action':action,'operation':str(uuid.uuid4()),'epoch':epoch,**kw}
    if g:req.update(grant=g['id'],revision=g['revision'])
    return rpc(who,req)
def request(epoch,who='a'):return mutate(who,'request',epoch,service='demo',duration=30)['original_result']['grant']
def approve(epoch,g):return mutate('approver','approve',epoch,g)['original_result']['grant']
def probe(mode,g=None):return json.loads(call(['ip','netns','exec','gw-client',PY,'-m','tools.probe','--pki',str(LAB/'pki'),'--mode',mode,*(['--grant',g['id']] if g else [])]))
def journal():
    path=LAB/'store/catalog.sqlite';db=sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True)
    result={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'grants':db.execute('select * from grants order by id').fetchall(),'ops_count':db.execute('select count(*) from ops').fetchone()[0]};db.close();return json.loads(json.dumps(result))

def cleanup(procs,namespaces):
    outcomes=[];errors=[];reaped=True;removed=True
    for index,(p,log) in enumerate(reversed(procs)):
        try:
            if p.poll() is None:p.terminate()
            try:p.wait(timeout=4)
            except subprocess.TimeoutExpired:
                errors.append('process-required-kill-'+str(index))
                p.kill();p.wait(timeout=2)
            if p.poll() is None:reaped=False
            outcomes.append(p.returncode)
        except Exception as exc:
            reaped=False;errors.append('process-'+str(index)+':'+type(exc).__name__)
        finally:
            for stream in (log,getattr(p,'stdin',None),getattr(p,'stdout',None),getattr(p,'stderr',None)):
                if stream is not None:
                    try:stream.close()
                    except Exception as exc:errors.append('log-close:'+type(exc).__name__)
    for n in reversed(namespaces):
        try:
            pids=ip('netns','pids',n).split()
            if pids:
                removed=False;errors.append('namespace-live-processes:'+n);continue
            ip('netns','del',n)
        except Exception as exc:
            removed=False;errors.append('namespace:'+n+':'+type(exc).__name__)
    return {'owned_processes_reaped':reaped,'namespaces_removed':removed,'exit_codes':outcomes,'errors':errors}

def finish_receipt(v,procs,namespaces,name):
    # Keep evidence even if cleanup itself has unexpected failures.
    try:
        v['cleanup']=cleanup(procs,namespaces)
        if not (v['cleanup']['owned_processes_reaped'] and v['cleanup']['namespaces_removed']) or v['cleanup']['errors']:
            v['passed']=False
    except Exception as exc:
        v.update(passed=False,cleanup_error=type(exc).__name__)
    finally:save(name,v)

def main():
    if not __debug__:raise RuntimeError('Qualification requires normal Python')
    p=argparse.ArgumentParser();p.add_argument('action',choices=['cases','prepare','finish']);a=p.parse_args()
    LAB.mkdir(exist_ok=True);os.chmod(LAB,0o755);procs=[];owned=[];v={'passed':False}
    try:
        if a.action=='finish':
            old=json.loads((LAB/'prepared.json').read_text());before=journal()
            assert before==old['journal_before']
            boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot!=old['boot_before']
            v.update(journal_after_before_gateway=before,journal_before=old['journal_before'],boot_before=old['boot_before'],boot_after=boot)
        v['topology']=topology(owned)
        if not (LAB/'config.json').exists():
            certs(LAB/'pki')
            cfg={'cert':str(LAB/'pki/server.pem'),'key':str(LAB/'pki/server.key'),'ca':str(LAB/'pki/ca.pem'),
                 'service':{'id':'demo','host':'10.71.0.2','port':9000},'control':{'host':'10.70.0.1','port':7443},'data':{'host':'10.70.0.1','port':7444},
                 'principals':{n:{'sha256':fingerprint(LAB/'pki'/(n+'.pem')),'role':'approver' if n=='approver' else 'requester'} for n in ('a','b','approver')}}
            (LAB/'config.json').write_text(json.dumps(cfg))
            (LAB/'store').mkdir(mode=0o700);os.chown(LAB/'store',65534,65534)
            for f in (LAB/'pki').iterdir():os.chown(f,65534,65534);os.chmod(f,0o600 if f.suffix=='.key' else 0o644)
        backend,log=start_backend(procs)
        gw,log,info=start_gateway(procs);epoch=info['epoch'];v['gateway_uid']=65534
        v['direct_backend']=probe('direct')
        if a.action=='cases':
            g=approve(epoch,request(epoch));v['roundtrip_trial']=probe('echo',g)
            status=Path('/proc',str(info['pid']),'status').read_text()
            v['resources']={'rss_kib':int(next(x for x in status.splitlines() if x.startswith('VmRSS:')).split()[1]),'fds':len(list(Path('/proc',str(info['pid']),'fd').iterdir())),'disk_allocated_bytes':sum(f.stat().st_blocks*512 for f in (LAB/'store').iterdir() if f.is_file()),'scope':'single Linux VM process observation after 20 roundtrips; not peak or long-term'}
            marker=LAB/'hold-ready'
            if marker.exists():marker.unlink()
            holder=subprocess.Popen(['ip','netns','exec','gw-client',PY,'-m','tools.probe','--pki',str(LAB/'pki'),'--mode','hold','--grant',g['id'],'--marker',str(marker)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            procs.append((holder,holder.stdout));wait(lambda:marker.exists() or holder.poll() is not None)
            if not marker.exists():raise RuntimeError('Holder failed before readiness')
            start=time.monotonic();r=mutate('approver','revoke',epoch,g);elapsed=time.monotonic()-start
            out,err=holder.communicate(timeout=5);assert holder.returncode==0,err
            holder.stderr.close()
            assert r['cleanup']=='COMPLETE' and json.loads(out)['connection_ended']
            v['revocation_trial']={'rpc_seconds':elapsed,'client_observation':json.loads(out),'cleanup':r['cleanup'],'sessions_after':rpc('approver',{'action':'status'})['sessions']}
            assert v['revocation_trial']['sessions_after']==0
            v['passed']=True
        elif a.action=='prepare':
            active=approve(epoch,request(epoch));pending=request(epoch,'b')
            v.update(active=active,pending=pending,epoch=epoch)
            os.kill(info['pid'],signal.SIGKILL);gw.wait(timeout=4)
            v.update(journal_before=journal(),boot_before=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),gateway_killed_before_reboot=True)
            assert {r[3] for r in v['journal_before']['grants']} >= {'ACTIVE','PENDING'}
            v['passed']=True
        else:
            recovered=rpc('approver',{'action':'status'})['grants'];v.update(epoch_after=epoch,recovered_grants=recovered)
            states={g['id']:g['state'] for g in recovered}
            assert states[old['active']['id']]==states[old['pending']['id']]=='INVALIDATED'
            denied=subprocess.run(['ip','netns','exec','gw-client',PY,'-m','tools.probe','--pki',str(LAB/'pki'),'--mode','echo','--grant',old['active']['id']],capture_output=True,text=True,timeout=5)
            assert denied.returncode!=0 and 'NO_ACCESS' in denied.stderr
            v['old_data_refusal']={'exit_code':denied.returncode,'code':'NO_ACCESS'}
            try:mutate('approver','revoke',old['epoch'],old['active'])
            except subprocess.CalledProcessError as exc:
                assert 'STALE_EPOCH' in exc.stderr
                v['stale_operation_refusal']={'exit_code':exc.returncode,'code':'STALE_EPOCH'}
            else:raise RuntimeError('Stale epoch accepted')
            fresh=approve(epoch,request(epoch));v['fresh_roundtrip']=probe('echo',fresh)
            v.update(old_grants_invalidated=True,stale_operation_refused=True,old_data_refused=True,passed=True)
    except BaseException as exc:
        v.update(passed=False,error=type(exc).__name__)
        raise
    finally:
        finish_receipt(v,procs,owned,{'cases':'cases','prepare':'prepared','finish':'finished'}[a.action])
    print(json.dumps({'passed':v['passed'],'action':a.action}))
    if not v['passed']:raise RuntimeError('Scenario cleanup incomplete')
if __name__=='__main__':main()
