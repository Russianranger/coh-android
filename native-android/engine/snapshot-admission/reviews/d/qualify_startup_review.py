#!/usr/bin/env python3
"""Independent original DB startup branch evidence; never starts a service."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
TREE='f634e21e230009fa8edc91d15429cd4da69eee8c'
def sha(value):return hashlib.sha256(value).hexdigest()
def qualify(root,output):
    deployment=root/'native-android/engine/auth-interop/deployment'
    sys.path.insert(0,str(deployment))
    from source_audit import decoded,extract
    def git(*args):return subprocess.check_output(['git','-C',str(root),*args],timeout=30)
    if git('rev-parse','HEAD:upstream/ouroboros').decode().strip()!=TREE:raise ValueError('original_tree_changed')
    path='upstream/ouroboros/AuthServer/src/DBConn.cpp'
    source=git('show','HEAD:'+path)
    names=['DBEnv::Init','DBEnv::AllocSQLPool','CDBConn::CDBConn']
    functions={name:extract(decoded(source),name) for name in names}
    fixture=(HERE/'startup_fixture.cpp').read_text()
    code=fixture.replace('/* EXACT_FUNCTIONS */','\n'.join(functions.values()))
    executions={}
    with tempfile.TemporaryDirectory(prefix='coh-d-review-') as temporary:
        temporary=Path(temporary);cpp=temporary/'review.cpp';cpp.write_text(code)
        for mode in ['release','asan_ubsan']:
            flags=['-O2'] if mode=='release' else ['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
            binary=temporary/mode
            result=subprocess.run(['c++','-std=c++17',*flags,cpp,'-o',binary],capture_output=True,timeout=60)
            if result.returncode:raise ValueError(result.stderr.decode()[:3000])
            result=subprocess.run([binary],capture_output=True,timeout=30,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'))
            if result.returncode:raise ValueError(result.stderr.decode()[:3000])
            value=json.loads(result.stdout)
            if not value['passed'] or value['checks']!=15:raise ValueError('result_changed')
            executions[mode]={'binary_sha256':sha(binary.read_bytes()),'result':value}
    proof={'schema':'coh-independent-auth-startup-review-v1','passed':True,'original_source_tree':TREE,
        'source_sha256':{path:sha(source)},'functions_sha256_utf8_lf':{name:sha(value.encode()) for name,value in functions.items()},
        'fixture_sha256':sha(fixture.encode()),'generated_oracle_sha256':sha(code.encode()),'executions':executions,
        'scope':'Exact Init, AllocSQLPool and CDBConn constructor; fixture ODBC/lock/logger and a Sleep interceptor raising after three waits. Does not establish historical failure cause, ODBC driver behavior or real wall-clock timeout.',
        'leak_sanitizer_enabled':False,'original_source_modified':False,'service_executed':False,'encrypted_login_verified':False}
    output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'checks_per_mode':15}))
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-root',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();qualify(args.source_root.resolve(),args.output)
