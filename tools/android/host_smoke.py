#!/usr/bin/env python3
"""Qualify cold and warm runs of the APK guest through PRoot on native ARM64 Linux."""
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

def validate_report(report, *, client_probe, repeat, runtime_lock_sha256):
    if report.get('passed') is not True or report.get('failures')!=[] or not all(report.get('cleanup',{}).get(k) is True for k in ('postgres_graceful','wine_prefix_stopped','owned_processes_reaped')):
        raise RuntimeError('Native ARM64 PRoot runtime gate failed')
    if report.get('android_execution_validated') is not False:
        raise RuntimeError('Host smoke cannot claim Android acceptance')
    if report.get('diagnostic_mode') != ('database_and_client' if client_probe else 'database'):
        raise RuntimeError('Host report did not exercise the requested diagnostic mode')
    initialized=[stage for stage in report.get('stages',[]) if stage.get('stage')=='initialize_owned_cluster']
    if len(initialized)!=1 or initialized[0].get('status')!='passed' or initialized[0].get('cluster_reused') is not repeat:
        raise RuntimeError('Host report did not prove the requested fresh/reused database state')
    wine=report.get('wine_initialization',{})
    if (wine.get('policy')!='initialize_once_then_reuse' or wine.get('state')!='ready'
            or wine.get('ready_prefix_reused') is not repeat
            or wine.get('runtime_lock_sha256')!=runtime_lock_sha256):
        raise RuntimeError('Host report did not prove the requested cold/warm Wine initialization')
    expected_registration=(0,0,0) if repeat else (3,1,1)
    for name,expected in zip(('registration_processes','wow64_registration_processes','registration_passes'),expected_registration):
        if type(wine.get(name)) is not int or wine[name]!=expected:
            raise RuntimeError('Wine registration count differs from the requested cold/warm initialization: '+name)
    if repeat:
        if wine.get('update_timestamp_removed') is not False:
            raise RuntimeError('Warm prefix initialization timestamp was unexpectedly reset')
    if client_probe:
        client=report.get('client_probe',{})
        if client.get('status') != 'passed' or client.get('scope') != 'headless_wgl_client_capabilities':
            raise RuntimeError('Client runtime probe was not passed')
        if any(client.get(key) is not False for key in ('game_rendering_validated','android_surface_validated','hardware_acceleration_validated')):
            raise RuntimeError('Client fixture cannot claim Android rendering or hardware acceleration')

def run_guest(command, env, state, evidence, *, repeat, client_probe, runtime_lock_sha256):
    report_path=evidence/('runtime-repeat-report.json' if repeat else 'runtime-smoke-report.json')
    log_path=evidence/('host-repeat.log' if repeat else 'host-diagnostic.log')
    # A previous pass may never stand in for a run that produces no fresh receipt.
    source_report=state/'latest-report.json'
    source_report.unlink(missing_ok=True)
    report_path.unlink(missing_ok=True)
    with log_path.open('w') as log:
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
            if source_report.is_file():shutil.copyfile(source_report,report_path)
    try:
        if code!=0:
            raise RuntimeError('Native ARM64 PRoot runtime returned a failure exit status')
        if not report_path.is_file():
            raise RuntimeError('Native ARM64 PRoot runtime did not write a fresh report')
        report=json.loads(report_path.read_text())
        validate_report(report,client_probe=client_probe,repeat=repeat,runtime_lock_sha256=runtime_lock_sha256)
    except (RuntimeError,ValueError):
        print(log_path.read_text()[-24000:])
        raise
    return report

