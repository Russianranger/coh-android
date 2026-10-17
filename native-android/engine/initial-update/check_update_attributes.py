#!/usr/bin/env python3
"""Whole initial diagnostic with schema-bound full attribute suffix, no ACK."""
import argparse,ast,gzip,hashlib,io,json,os,struct,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def read(p):
 p=p.resolve()
 if str(p).startswith(str(ROOT/'upstream/ouroboros')+'/'):return subprocess.check_output(['git','-C',ROOT,'show','HEAD:'+str(p.relative_to(ROOT))])
 return p.read_bytes()
def sha(p):return hashlib.sha256(read(p)).hexdigest()
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=240,**kw)
 if p.returncode:raise RuntimeError(str(args)+'\n'+p.stdout[-8000:]+p.stderr[-8000:])
 return p.stdout
def extract(text,name):
 a=text.index('static CohStatus '+name+'(');start=text.index('{',a);depth=1;b=start+1
 while depth:depth+=(text[b]=='{')-(text[b]=='}');b+=1
 return text[a:b]
def bitlist(raw,start,end):return [(raw[i//8]>>(i%8))&1 for i in range(start,end)]
def wire(bits):
 raw=bytearray((len(bits)+7)//8)
 for i,b in enumerate(bits):raw[i//8]|=b<<(i%8)
 return bytes(raw)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 oldproof=json.loads(gzip.decompress((HERE/'qualification/20261017/host-proof.json.gz').read_bytes()));profile=HERE/'../initial-suffix/qualification/attributes-20261017/host-proof.json.gz';newproof=json.loads(gzip.decompress(profile.read_bytes()))
 for proof in(oldproof,newproof):
  if any(sha(ROOT/p)!=h for p,h in proof['source_sha256'].items()):raise ValueError('frozen child source changed')
 binary=HERE/'qualification/20261017/native-fixtures.bin.gz';compressed=binary.read_bytes()
 if len(compressed)!=3072105 or hashlib.sha256(compressed).hexdigest()!='ce9e2143b3e0e21042688c916dd6369c4d67a560c12fb76f3bd1bb984fdd1892':raise ValueError('old fixture compressed identity')
 with gzip.GzipFile(fileobj=io.BytesIO(compressed))as f:
  raw=f.read(16870453)
  if len(raw)!=16870452 or f.read(1):raise ValueError('old fixture bound')
 if hashlib.sha256(raw).hexdigest()!='f5917df7da86829ad280051fa16c492209159f09f746b688e05d6b080141c508':raise ValueError('old fixture bytes')
 at=0
 def words(n):
  nonlocal at
  out=struct.unpack_from('<'+'I'*n,raw,at);at+=n*4;return out
 count=words(1)[0];old=[]
 for _ in range(count):
  row=words(12);data=raw[at:at+row[0]];at+=row[0];old.append((row,data))
 if at!=len(raw)or count!=len(oldproof['fixtures']['cases']):raise ValueError('old corpus exact end')
 fullpath=ROOT/'native-android/combined-client/diagnostics/attribute-full-20261017/host-proof.json.gz'
 if sha(fullpath)!='be06f922d1ef9ca5d8f851fc61d212b079c896d1574c4eeedfe80fbb1e41b579':raise ValueError('full leaf corpus')
 full=json.loads(gzip.decompress(fullpath.read_bytes()))
 command=extract((HERE/'coh_initial_update.c').read_text(),'command_tail')
 if command!=extract((HERE/'coh_initial_update_attributes.c').read_text(),'command_tail'):raise ValueError('frozen command parser changed')
 # The byte-identical private implementation was compared to180 exact original
 # append/end frames by the independent frozen native framing tranche.
 framing=json.loads(subprocess.check_output(['git','-C',ROOT,'show','0c6763e5c:native-android/engine/initial-update/qualification/20261017/framing-proof.json']))
 if framing['checks']['release']['cases']!=180 or framing['checks']['release']['checks']!=467797:raise ValueError('framing qualification identity')
 spec=ast.parse((HERE/'../initial-suffix/check.py').read_bytes());definitions=ast.literal_eval(next(n.value for n in spec.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='SOURCES'for t in n.targets)))
 sources=[HERE.parent/d/n for d,ns in definitions.items()for n in ns]+[HERE/'../selected-record/coh_selected_record.c',HERE/'../entities/coh_costume.c',HERE/'../entities/coh_taskforce.c',HERE/'../entities/coh_very_rare_tail.c',HERE/'../entities/coh_teammate_buffs.c',HERE/'../initial-record/coh_initial_record.c',HERE/'../initial-record/coh_initial_list.c',HERE/'../entity-control/coh_entity_control.c',HERE/'coh_initial_update.c',HERE/'coh_initial_update_attributes.c',HERE/'../initial-suffix/coh_initial_suffix_attributes.c',HERE/'../entity-attributes/coh_attrib_description.c',HERE/'../attribute-dictionary/coh_attribute_dictionary.c'];sources=list(dict.fromkeys(p.resolve()for p in sources))
 paths={ROOT/p for p in oldproof['source_sha256']}|{ROOT/p for p in newproof['source_sha256']}|set(sources)|{HERE/n for n in('coh_initial_update_attributes.h','check_update_attributes.py','test_update_attributes.c','ATTRIBUTES_PROFILE.md')}|{fullpath,binary,profile};hashes={str(p.resolve().relative_to(ROOT)):sha(p)for p in sorted(paths)};cases=[];metadata=[]
 for idx,((row,data),meta)in enumerate(zip(old,oldproof['fixtures']['cases'])):
  if meta['scenario']or meta['tail']not in(0,3,4):continue
  mode=row[3];attribute_begin=row[11]-(56 if mode else 4);attribute_end=attribute_begin+(8 if mode else 1)
  if any(bitlist(data,attribute_begin,row[11])):raise ValueError('expected empty scalar leaves')
  for leaf in full['cases']:
   if leaf['aligned']!=mode or leaf['begin']%8!=attribute_end%8:continue
   bits=bitlist(data,0,attribute_begin)+[1]+[0]*(7 if mode else 0)+bitlist(bytes.fromhex(leaf['wire_hex']),leaf['begin'],leaf['end']);new_attribute_end=len(bits);bits+=bitlist(data,attribute_end,row[11]);suffix_end=len(bits);bits+=bitlist(data,row[11],row[1]);out=wire(bits);ends=[row[7],row[8],row[9],row[10],attribute_begin,new_attribute_end,suffix_end];cases.append((out,[len(out),len(bits),row[2],mode,row[4],len(leaf['modifiers']),row[6],*ends]));metadata.append({'base_fixture':idx,'mode':mode,'record_count':row[4],'full_original_scenario':leaf['scenario'],'tail':row[6],'begin':row[2],'ends':ends,'bits':len(bits),'sha256':hashlib.sha256(out).hexdigest()})
 if len(cases)!=288:raise ValueError('missing composed profile '+str(len(cases)))
 checks={};binaries={};stack=[]
 with tempfile.TemporaryDirectory(prefix='coh-whole-full-attributes-')as tmp:
  work=Path(tmp);fixtures=work/'fixtures.bin'
  with fixtures.open('xb')as f:
   f.write(struct.pack('<I',len(cases)))
   for data,row in cases:f.write(struct.pack('<14I',*row));f.write(data)
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else[]):
   exe=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-fmax-errors=2','-fno-diagnostics-show-caret',*flags,*sources,HERE/'test_update_attributes.c','-lm','-lz','-lcrypto','-o',exe]);checks[mode]=json.loads(run([exe,fixtures,HERE/'../attribute-dictionary/attrib_descriptions.bin'],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(exe)
  cpp=work/'header.cpp';cpp.write_text('#include "coh_initial_update_attributes.h"\nint main(){return coh_initial_update_attributes_diagnostic(nullptr,nullptr,nullptr,nullptr,nullptr,nullptr,0,0)==COH_INVALID?0:1;}\n');objects=[]
  for i,source in enumerate(sources):
   obj=work/(str(i)+'.o');run(['cc','-std=c99','-O2','-c',source,'-o',obj]);objects.append(obj)
  run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-lm','-lz','-o',work/'cpp']);run([work/'cpp'])
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    location,n,kind=line.split('\t')
    if any(str(s)+':'in location for s in sources):stack.append({'function':location,'bytes':int(n),'kind':kind})
  if not stack or any(x['kind']not in('static','dynamic,bounded')for x in stack)or sum(x['bytes']for x in stack)>131072:raise ValueError('native stack reserve')
  fixture_sha=sha(fixtures)
 if any(x!=checks['release']for x in checks.values()):raise ValueError('mode mismatch')
 if hashes!={str(p.resolve().relative_to(ROOT)):sha(p)for p in sorted(paths)}:raise ValueError('source changed')
 result={'schema':'coh-whole-initial-full-attributes-v1','passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).strip(),'source_sha256':hashes,'checks':checks,'binary_sha256':binaries,'fixture_sha256':fixture_sha,'native_stack':stack,'cpp_link_passed':True,'joined_cases':metadata,'command_tail_frozen_source_sha256':hashlib.sha256(command.encode()).hexdigest(),'command_tail_existing_original_comparison':{'source_commit':'2ac9ba789','proof_commit':'0c6763e5c','cases':180,'native_checks_each_mode':467797},'original_initial_api_unchanged':True,'whole_original_object_graph_executed':False,'runtime_dictionary_generation':False,'selected_owner_authority':False,'dynamic_world_authority':False,'actor_publication':False,'ack_permitted':False,'external_zlib_crypto_callback_stack_sanitizer_closure':False,'android_built':False,'thor_accepted':False}
 with a.output.open('xb')as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0)as out:out.write((json.dumps(result,indent=2)+'\n').encode())
 print(json.dumps({'passed':True,'checks':checks,'cases':len(cases)}))
if __name__=='__main__':main()
