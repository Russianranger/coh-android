#!/usr/bin/env python3
"""Match bounded adapters to exact original AuthServer and DB packet writers."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from source_audit import decoded,extract
from hosted_auth_stage import ORIGINAL_TREE
import authenticated_handoff_contract as contract


def qualify(root,output):
    def git(*args):return subprocess.check_output(['git','-C',str(root),*args],timeout=30)
    if git('rev-parse','HEAD:upstream/ouroboros').decode().strip()!=ORIGINAL_TREE:raise ValueError('wire_original_source_tree')
    paths=('upstream/ouroboros/AuthServer/src/util.cpp','upstream/ouroboros/Common/auth/auth.c')
    source={p:git('show','HEAD:'+p) for p in paths}
    functions={'Assemble':extract(decoded(source[paths[0]]),'Assemble')}
    functions.update({n:extract(decoded(source[paths[1]]),n) for n in ('authPutU08','authPutU32')})
    template=Path(__file__).with_name('handoff_wire_fixture.cpp').read_text()
    code=template.replace('/* EXACT_FUNCTIONS */','\n'.join(functions.values()))
    executions={}
    with tempfile.TemporaryDirectory(prefix='coh-handoff-wire-') as temp:
        directory=Path(temp);generated=directory/'wire.cpp';generated.write_text(code)
        for mode in ('release','asan_ubsan'):
            flags=['-O2'] if mode=='release' else ['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
            binary=directory/mode
            result=subprocess.run(['c++','-std=c++17',*flags,generated,'-o',binary],capture_output=True,timeout=60)
            if result.returncode:raise ValueError('wire_fixture_compile_failed:'+result.stderr.decode()[:1000])
            result=subprocess.run([binary],capture_output=True,timeout=30,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'))
            if result.returncode:raise ValueError('wire_fixture_execution_failed:'+result.stderr.decode()[:1000])
            fixture=json.loads(result.stdout);checks=0;generation='a'*64
            if set(fixture)!={'about','short_userdata_disabled','db_play_ok','client_play_ok'} or [r['name']for r in fixture['about']]!=['x','sourcefixture','abcdefghijklmn']:raise ValueError('wire_fixture_corpus')
            for record in fixture['about']:
                about=contract.parse_about_to_play(bytes.fromhex(record['body']),generation)
                if (about.auth_id,about.account,about.time_remaining,about.login_flags,about.warning_flags,about.pay_stat,about.loyalty,about.loyalty_legacy,about.auth_data)!=(900001,record['name'],0,2,3,1,123,456,bytes(range(128))):raise ValueError('wire_adapter_original_producer_mismatch')
                checks+=1
            try:contract.parse_about_to_play(bytes.fromhex(fixture['short_userdata_disabled']),generation)
            except ValueError:checks+=1
            else:raise ValueError('wire_short_userdata_path_admitted')
            db=contract.parse_db_play_ok(bytes.fromhex(fixture['db_play_ok']),generation)
            client=contract.parse_client_play_ok(bytes.fromhex(fixture['client_play_ok']),generation)
            if db.auth_id!=900001 or db.cookie!=0x76543210 or client.cookie!=db.cookie or client.auth_id!=db.auth_id or client.shard_id!=3:raise ValueError('wire_cookie_relay_mismatch')
            checks+=1
            executions[mode]={'checks':checks,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'fixture_output_sha256':hashlib.sha256(result.stdout).hexdigest()}
    proof={'schema':'coh-original-auth-handoff-wire-v1','passed':True,'source_tree':ORIGINAL_TREE,
        'source_sha256':{p:hashlib.sha256(v).hexdigest() for p,v in source.items()},'function_sha256':{n:hashlib.sha256(v.encode()).hexdigest() for n,v in functions.items()},
        'fixture_sha256':hashlib.sha256(template.encode()).hexdigest(),'qualifier_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'executions':executions,
        'scope':'Exact original Assemble and authPutU08/U32 under bounded public fixture data; compares all bytes through bounded read-only parsers. No framing/encryption/socket/shard registration or live DB login.',
        'live_authenticated_db_login_verified':False,'cookie_generated':False,'leak_sanitizer_enabled':False}
    output.write_text(json.dumps(proof,indent=2)+'\n');return proof


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    proof=qualify(a.source_root.resolve(),a.output);print(json.dumps({'passed':True,'checks_per_mode':proof['executions']['release']['checks'],'live_authenticated_db_login_verified':False}))
