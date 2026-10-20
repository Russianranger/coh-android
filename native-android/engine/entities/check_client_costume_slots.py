#!/usr/bin/env python3
"""Exact CLIENT projection -> unchanged original indexed costume sender/receiver."""
import argparse,ctypes as C,gzip,hashlib,importlib.util,json,os,struct,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
RAW_SHA='2e69212432d1b16a38f307aca16ac892cca56cf59128d5d8d25e71386da4af81'
def sha(b):return hashlib.sha256(b).hexdigest()
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
def projection(raw):
 at=0;offsets=[];tables=[]
 def word():
  nonlocal at
  v=struct.unpack_from('<I',raw,at)[0];at+=4;return v
 for capacity,present in [(32768,13209),(256,156),(512,224)]:
  assert (word(),word())==(capacity,present);values=[]
  for i in range(capacity):
   flag=word();assert flag in (0,1);offsets.append(at if flag else 0)
   if not flag:values.append(None);continue
   n=word()
   if capacity==512:values.append(n)
   else:values.append(raw[at:at+n]);at+=n
  assert sum(v is not None for v in values)==present;tables.append(values)
 assert at==len(raw)
 # This index is independent of the C parser. Its bytes also encode every hole.
 return b''.join(struct.pack('<I',v)for v in offsets),tables

