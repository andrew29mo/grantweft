"""Install the shipped systemd unit. Linux root setup; gateway stays unprivileged."""
import argparse
import grp
import os
from pathlib import Path
import platform
import pwd
import subprocess
import sys

UNIT='grantweft.service'

def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    if platform.system()!='Linux' or os.geteuid()!=0:
        raise SystemExit('Linux root is required for installation')
    if Path(sys.prefix).resolve()!=Path('/opt/grantweft/venv'):
        raise SystemExit('Install runtime wheel in /opt/grantweft/venv first')
    try:user=pwd.getpwnam('grantweft')
    except KeyError:
        subprocess.run(['useradd','--system','--user-group','--home-dir','/var/lib/grantweft','--shell','/usr/sbin/nologin','grantweft'],check=True)
        user=pwd.getpwnam('grantweft')
    group=grp.getgrnam('grantweft')
    if user.pw_uid==0 or user.pw_gid!=group.gr_gid:
        raise SystemExit('Unsafe existing service account')
    config=Path('/etc/grantweft')
    if not config.exists():
        config.mkdir(mode=0o750);os.chown(config,0,group.gr_gid)
    unit=Path('/etc/systemd/system')/UNIT
    unit.write_bytes((Path(__file__).parent/'systemd'/UNIT).read_bytes())
    os.chmod(unit,0o644)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    print('Installed unit. Provision root-owned configuration and TLS files; then systemctl start grantweft.')

if __name__=='__main__':main()
