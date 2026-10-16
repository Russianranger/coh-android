#!/usr/bin/env python3
"""Run exact original create/quaternion producers and consumer, then native tests.
The historical writer executes only trusted padded input at -O0; sanitizers
cover new code and test harness. No source fixture is evidence of live traffic.
"""
from pathlib import Path
import argparse, ctypes as C, hashlib, importlib.util, json, os, re, shutil, struct, subprocess, tempfile
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
FILES=['MapServer/src/entity/entsend.c','Game/src/entity/entrecv.c',
       'Common/entity/entity_enum.h','Common/entity/entVarUpdate.h','Common/entity/entity.h','Common/entity/ragdoll.h',
       'libs/UtilitiesLib/src/components/BitStream.c','libs/UtilitiesLib/src/network/netcomp.c',
       'libs/UtilitiesLib/src/network/net_packetutil.c','libs/UtilitiesLib/src/utils/Quat.c',
       'libs/UtilitiesLib/include/utilitieslib/utils/mathutil.h','Common/entity/gametypes.h','MapServer/src/entity/entserver.c','MapServer/src/entity/entsend.h']
def run(cmd,**kw):
    p=subprocess.run([str(c) for c in cmd],text=True,capture_output=True,**kw)
    if p.returncode:raise RuntimeError(repr(cmd)+'\n'+p.stdout+p.stderr)
    return p

def extract(text,name):
    m=re.search(r'^(?:static\s+)?(?:unsigned\s+int|void|int|U32|F32)\s+(?:INLINEDBG\s+)?'+name+r'\s*\([^;{}]*\)\s*\{',text,re.M)
    if not m:raise ValueError('Missing original function '+name)
    start=text.index('{',m.start());at=start+1;depth=1
    while depth:
        depth+=(text[at]=='{')-(text[at]=='}');at+=1
    return text[m.start():at]+'\n'

