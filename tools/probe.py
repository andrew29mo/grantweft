"""Qualification client executed in the client network namespace."""
import argparse,json,socket,time,ssl
from pathlib import Path
from grantweft.client import command,tunnel,send,receive
from grantweft.protocol import DATA,EOF,CLOSE

def wait_closed(s, timeout=4):
    """Positive transport EOF/reset only. Idle timeout is failed observation."""
    until=time.monotonic()+timeout
    while True:
        left=until-time.monotonic()
        if left<=0:raise RuntimeError('CLOSE_NOT_OBSERVED')
        s.settimeout(left)
        try:
            k,b=receive(s)
            if k==DATA:raise RuntimeError('Unexpected data while observing closure')
            if k not in (EOF,6):raise RuntimeError('Unexpected control while observing closure')
        except TimeoutError as exc:
            raise RuntimeError('CLOSE_NOT_OBSERVED') from exc
        except (EOFError,ConnectionResetError,ssl.SSLEOFError,ssl.SSLZeroReturnError) as exc:
            return {'connection_ended':True,'close_reason':type(exc).__name__}

def echo_roundtrip(s,payload):
    send(s,DATA,payload);parts=[];left=len(payload)
    while left:
        k,b=receive(s)
        if k!=DATA or not b or len(b)>left:raise RuntimeError('Unexpected echo response')
        parts.append(b);left-=len(b)
    if b''.join(parts)!=payload:raise RuntimeError('Echo content/order mismatch')

def main():
    if not __debug__:raise RuntimeError("Qualification requires normal Python")
    p=argparse.ArgumentParser();p.add_argument('--pki',required=True);p.add_argument('--who',default='a')
    p.add_argument('--host',default='10.70.0.1');p.add_argument('--mode',choices=['control','echo','hold','direct'],required=True)
    p.add_argument('--request');p.add_argument('--grant');p.add_argument('--marker');a=p.parse_args()
    r=Path(a.pki);cred=(r/'ca.pem',r/(a.who+'.pem'),r/(a.who+'.key'))
    if a.mode=='control':
        print(json.dumps(command(a.host,7443,*cred,json.loads(a.request))));return
    if a.mode=='direct':
        try:
            with socket.create_connection(('10.71.0.2',9000),timeout=.5):pass
        except OSError as exc:print(json.dumps({'direct_backend_refused':True,'failure_reason':type(exc).__name__}));return
        raise RuntimeError('Client bypassed gateway')
    with tunnel(a.host,7444,*cred,a.grant,'demo') as s:
        if a.mode=='hold':
            echo_roundtrip(s,b'before-revoke')
            Path(a.marker).write_text('open');start=time.monotonic()
            result=wait_closed(s)
            print(json.dumps(result|{'observed_seconds':time.monotonic()-start}));return
        payload=b'vm-ordered-payload'+b'x'*(8192-18);start=time.monotonic()
        for _ in range(20):
            echo_roundtrip(s,payload)
        print(json.dumps({'roundtrips':20,'payload_bytes_per_roundtrip':len(payload),'seconds':time.monotonic()-start,'verified_bytes_each_direction':20*len(payload)}))
if __name__=='__main__':main()
