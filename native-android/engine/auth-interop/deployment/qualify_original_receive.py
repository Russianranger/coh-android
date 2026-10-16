#!/usr/bin/env python3
"""Qualify original receive-buffer offsets; no AuthServer binary is modified."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from source_audit import decoded, extract
from hosted_auth_stage import ORIGINAL_TREE

HERE = Path(__file__).resolve().parent


def qualify(root, output):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args], timeout=30)
    if git('rev-parse', 'HEAD:upstream/ouroboros').decode().strip() != ORIGINAL_TREE:
        raise ValueError('original_receive_source_tree_mismatch')
    paths = {'socket': 'upstream/ouroboros/AuthServer/src/SocketServerEx.cpp',
             'io': 'upstream/ouroboros/AuthServer/src/IOSocket.cpp'}
    source = {key: git('show', 'HEAD:' + path) for key, path in paths.items()}
    functions = {'CSocketServerEx::OnRead': extract(decoded(source['socket']), 'CSocketServerEx::OnRead'),
                 'CIOSocket::Read': extract(decoded(source['io']), 'CIOSocket::Read')}
    code = (HERE / 'original_receive_fixture.cpp').read_text()
    code = code.replace('/* EXACT_ORIGINAL_FUNCTIONS */', '\n'.join(functions.values()))
    results = {}
    with tempfile.TemporaryDirectory(prefix='coh-original-receive-') as temporary:
        directory = Path(temporary)
        generated = directory / 'original_receive.cpp'
        generated.write_text(code)
        for mode in ('release', 'asan_ubsan'):
            binary = directory / mode
            flags = ['-O2'] if mode == 'release' else ['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
            compiled = subprocess.run(['c++','-std=c++17',*flags,generated,'-o',binary], capture_output=True,timeout=60)
            if compiled.returncode:
                raise ValueError('original_receive_compile_failed:' + compiled.stderr.decode()[:3000])
            result = subprocess.run([binary],capture_output=True,timeout=30,env=dict(os.environ,ASAN_OPTIONS="detect_leaks=0:halt_on_error=1",UBSAN_OPTIONS="halt_on_error=1"))
            if result.returncode:
                raise ValueError('original_receive_control_failed:' + result.stderr.decode()[:3000])
            value = json.loads(result.stdout)
            if value != {'passed':True,'checks':344,'complete_body_matches':True,'one_and_two_byte_header_splits_match':True,
                         'body_split_offsets_wrong':167,'seven_byte_schedule_rejected':True,
                         'cryptography_executed':False,'live_service_executed':False}:
                raise ValueError('original_receive_result_mismatch')
            results[mode] = {'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'result':value}
    proof = {'schema':'coh-original-authserver-receive-offset-v1','passed':True,
             'original_source_tree':ORIGINAL_TREE,
             'source_sha256':{paths[key]:hashlib.sha256(data).hexdigest() for key,data in source.items()},
             'function_sha256_utf8_lf':{name:hashlib.sha256(text.encode()).hexdigest() for name,text in functions.items()},
             'generated_oracle_sha256':hashlib.sha256(code.encode()).hexdigest(),'executions':results,
             'scope':'Exact original OnRead and Read; deterministic opaque 168-byte body and exact-byte decoder-boundary stub. OS IO/dispatch are bounded fixtures, not Windows or cryptographic execution.',
             'inference':'Consistent with hosted run38972290813 reset after deliberate seven-byte sends; private server logs were removed, so the live close reason is not directly proven.',
             'original_service_changed':False,'encrypted_account_login_verified':False,'leak_sanitizer_enabled':False}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(proof,indent=2)+'\n')
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=qualify(args.source_root.resolve(),args.output)
    print(json.dumps({'passed':result['passed'],'checks_per_mode':344,'body_split_offsets_wrong':167,
                      'encrypted_account_login_verified':False}))
