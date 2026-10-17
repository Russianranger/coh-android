#!/usr/bin/env python3
"""Additive schema-bound full attributes in ordered initial suffix diagnostic."""
import argparse,ast,gzip,hashlib,json,os,re,subprocess,tempfile
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
def bits(raw,start,end):return [(raw[i//8]>>(i%8))&1 for i in range(start,end)]
def wire(data):
 raw=bytearray((len(data)+7)//8)
 for i,b in enumerate(data):raw[i//8]|=b<<(i%8)
 return bytes(raw)
def source_stage(text,name):
 a=text.index('  case '+name+':');b=text.index('\n  case ',a+1)if '\n  case 'in text[a+1:]else text.index('\n  default:',a)
 return text[a:b]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--suffix-evidence',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 host=json.loads((a.suffix_evidence/'host.json').read_bytes());header=a.suffix_evidence/'fixtures.h'
 if sha(header)!='da69e9a2c715526a9f1c263c9da57b08b659690550ca786741f5446dca8b68cb' or sha(header)!=host['fixtures_sha256']:raise ValueError('retained suffix mismatch')
 if any(sha(ROOT/p)!=h for p,h in host['source_sha256'].items()):raise ValueError('retained suffix source changed')
 fullprovider=ROOT/'native-android/combined-client/diagnostics/attribute-full-20261017';fullpath=fullprovider/'host-proof.json.gz'
 if sha(fullpath)!='be06f922d1ef9ca5d8f851fc61d212b079c896d1574c4eeedfe80fbb1e41b579':raise ValueError('full source corpus')
 full=json.loads(gzip.decompress(fullpath.read_bytes()));native=HERE/'../entity-attributes/qualification/full-20261017/host-proof.json.gz';nativeproof=json.loads(gzip.decompress(native.read_bytes()))
 if any(sha(ROOT/p)!=h for p,h in nativeproof['source_sha256'].items()):raise ValueError('full native source changed')
 original=(HERE/'coh_initial_suffix.c').read_text();new=(HERE/'coh_initial_suffix_attributes.c').read_text();stages={}
 for name in('CHARACTER','POWER_INFO','POWER_MODES','BADGES','BADGE_MONITOR','INVENTORY','SOCIAL','DYNAMIC','VIEW'):
  label='COH_SUFFIX_'+name;old=source_stage(original,label);current=source_stage(new,label)
  if old!=current:raise ValueError('frozen nonattribute stage changed '+name)
  stages[name]=hashlib.sha256(old.encode()).hexdigest()
 spec=ast.parse((HERE/'check.py').read_bytes());definitions=ast.literal_eval(next(n.value for n in spec.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='SOURCES'for t in n.targets)));sources=[HERE.parent/d/n for d,ns in definitions.items()for n in ns]+[HERE/'coh_initial_suffix_attributes.c',HERE/'../entity-attributes/coh_attrib_description.c',HERE/'../attribute-dictionary/coh_attribute_dictionary.c']
 paths={ROOT/p for p in host['source_sha256']}|{ROOT/p for p in nativeproof['source_sha256']}|set(sources)|{HERE/n for n in('coh_initial_suffix_attributes.h','check_attributes.py','test_suffix_attributes.c','test_suffix.c','ATTRIBUTES_PROFILE.md')};hashes={str(p.resolve().relative_to(ROOT)):sha(p)for p in sorted(paths)}
 text=header.read_text();raws={int(n):bytes(map(int,values.split(',')))for n,values in re.findall(r'static const uint8_t wire_(\d+)\[\]=\{([\d,]+)\};',text)};oldcases=host['original']['cases'];lines=[];rows=[];joined=[]
 for idx,c in enumerate(oldcases):
  if c['scenario']or c['control']:continue
  attr_begin,attr_end=c['spans'][7];body_begin=attr_begin+(8 if c['mode']else 1)
  for f in full['cases']:
   if f['aligned']!=c['mode']or f['begin']%8!=body_begin%8:continue
   data=bits(raws[idx],0,attr_begin)+[1]+[0]*(7 if c['mode']else 0)+bits(bytes.fromhex(f['wire_hex']),f['begin'],f['end']);new_attr_end=len(data)
   # Empty dynamic and sky/slave are scalar-only source leaves; no compressed
   # byte-array is relocated across an unqualified absolute-alignment boundary.
   tail=bits(raws[idx],attr_end,c['bits']);expected_tail=48 if c['mode']else 3
   if len(tail)!=expected_tail or any(tail):raise ValueError('not empty scalar-only tail')
   data+=tail;out=wire(data);name='full_suffix_'+str(len(rows));lines.append('static const uint8_t '+name+'[]={'+','.join(map(str,out))+'};');rows.append('{'+name+',sizeof('+name+'),'+','.join(map(str,[c['prefix'],len(data),c['mode'],len(f['modifiers']),attr_begin,new_attr_end,len(data)]))+'}');joined.append({'base_fixture':idx,'mode':c['mode'],'prefix':c['prefix'],'full_original_scenario':f['scenario'],'full_original_begin':f['begin'],'attribute_begin':attr_begin,'attribute_end':new_attr_end,'bits':len(data),'modifiers':len(f['modifiers']),'sha256':hashlib.sha256(out).hexdigest()})
 fixture='\n'.join(lines)+'\nstatic const FullFixture full_fixtures[]={'+','.join(rows)+'};\n';checks={};binaries={};stack=[]
 if len(joined)!=80:raise ValueError('missing joined source profiles')
 with tempfile.TemporaryDirectory(prefix='coh-suffix-full-attribute-')as tmp:
  work=Path(tmp);(work/'fixtures.h').write_bytes(header.read_bytes());(work/'attribute-suffix-fixtures.h').write_text(fixture)
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else[]):
   exe=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-fmax-errors=2','-fno-diagnostics-show-caret',*flags,'-I'+str(work),*sources,HERE/'test_suffix_attributes.c','-lm','-lz','-lcrypto','-o',exe]);checks[mode]=json.loads(run([exe,HERE/'../attribute-dictionary/attrib_descriptions.bin'],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(exe)
  cpp=work/'header.cpp';cpp.write_text('#include \"coh_initial_suffix_attributes.h\"\nint main(){return coh_initial_suffix_attributes_diagnostic(nullptr,nullptr,nullptr,nullptr,nullptr,0,0)==COH_INVALID?0:1;}\n');objects=[]
  for i,source in enumerate(sources):
   obj=work/(str(i)+'.o');run(['cc','-std=c99','-O2','-c',source,'-o',obj]);objects.append(obj)
  run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-lm','-lz','-o',work/'cpp']);run([work/'cpp'])
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    location,n,kind=line.split('\t')
    if any(str(s)+':'in location for s in sources):stack.append({'function':location,'bytes':int(n),'kind':kind})
  if not stack or any(x['kind']not in('static','dynamic,bounded')for x in stack)or sum(x['bytes']for x in stack)>65536:raise ValueError('native stack reserve')
 if any(x!=checks['release']for x in checks.values()):raise ValueError('mode mismatch')
 if hashes!={str(p.resolve().relative_to(ROOT)):sha(p)for p in sorted(paths)}:raise ValueError('source changed')
 result={'schema':'coh-initial-suffix-full-attributes-v1','passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).strip(),'source_sha256':hashes,'checks':checks,'binary_sha256':binaries,'native_stack':stack,'frozen_nonattribute_stage_sha256':stages,'joined_original_profiles':joined,'old_suffix_fixtures_sha256':sha(header),'old_suffix_host_sha256':sha(a.suffix_evidence/'host.json'),'attribute_fixture_sha256':hashlib.sha256(fixture.encode()).hexdigest(),'cpp_link_passed':True,'original_suffix_api_unchanged':True,'whole_original_object_graph_executed':False,'runtime_cache_generation':False,'dynamic_world_authority':False,'actor_publication':False,'ack_permitted':False,'external_zlib_crypto_callback_stack_sanitizer_closure':False,'android_built':False,'thor_accepted':False}
 with a.output.open('xb')as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0)as out:out.write((json.dumps(result,indent=2)+'\n').encode())
 print(json.dumps({'passed':True,'checks':checks,'joined':len(joined)}))
if __name__=='__main__':main()
