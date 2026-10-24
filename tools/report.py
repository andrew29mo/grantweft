"""Versioned evidence contract; explicit checks also run under python -O."""
import copy,html,json,math,hashlib,uuid
CONTRACT='grantweft-recovery-review-v4'
STAGES=('initial','create','dependencies','upload','install','provenance','native','linux','linux-read','cases','cases-read','recovery','recovery-read','prepare','prepared-read','schedule-reboot','finish','finished-read','delete','final')
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

def verify(v):
    require(v['contract']==CONTRACT and v['passed'] is True,'Wrong contract/not passed')
    no_errors(v)
    require(v['source_changed'] is False,'Source changed during qualification')
    require(hashlib.sha256(json.dumps(v['source'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==v['source_sha256'],'Invalid source fingerprint')
    for key,system in [('native','Darwin'),('linux','Linux')]:
        r=v[key];require(r['platform']==system and r['passed'] is True and r['count']>=42 and r['count']==len(r['tests'])==len(set(r['tests'])) and not (r['failures'] or r['errors'] or r['skipped']),'Unit failure/platform/count')
        require(r['source']==v['source'] and r['source_sha256']==v['source_sha256'],'Unit source mismatch')
    require(v['native']['tests']==v['linux']['tests'],'Platform test sets differ')
    names=('test_slow_commit_does_not_start_new_ttl','test_revoke_during_delayed_approval_cannot_reopen','test_process_pause_crosses_ttl_no_fresh_transfer_after_resume','test_second_process_cannot_take_lock_or_recover','test_bounded_db_queue_does_not_block_revoke_fence','test_slow_db_does_not_block_live_expiry','test_db_timeout_late_completion_cannot_reactivate','test_slow_consumer_revoke_discards_unsent_data','test_delayed_connected_session_cannot_survive_revoke','test_history_result_is_stable_after_expiry_and_restart','test_slow_approval_history_retains_original_commit','test_observed_backpressure_then_revoke_stops_transfer','test_full_ops_and_events_still_stop_access_and_recover_with_limits','test_grant_full_preserves_revoke_and_expiry_without_gc','test_catalog_full_expiry_does_not_need_new_audit_slot','test_storage_repair_requires_restart_and_preserves_history','test_slow_commit_after_retirement_stays_denied_through_repair','test_expiry_write_failure_degrades_and_repair_does_not_revive','test_sqlite_full_closes_live_access_and_recovers_with_page_budget','test_duplicate_identity_exits_before_creating_store_or_worker')
    require(all('test_gateway.GatewayTests.'+n in v['linux']['tests'] for n in names),'Formal test missing')
    for name in ('test_close_observer_rejects_live_idle_socket_timeout','test_close_observer_requires_positive_eof','test_cleanup_continues_after_forced_kill','test_cleanup_exception_still_saves_failed_receipt','test_startup_process_registered_before_readiness_failure'):
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
    require(v['limits']==dict(power_loss_tested=False,suspend_tested=False,systemd_autostart_tested=False,long_term_tested=False),'Unsupported claim')
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
    for mutate in mutations:
        b=copy.deepcopy(v);mutate(b)
        try:verify(b)
        except (ValueError,KeyError,TypeError):pass
        else:raise ValueError('Corrupted receipt accepted')
    return {'passed':True,'rejected':len(mutations)}

def render(v):
    return '<!doctype html><html lang="en"><meta charset="utf-8"><title>Grantweft recovery milestone</title><style>body{font:16px system-ui;max-width:1050px;margin:32px auto;padding:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Grantweft: bounded recovery milestone</h1><p>Formal mTLS service, installed package, client/gateway/backend namespaces. Positive EOF/reset is required; timeout is not termination. Controlled Linux VM observations, not native/physical performance or an SLO. Normal reboot only; no power loss, actual suspend or systemd autostart qualification. Approval/revocation revision conflicts conservatively degrade the service. Actual tmpfs exhaustion, live directory write denial, readonly-filesystem startup and SQLite page-budget failures are exercised. Recovery preserves the catalog and requires repair plus restart; no online reset or automatic GC. Production readiness is not claimed.</p><p>Passed: '+str(v.get('passed',False))+'</p><pre>'+html.escape(json.dumps(v,indent=2,allow_nan=False))+'</pre></html>'
