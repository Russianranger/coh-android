#!/usr/bin/env python3
"""First costume's fixed SG color array against unchanged original source."""
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
static U32 fixture_color(unsigned pattern,unsigned i){
 static const U32 edges[]={0,UINT32_MAX,0x80000000,0x7fffffff,0x01020304,0xffeeddcc};
 if(pattern==1)return 0;if(pattern==2)return UINT32_MAX;if(pattern==3)return~fixture_color(0,i);if(pattern==4)return(U32)1u<<(i%32);if(pattern==5)return fixture_color(0,71-i);
 return i<6?edges[i]:(0x9e3779b9u*(i+1u))^(0x01020304u+i);
}
void appearance_original(unsigned mode,unsigned prefix,const U32*v,U8*out,U32*bits,U32*offsets){
 assert(mode<=1&&prefix<8&&(!mode||!prefix)&&v[0]<=INT32_MAX&&v[1]<=5);
 U32 memory[32768]={0};Packet p={0};Costume c={0};
 c.appearance.entTypeFile="FixtureEntity";c.appearance.costumeFilePrefix="fixtureentity";c.appearance.bodytype=v[0];c.appearance.colorSkin.integer=0xffeeddcc;c.appearance.convertedScale=1;c.appearance.currentSuperColorSet=5;fixture_stash.capacity=8;
 SGColorBits*channels[]={c.appearance.superColorsPrimaryU,c.appearance.superColorsSecondaryU,c.appearance.superColorsPrimary2U,c.appearance.superColorsSecondary2U,c.appearance.superColorsTertiaryU,c.appearance.superColorsQuaternaryU};
 for(unsigned slot=0;slot<6;slot++)for(unsigned channel=0;channel<6;channel++){unsigned i=slot*12+channel*2;channels[channel][slot].SGBitSetLow=fixture_color(v[1],i);channels[channel][slot].SGBitSetHigh=fixture_color(v[1],i+1);}
 for(unsigned i=0;i<30;i++)c.appearance.fScales[i]=i?i*.125f:1.25f;
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);for(unsigned i=0;i<prefix;i++)bsWriteBits(&p.stream,1,i&1);p.stream.byteAlignedMode=mode;p.hasDebugInfo=0;
 bodytype_begin=first_scale_begin=UINT32_MAX;indexed_depth=observed_step=0;for(unsigned i=0;i<6;i++)appearance_offsets[i]=UINT32_MAX;costume_send(&p,&c,1);assert(!p.stream.errorFlags&&observed_step==6&&first_scale_begin==appearance_offsets[5]+72*32);*bits=p.stream.bitLength;offsets[0]=appearance_offsets[5];offsets[1]=first_scale_begin;memcpy(out,memory,(*bits+7)/8);
}
'''
def oracle(root,work):
 provider=module('accepted_appearance_source_provider',HERE/'check_initial_appearance_probe.py');loader=provider.module
 def observed_provider(n,p):
  m=loader(n,p)
  if p.name=='check_initial_costume_body_probe.py':
   before='static void pktSendF32(Packet*p,F32 v){U32 bits;memcpy(&bits,&v,4);pktSendBits(p,32,bits);}'
   after='static U32 first_scale_begin;static void pktSendF32(Packet*p,F32 v){if(first_scale_begin==UINT32_MAX)first_scale_begin=bsGetCursorBitPosition(&p->stream);U32 bits;memcpy(&bits,&v,4);pktSendBits(p,32,bits);}'
   if before not in m.SHIM:raise ValueError('accepted source-only float adapter changed')
   m.SHIM=m.SHIM.replace(before,after)
  return m
 provider.module=observed_provider;provider.WRAPPER=WRAPPER
 lib,old,proof=provider.oracle(root,work)
 header=(root/'upstream/ouroboros/Common/entity/costume.h').read_text()
 if not re.search(r'#define\s+NUM_SG_COLOR_SLOTS\s+\(6\)',header):raise ValueError('source SG slot count changed')
 proof['first_scale_callsite_observed']=True;proof['sg_words']=72;proof['sg_word_bits']=32;proof['source_provider_functions_only']=True
 return lib,provider,old,proof
def retained(root):
 d=HERE/'qualification/initial-appearance-20261019';host=json.loads((d/'host.json').read_text());header=(d/'jni-fixture.h').read_text();proof=host['source_generated_jni_fixture']
 if sha(header.encode())!=proof['header_sha256']:raise ValueError('accepted appearance header changed')
 for n,h in host['source_sha256'].items():
  if sha((root/n).read_bytes())!=h:raise ValueError('accepted appearance source changed: '+n)
 raw=bytes(map(int,re.search(r'coh_appearance_jni_fixture\[\]=\{([\d,]+)\}',header)[1].split(',')));c={n:int(v)for n,v in re.findall(r'#define COH_APPEARANCE_JNI_FIXTURE_(\w+) (\d+)u',header)}
 if sha(raw)!=proof['payload_sha256']or c['SCALARS_END']!=proof['scalars_end_bit']:raise ValueError('accepted appearance payload/boundary changed')
 return raw,c,{'host_sha256':sha((d/'host.json').read_bytes()),'header_sha256':proof['header_sha256'],'payload_sha256':proof['payload_sha256'],'prefix_bits':c['SCALARS_END'],'source_inputs_verified':len(host['source_sha256']),'old_checker_mains_executed':False,'old_native_suites_executed':False}
def color(pattern,i):
 if pattern==1:return 0
 if pattern==2:return 0xffffffff
 if pattern==3:return color(0,i)^0xffffffff
 if pattern==4:return 1<<(i%32)
 if pattern==5:return color(0,71-i)
 return[0,0xffffffff,0x80000000,0x7fffffff,0x01020304,0xffeeddcc][i]if i<6 else((0x9e3779b9*(i+1))^(0x01020304+i))&0xffffffff
def specifications():return[(1,i)for i in range(6)]+[(63,0),(4158,0),(16781373,0)]
def projection(provider,old,mode,start,scenario):
 bodytype,pattern=scenario;seq,at=provider.projection(old,mode,start,(bodytype,0xffeeddcc,1,5,1));begin=at[5];w=old.Writer(mode);w.bits=seq[:begin]
 for i in range(72):w.scalar(32,color(pattern,i))
 end=len(w.bits)
 for i in range(30):w.scalar(32,struct.unpack('<I',struct.pack('<f',i/8 if i else 1.25))[0])
 w.bits+=seq[end+30*32:]
 return w.bits,begin,end,at[1]-at[0]
def fixtures(lib,provider,old,work,retain,output):
 if len({color(0,i)for i in range(72)})!=72:raise ValueError('normal source color pattern must be distinct')
 specs=specifications();rows=[];manifest=[];comparisons=0
 def append(mode,start,scenario,variant=0,prefix=None):
  nonlocal comparisons
  seq,begin,end,pack_width=projection(provider,old,mode,start,specs[scenario]);raw=(C.c_ubyte*131072)();n=C.c_uint();observed=(C.c_uint*2)();lib.appearance_original(mode,0 if mode else start,(C.c_uint*2)(*specs[scenario]),raw,C.byref(n),observed);delta=start if mode else 0;original=[i&1 for i in range(delta)]+bitlist(raw,0,n.value)
  if seq!=original or(begin,end)!=tuple(v+delta for v in observed):raise ValueError('whole original SG array/order or first-scale callsite differs: '+repr((mode,start,scenario)))
  comparisons+=1;status=2
  if variant==1:seq=seq[:end];status=1
  if prefix is not None:
   if seq[:begin]!=prefix[retain[1]['BODY_BEGIN']:]:raise ValueError('whole original pre-SG prefix differs from accepted bytes')
   shift=len(prefix)-begin;seq=prefix+seq[begin:];begin+=shift;end+=shift
  packed=packbytes(seq);row=(len(packed),len(seq),mode,variant,scenario,begin,end,status,3,72,1,end,pack_width);rows.append((row,packed));manifest.append({'mode':mode,'begin':begin,'scenario':scenario,'variant':variant,'sha256':sha(packed)})
  return row,packed
 for mode in(0,1):
  for start in(range(8)if not mode else(0,8)):
   for scenario in range(len(specs)):append(mode,start,scenario)
  for scenario in range(len(specs)):append(mode,0,scenario,1)
 base,c,_=retain;prefix_bits=c['SCALARS_END'];row,jni=append(0,0,0,prefix=bitlist(base,0,prefix_bits));proof={'payload_bits':row[1],'payload_sha256':sha(jni),'sgcolors_begin_bit':row[5],'sgcolors_end_bit':row[6],'scales_begin_bit':row[6],'accepted_appearance_prefix_matched':bitlist(jni,0,prefix_bits)==bitlist(base,0,prefix_bits),'words':72,'array_bits':2304,'normal_pattern_distinct_words':72,'word_values_discarded':True,'first_scale_value_unaccepted':1.25,'device_packet':False,**{n.lower()+'_bit':v for n,v in c.items()if n!='BITS'}}
 if not proof['accepted_appearance_prefix_matched']:raise ValueError('accepted appearance prefix changed')
 if output:
  constants=[('BITS',row[1])]+[(n,v)for n,v in c.items()if n!='BITS']+[('SGCOLORS_BEGIN',row[5]),('SGCOLORS_END',row[6]),('SCALES_BEGIN',row[6])]
  header='/* SOURCE-GENERATED FIXTURE: accepted appearance prefix and original costume_send ordered SG words. Colors are discarded; source-produced scales/parts remain UNACCEPTED. No dictionary, entitlement or physical packet. */\nstatic const unsigned char coh_sgcolors_jni_fixture[]={'+','.join(map(str,jni))+'};\n'+''.join('#define COH_SGCOLORS_JNI_FIXTURE_'+n+' '+str(v)+'u\n'for n,v in constants);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(header);proof['header_sha256']=sha(header.encode())
 path=work/'fixtures.bin'
 with path.open('xb')as f:
  f.write(struct.pack('<I',len(rows)))
  for row,raw in rows:f.write(struct.pack('<13I',*row));f.write(raw)
 return path,{'count':len(rows),'sha256':sha(path.read_bytes()),'whole_original_order_and_callsite_checks':comparisons,'case_manifest_sha256':sha(json.dumps(manifest,sort_keys=True).encode()),'patterns':['distinct-edge-and-mixed','zero','ones','complement','walking-bit','reversed-distinct'],'source_pack6_widths':[6,18,42,74],'packed_offsets':list(range(8)),'compressed_offsets':[0,8],'source_words_per_slot':12,'source_slots':6,'first_scale_consumed':False},proof
def main():
 if not __debug__:raise ValueError('Python assertions required')
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--fixture-output',type=Path);p.add_argument('--sanitize',action='store_true');a=p.parse_args();root=a.source_root.resolve()
 if a.output.exists():raise ValueError('fresh evidence output required')
 retain=retained(root);sources=[HERE/'coh_initial_sgcolors_probe.c',HERE/'coh_initial_appearance_probe.c',root/'native-android/engine/replication/coh_replication.c'];inputs=set(sources+[Path(__file__),HERE/'test_initial_sgcolors_probe.c',HERE/'coh_initial_sgcolors_probe.h',HERE/'check_initial_appearance_probe.py',HERE/'check_initial_costume_body_probe.py',root/'native-android/engine/entities/costume_oracle.py',root/'native-android/engine/entities/source-pins.json',root/'native-android/tools/protocol_fixture/prepare.py',HERE/'qualification/initial-appearance-20261019/host.json',HERE/'qualification/initial-appearance-20261019/jni-fixture.h']);inputs.update(root/'upstream/ouroboros'/n for n in('libs/UtilitiesLib/src/components/BitStream.c','libs/UtilitiesLib/src/network/net_packetutil.c','libs/UtilitiesLib/src/utils/mathutil.c','Common/entity/costume.c','Common/entity/costume.h'))
 for s in sources+[HERE/'test_initial_sgcolors_probe.c']:
  deps=run(['cc','-std=c99','-MM',s]).replace('\\\n',' ').split(':',1)[1];inputs.update(Path(n).resolve()for n in shlex.split(deps))
 frozen={p.resolve():p.read_bytes()for p in inputs}
 def verify():
  if any(p.read_bytes()!=b for p,b in frozen.items()):raise ValueError('source changed during SG array qualification')
 modes=[('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else[]);checks={};binaries={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 with tempfile.TemporaryDirectory(prefix='coh-sgcolors-')as temp:
  work=Path(temp);lib,provider,old,original=oracle(root,work);verify();wire,fixture,jni=fixtures(lib,provider,old,work,retain,a.fixture_output)
  for mode,flags in modes:
   exe=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,HERE/'test_initial_sgcolors_probe.c','-o',exe]);checks[mode]=json.loads(run([exe,wire],env=env));binaries[mode]=sha(exe.read_bytes());verify()
  if any(v!=checks['release']for v in checks.values()):raise ValueError('mode results differ')
  stack=[]
  for path in work.glob('*.su'):
   for line in path.read_text().splitlines():
    location,size,bound=line.split('\t')
    if'coh_initial_sgcolors_probe.c:'in location:stack.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
  if not stack or any(x['bound']not in('static','dynamic,bounded')for x in stack):raise ValueError('unbounded native stack')
 verify();a.output.parent.mkdir(parents=True,exist_ok=True);result={'schema':'coh-initial-sgcolors-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).strip(),'source_sha256':{str(p.relative_to(root)):sha(b)for p,b in sorted(frozen.items())if'upstream/ouroboros'not in str(p)},'original_array_producer':original,'retained_appearance':retain[2],'fixtures':fixture,'source_generated_jni_fixture':jni,'checks':checks,'binary_sha256':binaries,'native_probe_stack_frames':stack,'source_stable_before_after':True,'scope':'Whole unchanged original costume_send with source cached/indexed-string and bit writers, under explicit member-subset/stash adapters. Independent projection checks all6slots*12orderedU32words and observed first-scale callsite. Native only reads/discards the72words, without resource/color/entitlement interpretation; all scales and parts remain unread. No original consumer application or server transaction qualified.','old_checker_mains_executed':False,'old_native_suites_executed':False,'physical_device_executed':False,'dictionary_admitted':False,'color_values_retained':False,'first_scale_consumed':False,'complete_costume':False,'source_generation_admitted':False,'complete_initial_character':False,'actor_publication':False,'ack_permitted':False,'world_authority':False};a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'jni':jni}))
if __name__=='__main__':main()