def indexed_sender(work,legacy,tables):
 # Existing fixture generator compiles exact whole original functions. Replace
 # only its deterministic table storage adapters and fixture data, never grammar.
 code=(work/'original-sender.c').read_text()
 code=code.replace('strings[16]','strings[32768]').replace('colors[16]','colors[512]').replace('present[16]','present[512]')
 for line in ['#define stashFindIndexByKey(t,s,p) ((void)(t),(void)(s),(void)(p),0)\n','#define stashIntFindIndexByKey(t,v,p) ((void)(t),(void)(v),(void)(p),0)\n']:
  assert line in code;code=code.replace(line,'')
 helper='''
static const char *ordinary_value(unsigned n){for(unsigned i=0;i<strings_table.max_size;i++)if(strings_table.strings[i]&&n--==0)return strings_table.strings[i];assert(0);return NULL;}
static const char *extra_value(unsigned n){for(unsigned i=0;i<extra_table.max_size;i++)if(extra_table.strings[i]&&n--==0)return extra_table.strings[i];assert(0);return NULL;}
static unsigned palette_value(unsigned n){for(unsigned i=0;i<palette_table.max_size;i++)if(palette_table.present[i]&&n--==0)return palette_table.colors[i];assert(0);return 0;}
void load_projection(const U8 *raw){unsigned at=0;Table *tables[3]={&strings_table,&extra_table,&palette_table};for(unsigned t=0;t<3;t++){Table *p=tables[t];memset(p,0,sizeof(*p));p->max_size=(unsigned)raw[at]|(unsigned)raw[at+1]<<8|(unsigned)raw[at+2]<<16|(unsigned)raw[at+3]<<24;at+=8;for(unsigned i=0;i<p->max_size;i++){unsigned present=(unsigned)raw[at];at+=4;if(!present)continue;unsigned value=(unsigned)raw[at]|(unsigned)raw[at+1]<<8|(unsigned)raw[at+2]<<16|(unsigned)raw[at+3]<<24;at+=4;if(t==2){p->colors[i]=value;p->present[i]=1;}else{char *s=malloc(value+1);assert(s);memcpy(s,raw+at,value);s[value]=0;p->strings[i]=s;at+=value;}}}assert(at==641477);}
'''
 code=code.replace('void fixture(',helper+'void fixture(')
 for before,after in [('names?"FixtureEntity":NULL','names?ordinary_value(0):NULL'),('names?"Male":NULL','names?ordinary_value(1):NULL'),('parts[i].pchGeom="FixtureGeometry"','parts[i].pchGeom=ordinary_value(2+i*4)'),('parts[i].pchTex1="InlineTexture"','parts[i].pchTex1=ordinary_value(3+i*4)'),('parts[i].pchTex2="InlineTexture"','parts[i].pchTex2=ordinary_value(4+i*4)'),('i%2?"GlowFX":NULL','i%2?ordinary_value(5+i*4):NULL'),('parts[i].regionName="Upper"','parts[i].regionName=extra_value(i%4)'),('parts[i].bodySetName="BodySet"','parts[i].bodySetName=extra_value(4+i%4)'),('0x12340000+j','palette_value(j)')]:
  assert before in code,before;code=code.replace(before,after)
 source=work/'indexed-original-sender.c';source.write_text(code);lib=work/'indexed-original-sender.so'
 legacy.run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(ROOT/'native-android/include'),'-I'+str(HERE),source,'-lm','-o',lib],work,'indexed-sender-compile')
 dll=C.CDLL(str(lib));raw=gzip.decompress((HERE/'qualification/costume-builder-20261017/offline-primary-slots.bin.gz').read_bytes());buffer=C.create_string_buffer(raw);dll.load_projection.argtypes=[C.c_void_p];dll.load_projection(buffer)
 dll.fixture.argtypes=[C.c_uint]*6+[C.c_void_p,C.c_void_p];scenarios=[]
 for mode in (0,1):
  for start in ((0,3,7)if not mode else(0,)):
   for count in (0,1,4,28):
    for extra in (0,1):
     for names in (0,1):
      b=(C.c_uint8*16384)();bits=C.c_uint32();dll.fixture(mode,start,count,28,extra,names,b,C.byref(bits));scenarios.append((mode,start,28,count,bits.value,bytes(b[:(bits.value+7)//8])))
 out=bytearray(struct.pack('<I',len(scenarios)))
 for mode,start,default,count,bits,b in scenarios:out+=struct.pack('<IIIII',mode,start,default,count,bits)+b
 target=work/'indexed-fixtures.bin';target.write_bytes(out)
 return target,{'scenarios':len(scenarios),'fixtures_sha256':sha(out),'whole_original_sender_functions_unchanged':True,'adapter':'Direct original CLIENT primary-slot projection; linear case-insensitive key search only in host sender shim.','source_sha256':sha(code.encode()),'source_oracle_sanitized':False}
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--source-root',type=Path,default=ROOT);parser.add_argument('--work',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args();work=a.work.resolve();work.mkdir(parents=True,exist_ok=False)
 legacy=module('original_receiver_checker',HERE/'check_original_costume_receive.py');gen=module('original_receiver_source',HERE/'prepare_original_costume_receive.py');generated,source=gen.generate(a.source_root);assert generated==(HERE/'original_costume_receive.inc').read_text()
 archive=HERE/'qualification/costume-builder-20261017/offline-primary-slots.bin.gz';raw=gzip.decompress(archive.read_bytes());assert len(raw)==641477 and sha(raw)==RAW_SHA;rawfile=work/'client-primary-slots.bin';rawfile.write_bytes(raw);expected,tables=projection(raw)
 inputs=[HERE/n for n in ['coh_original_costume_receive.c','coh_original_costume_receive.h','coh_client_costume_slots.h','original_costume_receive.inc','test_client_costume_slots.c','test_original_costume_receive.c','check_client_costume_slots.py','check_original_costume_receive.py','costume_oracle_shim.h']]+[archive]
 dependency_text=subprocess.check_output(['cc','-std=c99','-MM',str(HERE/'coh_original_costume_receive.c'),str(HERE/'../replication/coh_replication.c'),str(HERE/'test_client_costume_slots.c')],text=True)
 for rule in dependency_text.replace('\\\n',' ').splitlines():
  for name in rule.split(':',1)[1].split():
   path=Path(name).resolve()
   if path not in inputs:inputs.append(path)
 before={str(p.relative_to(ROOT)):sha(p.read_bytes())for p in inputs}
 literal,producer=legacy.fixtures(a.source_root,work,gen.extract);fixture,indexed=indexed_sender(work,legacy,tables)
 result={'schema':'coh-client-costume-slot-consumer-v1','source':source,'raw_sha256':RAW_SHA,'raw_bytes':len(raw),'index_bytes':len(expected),'independent_offset_index_sha256':sha(expected),'original_sender':producer,'indexed_sender':indexed,'inputs_sha256':before,'native':{}}
 for mode,flags in [('release',['-O2','-fstack-usage']),('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  target=work/mode;target.mkdir();binary=target/'slots';output_index=target/'offsets.bin'
  legacy.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,HERE/'coh_original_costume_receive.c',HERE/'../replication/coh_replication.c',HERE/'test_client_costume_slots.c','-lcrypto','-lm','-o',binary],target,'compile')
  env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'};native=json.loads(legacy.run([binary,rawfile,fixture,output_index],target,'native',env));assert output_index.read_bytes()==expected;result['native'][mode]=native
 frames=[]
 for path in(work/'release').glob('*.su'):
  for line in path.read_text().splitlines():
   name,size,kind=line.split('\t')
   if 'coh_original_costume_receive.c:'in name or 'original_costume_receive.inc:'in name or name.rsplit(':',1)[-1]in('valid','coh_rep_read','coh_rep_pack'):frames.append({'name':name,'bytes':int(size),'kind':kind})
 assert sum(x['bytes']for x in frames)<4096
 result['memory']={'raw_bytes':641477,'index_bytes':134144,'retained_payload_and_index':775621,'workspace_bytes':65536,'call_stack_reserve':4096,'prepare_stack_reserve':1024,'conservative_native_frame_sum':sum(x['bytes']for x in frames),'frames':frames,'initial_aggregate_limit':8388608,'device_RSS_PSS':None}
 assert before=={str(p.relative_to(ROOT)):sha(p.read_bytes())for p in inputs}
 result.update(passed=True,original_receiver_unchanged=True,physical_packet_replayed=False,complete_entity_or_ack=False)
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'native':result['native'],'memory':{k:v for k,v in result['memory'].items()if k!='frames'}}))
if __name__=='__main__':main()
