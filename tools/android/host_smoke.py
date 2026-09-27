#!/usr/bin/env python3
"""Run the APK's exact guest payload through the matching PRoot on native ARM64 Linux."""
import argparse
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from prepare_assets import fetch, digest

ROOT=Path(__file__).resolve().parents[2]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--assets',type=Path,default=ROOT/'out/android/assets/runtime')
    p.add_argument('--proot',type=Path,default=ROOT/'out/android/native/linux-arm64')
    p.add_argument('--work',type=Path,default=ROOT/'out/android/host-smoke')
    a=p.parse_args()
    if platform.machine().lower() not in ('aarch64','arm64'):raise RuntimeError('Native ARM64 Linux is required')
    if a.work.exists():raise RuntimeError('Use a fresh owned smoke directory')
    a.work.mkdir(parents=True)
    lock=json.loads((ROOT/'android/runtime-lock.json').read_text())
    base=fetch(lock['base'],ROOT/'out/android/cache/base.tar.gz')
    wine=fetch(lock['wine'],ROOT/'out/android/cache/wine.tar.gz')
    root=a.work/'rootfs'; win=a.work/'wine'; pg=a.work/'pg'
    subprocess.run([sys.executable,str(ROOT/'tools/android/test_archive.py'),
        '--extract',str(base),str(root),'--extract',str(wine),str(win),
        '--extract',str(a.assets/'postgresql-runtime.tar.gz'),str(pg)],check=True)
    if digest(win/'lsb-fex.json')!=lock['wine']['manifest_sha256']:raise RuntimeError('Wine source receipt mismatch')
    state=a.work/'state';tmp=a.work/'tmp'
    state.mkdir(mode=0o700);tmp.mkdir(mode=0o700)
    (a.work/'passwd').write_text('root:x:0:0:root:/root:/bin/sh\ncoh:x:1000:1000:COH:/state:/bin/sh\nnobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin\n')
    (a.work/'group').write_text('root:x:0:\ncoh:x:1000:\nnogroup:x:65534:\n')
    for directory in ['opt/coh','opt/coh/pgsql','opt/wine','state','tmp']:(root/directory).mkdir(parents=True,exist_ok=True)
    proot=a.proot.resolve()
    for name in ['proot','proot-loader']:(proot/name).chmod(0o755)
    command=[str(proot/'proot'),'--link2symlink','--kill-on-exit','--sysvipc','-i','1000:1000','-r',str(root.resolve())]
    binds=[('/dev','/dev'),('/proc','/proc'),('/sys','/sys'),(state,'/state'),(tmp,'/tmp'),(a.assets,'/opt/coh'),(pg/'opt/coh/pgsql','/opt/coh/pgsql'),(win,'/opt/wine'),(a.work/'passwd','/etc/passwd'),(a.work/'group','/etc/group')]
    for source,dest in binds:command+=['-b',str(Path(source).resolve())+':'+dest]
    command+=['-w','/state','/usr/bin/env','-i','HOME=/state','USER=coh','LOGNAME=coh','PATH=/opt/coh/pgsql/bin:/usr/local/bin:/usr/bin:/bin','LANG=C.UTF-8','TZ=UTC','TMPDIR=/tmp','PYTHONUNBUFFERED=1',
        '/usr/bin/python3','/opt/coh/diagnostic.py','--state','/state','--assets','/opt/coh','--pg-bin','/opt/coh/pgsql/bin','--wine','/opt/wine/bin/wine','--wineserver','/opt/wine/bin/wineserver','--execution-platform','host']
    env=os.environ.copy();env.update(PROOT_LOADER=str(proot/'proot-loader'),PROOT_TMP_DIR=str(tmp.resolve()),PROOT_NO_SECCOMP='1')
    evidence=ROOT/'out/android/host-evidence';evidence.mkdir(parents=True,exist_ok=True)
    with (evidence/'host-diagnostic.log').open('w') as log:
        process=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            code=process.wait(timeout=1200)
        except subprocess.TimeoutExpired:
            (state/'stop-request').write_text('stop\n')
            try:process.wait(timeout=35)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
            raise RuntimeError('Host runtime exceeded bounded diagnostic time')
        finally:
            report=state/'latest-report.json'
            if report.is_file():shutil.copyfile(report,evidence/'runtime-smoke-report.json')
    report=json.loads((evidence/'runtime-smoke-report.json').read_text())
    if code!=0 or report.get('passed') is not True or report.get('failures')!=[] or not all(report.get('cleanup',{}).get(k) is True for k in ('postgres_graceful','wine_prefix_stopped','owned_processes_reaped')):
        print((evidence/'host-diagnostic.log').read_text()[-24000:]);raise RuntimeError('Native ARM64 PRoot runtime gate failed')
    if report.get('android_execution_validated') is not False:raise RuntimeError('Host smoke cannot claim Android acceptance')
    print(json.dumps({'status':'native_arm64_proot_runtime_passed_android_unvalidated','report':str(evidence/'runtime-smoke-report.json'),'phases':len(report.get('phases',[]))}))

if __name__=='__main__':main()
