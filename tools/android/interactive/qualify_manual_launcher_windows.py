"""Exercise the actual newly built .35 launcher through genuine Windows APIs.

An owned tiny child substitutes only for the proprietary game. Production helper
bytes execute unchanged. A separate exact-source deadline fixture uses synthetic
elapsed time, without pretending to run a 48-hour game or AYN Thor session.
"""
from __future__ import annotations
import argparse
import ctypes
import json
import os
from pathlib import Path
import queue
import secrets
import subprocess
import tempfile
import threading
import time

import manual_launcher_contract as contract

CHILD = r'''
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
int main(void) {
    char path[2048]; DWORD ids[32], count, index; int owned=0;
    HANDLE screen; DWORD written;
    if(!GetEnvironmentVariableA("COH_NATIVE_FIXTURE_CONTROL_PATH",path,sizeof(path)))return 90;
    count=GetConsoleProcessList(ids,32);
    if(count&&count<=32)for(index=0;index<count;index++)if(ids[index]==GetCurrentProcessId())owned=1;
    printf("COH_NATIVE_FIXTURE_CHILD_V1 {\"pid\":%lu,\"owned_console\":%s}\n",
        (unsigned long)GetCurrentProcessId(),owned?"true":"false"); fflush(stdout);
    screen=CreateFileA("CONOUT$",GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE,NULL,OPEN_EXISTING,0,NULL);
    if(screen!=INVALID_HANDLE_VALUE) {
        const char text[]="COH_NATIVE_FIXTURE_CONSOLE_MARKER\n";
        WriteFile(screen,text,(DWORD)(sizeof(text)-1),&written,NULL);CloseHandle(screen);
    }
    for(index=0;index<600;index++) {
        if(GetFileAttributesA(path)!=INVALID_FILE_ATTRIBUTES)return 0;
        Sleep(25);
    }
    return 91;
}
'''
SESSION = '0123456789abcdef0123456789abcdef'


def source_block(raw, name):
    start=raw.index('static ', raw.index(name)-80)
    # Each requested exact function is selected by its signature.
    for signature in ('static const char *'+name+'(', 'static int '+name+'('):
        if signature in raw: start=raw.index(signature);break
    opening=raw.index('{',start);depth=0
    for end in range(opening,len(raw)):
        if raw[end]=='{':depth+=1
        elif raw[end]=='}':
            depth-=1
            if depth==0:return raw[start:end+1]
    raise ValueError('Incomplete native source function '+name)


def compile_fixture(source, output, work):
    path=work/(output.stem+'.c');path.write_text(source)
    run=subprocess.run(['cl','/nologo','/W4','/WX','/O2','/MT','/D_CRT_SECURE_NO_WARNINGS',
        str(path),'/Fe:'+str(output)],cwd=work,check=False,timeout=120,capture_output=True,text=True)
    contract.require(run.returncode==0,'Native MSVC fixture build failed:\n'+(run.stdout+run.stderr)[-16000:])


def deadline_fixture(work):
    raw=(contract.ROOT/contract.SOURCE).read_text()
    functions='\n'.join(source_block(raw,name)for name in ('launch_policy','graphics_policy','lifetime_expired'))
    body=r'''
static void need(int value){if(!value)exit(92);}
int main(void){int generate;unsigned long lifetime;const char *policy;
 policy=launch_policy(5,"--character-manual",&generate,&lifetime);
 need(policy&&!strcmp(policy," -noversioncheck 1")&&!generate&&lifetime==0);
 need(!lifetime_expired(lifetime,48ULL*60*60*1000,1));
 need(!lifetime_expired(lifetime,~0ULL,0));
 need(!strcmp(graphics_policy(5,"--character-manual","performance"),"performance"));
 policy=launch_policy(5,"--character-creation",&generate,&lifetime);
 need(policy&&!generate&&lifetime==36UL*60*1000);
 need(!lifetime_expired(lifetime,100,101)&&lifetime_expired(lifetime,101,101));
 policy=launch_policy(5,"--local-login",&generate,&lifetime);
 need(policy&&!generate&&lifetime==20UL*60*1000);
 policy=launch_policy(5,"--generate-caches",&generate,&lifetime);
 need(policy&&generate&&lifetime==20UL*60*1000);
 need(!launch_policy(5,"--character-manual-extra",&generate,&lifetime));
 puts("EXACT_SOURCE_DEADLINE_POLICY_PASS");return 0;}
'''
    source='#include <stdio.h>\n#include <string.h>\n#include <stdlib.h>\n'+functions+'\n'+body
    binary=work/'native-deadline-fixture.exe';compile_fixture(source,binary,work)
    run=subprocess.run([str(binary)],capture_output=True,text=True,check=True,timeout=20)
    contract.require(run.stdout.strip()=='EXACT_SOURCE_DEADLINE_POLICY_PASS','Native exact-source deadline fixture failed')


