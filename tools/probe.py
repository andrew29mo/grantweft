"""Qualification client executed in the client network namespace."""
import argparse,json,socket,time
from pathlib import Path
from grantweft.client import command,tunnel,send,receive
from grantweft.protocol import DATA,EOF,CLOSE

def main():
    p=argparse.ArgumentParser();p.add_argument('--pki',required=True);p.add_argument('--who',default='a')
    p.add_argument('--host',default='10.70.0.1');p.add_argument('--mode',choices=['control','echo','hold','direct'],required=True)
    p.add_argument('--request');p.add_argument('--grant');p.add_argument('--marker');a=p.parse_args()
    r=Path(a.pki);cred=(r/'ca.pem',r/(a.who+'.pem'),r/(a.who+'.key'))
    if a.mode=='control':
        print(json.dumps(command(a.host,7443,*cred,json.loads(a.request))));return
    if a.mode=='direct':
        try:
            with socket.create_connection(('10.71.0.2',9000),timeout=.5):pass
        except OSError:print(json.dumps({'direct_backend_refused':True}));return
        raise RuntimeError('Client bypassed gateway')
    with tunnel(a.host,7444,*cred,a.grant,'demo') as s:
        if a.mode=='hold':
            send(s,DATA,b'before-revoke');assert receive(s)==(DATA,b'before-revoke')
            Path(a.marker).write_text('open');start=time.monotonic();s.settimeout(4)
            try:receive(s)
            except (OSError,EOFError):print(json.dumps({'connection_ended':True,'observed_seconds':time.monotonic()-start}));return
            raise RuntimeError('Unexpected live-session data')
        payload=b'vm-ordered-payload'+b'x'*(8192-18);start=time.monotonic()
        for _ in range(20):
            send(s,DATA,payload);assert receive(s)==(DATA,payload)
        print(json.dumps({'roundtrips':20,'payload_bytes_per_roundtrip':len(payload),'seconds':time.monotonic()-start,'verified_bytes_each_direction':20*len(payload)}))
if __name__=='__main__':main()
