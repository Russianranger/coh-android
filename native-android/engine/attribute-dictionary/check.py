#!/usr/bin/env python3
"""Exact small attribute cache+whole original schema+native bounded owner."""
import argparse,ctypes as C,gzip,hashlib,importlib.util,json,os,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=240,**kw)
 if p.returncode:raise RuntimeError(str(args)+'\n'+p.stdout+p.stderr)
 return p.stdout
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 # Freeze executable helper dependencies BEFORE any dynamic import.
 helpers=[HERE/'oracle.py',HERE/'independent.py',HERE/'../costume-inputs/oracle.py',HERE/'../costume-tree/crc_provider.py'];helperhashes={str(p.resolve().relative_to(ROOT)):sha(p)for p in helpers}
 oracle=load('attribute_cache_original',HERE/'oracle.py');model=load('attribute_cache_model',HERE/'independent.py');small=load('attribute_small_source',HERE/'../costume-inputs/oracle.py')
 sourcepaths=small.PATHS+oracle.EXTRA+['libs/UtilitiesLib/include/utilitieslib/utils/structInternals.h','libs/UtilitiesLib/src/network/crypt.cpp'];paths={ROOT/'upstream/ouroboros'/p for p in sourcepaths}|set(helpers)|{p for p in HERE.iterdir()if p.suffix in('.c','.h','.py','.json','.bin','.md')}|{HERE/'../costume-inputs/coh_costume_inputs.h',HERE/'../costume-import/coh_costume_import.h',HERE/'../entities/coh_costume.h',HERE/'../entities/coh_entities.h',HERE/'../coh_contracts.h',HERE/'../replication/coh_replication.h'};hashes={str(p.resolve().relative_to(ROOT)):sha(p)for p in sorted(paths)}
 raw=(HERE/'attrib_descriptions.bin').read_bytes()
 if len(raw)!=5892 or sha(HERE/'attrib_descriptions.bin')!='20f770f406e661050434284e4253f721699df2112ea4481de66b50146304c132':raise ValueError('exact input mismatch')
 cases=[];lines=[];rows=[];checks={};binaryhashes={};stack=[]
 with tempfile.TemporaryDirectory(prefix='coh-attribute-dictionary-')as tmp:
  work=Path(tmp);lib,proof=oracle.build(ROOT,work)
  if lib.original_attribute_crc()&0xffffffff!=0x315acdb1:raise ValueError('original ParseTableCRC mismatch')
  for scenario in range(5):
   source=(C.c_ubyte*len(raw)).from_buffer_copy(raw);out=(C.c_ubyte*65536)();words=(C.c_uint*4096)();text=(C.c_char*131072)();n=C.c_uint();size=lib.original_attribute_variant(source,len(raw),72,out,words,text,C.byref(n),scenario);wire=bytes(out[:size]);expected=model.decode(wire)
   if not scenario and wire!=raw:raise ValueError('actual cache roundtrip mismatch')
   again=(C.c_ubyte*65536)();source=(C.c_ubyte*len(wire)).from_buffer_copy(wire);size2=lib.original_attribute_tree(source,len(wire),72,again,words,text,C.byref(n))
   if size2!=len(wire)or bytes(again[:size2])!=wire:raise ValueError('original variant roundtrip')
   strings=bytes(text[:n.value]).split(b'\0')[:-1]
   if words[0]!=expected['category_count']or words[1]!=expected['row_count']:raise ValueError('original/model count')
   for i,row in enumerate(expected['ordered_sender_rows']):
    actual=list(words[2+i*8:10+i*8]);wanted=[row[k]for k in('category','row','type','style','key','offset','show_base_word','category_rows')];wanted[6]&=255
    if actual!=wanted or [s.decode('ascii')for s in strings[i*4:i*4+4]]!=[row[k]for k in('category_name','name','display_name','tooltip')]:raise ValueError('original/model field')
   name='wire_'+str(scenario);lines.append('static const unsigned char '+name+'[]={'+','.join(map(str,wire))+'};');erows=[]
   for row in expected['ordered_sender_rows']:
    vals=[row[k]for k in('category','row','category_rows','type','style','key','offset','show_base_word','lookup_key')];strs=[row[k]for k in('category_name','name','display_name','tooltip')];erows.append('{'+','.join([str(v)+'u'for v in vals]+[json.dumps(s)for s in strs])+'}')
   lines.append('static const Expected expected_'+str(scenario)+'[]={'+','.join(erows)+'};');rows.append('{'+name+',sizeof('+name+'),expected_'+str(scenario)+','+str(expected['row_count'])+','+str(expected['category_count'])+','+str(scenario)+'}');cases.append({'scenario':scenario,'bytes':len(wire),'sha256':hashlib.sha256(wire).hexdigest(),'expected':expected,'whole_original_read_write_roundtrip':True})
  fixture='\n'.join(lines)+'\nstatic const Fixture fixtures[]={'+','.join(rows)+'};\n';(work/'dictionary-fixtures.h').write_text(fixture)
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else[]):
   exe=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(work),HERE/'coh_attribute_dictionary.c',HERE/'test_dictionary.c','-lcrypto','-o',exe]);checks[mode]=json.loads(run([exe],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaryhashes[mode]=sha(exe)
  cpp=work/'header.cpp';cpp.write_text('#include \"coh_attribute_dictionary.h\"\nint main(){return coh_attribute_dictionary_read({nullptr,0},0,nullptr,nullptr,nullptr,nullptr,0,0)==COH_INVALID?0:1;}\n');run(['cc','-std=c99','-O2','-c',HERE/'coh_attribute_dictionary.c','-o',work/'dictionary.o']);run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,work/'dictionary.o','-o',work/'cpp']);run([work/'cpp'])
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    name,n,kind=line.split('\t')
    if str(HERE/'coh_attribute_dictionary.c')+':'in name:stack.append({'function':name,'bytes':int(n),'kind':kind})
  if not stack or sum(s['bytes']for s in stack)>16384 or any(s['kind']not in('static','dynamic,bounded')for s in stack):raise ValueError('stack bound')
 if any(x!=checks['release']for x in checks.values()):raise ValueError('sanitizer mismatch')
 if hashes!={str(p.resolve().relative_to(ROOT)):sha(p)for p in sorted(paths)}or helperhashes!={str(p.resolve().relative_to(ROOT)):sha(p)for p in helpers}:raise ValueError('source changed')
 result={'schema':'coh-exact-attribute-dictionary-v1','passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).strip(),'source_sha256':hashes,'provider_sha256':helperhashes,'original':proof,'original_crc':0x315acdb1,'cases':cases,'checks':checks,'binary_sha256':binaryhashes,'fixture_sha256':hashlib.sha256(fixture.encode()).hexdigest(),'native_stack':stack,'cpp_link_passed':True,'actual_cache_bytes_decoded':True,'runtime_cache_branch_observed':False,'current_server_generation':False,'actor_authority':False,'original_oracle_sanitized':False,'external_crypto_stack_and_sanitizer_closure':False,'android_built':False,'thor_accepted':False}
 with a.output.open('xb')as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0)as out:out.write((json.dumps(result,indent=2)+'\n').encode())
 print(json.dumps({'passed':True,'checks':checks,'original_crc':'315acdb1','actual_rows':cases[0]['expected']['row_count']}))
if __name__=='__main__':main()