class OwnedRun:
    def __init__(self, helper, child, work, mode, *, session=SESSION):
        self.child=child.resolve();self.control=work/(mode.strip('-')+'-'+secrets.token_hex(8)+'-exit')
        self.lines=[];self.events=queue.Queue();self.pending=[];self.requested=set()
        self.child_pid=None;self.child_handle=None;self.kernel=None;self.bytes=0
        environment=dict(os.environ,COH_NATIVE_FIXTURE_CONTROL_PATH=str(self.control),
            COH_CLIENT_GRAPHICS_PROFILE='performance' if mode=='--character-manual' else 'standard')
        self.process=subprocess.Popen([str(helper),session,str(self.child),str(work),mode],
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=environment,
            creationflags=subprocess.CREATE_NEW_CONSOLE)
        def reader():
            for line in iter(self.process.stdout.readline,b''):
                self.bytes+=len(line)
                if self.bytes>256*1024:self.events.put(RuntimeError('Unbounded native fixture output'));return
                text=line.decode('utf-8','replace').rstrip('\r\n');self.lines.append(text);self.events.put(text)
            self.events.put(None)
        self.thread=threading.Thread(target=reader,daemon=True);self.thread.start()

    def event(self,prefix,timeout=12):
        contract.require(prefix not in self.requested, 'Each native event must be consumed once')
        self.requested.add(prefix)
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            matches=[index for index,item in enumerate(self.pending) if item.startswith(prefix)]
            contract.require(len(matches)<=1, 'Duplicate native event '+prefix)
            if matches:return json.loads(self.pending.pop(matches[0])[len(prefix):])
            try:item=self.events.get(timeout=min(.25,max(.01,deadline-time.monotonic())))
            except queue.Empty:continue
            if isinstance(item,Exception):raise item
            if item is None:raise ValueError('Native helper exited before '+prefix+'; '+repr(self.lines))
            self.pending.append(item)
        raise ValueError('Native helper event timed out: '+prefix+'; '+repr(self.lines))

    def hold_child(self):
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=(ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong)
        kernel.OpenProcess.restype=ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes=(ctypes.c_void_p,ctypes.c_ulong)
        kernel.QueryFullProcessImageNameW.argtypes=(ctypes.c_void_p,ctypes.c_ulong,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong))
        kernel.TerminateProcess.argtypes=(ctypes.c_void_p,ctypes.c_ulong)
        kernel.CloseHandle.argtypes=(ctypes.c_void_p,)
        handle=kernel.OpenProcess(0x100000|0x1000|1,False,self.child_pid)
        contract.require(handle is not None, 'Cannot retain the actual owned child process handle')
        try:
            path=ctypes.create_unicode_buffer(4096);length=ctypes.c_ulong(4096)
            contract.require(kernel.QueryFullProcessImageNameW(handle,0,path,ctypes.byref(length))
                and Path(path.value).resolve()==self.child and kernel.WaitForSingleObject(handle,0)==258,
                'Native fixture launch did not identify its live owned child image')
        except BaseException:
            kernel.CloseHandle(handle);raise
        self.child_handle,self.kernel=handle,kernel

    def owned(self):
        launch=self.event('COH_CLIENT_LAUNCH_V1 ')
        contract.require(launch.get('session_id')==SESSION and type(launch.get('pid'))is int and launch['pid']>0,
            'Native child launch identity differs')
        self.child_pid=launch['pid']
        self.hold_child()
        profile=self.event('COH_CLIENT_GRAPHICS_PROFILE_V1 ')
        contract.require(profile.get('session_id')==SESSION and profile.get('pid')==self.child_pid,
            'Native graphics event ownership differs')
        child=self.event('COH_NATIVE_FIXTURE_CHILD_V1 ')
        contract.require(child=={'pid':self.child_pid,'owned_console':True},'Actual native child console ownership failed')
        console=self.event('COH_CLIENT_CONSOLE_V1 ')
        contract.require(console=={'session_id':SESSION,'pid':self.child_pid,'attached':True},
            'Actual launcher native console membership failed')
        contract.require(self.process.poll() is None,'Manual helper ended while its owned child remained active')
        deadline=time.monotonic()+5
        while not any(line=='COH_NATIVE_FIXTURE_CONSOLE_MARKER' for line in self.lines) and time.monotonic()<deadline:
            time.sleep(.02)
        contract.require(any(line=='COH_NATIVE_FIXTURE_CONSOLE_MARKER' for line in self.lines),
            'Actual owned console bytes were not forwarded by the shipping helper')
        return profile['profile']

    def stop(self):
        self.control.write_text('owned native fixture child exit\n')
        exit_event=self.event('COH_CLIENT_EXIT_V1 ')
        contract.require(exit_event=={'session_id':SESSION,'exit_code':0},'Owned native child exit differs')
        contract.require(self.process.wait(timeout=12)==0,'Native helper return differs')
        self.thread.join(timeout=2)
        contract.require(not self.thread.is_alive(),'Native helper pipe output remained incomplete after exit')
        for prefix in self.requested:
            contract.require(sum(line.startswith(prefix) for line in self.lines)==1, 'Duplicate native metadata event '+prefix)
        contract.require(not any('LAUNCHER_TIMEOUT' in line for line in self.lines),'Unexpected gameplay helper expiry')

    def close(self):
        # Only the child PID emitted by this invocation may be cleaned. The
        # process image is rechecked through an actual owned Windows handle.
        self.control.write_text('owned cleanup\n')
        if self.process.poll() is None:self.process.terminate()
        try:self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=5)
        if self.child_handle:
            try:
                waited=self.kernel.WaitForSingleObject(self.child_handle,3000)
                contract.require(waited in (0,258),'Owned child wait failed; cleanup cannot be qualified')
                if waited==258:
                    # Retain the handle captured and image-verified immediately
                    # after the launch event. No later PID lookup authorizes a
                    # signal after the original process could have exited.
                    contract.require(self.kernel.TerminateProcess(self.child_handle,93), 'Owned fixture child stop failed')
                    contract.require(self.kernel.WaitForSingleObject(self.child_handle,3000)==0, 'Owned fixture child survived cleanup')
            finally:
                self.kernel.CloseHandle(self.child_handle);self.child_handle=None


