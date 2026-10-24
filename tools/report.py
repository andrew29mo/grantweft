"""Receipt validation has explicit checks; optimization cannot disable them."""
import copy,html,json,math,hashlib

def require(condition,message):
    if not condition:raise ValueError(message)

def verify(v):
    require(v['passed'] is True,'Run not passed')
    require(v['source_changed'] is False,'Source changed during qualification')
    require(hashlib.sha256(json.dumps(v['source'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==v['source_sha256'],'Invalid source fingerprint')
    for key in ('native','linux'):
        r=v[key];require(r['passed'] is True and r['count']>=25 and not (r['failures'] or r['errors'] or r['skipped']),'Unit failure')
        require(r['source']==v['source'] and r['source_sha256']==v['source_sha256'],'Unit source mismatch')
    require(v['native']['tests']==v['linux']['tests'],'Platform test sets differ')
    for name in ('test_slow_commit_does_not_start_new_ttl','test_revoke_during_delayed_approval_cannot_reopen','test_process_pause_crosses_ttl_no_fresh_transfer_after_resume','test_second_process_cannot_take_lock_or_recover','test_bounded_db_queue_does_not_block_revoke_fence','test_slow_db_does_not_block_live_expiry','test_db_timeout_late_completion_cannot_reactivate','test_slow_consumer_revoke_discards_unsent_data','test_delayed_connected_session_cannot_survive_revoke'):
        require('test_gateway.GatewayTests.'+name in v['linux']['tests'],'Required formal test missing')
    require(v['host_mounts']=='none' and v['wheel_modules_match'] is True and v['installed_source_absent'] is True,'Unqualified installation')
    require(v['installed_modules']=={k:h for k,h in v['source'].items() if k.startswith('grantweft/')},'Installed modules differ')
    require(v['vm_deleted'] is True and v['disk_removed'] is True and v['preexisting_profiles_unchanged'] is True,'Cleanup incomplete')
    require(all(s['exit_code']==0 and s['timed_out'] is False and math.isfinite(s['seconds']) and s['seconds']>=0 for s in v['stages']),'Stage failed or timed out')
    for key in ('cases','prepared','finished'):
        c=v[key];require(c['passed'] is True and c['cleanup']['owned_processes_reaped'] is c['cleanup']['namespaces_removed'] is True,'VM scenario incomplete')
        require(c['direct_backend']=={'direct_backend_refused':True} and c['gateway_uid']==65534,'Isolation/permissions missing')
    f=v['finished'];p=v['prepared']
    require(p['gateway_killed_before_reboot'] is True and f['boot_before']==p['boot_before'] and f['boot_before']!=f['boot_after'],'No actual reboot')
    require(f['journal_before']==p['journal_before']==f['journal_after_before_gateway'],'Shutdown cleanup masquerades as recovery')
    require(f['old_grants_invalidated'] is f['stale_operation_refused'] is f['old_data_refused'] is True,'Reboot authority not fenced')
    require(v['limits']==dict(power_loss_tested=False,suspend_tested=False,systemd_autostart_tested=False,long_term_tested=False),'Unsupported claim')
    trial=v['cases']['roundtrip_trial'];require(trial['roundtrips']==20 and trial['payload_bytes_per_roundtrip']==8192 and trial['verified_bytes_each_direction']==163840 and 0<trial['seconds']<60,'Wrong workload')
    r=v['cases']['revocation_trial'];require(r['cleanup']=='COMPLETE' and r['sessions_after']==0 and r['client_observation']['connection_ended'] is True and 0<r['rpc_seconds']<10,'No revocation evidence')
    require(v['cases']['resources']['rss_kib']>0,'RSS missing')
    return True

def controls(v):
    mutations=[lambda x:x.update(passed=False),lambda x:x.update(source_sha256='wrong'),lambda x:x['native'].update(passed=False),lambda x:x['linux'].update(skipped=1),lambda x:x['linux']['tests'].pop(),lambda x:x.update(source_changed=True),lambda x:x.update(installed_source_absent=False),lambda x:x['stages'][0].update(timed_out=True),lambda x:x['stages'][0].update(exit_code=1),lambda x:x['finished'].update(boot_after=x['finished']['boot_before']),lambda x:x['prepared'].update(gateway_killed_before_reboot=False),lambda x:x['finished']['journal_after_before_gateway'].update(sha256='wrong'),lambda x:x['finished'].update(old_data_refused=False),lambda x:x['cases']['direct_backend'].update(direct_backend_refused=False),lambda x:x['cases'].update(gateway_uid=0),lambda x:x.update(vm_deleted=False),lambda x:x['limits'].update(power_loss_tested=True),lambda x:x['cases']['revocation_trial'].update(sessions_after=1),lambda x:x['cases']['roundtrip_trial'].update(verified_bytes_each_direction=0)]
    for mutate in mutations:
        b=copy.deepcopy(v);mutate(b)
        try:verify(b)
        except (ValueError,KeyError,TypeError):pass
        else:raise ValueError('Corrupted receipt accepted')
    return {'passed':True,'rejected':len(mutations)}

def render(v):
    return '<!doctype html><html lang="en"><meta charset="utf-8"><title>Grantweft explorations</title><style>body{font:16px system-ui;max-width:1050px;margin:32px auto;padding:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Grantweft: four bounded technical explorations</h1><p>Formal mTLS service, installed package, client/gateway/backend namespaces. Single controlled Linux VM observations, not native/physical performance or an SLO. Normal VM reboot only; no power loss, actual suspend or systemd autostart qualification. Approval/revocation revision conflicts conservatively degrade the service. Production readiness is not claimed.</p><p>Passed: '+str(v.get('passed',False))+'</p><pre>'+html.escape(json.dumps(v,indent=2,allow_nan=False))+'</pre></html>'