def oracle(repo,directory):
    spec=importlib.util.spec_from_file_location('source_bit_adapter',repo/'native-android/tools/protocol_fixture/prepare.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    source={f:(repo/'upstream/ouroboros'/f).read_text().replace('\r\n','\n') for f in FILES}
    pins={f:hashlib.sha256(s.encode()).hexdigest() for f,s in source.items()}
    if pins!=json.loads((HERE/'source-pins.json').read_text())['sha256_lf']:raise ValueError('Entity source pin mismatch')
    pre=helper.PREAMBLE.replace('hasDebugInfo,compress,ordered,ordered_id;', 'hasDebugInfo,compress,ordered,ordered_id,id;')
    pre=re.sub(r'static void pktSendBitsAuto\([^\n]+\n','',pre)
    bit=source[FILES[6]];util=source[FILES[8]];send=source[FILES[0]];recv=source[FILES[1]]
    names=[]
    def get(text,name):names.append(name);return extract(text,name)
    code=pre+'\n'+''.join(get(bit,n) for n in ['initBitStream','bsWriteBits','bsWriteBitsPack','bsReadBits','bsAlignByte','bsGetCursorBitPosition','bsWriteString'])
    code+='''
static void pktSendBits(Packet *p,int n,U32 v){bsWriteBits(&p->stream,n,v);}
static void pktSendBitsPack(Packet *p,int n,U32 v){bsWriteBitsPack(&p->stream,n,v);}
static U32 pktGetBits(Packet *p,int n){return bsReadBits(&p->stream,n);}
static void pktSendString(Packet *p,const char *s){bsWriteString(&p->stream,s?s:"");}
static int auto_bins[]={2,10,24,32};
'''
    code+=''.join(get(util,n) for n in ['pktSendIfSetBitsPack','pktSendIfSetBits','pktGetIfSetBits','pktSendIfSetString','pktSendBitsAuto'])
    code+=(HERE/'oracle_shim.h').read_text()
    code+=''.join(get(send,n) for n in ['entSendPetInfo','entSendCreate','entSendPosUpdate','entSendQrotUpdate','entSendModes','entSendSeqTriggeredMoves','entSendAiAnimList','entSendDeletes'])
    code+=get(source[FILES[7]],'unpackQuatElem')
    code+=''.join(get(source[FILES[9]],n) for n in ['quatCalcWFromXYZ','quatNormalize'])
    code+=get(recv,'entGetOrientation')
    code+='''
void original_fields(const int *widths,const U32 *values,U32 count,int aligned,U8 *out,U32 *length){
 U32 storage[8192]={0};BitStream s;initBitStream(&s,(U8*)storage,sizeof(storage),Write,aligned,0);
 for(U32 i=0;i<count;i++){if(widths[i]<0)bsWriteBitsPack(&s,-widths[i],values[i]);else bsWriteBits(&s,widths[i],values[i]);}
 *length=s.bitLength;memcpy(out,storage,(*length+7)/8);
}
void original_create(int scenario,int aligned,U8 *out,U32 *length){
 U32 storage[8192]={0};Packet p={0};Entity e={0},owner={0},creator={0};
 Character ch={3,1,1,NULL};Player pl={0};Villain v={"fixture.def","FixtureCritter","FixtureOverride"};
 PNPCDef pn={"FixturePNPC"};PNPCInfo pi={&pn,1025};
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);
 e.type=scenario==0||scenario==1||scenario>=6?2:(scenario==2||scenario==3||scenario==4?4:1);
 e.id=scenario==6?70001:91;e.db_id=scenario==6?4243:4242;e.access_level=0;e.name="FixtureName";e.randSeed=0x12345678;e.fade=1;
 e.pchar=&ch;e.pl=e.type==2?&pl:NULL;
 pl.titleThe=3;pl.titleTheText="The";pl.titleCommon="Brave";pl.titleOrigin="Natural";
 pl.titleColors[0]=0x10203040;pl.titleColors[1]=0x50607080;pl.titleBadge=77;
 pl.titleSpecial="Synthetic";pl.chat_handle="Fixture";pl.playerSubType=2;pl.praetorianProgress=3;
 if(scenario==1)pl.isBeingCritter=1;
 if(scenario==2||scenario==3||scenario==4){e.villainDef=&v;e.villainRank=3;e.idDetail=7;e.favoriteWeaponAnimList="FixtureAnim";server_state.clickToSource=1;}
 if(scenario==3||scenario==4){owner.owner=12;creator.owner=13;e.erOwner=&owner;e.erCreator=&creator;e.commandablePet=1;e.petDismissable=1;e.petName="FixturePet";e.specialPowerDisplayName="FixturePower";e.specialPowerState=4;}
 if(scenario==4)ch.ppowCreatedMe=(void*)1;
 if(scenario==5){e.persistentNPCInfo=&pi;e.name=NULL;}
 pktSendBits(&p,1,1);entSendCreate(&p,&e,scenario==0||scenario==1?&e:NULL,1);
 *length=p.stream.bitLength;memcpy(out,storage,(*length+7)/8);
}
void original_record(int medium,int aligned,U8 *out,U32 *length){
 U32 storage[8192]={0};Packet p={0};Entity e={0};
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);
 e.type=1;e.id=91;e.name="FixtureNPC";e.randSeed=123;
 e.net_ipos[0]=(1<<23)+800;e.net_ipos[1]=(1<<23)-400;e.net_ipos[2]=(1<<23)+8192;
 e.net_iqrot[0]=e.net_iqrot[2]=256;e.net_iqrot[1]=384;e.state.mode=1;
 e.triggered_move_count=1;e.triggered_moves[0]=(TriggeredMove){42,6,1000,0};e.aiAnimList="FixtureAnim";
 pktSendBits(&p,1,1);entSendCreate(&p,&e,NULL,1);
 pktSendBits(&p,1,medium);if(medium){pktSendBits(&p,1,1);pktSendBits(&p,1,0);entSendModes(&p,&e,1);}
 entSendPosUpdate(&p,&e,7,1,0);entSendQrotUpdate(&p,&e,7);
 if(medium){
  pktSendBits(&p,1,1);pktSendIfSetBitsPack(&p,8,33);pktSendIfSetBitsPack(&p,4,4);pktSendIfSetBits(&p,11,3);
  entSendSeqTriggeredMoves(&p,&e);entSendAiAnimList(&p,&e,1);
 }
 pktSendBits(&p,1,0);pktSendBits(&p,1,0);
 if(medium){pktSendIfSetBitsPack(&p,2,0);pktSendIfSetBits(&p,8,20);}
 pktSendIfSetBits(&p,5,medium);if(medium)for(int i=0;i<3;i++)pktSendBits(&p,10,256);
 pktSendBitsAuto(&p,1);pktSendBitsAuto(&p,0);pktSendBitsAuto(&p,0);pktSendBits(&p,1,0);
 *length=p.stream.bitLength;memcpy(out,storage,(*length+7)/8);
}
void original_deletes(int aligned,U8 *out,U32 *length){
 U32 storage[8192]={0},visible[320]={0};Packet p={0};EntNetLink link={0};Entity e={0};
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);
 ent_delete_count=1;ent_deletes[0]=4;ent_delete_ids[0]=91;
 link.sent_ids[0]=(1u<<4)|(1u<<7);e.id=92;entities[7]=&e;entities_max=8;
 entSendDeletes(&p,&link,visible);
 *length=p.stream.bitLength;memcpy(out,storage,(*length+7)/8);
}
void original_orientation(const U32 *values,U32 mask,int aligned,U8 *out,U32 *length){
 U32 storage[8192]={0};Packet p={0};Entity e={0};memcpy(e.net_iqrot,values,12);
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);entSendQrotUpdate(&p,&e,mask);
 *length=p.stream.bitLength;memcpy(out,storage,(*length+7)/8);
}
void original_receive_orientation(const U8 *data,U32 bits,int aligned,U32 id,U32 *ids,float *q){
 U32 storage[8192]={0};Packet p={0};Entity e={0};memcpy(e.pkt_id_qrot,ids,12);memcpy(e.net_qrot,q,16);
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Read,aligned,0);memcpy(storage,data,(bits+7)/8);p.stream.bitLength=bits;p.id=id;
 entGetOrientation(&p,&e);memcpy(ids,e.pkt_id_qrot,12);memcpy(q,e.net_qrot,16);
}
'''
    cfile=directory/'source-oracle.c';cfile.write_text(code);so=directory/'source-oracle.so'
    run([os.environ.get('CC','cc'),'-std=c99','-O0','-shared','-fPIC','-w','-I'+str(repo/'native-android/include'),cfile,'-lm','-o',so])
    lib=C.CDLL(str(so))
    lib.original_fields.argtypes=[C.c_void_p,C.c_void_p,C.c_uint32,C.c_int,C.c_void_p,C.POINTER(C.c_uint32)]
    lib.original_create.argtypes=[C.c_int,C.c_int,C.c_void_p,C.POINTER(C.c_uint32)]
    lib.original_record.argtypes=[C.c_int,C.c_int,C.c_void_p,C.POINTER(C.c_uint32)]
    lib.original_deletes.argtypes=[C.c_int,C.c_void_p,C.POINTER(C.c_uint32)]
    lib.original_orientation.argtypes=[C.c_void_p,C.c_uint32,C.c_int,C.c_void_p,C.POINTER(C.c_uint32)]
    lib.original_receive_orientation.argtypes=[C.c_void_p,C.c_uint32,C.c_int,C.c_uint32,C.c_void_p,C.c_void_p]
    return lib,pins,names

def fixtures(lib,directory):
    content=[];count=0
    def emit(label,data,bits):
        nonlocal count
        content.append('static const unsigned char '+label+'[]={'+','.join(map(str,data))+'};\n#define '+label+'_bits '+str(bits)+'u\n');count+=1
    def fields(seq,mode):
        widths=(C.c_int*len(seq))(*(x[0] for x in seq));vals=(C.c_uint32*len(seq))(*(x[1] for x in seq));out=(C.c_uint8*32768)();bits=C.c_uint32()
        lib.original_fields(widths,vals,len(seq),mode,out,C.byref(bits));return bytes(out[:(bits.value+7)//8]),bits.value
    def u(w,v):return [(w,v)]
    def p(w,v):return [(-w,v)]
    def opt(w,v,packed=False):return u(1,1)+(p(w,v) if packed else u(w,v)) if v else u(1,0)
    def auto(v):
        widths=[2,10,24,32];i=next(i for i,w in enumerate(widths) if v<1<<w);return u(2,i)+u(widths[i],v)
    def string(s):return sum((u(8,v) for v in s.encode()+b'\0'),[])
    for mode in [0,1]:
        for scenario in range(8):
            out=(C.c_uint8*32768)();bits=C.c_uint32();lib.original_create(scenario,mode,out,C.byref(bits))
            emit('create_'+str(scenario)+'_'+str(mode),bytes(out[:(bits.value+7)//8]),bits.value)
        for medium in [0,1]:
            out=(C.c_uint8*32768)();bits=C.c_uint32();lib.original_record(medium,mode,out,C.byref(bits))
            emit(f'source_record_{medium}_{mode}',bytes(out[:(bits.value+7)//8]),bits.value)
        out=(C.c_uint8*32768)();bits=C.c_uint32();lib.original_deletes(mode,out,C.byref(bits))
        emit(f'source_deletes{mode}',bytes(out[:(bits.value+7)//8]),bits.value)
        ids=(C.c_uint32*3)();q=(C.c_float*4)(0,0,0,1)
        for step,(mask,vals,ident) in enumerate([(7,[256,384,256],10),(3,[320,256,256],12),(7,[256,256,384],11),(1,[400,0,0],12),(0,[0,0,0],20)]):
            out=(C.c_uint8*32768)();bits=C.c_uint32();values=(C.c_uint32*3)(*vals)
            lib.original_orientation(values,mask,mode,out,C.byref(bits));data=bytes(out[:(bits.value+7)//8]);label=f'orientation_{step}_{mode}'
            emit(label,data,bits.value);lib.original_receive_orientation(data,bits.value,mode,ident,ids,q)
            content.append('static const float '+label+'_expected[]={'+','.join(float(v).hex()+'f' for v in q)+'};\n')
            content.append('static const unsigned int '+label+'_ids[]={'+','.join(map(str,ids))+'};\n')
        # Complete source-layout per-record fixtures. They intentionally suppress
        # pchar/appearance: do not describe a complete real player full update.
        pos=u(3,7)+u(24,(1<<23)+800)+u(24,(1<<23)-400)+u(24,(1<<23)+8192)
        qrot=opt(3,7)+u(9,256)+u(9,384)+u(9,256)
        vision=auto(1)+auto(0)+auto(0)
        npc=u(1,1)+u(1,0)+p(12,91)+p(2,1)+u(1,0)+u(1,1)+string('FixtureNPC')+u(1,0)+u(1,1)+u(32,123)+u(1,0)*4+auto(0)
        simple=npc+u(1,0)+pos+qrot+u(1,0)*3+vision+u(1,0)
        emit('record_simple'+str(mode),*fields(simple,mode))
        medium=npc+u(1,1)+u(1,1)+u(1,0)+u(1,1)+opt(3,1,True)+pos+qrot+u(1,1)+opt(8,33,True)+opt(4,4,True)+opt(11,3)+p(1,1)+p(10,42)+p(6,6)+opt(16,1000,True)+u(1,1)+u(1,1)+string('FixtureAnim')+u(1,0)*2+opt(2,0,True)+opt(8,20)+opt(5,1)+u(10,256)*3+vision+u(1,0)
        emit('record_medium'+str(mode),*fields(medium,mode))
        update=u(1,0)+u(1,0)+pos+u(1,1)+u(1,1)+qrot+u(1,0)*3+vision+u(1,0)
        emit('record_update'+str(mode),*fields(update,mode))
        unsupported_interp=u(1,0)+u(1,0)+pos+u(1,1)+u(1,0)
        emit('unsupported_interp'+str(mode),*fields(unsupported_interp,mode))
        unsupported_appearance=npc+u(1,1)+u(1,1)+u(1,0)+u(1,0)+pos+qrot+u(1,0)+p(1,0)+u(1,0)+u(1,0)*2+opt(2,1,True)
        emit('unsupported_appearance'+str(mode),*fields(unsupported_appearance,mode))
        unsupported_pchar=npc+u(1,0)+pos+qrot+u(1,1)+u(1,0)*2
        emit('unsupported_pchar'+str(mode),*fields(unsupported_pchar,mode))
        for name,seq in [('delta_indices',p(1,4)+p(1,2)),('delta_overflow',p(1,0xffffffff)),('delta_zero',p(1,0)),('end',u(1,1)+u(1,1)),('update_flag',u(1,0)),('deletes',p(1,2)+p(12,4)+p(12,91)+p(12,7)+p(12,92)),('delete_large_generation',p(1,1)+p(12,4)+p(12,70001)),('delete_zero',p(1,1)+p(12,0)+p(12,91)),('delete_duplicate',p(1,2)+p(12,4)+p(12,91)+p(12,4)+p(12,92)),('delete_limit',p(1,257)),('bad_type',u(1,1)+u(1,0)+p(12,91)+p(2,99)),('bad_id',u(1,1)+u(1,0)+p(12,0)+p(2,1)),('long_name',u(1,1)+u(1,0)+p(12,91)+p(2,1)+u(1,0)+u(1,1)+string('x'*256))]:
            emit(name+str(mode),*fields(seq,mode))
    (directory/'fixtures.h').write_text(''.join(content));return count

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,default=REPO);ap.add_argument('--output',type=Path);ap.add_argument('--sanitize',action='store_true');ap.add_argument('--ndk',type=Path);ap.add_argument('--android-output',type=Path);args=ap.parse_args()
    if bool(args.ndk)!=bool(args.android_output):ap.error('--ndk and --android-output must be supplied together')
    with tempfile.TemporaryDirectory(prefix='coh-entities-') as d:
        directory=Path(d);lib,pins,names=oracle(args.source_root.resolve(),directory);n=fixtures(lib,directory)
        common=['-std=c99','-Wall','-Wextra','-Werror','-pedantic','-I'+str(directory),'-I'+str(HERE)]
        sources=[HERE/'coh_entities.c',HERE/'../replication/coh_replication.c',HERE/'test_entities.c']
        checks={};modes=[('release',['-O2'])]
        if args.sanitize:modes += [('asan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=undefined','-fno-sanitize-recover=all'])]
        for name,flags in modes:
            exe=directory/name;run([os.environ.get('CC','cc'),*common,*flags,*sources,'-lm','-o',exe])
            env=os.environ.copy();env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
            checks[name]=json.loads(run([exe],env=env).stdout)
        fixture_sha=hashlib.sha256((directory/'fixtures.h').read_bytes()).hexdigest()
        source_hashes={str(p.resolve().relative_to(REPO.resolve())):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*sources,HERE/'coh_entities.h',HERE/'check.py',HERE/'oracle_shim.h',HERE/'source-pins.json',HERE/'../replication/coh_replication.h',HERE/'../coh_contracts.h',REPO/'native-android/tools/protocol_fixture/prepare.py']}
        android={}
        if args.ndk:
            args.android_output.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(directory/'fixtures.h',args.android_output/'fixtures.h')
            tc=args.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'
            for abi,target in [('arm64-v8a','aarch64-linux-android26-clang'),('x86_64','x86_64-linux-android26-clang')]:
                dest=args.android_output/abi;dest.mkdir(parents=True,exist_ok=True);exe=dest/'coh_entities_test'
                run([tc/target,*common,'-O2',*sources,'-lm','-o',exe]);sha=hashlib.sha256(exe.read_bytes()).hexdigest()
                receipt={'passed':True,'abi':abi,'binary':exe.name,'binary_sha256':sha,'executed':False,'fixtures_sha256':fixture_sha,'source_sha256':source_hashes}
                (dest/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');android[abi]=receipt
        proof={'schema':1,'passed':True,'scope':'original create/pose/quaternion/modes/trigger/AI/delete functions; bounded independent staged entity records; synthetic fixtures only','source_files':len(pins),'original_functions':names,'fixtures':n,'fixtures_sha256':fixture_sha,'source_sha256':source_hashes,'checks':checks,'android':android,'full_update_tail_supported':False,'real_server_interoperability':False,'renderable_authoritative_actor':False,'emulator_qualified':False,'thor_accepted':False}
        if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(proof,indent=2)+'\n')
        print(json.dumps(proof,indent=2))
if __name__=='__main__':main()