def qualify(args):
    contract.require(os.name=='nt','Genuine Windows native helper qualification required; no skip or simulation')
    build=json.loads((args.directory/contract.MANIFEST_NAME).read_bytes())
    helper=(args.directory/contract.EXE_NAME).resolve()
    contract.validate_build(build,helper,args.repository_commit)
    contract.require(str(build['run_id'])==os.environ.get('GITHUB_RUN_ID'),'Current native fixture owner required')
    cases=[]
    with tempfile.TemporaryDirectory(prefix='coh-manual-native-')as temporary:
        work=Path(temporary);child=work/'owned-child.exe';compile_fixture(CHILD,child,work)
        for mode,session,expected,name in (
            ('--unknown-mode',SESSION,64,'invalid_mode_refused'),
            ('--character-manual','g'*32,64,'invalid_session_refused')):
            run=subprocess.run([str(helper),session,str(child),str(work),mode],stdin=subprocess.DEVNULL,
                capture_output=True,timeout=15,creationflags=subprocess.CREATE_NEW_CONSOLE)
            contract.require(run.returncode==expected and b'COH_CLIENT_LAUNCH_V1'not in run.stdout,'Invalid mode/session launched a child')
            cases.append(name)
        run=subprocess.run([str(helper),SESSION,str(work/'missing.exe'),str(work),'--character-manual'],
            stdin=subprocess.DEVNULL,capture_output=True,timeout=15,creationflags=subprocess.CREATE_NEW_CONSOLE)
        contract.require(run.returncode==66 and b'COH_CLIENT_LAUNCH_ERROR_V1'in run.stdout,'Native startup failure not reported')
        cases.append('missing_game_refused')
        for mode,name in (
            ('--character-manual','manual_owned_console_child_exit'),
            ('--character-creation','creation_mode_retained'),
            ('--local-login','local_login_mode_retained'),
            ('--generate-caches','cache_generation_mode_retained')):
            instance=OwnedRun(helper,child,work,mode)
            try:
                profile=instance.owned();contract.require(profile==('performance'if mode=='--character-manual'else'standard'),'Graphics policy changed')
                instance.stop()
            finally:instance.close()
            cases.append(name)
        instance=OwnedRun(helper,child,work,'--character-manual')
        try:
            instance.owned();instance.process.terminate();instance.process.wait(timeout=5)
        finally:instance.close()
        cases.append('manual_owned_interruption_cleanup')
        deadline_fixture(work);cases.append('exact_source_deadline_policy_native_fixture')
    proof={'format':1,'status':'passed','role':contract.ROLE,'repository_commit':args.repository_commit,
        'run_id':build['run_id'],'run_url':build['run_url'],'build_receipt':contract.pin(contract.encoded(build)),
        'executable':build['executable'],'source_files':contract.source_pins(),
        'executed_cases':sorted(cases),'skipped':0,'windows_platform':'genuine_windows_x86_process_and_console_api',
        'actual_shipping_helper_executed':True,'actual_owned_child_console_verified':True,
        'deadline_policy_fixture':{'actual_source_function_compiled':True,'simulated_elapsed_hours':48,
            'real_duration_48_hour_run':False,'shipping_helper_binary_modified':False},
        'game_db_map_executed':False,'physical_ayn_thor_validated':False}
    contract.validate_qualification(proof,build,helper,args.repository_commit)
    target=args.directory/contract.QUALIFICATION_NAME
    contract.require(not target.exists(),'Fresh native qualification receipt required')
    target.write_bytes(contract.encoded(proof));print('Qualified actual native manual helper; nine cases; zero skips')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--repository-commit',required=True);qualify(parser.parse_args())
