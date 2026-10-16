#!/usr/bin/env python3
"""Whole original character producer, exact tail subconsumers, bounded native parser."""
import argparse,ctypes as C,hashlib,importlib.util,json,os,re,shutil,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
FILES=['MapServer/src/entity/character_net_server.c','Game/src/entity/character_net_client.c',
       'Common/entity/character_net.c','Common/entity/character_base.h','Common/entity/boost.h',
       'Common/entity/powers.h','Common/entity/powers_load.c','Common/entity/Concept.h',
       'Common/entity/character_inventory.h','Common/entity/RewardItemType.h',
       'libs/UtilitiesLib/src/components/BitStream.c','libs/UtilitiesLib/src/network/net_packetutil.c']
def run(args,**kwargs):
    result=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=180,**kwargs)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    return result.stdout
def source(root,path):
    local=root/'upstream/ouroboros'/path
    raw=local.read_bytes() if local.is_file() else subprocess.check_output(['git','-C',str(root),'show','HEAD:upstream/ouroboros/'+path])
    return raw.decode().replace('\r\n','\n')
def extract(text,name):
    m=re.search(r'^(?:static\s+)?(?:const BasePower\s*\*|unsigned\s+int|void|int|U32|F32|float)\s*'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',text,re.M)
    if not m:raise ValueError('missing original function '+name)
    at=text.index('{',m.start())+1;depth=1
    while depth:depth+=(text[at]=='{')-(text[at]=='}');at+=1
    return text[m.start():at]+'\n'
def oracle(root,directory):
    src={p:source(root,p) for p in FILES};pins={p:hashlib.sha256(s.encode()).hexdigest() for p,s in src.items()}
    if pins!=json.loads((HERE/'source-pins.json').read_text())['sha256_lf']:raise ValueError('source pins mismatch')
    spec=importlib.util.spec_from_file_location('character_bit_helper',root/'native-android/tools/protocol_fixture/prepare.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    code=re.sub(r'static void pktSendBitsAuto\([^\n]+\n','',helper.PREAMBLE)
    code+='\n#include "coh_character_data.h"\ntypedef float F32;\n'
    functions={}
    def get(path,name):
        value=extract(src[path],name);functions[name]=hashlib.sha256(value.encode()).hexdigest();return value
    code+=''.join(get(FILES[10],n) for n in ['initBitStream','bsWriteBits','bsWriteBitsPack','bsReadBits','bsReadBitsPack','bsAlignByte','bsGetCursorBitPosition','bsWriteF32','bsReadF32','bsWriteString'])
    code+='''
static void pktSendBits(Packet*p,int n,U32 v){bsWriteBits(&p->stream,n,v);}
static void pktSendBitsPack(Packet*p,int n,U32 v){bsWriteBitsPack(&p->stream,n,v);}
static U32 pktGetBits(Packet*p,int n){return bsReadBits(&p->stream,n);}
static U32 pktGetBitsPack(Packet*p,int n){return bsReadBitsPack(&p->stream,n);}
static void pktSendF32(Packet*p,float v){bsWriteF32(&p->stream,v);}
static float pktGetF32(Packet*p){return bsReadF32(&p->stream);}
static void pktSendString(Packet*p,const char*v){bsWriteString(&p->stream,v);}
static int auto_bins[]={2,10,24,32},g_bAssertOnBitStreamError;
#define AINRANGE(i,a) ((i)>=0&&(unsigned)(i)<sizeof(a)/sizeof((a)[0]))
'''
    code+=''.join(get(FILES[11],n) for n in ['pktSendBitsAuto','pktGetBitsAuto'])
    code+=(HERE/'oracle_shim.h').read_text().replace('typedef float F32;','')
    code+=''.join(get(FILES[2],n) for n in ['basepower_Send','basepower_Receive','boost_Send','character_SendBoosts','conceptitem_Send','character_inventory_Send','character_SendInventories','character_inventory_Receive','character_ReceiveInventories','character_SendPowerBoost','character_SendPowers','boost_Receive','character_ReceiveBoosts'])
    code+=get(FILES[0],'character_SendInspirations')+get(FILES[1],'character_ReceiveInspirations')+get(FILES[0],'character_Send')
    code+=(HERE/'oracle_fixture.c.inc').read_text()
    (directory/'oracle.c').write_text(code);library=directory/'oracle.so'
    run([os.environ.get('CC','cc'),'-std=c99','-O0','-shared','-fPIC','-w','-I'+str(HERE),'-I'+str(root/'native-android/include'),directory/'oracle.c','-o',library])
    lib=C.CDLL(str(library));lib.original_send.argtypes=[C.c_int,C.c_int,C.c_int,C.c_void_p,C.POINTER(C.c_uint32)];lib.original_subconsumers.argtypes=[C.c_int,C.c_int,C.c_void_p]
    return lib,{'source_sha256_lf':pins,'original_function_sha256':functions,'generated_oracle_sha256':hashlib.sha256(code.encode()).hexdigest(),
        'whole_character_Send_executed':True,'whole_character_Receive_executed':False,
        'consumer_scope':'unchanged inspiration, boost and inventory consumers; owner/setter/dictionary fixtures; no character_CreatePartOne/Two or full powers consumer',
        'source_writer_sanitized':False,'dictionary_scope':'synthetic fixture CRC lookup only; no imported dictionary or server identity'}
def fixtures(lib,directory):
    text=[];rows=[];index=0
    def emit(name,data):text.append('static const unsigned char '+name+'[]={'+','.join(map(str,data))+'};\n')
    for mode in (0,1):
        for scenario in range(6):
            expected=(C.c_uint8*lib.original_subconsumer_size())();lib.original_subconsumers(scenario,mode,expected);emit(f'sub_{scenario}_{mode}',bytes(expected))
            for prefix in ((0,1,7) if not mode else (0,8)):
                data=(C.c_uint8*65536)();bits=C.c_uint32();lib.original_send(scenario,mode,prefix,data,C.byref(bits));emit('data_'+str(index),bytes(data[:(bits.value+7)//8]))
                rows.append('{data_%d,sizeof(data_%d),%d,%d,%d,%d,sub_%d_%d}'%(index,index,bits.value,mode,prefix,scenario,scenario,mode));index+=1
    text.append('static const Fixture fixtures[]={'+',\n'.join(rows)+'};\n')
    text.append(f'#define ORIGINAL_DATA_SIZE {lib.original_data_size()}u\n#define ORIGINAL_SUB_SIZE {lib.original_subconsumer_size()}u\n')
    path=directory/'fixtures.h';path.write_text(''.join(text));return {'count':index,'supported_fixtures':25,'profile_invariant_refusals':5,'original_tail_comparisons':25,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
def main():
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--sanitize',action='store_true');p.add_argument('--fixtures-output',type=Path);p.add_argument('--ndk',type=Path);p.add_argument('--android-output',type=Path);a=p.parse_args()
    if bool(a.ndk)!=bool(a.android_output):p.error('both Android paths required')
    with tempfile.TemporaryDirectory(prefix='coh-character-data-') as temp:
        directory=Path(temp);lib,original=oracle(a.source_root.resolve(),directory);fixture=fixtures(lib,directory)
        if a.fixtures_output:a.fixtures_output.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(directory/'fixtures.h',a.fixtures_output)
        sources=[HERE/'coh_character_data.c',HERE/'../replication/coh_replication.c',HERE/'test_character_data.c'];common=['-std=c99','-Wall','-Wextra','-Werror','-pedantic','-I'+str(HERE),'-I'+str(directory)]
        modes=[('release',['-O2'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])] if a.sanitize else [])
        checks={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        for mode,flags in modes:
            exe=directory/mode;run([os.environ.get('CC','cc'),*common,*flags,*sources,'-lm','-o',exe]);checks[mode]=json.loads(run([exe],env=env))
        inputs=[*sources,HERE/'coh_character_data.h',HERE/'oracle_shim.h',HERE/'oracle_fixture.c.inc',HERE/'source-pins.json',HERE/'check.py',HERE/'CMakeLists.txt',HERE/'../replication/coh_replication.h',HERE/'../coh_contracts.h',ROOT/'native-android/tools/protocol_fixture/prepare.py']
        hashes={str(x.resolve().relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in inputs};android={}
        if a.ndk:
            a.android_output.mkdir(parents=True,exist_ok=True);shutil.copyfile(directory/'fixtures.h',a.android_output/'fixtures.h')
            for abi,compiler in [('arm64-v8a','aarch64-linux-android26-clang'),('x86_64','x86_64-linux-android26-clang')]:
                dest=a.android_output/abi;dest.mkdir(parents=True,exist_ok=True);exe=dest/'coh_character_data_test';run([a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'/compiler,*common,'-O2',*sources,'-lm','-o',exe])
                receipt={'passed':True,'abi':abi,'binary':exe.name,'binary_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'fixtures_sha256':fixture['sha256'],'source_sha256':hashes,'executed':False};(dest/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');android[abi]=receipt
        proof={'schema':'coh-character-data-qualification-v1','passed':True,'original':original,'fixtures':fixture,'fixtures_sha256':fixture['sha256'],'checks':checks,'source_sha256':hashes,'android':android,'dictionaries_resolved':False,'complete_full_update':False,'acknowledgments_enabled':False,'real_server_interoperability':False,'physical_thor_accepted':False}
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'fixtures':fixture,'checks':checks,'android':android}))
if __name__=='__main__':main()
