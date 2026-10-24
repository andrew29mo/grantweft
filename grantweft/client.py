"""mTLS control client and framed single-session connector."""
import argparse
import json
import socket
import ssl
import sys
from .protocol import OPEN, OK, ERROR, DATA, EOF, CLOSE, HEADER, MAX_FRAME, Refused, encode, decode

def context(ca, cert, key):
    ctx=ssl.create_default_context(ssl.Purpose.SERVER_AUTH,cafile=str(ca))
    ctx.minimum_version=ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(str(cert),str(key));ctx.options|=ssl.OP_NO_TICKET
    return ctx

def connect(host,port,ca,cert,key):
    raw=socket.create_connection((host,port),timeout=3)
    try:return context(ca,cert,key).wrap_socket(raw,server_hostname=host)
    except BaseException:raw.close();raise

def exact(s,n):
    parts=[]
    while n:
        b=s.recv(n)
        if not b:raise EOFError('Connection ended')
        parts.append(b);n-=len(b)
    return b''.join(parts)

def send(s,k,b=b''):
    if len(b)>MAX_FRAME:raise Refused('FRAME_SIZE')
    s.sendall(HEADER.pack(k,len(b))+b)

def receive(s):
    k,n=HEADER.unpack(exact(s,HEADER.size))
    if k not in (DATA,EOF,CLOSE,OPEN,OK,ERROR) or n>MAX_FRAME or (k in (EOF,CLOSE) and n):raise Refused('FRAME_FORMAT')
    return k,exact(s,n)

def command(host,port,ca,cert,key,request):
    with connect(host,port,ca,cert,key) as s:
        send(s,OPEN,encode(request));k,b=receive(s);result=decode(b)
        if k==ERROR:raise Refused(result['code'])
        if k!=OK:raise Refused('RESPONSE')
        return result

def tunnel(host,port,ca,cert,key,grant,service):
    s=connect(host,port,ca,cert,key)
    try:
        send(s,OPEN,encode({'grant':grant,'service':service}));k,b=receive(s)
        if k==ERROR:raise Refused(decode(b)['code'])
        if k!=OK:raise Refused('RESPONSE')
        return s
    except BaseException:s.close();raise

def main():
    p=argparse.ArgumentParser();p.add_argument('--host',required=True);p.add_argument('--port',type=int,required=True)
    for key in ('ca','cert','key'):p.add_argument('--'+key,required=True)
    p.add_argument('--request',help='Control JSON object; omit with --grant for stdin/stdout connector')
    p.add_argument('--grant');p.add_argument('--service',default='demo');a=p.parse_args()
    if a.request:
        print(json.dumps(command(a.host,a.port,a.ca,a.cert,a.key,decode(a.request.encode()))));return
    if not a.grant:p.error('--request or --grant required')
    # stdio connector has no shared local TCP listener or extra identity boundary.
    with tunnel(a.host,a.port,a.ca,a.cert,a.key,a.grant,a.service) as s:
        import threading
        def upload():
            try:
                while True:
                    b=sys.stdin.buffer.read1(MAX_FRAME)
                    if not b:send(s,EOF);break
                    send(s,DATA,b)
            except (OSError,EOFError):pass
        worker=threading.Thread(target=upload,daemon=True);worker.start()
        while True:
            k,b=receive(s)
            if k==DATA:sys.stdout.buffer.write(b);sys.stdout.buffer.flush()
            elif k==EOF:send(s,CLOSE);break
            else:raise Refused('FRAME_STATE')
if __name__=='__main__':main()
