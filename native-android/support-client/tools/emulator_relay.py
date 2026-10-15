#!/usr/bin/env python3
"""Keep emulator and adb in one execution namespace; relay argv via files.

serve owns a disposable emulator and its adb subprocesses. call writes an atomic
bounded JSON request and reads its response. No shell command evaluation, sockets
between tool calls, credentials or production-device discovery is involved.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

MAX_OUTPUT=16<<20

def write_json(path,value):
    temp=path.with_name(path.name+'.tmp-'+uuid.uuid4().hex)
    temp.write_text(json.dumps(value,indent=2)+'\n');os.replace(temp,path)

def request(root,args,timeout=60):
    root=Path(root);identifier=uuid.uuid4().hex
    req=root/'requests'/(identifier+'.json');response=root/'responses'/(identifier+'.json')
    if not (root/'status.json').is_file():raise RuntimeError('Emulator relay has not started')
    req.parent.mkdir(parents=True,exist_ok=True)
    write_json(req,{'schema':1,'id':identifier,'args':args,'timeout':timeout})
    deadline=time.monotonic()+timeout+30
    while time.monotonic()<deadline:
        if response.is_file():
            value=json.loads(response.read_text());response.unlink()
            if value.get('relay_error'):raise RuntimeError(value['relay_error'])
            return subprocess.CompletedProcess(args,value['returncode'],base64.b64decode(value['stdout_b64']),base64.b64decode(value['stderr_b64']))
        status=json.loads((root/'status.json').read_text())
        if status.get('state') in ('failed','stopped'):raise RuntimeError('Emulator relay stopped: '+str(status))
        time.sleep(.08)
    raise TimeoutError('Filesystem adb relay response timed out')

def serve(a):
    root=a.root.resolve();root.mkdir(parents=True,exist_ok=True)
    for name in ('requests','responses'):(root/name).mkdir(exist_ok=True)
    adb=a.sdk/'platform-tools/adb';emulator=a.sdk/'emulator/emulator';serial='emulator-'+str(a.port)
    env=dict(os.environ);env['ANDROID_HOME']=str(a.sdk);env['ANDROID_SDK_ROOT']=str(a.sdk)
    if a.avd_home:env['ANDROID_AVD_HOME']=str(a.avd_home.resolve())
    state={'schema':1,'state':'starting','serial':serial,'port':a.port,'pid':os.getpid(),'avd':a.avd,'started_unix':time.time()}
    write_json(root/'status.json',state)
    log=(root/'emulator.log').open('ab');process=None
    try:
        command=[str(emulator),'-avd',a.avd,'-port',str(a.port),'-no-window','-no-audio',
                 '-no-boot-anim','-no-snapshot','-gpu','swiftshader_indirect',*a.emulator_arg]
        process=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT)
        subprocess.run([str(adb),'start-server'],env=env,capture_output=True,timeout=30)
        deadline=time.monotonic()+a.boot_timeout
        while time.monotonic()<deadline:
            if process.poll() is not None:raise RuntimeError('Emulator exited during startup: '+str(process.returncode))
            result=subprocess.run([str(adb),'-s',serial,'shell','getprop','sys.boot_completed'],env=env,capture_output=True,timeout=10)
            if result.returncode==0 and result.stdout.strip()==b'1':break
            time.sleep(1)
        else:raise TimeoutError('Emulator boot deadline exceeded')
        qemu=subprocess.run([str(adb),'-s',serial,'shell','getprop','ro.boot.qemu'],env=env,capture_output=True,timeout=10)
        if qemu.returncode or qemu.stdout.strip()!=b'1':raise RuntimeError('Target is not the owned emulator')
        state['state']='ready';write_json(root/'status.json',state);print(json.dumps(state),flush=True)
        deadline=time.monotonic()+a.lifetime
        while time.monotonic()<deadline:
            if process.poll() is not None:raise RuntimeError('Owned emulator exited unexpectedly')
            if (root/'stop').exists():break
            for pending in sorted((root/'requests').glob('*.json')):
                identifier=pending.stem;response=root/'responses'/(identifier+'.json')
                try:
                    if pending.stat().st_size>65536:raise ValueError('Oversized relay request')
                    value=json.loads(pending.read_text())
                    args=value['args'];timeout=value.get('timeout',60)
                    if value.get('schema')!=1 or value.get('id')!=identifier:raise ValueError('Invalid relay request identity')
                    if not isinstance(args,list) or len(args)>128 or not all(isinstance(x,str) and '\0' not in x and len(x)<=8192 for x in args):raise ValueError('Invalid relay argv')
                    if not isinstance(timeout,(int,float)) or not 0<timeout<=120:raise ValueError('Invalid relay timeout')
                    # Device/server options are parsed before the adb verb.
                    # Child argv such as logcat -d or shell am ... -e is legal.
                    allowed={'shell','exec-out','install','uninstall','push','pull','logcat','get-state','wait-for-device','version'}
                    if not args or args[0] not in allowed:raise ValueError('Relay device/server redirection or unsupported adb verb')
                    result=subprocess.run([str(adb),'-s',serial,*args],env=env,capture_output=True,timeout=timeout)
                    if len(result.stdout)+len(result.stderr)>MAX_OUTPUT:raise ValueError('Relay output exceeds bound')
                    write_json(response,{'schema':1,'id':identifier,'returncode':result.returncode,
                                         'stdout_b64':base64.b64encode(result.stdout).decode(),
                                         'stderr_b64':base64.b64encode(result.stderr).decode()})
                except Exception as error:write_json(response,{'schema':1,'id':identifier,'relay_error':str(error)})
                finally:pending.unlink(missing_ok=True)
            time.sleep(.05)
        state['state']='stopped'
    except Exception as error:
        state.update(state='failed',error=str(error));raise
    finally:
        write_json(root/'status.json',state)
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        log.close()

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='operation',required=True)
    server=sub.add_parser('serve');server.add_argument('--root',type=Path,required=True);server.add_argument('--sdk',type=Path,required=True)
    server.add_argument('--avd',required=True);server.add_argument('--avd-home',type=Path);server.add_argument('--port',type=int,default=5556)
    server.add_argument('--boot-timeout',type=int,default=300);server.add_argument('--lifetime',type=int,default=3600)
    server.add_argument('--emulator-arg',action='append',default=[])
    client=sub.add_parser('call');client.add_argument('--root',type=Path,required=True);client.add_argument('--timeout',type=int,default=60);client.add_argument('args',nargs=argparse.REMAINDER)
    a=p.parse_args()
    if a.operation=='serve':
        if a.port%2 or not 5554<=a.port<=5682:raise ValueError('Emulator port must be even within5554..5682')
        serve(a)
    else:
        args=a.args[1:] if a.args[:1]==['--'] else a.args
        result=request(a.root,args,a.timeout);sys.stdout.buffer.write(result.stdout);sys.stderr.buffer.write(result.stderr);sys.exit(result.returncode)

if __name__=='__main__':main()
