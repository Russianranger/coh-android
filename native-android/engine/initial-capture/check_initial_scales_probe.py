#!/usr/bin/env python3
"""Initial extra1 scale words from original costume_send, with native finite policy."""
import argparse,ctypes as C,hashlib,importlib.util,json,os,re,shlex,struct,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
PACKET_PATH='libs/UtilitiesLib/src/network/net_packet.c'
PACKET_SHA256_LF='4c970280e323d50e4d2f36882b493a1b640df4b8d9b1192c72598315c8387039'
PACKET_BASELINE_BLOB='fc3c1df99f09fafb79dc1b15c53945853d613c05'
PACKET_PIN_REVISION='df2b23e36f1ae5554499ef2d4e7846096ddb5b04'
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
SCALE_WRAPPER=r'''
static U32 fixture_scale(unsigned pattern,unsigned i){
 static const U32 edges[]={0,0x80000000,1,0x007fffff,0x00800000,0x7f7fffff,0xff7fffff,0x3f800000,0xbf800000,0x40000000,0xc0000000,0x3fa00000,0xbe800000,0x80000001,0x807fffff,0x80800000};
 if(pattern==1)return 0;if(pattern==2)return 0x80000000;if(pattern==3)return 0x7f7fffff;if(pattern==4)return(i&1)?0x80000001:1;if(pattern==5)return fixture_scale(0,29-i);
 return i<16?edges[i]:0x3e000000u|((i*0x10203u)&0x007fffffu);
}
void appearance_original(unsigned mode,unsigned prefix,const U32*v,U8*out,U32*bits,U32*offsets){
 assert(mode<=1&&prefix<8&&(!mode||!prefix)&&v[0]<=INT32_MAX&&v[1]<=5&&v[2]<=30);
 U32 memory[32768]={0};Packet p={0};Costume c={0};
 c.appearance.entTypeFile="FixtureEntity";c.appearance.costumeFilePrefix="fixtureentity";c.appearance.bodytype=v[0];c.appearance.colorSkin.integer=0xffeeddcc;c.appearance.convertedScale=1;c.appearance.currentSuperColorSet=5;fixture_stash.capacity=8;
 SGColorBits*channels[]={c.appearance.superColorsPrimaryU,c.appearance.superColorsSecondaryU,c.appearance.superColorsPrimary2U,c.appearance.superColorsSecondary2U,c.appearance.superColorsTertiaryU,c.appearance.superColorsQuaternaryU};
 for(unsigned slot=0;slot<6;slot++)for(unsigned channel=0;channel<6;channel++){unsigned i=slot*12+channel*2;channels[channel][slot].SGBitSetLow=fixture_color(0,i);channels[channel][slot].SGBitSetHigh=fixture_color(0,i+1);}
 for(unsigned i=0;i<30;i++){U32 value=i==v[2]?v[3]:fixture_scale(v[1],i);memcpy(&c.appearance.fScales[i],&value,4);}
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);for(unsigned i=0;i<prefix;i++)bsWriteBits(&p.stream,1,i&1);p.stream.byteAlignedMode=mode;p.hasDebugInfo=0;
 bodytype_begin=first_scale_begin=last_scale_end=part_flag_begin=UINT32_MAX;indexed_depth=observed_step=scale_count=0;for(unsigned i=0;i<6;i++)appearance_offsets[i]=UINT32_MAX;costume_send(&p,&c,1);assert(!p.stream.errorFlags&&observed_step==6&&scale_count==30&&first_scale_begin==appearance_offsets[5]+72*32&&last_scale_end==part_flag_begin&&part_flag_begin==first_scale_begin+30*32);*bits=p.stream.bitLength;offsets[0]=first_scale_begin;offsets[1]=last_scale_end;offsets[2]=part_flag_begin;memcpy(out,memory,(*bits+7)/8);
}
'''
def oracle(root,work):
 provider=module('accepted_appearance_source_provider',HERE/'check_initial_appearance_probe.py');sg=module('accepted_sg_source_provider',HERE/'check_initial_sgcolors_probe.py');loader=provider.module;extract=module('scale_source_extract',root/'native-android/engine/entities/costume_oracle.py');f32=extract.extract((root/'upstream/ouroboros/libs/UtilitiesLib/src/components/BitStream.c').read_text().replace('\r\n','\n'),'bsWriteF32')
 packet=(root/'upstream/ouroboros'/PACKET_PATH).read_bytes().replace(b'\r\n',b'\n')
 if sha(packet)!=PACKET_SHA256_LF or run(['git','-C',root,'rev-parse','HEAD:upstream/ouroboros/'+PACKET_PATH]).strip()!=PACKET_BASELINE_BLOB:raise ValueError('new original packet source pin changed')
 packet_f32=extract.extract(packet.decode(),'pktSendF32')
 def observed_provider(n,p):
  m=loader(n,p)
  if p.name=='check_initial_costume_body_probe.py':
   before='static void pktSendF32(Packet*p,F32 v){U32 bits;memcpy(&bits,&v,4);pktSendBits(p,32,bits);}'
   after='static void observed_pktSendF32(Packet*p,F32 v){if(!scale_count)first_scale_begin=bsGetCursorBitPosition(&p->stream);pktSendF32(p,v);scale_count++;if(scale_count==30)last_scale_end=bsGetCursorBitPosition(&p->stream);}\n#define pktSendF32 observed_pktSendF32'
   write='static void pktSendBits(Packet*p,int n,U32 v){bsWriteBits(&p->stream,n,v);}'
   observe='static void pktSendBits(Packet*p,int n,U32 v){if(observed_step>=1&&observed_step<=5){appearance_offsets[observed_step]=bsGetCursorBitPosition(&p->stream);observed_step++;}if(scale_count==30&&part_flag_begin==UINT32_MAX)part_flag_begin=bsGetCursorBitPosition(&p->stream);bsWriteBits(&p->stream,n,v);}'
   if before not in m.SHIM or write not in m.SHIM:raise ValueError('accepted source-only adapters changed')
   m.SHIM='/* Debug profile is explicitly excluded; trap if reached. */\nstatic void bsTypedWriteF32(BitStream*b,float f){(void)b;(void)f;assert(0);}\n'+f32+packet_f32+'static U32 first_scale_begin,last_scale_end,part_flag_begin;static unsigned scale_count;\n'+m.SHIM.replace(before,after).replace(write,observe)
  return m
 provider.module=observed_provider;provider.WRAPPER=sg.WRAPPER[:sg.WRAPPER.index('void appearance_original')]+SCALE_WRAPPER
 lib,old,proof=provider.oracle(root,work)
 header=(root/'upstream/ouroboros/Common/entity/costume.h').read_text();enum=header[header.index('kBodyScale_Global'):header.index('MAX_BODY_SCALES')]
 if len(re.findall(r'kBodyScale_\w+',enum))!=30:raise ValueError('original scale count changed')
 finite=root/'native-android/engine/entities/coh_costume.c';text=finite.read_text();extract=module('scale_policy_extract',root/'native-android/engine/entities/costume_oracle.py')
 if 'need(p,isfinite(f),COH_INVALID)'not in text:raise ValueError('accepted native finite policy changed')
 proof['whole_functions_sha256_lf'].update({'bsWriteF32':sha(f32.encode()),'pktSendF32':sha(packet_f32.encode())});proof['original_source_sha256_lf'][PACKET_PATH]=PACKET_SHA256_LF;proof.update({'new_packet_source_pin':{'path':'upstream/ouroboros/'+PACKET_PATH,'baseline_revision':PACKET_PIN_REVISION,'baseline_blob_sha1':PACKET_BASELINE_BLOB,'sha256_lf':PACKET_SHA256_LF,'accepted_manifest_modified':False},'source_scale_count':30,'first_scale_and_part_flag_callsites_observed':True,'source_provider_functions_only':True,'packet_f32_profile':'Unchanged whole pktSendF32 and bsWriteF32 execute with hasDebugInfo0/printPacketSendData0; unexecuted typed/debug branch traps. Original alias idiom runs unsanitized O0.','native_finite_policy_source_sha256':sha(finite.read_bytes()),'native_finite_policy_function_sha256':sha(extract.extract(text,'float32').encode()),'nonfinite_refusal_is_native_policy':True,'signaling_nan_controls_are_synthetic_wire':True})
 return lib,provider,old,sg,proof
