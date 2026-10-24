"""Deterministic backend fixture; never part of the gateway package."""
import argparse,signal,time
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from support import Backend
p=argparse.ArgumentParser();p.add_argument('--root',required=True);a=p.parse_args()
b=Backend('10.71.0.2',9000)
Path(a.root,'backend-ready').write_text('ready')
signal.signal(signal.SIGTERM,lambda *_:sys.exit(0))
try:
    while True:time.sleep(.1)
finally:b.close()
