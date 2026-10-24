"""Adversarial controls for evidence observers, not product-pass substitutes."""
import copy
import io
import json
from pathlib import Path
import socket
import subprocess
import unittest
from unittest.mock import patch
from tools.probe import wait_closed,echo_roundtrip
from tools import vm_cases
from grantweft.protocol import DATA,HEADER

class EvidenceObserverTests(unittest.TestCase):
    def test_close_observer_rejects_live_idle_socket_timeout(self):
        a,b=socket.socketpair()
        try:
            with self.assertRaisesRegex(RuntimeError,'CLOSE_NOT_OBSERVED'):wait_closed(a,.03)
        finally:a.close();b.close()
    def test_close_observer_requires_positive_eof(self):
        a,b=socket.socketpair();b.close()
        try:self.assertEqual(wait_closed(a,.03)['close_reason'],'EOFError')
        finally:a.close()
    def test_echo_observer_accepts_fragmentation_and_checks_order(self):
        a,b=socket.socketpair()
        try:
            b.sendall(HEADER.pack(DATA,2)+b'ab'+HEADER.pack(DATA,2)+b'cd')
            echo_roundtrip(a,b'abcd')
            b.sendall(HEADER.pack(DATA,4)+b'abce')
            with self.assertRaisesRegex(RuntimeError,'content/order'):echo_roundtrip(a,b'abcd')
        finally:a.close();b.close()
    def test_cleanup_continues_after_forced_kill(self):
        class Fake:
            returncode=None
            def __init__(self,stuck):self.stuck=stuck;self.terminated=False
            def poll(self):return self.returncode
            def terminate(self):self.terminated=True
            def kill(self):self.returncode=-9
            def wait(self,timeout):
                if self.stuck and self.returncode is None:raise subprocess.TimeoutExpired('fake',timeout)
                self.returncode=self.returncode if self.returncode is not None else 0
        a,b=Fake(False),Fake(True)
        with patch.object(vm_cases,'ip',return_value='') as ip:
            result=vm_cases.cleanup([(a,io.StringIO()),(b,io.StringIO())],['one','two'])
        self.assertTrue(a.terminated and b.terminated)
        self.assertTrue(result['owned_processes_reaped'] and result['namespaces_removed'])
        self.assertTrue(result['errors']);self.assertEqual(ip.call_count,4)
    def test_cleanup_exception_still_saves_failed_receipt(self):
        v={'passed':True}
        with patch.object(vm_cases,'cleanup',side_effect=RuntimeError),patch.object(vm_cases,'save') as save:
            vm_cases.finish_receipt(v,[],[],'failed')
        self.assertFalse(v['passed']);save.assert_called_once_with('failed',v)
    def test_startup_process_registered_before_readiness_failure(self):
        import tempfile
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory(prefix='gw-ready-') as path:
            procs=[];proc=Mock();proc.poll.return_value=None
            with patch.object(vm_cases,'LAB',Path(path)),patch.object(vm_cases.subprocess,'Popen',return_value=proc),patch.object(vm_cases,'wait',side_effect=TimeoutError):
                with self.assertRaises(TimeoutError):vm_cases.start_backend(procs)
            self.assertEqual(len(procs),1);self.assertIs(procs[0][0],proc);procs[0][1].close()
    def test_service_status_rejects_allowed_or_incomplete_old_authority(self):
        from tools.report import denied_state
        r={'ok':True,'epoch':4,'degraded':True,'health':'DEGRADED','sessions':0,
           'remaining_after_cursor':0,'next_cursor':None,
           'grants':[{'id':'old','access':'DENIED','sessions':0}]}
        self.assertEqual(set(denied_state(r,4,True)),{'old'})
        for change in (lambda x:x.update(health='READY'),lambda x:x.update(sessions=5),
                       lambda x:x['grants'][0].update(access='ALLOWED'),
                       lambda x:x.update(remaining_after_cursor=1),lambda x:x.update(grants=[])):
            bad=copy.deepcopy(r);change(bad)
            with self.assertRaises(ValueError):denied_state(bad,4,True)
    def test_service_catalog_requires_old_grant_invalidation(self):
        from tools.report import retained_catalog
        a={'counts':{'grants':1,'ops':2,'events':2},'history_sha256':'a'*64,
           'file_ids':{'catalog.sqlite':{'device':1,'inode':1},'writer.lock':{'device':1,'inode':2}},
           'grants':[{'id':'old','state':'ACTIVE','revision':2,'epoch':4}]}
        b=copy.deepcopy(a);b['grants'][0].update(state='INVALIDATED',revision=3)
        self.assertEqual(retained_catalog(a,b)['old']['state'],'INVALIDATED')
        for bad in (copy.deepcopy(a),b|{'grants':[]},b|{'grants':[b['grants'][0]|{'revision':2}]}):
            with self.assertRaises(ValueError):retained_catalog(a,bad)
        with self.assertRaises(KeyError):retained_catalog(a,{k:v for k,v in b.items() if k!='grants'})
    def test_boot_journal_witness_rejects_shutdown_cleanup_or_replacement(self):
        from tools.closeout_contract import same_journal
        a={'sha256':'a'*64,'catalog':{'counts':{'grants':1},'history_sha256':'b'*64,
           'grants':[{'id':'old','state':'ACTIVE'}],
           'file_ids':{'catalog.sqlite':{'inode':1,'device':1},'writer.lock':{'inode':2,'device':1}}}}
        b=copy.deepcopy(a);b['catalog']['file_ids']['writer.lock']['device']=2
        same_journal(a,b)  # Device number can change across a VM boot; inode/content cannot.
        for change in (lambda x:x.update(sha256='c'*64),
                       lambda x:x['catalog']['grants'][0].update(state='INVALIDATED'),
                       lambda x:x['catalog']['file_ids']['writer.lock'].update(inode=3)):
            bad=copy.deepcopy(b);change(bad)
            with self.assertRaises(ValueError):same_journal(a,bad)
    def test_sustained_observer_rejects_process_identity_change(self):
        from tools.closeout_contract import identity
        from tools.report import SERVICE_ARGV
        u=dict(ActiveState='active',SubState='running',LoadState='loaded',Result='success',
               MainPID='99',InvocationID='a'*32,NRestarts='0',User='grantweft',Group='grantweft',
               Type='notify',Restart='on-failure',KillMode='control-group',ProtectSystem='strict',
               NoNewPrivileges='yes',CapabilityBoundingSet='',StartLimitBurst='3',
               StartLimitIntervalUSec='30s',RestartUSec='1s',TimeoutStopUSec='5s')
        s={'unit':u,'privileges':dict(uid=996,uids=[996]*4,pid=99,argv=SERVICE_ARGV,
           effective_capabilities='0',no_new_privileges=1),'process_start_ticks':20,
           'rss_kib':25000,'fds':10,'disk_allocated_bytes':32768}
        identity(s,s)
        for change in (lambda x:x['unit'].update(InvocationID='b'*32),
                       lambda x:x['unit'].update(NRestarts='1'),
                       lambda x:x.update(process_start_ticks=21),
                       lambda x:x['privileges'].update(uids=[0]*4)):
            bad=copy.deepcopy(s);change(bad)
            with self.assertRaises(ValueError):identity(bad,s)
        bad=copy.deepcopy(s);bad['rss_kib']=1048576
        with self.assertRaisesRegex(ValueError,'Absolute RSS'):identity(bad,bad)
    def test_sustained_resource_limits_are_fixed_and_detect_growth(self):
        from tools.closeout_contract import check_resources
        samples=[{'rss_kib':25000,'fds':10} for _ in range(35)]
        check_resources(samples,samples[-1])
        for changed in (samples[:-1],samples[:-1]+[{'rss_kib':25000,'fds':11}],
                        samples[:-1]+[{'rss_kib':34000,'fds':10}],
                        samples[:20]+[{'rss_kib':30000,'fds':10} for _ in range(15)]):
            with self.assertRaises(ValueError):check_resources(changed,samples[-1])
        with self.assertRaises(ValueError):check_resources(samples,{'rss_kib':25000,'fds':11})
    def test_readonly_degraded_catalog_rejects_live_or_missing_authority(self):
        from tools.closeout_contract import degraded_catalog
        g=dict(id='old',state='ACTIVE',revision=2,epoch=5)
        catalog={'grants':[g],'counts':{'grants':1}}
        status={'ok':True,'epoch':5,'degraded':True,'health':'DEGRADED','sessions':0,
                'remaining_after_cursor':0,'next_cursor':None,
                'grants':[g|{'access':'DENIED','sessions':0}]}
        self.assertEqual(set(degraded_catalog(status,catalog,5)),{'old'})
        for mutate in (lambda x:x.update(sessions=1),
                       lambda x:x['grants'][0].update(access='ALLOWED',sessions=1),
                       lambda x:x.update(grants=[]),
                       lambda x:x['grants'][0].update(revision=3),
                       lambda x:x.update(epoch=6)):
            bad=copy.deepcopy(status);mutate(bad)
            with self.assertRaises(ValueError):degraded_catalog(bad,catalog,5)
    def test_sustained_cycle_requires_new_matching_committed_grant(self):
        from tools.closeout_contract import cycle_grant
        gid='f458daee-50c0-4821-9e3b-fbd458301aaa'
        terminal=dict(id=gid,state='REVOKED',revision=3,epoch=7,persistence='COMMITTED')
        row={'grant_id':gid,'kind':'revoke','terminal':terminal,
             'revoke':{'ok':True,'historical':False,'cleanup':'COMPLETE',
                       'original_result':{'epoch':7,'grant':{k:v for k,v in terminal.items() if k!='persistence'}}}}
        seen=set();cycle_grant(row,7,seen);self.assertEqual(seen,{gid})
        with self.assertRaises(ValueError):cycle_grant(row,7,seen)
        for mutate in (lambda x:x['revoke']['original_result']['grant'].update(id='unrelated'),
                       lambda x:x['revoke'].update(historical=True),
                       lambda x:x['terminal'].update(epoch=6),
                       lambda x:x['terminal'].update(revision=4)):
            bad=copy.deepcopy(row);mutate(bad)
            with self.assertRaises(ValueError):cycle_grant(bad,7,set())
