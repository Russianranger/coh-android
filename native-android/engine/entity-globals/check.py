#!/usr/bin/env python3
"""Standalone power-mode grammar; unchanged original send/receive oracle."""
import argparse
import ctypes as C
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
FILES=['Common/entity/PowerInfo.c','MapServer/src/entity/entsend.c',
       'Game/src/entity/entrecv.c','libs/UtilitiesLib/src/components/BitStream.c']

def sha(data):return hashlib.sha256(data).hexdigest()
def run(command,**kwargs):
    result=subprocess.run(list(map(str,command)),capture_output=True,text=True,timeout=120,**kwargs)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    return result.stdout
def source(root,path):
    file=root/'upstream/ouroboros'/path
    raw=file.read_bytes() if file.is_file() else subprocess.check_output(['git','-C',str(root),'show','HEAD:upstream/ouroboros/'+path])
    return raw.decode().replace('\r\n','\n')
def extract(text,name):
    m=re.search(r'^(?:static\s+)?(?:unsigned\s+int|void|int|U32)\s+'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',text,re.M)
    if not m:raise ValueError('original function missing: '+name)
    at=text.index('{',m.start())+1;depth=1
    while depth:depth+=(text[at]=='{')-(text[at]=='}');at+=1
    return text[m.start():at]+'\n'
def oracle(root,directory):
    sources={p:source(root,p) for p in FILES}
    pins={p:sha(s.encode()) for p,s in sources.items()}
    if pins!=json.loads((HERE/'source-pins.json').read_text())['sha256_lf']:raise ValueError('original source pin mismatch')
    spec=importlib.util.spec_from_file_location('globals_bit_helper',root/'native-android/tools/protocol_fixture/prepare.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    functions={}
    def get(path,name):
        body=extract(sources[path],name);functions[name]=sha(body.encode());return body
    code=helper.PREAMBLE+'\n#include "coh_entity_globals.h"\n'
    code+=''.join(get(FILES[3],n) for n in ['initBitStream','bsWriteBits','bsWriteBitsPack','bsReadBits','bsReadBitsPack','bsAlignByte','bsGetCursorBitPosition'])
    code+='''
static void pktSendBits(Packet *p,int n,U32 v){bsWriteBits(&p->stream,n,v);}
static void pktSendBitsPack(Packet *p,int n,U32 v){bsWriteBitsPack(&p->stream,n,v);}
static U32 pktGetBits(Packet *p,int n){return bsReadBits(&p->stream,n);}
static U32 pktGetBitsPack(Packet *p,int n){return bsReadBitsPack(&p->stream,n);}
'''
    code+=(HERE/'oracle_shim.h').read_text()
    code+=''.join(get(FILES[0],n) for n in ['entity_SendPowerModeUpdate','entity_ReceivePowerModeUpdate'])
    code+=(HERE/'oracle_fixture.c.inc').read_text()
    cfile=directory/'original.c';cfile.write_text(code);library=directory/'original.so'
    run([os.environ.get('CC','cc'),'-std=c99','-O0','-shared','-fPIC','-w','-I'+str(root/'native-android/include'),'-I'+str(HERE),cfile,'-o',library])
    lib=C.CDLL(str(library))
    lib.original_send.argtypes=[C.c_int,C.c_int,C.c_int,C.c_int,C.c_void_p,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32)]
    lib.original_receive.argtypes=[C.c_void_p,C.c_uint32,C.c_int,C.c_int,C.c_void_p,C.POINTER(C.c_uint32)]
    lib.original_prior.argtypes=[C.c_void_p]
    return lib,{'source_sha256_lf':pins,'original_functions':functions,'generated_oracle_sha256':sha(code.encode()),
                'producer_consumer':'both complete unchanged power-mode grammar functions executed',
                'adapters':'non-debug packet wrappers, bounded deterministic owner/earray shells; no original dictionaries or allocator',
                'source_oracle_sanitized':False,'scope':'trusted padded fixtures at O0; native parser separately sanitized; no malformed original consumer calls'}
def fixtures(lib,directory):
    state_size=lib.original_state_size()
    if state_size!=4100:raise ValueError('unexpected original observation ABI')
    rows=[];lines=[];comparisons=0
    def emit(name,data):lines.append('static const unsigned char '+name+'[]={'+','.join(map(str,data))+'};\n')
    prior=(C.c_uint8*state_size)();lib.original_prior(prior);emit('prior_state',bytes(prior))
    index=0
    for aligned in (0,1):
        for prefix in (range(8) if not aligned else (0,8)):
            for present,count in [(0,0),(0,1024),*[(1,n) for n in (0,1,6,7,8,63,64,1024,1025)]]:
                data=(C.c_uint8*32768)();bits=C.c_uint32();flag=C.c_uint32(999)
                lib.original_send(present,count,aligned,prefix,data,C.byref(bits),C.byref(flag))
                if flag.value!=0:raise ValueError('source send did not clear dirty flag')
                emit('data_'+str(index),bytes(data[:(bits.value+7)//8]))
                expected='NULL';status='COH_LIMIT' if count>1024 else 'COH_OK'
                if status=='COH_OK':
                    state=(C.c_uint8*state_size)();cursor=C.c_uint32()
                    lib.original_receive(data,bits.value,aligned,prefix,state,C.byref(cursor))
                    if cursor.value!=bits.value:raise ValueError('original consumer cursor mismatch')
                    emit('state_'+str(index),bytes(state));expected='state_'+str(index);comparisons+=1
                rows.append('{data_%d,sizeof(data_%d),%d,%d,%d,%d,%d,%s,%s}'%(index,index,bits.value,aligned,prefix,present,count,status,expected));index+=1
    lines.append('static const Fixture fixtures[]={'+',\n'.join(rows)+'};\n')
    path=directory/'fixtures.h';path.write_text(''.join(lines))
    return {'count':index,'producer_consumer_comparisons':comparisons,'sha256':sha(path.read_bytes())}
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source-root',type=Path,default=ROOT);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--sanitize',action='store_true');parser.add_argument('--fixtures-output',type=Path)
    parser.add_argument('--ndk',type=Path);parser.add_argument('--android-output',type=Path);args=parser.parse_args()
    if args.source_root.resolve()!=ROOT:parser.error('--source-root must identify this driver checkout')
    if bool(args.ndk)!=bool(args.android_output):parser.error('both --ndk and --android-output required')
    before=run(['git','-C',ROOT,'status','--porcelain']).strip();revision=run(['git','-C',ROOT,'rev-parse','HEAD']).strip();tree=run(['git','-C',ROOT,'rev-parse','HEAD^{tree}']).strip()
    with tempfile.TemporaryDirectory(prefix='coh-entity-globals-') as name:
        directory=Path(name);lib,original=oracle(ROOT,directory);fixture=fixtures(lib,directory)
        if args.fixtures_output:args.fixtures_output.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(directory/'fixtures.h',args.fixtures_output)
        sources=[HERE/'coh_entity_globals.c',HERE/'../replication/coh_replication.c',HERE/'test_entity_globals.c']
        common=['-std=c99','-Wall','-Wextra','-Werror','-pedantic','-I'+str(directory),'-I'+str(HERE)]
        modes=[('release',['-O2'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])] if args.sanitize else [])
        checks={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        for mode,flags in modes:
            binary=directory/mode;run([os.environ.get('CC','cc'),*common,*flags,*sources,'-lm','-o',binary]);checks[mode]=json.loads(run([binary],env=env))
        if any(v!=checks['release'] for v in checks.values()):raise ValueError('native mode results differ')
        # A real C++ link verifies the additive public ABI guard.
        cpp=directory/'abi.cpp';cpp.write_text('#include "coh_entity_globals.h"\nint main(){return coh_global_power_modes(nullptr,nullptr,nullptr)==COH_INVALID?0:1;}\n')
        objects=[]
        for i,p in enumerate(sources[:2]):
            obj=directory/(str(i)+'.o');run([os.environ.get('CC','cc'),*common,'-O2','-c',p,'-o',obj]);objects.append(obj)
        run([os.environ.get('CXX','c++'),'-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-lm','-o',directory/'cpp-abi']);run([directory/'cpp-abi'])
        paths=[*sources,*sorted(HERE.glob('*.h')),HERE/'CMakeLists.txt',HERE/'check.py',HERE/'oracle_fixture.c.inc',HERE/'source-pins.json',HERE/'../replication/coh_replication.h',HERE/'../coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',ROOT/'native-android/tools/protocol_fixture/prepare.py']
        source_hashes={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in paths}
        android={}
        if args.ndk:
            args.android_output.mkdir(parents=True,exist_ok=True);shutil.copyfile(directory/'fixtures.h',args.android_output/'fixtures.h')
            for abi,compiler in [('arm64-v8a','aarch64-linux-android26-clang'),('x86_64','x86_64-linux-android26-clang')]:
                dest=args.android_output/abi;dest.mkdir(parents=True,exist_ok=True);binary=dest/'coh_entity_globals_test'
                run([args.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'/compiler,*common,'-O2',*sources,'-lm','-o',binary])
                receipt={'passed':True,'abi':abi,'binary':binary.name,'binary_sha256':sha(binary.read_bytes()),'fixtures_sha256':fixture['sha256'],'source_sha256':source_hashes,'executed':False}
                (dest/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');android[abi]=receipt
        after=run(['git','-C',ROOT,'status','--porcelain']).strip()
        proof={'schema':'coh-entity-globals-qualification-v1','passed':True,'original':original,'fixtures':fixture,'fixtures_sha256':fixture['sha256'],'checks':checks,'android':android,
               'source_revision':revision,'source_tree':tree,'source_worktree_clean_before':not before,'source_worktree_clean_after':not after,
               'cpp_link_passed':True,'full_update_complete':False,'acknowledgments_enabled':False,'real_server_interoperability':False,'thor_accepted':False,'source_sha256':source_hashes}
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(proof,indent=2)+'\n')
        print(json.dumps({'passed':True,'checks':checks,'fixtures':fixture,'cpp_link_passed':True,'android_built':list(android)}))
if __name__=='__main__':main()