def run_owned_wine_fixture(command, env, state, evidence):
    guest_index=command.index('/usr/bin/python3')
    fixture_command=command[:guest_index]+[
        '/usr/bin/python3','/opt/coh-host-tools/owned_wine_smoke.py',
        '--diagnostic','/opt/coh/diagnostic.py','--state','/state/owned-wine-smoke']
    bind_index=fixture_command.index('-w')
    fixture_command[bind_index:bind_index]=['-b',str(ROOT/'tools/android')+':/opt/coh-host-tools']
    source_report=state/'owned-wine-smoke/report.json'
    report_path=evidence/'owned-wine-cleanup-report.json'
    log_path=evidence/'host-owned-wine.log'
    report_path.unlink(missing_ok=True)
    with log_path.open('w') as log:
        process=subprocess.Popen(fixture_command,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            code=process.wait(timeout=60)
        except subprocess.TimeoutExpired:
            # The pinned PRoot SIGQUIT handler kills its tracked tracees and
            # drains their wait events, including detached session leaders.
            process.send_signal(signal.SIGQUIT)
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
            raise RuntimeError('Owned Wine cleanup fixture exceeded its time limit')
        finally:
            if source_report.is_file():shutil.copyfile(source_report,report_path)
    if code!=0 or not report_path.is_file():
        print(log_path.read_text()[-24000:])
        raise RuntimeError('Owned Wine cleanup fixture did not complete successfully')
    report=json.loads(report_path.read_text())
    required=('passed','detached_helper_retained_output','detached_helper_reaped',
              'output_eof_observed','unrelated_sentinel_survived','same_prefix_different_token_preserved')
    if (report.get('scope')!='synthetic_owned_process_cleanup_under_proot'
            or not all(report.get(name) is True for name in required)
            or report.get('android_execution_validated') is not False
            or report.get('wine_process_cleanup',{}).get('complete') is not True):
        raise RuntimeError('Owned Wine cleanup fixture did not prove detached cleanup and sentinel preservation')
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--assets',type=Path,default=ROOT/'out/android/assets/runtime')
    p.add_argument('--proot',type=Path,default=ROOT/'out/android/native/linux-arm64')
    p.add_argument('--work',type=Path,default=ROOT/'out/android/host-smoke')
    p.add_argument('--client-probe',action='store_true',help='Also require the PE32 WGL/input fixture')
    p.add_argument('--evidence',type=Path,default=ROOT/'out/android/host-evidence')
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
    for directory in ['opt/coh','opt/coh/pgsql','opt/coh-host-tools','opt/wine','state','tmp']:(root/directory).mkdir(parents=True,exist_ok=True)
    proot=a.proot.resolve()
    for name in ['proot','proot-loader']:(proot/name).chmod(0o755)
    command=[str(proot/'proot'),'--link2symlink','--kill-on-exit','--sysvipc','-i','1000:1000','-r',str(root.resolve())]
    binds=[('/dev','/dev'),('/proc','/proc'),('/sys','/sys'),(state,'/state'),(tmp,'/tmp'),(a.assets,'/opt/coh'),(pg/'opt/coh/pgsql','/opt/coh/pgsql'),(win,'/opt/wine'),(a.work/'passwd','/etc/passwd'),(a.work/'group','/etc/group')]
    for source,dest in binds:command+=['-b',str(Path(source).resolve())+':'+dest]
    command+=['-w','/state','/usr/bin/env','-i','HOME=/state','USER=coh','LOGNAME=coh','PATH=/opt/coh/pgsql/bin:/usr/local/bin:/usr/bin:/bin','LANG=C.UTF-8','TZ=UTC','TMPDIR=/tmp','PYTHONUNBUFFERED=1',
        '/usr/bin/python3','/opt/coh/diagnostic.py','--state','/state','--assets','/opt/coh','--pg-bin','/opt/coh/pgsql/bin','--wine','/opt/wine/bin/wine','--wineserver','/opt/wine/bin/wineserver','--execution-platform','host']
    if a.client_probe:command+=['--client-probe']
    env=os.environ.copy();env.update(PROOT_LOADER=str(proot/'proot-loader'),PROOT_TMP_DIR=str(tmp.resolve()),PROOT_NO_SECCOMP='1')
    evidence=a.evidence;evidence.mkdir(parents=True,exist_ok=True)
    for name in ('runtime-smoke-report.json','runtime-repeat-report.json','host-diagnostic.log','host-repeat.log',
                 'owned-wine-cleanup-report.json','host-owned-wine.log'):
        (evidence/name).unlink(missing_ok=True)
    run_owned_wine_fixture(command,env,state,evidence)
    runtime_lock_sha256=digest(a.assets/'runtime-lock.json')
    # Keep the first run's accepted evidence stable and use the exact same
    # command/runtime/workspace again only after its owned shutdown passed.
    reports=[]
    for repeat in (False,True):
        reports.append(run_guest(command,env,state,evidence,repeat=repeat,
                                 client_probe=a.client_probe,runtime_lock_sha256=runtime_lock_sha256))
    print(json.dumps({'status':'native_arm64_proot_runtime_passed_android_unvalidated',
                      'report':str(evidence/'runtime-smoke-report.json'),
                      'repeat_report':str(evidence/'runtime-repeat-report.json'),
                      'stages':len(reports[0].get('stages',[])),
                      'repeat_stages':len(reports[1].get('stages',[])),
                      'client_probe':a.client_probe,'warm_repeat_validated':True,
                      'owned_wine_cleanup_fixture':str(evidence/'owned-wine-cleanup-report.json')}))

if __name__=='__main__':main()
