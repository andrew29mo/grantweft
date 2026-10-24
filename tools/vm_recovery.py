"""Bounded storage faults around the installed unprivileged gateway, in a fresh VM."""
import concurrent.futures
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import time
import uuid
from . import vm_cases as vm

LAB=vm.LAB

def stop(p):
    p.terminate();p.wait(timeout=4)

def expect_code(who,req,code):
    try:vm.rpc(who,req)
    except subprocess.CalledProcessError as exc:
        if code not in exc.stderr:raise
        return {'exit_code':exc.returncode,'code':code}
    raise RuntimeError('Expected refusal absent: '+code)

def stale(epoch,g):
    return expect_code('approver',dict(action='revoke',operation=str(uuid.uuid4()),epoch=epoch,grant=g['id'],revision=g['revision']),'STALE_EPOCH')

def denied(g,who='a'):
    p=subprocess.run(['ip','netns','exec','gw-client',vm.PY,'-m','tools.probe','--pki',str(LAB/'pki'),'--who',who,'--mode','echo','--grant',g['id']],capture_output=True,text=True,timeout=5)
    if p.returncode==0 or 'NO_ACCESS' not in p.stderr:raise RuntimeError('Old data not refused')
    return {'exit_code':p.returncode,'code':'NO_ACCESS'}

