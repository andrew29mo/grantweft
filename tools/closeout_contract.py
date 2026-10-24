"""Explicit boot/sustained evidence checks, usable with Python -O."""
import uuid
from .report import (require,number,no_errors,active_unit,process_identity,
                     retained_catalog,denied_state,all_refusals,refusal,trial,CLOSE_REASONS)

POLICY={'cycles':40,'warmup_cycles':5,'interval_seconds':15,'minimum_seconds':600,'maximum_seconds':720,'rss_absolute_kib':65536,'rss_range_kib':8192,'rss_end_mean_growth_kib':4096,'idle_fd_growth':0}

def identity(sample,initial):
    active_unit(sample['unit']);process_identity(sample['privileges'],sample['unit'],initial['privileges']['uid'])
    for field in ('MainPID','InvocationID','NRestarts'):require(sample['unit'][field]==initial['unit'][field],'Sustained process restarted')
    require(sample['process_start_ticks']==initial['process_start_ticks'] and type(sample['process_start_ticks']) is int and sample['process_start_ticks']>0,'Process identity changed')
    for field in ('rss_kib','fds','disk_allocated_bytes'):require(type(sample[field]) is int and sample[field]>0,'Resource sample missing')
    require(sample['rss_kib']<=POLICY['rss_absolute_kib'],'Absolute RSS limit exceeded')

def cycle_grant(row,epoch,seen):
    gid=row['grant_id']
    require(isinstance(gid,str) and str(uuid.UUID(gid))==gid and gid not in seen,'Cycle grant not new/unique')
    terminal=row['terminal']
    require(terminal['id']==gid and terminal['epoch']==epoch and terminal['persistence']=='COMMITTED' and
            terminal['state']==('REVOKED' if row['kind']=='revoke' else 'EXPIRED') and
            type(terminal['revision']) is int and terminal['revision']==3,'Terminal grant identity/state mismatch')
    if row['kind']=='revoke':
        result=row['revoke'];g=result['original_result']['grant']
        require(result['ok'] is True and result['historical'] is False and result['cleanup']=='COMPLETE' and
                result['original_result']['epoch']==epoch and
                all(g[k]==terminal[k] for k in ('id','state','revision','epoch')),'Revoke did not commit this cycle grant')
    seen.add(gid)

def degraded_catalog(status,catalog,epoch):
    rows=denied_state(status,epoch,True)
    persisted={g['id']:g for g in catalog['grants']}
    require(len(persisted)==len(catalog['grants'])==catalog['counts']['grants'] and rows.keys()==persisted.keys(),'DEGRADED catalog coverage incomplete')
    for gid,g in persisted.items():require(all(rows[gid][k]==g[k] for k in ('id','state','revision','epoch')),'DEGRADED status differs from catalog')
    return rows

def check_sustained(r):
    no_errors(r);require(r['passed'] is True and r['policy']==POLICY,'Sustained policy changed')
    require(number(r['seconds']) and POLICY['minimum_seconds']<=r['seconds']<=POLICY['maximum_seconds'],'Sustained observation too short/long')
    rows=r['cycles'];require(len(rows)==POLICY['cycles'] and r['config_limits']==dict(max_ops=512,max_events=512,max_grants=96),'Wrong finite workload/config')
    initial=r['initial'];identity(initial,initial);identity(r['final'],initial)
    last=r['initial_status'];epoch=last['epoch'];seen=set(denied_state(last,epoch,False))
    for i,row in enumerate(rows):
        no_errors(row);require(row['passed'] is True and row['index']==i and row['kind']==('revoke' if i%2==0 else 'expiry'),'Cycle missing/failed')
        trial(row['roundtrip']);refusal(row['old_data_refusal'],'NO_ACCESS')
        require(row['closure']['connection_ended'] is True and row['closure']['close_reason'] in CLOSE_REASONS,'Sustained closure missing')
        cycle_grant(row,epoch,seen)
        require(number(row['elapsed_seconds']) and i*15<=row['elapsed_seconds']<(i+1)*15 and 0<row['work_seconds']<15,'Cycle schedule exceeded')
        s=row['status'];require(s['health']=='READY' and s['degraded'] is False and s['sessions']==0 and s['all_denied'] is True,'Live authority after cycle')
        if epoch is None:epoch=s['epoch']
        require(s['epoch']==epoch,'Sustained epoch changed')
        identity(row['sample'],initial)
        require(row['sample']['rss_kib']<=POLICY['rss_absolute_kib'],'Absolute RSS limit exceeded')
        cap=s['capacity']
        for key in ('ops','events','grants'):
            c=cap[key];require(c['exact'] is True and c['full'] is False and 0<c['used']<c['limit']==r['config_limits']['max_'+key],'Unexpected capacity pressure')
        require(s['grant_count']==cap['grants']['used'],'Status pagination incomplete')
        if last:
            for key,step in (('ops',3 if row['kind']=='revoke' else 2),('events',3 if row['kind']=='revoke' else 2),('grants',1)):
                require(cap[key]['used']==last['capacity'][key]['used']+step,'Missing/extra catalog work')
            require(s['facts']['admitted']==last['facts']['admitted']+2 and s['facts']['closed']==last['facts']['closed']+2,'Session accounting mismatch')
        last=s
    check_resources([x['sample'] for x in rows[POLICY['warmup_cycles']:]],r['final'])
    return True

