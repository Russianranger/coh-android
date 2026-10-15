#!/usr/bin/env python3
"""Source-checked TCP auth controller tests; peer is explicitly synthetic."""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, tempfile
HERE=Path(__file__).resolve().parent
NATIVE=HERE.parents[1]

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd,**kwargs):
    r=subprocess.run([str(x) for x in cmd],text=True,capture_output=True,timeout=120,**kwargs)
    if r.returncode:raise RuntimeError(repr(cmd)+'\n'+r.stdout+r.stderr)
    return r.stdout

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--sanitize',action='store_true')
    p.add_argument('--ndk',type=Path)
    p.add_argument('--crypto-root',type=Path,help='Parent of both ABI public libcrypto builds')
    p.add_argument('--android-output',type=Path)
    a=p.parse_args()
    pins=json.loads((HERE/'source-pins.json').read_text())
    for path,sha in pins['sha256_lf'].items():
        actual=hashlib.sha256((a.source_root/path).read_text().replace('\r\n','\n').encode()).hexdigest()
        if actual!=sha:raise RuntimeError('Pinned source differs: '+path)
    sources=[HERE/'coh_login.c',NATIVE/'engine/auth/coh_auth.c',NATIVE/'protocol/coh_protocol.c',NATIVE/'src/coh_blowfish.c']
    host=[*sources,NATIVE/'engine/auth/coh_auth_openssl.c',HERE/'test_login.c']
    accepted=[NATIVE/'protocol/coh_protocol.c',NATIVE/'src/coh_blowfish.c']
    flags=['-std=c11','-Wall','-Wextra','-Werror','-ffp-contract=off','-I'+str(NATIVE/'include')]
    wrap=['-Wl,--wrap=connect,--wrap=send']
    proof={'schema':'coh-native-auth-tcp-controller-v1','source_audit':pins,'tests':{},'android':{},
           'actual_server_interoperability_verified':False,'real_account_login_verified':False,'thor_accepted':False,
           'scope':'Actual TCP sockets/real host or public Android crypto; scripted source-layout AuthServer replies. No real account database.'}
    with tempfile.TemporaryDirectory(prefix='coh-login-') as d:
        d=Path(d)
        modes=[('release',['-O2'])]
        if a.sanitize:modes += [('asan_ubsan',['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie'])]
        for name,extra in modes:
            exe=d/name
            # GCC13 inlines an accepted, unused protocol decoder into a false-positive
            # maybe-uninitialized warning at O2. Keep that pinned dependency at O0;
            # new controller/test/provider code remains optimized and strict.
            objects=[]
            for index,source in enumerate(accepted):
                obj=d/(name+'-'+str(index)+'.o')
                run(['cc',*flags,*extra,'-O0','-c',source,'-o',obj]);objects.append(obj)
            run(['cc',*flags,*extra,*[s for s in host if s not in accepted],*objects,*wrap,'-lcrypto','-o',exe])
            env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
            proof['tests'][name]=json.loads(run([exe],env=env))
    if a.ndk:
        if not a.crypto_root or not a.android_output:p.error('Android linkage requires --crypto-root and --android-output')
        tools=a.ndk.resolve()/'toolchains/llvm/prebuilt/linux-x86_64/bin'
        for abi,triple in [('arm64-v8a','aarch64'),('x86_64','x86_64')]:
            crypto=a.crypto_root.resolve()/abi;receipt=json.loads((crypto/'receipt.json').read_text())
            if receipt['status']!='PASS' or receipt['abi']!=abi:raise RuntimeError('Wrong public crypto receipt')
            for path,sha in receipt['artifacts_sha256'].items():
                if digest(crypto/path)!=sha:raise RuntimeError('Public crypto archive identity differs')
            out=a.android_output.resolve()/abi;out.mkdir(parents=True,exist_ok=True)
            exe=out/'test_login_android';cc=tools/(triple+'-linux-android26-clang')
            archives=[crypto/'lib/libcoh_auth_android_crypto.a',crypto/'lib/libcrypto.a']
            command=[cc,*flags,'-O2','-I'+str(crypto/'include'),*sources,HERE/'test_login.c',*wrap,*archives,'-ldl','-lm','-o',exe]
            run(command)
            elf=run([tools/'llvm-readelf','-h','-d',exe]);(out/'elf.txt').write_text(elf)
            if 'libcrypto.so' in elf or 'libssl.so' in elf:raise RuntimeError('Unexpected dynamic crypto dependency')
            build={'passed':True,'abi':abi,'command':list(map(str,command)),'binary_sha256':digest(exe),
                   'binary':exe.name,'crypto_build_receipt_sha256':digest(crypto/'receipt.json'),
                   'source_sha256':{str(s.relative_to(NATIVE)):digest(s) for s in [*host,HERE/'coh_login.h']},
                   'android_executed':False,'real_account_login_verified':False}
            (out/'receipt.json').write_text(json.dumps(build,indent=2)+'\n');proof['android'][abi]=build
    proof['passed']=True
    proof['leak_sanitizer']='not claimed locally; task enumeration unavailable, address/UB checks enabled'
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps({'passed':True,'tests':proof['tests'],'android_built':list(proof['android'])}))
if __name__=='__main__':main()
