#!/usr/bin/env python3
"""Qualify bounded TCP assembly using existing native frame/bit kernels, no sockets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from source_audit import decoded,extract
from hosted_auth_stage import ORIGINAL_TREE

HERE=Path(__file__).resolve().parent
BASE='native-android/'
DEPENDENCIES=['engine/network/coh_net.h','engine/network/coh_net_frame.c','engine/coh_contracts.h',
              'protocol/coh_protocol.h','protocol/coh_protocol.c','include/coh_native_core.h','src/coh_blowfish.c','src/byte_reader.h']
ORIGINALS=['network/netio_receive.c','network/netio_send.c','network/netio_core.c','network/net_link.c','network/net_version.c']


def qualify(root,output):
    git=lambda *args:subprocess.check_output(['git','-C',str(root),*args],timeout=30)
    if git('rev-parse','HEAD:upstream/ouroboros').decode().strip()!=ORIGINAL_TREE:raise ValueError('monitor_original_source_tree')
    original={n:git('show','HEAD:upstream/ouroboros/libs/UtilitiesLib/src/'+n) for n in ORIGINALS}
    network_pins=json.loads(git('show','HEAD:native-android/engine/network/source-pins.json'))['files']
    for name,raw in original.items():
        if hashlib.sha256(decoded(raw).encode()).hexdigest()!=network_pins[Path(name).name]['sha256_lf']:raise ValueError('monitor_original_source_pin')
    raw_deps={BASE+n:git('show','HEAD:'+BASE+n) for n in DEPENDENCIES}
    local_names=['coh_monitor_envelope.c','coh_monitor_envelope.h','monitor_envelope_fixture.c'];executions={}
    with tempfile.TemporaryDirectory(prefix='coh-monitor-envelope-') as temp:
        temp=Path(temp)
        for name,data in raw_deps.items():path=temp/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        local=temp/'native-android/engine/auth-interop/deployment';local.mkdir(parents=True)
        for name in local_names:shutil.copy2(HERE/name,local/name)
        fixture=local/'monitor_envelope_fixture.c'
        fixture.write_text(fixture.read_text().replace('/* EXACT_ORIGINAL_BLOWFISH_PAD */',extract(decoded(original['network/netio_core.c']),'blowfishPad')))
        sources=[local/'coh_monitor_envelope.c',local/'monitor_envelope_fixture.c',temp/(BASE+'engine/network/coh_net_frame.c'),temp/(BASE+'protocol/coh_protocol.c'),temp/(BASE+'src/coh_blowfish.c')]
        for mode in ('release','asan_ubsan'):
            flags=['-O2'] if mode=='release' else ['-O1','-g','-fsanitize=address,undefined','-fno-pie','-no-pie']
            binary=temp/mode
            result=subprocess.run(['cc','-std=c99',*flags,'-I'+str(temp/(BASE+'include')),*sources,'-o',binary],capture_output=True,timeout=60)
            if result.returncode:raise ValueError('monitor_envelope_compile:'+result.stderr.decode()[:1000])
            result=subprocess.run([binary],capture_output=True,timeout=30,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'))
            if result.returncode:raise ValueError('monitor_envelope_controls:'+result.stderr.decode()[:1000])
            value=json.loads(result.stdout)
            if value!={'passed':True,'checks':35338,'send_caps':20,'coalesced_frames':3,'sockets_opened':0}:raise ValueError('monitor_envelope_result')
            if executions and value!=executions['release']['result']:raise ValueError('monitor_envelope_modes')
            executions[mode]={'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'result':value}
    functions={}
    for file,names in [('network/netio_receive.c',['pktGetTcp','pktGetTcpAsync']),('network/netio_core.c',['blowfishPad']),('network/netio_send.c',['pktSendCmd']),('network/net_link.c',['netConnectEx','handleControlCommand']),('network/net_version.c',['applyNetworkVersionToLink'])]:
        for name in names:functions[name]=hashlib.sha256(extract(decoded(original[file]),name).encode()).hexdigest()
    proof={'schema':'coh-bounded-monitor-tcp-envelope-host-v1','passed':True,'source_tree':ORIGINAL_TREE,
           'original_source_sha256':{n:hashlib.sha256(v).hexdigest() for n,v in original.items()},'original_function_sha256':functions,
           'reused_native_dependencies_sha256':{n:hashlib.sha256(v).hexdigest() for n,v in raw_deps.items()},
           'local_source_sha256':{name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in local_names+['qualify_monitor_envelope.py']},
           'executions':executions,'native_frame_and_bit_kernels_reused':True,'original_socket_functions_executed':False,'original_blowfishPad_executed':True,
           'actual_tcp_delivery_executed':False,'actual_process_channel_verified':False,'tcp_streaming_compression_qualified':False,
           'android_execution_performed':False,'leak_sanitizer_enabled':False}
    output.write_text(json.dumps(proof,indent=2)+'\n');return proof


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    proof=qualify(a.source_root.resolve(),a.output);print(json.dumps(proof['executions']['release']['result']))
