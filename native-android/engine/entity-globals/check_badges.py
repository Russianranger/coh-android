#!/usr/bin/env python3
"""Whole original badge sender/consumer and monitor grammar qualification."""
import argparse,ctypes as C,hashlib,importlib.util,json,os,re,shutil,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
FILES=['MapServer/src/player/badges_server.c','Game/src/player/badges_client.c',
       'Common/player/badges.c','Common/player/badges.h','MapServer/src/entity/entsend.c',
       'Game/src/entity/entrecv.c','libs/UtilitiesLib/src/components/BitStream.c',
       'libs/UtilitiesLib/src/network/net_packetutil.c']
def sha(data):return hashlib.sha256(data).hexdigest()
def run(command,**kw):
    p=subprocess.run(list(map(str,command)),capture_output=True,text=True,timeout=180,**kw)
    if p.returncode:raise RuntimeError(repr(command)+'\n'+p.stdout+p.stderr)
    return p.stdout
def source(path):
    p=ROOT/'upstream/ouroboros'/path
    data=p.read_bytes() if p.exists() else subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:upstream/ouroboros/'+path])
    return data.decode().replace('\r\n','\n')
def extract(text,name):
    m=re.search(r'^[^\n{};]+?\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',text,re.M)
    if not m:raise ValueError('missing original function '+name)
    at=text.index('{',m.start())+1;depth=1
    while depth:depth+=(text[at]=='{')-(text[at]=='}');at+=1
    return text[m.start():at]+'\n'
def oracle(directory):
    texts={p:source(p) for p in FILES};pins={p:sha(s.encode()) for p,s in texts.items()}
    if pins!=json.loads((HERE/'badge-source-pins.json').read_text())['sha256_lf']:raise ValueError('original source pin mismatch')
    header=texts[FILES[3]]
    for name,count in [('BADGE_ENT_MAX_BADGES',4096),('BADGE_SG_MAX_BADGES',1050),('BADGE_ENT_RECENT_BADGES',50),('MAX_BADGE_MONITOR_ENTRIES',10)]:
        if not re.search(r'#define\s+'+name+r'\s+'+str(count)+r'\b',header):raise ValueError('source extent changed '+name)
    spec=importlib.util.spec_from_file_location('badge_bits',ROOT/'native-android/tools/protocol_fixture/prepare.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    functions={}
    def get(path,name):
        value=extract(texts[path],name);functions[name]=sha(value.encode());return value
    code='#define _POSIX_C_SOURCE 200809L\n'+helper.PREAMBLE
    code+='\n#define THREADSAFE_STATIC static\n#define THREADSAFE_STATIC_MARK(x)\n'
    code+=''.join(get(FILES[6],n) for n in ['initBitStream','bsWriteBits','bsWriteBitsPack','bsReadBits','bsReadBitsPack','bsAlignByte','bsGetCursorBitPosition','bsWriteString','bsReadStringAndLength'])
    code+='''
static void pktSendBits(Packet *p,int n,U32 v){bsWriteBits(&p->stream,n,v);}
static void pktSendBitsPack(Packet *p,int n,U32 v){bsWriteBitsPack(&p->stream,n,v);}
static U32 pktGetBits(Packet *p,int n){return bsReadBits(&p->stream,n);}
static U32 pktGetBitsPack(Packet *p,int n){return bsReadBitsPack(&p->stream,n);}
static void pktSendString(Packet *p,const char *s){bsWriteString(&p->stream,s);}
static char *pktGetString(Packet *p){int length;return bsReadStringAndLength(&p->stream,&length);}
'''
    code+=''.join(get(FILES[7],n) for n in ['pktSendIfSetBitsPack','pktGetIfSetBitsPack','pktSendIfSetBits','pktGetIfSetBits'])
    # Use exact original badge flag/assignment macros, not independent guessed masks.
    code+='\n'.join(line for line in header.splitlines() if line.startswith('#define BADGE_') and any(token in line for token in ['_MASK','_OWNERSHIP','BADGE_IS_','BADGE_SET_','BADGE_CLEAR_','BADGE_COMPLETION(']))+'\n'
    code+=(HERE/'badge_oracle_shim.h').read_text()
    code+=get(FILES[0],'entity_SendBadgeUpdate')+get(FILES[1],'entity_ReceiveBadgeUpdate')
    code+=get(FILES[2],'badgeMonitor_SendInfo')+get(FILES[2],'badgeMonitor_ReceiveInfo')
    code+=(HERE/'badge_oracle_fixture.c.inc').read_text()
    path=directory/'badge-original.c';path.write_text(code);binary=directory/'badge-original.so'
    run([os.environ.get('CC','cc'),'-std=c99','-O0','-fPIC','-shared','-w','-I'+str(ROOT/'native-android/include'),'-I'+str(HERE),path,'-o',binary])
    library=C.CDLL(str(binary));library.badge_original.argtypes=[C.c_uint,C.c_uint,C.c_uint,C.c_void_p,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32),C.c_void_p]
    return library,{'source_sha256_lf':pins,'original_function_sha256_lf':functions,'generated_oracle_sha256':sha(code.encode()),
        'whole_functions_executed':['entity_SendBadgeUpdate','entity_ReceiveBadgeUpdate','badgeMonitor_SendInfo','badgeMonitor_ReceiveInfo'],
        'oracle_sanitized':False,'dictionary_ui_and_owner_shells':'fixed valid badge dictionary; original strings allocated/freed; UI no-op; monitor CheckAndSortInfo raw-entry observer only',
        'consumer_projection':'all numeric state, recent records, raw monitor IDs, non-security FNV filename comparison; source dictionary/text/UI semantics are not qualification claims'}
