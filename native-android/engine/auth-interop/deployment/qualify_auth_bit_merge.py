#!/usr/bin/env python3
"""Qualify exact original auth ownership masks and the DB merge block."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from source_audit import decoded,extract
from hosted_auth_stage import ORIGINAL_TREE


def qualify(root,output):
    def git(*args):return subprocess.check_output(['git','-C',str(root),*args],timeout=30)
    if git('rev-parse','HEAD:upstream/ouroboros').decode().strip()!=ORIGINAL_TREE:raise ValueError('auth_mask_original_tree')
    paths=['upstream/ouroboros/Common/auth/authUserData.c','upstream/ouroboros/DBServer/src/authcomm.c']
    raw={p:git('show','HEAD:'+p) for p in paths};source=decoded(raw[paths[0]])
    defines='\n'.join(line for line in source.splitlines() if re.match(r'#define (WORD_|BITS_|SHIFT_|TRANSLATE_)',line))
    start=source.index('static U32 authUserBitMaskAuth[]');end=source.index('};',source.index('static U32 authUserBitMaskGame[]'))+2
    arrays=source[start:end];function=extract(source,'authUserMaskAuthBits')
    receive=extract(decoded(raw[paths[1]]),'handleRecvGameData')
    begin=receive.index('    authUserMaskAuthBits(entry->user_data');finish=receive.index('    authSendPlayOK(',begin)
    merge=receive[begin:finish]
    template=Path(__file__).with_name('auth_bit_merge_fixture.c').read_text()
    code=template.replace('/* EXACT_MASK_SOURCE */',defines+'\n'+arrays+'\n'+function).replace('/* EXACT_MERGE_BLOCK */',merge)
    executions={};masks=None
    with tempfile.TemporaryDirectory(prefix='coh-auth-mask-') as temp:
        directory=Path(temp);generated=directory/'mask.c';generated.write_text(code)
        for mode in ('release','asan_ubsan'):
            flags=['-O2'] if mode=='release' else ['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
            binary=directory/mode
            result=subprocess.run(['cc','-std=c11',*flags,generated,'-o',binary],capture_output=True,timeout=60)
            if result.returncode:raise ValueError('auth_mask_compile_failed:'+result.stderr.decode()[:1000])
            result=subprocess.run([binary],capture_output=True,timeout=30,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'))
            if result.returncode:raise ValueError('auth_mask_control_failed:'+result.stderr.decode()[:1000])
            value=json.loads(result.stdout)
            if value.get('passed') is not True or value.get('checks')!=397313 or value.get('bits')!=1024 or value.get('overlapping_source_bits')!=31 or len(bytes.fromhex(value['auth_mask']))!=128 or len(bytes.fromhex(value['db_mask']))!=128:raise ValueError('auth_mask_result_shape')
            current=(value['auth_mask'],value['db_mask'])
            if masks is not None and current!=masks:raise ValueError('auth_mask_mode_mismatch')
            if executions and value!=executions['release']['result']:raise ValueError('auth_mask_result_mode_mismatch')
            masks=current;executions[mode]={'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'result':value}
    proof={'schema':'coh-original-auth-bit-ownership-merge-v1','passed':True,'source_tree':ORIGINAL_TREE,
        'source_sha256':{p:hashlib.sha256(v).hexdigest() for p,v in raw.items()},'mask_function_sha256':hashlib.sha256(function.encode()).hexdigest(),
        'original_merge_block_sha256':hashlib.sha256(merge.encode()).hexdigest(),'mask_definitions_sha256':hashlib.sha256((defines+'\n'+arrays).encode()).hexdigest(),
        'fixture_sha256':hashlib.sha256(template.encode()).hexdigest(),'qualifier_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'auth_mask_hex':masks[0],'db_mask_hex':masks[1],'executions':executions,
        'scope':'Exact original U32 ownership-mask definitions and authUserMaskAuthBits plus exact handleRecvGameData mask/OR block, bounded synthetic inputs. Includes legitimate overlap; no live ownership or session provenance.',
        'live_authenticated_db_login_verified':False,'runtime_order_or_channel_ownership_verified':False,'leak_sanitizer_enabled':False}
    output.write_text(json.dumps(proof,indent=2)+'\n');return proof


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    proof=qualify(a.source_root.resolve(),a.output);print(json.dumps({'passed':True,'checks_per_mode':proof['executions']['release']['result']['checks'],'live_authenticated_db_login_verified':False}))