def retained(root):
 d=HERE/'qualification/initial-sgcolors-20261019';host=json.loads((d/'host.json').read_text());header=(d/'jni-fixture.h').read_text();proof=host['source_generated_jni_fixture']
 if sha(header.encode())!=proof['header_sha256']:raise ValueError('accepted SG header changed')
 for n,h in host['source_sha256'].items():
  if sha((root/n).read_bytes())!=h:raise ValueError('accepted SG source changed: '+n)
 raw=bytes(map(int,re.search(r'coh_sgcolors_jni_fixture\[\]=\{([\d,]+)\}',header)[1].split(',')));c={n:int(v)for n,v in re.findall(r'#define COH_SGCOLORS_JNI_FIXTURE_(\w+) (\d+)u',header)}
 if sha(raw)!=proof['payload_sha256']or c['SGCOLORS_END']!=proof['sgcolors_end_bit']:raise ValueError('accepted SG payload/boundary changed')
 return raw,c,{'host_sha256':sha((d/'host.json').read_bytes()),'header_sha256':proof['header_sha256'],'payload_sha256':proof['payload_sha256'],'prefix_bits':c['SGCOLORS_END'],'source_inputs_verified':len(host['source_sha256']),'old_checker_mains_executed':False,'old_native_suites_executed':False}
