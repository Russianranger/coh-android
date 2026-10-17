#!/usr/bin/env python3
"""Original inventory update and invention producer staging; source consumer mismatch retained."""
from pathlib import Path
import argparse,ctypes as C,hashlib,json,os,re,shutil,sys,tempfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE/'../entities'));import check_teammate_buffs as common
import fixture_builder

def sha(b):return hashlib.sha256(b).hexdigest()
def workshop(q,work):
 sources=['MapServer/src/entity/entsend.c','Game/src/entity/entrecv.c'];texts={p:common.source(p) for p in sources};pins={p:sha(s.encode()) for p,s in texts.items()}
 if pins!=json.loads((HERE/'phase-order-source-pins.json').read_text()):raise ValueError('phase order source changed')
 send=next(line for line in texts[sources[0]].splitlines() if 'pktSendString(pak, player_ent->pl->workshopInteracting)' in line)+'\n'
 receive=next(line for line in texts[sources[1]].splitlines() if 'strncpy( player->pl->workshopInteracting' in line)+'\n'
 for name,text,first,second in [('send',texts[sources[0]],'entity_SendInvUpdate( player_ent, pak );','entity_SendInventionUpdate( player_ent, pak );'),('receive',texts[sources[1]],'entity_ReceiveInvUpdate(player, pak);','entity_ReceiveInventionUpdate(player, pak);')]:
  if text.index(first)>text.index(second) or text.index(second)>text.index(send.strip() if name=='send' else receive.strip()):raise ValueError('phase statement order changed')
 code,_,_=q.generate({p:q.source(p) for p in q.PATHS})
 code+='''
typedef struct{char workshopInteracting[32];}WorkshopPlayer;
typedef struct{WorkshopPlayer*pl;}WorkshopEntity;
static void original_workshop_send(Packet*pak,WorkshopEntity*player_ent){
'''+send+'}\nstatic void original_workshop_receive(Packet*pak,WorkshopEntity*player){\n'+receive+'''}
void workshop_fixture(U32 aligned,U32 prefix,U8*out,U32*bits,U32*end){
 U32 memory[1024]={0};Packet p={0};WorkshopPlayer a={"Workshop_Unknown"},b={{0}};WorkshopEntity source={&a},dest={&b};initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);p.stream.byteAlignedMode=aligned;if(prefix)bsWriteBits(&p.stream,prefix,0);original_workshop_send(&p,&source);*bits=p.stream.bitLength;memcpy(out,memory,(*bits+7)/8);p.stream.mode=Read;p.stream.cursor.byte=prefix/8;p.stream.cursor.bit=prefix%8;original_workshop_receive(&p,&dest);*end=bsGetCursorBitPosition(&p.stream);assert(!strcmp(b.workshopInteracting,a.workshopInteracting));
}
'''
 (work/'workshop.c').write_text(code);common.run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-Wl,-z,defs','-I'+str(ROOT/'native-android/include'),work/'workshop.c','-o',work/'workshop.so']);lib=C.CDLL(str(work/'workshop.so'));lib.workshop_fixture.argtypes=[C.c_uint32,C.c_uint32,C.c_void_p,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32)];lines=[];rows=[]
 for mode in (0,1):
  for prefix in (range(8) if not mode else (0,8)):
   data=(C.c_uint8*4096)();bits=C.c_uint32();end=C.c_uint32();lib.workshop_fixture(mode,prefix,data,C.byref(bits),C.byref(end));assert bits.value==end.value;name='workshop_'+str(len(rows));lines.append('static const uint8_t '+name+'[]='+fixture_builder.bytes_c(data[:(bits.value+7)//8])+';');rows.append('{'+name+',sizeof('+name+'),'+','.join(map(str,[prefix,bits.value,mode]))+'}')
 text='\n'.join(lines)+'\nstatic const WorkshopFixture workshop_fixtures[]={'+',\n'.join(rows)+'};\n';(work/'workshop_fixtures.h').write_text(text)
 return {'source_sha256_lf':pins,'sender_statement_sha256':sha(send.encode()),'receiver_statement_sha256':sha(receive.encode()),'generated_oracle_sha256':sha(code.encode()),'fixtures_sha256':sha(text.encode()),'cases':len(rows),'scope':'Exact workshop source statements and original bitstream functions; synthetic entity storage only. Enclosing whole update not executed.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--oracle-root',type=Path,default=ROOT);ap.add_argument('--sanitize',action='store_true');ap.add_argument('--ndk',type=Path);ap.add_argument('--android-output',type=Path);a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 if bool(a.ndk)!=bool(a.android_output):ap.error('both Android paths required')
 provider=a.oracle_root/'native-android/combined-client/diagnostics/allents-tail-20261017';sys.path.insert(0,str(provider));import update_oracle as update;import active_invention_oracle as active;q=update.q
 ppaths=[provider/n for n in ['update_oracle.py','update-source-pins.json','inventory_oracle.py','active_invention_oracle.py','active-invention-source-pins.json']]+[provider.parent/'character-outer-20261017'/n for n in ['qualify_outer.py','independent.py']]
 provider_hashes={str(p.relative_to(a.oracle_root)):sha(p.read_bytes()) for p in ppaths}
 sources=[HERE/n for n in ['coh_inventory.c','coh_invention.c','coh_inventory_phase.c']]+[HERE/'../replication/coh_replication.c',HERE/'test_inventory.c']
 inputs=sources+[HERE/n for n in ['CONTRACT.md','coh_inventory.h','coh_invention.h','coh_inventory_phase.h','inventory_reader.h','check.py','fixture_builder.py','phase-order-source-pins.json','admission-source-pins.json']]+[HERE/'../replication/coh_replication.h',HERE/'../coh_contracts.h',HERE/'../entities/check_teammate_buffs.py',ROOT/'native-android/tools/protocol_fixture/prepare.py',ROOT/'native-android/include/coh_native_core.h']
 hashes={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in inputs};revision=common.run(['git','-C',ROOT,'rev-parse','HEAD']).strip();admission=json.loads((HERE/'admission-source-pins.json').read_text());admission_text={n:common.source(n) for n in admission}
 if admission!={n:sha(t.encode()) for n,t in admission_text.items()}:raise ValueError('admission source changed')
 for path,name,value in [('Common/entity/Invention.h','INVENTION_SLOTS_MAX_COUNT',10),('Common/entity/Concept.h','CONCEPTITEM_MAX_VARS',4),('Common/entity/boost.h','POWER_VAR_MAX_COUNT',4),('Common/entity/boost.h','POWERUP_COST_SLOTS_MAX_COUNT',10)]:
  if not re.search(r'^#define\s+'+name+r'\s+\(?'+str(value)+r'\)?(?:\s|$)',admission_text[path],re.M):raise ValueError('source dimension changed '+name)
 inventory_proof=update.qualify();invention_proof=active.qualify()
 with tempfile.TemporaryDirectory(prefix='coh-inventory-phase-') as tmp:
  work=Path(tmp);inventory_fixtures=fixture_builder.inventory(inventory_proof);invention_fixtures=fixture_builder.invention(invention_proof);(work/'inventory_fixtures.h').write_text(inventory_fixtures);(work/'invention_fixtures.h').write_text(invention_fixtures);workshop_proof=workshop(q,work);fixture_hashes={'inventory_fixtures.h':sha(inventory_fixtures.encode()),'invention_fixtures.h':sha(invention_fixtures.encode()),'workshop_fixtures.h':workshop_proof['fixtures_sha256']};checks={};binaries={};stack=[];android={}
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])] if a.sanitize else []):
   exe=work/mode;common.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(work),*sources,'-lm','-o',exe]);checks[mode]=json.loads(common.run([exe],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(exe.read_bytes())
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    location,size,bound=line.split('\t');fn=location.rsplit(':',1)[-1];admitted=any(n+':' in location for n in ['coh_inventory.c','coh_invention.c','coh_inventory_phase.c']) or ('coh_replication.c:' in location and fn.split('.')[0] in {'valid','coh_rep_read','coh_rep_pack','coh_rep_string'})
    if admitted:stack.append({'function':fn,'bytes':int(size),'bound':bound})
  if any(row['bound'] not in {'static','dynamic,bounded'} for row in stack) or sum(row['bytes'] for row in stack)>8192:raise ValueError('stack reserve not justified')
  if any(c!=checks['release'] for c in checks.values()):raise ValueError('mode mismatch')
  cpp=work/'link.cpp';cpp.write_text('#include "coh_inventory_phase.h"\nint main(){return coh_inventory_phase_read(nullptr,nullptr,nullptr,0,0)==COH_INVALID?0:1;}\n');objects=[]
  for i,path in enumerate(sources[:-1]):
   obj=work/(str(i)+'.o');common.run(['cc','-std=c99','-O2','-c',path,'-o',obj]);objects.append(obj)
  common.run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-lm','-o',work/'cpp-link']);common.run([work/'cpp-link'])
  if a.ndk:
   a.android_output.mkdir(parents=True,exist_ok=True)
   for name in fixture_hashes:shutil.copy2(work/name,a.android_output/name)
   for abi,cc in [('arm64-v8a','aarch64-linux-android26-clang'),('x86_64','x86_64-linux-android26-clang')]:
    dest=a.android_output/abi;dest.mkdir(exist_ok=True);exe=dest/'coh_inventory_phase_test';common.run([a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'/cc,'-std=c99','-Wall','-Wextra','-Werror','-pedantic','-O2','-I'+str(work),*sources,'-lm','-o',exe]);r={'built':True,'executed':False,'binary':exe.name,'binary_sha256':sha(exe.read_bytes()),'fixtures_sha256':fixture_hashes,'source_sha256':hashes};(dest/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');android[abi]=r
  if hashes!={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in inputs} or provider_hashes!={n:sha((a.oracle_root/n).read_bytes()) for n in provider_hashes} or admission!={n:sha(common.source(n).encode()) for n in admission} or revision!=common.run(['git','-C',ROOT,'rev-parse','HEAD']).strip():raise ValueError('source/provider changed')
  del inventory_proof['cases'];del invention_proof['cases'];result={'schema':'coh-inventory-phase-qualification-v1','passed':True,'source_revision':revision,'source_sha256':hashes,'provider_sha256':provider_hashes,'admission_original_source_sha256_lf':admission,'original_inventory':inventory_proof,'original_invention':invention_proof,'original_workshop':workshop_proof,'fixtures_sha256':fixture_hashes,'source_stable_before_after':True,'checks':checks,'binary_sha256':binaries,'production_stack_frames':stack,'cpp_link_passed':True,'android':android,'auction_text_semantics':False,'active_invention_original_consumer_compatible':False,'whole_initial_update_complete':False,'dictionary_authority':False,'actor_publication':False,'acknowledgments_enabled':False,'android_executed':False}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks}))
if __name__=='__main__':main()