def holder(procs,g,name):
    marker=LAB/(name+'-ready')
    p=subprocess.Popen(['ip','netns','exec','gw-client',vm.PY,'-m','tools.probe','--pki',str(LAB/'pki'),'--mode','hold','--grant',g['id'],'--marker',str(marker)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    procs.append((p,p.stdout));vm.wait(lambda:marker.exists() or p.poll() is not None)
    if not marker.exists():raise RuntimeError('Holder failed')
    return p

def closure(p):
    out,err=p.communicate(timeout=5)
    if p.returncode:raise RuntimeError('No positive closure: '+err[-200:])
    r=json.loads(out)
    if not r['connection_ended']:raise RuntimeError('Closure not observed')
    return r

def state():return vm.rpc('approver',{'action':'status'})

def catalog_snapshot(root):
    """Read-only receipt after writer exit / after boot, before fresh mutations."""
    with closing(sqlite3.connect('file:'+str(root/'catalog.sqlite')+'?mode=ro',uri=True)) as db:
        counts={t:db.execute('select count(*) from '+t).fetchone()[0] for t in ('ops','events','grants')}
        history={t:db.execute(query).fetchall() for t,query in (
            ('ops','select principal,id,payload,result from ops order by principal,id'),
            ('events','select seq,value from events order by seq'))}
        grants=[dict(zip(('id','state','revision','epoch'),r)) for r in db.execute('select id,state,revision,epoch from grants order by id')]
    return {'counts':counts,'grants':grants,
            'history_sha256':hashlib.sha256(json.dumps(history,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'file_ids':{n:{'device':(root/n).stat().st_dev,'inode':(root/n).stat().st_ino} for n in ('catalog.sqlite','writer.lock')}}

def main():
    if not __debug__:raise RuntimeError('Qualification requires normal Python')
    procs=[];owned=[];mount=None;v={'passed':False,'gateway_uid':65534,'scenarios':[]}
    try:
        v['topology']=vm.topology(owned);vm.start_backend(procs)
        v['direct_backend']=vm.probe('direct')
        base=json.loads((LAB/'config.json').read_text())
        # Every scenario uses a fresh state root; recovery always reuses that same root.
        for mode in ('ops_full','events_full','grant_full','sqlite_full','disk_full','read_only','late_commit'):
            row={'mode':mode,'passed':False};v['scenarios'].append(row)
            root=LAB/('recovery-'+mode);root.mkdir(mode=0o700)
            if mode in ('disk_full','read_only'):
                vm.call(['mount','-t','tmpfs','-o','size=1m,mode=0700','tmpfs',root]);mount=root
            os.chown(root,65534,65534);os.chmod(root,0o700)
            cfg=base|({'max_ops':2} if mode=='ops_full' else {'max_events':2} if mode=='events_full' else {'max_grants':1} if mode=='grant_full' else {'max_store_pages':8} if mode=='sqlite_full' else {'db_seconds':.4} if mode=='late_commit' else {})
            path=LAB/('config-'+mode+'.json');path.write_text(json.dumps(cfg))
            barriers=LAB/('barriers-'+mode);barriers.mkdir();os.chown(barriers,65534,65534)
            gw,_,info=vm.start_gateway(procs,root,path,barriers);epoch=info['epoch']
            g=vm.approve(epoch,vm.request(epoch));h=holder(procs,g,mode)
            begin=time.monotonic()
            if mode=='late_commit':
                pending=vm.request(epoch,'b');hold=barriers/'hold-approve';hold.touch()
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    approval=dict(action='approve',operation=str(uuid.uuid4()),epoch=epoch,grant=pending['id'],revision=pending['revision'])
                    f=pool.submit(vm.rpc,'approver',approval)
                    vm.wait(lambda:(barriers/'entered-approve').exists())
                    try:f.result(timeout=4)
                    except subprocess.CalledProcessError as exc:
                        if 'STORAGE_FAILED' not in exc.stderr:raise
                        row['refusal']={'exit_code':exc.returncode,'code':'STORAGE_FAILED'}
                    else:raise RuntimeError('Timed-out approval reported success')
                    row['closure']=closure(h);row['degraded_before_release']=state()['degraded'];hold.unlink()
                    def active_on_disk():
                        with sqlite3.connect(root/'catalog.sqlite') as db:
                            return db.execute('select state from grants where id=?',(pending['id'],)).fetchone()[0]=='ACTIVE'
                    vm.wait(active_on_disk)
                    row['late_commit_observed_on_disk']=True
                    row['late_data_refusal']=denied(pending,'b')
            elif mode in ('ops_full','events_full','grant_full'):
                code='GRANT_FULL' if mode=='grant_full' else 'CATALOG_FULL'
                row['admission_refusal']=expect_code('b',dict(action='request',operation=str(uuid.uuid4()),epoch=epoch,service='demo',duration=30),code)
                if mode=='grant_full':
                    row['revoke']=vm.mutate('approver','revoke',epoch,g)
                else:
                    row['refusal']=expect_code('approver',dict(action='revoke',operation=str(uuid.uuid4()),epoch=epoch,grant=g['id'],revision=g['revision']),code)
                row['closure']=closure(h)
            else:
                if mode=='disk_full':
                    stats=os.statvfs(root);free=stats.f_bavail*stats.f_frsize
                    vm.call(['fallocate','-l',str(free),root/'fill'])
                    row['free_bytes_after_fill']=os.statvfs(root).f_bavail*stats.f_frsize
                    if row['free_bytes_after_fill']!=0:raise RuntimeError('Disk not full')
                elif mode=='read_only':
                    os.chmod(root,0o500)
                    row['live_fault']='directory-write-permission-removed'
                for _ in range(64 if mode=='sqlite_full' else 1):
                    try:
                        if mode=='sqlite_full':vm.request(epoch,'b')
                        else:vm.mutate('approver','revoke',epoch,g)
                    except subprocess.CalledProcessError as exc:
                        if 'STORAGE_FAILED' not in exc.stderr:raise
                        row['refusal']={'exit_code':exc.returncode,'code':'STORAGE_FAILED'};break
                else:raise RuntimeError('Storage fault was not exercised')
                row['closure']=closure(h)
            row['fault_phase_seconds']=time.monotonic()-begin
            before=state();row['status_before_repair']=before
            if mode!='grant_full':
                if not before['degraded']:raise RuntimeError('Fault did not retire authority')
                expect_code('a',dict(action='request',operation=str(uuid.uuid4()),epoch=epoch,service='demo',duration=30),'DEGRADED')
            row['old_data_refusal']=denied(g)
            stop(gw)
            row['catalog_before_restart']=catalog_snapshot(root)
            if mode=='read_only':
                # Boot must fail without creating ready state; then repair the actual mount.
                vm.call(['mount','-o','remount,ro',root])
                row['startup_fault']='actual-readonly-filesystem'
                p=subprocess.run(['ip','netns','exec','gw-router','runuser','-u','nobody','--',vm.PY,'-m','grantweft.gateway','--config',str(path),'--root',str(root)],capture_output=True,text=True,timeout=5)
                last=p.stderr.strip().splitlines()[-1] if p.stderr.strip() else ''
                row['readonly_restart_refusal']={'exit_code':p.returncode,'exception':last.replace(str(root),'<state>')}
                if p.returncode==0 or not ('Read-only file system' in last or 'readonly database' in last):
                    raise RuntimeError('Readonly startup refusal not observed: '+last.replace(str(root),'<state>'))
                vm.call(['mount','-o','remount,rw',root]);os.chmod(root,0o700)
            if mode=='disk_full':(root/'fill').unlink()
            if mode in ('ops_full','events_full','grant_full','sqlite_full'):
                cfg.update(max_ops=256,max_events=256,max_grants=64,max_store_pages=1024);path.write_text(json.dumps(cfg))
            gw,_,info=vm.start_gateway(procs,root,path,barriers)
            row['epoch_before']=epoch;row['epoch_after']=info['epoch']
            row['catalog_after_boot']=catalog_snapshot(root)
            if row['catalog_before_restart']['counts']!=row['catalog_after_boot']['counts'] or row['catalog_before_restart']['history_sha256']!=row['catalog_after_boot']['history_sha256'] or row['catalog_before_restart']['file_ids']!=row['catalog_after_boot']['file_ids']:
                raise RuntimeError('Recovery replaced or lost catalog/history')
            if info['epoch']<=epoch:raise RuntimeError('Epoch did not advance')
            row['old_after_restart_refusal']=denied(g);row['stale_refusal']=stale(epoch,g)
            if mode=='late_commit':
                row['late_after_restart_refusal']=denied(pending,'b')
                row['late_history_replay']=vm.rpc('approver',approval)
                if row['late_history_replay'].get('historical') is not True or row['late_history_replay']['original_result']['grant']['state']!='ACTIVE':
                    raise RuntimeError('Late committed history missing')
                row['late_after_replay_refusal']=denied(pending,'b')
            fresh=vm.approve(info['epoch'],vm.request(info['epoch']));row['fresh_roundtrip']=vm.probe('echo',fresh)
            row['status_after_repair']=state()
            if row['status_after_repair']['degraded']:raise RuntimeError('Repair not recovered')
            row['resources']={'rss_kib':int(next(x for x in Path('/proc',str(info['pid']),'status').read_text().splitlines() if x.startswith('VmRSS:')).split()[1]),'fds':len(list(Path('/proc',str(info['pid']),'fd').iterdir())),'disk_allocated_bytes':sum(f.stat().st_blocks*512 for f in root.iterdir() if f.is_file())}
            stop(gw)
            if mount:vm.call(['umount',mount]);mount=None
            row['passed']=True
        v['passed']=True
    except BaseException as exc:
        v.update(passed=False,error=type(exc).__name__)
        raise
    finally:
        # Always attempt both process/namespace cleanup and mount cleanup, then save.
        try:
            v['cleanup']=vm.cleanup(procs,owned)
            if v['cleanup']['errors'] or not (v['cleanup']['owned_processes_reaped'] and v['cleanup']['namespaces_removed']):v['passed']=False
        except Exception as exc:v.update(passed=False,cleanup_error=type(exc).__name__)
        finally:
            if mount:
                try:vm.call(['umount',mount])
                except Exception:v.update(passed=False,mount_cleanup_error=True)
            vm.save('recovery',v)
    if not v['passed']:raise RuntimeError('Cleanup incomplete')
if __name__=='__main__':main()
