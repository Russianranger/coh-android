#!/usr/bin/env python3
"""Whole original class binary bodies against compact native leased raw owner."""
import argparse,ctypes as C,gzip,hashlib,json,os,re,struct,subprocess,tempfile,types,zipfile,py_compile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];LOCKED={}
def read(p):
 p=p.resolve()
 if str(p).startswith(str(ROOT/'upstream/ouroboros')+'/'):return subprocess.check_output(['git','-C',ROOT,'show','HEAD:'+str(p.relative_to(ROOT))])
 return p.read_bytes()
def sha(p):return hashlib.sha256(read(p)).hexdigest()
def module(n,p):
 p=p.resolve();body=p.read_bytes()
 if LOCKED.get(p)!=hashlib.sha256(body).hexdigest():raise ValueError('helper source not admitted '+str(p))
 m=types.ModuleType(n);m.__file__=str(p);exec(compile(body,str(p),'exec'),m.__dict__);return m
def loader_controls(work):
 p=work/'stale.py';p.write_text('value=1\n');py_compile.compile(str(p),doraise=True);stat=p.stat();p.write_text('value=2\n');os.utime(p,ns=(stat.st_atime_ns,stat.st_mtime_ns));LOCKED[p.resolve()]=sha(p)
 if module('class_stale_control',p).value!=2:raise ValueError('stale PYC executed')
 p.write_text('value=3\n')
 try:module('class_changed_control',p)
 except ValueError:pass
 else:raise ValueError('changed source executed')
 LOCKED.pop(p.resolve());return {'stale_pyc_ignored':True,'changed_source_refused_before_execution':True}
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=240,**kw)
 if p.returncode:raise RuntimeError(str(args)+'\n'+p.stdout[-6000:]+p.stderr[-6000:])
 return p.stdout
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--cache-zip',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 helpers=[HERE/n for n in('classes_oracle.py','classes_independent.py','class_schema.py','origins_oracle.py','../costume-inputs/oracle.py','../costume-inputs/source-pins.json','../costume-inputs/coh_costume_inputs.h','../costume-tree/crc_provider.py')];LOCKED.update({p.resolve():sha(p.resolve())for p in helpers});oracle=module('class_original',helpers[0]);oracle.module=module;independent=module('class_independent',helpers[1]);schema=module('class_schema',helpers[2]);origin=module('class_origin_paths',helpers[3]);small=module('class_small_paths',helpers[4]);crc=module('class_crc_paths',helpers[-1]);original=small.PATHS+origin.EXTRA+oracle.EXTRA+crc.PATHS;sourcepaths=[ROOT/'upstream/ouroboros'/p for p in original];texts={p:read(ROOT/'upstream/ouroboros'/p).decode().replace('\r\n','\n')for p,_ in schema.TABLES};tables,pins,generated=schema.schema(texts)
 if generated!=(HERE/'class_schema.inc').read_text():raise ValueError('native schema changed')
 sources=[HERE/'coh_classes.c'];paths=set(helpers+sourcepaths+sources+[HERE/n for n in('coh_classes.h','class_schema.inc','check_classes.py','test_classes.c','CLASSES.md')]);pending=[HERE/'coh_classes.c',HERE/'coh_classes.h',HERE/'test_classes.c',helpers[-2]];seen=set()
 while pending:
  p=pending.pop().resolve()
  if p in seen:continue
  seen.add(p);paths.add(p)
  for inc in re.findall(r'^#include "([^"]+)"',p.read_text(),re.M):
   q=(p.parent/inc).resolve()
   if q.is_file():pending.append(q)
 hashes={str(p.resolve().relative_to(ROOT)):sha(p.resolve())for p in sorted(paths)}
 if a.cache_zip.stat().st_size!=27071659 or sha(a.cache_zip)!='5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051':raise ValueError('exact donor ZIP required')
 expected={'classes.bin':(1219292,'91af1ca0b304d77e56f356d54e1a880309b910c40f1729672cc0af1b83dd6733'),'villain_classes.bin':(4228088,'bc0789f03941d845f9574f6df4dd1ad953ad35328a3d7323c07d02d92fdbd523')};cases=[];checks={};binaries={};stack=[]
 with tempfile.TemporaryDirectory(prefix='coh-classes-')as tmp:
  work=Path(tmp);loader=loader_controls(work);(work/'class-controls.h').write_text('#define CLASS_ORIGINS_FIELD '+str(next(i for i,f in enumerate(tables[1])if f['name']=='AllowedOrigins'))+'\n#define CLASS_MOD_FIELD '+str(next(i for i,f in enumerate(tables[1])if f['name']=='ModTable'))+'\n');originalroot=work/'source'
  for p in sourcepaths:
   dst=originalroot/p.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(read(p))
  ow=work/'oracle';ow.mkdir();lib,proof=oracle.build(originalroot,ow);fixture=work/'fixtures.bin'
  with zipfile.ZipFile(a.cache_zip)as z,fixture.open('xb')as f:
   f.write(struct.pack('<I',8))
   for name,(size,digest)in expected.items():
    info=z.getinfo('data/bin/'+name)
    if info.file_size!=size:raise ValueError('cache member bound')
    with z.open(info)as stream:
     raw=stream.read(size+1)
     if len(raw)!=size or stream.read(1)or hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('cache identity')
    initial=independent.decode(raw,tables)
    for scenario in range(4):
     out=C.create_string_buffer(size+65536);counts=(C.c_uint*128)();written=lib.original_class_tree(raw,len(raw),initial['begin'],out,counts,scenario);assert written;wire=out.raw[:written];decoded=independent.decode(wire,tables);assert decoded['header_crc']==0x7ff68aaf
     if not scenario:assert wire==raw
     names=[decoded['texts'][e['name_text']]['text']for e in decoded['entries']];indices=[max(j for j,s in enumerate(names)if s.lower()==n.lower())for n in names];assert counts[0]==len(names)and list(counts[1:1+len(names)])==indices
     projection=independent.serialize(decoded);f.write(struct.pack('<I',len(wire)));f.write(wire);f.write(projection);f.write(struct.pack('<'+'I'*len(indices),*indices));cases.append({'input':name,'scenario':scenario,'bytes':len(wire),'sha256':hashlib.sha256(wire).hexdigest(),'classes':len(names),'scalar_words':decoded['scalar_words'],'array_words':decoded['array_words'],'text_count':len(decoded['texts']),'modtables':len(decoded['modtables']),'identity_names':names,'original_reverse_indices':indices,'independent_projection_sha256':hashlib.sha256(projection).hexdigest()})
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else[]):
   exe=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(work),*sources,HERE/'test_classes.c','-lcrypto','-o',exe]);checks[mode]=json.loads(run([exe,fixture],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(exe)
  cpp=work/'header.cpp';cpp.write_text('#include "coh_classes.h"\nint main(){return coh_classes_find(nullptr,CohBytes{nullptr,0},nullptr)==COH_INVALID?0:1;}\n');obj=work/'classes.o';run(['cc','-std=c99','-O2','-c',sources[0],'-o',obj]);run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,obj,'-o',work/'cpp']);run([work/'cpp'])
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    location,n,kind=line.split('\t')
    if str(sources[0])+':'in location:stack.append({'function':location,'bytes':int(n),'kind':kind})
  assert stack and all(x['kind']in('static','dynamic,bounded')for x in stack)and 4*sum(x['bytes']for x in stack)<16384
  fixture_hash=sha(fixture)
 if hashes!={str(p.resolve().relative_to(ROOT)):sha(p.resolve())for p in sorted(paths)}:raise ValueError('source changed')
 assert all(c==checks['release']for c in checks.values())
 result={'schema':'coh-original-classes-compact-raw-v1','passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).strip(),'source_sha256':hashes,'original':proof,'helper_loader_controls':loader,'source_table_sha256_lf':pins,'original_cases':cases,'checks':checks,'binary_sha256':binaries,'native_stack':stack,'maximum_recursive_frames':4,'fixture_sha256':fixture_hash,'cpp_link_passed':True,'owned_strings':True,'leased_raw_arrays':True,'global_define_source_crc_executed':False,'repack_finalize_callbacks_executed':False,'runtime_shared_cache_generation':False,'serveronly_cache_association':False,'actor_authority':False,'original_oracle_sanitized':False,'android_executed':False}
 with a.output.open('xb')as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0)as z:z.write((json.dumps(result,indent=2)+'\n').encode())
 print(json.dumps({'passed':True,'checks':checks,'cases':len(cases)}))
if __name__=='__main__':main()
