#!/usr/bin/env python3
"""Execute exact original one-shot auth cache consumer under bounded fixtures."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from source_audit import decoded,extract
from hosted_auth_stage import ORIGINAL_TREE

PATH='upstream/ouroboros/DBServer/src/authcomm.c'


def qualify(root,output):
    def git(*args):return subprocess.check_output(['git','-C',str(root),*args],timeout=30)
    if git('rev-parse','HEAD:upstream/ouroboros').decode().strip()!=ORIGINAL_TREE:raise ValueError('handoff_original_source_tree')
    source=git('show','HEAD:'+PATH);text=decoded(source)
    struct=text[text.index('typedef struct'):text.index('} AuthEntry;')+len('} AuthEntry;')]
    functions={name:extract(text,name) for name in ('trimTrailingWhitespace','authValidLogin')}
    fixture=Path(__file__).with_name('auth_cache_consumer_fixture.c').read_text()
    code=fixture.replace('/* EXACT_AUTH_ENTRY */',struct).replace('/* EXACT_FUNCTIONS */','\n'.join(functions.values()))
    results={}
    with tempfile.TemporaryDirectory(prefix='coh-auth-cache-') as temp:
        directory=Path(temp);generated=directory/'consumer.c';generated.write_text(code)
        for mode in ('release','asan_ubsan'):
            flags=['-O2'] if mode=='release' else ['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
            binary=directory/mode
            result=subprocess.run(['cc','-std=c11',*flags,generated,'-o',binary],capture_output=True,timeout=60)
            if result.returncode:raise ValueError('auth_cache_fixture_compile_failed:'+result.stderr.decode()[:1000])
            result=subprocess.run([binary],capture_output=True,timeout=30,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'))
            if result.returncode:raise ValueError('auth_cache_fixture_control_failed:'+result.stderr.decode()[:1000])
            value=json.loads(result.stdout)
            expected={'passed':True,'checks':544839,'cache_slots':4096,'one_shot_consumer':True,'zero_cookie_source_semantics':True,'cookie_generator_executed':False,'live_service_executed':False}
            if json.dumps(value,sort_keys=True)!=json.dumps(expected,sort_keys=True):raise ValueError('auth_cache_fixture_result')
            results[mode]={'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'result':value}
    proof={'schema':'coh-original-auth-cache-consumer-v1','passed':True,'source_tree':ORIGINAL_TREE,'source_path':PATH,
        'source_sha256':hashlib.sha256(source).hexdigest(),'function_sha256':{n:hashlib.sha256(v.encode()).hexdigest() for n,v in functions.items()},
        'fixture_sha256':hashlib.sha256(fixture.encode()).hexdigest(),'qualifier_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'generated_sha256':hashlib.sha256(code.encode()).hexdigest(),'executions':results,
        'scope':'Exact original authValidLogin and trimTrailingWhitespace with fixed bounded nonempty names and in-memory AuthEntry cache; no network, cryptography, SQL or service execution.',
        'live_authenticated_db_login_verified':False,'cookie_generator_executed':False,'leak_sanitizer_enabled':False}
    output.write_text(json.dumps(proof,indent=2)+'\n');return proof


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    proof=qualify(a.source_root.resolve(),a.output);print(json.dumps({'passed':True,'checks_per_mode':proof['executions']['release']['result']['checks'],'live_authenticated_db_login_verified':False}))
