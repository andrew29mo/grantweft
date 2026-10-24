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
