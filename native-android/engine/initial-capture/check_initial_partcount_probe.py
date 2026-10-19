#!/usr/bin/env python3
"""Original costume_send part-count framing; stop before runtime catalogs/parts."""
import argparse,ctypes as C,hashlib,importlib.util,json,os,re,shlex,struct,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=180,**kw)
 if p.returncode:raise RuntimeError(repr(args)+'\n'+p.stdout+p.stderr)
 return p.stdout
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def bitlist(b,a,z):return[(b[i//8]>>(i%8))&1 for i in range(a,z)]
def packbytes(seq):
 b=bytearray((len(seq)+7)//8)
 for i,v in enumerate(seq):b[i//8]|=v<<(i%8)
 return b
WRAPPER=r'''
#undef pktSendIndexedString
void partcount_original(unsigned mode,unsigned prefix,const U32*v,U8*out,U32*bits,U32*offsets){
 assert(mode<=1&&prefix<8&&(!mode||!prefix)&&v[0]<=INT32_MAX&&v[1]<=INT32_MAX&&v[2]<=INT32_MAX);
 /* Static transaction storage avoids indeterminate automatic state on longjmp. */
 static U32 memory[32768];static Packet p;static Costume c;
 memset(memory,0,sizeof(memory));memset(&p,0,sizeof(p));memset(&c,0,sizeof(c));
 c.appearance.entTypeFile="FixtureEntity";c.appearance.costumeFilePrefix="fixtureentity";c.appearance.bodytype=v[2];c.appearance.colorSkin.integer=0xffeeddcc;c.appearance.convertedScale=1;c.appearance.currentSuperColorSet=5;c.appearance.iNumParts=v[0];fixture_bodypart_count=v[1];fixture_stash.capacity=8;
 SGColorBits*channels[]={c.appearance.superColorsPrimaryU,c.appearance.superColorsSecondaryU,c.appearance.superColorsPrimary2U,c.appearance.superColorsSecondary2U,c.appearance.superColorsTertiaryU,c.appearance.superColorsQuaternaryU};
 for(unsigned slot=0;slot<6;slot++)for(unsigned channel=0;channel<6;channel++){unsigned i=slot*12+channel*2;channels[channel][slot].SGBitSetLow=fixture_color(0,i);channels[channel][slot].SGBitSetHigh=fixture_color(0,i+1);}
 for(unsigned i=0;i<30;i++){U32 value=fixture_scale(0,i);memcpy(&c.appearance.fScales[i],&value,4);}
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);for(unsigned i=0;i<prefix;i++)bsWriteBits(&p.stream,1,i&1);p.stream.byteAlignedMode=mode;p.hasDebugInfo=0;
 bodytype_begin=frame_begin=frame_end=count_begin=UINT32_MAX;indexed_depth=scale_count=frame_flag=0;
 /* Explicit observer handoff after real flag/Pack4 write, before any part bit.
  * No original source text is edited and no part/cache body is fabricated. */
 if(!setjmp(frame_handoff)){costume_send(&p,&c,1);assert(0);}
 assert(!p.stream.errorFlags&&scale_count==30&&frame_begin!=UINT32_MAX&&frame_end==bsGetCursorBitPosition(&p.stream));
 *bits=p.stream.bitLength;offsets[0]=frame_begin;offsets[1]=frame_end;offsets[2]=count_begin;offsets[3]=frame_flag;memcpy(out,memory,(*bits+7)/8);
}
'''
def oracle(root,work):
 old=module('partcount_body_provider',HERE/'check_initial_costume_body_probe.py');scales=module('partcount_scale_provider',HERE/'check_initial_scales_probe.py');sg=module('partcount_sg_provider',HERE/'check_initial_sgcolors_probe.py');e=root/'native-android/engine/entities';extract=module('partcount_extract',e/'costume_oracle.py');prepare=module('partcount_bits',root/'native-android/tools/protocol_fixture/prepare.py');pins=json.loads((e/'source-pins.json').read_text())['sha256_lf'];names=['libs/UtilitiesLib/src/components/BitStream.c','libs/UtilitiesLib/src/network/net_packetutil.c','libs/UtilitiesLib/src/utils/mathutil.c','Common/entity/costume.c','Common/entity/costume.h'];texts={n:(root/'upstream/ouroboros'/n).read_text().replace('\r\n','\n')for n in names}
 if any(sha(texts[n].encode())!=pins[n]for n in names):raise ValueError('accepted original source changed')
 packet=(root/'upstream/ouroboros'/scales.PACKET_PATH).read_bytes().replace(b'\r\n',b'\n')
 if sha(packet)!=scales.PACKET_SHA256_LF or run(['git','-C',root,'rev-parse','HEAD:upstream/ouroboros/'+scales.PACKET_PATH]).strip()!=scales.PACKET_BASELINE_BLOB:raise ValueError('original packet source pin changed')
 f32=extract.extract(texts[names[0]],'bsWriteF32');packet_f32=extract.extract(packet.decode(),'pktSendF32');packet_bits=extract.extract(packet.decode(),'pktSendBits');packet_pack=extract.extract(packet.decode(),'pktSendBitsPack')
 shim='#include <setjmp.h>\nstatic jmp_buf frame_handoff;static U32 frame_begin,frame_end,count_begin,frame_flag,scale_count,fixture_bodypart_count;\n'+old.SHIM
 shim=shim.replace('static void pktSendBits(Packet*p,int n,U32 v){bsWriteBits(&p->stream,n,v);}','static void observed_pktSendBits(Packet*p,int n,U32 v){if(scale_count==30){assert(n==1&&frame_begin==UINT32_MAX);frame_begin=bsGetCursorBitPosition(&p->stream);frame_flag=v;pktSendBits(p,n,v);if(!v){frame_end=bsGetCursorBitPosition(&p->stream);longjmp(frame_handoff,1);}return;}pktSendBits(p,n,v);}\n#define pktSendBits observed_pktSendBits')
 shim=shim.replace('static void pktSendBitsPack(Packet*p,int n,U32 v){if(n==6&&!indexed_depth&&bodytype_begin==UINT32_MAX)bodytype_begin=bsGetCursorBitPosition(&p->stream);bsWriteBitsPack(&p->stream,n,v);}','static void observed_pktSendBitsPack(Packet*p,int n,U32 v){if(n==6&&!indexed_depth&&bodytype_begin==UINT32_MAX)bodytype_begin=bsGetCursorBitPosition(&p->stream);if(scale_count==30){assert(n==4&&frame_flag==1);count_begin=bsGetCursorBitPosition(&p->stream);pktSendBitsPack(p,n,v);frame_end=bsGetCursorBitPosition(&p->stream);longjmp(frame_handoff,1);}pktSendBitsPack(p,n,v);}\n#define pktSendBitsPack observed_pktSendBitsPack')
 shim=shim.replace('static void pktSendF32(Packet*p,F32 v){U32 bits;memcpy(&bits,&v,4);pktSendBits(p,32,bits);}','static void observed_pktSendF32(Packet*p,F32 v){pktSendF32(p,v);scale_count++;}\n#define pktSendF32 observed_pktSendF32')
 shim=shim.replace('static int GetBodyPartCount(void){return 4;}','static int GetBodyPartCount(void){return fixture_bodypart_count;}')
 shim=re.sub(r'static void pktSendF\([^\n]+\n','static int g_bAssertOnBitStreamError=1;\n',shim)
 functions=[(names[0],n)for n in('initBitStream','bsWriteBits','bsWriteBitsPack','bsAlignByte','bsGetCursorBitPosition','bsWriteString')]
 # prepare.PREAMBLE already supplies trapping typed Bits/Pack debug adapters.
 debug='static void bsTypedWriteF32(BitStream*b,float f){(void)b;(void)f;assert(0);}\n'
 code=prepare.PREAMBLE+''.join(extract.extract(texts[p],n)for p,n in functions)+debug+f32+packet_f32+packet_bits+packet_pack+shim
 rest=[(names[1],'pktSendF'),(names[2],'log2i'),(names[1],'defaultBitsPack'),(names[1],'pktSendIndexedString')];code+=''.join(extract.extract(texts[p],n)for p,n in rest)+old.OBSERVER
 rest +=[(names[3],'sendCachedIndexedString'),(names[3],'costume_send')];code+=''.join(extract.extract(texts[p],n)for p,n in rest[-2:])+sg.WRAPPER[:sg.WRAPPER.index('void appearance_original')]+scales.SCALE_WRAPPER[:scales.SCALE_WRAPPER.index('void appearance_original')]+WRAPPER
 src=work/'partcount-original.c';src.write_text(code);library=work/'original.so';run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(root/'native-android/include'),src,'-o',library]);lib=C.CDLL(str(library));lib.partcount_original.argtypes=[C.c_uint,C.c_uint]+[C.c_void_p]*4
 original={'original_source_sha256_lf':{**{n:pins[n]for n in names},scales.PACKET_PATH:scales.PACKET_SHA256_LF},'whole_functions_sha256_lf':{**{n:sha(extract.extract(texts[p],n).encode())for p,n in functions+rest},'bsWriteF32':sha(f32.encode()),'pktSendF32':sha(packet_f32.encode()),'pktSendBits':sha(packet_bits.encode()),'pktSendBitsPack':sha(packet_pack.encode())},'packet_source_pin':{'path':'upstream/ouroboros/'+scales.PACKET_PATH,'baseline_revision':scales.PACKET_PIN_REVISION,'baseline_blob_sha1':scales.PACKET_BASELINE_BLOB,'sha256_lf':scales.PACKET_SHA256_LF,'accepted_manifest_modified':False},'consumer_source_function_sha256_lf':sha(extract.extract(texts[names[3]],'costume_receive').encode()),'generated_oracle_sha256':sha(code.encode()),'shim_sha256':sha(shim.encode()),'wrapper_sha256':sha(WRAPPER.encode()),'unchanged_whole_original_functions_extracted':True,'execution_bounded_after_original_framing_call_before_any_part_bit':True,'fixture_GetBodyPartCount_is_not_admitted_catalog':True,'source_counts_limited_to_int_max':True,'original_consumer_executed':False,'packet_debug_profile':0,'oracle_sanitized':False,'packet_writer_profile':'Whole original pktSendBits/pktSendBitsPack/pktSendF32/bsWriteF32; hasDebugInfo0/printPacketSendData0; original alias idiom unsanitized O0. Unexecuted typed branches trap.'}
 return lib,old,scales,sg,original
def retained(root):
 d=HERE/'qualification/initial-scales-20261019';host=json.loads((d/'host.json').read_text());header=(d/'jni-fixture.h').read_text();proof=host['source_generated_jni_fixture']
 if sha(header.encode())!=proof['header_sha256']:raise ValueError('accepted scales header changed')
 for n,h in host['source_sha256'].items():
  if sha((root/n).read_bytes())!=h:raise ValueError('accepted scales source changed: '+n)
 raw=bytes(map(int,re.search(r'coh_scales_jni_fixture\[\]=\{([\d,]+)\}',header)[1].split(',')));c={n:int(v)for n,v in re.findall(r'#define COH_SCALES_JNI_FIXTURE_(\w+) (\d+)u',header)}
 if sha(raw)!=proof['payload_sha256']or c['SCALES_END']!=proof['scales_end_bit']:raise ValueError('accepted scales payload changed')
 return raw,c,{'host_sha256':sha((d/'host.json').read_bytes()),'header_sha256':proof['header_sha256'],'payload_sha256':proof['payload_sha256'],'prefix_bits':c['SCALES_END'],'source_inputs_verified':len(host['source_sha256']),'old_checker_mains_executed':False,'old_native_suites_executed':False}
def specifications():
 counts=[0,1,2,14,15,16,29,30,31,269,270,65804,65805,0x7fffffff]
 return[(v,32,1)for v in counts]+[(v,v,1)for v in(0,4,30,0x7fffffff)]+[(2,32,v)for v in(63,4158,16781373)]
def projection(old,scales,sg,mode,start,values):
 count,default,bodytype=values;seq,_,end,_=scales.projection(module('partcount_projection_appearance',HERE/'check_initial_appearance_probe.py'),old,sg,mode,start,(bodytype,0,30,0));w=old.Writer(mode);w.bits=seq[:end];begin=end;explicit=int(count!=default);w.scalar(1,explicit);count_begin=len(w.bits)if explicit else 0xffffffff
 if explicit:w.pack(4,count)
 return w.bits,begin,len(w.bits),count_begin,explicit
def fixtures(lib,old,scales,sg,work,retain,output):
 specs=specifications();rows=[];manifest=[];comparisons=0
 def append(mode,start,scenario,variant=0,prefix=None):
  nonlocal comparisons
  values=specs[scenario];seq,begin,end,count_begin,explicit=projection(old,scales,sg,mode,start,values);raw=(C.c_ubyte*131072)();n=C.c_uint();observed=(C.c_uint*4)();lib.partcount_original(mode,0 if mode else start,(C.c_uint*3)(*values),raw,C.byref(n),observed);shift=start if mode else 0;actual=[i&1 for i in range(shift)]+bitlist(raw,0,n.value)
  want=(begin,end,count_begin,explicit);got=tuple(v+shift if i<3 and v!=0xffffffff else v for i,v in enumerate(observed))
  if seq!=actual or want!=got:raise ValueError('original framing callsite differs '+repr((mode,start,scenario,want,got)))
  comparisons+=1;kind=0
  if variant==1:seq +=[i&1 for i in range(79)]
  elif variant==2:
   w=old.Writer(mode);w.scalar(1,1);w.pack(4,0xffffffff);seq=seq[:begin]+w.bits;kind=1
  elif variant==3:
   if mode:raise ValueError('Pack overflow is packed-only')
   w=old.Writer(mode);w.scalar(1,1)
   for width in(4,8,16,32):w.scalar(width,(1<<width)-1)
   seq=seq[:begin]+w.bits;kind=2
  elif variant in(4,5):
   if not mode:raise ValueError('malformed Boolean compressed-only')
   seq[begin:begin+8]=[((2 if variant==4 else 255)>>i)&1 for i in range(8)];kind=3
  # Synthetic variants are intentionally distinct from original sender evidence.
  if prefix is not None:
   if seq[:begin]!=prefix[retain[1]['BODY_BEGIN']:]:raise ValueError('accepted scale prefix mismatch')
   shift=len(prefix)-begin;seq=prefix+seq[begin:];begin+=shift
  payload=packbytes(seq);width=32 if mode else 6 if values[2]<63 else 18 if values[2]<4158 else 42 if values[2]<16781373 else 74
  row=(len(payload),len(seq),mode,variant,scenario,begin,width,kind);rows.append((row,payload));manifest.append({'mode':mode,'variant':variant,'scenario':scenario,'kind':kind,'sha256':sha(payload)})
  return row,payload
 for mode in(0,1):
  for start in(range(8)if not mode else(0,8)):
   for scenario in range(len(specs)):append(mode,start,scenario)
  for scenario in(0,2,4,7,8,10,12,14,17):append(mode,0,scenario,1)
  append(mode,0,0,2)
  if mode:
   for variant in(4,5):append(mode,0,0,variant)
  else:
   append(mode,0,0,3)
 base,c,_=retain;row,jni=append(0,0,2,prefix=bitlist(base,0,c['SCALES_END']));frame_end=row[5]+5
 proof={'payload_bits':row[1],'payload_sha256':sha(jni),'partcount_begin_bit':row[5],'partcount_end_bit':frame_end,'explicit_part_count':2,'accepted_scale_prefix_matched':bitlist(jni,0,c['SCALES_END'])==bitlist(base,0,c['SCALES_END']),'catalog_admitted':False,'part_body_bits_consumed':0,'device_packet':False,**{n.lower()+'_bit':v for n,v in c.items()if n not in('BITS','PART_COUNT_BEGIN')}}
 if output:
  constants=[('BITS',row[1])]+[(n,v)for n,v in c.items()if n!='BITS']+[('PARTCOUNT_BEGIN',row[5]),('PARTCOUNT_COUNT_BEGIN',row[5]+1),('PARTCOUNT_END',frame_end)]
  header='/* SOURCE-GENERATED FIXTURE: exact accepted scale prefix; unchanged costume_send flag1/Pack4 count2. Observer handoff after original framing call, BEFORE any part bit. Runtime bodytype/count catalogs UNADMITTED; no default, part body, dictionary generation or physical packet. */\nstatic const unsigned char coh_partcount_jni_fixture[]={'+','.join(map(str,jni))+'};\n'+''.join('#define COH_PARTCOUNT_JNI_FIXTURE_'+n+' '+str(v)+'u\n'for n,v in constants);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(header);proof['header_sha256']=sha(header.encode())
 path=work/'fixtures.bin'
 with path.open('xb')as f:
  f.write(struct.pack('<I',len(rows)))
  for row,raw in rows:f.write(struct.pack('<8I',*row));f.write(raw)
 return path,{'count':len(rows),'sha256':sha(path.read_bytes()),'whole_original_framing_callsite_checks':comparisons,'case_manifest_sha256':sha(json.dumps(manifest,sort_keys=True).encode()),'source_explicit_counts':[v[0]for v in specs[:14]],'fixture_default_counts':[0,4,30,0x7fffffff],'source_pack_widths':[4,12,28,60],'compressed_count_width':32,'synthetic_uint32_count':0xffffffff,'synthetic_arithmetic_overflow':True,'synthetic_compressed_nonboolean_flags':[2,255],'synthetic_unread_tail_bits':79,'packed_offsets':list(range(8)),'compressed_offsets':[0,8],'part_body_bits_consumed':0},proof
def main():
 if not __debug__:raise ValueError('Python assertions required')
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--fixture-output',type=Path);p.add_argument('--sanitize',action='store_true');a=p.parse_args();root=a.source_root.resolve()
 if a.output.exists():raise ValueError('fresh evidence output required')
 retain=retained(root);sources=[HERE/'coh_initial_partcount_probe.c',HERE/'coh_initial_scales_probe.c',HERE/'coh_initial_sgcolors_probe.c',HERE/'coh_initial_appearance_probe.c',root/'native-android/engine/replication/coh_replication.c'];inputs=set(sources+[Path(__file__),HERE/'test_initial_partcount_probe.c',HERE/'coh_initial_partcount_probe.h',HERE/'check_initial_scales_probe.py',HERE/'check_initial_sgcolors_probe.py',HERE/'check_initial_appearance_probe.py',HERE/'check_initial_costume_body_probe.py',root/'native-android/engine/entities/costume_oracle.py',root/'native-android/engine/entities/source-pins.json',root/'native-android/tools/protocol_fixture/prepare.py',HERE/'qualification/initial-scales-20261019/host.json',HERE/'qualification/initial-scales-20261019/jni-fixture.h']);inputs.update(root/'upstream/ouroboros'/n for n in('libs/UtilitiesLib/src/components/BitStream.c','libs/UtilitiesLib/src/network/net_packet.c','libs/UtilitiesLib/src/network/net_packetutil.c','libs/UtilitiesLib/src/utils/mathutil.c','Common/entity/costume.c','Common/entity/costume.h'))
 for s in sources+[HERE/'test_initial_partcount_probe.c']:
  deps=run(['cc','-std=c99','-MM',s]).replace('\\\n',' ').split(':',1)[1];inputs.update(Path(n).resolve()for n in shlex.split(deps))
 frozen={p.resolve():p.read_bytes()for p in inputs}
 def verify():
  if any(p.read_bytes()!=b for p,b in frozen.items()):raise ValueError('source changed during partcount qualification')
 modes=[('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else[]);checks={};binaries={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 with tempfile.TemporaryDirectory(prefix='coh-partcount-')as temp:
  work=Path(temp);lib,old,scales,sg,original=oracle(root,work);verify();wire,fixture,jni=fixtures(lib,old,scales,sg,work,retain,a.fixture_output)
  for mode,flags in modes:
   exe=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,HERE/'test_initial_partcount_probe.c','-o',exe]);checks[mode]=json.loads(run([exe,wire],env=env));binaries[mode]=sha(exe.read_bytes());verify()
  if any(v!=checks['release']for v in checks.values()):raise ValueError('mode results differ')
  stack=[]
  for path in work.glob('*.su'):
   for line in path.read_text().splitlines():
    location,size,bound=line.split('\t')
    if'coh_initial_partcount_probe.c:'in location:stack.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
  if not stack or any(x['bound']not in('static','dynamic,bounded')for x in stack):raise ValueError('unbounded stack')
 verify();a.output.parent.mkdir(parents=True,exist_ok=True);result={'schema':'coh-initial-partcount-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).strip(),'source_sha256':{str(p.relative_to(root)):sha(b)for p,b in sorted(frozen.items())if'upstream/ouroboros'not in str(p)},'original_partcount_producer':original,'retained_scales':retain[2],'fixtures':fixture,'source_generated_jni_fixture':jni,'checks':checks,'binary_sha256':binaries,'native_probe_stack_frames':stack,'source_stable_before_after':True,'scope':'Whole unchanged original costume_send/pktSendF32/bsWriteF32 extracted; execution observer hands off after actual raw1/Pack4 framing call and before any part/cache bit. GetBodyPartCount remains an explicit fixture adapter only. Independent projections compare source-generated counts through INT32_MAX and all packed widths. UINT32_MAX, arithmetic overflow and malformed compressed Boolean controls are labelled synthetic. Existing native cap30 is policy, not original runtime catalog maximum. No original consumer, server transaction, bodytype/count catalog, default count or complete costume acceptance.','old_checker_mains_executed':False,'old_native_suites_executed':False,'physical_device_executed':False,'dictionary_admitted':False,'catalog_admitted':False,'default_count_substituted':False,'part_body_bits_consumed':0,'complete_costume':False,'source_generation_admitted':False,'complete_initial_character':False,'actor_publication':False,'ack_permitted':False,'world_authority':False};a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'jni':jni}))
if __name__=='__main__':main()