def check_resources(samples,final):
    require(len(samples)==35,'Missing post-warmup samples')
    rss=[x['rss_kib'] for x in samples]+[final['rss_kib']];fd=[x['fds'] for x in samples]
    require(max(rss)<=POLICY['rss_absolute_kib'] and max(rss)-min(rss)<=POLICY['rss_range_kib'],'Post-warmup RSS limit exceeded')
    require(sum(rss[-10:])/10-sum(rss[:10])/10<=POLICY['rss_end_mean_growth_kib'],'Post-warmup RSS trend exceeded')
    require(all(n==fd[0] for n in fd) and final['fds']==fd[0],'Idle FD accumulation')
    return True

def same_journal(a,b):
    require(a['sha256']==b['sha256'] and a['catalog']['counts']==b['catalog']['counts'] and a['catalog']['history_sha256']==b['catalog']['history_sha256'] and a['catalog']['grants']==b['catalog']['grants'],'Shutdown cleanup / lost journal before service')
    require({k:v['inode'] for k,v in a['catalog']['file_ids'].items()}=={k:v['inode'] for k,v in b['catalog']['file_ids'].items()},'Journal/lock replaced at boot')

def check_closeout(v):
    c=v['closeout'];no_errors(c)
    for mode in ('normal','readonly'):
        r=c[mode];no_errors(r);require(r['passed'] is True and r['mode']==mode,'Boot case failed')
        p=r['prepared'];w=r['witness'];no_errors(p);require(p['passed'] is True and p['enabled']==r['enabled']=='enabled','Service not enabled')
        require(p['boot_before']!=r['boot_after']==w['boot_id'] and w['before_gateway'] is True and w['service_uid_pids']==[],'No pre-service new-boot witness')
        require(w['backing_device_readonly']==0,'Unintended readonly backing device')
        require(w['storage_mode']==('ro' if mode=='readonly' else 'rw') and w['storage_mode'] in w['mount_options'].split(','),'Wrong boot mount')
        same_journal(p['before_shutdown'],w)
        require({'ACTIVE','PENDING'}<={g['state'] for g in w['catalog']['grants']},'No old live authority persisted')
        require(r['topology']['observed_ip_forward']==0 and r['topology']['forwarding'] is False and r['direct_backend']['direct_backend_refused'] is True,'Boot topology permits bypass')
        require(p['installed_unit_sha256']==v['source']['grantweft/systemd/grantweft.service'],'Boot unit differs from package')
        active_unit(p['unit']);process_identity(p['privileges'],p['unit'])
        active_unit(r['service']['unit']);process_identity(r['service']['privileges'],r['service']['unit'],p['privileges']['uid'])
        rows=retained_catalog(w['catalog'],r['after_recovery']['catalog']);st=denied_state(r['status_after_recovery'],r['epoch_after'],False)
        require(r['epoch_after']>p['epoch'] and rows.keys()==st.keys(),'Old grants missing')
        for gid,g in rows.items():require(all(g[k]==st[gid][k] for k in g),'Recovered status differs from catalog')
        all_refusals(r['old_data_refusals'],rows);refusal(r['stale_operation'],'STALE_EPOCH');trial(r['fresh_roundtrip'])
        fresh=r['fresh_retirement'];require(fresh['grant_id'] not in rows and fresh['revoke']['ok'] is True and fresh['revoke']['cleanup']=='COMPLETE' and fresh['revoke']['original_result']['grant']['id']==fresh['grant_id'] and fresh['revoke']['original_result']['grant']['state']=='REVOKED','Fresh verification grant left active')
        refusal(fresh['data_refusal'],'NO_ACCESS')
        polls=v['closeout_reboot_polls'][mode]
        require(polls and polls[-1]['exit_code']==0 and polls[-1]['timed_out'] is False and polls[-1]['boot_id']==r['boot_after'],'Boot polling missing')
        if mode=='readonly':
            refusal(p['live_refusal'],'STORAGE_FAILED');refusal(p['degraded_refusal'],'DEGRADED')
            before=degraded_catalog(p['degraded'],p['before_shutdown']['catalog'],p['epoch'])
            after=degraded_catalog(p['degraded_after_permission_repair'],p['before_shutdown']['catalog'],p['epoch'])
            require(before.keys()==after.keys(),'Online repair changed old grant coverage')
            all_refusals(p['degraded_old_data_refusals'],after)
            active_unit(p['unit_after_permission_repair'])
            for key in ('MainPID','InvocationID','NRestarts'):require(p['unit'][key]==p['unit_after_permission_repair'][key],'DEGRADED authority restarted during online repair')
            require(p['degraded']['failure']['sqlite_code'].startswith('SQLITE_READONLY') and p['degraded_after_permission_repair']['failure']==p['degraded']['failure'],'No actual retained preboot storage failure')
            f=r['failed_start'];same_journal(p['before_shutdown'],f['catalog_after_failed_starts'])
            for u in (f['unit'],f['stable_unit']):require(u['MainPID']=='0' and u['ActiveState']=='failed' and u['NRestarts']=='3','Readonly service did not stop retrying')
            require(f['service_uid_pids']==[] and f['readonly_error_traces']==3 and f['limit_message']=='Start request repeated too quickly' and f['stable_seconds']>=1,'Readonly rate limit missing')
            require(f['admission_refusal']['exit_code']!=0 and f['admission_refusal']['exception']=='ConnectionRefusedError','Faulted service accepted requests')
    check_sustained(c['sustained']);require(c['sustained']['cleanup']['errors']==[] and c['sustained']['cleanup']['owned_processes_reaped'] is True,'Sustained clients leaked')
    r=c['cleanup'];no_errors(r);require(r['passed'] is True and r['disabled'] is True and r['mount_removed'] is True and r['stopped']['old_pid_absent'] is True and r['stopped']['service_uid_pids']==[] and r['namespace_cleanup']['errors']==[] and r['namespace_cleanup']['namespaces_removed'] is True,'Closeout cleanup failed')
    return True
