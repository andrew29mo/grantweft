import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import socketserver
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from grantweft.client import command, tunnel, send, receive
from grantweft.protocol import DATA, EOF, CLOSE, Refused

def certs(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    def run(*args):subprocess.run(['openssl',*map(str,args)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
    run('req','-x509','-newkey','rsa:2048','-nodes','-keyout',root/'ca.key','-out',root/'ca.pem','-subj','/CN=Grantweft test CA','-days','2')
    for name in ('server','a','b','approver','unknown'):
        run('req','-newkey','rsa:2048','-nodes','-keyout',root/(name+'.key'),'-out',root/(name+'.csr'),'-subj','/CN='+name)
        ext=root/(name+'.ext');ext.write_text('subjectAltName=DNS:localhost,IP:127.0.0.1,IP:10.70.0.1\nextendedKeyUsage='+('serverAuth' if name=='server' else 'clientAuth')+'\n')
        run('x509','-req','-in',root/(name+'.csr'),'-CA',root/'ca.pem','-CAkey',root/'ca.key','-CAcreateserial','-out',root/(name+'.pem'),'-days','2','-extfile',ext)
    return root

def fingerprint(path):
    return hashlib.sha256(ssl.PEM_cert_to_DER_cert(Path(path).read_text())).hexdigest()

class Backend(socketserver.ThreadingTCPServer):
    allow_reuse_address=True;daemon_threads=True
    def __init__(self,host='127.0.0.1',port=0,mode='echo'):
        self.mode=mode;self.received=bytearray();self.conn=0;self.closed=0;self.allow_read=threading.Event()
        parent=self
        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                parent.conn+=1;self.request.settimeout(4)
                if parent.mode=='blocked':
                    self.request.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,4096)
                    parent.allow_read.wait(4)
                try:
                    while True:
                        b=self.request.recv(16384)
                        if not b:
                            if parent.mode=='half':self.request.sendall(b'after-eof:'+bytes(parent.received))
                            break
                        parent.received.extend(b)
                        if parent.mode=='echo':self.request.sendall(b)
                        if parent.mode=='slow':time.sleep(.1)
                except OSError:pass
                finally:parent.closed+=1
        super().__init__((host,port),Handler)
        self.thread=threading.Thread(target=self.serve_forever,daemon=True);self.thread.start()
    def close(self):self.allow_read.set();self.shutdown();self.server_close();self.thread.join()

class Harness:
    def __init__(self,pki,root=None,backend=None,**limits):
        self.base=Path(root or tempfile.mkdtemp(prefix='gw-')).resolve();self.base.mkdir(parents=True,exist_ok=True)
        self.pki=pki;self.backend=backend or Backend();self.owns_backend=backend is None
        self.store=self.base/'store';self.barriers=self.base/'barriers';self.barriers.mkdir(exist_ok=True)
        self.cfg={'cert':str(pki/'server.pem'),'key':str(pki/'server.key'),'ca':str(pki/'ca.pem'),
                  'service':{'id':'demo','host':self.backend.server_address[0],'port':self.backend.server_address[1]},
                  'control':{'host':'127.0.0.1','port':0},'data':{'host':'127.0.0.1','port':0},
                  'principals':{n:{'sha256':fingerprint(pki/(n+'.pem')),'role':'approver' if n=='approver' else 'requester'} for n in ('a','b','approver')},**limits}
        self.config=self.base/'config.json';self.config.write_text(json.dumps(self.cfg));self.proc=None
        self.start()
    def start(self):
        ready=self.store/'ready.json'
        if ready.exists():ready.unlink()
        self.log=open(self.base/'gateway.log','ab')
        self.proc=subprocess.Popen([sys.executable,'-m','grantweft.gateway','--config',str(self.config),'--root',str(self.store),'--barriers',str(self.barriers)],stdout=self.log,stderr=self.log)
        until=time.monotonic()+5
        while time.monotonic()<until:
            if ready.exists():
                self.ready=json.loads(ready.read_text());return
            if self.proc.poll() is not None:raise RuntimeError('Gateway startup failed: '+(self.base/'gateway.log').read_text()[-2000:])
            time.sleep(.02)
        raise TimeoutError('Gateway readiness')
    def stop(self,kill=False):
        if self.proc and self.proc.poll() is None:
            self.proc.kill() if kill else self.proc.terminate()
            try:self.proc.wait(timeout=4)
            except subprocess.TimeoutExpired:self.proc.kill();self.proc.wait(timeout=2);raise
        if hasattr(self,'log'):self.log.close()
    def close(self):
        self.stop()
        if self.owns_backend:self.backend.close()
    def credentials(self,who='a'):
        return (self.pki/'ca.pem',self.pki/(who+'.pem'),self.pki/(who+'.key'))
    def call(self,who,request):return command('127.0.0.1',self.ready['ports']['control'],*self.credentials(who),request)
    def status(self,who='approver'):return self.call(who,{'action':'status'})
    def mutate(self,who,action,grant=None,**kwargs):
        p={'action':action,'operation':str(uuid.uuid4()),'epoch':self.ready['epoch'],**kwargs}
        if grant:p.update(grant=grant['id'],revision=grant['revision'])
        return self.call(who,p)
    def request(self,who='a',duration=5):
        return self.mutate(who,'request',service='demo',duration=duration)['original_result']['grant']
    def approve(self,g):return self.mutate('approver','approve',g)['original_result']['grant']
    def access(self,g,who='a'):return tunnel('127.0.0.1',self.ready['ports']['data'],*self.credentials(who),g['id'],'demo')
    def wait(self,predicate,seconds=3):
        until=time.monotonic()+seconds
        while time.monotonic()<until:
            if predicate():return
            time.sleep(.02)
        raise TimeoutError('Condition not observed')
