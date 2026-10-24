"""Actual installed systemd unit in a dedicated Linux VM/network namespace."""
import hashlib
import ctypes
import json
import os
from pathlib import Path
import pwd
import shutil
import signal
import subprocess
import time
import uuid
from . import vm_cases as vm
from . import vm_recovery as recovery

UNIT='grantweft.service';STATE=Path('/var/lib/grantweft');CONFIG=Path('/etc/grantweft/config.json')
FIELDS=('ActiveState','SubState','Result','MainPID','InvocationID','NRestarts','User','Group','Type','Restart','RestartUSec','StartLimitBurst','StartLimitIntervalUSec','TimeoutStopUSec','KillMode','NoNewPrivileges','CapabilityBoundingSet','ProtectSystem','LoadState','RestartPreventExitStatus')

def ctl(*args,timeout=15):return vm.call(['systemctl',*args],timeout=timeout)
def show():
    data=ctl('show',UNIT,*['--property='+f for f in FIELDS])
    return dict(line.split('=',1) for line in data.splitlines() if '=' in line)
def reset_failed():
    if show()['ActiveState']=='failed':ctl('reset-failed',UNIT)

def status():return vm.rpc('approver',{'action':'status'})
def configure(cfg):
    CONFIG.write_text(json.dumps(cfg));os.chmod(CONFIG,0o640);os.chown(CONFIG,0,pwd.getpwnam('grantweft').pw_gid)
def start():
    ctl('start',UNIT);s=show();r=status()
    if s['ActiveState']!='active' or s['Type']!='notify' or r['health']!='READY':raise RuntimeError('Service not initialized')
    return s,r['epoch']
def fresh(epoch):
    g=vm.approve(epoch,vm.request(epoch));return g,vm.probe('echo',g)
def privileges(pid):
    lines=dict((x.split(':',1)[0],x.split(':',1)[1].strip()) for x in Path('/proc',str(pid),'status').read_text().splitlines() if ':' in x)
    uid=pwd.getpwnam('grantweft').pw_uid
    if list(map(int,lines['Uid'].split()))!=[uid]*4 or uid==0 or int(lines['CapEff'],16)!=0 or lines['NoNewPrivs']!='1':raise RuntimeError('Unexpected runtime privileges')
    argv=Path('/proc',str(pid),'cmdline').read_bytes().rstrip(b'\0').decode().split('\0')
    expected=['/opt/grantweft/venv/bin/python','-m','grantweft.gateway','--config','/etc/grantweft/config.json','--root','/var/lib/grantweft','--notify']
    if argv!=expected:raise RuntimeError('Unexpected service command')
    return {'pid':pid,'argv':argv,'uid':uid,'uids':list(map(int,lines['Uid'].split())),'effective_capabilities':lines['CapEff'],'no_new_privileges':int(lines['NoNewPrivs'])}
def owned_pids():
    uid=pwd.getpwnam('grantweft').pw_uid;out=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            fields=p.joinpath('status').read_text().splitlines()
            if int(next(x for x in fields if x.startswith('Uid:')).split()[1])==uid:out.append(int(p.name))
        except (FileNotFoundError,ProcessLookupError):pass
    return sorted(out)
def stopped(pid):
    s=show();pids=owned_pids()
    if int(s['MainPID']) or pids or Path('/proc',str(pid)).exists():raise RuntimeError('Service process leaked')
    return {'unit':s,'service_uid_pids':pids,'old_pid_absent':True}
def admission_pair(epoch,g):return {'grant_id':g['id'],'old_data':recovery.denied(g),'old_operation':recovery.stale(epoch,g)}
def saved_catalog():return recovery.catalog_snapshot(STATE)
def unchanged(a,b):
    if a['counts']!=b['counts'] or a['history_sha256']!=b['history_sha256'] or a['file_ids']!=b['file_ids']:raise RuntimeError('Catalog/history/lock replaced')

def denied_status(epoch, degraded):
    snapshot=status()
    if (snapshot['epoch']!=epoch or snapshot['degraded'] is not degraded or
        snapshot['health']!=('DEGRADED' if degraded else 'READY') or
        snapshot['sessions']!=0 or snapshot['remaining_after_cursor']!=0 or
        any(g['access']!='DENIED' or g['sessions']!=0 for g in snapshot['grants'])):
        raise RuntimeError('Old authority not completely denied')
    return snapshot

