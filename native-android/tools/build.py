#!/usr/bin/env python3
"""Build the independent core library/test runner; never builds the Game/launcher."""
from pathlib import Path
import argparse,subprocess,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--cc',default='gcc');p.add_argument('--output',type=Path,required=True);p.add_argument('--android',action='store_true');p.add_argument('--sanitize',action='store_true');a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    sources=[ROOT/'src/coh_blowfish.c',ROOT/'src/coh_assets.c',ROOT/'src/coh_dds.c'];flags=['-std=c11','-O2','-Wall','-Wextra','-Werror','-I'+str(ROOT/'include'),'-I'+str(ROOT/'src')]
    if a.sanitize:flags+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
    lib=out/'libcoh_native_core.so';exe=out/'coh-native-core-tests'
    commands=[[a.cc,*flags,'-shared','-fPIC',*map(str,sources),'-lm','-o',str(lib)],[a.cc,*flags,*map(str,sources),str(ROOT/'tests/core_test.c'),'-lm','-o',str(exe)]]
    for command in commands:subprocess.run(command,check=True)
    result={'compiler':subprocess.check_output([a.cc,'--version'],text=True).splitlines()[0],'commands':commands,'android_cross_compiled':a.android,'device_executed':False,'files':[]}
    for f in [lib,exe]:result['files'].append({'name':f.name,'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
    if not a.android:
        result['host_test']=json.loads(subprocess.check_output([str(exe)],text=True));assert result['host_test']['passed']
    (out/'build-receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
