"""Four genuine SDK controls; durable failures, never Wine/Android authority."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import queue
import threading
import parse_live_bridge_probe as parser

SOURCE_NAMES=('coh_live_bridge_probe.c','parse_live_bridge_probe.py','qualify_live_bridge_probe_windows.py')
RESULT_RE=re.compile(r'COH_NT_PROBE_RESULT pid=([1-9][0-9]*) mode=([12]) complete=([01]) '
                     r'rows=([0-9]+) batches=([0-9]+) input_cleanup_failed=([01]) bytes=([0-9]+)')


def pin(path):
    data=Path(path).read_bytes()
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}


def source_pins():
    root=Path(__file__).resolve().parent
    return {name:pin(root/name) for name in SOURCE_NAMES}


def require_windows():
    parser.require(os.name=='nt','Real Windows SDK controls require Windows')


def observe_packet(record,output):
    """Keep raw partial packet custody even when native execution failed."""
    record.update(packet=None,parsed=None,packet_parse_error=None)
    try:
        if Path(output).is_file():
            record['packet']=pin(output)
            record['parsed']=parser.parse(Path(output).read_bytes())
    except Exception as error:
        record['packet_parse_error']=repr(error)


def partial_text(value):
    return value.decode('utf-8',errors='replace') if isinstance(value,bytes) else value or ''


def close_owned(process,record):
    """Stop/reap only this exact child; retain stream and failure attribution."""
    cleanup={'held_pid':process.pid,'forced_termination':False,'reaped':False,
             'streams_closed':False,'errors':[],'returncode':None}
    record['process_cleanup']=cleanup
    try:
        if process.poll() is None:
            cleanup['forced_termination']=True
            process.kill()
        process.wait(timeout=10)
        cleanup['reaped']=True
        cleanup['returncode']=process.returncode
    except Exception as error:
        cleanup['errors'].append(repr(error))
    for stream in (process.stdin,process.stdout,process.stderr):
        if stream is not None:
            try:
                stream.close()
            except Exception as error:
                cleanup['errors'].append(repr(error))
    cleanup['streams_closed']=all(stream is None or stream.closed for stream in
                                  (process.stdin,process.stdout,process.stderr))
    cleanup['closed_exact_owned_child']=cleanup['reaped'] and cleanup['streams_closed'] and not cleanup['errors']


def execute(binary,args,output,timeout=30):
    begin=time.monotonic()
    invocation=[str(binary),*map(str,args)]
    record={'invocation':invocation,'held_native_pid':None,'returncode':None,
            'stdout':'','stderr':'','execution_error':None,'process_cleanup':None}
    process=None
    try:
        process=subprocess.Popen(invocation,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        record['held_native_pid']=process.pid
        try:
            stdout,stderr=process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as error:
            record['execution_error']=repr(error)
            record.update(stdout=partial_text(error.output),stderr=partial_text(error.stderr))
            process.kill()
            record['termination_requested_after_timeout']=True
            # Communicate returns all retained bytes without duplicating the prefix.
            stdout,stderr=process.communicate(timeout=10)
        record.update(stdout=stdout,stderr=stderr,returncode=process.returncode)
    except Exception as error:
        record['execution_error']=repr(error)
        if isinstance(error,subprocess.TimeoutExpired):
            record.update(stdout=partial_text(error.output),stderr=partial_text(error.stderr))
    finally:
        if process is not None:
            close_owned(process,record)
            record['returncode']=process.returncode
        record['seconds']=time.monotonic()-begin
        observe_packet(record,output)
    return record


def genuine_result(value,expected_mode,require_complete):
    """Bind exact console fields to held SDK PID, raw packet and cleanup."""
    parsed=value.get('parsed')
    cleanup=value.get('process_cleanup') or {}
    parser.require(value.get('execution_error') is None and parsed and
                   cleanup.get('closed_exact_owned_child') is True and
                   not cleanup.get('forced_termination') and
                   not value.get('termination_requested_after_timeout') and
                   not value.get('termination_requested_after_failure') and
                   cleanup.get('held_pid')==value.get('held_native_pid')==parsed['native_pid'] and
                   cleanup.get('returncode')==value.get('returncode'),
                   'Current held native PID/execution/cleanup witness differs')
    matches=[RESULT_RE.fullmatch(line) for line in value.get('stdout','').splitlines()
             if line.startswith('COH_NT_PROBE_RESULT')]
    parser.require(len(matches)==1 and matches[0] is not None,'Exact single native completion console missing')
    fields=tuple(map(int,matches[0].groups()))
    expected=(parsed['native_pid'],expected_mode,int(parsed['packet_complete']),
              len(parsed['rows']),len(parsed['batches']),int(parsed['native_cleanup_failed']),value['packet']['bytes'])
    parser.require(fields==expected and parsed['mode']==expected_mode,
                   'Current native mode/cardinality/cleanup/byte console differs')
    if expected_mode==2:
        ready=[line for line in value.get('stdout','').splitlines() if line.startswith('COH_NT_SHARE_READY')]
        parser.require(ready==['COH_NT_SHARE_READY pid='+str(parsed['native_pid'])+' inode='+str(parsed['native_inode'])],
                       'Current native sharing readiness inode/PID differs')
    if require_complete:
        parser.require(value['returncode']==0 and parsed['packet_complete'] and not parsed['native_cleanup_failed'],
                       'Current native SDK execution did not complete')
    else:
        parser.require(value['returncode']!=0 and not parsed['packet_complete'],
                       'Current failed native SDK control unexpectedly completed')


def genuine_success(value):
    genuine_result(value,value['parsed']['mode'] if value.get('parsed') else 0,True)


def qualify(binary,output,commit):
    require_windows()
    parser.require(re.fullmatch('[0-9a-f]{40}',commit),'Exact current source commit required')
    binary=Path(binary).resolve()
    # Workflow supplies out/windows-probe; native DOS arguments must be absolute.
    output=Path(output).resolve()
    parser.require(binary.is_file() and not binary.is_symlink() and not output.exists(),
                   'Fresh actual native evidence required')
    output.mkdir(parents=True)
    cases={}
    report={'format':1,'role':'fresh_native_Win32_NT_bridge_observer_controls','status':'running',
            'repository_commit':commit,'probe_source':source_pins(),'binary':pin(binary),'cases':cases,
            'fresh_native_control_groups':0,'Wine_executed':False,'Android_runtime_executed':False,
            'Game_executed':False,'provider_authority':False,'publication_allowed':False,
            'output_directory':str(output),'input_output_custody_scope':'fresh ordinary separate SDK directories; normalized DOS spelling refusal only'}
    receipt=output/'windows-controls.json'
    def checkpoint():
        temporary=receipt.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
        temporary.replace(receipt)
    checkpoint()
    try:
        with tempfile.TemporaryDirectory(prefix='coh-nt-bridge-SDK-') as temporary:
            source=Path(temporary).resolve()/'input'
            source.mkdir()
            names=[]
            for number in range(200):
                name=f'fixture_{number:03d}_'+('x'*70)+'.fx'
                (source/name).write_bytes(bytes([number%256])*17)
                names.append(name)
            stock=output/'stock.bin'
            first=execute(binary,('stock',source,stock),stock)
            cases['actual_stock_multibuffer']=first;checkpoint()
            genuine_result(first,1,True)
            observed=[r['name'] for r in first['parsed']['rows'] if r['name'] not in ('.','..')]
            parser.require(sorted(observed)==sorted(names) and len(first['parsed']['batches'])>1,
                           'Actual multibuffer fixture cardinality missing')
            report['fresh_native_control_groups']=1
            before=pin(stock)
            refused=execute(binary,('stock',source,stock),stock)
            cases['existing_output_preserved']=refused;checkpoint()
            parser.require(refused['execution_error'] is None and refused['returncode']==65 and
                           refused['process_cleanup']['closed_exact_owned_child'] and pin(stock)==before,
                           'Existing native packet changed or child cleanup failed')
            report['fresh_native_control_groups']=2
            blocker_output=output/'share-block.bin'
            blocker={'invocation':[str(binary),'share-block',str(source),str(blocker_output)],
                     'held_native_pid':None,'returncode':None,'stdout':'','stderr':'',
                     'execution_error':None,'process_cleanup':None}
            share={'held':blocker}
            cases['native_share_refusal_and_owned_release']=share;checkpoint()
            held=None;observer=None;begin=time.monotonic()
            try:
                held=subprocess.Popen(blocker['invocation'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,text=True)
                blocker['held_native_pid']=held.pid
                lines=queue.Queue(maxsize=1)
                def read_ready():
                    try:
                        lines.put(held.stdout.readline())
                    except Exception as error:
                        lines.put(error)
                observer=threading.Thread(target=read_ready,daemon=True)
                observer.start()
                ready=lines.get(timeout=30)
                if isinstance(ready,Exception):
                    raise ready
                blocker['stdout']=ready;checkpoint()
                parser.require(re.fullmatch(r'COH_NT_SHARE_READY pid='+str(held.pid)+r' inode=[1-9][0-9]*\n',ready),
                               'Current held native sharing PID/handle not ready')
                observer.join(timeout=5)
                parser.require(not observer.is_alive(),'Owned readiness reader did not complete')
                refused_output=output/'sharing-refusal.bin'
                refused=execute(binary,('stock',source,refused_output),refused_output)
                share['blocked']=refused;checkpoint()
                genuine_result(refused,1,False)
                parser.require(refused['parsed']['native_open_status']==0xc0000043,'Actual sharing refusal did not occur')
                stdout,stderr=held.communicate('C',timeout=30)
                blocker.update(stdout=ready+stdout,stderr=stderr,returncode=held.returncode)
            except Exception as error:
                blocker['execution_error']=repr(error)
                if held is not None:
                    if held.poll() is None:
                        held.kill();blocker['termination_requested_after_failure']=True
                    if observer is not None:
                        observer.join(timeout=5)
                    if observer is None or not observer.is_alive():
                        stdout,stderr=held.communicate(timeout=10)
                        blocker.update(stdout=blocker['stdout']+stdout,stderr=stderr,returncode=held.returncode)
                raise
            finally:
                if held is not None:
                    close_owned(held,blocker)
                    blocker['returncode']=held.returncode
                if observer is not None:
                    observer.join(timeout=5)
                    blocker['readiness_observer_stopped']=not observer.is_alive()
                    if observer.is_alive():
                        blocker['execution_error']='Owned readiness observer did not terminate'
                blocker['seconds']=time.monotonic()-begin
                observe_packet(blocker,blocker_output)
                checkpoint()
            genuine_result(blocker,2,True)
            parser.require(blocker['readiness_observer_stopped'],'Readiness observer cleanup failed')
            report['fresh_native_control_groups']=3
            invalid=source/'invalid-output.bin'
            refused=execute(binary,('stock',source,invalid),invalid)
            cases['input_namespace_output_refused']=refused;checkpoint()
            parser.require(refused['execution_error'] is None and refused['returncode']==64 and
                           refused['process_cleanup']['closed_exact_owned_child'] and not invalid.exists(),
                           'Input namespace output was not refused or cleanup failed')
            report.update(status='passed',fresh_native_control_groups=4)
    except Exception as error:
        report.update(status='failed',failure=repr(error))
        raise
    finally:
        checkpoint()
    return report


if __name__=='__main__':
    args=argparse.ArgumentParser(description=__doc__)
    args.add_argument('--binary',type=Path,required=True)
    args.add_argument('--output',type=Path,required=True)
    args.add_argument('--commit',required=True)
    parsed=args.parse_args()
    print(json.dumps(qualify(parsed.binary,parsed.output,parsed.commit),sort_keys=True))
