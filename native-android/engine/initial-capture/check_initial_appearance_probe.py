#!/usr/bin/env python3
"""Bounded first-body appearance scalars from the unchanged original sender."""
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
void appearance_original(unsigned mode,unsigned prefix,const U32*v,U8*out,U32*bits,U32*offsets){
 assert(mode<=1&&prefix<8&&(!mode||!prefix)&&v[0]<=INT32_MAX&&v[2]<=1&&v[3]<=7&&v[4]<=1);
 U32 memory[32768]={0};Packet p={0};Costume c={0};
 c.appearance.entTypeFile="FixtureEntity";c.appearance.costumeFilePrefix="fixtureentity";c.appearance.bodytype=v[0];c.appearance.colorSkin.integer=v[1];c.appearance.convertedScale=v[2];c.appearance.currentSuperColorSet=v[3];fixture_stash.capacity=8;
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);for(unsigned i=0;i<prefix;i++)bsWriteBits(&p.stream,1,i&1);p.stream.byteAlignedMode=mode;p.hasDebugInfo=0;
 bodytype_begin=UINT32_MAX;indexed_depth=observed_step=0;for(unsigned i=0;i<6;i++)appearance_offsets[i]=UINT32_MAX;costume_send(&p,&c,v[4]);assert(!p.stream.errorFlags&&observed_step==6);*bits=p.stream.bitLength;memcpy(offsets,appearance_offsets,sizeof(appearance_offsets));memcpy(out,memory,(*bits+7)/8);
}
'''
def oracle(root,work):
 old=module('accepted_body_provider',HERE/'check_initial_costume_body_probe.py');e=root/'native-android/engine/entities';extract=module('appearance_extract',e/'costume_oracle.py');prepare=module('appearance_bits',root/'native-android/tools/protocol_fixture/prepare.py');pins=json.loads((e/'source-pins.json').read_text())['sha256_lf'];names=['libs/UtilitiesLib/src/components/BitStream.c','libs/UtilitiesLib/src/network/net_packetutil.c','libs/UtilitiesLib/src/utils/mathutil.c','Common/entity/costume.c','Common/entity/costume.h'];texts={n:(root/'upstream/ouroboros'/n).read_text().replace('\r\n','\n')for n in names}
 if any(sha(texts[n].encode())!=pins[n]for n in names):raise ValueError('original appearance source changed')
 shim=old.SHIM.replace('static unsigned bodytype_begin,indexed_depth;','static unsigned bodytype_begin,indexed_depth,appearance_offsets[6],observed_step;')
 shim=shim.replace('static void pktSendBits(Packet*p,int n,U32 v){bsWriteBits(&p->stream,n,v);}','static void pktSendBits(Packet*p,int n,U32 v){if(observed_step>=1&&observed_step<=5){appearance_offsets[observed_step]=bsGetCursorBitPosition(&p->stream);observed_step++;}bsWriteBits(&p->stream,n,v);}')
 shim=shim.replace('bodytype_begin=bsGetCursorBitPosition(&p->stream);bsWriteBitsPack','{bodytype_begin=appearance_offsets[0]=bsGetCursorBitPosition(&p->stream);observed_step=1;}bsWriteBitsPack')
 shim=re.sub(r'static void pktSendF\([^\n]+\n','static int g_bAssertOnBitStreamError=1;\n',shim)
 code=prepare.PREAMBLE+''.join(extract.extract(texts[names[0]],n)for n in('initBitStream','bsWriteBits','bsWriteBitsPack','bsAlignByte','bsGetCursorBitPosition','bsWriteString'))+shim
 functions=[(names[1],'pktSendF'),(names[2],'log2i'),(names[1],'defaultBitsPack'),(names[1],'pktSendIndexedString')];code+=''.join(extract.extract(texts[p],n)for p,n in functions)+old.OBSERVER;functions +=[(names[3],'sendCachedIndexedString'),(names[3],'costume_send')];code+=''.join(extract.extract(texts[p],n)for p,n in functions[-2:])+WRAPPER
 src=work/'appearance-original.c';src.write_text(code);library=work/'original.so';run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(root/'native-android/include'),src,'-o',library]);lib=C.CDLL(str(library));lib.appearance_original.argtypes=[C.c_uint,C.c_uint]+[C.c_void_p]*4
 return lib,old,{'original_source_sha256_lf':{n:pins[n]for n in names},'whole_functions_sha256_lf':{n:sha(extract.extract(texts[p],n).encode())for p,n in functions},'consumer_source_function_sha256_lf':sha(extract.extract(texts[names[3]],'costume_receive').encode()),'generated_oracle_sha256':sha(code.encode()),'shim_sha256':sha(shim.encode()),'observer_sha256':sha(old.OBSERVER.encode()),'wrapper_sha256':sha(WRAPPER.encode()),'fixture_stash_capacity':8,'stash_and_member_subset_are_fixture_adapters':True,'source_bodytype_inputs_limited_to_int_max':True,'catalog_count_supplied':False,'bodytype_catalog_admitted':False,'original_consumer_executed':False,'packet_debug_profile':0,'oracle_sanitized':False}
def retained(root):
 d=HERE/'qualification/initial-costume-body-20261019';host=json.loads((d/'host.json').read_text());header=(d/'jni-fixture.h').read_text();proof=host['source_generated_jni_fixture']
 if sha(header.encode())!=proof['header_sha256']:raise ValueError('accepted body header changed')
 for n,h in host['source_sha256'].items():
  if sha((root/n).read_bytes())!=h:raise ValueError('accepted body source changed: '+n)
 raw=bytes(map(int,re.search(r'coh_costume_body_jni_fixture\[\]=\{([\d,]+)\}',header)[1].split(',')));c={n:int(v)for n,v in re.findall(r'#define COH_COSTUME_BODY_JNI_FIXTURE_(\w+) (\d+)u',header)}
 if sha(raw)!=proof['payload_sha256']or c['PREFIX_END']!=proof['prefix_end_bit']:raise ValueError('accepted body payload/boundary changed')
 return raw,c,{'host_sha256':sha((d/'host.json').read_bytes()),'header_sha256':proof['header_sha256'],'payload_sha256':proof['payload_sha256'],'prefix_bits':c['PREFIX_END'],'source_inputs_verified':len(host['source_sha256']),'old_checker_mains_executed':False,'old_native_suites_executed':False}
def specifications():
 values=[0,1,8,9,62,63,64,4157,4158,4159,16781372,16781373,16781374,0x7fffffff]
 rows=[(v,[0,0xffffffff,0x80000000,0xffeeddcc][i%4],i%2,[0,7,5][i%3],1)for i,v in enumerate(values)]
 return[(1,0xffeeddcc,1,5,1),*rows,(1,0xffeeddcc,1,5,0),(63,0xffffffff,0,7,0)]
def projection(old,mode,start,values):
 seq,_,body=old.projection(mode,start,(1,2),8);w=old.Writer(mode);w.bits=seq[:body];at=[body];w.pack(6,values[0]);at.append(len(w.bits))
 for width,value in zip((32,1,3,1),values[1:]):w.scalar(width,value);at.append(len(w.bits))
 for _ in range(72):w.scalar(32,0)
 if values[4]:
  for _ in range(30):w.scalar(32,0)
 else:
  w.scalar(32,0)
  for _ in range(29):w.scalar(6,31)
 w.scalar(1,1);w.pack(4,0)
 return w.bits,at
def fixtures(lib,old,work,retain,output):
 specs=specifications();rows=[];manifest=[];comparisons=0
 def append(mode,start,scenario,variant=0,prefix=None):
  nonlocal comparisons
  values=specs[scenario];seq,at=projection(old,mode,start,values);raw=(C.c_ubyte*131072)();n=C.c_uint();observed=(C.c_uint*6)();lib.appearance_original(mode,0 if mode else start,(C.c_uint*5)(*values),raw,C.byref(n),observed);delta=start if mode else 0;original=[i&1 for i in range(delta)]+bitlist(raw,0,n.value)
  if seq!=original or at!=[v+delta for v in observed]:raise ValueError('whole original appearance producer differs from independent projection: '+repr((mode,start,scenario)))
  comparisons+=1;begin=at[0];body_end=at[1];stop=at[5];status=2;stage=7 if values[4]else 6;fields=5;validated=int(bool(values[4]));end=stop if validated else 0
  if variant==1:seq=seq[:stop];status=1 if validated else 2
  elif variant in(10,11,12):
   w=old.Writer(mode);value=0x80000000 if variant==10 else 0xffffffff
   if variant==12:
    for width in(6,12,24,32):w.scalar(width,(1<<width)-1)
   else:w.pack(6,value)
   shift=len(w.bits)-(body_end-begin);seq=seq[:begin]+w.bits+seq[body_end:];body_end+=shift;stop+=shift;at=[v if i==0 else v+shift for i,v in enumerate(at)];end=end+shift if end else 0
   if variant==12:body_end=0;stop=begin;status=1;stage=2;fields=validated=end=0
  elif variant in(20,21,22):
   field=variant-20+2;where=at[field];value=8 if variant==21 else 2;seq[where:where+8]=[(value>>i)&1 for i in range(8)];stop=where+8;status=1;stage=variant-20+4;fields=variant-20+2;validated=end=0
  elif variant==30:seq=seq[:body_end];stop=body_end;status=1;stage=3;fields=1;validated=end=0
  if prefix is not None:
   # Match and retain the actual optional-name source prefix, not a fabricated body.
   source_prefix=seq[:begin];accepted_body_begin=retain[1]['BODY_BEGIN']
   if source_prefix!=prefix[accepted_body_begin:]:raise ValueError('source optional-name prefix does not match retained bytes')
   shift=len(prefix)-begin;seq=prefix+seq[begin:];begin+=shift;body_end=body_end+shift if body_end else 0;stop+=shift;end=end+shift if end else 0;at=[v+shift for v in at]
  packed=packbytes(seq);row=(len(packed),len(seq),mode,variant,scenario,begin,stop,status,stage,body_end,fields,validated,end);rows.append((row,packed));manifest.append({'mode':mode,'begin':begin,'scenario':scenario,'variant':variant,'sha256':sha(packed)})
  return row,packed,at
 for mode in(0,1):
  for start in(range(8)if not mode else(0,8)):
   for scenario in range(len(specs)):append(mode,start,scenario)
  for scenario in(0,6,14,15,16):append(mode,0,scenario,1)
  append(mode,0,0,30)
  for variant in(10,11):append(mode,0,0,variant)
  if mode:
   for variant in(20,21,22):append(mode,0,0,variant)
  else:append(mode,0,0,12)
 base,c,_=retain;prefix_bits=c['PREFIX_END']
 row,jni,at=append(0,0,0,prefix=bitlist(base,0,prefix_bits));proof={'payload_bits':row[1],'payload_sha256':sha(jni),'appearance_begin_bit':row[5],'bodytype_end_bit':row[9],'scalars_end_bit':row[6],'accepted_body_prefix_matched':bitlist(jni,0,prefix_bits)==bitlist(base,0,prefix_bits),'values_discarded':True,'bodytype_catalog_admitted':False,'device_packet':False,**{n.lower()+'_bit':v for n,v in c.items()if n!='BITS'}}
 if not proof['accepted_body_prefix_matched']:raise ValueError('accepted body prefix changed')
 if output:
  constants=[('BITS',row[1])]+[(n,v)for n,v in c.items()if n!='BITS']+[('APPEARANCE_BEGIN',row[5]),('SKIN_BEGIN',at[1]),('CONVERTED_BEGIN',at[2]),('SUPERSET_BEGIN',at[3]),('EXTRA_BEGIN',at[4]),('SCALARS_END',row[6])]
  header='/* SOURCE-GENERATED FIXTURE: accepted optional-name prefix and unchanged original costume_send appearance scalars. SG colors and later source-produced suffix remain UNACCEPTED. No dictionary/catalog identity or physical packet. */\nstatic const unsigned char coh_appearance_jni_fixture[]={'+','.join(map(str,jni))+'};\n'+''.join('#define COH_APPEARANCE_JNI_FIXTURE_'+n+' '+str(v)+'u\n'for n,v in constants);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(header);proof['header_sha256']=sha(header.encode())
 path=work/'fixtures.bin'
 with path.open('xb')as f:
  f.write(struct.pack('<I',len(rows)))
  for row,raw in rows:f.write(struct.pack('<13I',*row));f.write(raw)
 return path,{'count':len(rows),'sha256':sha(path.read_bytes()),'whole_original_projection_checks':comparisons,'case_manifest_sha256':sha(json.dumps(manifest,sort_keys=True).encode()),'source_bodytype_values':[v[0]for v in specs],'synthetic_native_bodytype_values':[0x80000000,0xffffffff],'synthetic_pack_overflow_control':True,'packed_offsets':list(range(8)),'compressed_offsets':[0,8],'maximum_scalar_bits':[111,88],'supergroup_colors_consumed':False},proof
def main():
 if not __debug__:raise ValueError('Python assertions required')
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--fixture-output',type=Path);p.add_argument('--sanitize',action='store_true');a=p.parse_args();root=a.source_root.resolve()
 if a.output.exists():raise ValueError('fresh evidence output required')
 retain=retained(root);sources=[HERE/'coh_initial_appearance_probe.c',root/'native-android/engine/replication/coh_replication.c'];inputs=set(sources+[Path(__file__),HERE/'test_initial_appearance_probe.c',HERE/'coh_initial_appearance_probe.h',HERE/'check_initial_costume_body_probe.py',root/'native-android/engine/entities/costume_oracle.py',root/'native-android/engine/entities/source-pins.json',root/'native-android/tools/protocol_fixture/prepare.py',HERE/'qualification/initial-costume-body-20261019/host.json',HERE/'qualification/initial-costume-body-20261019/jni-fixture.h']);inputs.update(root/'upstream/ouroboros'/n for n in('libs/UtilitiesLib/src/components/BitStream.c','libs/UtilitiesLib/src/network/net_packetutil.c','libs/UtilitiesLib/src/utils/mathutil.c','Common/entity/costume.c','Common/entity/costume.h'))
 for s in sources+[HERE/'test_initial_appearance_probe.c']:
  deps=run(['cc','-std=c99','-MM',s]).replace('\\\n',' ').split(':',1)[1];inputs.update(Path(n).resolve()for n in shlex.split(deps))
 frozen={p.resolve():p.read_bytes()for p in inputs}
 def verify():
  if any(p.read_bytes()!=b for p,b in frozen.items()):raise ValueError('source changed during appearance qualification')
 modes=[('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else[]);checks={};binaries={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 with tempfile.TemporaryDirectory(prefix='coh-appearance-')as temp:
  work=Path(temp);lib,old,original=oracle(root,work);verify();wire,fixture,jni=fixtures(lib,old,work,retain,a.fixture_output)
  for mode,flags in modes:
   exe=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,HERE/'test_initial_appearance_probe.c','-o',exe]);checks[mode]=json.loads(run([exe,wire],env=env));binaries[mode]=sha(exe.read_bytes());verify()
  if any(v!=checks['release']for v in checks.values()):raise ValueError('mode results differ')
  stack=[]
  for path in work.glob('*.su'):
   for line in path.read_text().splitlines():
    location,size,bound=line.split('\t')
    if'coh_initial_appearance_probe.c:'in location:stack.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
  if not stack or any(x['bound']not in('static','dynamic,bounded')for x in stack):raise ValueError('unbounded native stack')
 verify();a.output.parent.mkdir(parents=True,exist_ok=True);result={'schema':'coh-initial-appearance-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).strip(),'source_sha256':{str(p.relative_to(root)):sha(b)for p,b in sorted(frozen.items())if'upstream/ouroboros'not in str(p)},'original_scalar_producer':original,'retained_costume_body':retain[2],'fixtures':fixture,'source_generated_jni_fixture':jni,'checks':checks,'binary_sha256':binaries,'native_probe_stack_frames':stack,'source_stable_before_after':True,'scope':'Whole unchanged original costume_send with original cached/indexed-string and pktSendF/bit writers, under explicit member-subset/stash adapters. Only raw five-scalar syntax is accepted; values are discarded, extra0 refuses the initial-self profile, and all SG colors/suffix remain unread. Raw bodytype decoding establishes no catalog identity or complete costume. No original consumer application or server transaction qualified.','old_checker_mains_executed':False,'old_native_suites_executed':False,'physical_device_executed':False,'dictionary_admitted':False,'bodytype_catalog_admitted':False,'supergroup_colors_consumed':False,'complete_costume':False,'source_generation_admitted':False,'complete_initial_character':False,'actor_publication':False,'ack_permitted':False,'world_authority':False};a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'jni':jni}))
if __name__=='__main__':main()