def fixtures(library,directory):
    size=library.badge_observation_size();lines=[];rows=[];expected={};count=0
    if size!=41612:raise ValueError('unexpected observation size '+str(size))
    def emit(name,data):lines.append('static const unsigned char '+name+'[]={'+','.join(map(str,data))+'};\n')
    for aligned in (0,1):
        for prefix in (range(8) if not aligned else (0,8)):
            for scenario in range(17):
                data=(C.c_uint8*262144)();bits=C.c_uint32();badge_bits=C.c_uint32();observation=(C.c_uint8*size)()
                library.badge_original(scenario,aligned,prefix,data,C.byref(bits),C.byref(badge_bits),observation)
                raw=bytes(observation)
                if scenario not in expected:expected[scenario]=raw;emit('expected_'+str(scenario),raw)
                elif expected[scenario]!=raw:raise ValueError('original layout-dependent output')
                name='packet_'+str(count);emit(name,bytes(data[:(bits.value+7)//8]))
                status='COH_LIMIT' if scenario in (12,14) else 'COH_OK'
                rows.append('{%s,sizeof(%s),%d,%d,%d,%d,%d,%s,expected_%d}'%(name,name,bits.value,badge_bits.value,aligned,prefix,scenario,status,scenario));count+=1
    lines.append('static const BadgeFixture badge_fixtures[]={'+',\n'.join(rows)+'};\n')
    path=directory/'badge_fixtures.h';path.write_text(''.join(lines))
    return {'producer_fixtures':count,'supported_consumer_comparisons':count-20,'admission_refused_source_fixtures':20,'observation_bytes':size,'sha256':sha(path.read_bytes())}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,default=ROOT);ap.add_argument('--sanitize',action='store_true');ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--fixtures-output',type=Path);ap.add_argument('--ndk',type=Path);ap.add_argument('--android-output',type=Path);a=ap.parse_args()
    if a.source_root.resolve()!=ROOT:ap.error('--source-root must identify this driver checkout')
    if bool(a.ndk)!=bool(a.android_output):ap.error('--ndk and --android-output required together')
    revision=run(['git','-C',ROOT,'rev-parse','HEAD']).strip();tree=run(['git','-C',ROOT,'rev-parse','HEAD^{tree}']).strip()
    clean=not run(['git','-C',ROOT,'status','--porcelain']).strip()
    sources=[HERE/'coh_badges.c',HERE/'../replication/coh_replication.c',HERE/'test_badges.c']
    paths=[*sources,HERE/'coh_badges.h',HERE/'badge_observation.h',HERE/'badge_oracle_shim.h',HERE/'badge_oracle_fixture.c.inc',HERE/'badge-source-pins.json',HERE/'check_badges.py',HERE/'../replication/coh_replication.h',HERE/'../coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',ROOT/'native-android/tools/protocol_fixture/prepare.py']
    hashes={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in paths}
    with tempfile.TemporaryDirectory(prefix='coh-badges-') as name:
        directory=Path(name);library,original=oracle(directory);fixture=fixtures(library,directory)
        if a.fixtures_output:a.fixtures_output.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(directory/'badge_fixtures.h',a.fixtures_output)
        common=['-std=c99','-Wall','-Wextra','-Werror','-pedantic','-I'+str(HERE),'-I'+str(directory)]
        modes=[('release',['-O2'])]
        if a.sanitize:modes += [('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
        checks={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        for mode,flags in modes:
            binary=directory/mode;run([os.environ.get('CC','cc'),*common,*flags,*sources,'-lm','-o',binary]);checks[mode]=json.loads(run([binary],env=env))
        if any(v!=checks['release'] for v in checks.values()):raise ValueError('native mode results differ')
        cpp=directory/'abi.cpp';cpp.write_text('#include "coh_badges.h"\nint main(){return coh_global_badges(nullptr,nullptr,nullptr,0,1)==COH_INVALID && coh_global_badge_monitor(nullptr,nullptr)==COH_INVALID?0:1;}\n')
        objects=[]
        for i,p in enumerate(sources[:2]):
            obj=directory/(str(i)+'.o');run([os.environ.get('CC','cc'),*common,'-O2','-c',p,'-o',obj]);objects.append(obj)
        run([os.environ.get('CXX','c++'),'-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-lm','-o',directory/'cpp-abi']);run([directory/'cpp-abi'])
        android={}
        if a.ndk:
            a.android_output.mkdir(parents=True,exist_ok=True);shutil.copy2(directory/'badge_fixtures.h',a.android_output/'badge_fixtures.h')
            for abi,cc in [('arm64-v8a','aarch64-linux-android26-clang'),('x86_64','x86_64-linux-android26-clang')]:
                dest=a.android_output/abi;dest.mkdir(exist_ok=True);binary=dest/'coh_badges_test'
                run([a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'/cc,*common,'-O2',*sources,'-lm','-o',binary])
                receipt={'built':True,'executed':False,'abi':abi,'binary':binary.name,'binary_sha256':sha(binary.read_bytes()),'fixtures_sha256':fixture['sha256'],'source_sha256':hashes}
                (dest/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');android[abi]=receipt
        if hashes!={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in paths}:raise ValueError('native source changed during qualification')
        for path,digest in original['source_sha256_lf'].items():
            if sha(source(path).encode())!=digest:raise ValueError('original source changed during qualification')
        proof={'source_unchanged_during_qualification':True,'schema':'coh-badge-wire-qualification-v1','passed':True,'source_revision':revision,'source_tree':tree,'source_worktree_clean':clean,'source_sha256':hashes,'original':original,'fixtures':fixture,'checks':checks,'cpp_link_passed':True,'android':android,'leak_sanitizer_enabled':False,'leak_sanitizer_limitation':'Executor reports LeakSanitizer cannot run under ptrace; fixed caller allocations are explicitly freed.', 'full_update_complete':False,'dictionary_bindings_verified':False,'monitor_sorting_qualified':False,'acknowledgments_enabled':False,'real_server_interoperability':False,'thor_accepted':False}
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n')
        print(json.dumps({'passed':True,'checks':checks,'fixtures':fixture,'android_built':list(android)}))
if __name__=='__main__':main()
