"""Bounded installed-service boot/readonly recovery qualification; VM fixtures only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid
from . import vm_cases as vm
from . import vm_recovery as rec
from . import vm_service as svc

SETUP='grantweft-qualification-setup.service'
BACKEND='grantweft-qualification-backend.service'
IMAGE=Path('/opt/grantweft/state.ext4')
MODE=vm.LAB/'boot-storage-mode'
DROP=Path('/etc/systemd/system/grantweft.service.d/99-test-boot.conf')

def bootid():return Path('/proc/sys/kernel/random/boot_id').read_text().strip()
def digest():return hashlib.sha256((svc.STATE/'catalog.sqlite').read_bytes()).hexdigest()
def receipt(name,value):vm.save(name,value)
def unit_file(name,text):Path('/etc/systemd/system',name).write_text(text)
def sample():
    u=svc.show();pid=int(u['MainPID']);p=Path('/proc',str(pid));text=p.joinpath('status').read_text()
    return {'unit':u,'privileges':svc.privileges(pid),'process_start_ticks':int(p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]),
            'rss_kib':int(next(x for x in text.splitlines() if x.startswith('VmRSS:')).split()[1]),
            'fds':len(list(p.joinpath('fd').iterdir())),
            'disk_allocated_bytes':sum(f.stat().st_blocks*512 for f in svc.STATE.iterdir() if f.is_file())}

def snapshot():return {'catalog':svc.saved_catalog(),'sha256':digest()}
def same_content(a,b):
    if a['sha256']!=b['sha256'] or a['catalog']['counts']!=b['catalog']['counts'] or a['catalog']['history_sha256']!=b['catalog']['history_sha256'] or a['catalog']['grants']!=b['catalog']['grants']:
        raise RuntimeError('Pre-service journal changed across shutdown/boot')
    if {k:v['inode'] for k,v in a['catalog']['file_ids'].items()}!={k:v['inode'] for k,v in b['catalog']['file_ids'].items()}:raise RuntimeError('Catalog/lock inode replaced')

def setup():
    # Runs BEFORE the real service on every boot. Read-only journal witness precedes
    # topology/backend initialization and never repairs or writes gateway state.
    if svc.owned_pids():raise RuntimeError('Service already ran before boot witness')
    # Keep the backing loop writable; inject a readonly filesystem mount, not
    # a second unintended readonly block-device fault.
    device=vm.call(['losetup','--find','--show',IMAGE]).strip()
    vm.call(['mount','-o',MODE.read_text().strip(),device,svc.STATE])
    (vm.LAB/'boot-loop-device').write_text(device)
    witness={'boot_id':bootid(),'before_gateway':True,'service_uid_pids':svc.owned_pids(),
             'monotonic_seconds':time.monotonic(),'storage_mode':MODE.read_text().strip(),
             'mount_options':vm.call(['findmnt','-no','OPTIONS','--target',svc.STATE]).strip(),'backing_device_readonly':int(vm.call(['blockdev','--getro',device]).strip()),**snapshot()}
    receipt('boot-witness',witness)
    (vm.LAB/'backend-ready').unlink(missing_ok=True)
    owned=[]
    try:topology=vm.topology(owned)
    except BaseException:
        vm.cleanup([],owned);raise
    receipt('boot-topology',topology)

def prepare(mode):
    v={'passed':False,'mode':mode}
    try:
        if mode=='normal':
            # The prior formal service is stopped; migrate its unchanged catalog to
            # a dedicated persistent ext4 filesystem. No reset/history deletion.
            if svc.owned_pids():raise RuntimeError('Service must be stopped before mounting fixture storage')
            old=snapshot();staging=Path('/opt/grantweft/prior-state');shutil.copytree(svc.STATE,staging)
            vm.call(['truncate','-s','32M',IMAGE]);vm.call(['mkfs.ext4','-q','-F',IMAGE]);vm.call(['mount','-o','loop,rw',IMAGE,svc.STATE])
            import pwd
            account=pwd.getpwnam('grantweft');os.chown(svc.STATE,account.pw_uid,account.pw_gid);os.chmod(svc.STATE,0o700)
            for f in staging.iterdir():
                if f.is_file():shutil.copy2(f,svc.STATE/f.name);os.chown(svc.STATE/f.name,account.pw_uid,account.pw_gid)
            if digest()!=old['sha256'] or svc.saved_catalog()['counts']!=old['catalog']['counts']:raise RuntimeError('Storage fixture migration altered catalog')
            cfg=json.loads(svc.CONFIG.read_text());cfg.update(max_ops=512,max_events=512,max_grants=96);svc.configure(cfg)
            unit_file(SETUP,'[Unit]\nDescription=Grantweft VM fixture and read-only boot witness\nBefore=grantweft.service '+BACKEND+'\n[Service]\nType=oneshot\nRemainAfterExit=yes\nExecStart=/opt/grantweft/venv/bin/python -m tools.vm_closeout setup\nWorkingDirectory=/opt/grantweft/source\nTimeoutStartSec=15s\n')
            unit_file(BACKEND,'[Unit]\nRequires='+SETUP+'\nAfter='+SETUP+'\n[Service]\nExecStart=/usr/sbin/ip netns exec gw-backend /opt/grantweft/venv/bin/python -m tools.endpoint --root /opt/grantweft/lab\nWorkingDirectory=/opt/grantweft/source\nKillMode=control-group\n')
            DROP.parent.mkdir(exist_ok=True)
            DROP.write_text('[Unit]\nRequires='+SETUP+' '+BACKEND+'\nAfter='+SETUP+' '+BACKEND+'\n[Service]\nNetworkNamespacePath=/run/netns/gw-router\n')
            # Let the real fixture dependency perform initial mount/witness/network
            # setup too, avoiding a temporary alternative setup command.
            vm.call(['umount',svc.STATE]);MODE.write_text('rw')
            svc.ctl('daemon-reload');svc.ctl('enable',svc.UNIT);svc.reset_failed();svc.ctl('start',svc.UNIT)
            vm.wait(lambda:(vm.LAB/'backend-ready').exists())
            v['topology']=json.loads((vm.LAB/'boot-topology.json').read_text())
        else:
            cfg=json.loads(svc.CONFIG.read_text());epoch=svc.status()['epoch']
            v['pre_fault_service']=sample()
        epoch=svc.status()['epoch']
        # Freeze expiry windows for reboot witnesses, distinct from sustained tests.
        g=vm.approve(epoch,vm.mutate('a','request',epoch,service='demo',duration=900)['original_result']['grant'])
        pending=vm.request(epoch,'b')
        v.update(epoch=epoch,active=g,pending=pending,boot_before=bootid(),unit=svc.show(),privileges=svc.privileges(int(svc.show()['MainPID'])),installed_unit_sha256=hashlib.sha256(Path('/etc/systemd/system',svc.UNIT).read_bytes()).hexdigest())
        v['direct_backend']=vm.probe('direct')
        if mode=='readonly':
            # Actual live write failure; service remains DEGRADED until manually stopped.
            os.chmod(svc.STATE,0o500)
            v['live_refusal']=rec.expect_code('approver',dict(action='revoke',operation=str(uuid.uuid4()),epoch=epoch,grant=g['id'],revision=g['revision']),'STORAGE_FAILED')
            v['degraded']=svc.denied_status(epoch,True)
            v['degraded_refusal']=rec.expect_code('a',dict(action='request',operation=str(uuid.uuid4()),epoch=epoch,service='demo',duration=30),'DEGRADED')
            if not v['degraded']['failure']['sqlite_code'].startswith('SQLITE_READONLY'):raise RuntimeError('Live storage fault not observed')
            os.chmod(svc.STATE,0o700)
            v['degraded_after_permission_repair']=svc.denied_status(epoch,True)
            v['degraded_old_data_refusals']=svc.deny_all(v['degraded_after_permission_repair'])
            v['unit_after_permission_repair']=svc.show()
            for key in ('MainPID','InvocationID','NRestarts'):
                if v['unit_after_permission_repair'][key]!=v['unit'][key]:raise RuntimeError('Online storage repair restarted authority')
            MODE.write_text('ro')
        v['before_shutdown']=snapshot()
        if not {'ACTIVE','PENDING'}<={g['state'] for g in v['before_shutdown']['catalog']['grants']}:raise RuntimeError('Missing live pre-reboot authority')
        if mode=='readonly':
            from .closeout_contract import degraded_catalog
            degraded_catalog(v['degraded'],v['before_shutdown']['catalog'],epoch)
            degraded_catalog(v['degraded_after_permission_repair'],v['before_shutdown']['catalog'],epoch)
        v['enabled']=vm.call(['systemctl','is-enabled',svc.UNIT]).strip()
        v['passed']=True
    except BaseException as exc:v['error']=type(exc).__name__;raise
    finally:receipt('boot-prepared-'+mode,v)

def complete(mode):
    v={'passed':False,'mode':mode}
    try:
        old=json.loads((vm.LAB/('boot-prepared-'+mode+'.json')).read_text());w=json.loads((vm.LAB/'boot-witness.json').read_text())
        if bootid()==old['boot_before'] or w['boot_id']!=bootid() or w['service_uid_pids'] or not w['before_gateway']:raise RuntimeError('No real pre-service reboot witness')
        same_content(old['before_shutdown'],w)
        v.update(prepared=old,witness=w,boot_after=bootid(),topology=json.loads((vm.LAB/'boot-topology.json').read_text()),direct_backend=vm.probe('direct'))
        if mode=='readonly':
            def limited():
                s=svc.show()
                return s['ActiveState']=='failed' and s['MainPID']=='0' and int(s['NRestarts'])==3
            vm.wait(limited,timeout=15);s=svc.show();time.sleep(1.3);stable=svc.show()
            journal=vm.call(['journalctl','-b','-u',svc.UNIT,'--no-pager','-o','cat'])
            if 'Start request repeated too quickly' not in journal or journal.count('Read-only file system')!=3 or svc.owned_pids() or stable['NRestarts']!=s['NRestarts']:raise RuntimeError('Readonly restart limiting not evidenced')
            same_content(old['before_shutdown'],snapshot())
            p=subprocess.run(['ip','netns','exec','gw-client',vm.PY,'-m','tools.probe','--pki',str(vm.LAB/'pki'),'--mode','control','--request','{"action":"status"}'],capture_output=True,text=True,timeout=5)
            if p.returncode==0 or 'ConnectionRefusedError' not in p.stderr:raise RuntimeError('Broken startup unexpectedly accepted control')
            v['failed_start']={'unit':s,'stable_unit':stable,'stable_seconds':1.3,'service_uid_pids':svc.owned_pids(),'readonly_error_traces':journal.count('Read-only file system'),'limit_message':'Start request repeated too quickly','admission_refusal':{'exit_code':p.returncode,'exception':'ConnectionRefusedError'},'catalog_after_failed_starts':snapshot()}
            # Explicit repair: retain mounted filesystem, catalog and stable lock.
            vm.call(['mount','-o','remount,rw',svc.STATE]);os.chmod(svc.STATE,0o700);MODE.write_text('rw');svc.reset_failed();svc.ctl('start',svc.UNIT)
        else:vm.wait(lambda:svc.show()['ActiveState']=='active',timeout=15)
        vm.wait(lambda:(vm.LAB/'backend-ready').exists())
        before_fresh=snapshot();svc.restored(w['catalog'],before_fresh['catalog']);epoch=svc.status()['epoch']
        if epoch<=old['epoch']:raise RuntimeError('Old epoch survived reboot')
        st=svc.denied_status(epoch,False)
        old_refusals=svc.deny_all(st);old_stale=rec.stale(old['epoch'],old['active'])
        g,trial=svc.fresh(epoch)
        retired=vm.mutate('approver','revoke',epoch,g)
        fresh_retirement={'grant_id':g['id'],'revoke':retired,'data_refusal':rec.denied(g)}
        v.update(enabled=vm.call(['systemctl','is-enabled',svc.UNIT]).strip(),service=sample(),after_recovery=before_fresh,status_after_recovery=st,
                 old_data_refusals=old_refusals,stale_operation=old_stale,epoch_after=epoch,
                 fresh_roundtrip=trial,fresh_retirement=fresh_retirement,passed=True)
    except BaseException as exc:v['error']=type(exc).__name__;raise
    finally:receipt('boot-finished-'+mode,v)

def sustain():
    from .closeout_contract import check_sustained,cycle_grant,identity
    procs=[];v={'passed':False,'cycles':[],'policy':{'cycles':40,'warmup_cycles':5,'interval_seconds':15,'minimum_seconds':600,'maximum_seconds':720,'rss_absolute_kib':65536,'rss_range_kib':8192,'rss_end_mean_growth_kib':4096,'idle_fd_growth':0},'scope':'Linux VM formal systemd main process; idle samples after each mixed revoke/expiry cycle, same process throughout; finite configured catalog, no GC/rollover or long-term claim'}
    try:
        epoch=svc.status()['epoch'];v['initial_status']=svc.denied_status(epoch,False);v['initial']=sample();v['config_limits']={k:json.loads(svc.CONFIG.read_text())[k] for k in ('max_ops','max_events','max_grants')};seen={g['id'] for g in v['initial_status']['grants']};identity(v['initial'],v['initial']);begin=time.monotonic()
        for i in range(40):
            row={'index':i,'passed':False};v['cycles'].append(row);start=time.monotonic()
            # Alternate explicit revoke and natural expiry; real holders prove positive closure.
            kind='revoke' if i%2==0 else 'expiry';duration=30 if kind=='revoke' else 2
            g=vm.approve(epoch,vm.mutate('a','request',epoch,service='demo',duration=duration)['original_result']['grant'])
            row['roundtrip']=vm.probe('echo',g);h=rec.holder(procs,g,'sustain-'+str(i))
            if kind=='revoke':
                time.sleep(.15);row['revoke']=vm.mutate('approver','revoke',epoch,g)
            row['closure']=rec.closure(h);row['old_data_refusal']=rec.denied(g)
            vm.wait(lambda:svc.status()['sessions']==0);time.sleep(.1)
            s=svc.status();grants=[]
            while True:
                grants+=s['grants']
                if not s['next_cursor']:break
                s=vm.rpc('approver',{'action':'status','after':s['next_cursor']})
            if any(x['access']!='DENIED' or x['sessions'] for x in grants) or s['degraded'] or s['epoch']!=epoch:raise RuntimeError('Sustained access did not retire')
            target=next(x for x in grants if x['id']==g['id'])
            if target['state']!=('REVOKED' if kind=='revoke' else 'EXPIRED') or target['persistence']!='COMMITTED':raise RuntimeError('Terminal state did not persist')
            row.update(kind=kind,terminal={k:target[k] for k in ('id','state','revision','epoch','persistence')},grant_id=g['id'],status={'epoch':s['epoch'],'health':s['health'],'degraded':s['degraded'],'sessions':s['sessions'],'facts':s['facts'],'capacity':s['capacity'],'grant_count':len(grants),'all_denied':True},sample=sample(),elapsed_seconds=time.monotonic()-begin,work_seconds=time.monotonic()-start,passed=True)
            cycle_grant(row,epoch,seen)
            identity(row['sample'],v['initial'])
            receipt('sustained-progress',v)
            until=begin+(i+1)*15
            if time.monotonic()>until:raise TimeoutError('Sustained cycle exceeded fixed schedule')
            time.sleep(until-time.monotonic())
        v.update(seconds=time.monotonic()-begin,final=sample(),passed=True)
        check_sustained(v)
    except BaseException as exc:v.update(passed=False,error=type(exc).__name__);raise
    finally:
        v['cleanup']=vm.cleanup(procs,[])
        if v['cleanup']['errors']:v['passed']=False
        receipt('sustained',v)
    if not v['passed']:raise RuntimeError('Sustained cleanup failed')

def cleanup():
    v={'passed':False}
    try:
        pid=int(svc.show()['MainPID']);svc.ctl('stop',svc.UNIT);v['stopped']=svc.stopped(pid);svc.ctl('disable',svc.UNIT)
        svc.ctl('stop',BACKEND,SETUP)
        v['namespace_cleanup']=vm.cleanup([],list(vm.NS))
        if v['namespace_cleanup']['errors']:raise RuntimeError('Namespace cleanup failed')
        vm.call(['umount',svc.STATE]);vm.call(['losetup','--detach',(vm.LAB/'boot-loop-device').read_text().strip()]);DROP.unlink();Path('/etc/systemd/system',SETUP).unlink();Path('/etc/systemd/system',BACKEND).unlink();svc.ctl('daemon-reload')
        v.update(disabled=not Path('/etc/systemd/system/multi-user.target.wants/grantweft.service').exists(),mount_removed=not os.path.ismount(svc.STATE),passed=True)
    except BaseException as exc:v['error']=type(exc).__name__;raise
    finally:receipt('closeout-cleanup',v)

def main():
    if not __debug__:raise RuntimeError('Normal Python required')
    p=argparse.ArgumentParser();p.add_argument('action',choices=['setup','prepare-normal','finish-normal','prepare-readonly','finish-readonly','sustain','cleanup']);a=p.parse_args()
    if a.action=='setup':setup()
    elif a.action.startswith('prepare-'):prepare(a.action.split('-',1)[1])
    elif a.action.startswith('finish-'):complete(a.action.split('-',1)[1])
    elif a.action=='sustain':sustain()
    else:cleanup()
if __name__=='__main__':main()