def scale(pattern,i):
 if pattern==1:return 0
 if pattern==2:return 0x80000000
 if pattern==3:return 0x7f7fffff
 if pattern==4:return 0x80000001 if i&1 else 1
 if pattern==5:return scale(0,29-i)
 return[0,0x80000000,1,0x007fffff,0x00800000,0x7f7fffff,0xff7fffff,0x3f800000,0xbf800000,0x40000000,0xc0000000,0x3fa00000,0xbe800000,0x80000001,0x807fffff,0x80800000][i]if i<16 else 0x3e000000|((i*0x10203)&0x007fffff)
def specifications():return[(1,i,30,0)for i in range(6)]+[(63,0,30,0),(4158,0,30,0),(16781373,0,30,0)]+[(1,0,i,v)for i in(0,14,29)for v in(0x7f800000,0xff800000,0x7fc01234,0xffc01234)]
def projection(provider,old,sg,mode,start,scenario):
 bodytype,pattern,bad,value=scenario;seq,_,begin,_=sg.projection(provider,old,mode,start,(bodytype,0));w=old.Writer(mode);w.bits=seq[:begin]
 for i in range(30):w.scalar(32,value if i==bad else scale(pattern,i))
 end=len(w.bits);w.bits+=seq[end:];pack_width=32 if mode else 6 if bodytype<63 else 18 if bodytype<4158 else 42 if bodytype<16781373 else 74
 return w.bits,begin,end,pack_width