def restored(a,b):
    unchanged(a,b)
    old={g['id']:g for g in a['grants']};new={g['id']:g for g in b['grants']}
    if not old or len(old)!=a['counts']['grants'] or old.keys()!=new.keys():raise RuntimeError('Old catalog rows lost')
    for gid,g in old.items():
        expected=g|({'state':'INVALIDATED','revision':g['revision']+1} if g['state'] in ('PENDING','ACTIVE') else {})
        if new[gid]!=expected:raise RuntimeError('Old catalog authority revived')

def deny_all(snapshot):
    return {g['id']:recovery.denied(g,g['owner']) for g in snapshot['grants']}

def main():
    if not __debug__:raise RuntimeError('Normal Python required')
    v={'passed':False};procs=[];owned=[];override=Path('/etc/systemd/system/grantweft.service.d/99-test-network-namespace.conf')
    try:
        v['topology']=vm.topology(owned);vm.start_backend(procs);v['direct_backend']=vm.probe('direct')
        vm.call([vm.PY,'-m','grantweft.deploy'])
        import grantweft
        shipped=Path(grantweft.__file__).parent/'systemd'/UNIT;installed=Path('/etc/systemd/system')/UNIT
        if shipped.read_bytes()!=installed.read_bytes():raise RuntimeError('Unit differs from installed package')
        v['installed_unit_sha256']=hashlib.sha256(installed.read_bytes()).hexdigest()
        cfg=json.loads((vm.LAB/'config.json').read_text());pki=Path('/etc/grantweft/pki');pki.mkdir(mode=0o750)
        account=pwd.getpwnam('grantweft');os.chown(pki,0,account.pw_gid)
        for name in ('ca.pem','server.pem','server.key'):
            shutil.copyfile(vm.LAB/'pki'/name,pki/name);os.chmod(pki/name,0o640);os.chown(pki/name,0,account.pw_gid)
        cfg.update(ca=str(pki/'ca.pem'),cert=str(pki/'server.pem'),key=str(pki/'server.key'));configure(cfg)
        override.parent.mkdir(exist_ok=True);override.write_text('[Service]\nNetworkNamespacePath=/run/netns/gw-router\n')
        ctl('daemon-reload');vm.call(['systemd-analyze','verify',str(installed)])
        v['test_override']={'network_namespace_only':True,'exec_start_unchanged':True}
        s,epoch=start();pid=int(s['MainPID']);v['initial']={'unit':s,'epoch':epoch,'privileges':privileges(pid)}
        g,trial=fresh(epoch);h=recovery.holder(procs,g,'service-normal')
        sample=Path('/proc',str(pid),'status').read_text()
        v['workload']={'roundtrip':trial,'rss_kib':int(next(x for x in sample.splitlines() if x.startswith('VmRSS:')).split()[1]),'fds':len(list(Path('/proc',str(pid),'fd').iterdir())),'disk_allocated_bytes':sum(f.stat().st_blocks*512 for f in STATE.iterdir() if f.is_file()),'scope':'Linux VM main-process point sample after fresh roundtrips with one additional held idle tunnel; not peak/endurance'}
        begin=time.monotonic();ctl('stop',UNIT)
        v['normal_stop']={'seconds':time.monotonic()-begin,'closure':recovery.closure(h),**stopped(pid)}
        time.sleep(1.3)
        if show()['ActiveState']!='inactive' or owned_pids():raise RuntimeError('Explicit stop unexpectedly restarted')
        v['normal_stop']['remained_stopped_after_seconds']=1.3
        s,epoch2=start();v['normal_restart']={'unit':s,'privileges':privileges(int(s['MainPID'])),'status_after_boot':denied_status(epoch2,False),'epoch':epoch2,**admission_pair(epoch,g)}
        if epoch2<=epoch:raise RuntimeError('Restart epoch unchanged')
        g,_=fresh(epoch2);h=recovery.holder(procs,g,'service-crash');old=s;before_crash=status();begin=time.monotonic()
        ctl('kill','--kill-whom=main','--signal=SIGKILL',UNIT)
        vm.wait(lambda:show()['ActiveState']=='active' and int(show()['MainPID']) not in (0,int(old['MainPID'])),timeout=12)
        s=show();r=status();epoch3=r['epoch']
        if s['InvocationID']==old['InvocationID'] or int(s['NRestarts'])<int(old['NRestarts'])+1 or epoch3<=epoch2:raise RuntimeError('No actual crash takeover')
        v['crash_takeover']={'observed_seconds':time.monotonic()-begin,'before':old,'after':s,'status_before':before_crash,'status_after_boot':denied_status(epoch3,False),'epoch_before':epoch2,'epoch_after':epoch3,'closure':recovery.closure(h),'privileges':privileges(int(s['MainPID'])),**admission_pair(epoch2,g)}
        v['crash_takeover']['fresh_roundtrip']=fresh(epoch3)[1]
        # Exhaust real catalog capacity under the unchanged official ExecStart.
        limit=status()['capacity']['ops']['used']+2;ctl('stop',UNIT);cfg['max_ops']=limit;configure(cfg)
        s,epoch4=start();g,_=fresh(epoch4);h=recovery.holder(procs,g,'service-degraded')
        req=dict(action='revoke',operation=str(uuid.uuid4()),epoch=epoch4,grant=g['id'],revision=g['revision'])
        refusal=recovery.expect_code('approver',req,'CATALOG_FULL');closed=recovery.closure(h)
        vm.wait(lambda:status()['sessions']==0)
        r=denied_status(epoch4,True);old_denials=deny_all(r)
        blocked=recovery.expect_code('a',dict(action='request',operation=str(uuid.uuid4()),epoch=epoch4,service='demo',duration=30),'DEGRADED')
        time.sleep(1.3);same=show()
        if same['MainPID']!=s['MainPID'] or same['InvocationID']!=s['InvocationID'] or same['NRestarts']!=s['NRestarts']:raise RuntimeError('DEGRADED auto-restarted')
        v['degraded']={'old_data_refusals':old_denials,'admission_refusal':blocked,'refusal':refusal,'closure':closed,'status':r,'unit_before':s,'unit_after_wait':same,'wait_seconds':1.3}
        ctl('stop',UNIT);before=saved_catalog();cfg['max_ops']=limit+16;configure(cfg)
        s,epoch5=start();after=saved_catalog();restored(before,after)
        after_status=denied_status(epoch5,False);after_denials=deny_all(after_status)
        if epoch5<=epoch4:raise RuntimeError('Repair epoch unchanged')
        v['repair']={'unit':s,'privileges':privileges(int(s['MainPID'])),'status_after_boot':after_status,'old_data_refusals':after_denials,'catalog_before':before,'catalog_after':after,'epoch_before':epoch4,'epoch_after':epoch5,**admission_pair(epoch4,g),'fresh_roundtrip':fresh(epoch5)[1]}
        # A stopped main cannot process TERM: exercise the shipped stop timeout/cgroup kill.
        s=show();g,_=fresh(epoch5);h=recovery.holder(procs,g,'service-forced-stop',close_timeout=10);pid=int(s['MainPID'])
        # SIGSTOP alone is insufficient: systemd sends SIGCONT during stop.
        # Root-only ptrace stop prevents TERM handling; SIGKILL still terminates it.
        libc=ctypes.CDLL(None,use_errno=True);libc.ptrace.restype=ctypes.c_long
        libc.ptrace.argtypes=[ctypes.c_uint,ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p]
        for request,data in ((0x4206,0x00100000),(0x4207,0)):
            if libc.ptrace(request,pid,None,ctypes.c_void_p(data))==-1:raise OSError(ctypes.get_errno(),'ptrace fault injection failed')
        traced,status_code=os.waitpid(pid,os.WUNTRACED)
        if traced!=pid or not os.WIFSTOPPED(status_code):raise RuntimeError('Trace stop not observed')
        begin=time.monotonic();stopper=subprocess.Popen(['systemctl','stop',UNIT],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        procs.append((stopper,stopper.stdout));until=time.monotonic()+10;killed=False
        while time.monotonic()<until:
            traced,status_code=os.waitpid(pid,os.WNOHANG)
            if traced:
                if not os.WIFSIGNALED(status_code) or os.WTERMSIG(status_code)!=signal.SIGKILL:raise RuntimeError('Expected systemd SIGKILL absent')
                killed=True;break
            time.sleep(.02)
        if not killed:raise TimeoutError('Tracee did not terminate')
        stopper.communicate(timeout=2);evidence=stopped(pid)
        v['forced_stop']={'seconds':time.monotonic()-begin,'injection':'root-ptrace-stop','trace_stop_observed':True,'termination_signal':signal.SIGKILL,'stop_exit_code':stopper.returncode,'closure':recovery.closure(h),**evidence}
        if evidence['unit']['Result']!='timeout':raise RuntimeError('Stop timeout not exercised')
        reset_failed();s,epoch6=start()
        if epoch6<=epoch5:raise RuntimeError('Forced-stop recovery epoch unchanged')
        v['forced_stop']['recovery']={'unit':s,'privileges':privileges(int(s['MainPID'])),'status_after_boot':denied_status(epoch6,False),'epoch_before':epoch5,'epoch_after':epoch6,**admission_pair(epoch5,g),'fresh_roundtrip':fresh(epoch6)[1]}
        ctl('stop',UNIT);before=saved_catalog()
        broken=json.loads(json.dumps(cfg));broken['principals']['b']['sha256']=broken['principals']['a']['sha256'];configure(broken)
        reset_failed();r=subprocess.run(['systemctl','start',UNIT],capture_output=True,text=True,timeout=12)
        def limited():
            state=show()
            return state['ActiveState']=='failed' and int(state['NRestarts'])>=3 and 'Start request repeated too quickly' in vm.call(['journalctl','-u',UNIT,'--no-pager','-o','cat','--grep','Start request repeated too quickly'])
        vm.wait(limited,timeout=12);s=show()
        time.sleep(1.3);stable=show()
        if stable['NRestarts']!=s['NRestarts'] or stable['MainPID']!='0' or stable['ActiveState']!='failed':raise RuntimeError('Restart loop continued after limit')
        if int(s['MainPID']) or owned_pids() or s['ActiveState']!='failed':raise RuntimeError('Restart limit did not stop attempts')
        after=saved_catalog();unchanged(before,after)
        if before['grants']!=after['grants']:raise RuntimeError('Invalid startup mutated grant states')
        traces=vm.call(['journalctl','-u',UNIT,'--no-pager','-o','cat','--grep','grantweft.protocol.Refused: DUPLICATE_IDENTITY']).count('grantweft.protocol.Refused: DUPLICATE_IDENTITY')
        if traces!=3:raise RuntimeError('Expected three invalid-config attempts')
        v['restart_limit']={'limit_message':'Start request repeated too quickly','unit_after_wait':stable,'stable_seconds':1.3,'failure_reason':'DUPLICATE_IDENTITY','observed_failure_traces':traces,'unit':s,'initial_start_exit_code':r.returncode,'service_uid_pids':owned_pids(),'catalog_before':before,'catalog_after':after}
        configure(cfg);reset_failed();s,epoch7=start()
        if epoch7<=epoch6:raise RuntimeError('Repaired config epoch unchanged')
        v['restart_limit']['repair']={'unit':s,'privileges':privileges(int(s['MainPID'])),'status_after_boot':denied_status(epoch7,False),'epoch_before':epoch6,'epoch_after':epoch7,'fresh_roundtrip':fresh(epoch7)[1]}
        ctl('stop',UNIT);v['final_stopped']=stopped(int(s['MainPID']))
        v['passed']=True
    except BaseException as exc:
        v.update(passed=False,error=type(exc).__name__)
        raise
    finally:
        try:
            # Keep raw service diagnostics inside ignored VM/host logs, not published receipts.
            (vm.LAB/'systemd-journal.log').write_text(ctl('status',UNIT) if show()['ActiveState']=='active' else vm.call(['journalctl','-u',UNIT,'--no-pager','-n','80']))
        except Exception:pass
        if not v['passed']:
            try:v['failure_unit_state']=show()
            except Exception:pass
        try:ctl('stop',UNIT)
        except Exception as exc:v.update(passed=False,cleanup_error=type(exc).__name__)
        try:
            override.unlink(missing_ok=True);ctl('daemon-reload');v['test_override_removed']=True
        except Exception as exc:v.update(passed=False,cleanup_error=type(exc).__name__)
        vm.finish_receipt(v,procs,owned,'service')
    if not v['passed']:raise RuntimeError('Service cleanup incomplete')
if __name__=='__main__':main()
