"""Fresh no-mount Colima VM; installs wheel and removes product source imports."""
import argparse,base64,datetime,hashlib,io,json,os,signal,subprocess,sys,tarfile,time,zipfile
from pathlib import Path
from .unit import manifest,fingerprint
from .report import verify,controls,render,CONTRACT
ROOT=Path(__file__).resolve().parents[1]

def main():
    if not __debug__:raise RuntimeError('Validation requires normal Python')
    p=argparse.ArgumentParser();p.add_argument('--colima-home',required=True);p.add_argument('--toolchain',required=True);p.add_argument('--profile',required=True);p.add_argument('--wheel',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    if not a.profile.startswith('gw-exp-') or not all(c.isalnum() or c=='-' for c in a.profile):p.error('Fresh dedicated gw-exp-* profile required')
    task_home=Path(a.colima_home).resolve();binpath=Path(a.toolchain).resolve();colima=binpath/'colima'
    if len(os.fsencode(str(task_home/'_lima'/('colima-'+a.profile)/'ssh.sock.1234567890123456')))>=104:p.error('VM socket path too long')
    out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()):p.error('Fresh output directory required')
    logs=out/'private-logs';logs.mkdir();wheel=Path(a.wheel).resolve();source=manifest()
    with zipfile.ZipFile(wheel) as z:modules={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('grantweft/') and n.endswith(('.py','.service'))}
    if modules!={k:h for k,h in source.items() if k.startswith('grantweft/')}:p.error('Wheel differs from source')
    env=dict(os.environ,COLIMA_HOME=str(task_home),PATH=str(binpath)+os.pathsep+os.environ['PATH'])
    v={'contract':CONTRACT,'passed':False,'recorded_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':source,'source_sha256':fingerprint(source),'source_changed':False,'host_mounts':'none','wheel_modules_match':True,'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),'stages':[]}
    def persist():
        (out/'evidence.json').write_text(json.dumps(v,indent=2,allow_nan=False)+'\n');(out/'report.html').write_text(render(v))
    def run(name,args,timeout=60,stdin=None):
        start=time.monotonic();proc=subprocess.Popen(list(map(str,args)),cwd=ROOT,env=env,stdin=subprocess.PIPE if stdin is not None else None,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True);timed=False
        try:stdout,stderr=proc.communicate(stdin,timeout=timeout)
        except subprocess.TimeoutExpired:
            timed=True;os.killpg(proc.pid,signal.SIGKILL);stdout,stderr=proc.communicate(timeout=5)
        except BaseException:
            os.killpg(proc.pid,signal.SIGKILL);stdout,stderr=proc.communicate(timeout=5)
            v['stages'].append({'name':name,'exit_code':proc.returncode,'timed_out':True,'seconds':time.monotonic()-start});persist();raise
        (logs/(name+'.log')).write_text(stdout+stderr);v['stages'].append({'name':name,'exit_code':proc.returncode,'timed_out':timed,'seconds':time.monotonic()-start});persist()
        if timed or proc.returncode:raise RuntimeError(name+' failed/timeout; see ignored private log')
        return stdout
    def ssh(name,args,**kw):return run(name,[colima,'--profile',a.profile,'ssh','--',*args],**kw)
    def guest(name,command,**kw):return ssh(name,['sudo','sh','-c','cd /opt/grantweft/source && '+command],**kw)
    created=False;initial=[];disk=task_home/'_lima/_disks'/('colima-'+a.profile)
    try:
        initial=[json.loads(x) for x in run('initial',[colima,'list','--json']).splitlines()]
        if disk.exists() or any(r['name']==a.profile for r in initial):raise RuntimeError('Existing VM/disk refused')
        created=True
        run('create',[colima,'start',a.profile,'--cpu','2','--memory','2','--disk','15','--mount','none','--activate=false','--ssh-config=false','--hostname','grantweft-exp','--dns-host','grantweft-exp=127.0.0.1','--dns-host','lima-colima-'+a.profile+'=127.0.0.1'],timeout=300)
        ssh('dependencies',['sudo','sh','-c','apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-venv openssl iproute2 util-linux'],timeout=300)
        buf=io.BytesIO()
        with tarfile.open(fileobj=buf,mode='w:gz') as tar:
            for file in source:tar.add(ROOT/file,arcname='source/'+file,recursive=False)
            tar.add(wheel,arcname=wheel.name,recursive=False)
        code='import sys,io,tarfile,base64,pathlib;p=pathlib.Path("/opt/grantweft");p.mkdir();tarfile.open(fileobj=io.BytesIO(base64.b64decode(sys.stdin.read()))).extractall(p,filter="data")'
        ssh('upload',['sudo','python3','-c',code],stdin=base64.b64encode(buf.getvalue()).decode())
        guest('install','python3 -m venv /opt/grantweft/venv && /opt/grantweft/venv/bin/pip install --no-index --no-deps /opt/grantweft/'+wheel.name+' && mv grantweft /opt/grantweft/retired-source')
        provenance='import grantweft,pathlib,hashlib,json,sqlite3,ssl,platform;root=pathlib.Path(grantweft.__file__).parent;print(json.dumps(dict(installed_modules={"grantweft/"+str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file() and p.suffix in (".py",".service") and "__pycache__" not in p.parts},installed_source_absent=not pathlib.Path("grantweft").exists(),sqlite=sqlite3.sqlite_version,openssl=ssl.OPENSSL_VERSION,python=platform.python_version())))'
        v.update(json.loads(guest('provenance',"/opt/grantweft/venv/bin/python -c '"+provenance+"'")))
        run('native',[sys.executable,'-m','tools.unit','--output',out/'native.json']);v['native']=json.loads((out/'native.json').read_text())
        guest('linux','/opt/grantweft/venv/bin/python -m tools.unit --output /opt/grantweft/linux.json',timeout=120)
        v['linux']=json.loads(ssh('linux-read',['sudo','cat','/opt/grantweft/linux.json']))
        guest('cases','/opt/grantweft/venv/bin/python -m tools.vm_cases cases',timeout=120)
        v['cases']=json.loads(ssh('cases-read',['sudo','cat','/opt/grantweft/lab/cases.json']))
        guest('recovery','/opt/grantweft/venv/bin/python -m tools.vm_recovery',timeout=120)
        v['recovery']=json.loads(ssh('recovery-read',['sudo','cat','/opt/grantweft/lab/recovery.json']))
        guest('service','/opt/grantweft/venv/bin/python -m tools.vm_service',timeout=120)
        v['service']=json.loads(ssh('service-read',['sudo','cat','/opt/grantweft/lab/service.json']))
        for action in ('prepare',):
            guest(action,'/opt/grantweft/venv/bin/python -m tools.vm_cases '+action,timeout=120)
            name='prepared' if action=='prepare' else action
            v[name]=json.loads(ssh(name+'-read',['sudo','cat','/opt/grantweft/lab/'+name+'.json']))
        ssh('schedule-reboot',['sudo','systemd-run','--unit=grantweft-test-reboot','--on-active=2s','--timer-property=AccuracySec=1s','/usr/bin/systemctl','reboot'])
        until=time.monotonic()+120;new=None;v['reboot_polls']=[]
        while time.monotonic()<until:
            try:
                r=subprocess.run([str(colima),'--profile',a.profile,'ssh','--','cat','/proc/sys/kernel/random/boot_id'],env=env,capture_output=True,text=True,timeout=5)
                v['reboot_polls'].append({'exit_code':r.returncode,'timed_out':False,'boot_id':r.stdout.strip() if r.returncode==0 else None})
                if r.returncode==0 and len(r.stdout.strip())==36 and r.stdout.strip()!=v['prepared']['boot_before']:new=r.stdout.strip();break
            except subprocess.TimeoutExpired:v['reboot_polls'].append({'exit_code':None,'timed_out':True,'boot_id':None})
            time.sleep(1)
        if new is None:
            for tag,args in [('reboot-state',['systemctl','show','grantweft-test-reboot.timer','grantweft-test-reboot.service']),('reboot-journal',['journalctl','-u','grantweft-test-reboot.service','-u','grantweft-test-reboot.timer','--no-pager','-n','80']),('reboot-jobs',['systemctl','list-jobs','--no-pager'])]:
                try:ssh(tag,['sudo',*args],timeout=8)
                except Exception:pass
            raise TimeoutError('Boot identity did not change')
        guest('finish','/opt/grantweft/venv/bin/python -m tools.vm_cases finish',timeout=120)
        v['finished']=json.loads(ssh('finished-read',['sudo','cat','/opt/grantweft/lab/finished.json']))
        v['closeout']={};v['closeout_reboot_polls']={}
        for mode in ('normal','readonly'):
            guest('boot-prepare-'+mode,'/opt/grantweft/venv/bin/python -m tools.vm_closeout prepare-'+mode,timeout=90)
            prepared=json.loads(ssh('boot-prepared-'+mode+'-read',['sudo','cat','/opt/grantweft/lab/boot-prepared-'+mode+'.json']))
            ssh('boot-schedule-'+mode,['sudo','systemd-run','--unit=grantweft-closeout-'+mode,'--on-active=2s','--timer-property=AccuracySec=1s','/usr/bin/systemctl','reboot'])
            until=time.monotonic()+120;new=None;polls=[];v['closeout_reboot_polls'][mode]=polls
            while time.monotonic()<until:
                try:
                    r=subprocess.run([str(colima),'--profile',a.profile,'ssh','--','cat','/proc/sys/kernel/random/boot_id'],env=env,capture_output=True,text=True,timeout=5)
                    polls.append({'exit_code':r.returncode,'timed_out':False,'boot_id':r.stdout.strip() if r.returncode==0 else None})
                    if r.returncode==0 and len(r.stdout.strip())==36 and r.stdout.strip()!=prepared['boot_before']:new=r.stdout.strip();break
                except subprocess.TimeoutExpired:polls.append({'exit_code':None,'timed_out':True,'boot_id':None})
                time.sleep(1)
            if new is None:raise TimeoutError('Closeout boot identity did not change')
            guest('boot-finish-'+mode,'/opt/grantweft/venv/bin/python -m tools.vm_closeout finish-'+mode,timeout=90)
            v['closeout'][mode]=json.loads(ssh('boot-finished-'+mode+'-read',['sudo','cat','/opt/grantweft/lab/boot-finished-'+mode+'.json']))
        guest('sustain','/opt/grantweft/venv/bin/python -m tools.vm_closeout sustain',timeout=780)
        v['closeout']['sustained']=json.loads(ssh('sustained-read',['sudo','cat','/opt/grantweft/lab/sustained.json']))
        guest('closeout-cleanup','/opt/grantweft/venv/bin/python -m tools.vm_closeout cleanup',timeout=45)
        v['closeout']['cleanup']=json.loads(ssh('closeout-cleanup-read',['sudo','cat','/opt/grantweft/lab/closeout-cleanup.json']))
        v['limits']=dict(power_loss_tested=False,suspend_tested=False,systemd_autostart_tested=True,long_term_tested=False,boot_zero_gap_tested=False)
        v['passed']=True
    except BaseException as exc:
        v['error']=type(exc).__name__+': '+str(exc).replace(str(ROOT),'<checkout>')
        if created:
            for name in ('cases','recovery','service','prepared','finished','boot-prepared-normal','boot-finished-normal','boot-prepared-readonly','boot-finished-readonly','sustained','sustained-progress','closeout-cleanup','boot-witness'):
                try:v['failed_'+name]=json.loads(ssh('failed-'+name,['sudo','cat','/opt/grantweft/lab/'+name+'.json'],timeout=5))
                except Exception:pass
            try:ssh('failed-boot-diagnostics',['sudo','journalctl','-b','-u','grantweft.service','-u','grantweft-qualification-setup.service','--no-pager','-n','120'],timeout=5)
            except Exception:pass
            try:ssh('failed-service-diagnostics',['sudo','cat','/opt/grantweft/lab/systemd-journal.log'],timeout=5)
            except Exception:pass
    finally:
        if created:
            try:
                run('delete',[colima,'delete',a.profile,'--data','--force'],timeout=120)
                if disk.exists():run('delete-disk',['env','LIMA_HOME='+str(task_home/'_lima'),binpath/'limactl','--tty=false','disk','delete','colima-'+a.profile],timeout=30)
                final=[json.loads(x) for x in run('final',[colima,'list','--json']).splitlines()]
                v['vm_deleted']=not any(r['name']==a.profile for r in final);v['disk_removed']=not disk.exists()
                v['preexisting_profiles_unchanged']=all(any(x['name']==r['name'] and x['status']==r['status'] for x in final) for r in initial)
            except BaseException as exc:v.update(passed=False,cleanup_error=type(exc).__name__+': '+str(exc))
        v['source_changed']=manifest()!=source
        if v['passed']:
            try:verify(v);v['controls']=controls(v)
            except Exception as exc:v.update(passed=False,verification_error=str(exc))
        persist()
    print(json.dumps({k:v.get(k) for k in ('passed','error','verification_error','cleanup_error')}));raise SystemExit(0 if v['passed'] else 1)
if __name__=='__main__':main()
