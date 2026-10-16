#!/usr/bin/env python3
"""Execute unchanged original control producer/TEST_CLIENT consumer and native controls."""
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
FILES=['MapServer/src/svr/svr_player.c','Game/src/player/player.c',
       'Common/cmdparse/cmdcontrols.h','Common/entity/motion.h','Common/player/pmotion.c',
       'libs/UtilitiesLib/src/components/BitStream.c','libs/UtilitiesLib/src/network/net_packetutil.c']

def run(command,**kwargs):
    result=subprocess.run(list(map(str,command)),capture_output=True,text=True,timeout=120,**kwargs)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    return result.stdout

def source(root,path):
    local=root/'upstream/ouroboros'/path
    raw=local.read_bytes() if local.is_file() else subprocess.check_output(['git','-C',str(root),'show','HEAD:upstream/ouroboros/'+path])
    return raw.decode().replace('\r\n','\n')

def extract(text,name):
    m=re.search(r'^(?:static\s+)?(?:unsigned\s+int|void|int|U32|F32|float)\s+'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',text,re.M)
    if not m:raise ValueError('missing original function '+name)
    at=text.index('{',m.start())+1;depth=1
    while depth:depth+=(text[at]=='{')-(text[at]=='}');at+=1
    return text[m.start():at]+'\n'

def declaration(text,name):
    match=re.search(r'typedef (?:struct|enum) '+name+r'\s*\{.*?\}\s*'+name+r';',text,re.S)
    if not match:raise ValueError('missing declaration '+name)
    return match[0]+'\n'

def oracle(root,directory):
    src={p:source(root,p) for p in FILES}
    pins={p:hashlib.sha256(s.encode()).hexdigest() for p,s in src.items()}
    if pins!=json.loads((HERE/'source-pins.json').read_text())['sha256_lf']:raise ValueError('source pin mismatch')
    spec=importlib.util.spec_from_file_location('control_bit_helper',root/'native-android/tools/protocol_fixture/prepare.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    pre=helper.PREAMBLE.replace('hasDebugInfo,compress,ordered,ordered_id;','hasDebugInfo,compress,ordered,ordered_id,id;')
    pre=pre.replace('int compressionAllowed,orderedAllowed;} NetLink;','int compressionAllowed,orderedAllowed;void *userData;int lost_packet_recv;} NetLink;')
    # Above pinned helper declares NetLink with compressionAllowed on same line.
    pre=pre.replace('int ack_count;U32 ids_toack[32];int compressionAllowed,orderedAllowed;} NetLink;',
                    'int ack_count;U32 ids_toack[32];int compressionAllowed,orderedAllowed;void *userData;int lost_packet_recv;} NetLink;')
    code=pre+'\n#include "coh_entity_control.h"\ntypedef float F32;\n'
    names=[];function_hashes={}
    def get(path,name):
        body=extract(src[path],name);names.append(name);function_hashes[name]=hashlib.sha256(body.encode()).hexdigest();return body
    bit=FILES[5]
    code+=''.join(get(bit,n) for n in ['initBitStream','bsWriteBits','bsWriteBitsPack','bsReadBits','bsReadBitsPack','bsAlignByte','bsGetCursorBitPosition','bsWriteBitsArray','bsReadBitsArray','bsWriteF32','bsReadF32'])
    code+='''
static void pktSendBits(Packet*p,int n,U32 v){bsWriteBits(&p->stream,n,v);}
static void pktSendBitsPack(Packet*p,int n,U32 v){bsWriteBitsPack(&p->stream,n,v);}
static U32 pktGetBits(Packet*p,int n){return bsReadBits(&p->stream,n);}
static U32 pktGetBitsPack(Packet*p,int n){return bsReadBitsPack(&p->stream,n);}
static void pktSendF32(Packet*p,float v){bsWriteF32(&p->stream,v);}
static float pktGetF32(Packet*p){return bsReadF32(&p->stream);}
static void pktSendBitsArray(Packet*p,int n,const void*v){bsWriteBitsArray(&p->stream,n,v);}
static void pktGetBitsArray(Packet*p,int n,void*v){bsReadBitsArray(&p->stream,n,v);}
'''
    code+=''.join(get(FILES[6],n) for n in ['pktSendIfSetF32','pktGetIfSetF32'])
    code+='#define SERVER 1\ntypedef struct ServerControlState ServerControlState;\n'
    code+=declaration(src[FILES[3]],'SurfaceParams')+declaration(src[FILES[3]],'SurfParamIndex')+declaration(src[FILES[2]],'ServerControlState')
    code+=(HERE/'oracle_shim.h').read_text().replace('typedef float F32;','').replace('enum { SURFPARAM_GROUND, SURFPARAM_AIR, SURFPARAM_MAX };','')
    code+=''.join(get(FILES[0],n) for n in ['svrPlayerSendFuturePushList','svrPlayerSendPhysicsPositions','svrPlayerSendControlState'])
    code+=''.join(get(FILES[1],n) for n in ['playerReceiveFuturePushList','playerReceiveServerPhysicsPositions','playerReceiveServerControlState','playerReceiveControlState'])
    code+='''
typedef char exact_surface_size[sizeof(SurfaceParams)==20?1:-1];
typedef char exact_surface_offsets[(offsetof(SurfaceParams,traction)==0&&offsetof(SurfaceParams,friction)==4&&offsetof(SurfaceParams,bounce)==8&&offsetof(SurfaceParams,gravity)==12&&offsetof(SurfaceParams,max_speed)==16)?1:-1];
unsigned original_state_size(void){U32 endian=1;assert(*(U8*)&endian==1);assert(sizeof(float)==4);return sizeof(CohControlState);}
unsigned original_update_size(void){return sizeof(CohControlUpdate);}
'''
    code+=(HERE/'oracle_fixture.c.inc').read_text()
    cfile=directory/'original.c';cfile.write_text(code);library=directory/'original.so'
    run([os.environ.get('CC','cc'),'-std=c99','-O0','-shared','-fPIC','-w','-I'+str(root/'native-android/include'),'-I'+str(HERE),cfile,'-lm','-o',library])
    lib=C.CDLL(str(library));lib.original_send.argtypes=[C.c_int,C.c_int,C.c_int,C.c_void_p,C.POINTER(C.c_uint32)]
    lib.original_receive.argtypes=[C.c_void_p,C.c_uint32,C.c_int,C.c_int,C.c_uint32,C.c_uint32,C.c_void_p,C.c_void_p,C.POINTER(C.c_uint32)]
    return lib,{'source_sha256_lf':pins,'original_functions':function_hashes,
                'generated_oracle_sha256':hashlib.sha256(code.encode()).hexdigest(),
                'surface_bytes':40,'surface_member_offsets':[0,4,8,12,16],
                'consumer_mode':'unchanged TEST_CLIENT functions; empty local history and first_packet_sent=0; deterministic owner shells',
                'packet_adapters':'non-debug wrappers around unchanged original BitStream functions',
                'source_writer_sanitized':False,'source_writer_scope':'trusted padded input at O0; no malformed source consumer calls'}

def fixtures(lib,directory):
    rows=[];text=[];state_size=lib.original_state_size();update_size=lib.original_update_size()
    def emit(label,value):
        text.append('static const unsigned char '+label+'[]={'+','.join(map(str,value))+'};\n')
    index=0
    for mode in (0,1):
        for prefix in (range(8) if not mode else (0,8)):
            for scenario in range(9):
                data=(C.c_uint8*32768)();bits=C.c_uint32();lib.original_send(scenario,mode,prefix,data,C.byref(bits))
                emit(f'data_{index}',bytes(data[:(bits.value+7)//8]))
                expected='NULL';events='NULL';ordering='NULL';status='COH_UNSUPPORTED' if scenario==5 else ('COH_LIMIT' if scenario==6 else 'COH_OK')
                if status=='COH_OK':
                    state=(C.c_uint8*state_size)();event=(C.c_uint8*update_size)();cursor=C.c_uint32()
                    lib.original_receive(data,bits.value,mode,prefix,12,0,state,event,C.byref(cursor))
                    if cursor.value!=bits.value:raise ValueError('original end cursor differs')
                    emit(f'state_{index}',bytes(state));emit(f'events_{index}',bytes(event));expected=f'state_{index}';events=f'events_{index}'
                    ordered=[]
                    for prior in (11,12,13):
                        lib.original_receive(data,bits.value,mode,prefix,12,prior,state,event,C.byref(cursor))
                        if cursor.value!=bits.value:raise ValueError('original stale end cursor differs')
                        ordered.extend(bytes(state))
                    emit(f'ordering_{index}',ordered);ordering=f'ordering_{index}'
                rows.append('{data_%d,sizeof(data_%d),%d,%d,%d,%s,%s,%s,%s}'%(index,index,bits.value,mode,prefix,status,expected,events,ordering));index+=1
    text.append('static const Fixture fixtures[]={'+',\n'.join(rows)+'};\n')
    text.append(f'#define ORIGINAL_STATE_SIZE {state_size}u\n#define ORIGINAL_UPDATE_SIZE {update_size}u\n')
    output=directory/'fixtures.h';output.write_text(''.join(text))
    return {'count':index,'producer_consumer_comparisons':280,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source-root',type=Path,default=ROOT);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--sanitize',action='store_true');parser.add_argument('--fixtures-output',type=Path)
    parser.add_argument('--ndk',type=Path);parser.add_argument('--android-output',type=Path);args=parser.parse_args()
    if bool(args.ndk)!=bool(args.android_output):parser.error('both --ndk and --android-output required')
    with tempfile.TemporaryDirectory(prefix='coh-entity-control-') as name:
        directory=Path(name);lib,original=oracle(args.source_root.resolve(),directory);fixture=fixtures(lib,directory)
        if args.fixtures_output:args.fixtures_output.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(directory/'fixtures.h',args.fixtures_output)
        sources=[HERE/'coh_entity_control.c',HERE/'../replication/coh_replication.c',HERE/'test_entity_control.c']
        common=['-std=c99','-Wall','-Wextra','-Werror','-pedantic','-I'+str(directory),'-I'+str(HERE)]
        modes=[('release',['-O2'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])] if args.sanitize else [])
        checks={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        for mode,flags in modes:
            exe=directory/mode;run([os.environ.get('CC','cc'),*common,*flags,*sources,'-lm','-o',exe]);checks[mode]=json.loads(run([exe],env=env))
        source_hashes={str(p.resolve().relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*sources,*sorted(HERE.glob('*.h')),HERE/'CMakeLists.txt',HERE/'check.py',HERE/'oracle_fixture.c.inc',HERE/'source-pins.json',HERE/'../replication/coh_replication.h',HERE/'../coh_contracts.h',ROOT/'native-android/tools/protocol_fixture/prepare.py']}
        android={}
        if args.ndk:
            args.android_output.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(directory/'fixtures.h',args.android_output/'fixtures.h')
            for abi,compiler in [('arm64-v8a','aarch64-linux-android26-clang'),('x86_64','x86_64-linux-android26-clang')]:
                dest=args.android_output/abi;dest.mkdir(parents=True,exist_ok=True);binary=dest/'coh_entity_control_test'
                run([args.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'/compiler,*common,'-O2',*sources,'-lm','-o',binary])
                receipt={'passed':True,'abi':abi,'binary':binary.name,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
                         'fixtures_sha256':fixture['sha256'],'source_sha256':source_hashes,'executed':False}
                (dest/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');android[abi]=receipt
        proof={'schema':'coh-entity-control-qualification-v1','passed':True,'original':original,'fixtures':fixture,'fixtures_sha256':fixture['sha256'],'checks':checks,'android':android,
               'full_update_complete':False,'acknowledgments_enabled':False,'real_server_interoperability':False,'thor_accepted':False,
               'source_sha256':source_hashes}
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(proof,indent=2)+'\n')
        print(json.dumps({'passed':True,'checks':checks,'fixtures':fixture,'android':android}))
if __name__=='__main__':main()