def fixtures(lib,provider,old,sg,work,retain,output):
 if len({scale(0,i)for i in range(30)})!=30 or any((scale(0,i)&0x7f800000)==0x7f800000 for i in range(30)):raise ValueError('normal scale pattern must be distinct and finite')
 specs=specifications();rows=[];manifest=[];comparisons=0
 def append(mode,start,scenario,variant=0,prefix=None):
  nonlocal comparisons
  values=specs[scenario];seq,begin,end,pack_width=projection(provider,old,sg,mode,start,values);raw=(C.c_ubyte*131072)();n=C.c_uint();observed=(C.c_uint*3)();lib.appearance_original(mode,0 if mode else start,(C.c_uint*4)(*values),raw,C.byref(n),observed);delta=start if mode else 0;original=[i&1 for i in range(delta)]+bitlist(raw,0,n.value)
  if seq!=original or(begin,end,end)!=tuple(v+delta for v in observed):raise ValueError('whole original F32 order/bits or part-flag callsite differs: '+repr((mode,start,scenario)))
  comparisons+=1;bad=values[2]
  if variant in(10,11):
   bad=0 if variant==10 else 29;bits=0x7f801234 if variant==10 else 0xff801234;where=begin+bad*32;seq[where:where+32]=[(bits>>i)&1 for i in range(32)]
  finite=bad if bad<30 else 30;nonfinite=int(bad<30);validated=1-nonfinite;status=1 if nonfinite else 2;stage=3 if nonfinite else 4;stop=begin+(finite+nonfinite)*32;validated_end=end if validated else 0
  if variant==1:seq=seq[:stop];status=1
  if prefix is not None:
   if seq[:begin]!=prefix[retain[1]['BODY_BEGIN']:]:raise ValueError('whole original pre-scale prefix differs from accepted bytes')
   shift=len(prefix)-begin;seq=prefix+seq[begin:];begin+=shift;stop+=shift;end+=shift;validated_end=validated_end+shift if validated_end else 0
  packed=packbytes(seq);row=(len(packed),len(seq),mode,variant,scenario,begin,stop,status,stage,finite,nonfinite,validated,validated_end,pack_width);rows.append((row,packed));manifest.append({'mode':mode,'begin':begin,'scenario':scenario,'variant':variant,'sha256':sha(packed)})
  return row,packed,end
 for mode in(0,1):
  for start in(range(8)if not mode else(0,8)):
   for scenario in range(len(specs)):append(mode,start,scenario)
  for scenario in range(len(specs)):append(mode,0,scenario,1)
  for variant in(10,11):append(mode,0,0,variant)
 base,c,_=retain;prefix_bits=c['SGCOLORS_END'];row,jni,end=append(0,0,0,prefix=bitlist(base,0,prefix_bits));proof={'payload_bits':row[1],'payload_sha256':sha(jni),'scales_begin_bit':row[5],'scales_end_bit':row[6],'part_count_begin_bit':end,'accepted_sg_prefix_matched':bitlist(jni,0,prefix_bits)==bitlist(base,0,prefix_bits),'finite_scales':30,'scale_bits':960,'normal_pattern_distinct_words':30,'scale_values_discarded':True,'device_packet':False,**{n.lower()+'_bit':v for n,v in c.items()if n not in('BITS','SCALES_BEGIN')}}
 if not proof['accepted_sg_prefix_matched']:raise ValueError('accepted SG prefix changed')
 if output:
  constants=[('BITS',row[1])]+[(n,v)for n,v in c.items()if n not in('BITS','SCALES_BEGIN')]+[('SCALES_BEGIN',row[5]),('SCALES_END',row[6]),('PART_COUNT_BEGIN',end)]
  header='/* SOURCE-GENERATED FIXTURE: accepted SG prefix and original costume_send30orderedF32words. Finite policy is native; all scale values discarded. Part-count/body suffix UNACCEPTED. No dictionary, gameplay range or physical packet. */\nstatic const unsigned char coh_scales_jni_fixture[]={'+','.join(map(str,jni))+'};\n'+''.join('#define COH_SCALES_JNI_FIXTURE_'+n+' '+str(v)+'u\n'for n,v in constants);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(header);proof['header_sha256']=sha(header.encode())
 path=work/'fixtures.bin'
 with path.open('xb')as f:
  f.write(struct.pack('<I',len(rows)))
  for row,raw in rows:f.write(struct.pack('<14I',*row));f.write(raw)
 return path,{'count':len(rows),'sha256':sha(path.read_bytes()),'whole_original_f32_order_and_callsite_checks':comparisons,'case_manifest_sha256':sha(json.dumps(manifest,sort_keys=True).encode()),'finite_patterns':['distinct-IEEE-edges','positive-zero','negative-zero','maximum-finite','signed-minimum-subnormal','reversed-distinct'],'source_nonfinite_words':[0x7f800000,0xff800000,0x7fc01234,0xffc01234],'source_nonfinite_positions':[0,14,29],'synthetic_signaling_nan_words':[0x7f801234,0xff801234],'packed_offsets':list(range(8)),'compressed_offsets':[0,8],'source_scale_count':30,'part_count_flag_consumed':False},proof
