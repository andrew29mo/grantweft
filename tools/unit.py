import argparse
import hashlib
import io
import json
from pathlib import Path
import platform
import sys
import time
import unittest
import grantweft

def manifest():
    root=Path(__file__).resolve().parents[1]
    paths=[root/'pyproject.toml']
    for folder in ('tools','tests'):
        paths += [p for p in (root/folder).rglob('*.py') if '__pycache__' not in p.parts]
    out={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
    product=Path(grantweft.__file__).resolve().parent
    out.update({'grantweft/'+p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in product.glob('*.py')})
    return dict(sorted(out.items()))
def fingerprint(m):return hashlib.sha256(json.dumps(m,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
    if not __debug__:raise RuntimeError('Validation requires normal Python')
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    suite=unittest.defaultTestLoader.discover('tests')
    def ids(s):return [v for child in s for v in ids(child)] if isinstance(s,unittest.TestSuite) else [s.id()]
    names=ids(suite);stream=io.StringIO();start=time.monotonic()
    r=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    value={'passed':r.wasSuccessful() and not r.skipped,'count':r.testsRun,'tests':names,'failures':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped),'seconds':time.monotonic()-start,'platform':platform.system(),'source':manifest(),'source_sha256':fingerprint(manifest())}
    Path(a.output).write_text(json.dumps(value,indent=2)+'\n');print(stream.getvalue());raise SystemExit(0 if value['passed'] else 1)
if __name__=='__main__':main()
