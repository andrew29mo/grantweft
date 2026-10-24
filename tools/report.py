"""Versioned evidence contract; explicit checks also run under python -O."""
import copy,html,json,math,hashlib,uuid
CONTRACT='grantweft-closeout-v7'
STAGES=('initial','create','dependencies','upload','install','provenance','native','linux','linux-read','cases','cases-read','recovery','recovery-read','service','service-read','prepare','prepared-read','schedule-reboot','finish','finished-read','boot-prepare-normal','boot-prepared-normal-read','boot-schedule-normal','boot-finish-normal','boot-finished-normal-read','boot-prepare-readonly','boot-prepared-readonly-read','boot-schedule-readonly','boot-finish-readonly','boot-finished-readonly-read','sustain','sustained-read','closeout-cleanup','closeout-cleanup-read','delete','final')
CLOSE_REASONS=('EOFError','ConnectionResetError','SSLEOFError','SSLZeroReturnError')

def require(condition,message):
    if not condition:raise ValueError(message)

def number(x):return type(x) in (int,float) and math.isfinite(x)

def refusal(r,code):
    require(type(r['exit_code']) is int and r['exit_code']!=0 and r['code']==code,'Missing/contradictory refusal')

def no_errors(r):
    require(not any(k in r for k in ('error','verification_error','cleanup_error','mount_cleanup_error')),'Explicit failure marker')

def trial(r):
    require(r['roundtrips']==20 and r['payload_bytes_per_roundtrip']==8192 and r['verified_bytes_each_direction']==163840 and number(r['seconds']) and 0<r['seconds']<60,'Wrong workload')

SERVICE_ARGV=['/opt/grantweft/venv/bin/python','-m','grantweft.gateway','--config','/etc/grantweft/config.json','--root','/var/lib/grantweft','--notify']

def active_unit(u):
    require(u['ActiveState']=='active' and u['SubState']=='running' and u['LoadState']=='loaded' and u['Result']=='success' and u['MainPID'].isdigit() and int(u['MainPID'])>0,'Takeover unit is not running')
    require(len(u['InvocationID'])==32 and uuid.UUID(hex=u['InvocationID']).hex==u['InvocationID'],'Missing service invocation')
    require(u['User']==u['Group']=='grantweft' and u['Type']=='notify' and u['Restart']=='on-failure' and u['KillMode']=='control-group' and u['ProtectSystem']=='strict' and u['NoNewPrivileges']=='yes' and u['CapabilityBoundingSet']=='','Unsafe unit configuration')
    require(u['StartLimitBurst']=='3' and u['StartLimitIntervalUSec']=='30s' and u['RestartUSec']=='1s' and u['TimeoutStopUSec']=='5s','Unexpected service budgets')

def process_identity(p,u,uid=None):
    require(type(p['uid']) is int and p['uid']>0 and (uid is None or p['uid']==uid) and p['uids']==[p['uid']]*4 and type(p['pid']) is int and p['pid']==int(u['MainPID']),'Wrong process identity')
    require(p['argv']==SERVICE_ARGV and int(p['effective_capabilities'],16)==0 and p['no_new_privileges']==1,'Wrong process command/privileges')

def denied_state(r,epoch,degraded):
    require(r['ok'] is True and r['epoch']==epoch and r['degraded'] is degraded and r['health']==('DEGRADED' if degraded else 'READY'),'Inconsistent service health')
    require(r['sessions']==0 and r['remaining_after_cursor']==0 and r['next_cursor'] is None,'Incomplete or live old sessions')
    rows={g['id']:g for g in r['grants']}
    require(rows and len(rows)==len(r['grants']) and all(g['access']=='DENIED' and g['sessions']==0 for g in rows.values()),'Old effective authority allowed')
    return rows

def retained_catalog(a,b):
    for key in ('counts','history_sha256','file_ids'):require(a[key]==b[key],'Service repair lost catalog')
    require(len(a['history_sha256'])==64 and all(c in '0123456789abcdef' for c in a['history_sha256']),'Missing service history digest')
    require(set(a['file_ids'])=={'catalog.sqlite','writer.lock'} and all(type(f['inode']) is int and f['inode']>0 and type(f['device']) is int for f in a['file_ids'].values()),'Missing service file identities')
    require(set(a['counts'])=={'grants','ops','events'} and all(type(n) is int and n>0 for n in a['counts'].values()),'Missing service catalog counts')
    old={g['id']:g for g in a['grants']};new={g['id']:g for g in b['grants']}
    require(old and len(old)==len(a['grants'])==a['counts']['grants'] and len(new)==len(b['grants'])==b['counts']['grants'] and old.keys()==new.keys(),'Service catalog rows lost')
    for gid,g in old.items():
        expected=g|({'state':'INVALIDATED','revision':g['revision']+1} if g['state'] in ('PENDING','ACTIVE') else {})
        require(new[gid]==expected,'Service old grant not invalidated')
    return new