def main():
 if not __debug__:raise ValueError('Python assertions required')
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--fixture-output',type=Path);p.add_argument('--sanitize',action='store_true');a=p.parse_args();root=a.source_root.resolve()
 if a.output.exists():raise ValueError('fresh evidence output required')
 retain=retained(root);sources=[HERE/'coh_initial_scales_probe.c',HERE/'coh_initial_sgcolors_probe.c',HERE/'coh_initial_appearance_probe.c',root/'native-android/engine/replication/coh_replication.c'];inputs=set(sources+[Path(__file__),HERE/'test_initial_scales_probe.c',HERE/'coh_initial_scales_probe.h',HERE/'check_initial_sgcolors_probe.py',HERE/'check_initial_appearance_probe.py',HERE/'check_initial_costume_body_probe.py',root/'native-android/engine/entities/coh_costume.c',root/'native-android/engine/entities/costume_oracle.py',root/'native-android/engine/entities/source-pins.json',root/'native-android/tools/protocol_fixture/prepare.py',HERE/'qualification/initial-sgcolors-20261019/host.json',HERE/'qualification/initial-sgcolors-20261019/jni-fixture.h']);inputs.update(root/'upstream/ouroboros'/n for n in('libs/UtilitiesLib/src/components/BitStream.c',PACKET_PATH,'libs/UtilitiesLib/src/network/net_packetutil.c','libs/UtilitiesLib/src/utils/mathutil.c','Common/entity/costume.c','Common/entity/costume.h'))
 for s in sources+[HERE/'test_initial_scales_probe.c']:
  deps=run(['cc','-std=c99','-MM',s]).replace('\\\n',' ').split(':',1)[1];inputs.update(Path(n).resolve()for n in shlex.split(deps))
 frozen={p.resolve():p.read_bytes()for p in inputs}
 def verify():
  if any(p.read_bytes()!=b for p,b in frozen.items()):raise ValueError('source changed during scale qualification')
 modes=[('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else[]);checks={};binaries={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 with tempfile.TemporaryDirectory(prefix='coh-scales-')as temp:
  work=Path(temp);lib,provider,old,sg,original=oracle(root,work);verify();wire,fixture,jni=fixtures(lib,provider,old,sg,work,retain,a.fixture_output)
  for mode,flags in modes:
   exe=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,HERE/'test_initial_scales_probe.c','-o',exe]);checks[mode]=json.loads(run([exe,wire],env=env));binaries[mode]=sha(exe.read_bytes());verify()
  if any(v!=checks['release']for v in checks.values()):raise ValueError('mode results differ')
  stack=[]
  for path in work.glob('*.su'):
   for line in path.read_text().splitlines():
    location,size,bound=line.split('\t')
    if'coh_initial_scales_probe.c:'in location:stack.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
  if not stack or any(x['bound']not in('static','dynamic,bounded')for x in stack):raise ValueError('unbounded native stack')
 verify();a.output.parent.mkdir(parents=True,exist_ok=True);result={'schema':'coh-initial-scales-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).strip(),'source_sha256':{str(p.relative_to(root)):sha(b)for p,b in sorted(frozen.items())if'upstream/ouroboros'not in str(p)},'original_scale_producer':original,'retained_sgcolors':retain[2],'fixtures':fixture,'source_generated_jni_fixture':jni,'checks':checks,'binary_sha256':binaries,'native_probe_stack_frames':stack,'source_stable_before_after':True,'scope':'Whole unchanged original costume_send, pktSendF32 and bsWriteF32 with source cached/indexed-string/bit writers and explicit member-subset/stash adapters; non-debug profile only. Independent projection checks all30F32bitpatterns and actual part-count callsite. Native finite policy rejects NaN/Inf without FP evaluation, accepts every finite magnitude, and discards values. SignalingNaNs are labelled synthetic wire controls. No part-count flag, parts, dictionary/catalog or complete costume is accepted; no original consumer application or server transaction qualified.','old_checker_mains_executed':False,'old_native_suites_executed':False,'physical_device_executed':False,'dictionary_admitted':False,'scale_values_retained':False,'gameplay_scale_range_admitted':False,'part_count_flag_consumed':False,'complete_costume':False,'source_generation_admitted':False,'complete_initial_character':False,'actor_publication':False,'ack_permitted':False,'world_authority':False};a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'jni':jni}))
if __name__=='__main__':main()
