#!/usr/bin/env python3
"""Execute exact original bsWriteString on bounded synthetic version strings."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from source_audit import decoded,extract
import version_observation_contract as contract

HERE=Path(__file__).resolve().parent
SOURCE='upstream/ouroboros/libs/UtilitiesLib/src/components/BitStream.c'


def qualify(root,output):
    audit=contract.source_audit(root)
    raw=subprocess.check_output(['git','-C',str(root),'show','HEAD:'+SOURCE],timeout=30)
    function=extract(decoded(raw),'bsWriteString')
    template=(HERE/'version_string_writer_fixture.c').read_text()
    if template.count('/* EXACT_ORIGINAL_WRITER */')!=1:raise ValueError('version_writer_fixture_boundary')
    generated=template.replace('/* EXACT_ORIGINAL_WRITER */',function);executions={}
    with tempfile.TemporaryDirectory(prefix='coh-version-string-') as temp:
        path=Path(temp)/'fixture.c';path.write_text(generated)
        for mode in ('release','asan_ubsan'):
            flags=['-O2'] if mode=='release' else ['-O1','-g','-fsanitize=address,undefined','-fno-pie','-no-pie']
            binary=Path(temp)/mode
            result=subprocess.run(['cc','-std=c11',*flags,path,'-o',binary],capture_output=True,timeout=60)
            if result.returncode:raise ValueError('version_writer_compile:'+result.stderr.decode()[:1000])
            result=subprocess.run([binary],capture_output=True,timeout=30,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'))
            if result.returncode or len(result.stdout)>1024*1024:raise ValueError('version_writer_execution')
            rows=[json.loads(row) for row in result.stdout.splitlines()]
            if len(rows)!=792:raise ValueError('version_writer_count')
            for index,row in enumerate(rows):
                offset=index//99;length=index%99+1
                if row['offset']!=offset or row['length']!=length or row['bits']!=(length+16)*8:raise ValueError('version_writer_fixture_shape')
                value=contract.decode_body(bytes.fromhex(row['data']),start_bit=offset,bit_count=row['bits'],command=10,has_debug_info=False,owner_generation='a'*64)
                if value.compatible_version!='v'*length or value.server_patch_version!='server-version' or value.actual_process_version_verified:
                    raise ValueError('version_writer_decoder_mismatch')
            executions[mode]={'checks':792,'offsets':8,'first_lengths':99,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
                              'writer_output_sha256':hashlib.sha256(result.stdout).hexdigest()}
    if executions['release']['writer_output_sha256']!=executions['asan_ubsan']['writer_output_sha256']:raise ValueError('version_writer_mode_mismatch')
    proof={'schema':'coh-original-version-string-writer-qualification-v1','passed':True,'source_tree':audit['source_tree'],
           'source_sha256':hashlib.sha256(raw).hexdigest(),'original_function_sha256':hashlib.sha256(function.encode()).hexdigest(),
           'local_source_sha256':{name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in ('version_string_writer_fixture.c','qualify_version_string_writer.py','version_observation_contract.py')},
           'executions':executions,'original_bsWriteString_executed':True,'actual_version_getter_executed':False,
           'original_packet_wrapper_executed':False,'netlink_transport_executed':False,'actual_process_version_verified':False,
           'windows_service_executed':False,'leak_sanitizer_enabled':False}
    output.write_text(json.dumps(proof,indent=2)+'\n');return proof


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=qualify(a.source_root.resolve(),a.output);print(json.dumps({'passed':result['passed'],'checks_per_mode':792,'actual_process_version_verified':False}))