def all_refusals(refs,rows):
    require(refs.keys()==rows.keys(),'Missing old-grant admission probe')
    for r in refs.values():refusal(r,'NO_ACCESS')

def verify(v):
    require(v['contract']==CONTRACT and v['passed'] is True,'Wrong contract/not passed')
    no_errors(v)
    require(v['source_changed'] is False,'Source changed during qualification')
    require(hashlib.sha256(json.dumps(v['source'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==v['source_sha256'],'Invalid source fingerprint')
    for key,system in [('native','Darwin'),('linux','Linux')]:
        r=v[key];require(r['platform']==system and r['passed'] is True and r['count']>=49 and r['count']==len(r['tests'])==len(set(r['tests'])) and not (r['failures'] or r['errors'] or r['skipped']),'Unit failure/platform/count')
        require(r['source']==v['source'] and r['source_sha256']==v['source_sha256'],'Unit source mismatch')
    require(v['native']['tests']==v['linux']['tests'],'Platform test sets differ')
    names=('test_slow_commit_does_not_start_new_ttl','test_revoke_during_delayed_approval_cannot_reopen','test_process_pause_crosses_ttl_no_fresh_transfer_after_resume','test_second_process_cannot_take_lock_or_recover','test_bounded_db_queue_does_not_block_revoke_fence','test_slow_db_does_not_block_live_expiry','test_db_timeout_late_completion_cannot_reactivate','test_slow_consumer_revoke_discards_unsent_data','test_delayed_connected_session_cannot_survive_revoke','test_history_result_is_stable_after_expiry_and_restart','test_slow_approval_history_retains_original_commit','test_observed_backpressure_then_revoke_stops_transfer','test_full_ops_and_events_still_stop_access_and_recover_with_limits','test_grant_full_preserves_revoke_and_expiry_without_gc','test_catalog_full_expiry_does_not_need_new_audit_slot','test_storage_repair_requires_restart_and_preserves_history','test_slow_commit_after_retirement_stays_denied_through_repair','test_expiry_write_failure_degrades_and_repair_does_not_revive','test_sqlite_full_closes_live_access_and_recovers_with_page_budget','test_duplicate_identity_exits_before_creating_store_or_worker','test_readiness_notification_requires_socket_and_sends_ready','test_startup_receipt_is_not_visible_until_complete')
    require(all('test_gateway.GatewayTests.'+n in v['linux']['tests'] for n in names),'Formal test missing')
    for name in ('test_close_observer_rejects_live_idle_socket_timeout','test_close_observer_requires_positive_eof','test_cleanup_continues_after_forced_kill','test_cleanup_exception_still_saves_failed_receipt','test_startup_process_registered_before_readiness_failure','test_service_status_rejects_allowed_or_incomplete_old_authority','test_service_catalog_requires_old_grant_invalidation','test_boot_journal_witness_rejects_shutdown_cleanup_or_replacement','test_sustained_observer_rejects_process_identity_change','test_sustained_resource_limits_are_fixed_and_detect_growth'):
        require('test_review.EvidenceObserverTests.'+name in v['linux']['tests'],'Observer negative control missing')
    require(v['host_mounts']=='none' and v['wheel_modules_match'] is True and v['installed_source_absent'] is True,'Unqualified installation')
    require(v['installed_modules']=={k:h for k,h in v['source'].items() if k.startswith('grantweft/')},'Installed modules differ')
    require(v['vm_deleted'] is True and v['disk_removed'] is True and v['preexisting_profiles_unchanged'] is True,'Cleanup incomplete')
    stages=tuple(s['name'] for s in v['stages'])
    require(stages in (STAGES,STAGES[:-1]+('delete-disk','final')),'Missing/duplicate/reordered stages')
    require(all(type(s['exit_code']) is int and s['exit_code']==0 and s['timed_out'] is False and number(s['seconds']) and s['seconds']>=0 for s in v['stages']),'Stage failed or timed out')
    for key in ('cases','prepared','finished','recovery'):
        c=v[key];no_errors(c);require(c['passed'] is True and c['cleanup']['owned_processes_reaped'] is c['cleanup']['namespaces_removed'] is True and c['cleanup']['errors']==[],'VM scenario/cleanup incomplete')
        require(c['direct_backend']['direct_backend_refused'] is True and c['direct_backend']['failure_reason'] in ('TimeoutError','ConnectionRefusedError','OSError') and c['gateway_uid']==65534,'Isolation/permissions missing')
        require(c['topology']['forwarding'] is False and c['topology']['observed_ip_forward']==0,'Forwarding state unobserved')
    recovery=v['recovery']
    modes=('ops_full','events_full','grant_full','sqlite_full','disk_full','read_only','late_commit')
    require(tuple(r['mode'] for r in recovery['scenarios'])==modes,'Missing recovery scenario')
    for r in recovery['scenarios']:
        mode=r['mode'];no_errors(r);require(r['passed'] is True and r['epoch_after']>r['epoch_before'],'Recovery failed/epoch')
        require(r['closure']['connection_ended'] is True and r['closure']['close_reason'] in CLOSE_REASONS,'Recovery closure unobserved')
        require(number(r['fault_phase_seconds']) and 0<r['fault_phase_seconds']<30,'Fault phase timing missing')
        before=r['status_before_repair'];after=r['status_after_repair']
        require(after['degraded'] is False and after['health']=='READY' and all(g['access']=='DENIED' for g in after['grants'] if g['epoch']!=after['epoch']),'Recovery authority unsafe')
        require(before['epoch']==r['epoch_before'] and after['epoch']==r['epoch_after'],'Status epoch mismatch')
        old={g['id']:g for g in before['grants']};new={g['id']:g for g in after['grants']}
        require(old and old.keys()<=new.keys(),'Old grant rows lost')
        require(all(new[gid]['access']=='DENIED' for gid in old),'Old grants reactivated')
        a=r['catalog_before_restart'];b=r['catalog_after_boot']
        require(a['counts']==b['counts'] and a['history_sha256']==b['history_sha256'] and a['file_ids']==b['file_ids'],'Catalog/history replaced or changed')
        require(len(a['history_sha256'])==64 and all(c in '0123456789abcdef' for c in a['history_sha256']),'Missing history digest')
        require(set(a['file_ids'])=={'catalog.sqlite','writer.lock'} and all(type(x['inode']) is int and x['inode']>0 and type(x['device']) is int for x in a['file_ids'].values()),'Store identities missing')
        persisted={g['id']:g for g in a['grants']};booted={g['id']:g for g in b['grants']}
        require(persisted and persisted.keys()==booted.keys() and old.keys()<=persisted.keys(),'Catalog rows lost')
        for gid,g in persisted.items():
            expected=g|({'state':'INVALIDATED','revision':g['revision']+1} if g['state'] in ('PENDING','ACTIVE') else {})
            require(booted[gid]==expected,'Boot did not invalidate old authority')
        for name,extra in (('ops',2),('events',2),('grants',1)):
            cap=after['capacity'][name]
            require(type(a['counts'][name]) is int and a['counts'][name]>=before['capacity'][name]['used'] and a['counts'][name]>0,'Committed count inconsistent')
            require(cap['exact'] is True and cap['used']==a['counts'][name]+extra and cap['limit']>=cap['used'] and cap['full']==(cap['used']>=cap['limit']),'Recovered capacity inconsistent')
        require(r['resources']['rss_kib']>0 and r['resources']['fds']>0 and r['resources']['disk_allocated_bytes']>0,'Recovery resources absent')
        for key,code in [('old_data_refusal','NO_ACCESS'),('old_after_restart_refusal','NO_ACCESS'),('stale_refusal','STALE_EPOCH')]:
            refusal(r[key],code)
        if mode in ('ops_full','events_full','grant_full'):
            refusal(r['admission_refusal'],'GRANT_FULL' if mode=='grant_full' else 'CATALOG_FULL')
        if mode=='grant_full':
            revoke=r['revoke'];gr=revoke['original_result']['grant']
            require(revoke['ok'] is True and revoke['historical'] is False and revoke['cleanup']=='COMPLETE' and gr['state']=='REVOKED' and gr['id'] in old,'Grant-full revoke failed')
            require(before['degraded'] is False and before['health']=='READY' and old[gr['id']]['state']=='REVOKED' and old[gr['id']]['persistence']=='COMMITTED','Grant-full revoke did not commit')
        if mode!='grant_full':
            require(before['degraded'] is True and before['health']=='DEGRADED' and before['recovery']['required'] is True and before['recovery']['online_reset_supported'] is False,'Degraded recovery not explicit')
            require(before['failure']['code'] and all(c['exact'] is False for c in before['capacity'].values()),'Degraded diagnostics absent')
            refusal(r['refusal'],'CATALOG_FULL' if mode in ('ops_full','events_full') else 'STORAGE_FAILED')
        if mode in ('sqlite_full','disk_full'):require(before['failure']['sqlite_code']=='SQLITE_FULL','No real SQLite FULL')
        if mode=='disk_full':require(r['free_bytes_after_fill']==0,'Filesystem not full')
        if mode=='read_only':require(before['failure']['sqlite_code'].startswith('SQLITE_READONLY') and r['readonly_restart_refusal']['exit_code']!=0 and ('Read-only file system' in r['readonly_restart_refusal']['exception'] or 'readonly database' in r['readonly_restart_refusal']['exception']) and r['live_fault']=='directory-write-permission-removed' and r['startup_fault']=='actual-readonly-filesystem','No real readonly refusal')
        if mode=='late_commit':
            require(r['late_commit_observed_on_disk'] is r['degraded_before_release'] is True,'Late completion not exercised')
            for key in ('late_data_refusal','late_after_restart_refusal','late_after_replay_refusal'):refusal(r[key],'NO_ACCESS')
            replay=r['late_history_replay'];grant=replay['original_result']['grant']
            require(replay['ok'] is True and replay['historical'] is True and grant['state']=='ACTIVE' and persisted[grant['id']]['state']=='ACTIVE','Late history lost/re-executed')
            require(replay['current']['epoch']==after['epoch'] and all(g['access']=='DENIED' for g in replay['current']['grants']),'Historical replay activated access')
        trial(r['fresh_roundtrip'])
    service=v['service'];no_errors(service)
    require(service['passed'] is True and service['test_override_removed'] is True and service['cleanup']['errors']==[] and service['cleanup']['owned_processes_reaped'] is service['cleanup']['namespaces_removed'] is True,'Service cleanup failed')
    require(service['topology']['forwarding'] is False and service['topology']['observed_ip_forward']==0 and service['direct_backend']['direct_backend_refused'] is True and service['direct_backend']['failure_reason'] in ('TimeoutError','ConnectionRefusedError','OSError'),'Service isolation missing')
    require(service['test_override']=={'network_namespace_only':True,'exec_start_unchanged':True},'Altered service execution')
    require(service['installed_unit_sha256']==v['source']['grantweft/systemd/grantweft.service'],'Wrong installed unit')
    initial=service['initial'];u=initial['unit'];priv=initial['privileges']
    active_unit(u);process_identity(priv,u)
    trial(service['workload']['roundtrip'])
    for k in ('rss_kib','fds','disk_allocated_bytes'):require(type(service['workload'][k]) is int and service['workload'][k]>0,'Service resource missing')
    for key in ('normal_stop','forced_stop'):
        r=service[key];require(r['old_pid_absent'] is True and r['service_uid_pids']==[] and r['unit']['MainPID']=='0','Service process leaked')
        require(r['closure']['connection_ended'] is True and r['closure']['close_reason'] in CLOSE_REASONS and number(r['seconds']) and 0<r['seconds']<12,'Service stop not observed')
    require(service['normal_stop']['unit']['ActiveState']=='inactive' and service['normal_stop']['remained_stopped_after_seconds']>=1,'Explicit stop restarted')
    r=service['normal_restart'];require(r['epoch']>initial['epoch'],'Normal restart did not fence')
    active_unit(r['unit']);process_identity(r['privileges'],r['unit'],priv['uid'])
    normal_rows=denied_state(r['status_after_boot'],r['epoch'],False);require(r['grant_id'] in normal_rows and normal_rows[r['grant_id']]['state']=='INVALIDATED','Normal restart forgot old grant')
    refusal(r['old_data'],'NO_ACCESS');refusal(r['old_operation'],'STALE_EPOCH')
    r=service['crash_takeover'];require(r['before']['MainPID']!=r['after']['MainPID'] and r['before']['InvocationID']!=r['after']['InvocationID'] and int(r['after']['NRestarts'])>int(r['before']['NRestarts']) and r['epoch_after']>r['epoch_before'],'No actual systemd takeover')
    active_unit(r['before']);active_unit(r['after']);process_identity(r['privileges'],r['after'],priv['uid'])
    require(r['closure']['connection_ended'] is True and r['closure']['close_reason'] in CLOSE_REASONS,'Crash takeover closure')
    after_crash=denied_state(r['status_after_boot'],r['epoch_after'],False)
    before_crash={g['id']:g for g in r['status_before']['grants']}
    require(r['status_before']['epoch']==r['epoch_before'] and before_crash and before_crash.keys()==after_crash.keys() and r['grant_id'] in before_crash,'Crash grant rows missing')
    for gid,g in before_crash.items():
        require({k:after_crash[gid][k] for k in ('id','state','revision','epoch')}==({k:g[k] for k in ('id','state','revision','epoch')}|({'state':'INVALIDATED','revision':g['revision']+1} if g['state'] in ('PENDING','ACTIVE') else {})),'Crash did not invalidate old authority')
    refusal(r['old_data'],'NO_ACCESS');refusal(r['old_operation'],'STALE_EPOCH');trial(r['fresh_roundtrip'])
    r=service['degraded'];refusal(r['refusal'],'CATALOG_FULL');refusal(r['admission_refusal'],'DEGRADED')
    degraded_rows=denied_state(r['status'],r['status']['epoch'],True);all_refusals(r['old_data_refusals'],degraded_rows)
    require(r['status']['failure']['code']=='CATALOG_FULL' and r['status']['capacity']['ops']['full'] is True,'No actual catalog degradation')
    active_unit(r['unit_before']);active_unit(r['unit_after_wait'])
    require(r['status']['degraded'] is True and r['unit_before']['MainPID']==r['unit_after_wait']['MainPID'] and r['unit_before']['InvocationID']==r['unit_after_wait']['InvocationID'] and r['unit_before']['NRestarts']==r['unit_after_wait']['NRestarts'] and r['wait_seconds']>=1 and r['closure']['connection_ended'] is True and r['closure']['close_reason'] in CLOSE_REASONS,'DEGRADED silently restarted')
    r=service['repair'];require(r['epoch_after']>r['epoch_before'],'Repair did not advance epoch')
    active_unit(r['unit']);process_identity(r['privileges'],r['unit'],priv['uid'])
    persisted=retained_catalog(r['catalog_before'],r['catalog_after'])
    repaired_rows=denied_state(r['status_after_boot'],r['epoch_after'],False)
    require(r['epoch_before']==service['degraded']['status']['epoch'] and degraded_rows.keys()==persisted.keys()==repaired_rows.keys() and r['grant_id'] in repaired_rows,'Repair lost old status rows')
    for gid,g in persisted.items():require(all(repaired_rows[gid][k]==g[k] for k in ('id','state','revision','epoch')),'Repair status differs from catalog')
    all_refusals(r['old_data_refusals'],repaired_rows)
    refusal(r['old_data'],'NO_ACCESS');refusal(r['old_operation'],'STALE_EPOCH');trial(r['fresh_roundtrip'])
    require(service['forced_stop']['unit']['Result']=='timeout' and service['forced_stop']['injection']=='root-ptrace-stop' and service['forced_stop']['trace_stop_observed'] is True and service['forced_stop']['termination_signal']==9,'Stop timeout not exercised')
    r=service['forced_stop']['recovery'];active_unit(r['unit']);process_identity(r['privileges'],r['unit'],priv['uid']);forced_rows=denied_state(r['status_after_boot'],r['epoch_after'],False);require(r['grant_id'] in forced_rows and forced_rows[r['grant_id']]['state']=='INVALIDATED','Forced stop old grant lost');require(r['epoch_after']>r['epoch_before'],'Forced stop recovery stale');refusal(r['old_data'],'NO_ACCESS');refusal(r['old_operation'],'STALE_EPOCH');trial(r['fresh_roundtrip'])
    r=service['restart_limit'];require(r['failure_reason']=='DUPLICATE_IDENTITY' and r['observed_failure_traces']==3,'Restart failure cause unobserved')
    require(r['limit_message']=='Start request repeated too quickly' and r['stable_seconds']>=1 and r['unit_after_wait']['NRestarts']==r['unit']['NRestarts']=='3' and r['unit_after_wait']['MainPID']=='0' and r['unit_after_wait']['ActiveState']=='failed' and r['unit']['Result'] in ('exit-code','start-limit-hit') and r['unit']['ActiveState']=='failed' and r['unit']['MainPID']=='0' and r['service_uid_pids']==[],'No restart limit')
    require(r['catalog_before']==r['catalog_after'],'Invalid startup changed state')
    require(r['repair']['epoch_after']>r['repair']['epoch_before'],'Restart limit not repaired');active_unit(r['repair']['unit']);process_identity(r['repair']['privileges'],r['repair']['unit'],priv['uid']);denied_state(r['repair']['status_after_boot'],r['repair']['epoch_after'],False);trial(r['repair']['fresh_roundtrip'])
    require(service['final_stopped']['old_pid_absent'] is True and service['final_stopped']['service_uid_pids']==[] and service['final_stopped']['unit']['MainPID']=='0','Final service leaked')
    f=v['finished'];p=v['prepared']
    require(p['gateway_killed_before_reboot'] is True and f['boot_before']==p['boot_before'] and f['boot_before']!=f['boot_after'],'No actual reboot')
    for boot in (f['boot_before'],f['boot_after']):require(str(uuid.UUID(boot))==boot,'Invalid boot identity')
    require(f['journal_before']==p['journal_before']==f['journal_after_before_gateway'],'Shutdown cleanup masquerades as recovery')
    rows={r[0]:r for r in p['journal_before']['grants']}
    for name,state in [('active','ACTIVE'),('pending','PENDING')]:
        g=p[name];r=rows[g['id']];require(r[3]==state and r[7]==p['epoch'],'Wrong pre-reboot state')
        recovered={g['id']:g for g in f['recovered_grants']}
        require(recovered[g['id']]['state']=='INVALIDATED' and recovered[g['id']]['access']=='DENIED','Old state not invalidated')
    require(f['epoch_after']>p['epoch'] and f['old_grants_invalidated'] is f['stale_operation_refused'] is f['old_data_refused'] is True,'Reboot authority not fenced')
    require(f['old_data_refusal']['exit_code']!=0 and f['old_data_refusal']['code']=='NO_ACCESS' and f['stale_operation_refusal']['exit_code']!=0 and f['stale_operation_refusal']['code']=='STALE_EPOCH','No actual stale refusals')
    polls=v['reboot_polls'];require(polls and polls[-1]['exit_code']==0 and polls[-1]['timed_out'] is False and polls[-1]['boot_id']==f['boot_after'],'Reboot observation missing')
    from .closeout_contract import check_closeout
    check_closeout(v)
    require(v['limits']==dict(power_loss_tested=False,suspend_tested=False,systemd_autostart_tested=True,long_term_tested=False,boot_zero_gap_tested=False),'Unsupported claim')
    trial(v['cases']['roundtrip_trial']);trial(f['fresh_roundtrip'])
    r=v['cases']['revocation_trial'];o=r['client_observation']
    require(r['cleanup']=='COMPLETE' and r['sessions_after']==0 and o['connection_ended'] is True and o['close_reason'] in CLOSE_REASONS and number(o['observed_seconds']) and 0<o['observed_seconds']<5 and number(r['rpc_seconds']) and 0<r['rpc_seconds']<10,'No positive revocation closure')
    r=v['cases']['resources'];require(number(r['rss_kib']) and r['rss_kib']>0 and type(r['fds']) is int and r['fds']>0 and type(r['disk_allocated_bytes']) is int and r['disk_allocated_bytes']>0,'Resource observation missing')
    return True

def controls(v):
    mutations=[lambda x:x.update(passed=False),lambda x:x.update(contract='old'),lambda x:x.update(source_sha256='wrong'),lambda x:x['native'].update(passed=False),lambda x:x['linux'].update(skipped=1),lambda x:x['linux']['tests'].pop(),lambda x:x['linux'].update(platform='Darwin'),lambda x:x['native'].update(platform='Linux'),lambda x:x['linux'].update(count=999),lambda x:x.update(source_changed=True),lambda x:x.update(installed_source_absent=False),lambda x:x.update(stages=[]),lambda x:x['stages'].pop(3),lambda x:x['stages'][0].update(timed_out=True),lambda x:x['stages'][0].update(exit_code=1),lambda x:x['finished'].update(boot_after=x['finished']['boot_before']),lambda x:x['prepared'].update(gateway_killed_before_reboot=False),lambda x:x['finished']['journal_after_before_gateway'].update(sha256='wrong'),lambda x:x['finished'].update(old_data_refused=False),lambda x:x['cases']['direct_backend'].update(direct_backend_refused=False),lambda x:x['cases']['topology'].update(observed_ip_forward=1),lambda x:x['cases'].update(gateway_uid=0),lambda x:x.update(vm_deleted=False),lambda x:x['limits'].update(power_loss_tested=True),lambda x:x['cases']['revocation_trial'].update(sessions_after=1),lambda x:x['cases']['revocation_trial']['client_observation'].update(close_reason='TimeoutError'),lambda x:x['cases']['roundtrip_trial'].update(verified_bytes_each_direction=0),lambda x:x['finished'].pop('fresh_roundtrip'),lambda x:x['finished']['fresh_roundtrip'].update(verified_bytes_each_direction=0),lambda x:x['cases']['cleanup'].update(errors=['forced-kill']),lambda x:x['finished'].update(epoch_after=x['prepared']['epoch']),lambda x:x['finished']['old_data_refusal'].update(exit_code=0),lambda x:x.update(reboot_polls=[])]
    mutations += [lambda x:x.pop('recovery'),lambda x:x['recovery']['scenarios'].pop(),
                  lambda x:x['recovery']['scenarios'][0]['closure'].update(close_reason='TimeoutError'),
                  lambda x:x['recovery']['scenarios'][0].update(epoch_after=x['recovery']['scenarios'][0]['epoch_before']),
                  lambda x:x['recovery']['scenarios'][4].update(free_bytes_after_fill=4096),
                  lambda x:x['recovery']['scenarios'][3]['status_before_repair']['failure'].update(sqlite_code='SQLITE_ERROR'),
                  lambda x:x['recovery']['scenarios'][5]['readonly_restart_refusal'].update(exit_code=0),
                  lambda x:x['recovery']['scenarios'][6].update(late_commit_observed_on_disk=False),
                  lambda x:x['recovery']['scenarios'][0]['status_after_repair'].update(degraded=True)]
    mutations += [lambda x:x['recovery']['scenarios'][6]['late_data_refusal'].update(exit_code=0),
                  lambda x:x['recovery']['scenarios'][6]['late_after_restart_refusal'].pop('exit_code'),
                  lambda x:x['recovery']['scenarios'][6]['late_after_replay_refusal'].update(exit_code=0),
                  lambda x:x['recovery']['scenarios'][0].pop('admission_refusal'),
                  lambda x:x['recovery']['scenarios'][1]['admission_refusal'].update(exit_code=0),
                  lambda x:x['recovery']['scenarios'][2]['admission_refusal'].update(code='UNEXPECTED'),
                  lambda x:x['recovery']['scenarios'][2].pop('revoke'),
                  lambda x:x['recovery']['scenarios'][2]['revoke']['original_result']['grant'].update(state='ACTIVE'),
                  lambda x:x['recovery']['scenarios'][2]['status_before_repair'].update(degraded=True),
                  lambda x:x['recovery']['scenarios'][0]['status_after_repair'].update(grants=[]),
                  lambda x:x['recovery']['scenarios'][0]['status_after_repair']['capacity']['ops'].update(used=0),
                  lambda x:x['recovery']['scenarios'][0]['catalog_after_boot'].update(history_sha256='0'*64),
                  lambda x:x['recovery']['scenarios'][0]['catalog_after_boot']['file_ids']['writer.lock'].update(inode=0),
                  lambda x:x.update(cleanup_error='RuntimeError'),
                  lambda x:x['recovery'].update(cleanup_error='RuntimeError'),
                  lambda x:x['recovery'].update(mount_cleanup_error=True),
                  lambda x:x['recovery']['scenarios'][0]['refusal'].update(code='UNEXPECTED'),
                  lambda x:x['recovery']['scenarios'][6]['late_history_replay'].update(historical=False)]
    mutations += [lambda x:x.pop('service'),lambda x:x['service']['initial']['privileges'].update(uid=0),
                  lambda x:x['service']['initial']['unit'].update(Type='simple'),
                  lambda x:x['service']['initial']['unit'].update(CapabilityBoundingSet='cap_net_admin'),
                  lambda x:x['service']['crash_takeover']['after'].update(InvocationID=x['service']['crash_takeover']['before']['InvocationID']),
                  lambda x:x['service']['degraded']['unit_after_wait'].update(MainPID='0'),
                  lambda x:x['service']['repair']['catalog_after'].update(history_sha256='0'*64),
                  lambda x:x['service']['restart_limit'].update(limit_message='no observed limit'),
                  lambda x:x['service']['forced_stop']['unit'].update(Result='success'),
                  lambda x:x['service']['normal_stop']['closure'].update(close_reason='TimeoutError'),
                  lambda x:x['service'].update(installed_unit_sha256='wrong'),
                  lambda x:x['service']['test_override'].update(exec_start_unchanged=False)]
    mutations += [lambda x:x['service'].pop('topology'),lambda x:x['service'].pop('direct_backend'),
                  lambda x:x['service']['topology'].update(forwarding=True),lambda x:x['service']['topology'].update(observed_ip_forward=1),
                  lambda x:x['service']['direct_backend'].update(direct_backend_refused=False),
                  lambda x:x['service']['crash_takeover']['privileges'].update(uids=[996,0,0,0]),
                  lambda x:x['service']['crash_takeover']['privileges'].update(argv=['/tmp/other.py']),
                  lambda x:x['service']['crash_takeover']['privileges'].update(pid=0),
                  lambda x:x['service']['crash_takeover']['after'].update(MainPID='0'),
                  lambda x:x['service']['crash_takeover']['after'].update(ActiveState='inactive'),
                  lambda x:x['service']['crash_takeover']['after'].update(InvocationID=''),
                  lambda x:x['service']['degraded']['status'].update(health='READY'),
                  lambda x:x['service']['degraded']['status'].update(sessions=5),
                  lambda x:x['service']['degraded']['status']['grants'][0].update(access='ALLOWED'),
                  lambda x:x['service']['degraded']['status'].update(remaining_after_cursor=1),
                  lambda x:x['service']['degraded']['old_data_refusals'].clear(),
                  lambda x:x['service']['degraded']['admission_refusal'].update(exit_code=0),
                  lambda x:x['service']['repair']['catalog_after'].update(grants=copy.deepcopy(x['service']['repair']['catalog_before']['grants'])),
                  lambda x:x['service']['repair']['catalog_before'].pop('grants'),
                  lambda x:x['service']['repair']['status_after_boot']['grants'][0].update(access='ALLOWED'),
                  lambda x:x['service']['repair']['old_data_refusals'].clear(),
                  lambda x:x['service']['forced_stop']['recovery']['privileges'].update(no_new_privileges=0),
                  lambda x:x['service']['restart_limit']['repair']['unit'].update(MainPID='0')]
    mutations += [lambda x:x.pop('closeout'),
                  lambda x:x['closeout']['normal'].pop('fresh_retirement'),
                  lambda x:x['closeout']['readonly']['fresh_retirement']['data_refusal'].update(exit_code=0),
                  lambda x:x['closeout']['normal'].update(enabled='disabled'),
                  lambda x:x['closeout']['normal']['witness'].update(before_gateway=False),
                  lambda x:x['closeout']['normal']['witness'].update(boot_id=x['closeout']['normal']['prepared']['boot_before']),
                  lambda x:x['closeout']['normal']['witness'].update(service_uid_pids=[1]),
                  lambda x:x['closeout']['normal']['witness'].update(sha256='0'*64),
                  lambda x:x['closeout']['normal']['service']['privileges'].update(uid=0),
                  lambda x:x['closeout']['normal']['old_data_refusals'].clear(),
                  lambda x:x['closeout']['readonly']['witness'].update(mount_options='rw'),
                  lambda x:x['closeout']['readonly']['failed_start'].update(readonly_error_traces=0),
                  lambda x:x['closeout']['readonly']['failed_start']['stable_unit'].update(NRestarts='4'),
                  lambda x:x['closeout']['readonly']['failed_start']['admission_refusal'].update(exit_code=0),
                  lambda x:x['closeout']['readonly']['after_recovery']['catalog'].update(grants=[]),
                  lambda x:x['closeout']['sustained'].update(seconds=100),
                  lambda x:x['closeout']['sustained']['policy'].update(rss_range_kib=999999),
                  lambda x:x['closeout']['sustained']['cycles'].pop(),
                  lambda x:x['closeout']['sustained']['cycles'][10]['sample']['unit'].update(InvocationID='0'*32),
                  lambda x:x['closeout']['sustained']['cycles'][10]['sample'].update(process_start_ticks=0),
                  lambda x:x['closeout']['sustained']['cycles'][10]['sample'].update(fds=999),
                  lambda x:x['closeout']['sustained']['cycles'][10]['sample'].update(rss_kib=999999),
                  lambda x:x['closeout']['sustained']['cycles'][10]['status'].update(sessions=1),
                  lambda x:x['closeout']['sustained']['cycles'][10]['closure'].update(close_reason='TimeoutError'),
                  lambda x:x['closeout']['sustained']['cycles'][10]['terminal'].update(state='ACTIVE'),
                  lambda x:x['closeout']['cleanup'].update(mount_removed=False),
                  lambda x:x['limits'].update(boot_zero_gap_tested=True)]
    for mutate in mutations:
        b=copy.deepcopy(v);mutate(b)
        try:verify(b)
        except (ValueError,KeyError,TypeError):pass
        else:raise ValueError('Corrupted receipt accepted')
    return {'passed':True,'rejected':len(mutations)}

def render(v):
    return '<!doctype html><html lang="en"><meta charset="utf-8"><title>Grantweft recovery milestone</title><style>body{font:16px system-ui;max-width:1050px;margin:32px auto;padding:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Grantweft: bounded recovery milestone</h1><p>Formal mTLS service, installed package, client/gateway/backend namespaces. Positive EOF/reset is required; timeout is not termination. Controlled Linux VM observations, not native/physical performance or an SLO. Qualification scope includes the installed systemd unit: start/stop, crash restart, restart limiting and manual DEGRADED repair; consult the pass flag and per-case outcomes. Additional closeout checks cover enabled systemd boot startup with a read-only pre-service journal witness, a persistent readonly ext4 boot fault and explicit repair, plus a fixed 40-cycle/ten-minute same-process observation. No sudden power loss, actual suspend, boot-zero-gap or long-term qualification. Approval/revocation revision conflicts conservatively degrade the service. Actual tmpfs exhaustion, live directory write denial, readonly-filesystem startup and SQLite page-budget failures are exercised. Recovery preserves the catalog and requires repair plus restart; no online reset or automatic GC. Production readiness is not claimed.</p><p>Passed: '+str(v.get('passed',False))+'</p><pre>'+html.escape(json.dumps(v,indent=2,allow_nan=False))+'</pre></html>'
