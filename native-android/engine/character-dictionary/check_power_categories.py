#!/usr/bin/env python3
"""Exact category payload + original partial dictionary constructor/native owner."""
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
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=240,**kw)
 if p.returncode:raise RuntimeError(str(args)+'\n'+p.stdout[-6000:]+p.stderr[-6000:])
 return p.stdout
def controls(work):
 p=work/'stale.py';p.write_text('value=1\n');py_compile.compile(str(p),doraise=True);stat=p.stat();p.write_text('value=2\n');os.utime(p,ns=(stat.st_atime_ns,stat.st_mtime_ns));LOCKED[p.resolve()]=sha(p);assert module('category_stale',p).value==2;p.write_text('value=3\n')
 try:module('category_changed',p)
 except ValueError:pass
 else:raise ValueError('changed helper executed')
 LOCKED.pop(p.resolve());return {'stale_pyc_ignored':True,'changed_source_refused_before_execution':True}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--cache-zip',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 if not __debug__:raise ValueError('assertion controls must remain enabled')
 helpers=[HERE/p for p in('category_hash_oracle.py','power_categories_oracle.py','power_categories_independent.py','classes_oracle.py','origins_oracle.py','../costume-inputs/oracle.py','../costume-inputs/source-pins.json','../costume-inputs/coh_costume_inputs.h','../costume-tree/crc_provider.py','../stash32/oracle.py','../stash32/source-pins.json')];LOCKED.update({p.resolve():sha(p.resolve())for p in helpers});oracle=module('category_hash',helpers[0]);oracle.module=module;payload=module('category_payload_paths',helpers[1]);independent=module('category_independent',helpers[2]);classes=module('category_class_paths',helpers[3]);origin=module('category_origin_paths',helpers[4]);small=module('category_small_paths',helpers[5]);crc=module('category_crc_paths',helpers[8]);stash=module('category_stash_paths',helpers[9]);sourcepaths=[ROOT/'upstream/ouroboros'/p for p in set(oracle.EXTRA+payload.EXTRA+classes.EXTRA+origin.EXTRA+small.PATHS+crc.PATHS+stash.PATHS)];sources=[HERE/'coh_power_categories.c'];paths=set(helpers+sourcepaths+sources+[HERE/p for p in('coh_power_categories.h','test_power_categories.c','check_power_categories.py','POWER_CATEGORIES.md')]);pending=[*sources,HERE/'coh_power_categories.h',HERE/'test_power_categories.c',helpers[7]];seen=set()
 while pending:
  p=pending.pop().resolve()
  if p in seen:continue
  seen.add(p);paths.add(p)
  for name in re.findall(r'^#include "([^"]+)"',p.read_text(),re.M):
   q=(p.parent/name).resolve()
   if q.is_file():pending.append(q)
 hashes={str(p.resolve().relative_to(ROOT)):sha(p.resolve())for p in sorted(paths)}
 if a.cache_zip.stat().st_size!=27071659 or sha(a.cache_zip)!='5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051':raise ValueError('exact donor ZIP required')
 with zipfile.ZipFile(a.cache_zip)as z:
  info=z.getinfo('data/bin/powercats.bin')
  if info.file_size!=239304:raise ValueError('cache bound')
  with z.open(info)as f:raw=f.read(239305);assert len(raw)==239304 and not f.read(1)
 if hashlib.sha256(raw).hexdigest()!='67b46915b9bf4440de8f5cf8bf7dd4a9047daee7dc5cb96f2c2be3999f8fc5e7':raise ValueError('cache identity')
 actual=independent.decode(raw);cases=[];checks={};binaries={};stack=[]
 with tempfile.TemporaryDirectory(prefix='coh-power-categories-')as tmp:
  work=Path(tmp);loader=controls(work);originalroot=work/'source'
  for p in sourcepaths:
   q=originalroot/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(read(p))
  ow=work/'original';ow.mkdir();lib,proof=oracle.build(originalroot,ow);assert(lib.original_category_crc()&0xffffffff)==actual['crc']==0x59248ecb;fixture=work/'fixtures.bin'
  with fixture.open('xb')as f:
   f.write(struct.pack('<I',8))
   for scenario in range(8):
    out=C.create_string_buffer(1048576);stats=(C.c_uint*8)();n=lib.original_category_tree(raw,len(raw),actual['begin'],out,stats,scenario);assert n;wire=out.raw[:n];decoded=independent.decode(wire)
    if not scenario:assert raw==wire
    assert stats[0]==len(decoded['rows'])and stats[1]==sum(len(r['sets'])for r in decoded['rows'])and stats[2]==sum(len(r['indices'])for r in decoded['rows']);indices=(C.c_uint*4096)();stats=(C.c_uint*8)();accepted=lib.original_category_hash(wire,len(wire),decoded['begin'],indices,stats);names=[r['fields'][1]for r in decoded['rows']];expected=[next(j for j,k in enumerate(names)if k.lower()==name.lower())for name in names];assert list(indices[:len(names)])==expected;assert stats[0]==len(names)and stats[2]==len(set(n.lower()for n in names))and stats[3]==len(names)-stats[2]and stats[4]==stats[5]==0;assert accepted==int(stats[3]==0);status=7 if scenario==2 else 4 if scenario==7 else 0;projection=independent.serialize(decoded);f.write(struct.pack('<IIII',len(wire),decoded['begin'],status,len(projection)));f.write(wire);f.write(projection);cases.append({'scenario':scenario,'native_expected_status':status,'original_dictionary_constructor_accepted':bool(accepted),'constructor_statistics':list(stats[:6]),'bytes':len(wire),'wire_sha256':hashlib.sha256(wire).hexdigest(),'projection_sha256':hashlib.sha256(projection).hexdigest(),'categories':len(names),'set_references':sum(len(r['sets'])for r in decoded['rows']),'packed_indices':sum(len(r['indices'])for r in decoded['rows']),'source_lookup_indices_sha256':hashlib.sha256(bytes(indices)[:4*len(names)]).hexdigest()})
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else[]):
   exe=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,HERE/'test_power_categories.c','-lcrypto','-o',exe]);checks[mode]=json.loads(run([exe,fixture],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(exe)
  cpp=work/'header.cpp';cpp.write_text('#include "coh_power_categories.h"\nint main(){return coh_power_categories_find(nullptr,CohBytes{nullptr,0},nullptr)==COH_INVALID?0:1;}\n');obj=work/'category.o';run(['cc','-std=c99','-O2','-c',sources[0],'-o',obj]);run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,obj,'-o',work/'cpp']);run([work/'cpp'])
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    location,n,kind=line.split('\t')
    if str(sources[0])+':'in location:stack.append({'function':location,'bytes':int(n),'kind':kind})
  assert stack and all(x['kind']in('static','dynamic,bounded')for x in stack)and sum(x['bytes']for x in stack)<8192;fixture_sha=sha(fixture)
 if hashes!={str(p.resolve().relative_to(ROOT)):sha(p.resolve())for p in sorted(paths)}:raise ValueError('source changed')
 assert all(x==checks['release']for x in checks.values())
 result={'schema':'coh-original-power-category-compact-v1','passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).strip(),'source_sha256':hashes,'original':proof,'original_schema_crc':'0x59248ecb','exact_input_bytes':len(raw),'exact_input_sha256':hashlib.sha256(raw).hexdigest(),'cases':cases,'checks':checks,'binary_sha256':binaries,'native_stack':stack,'fixture_sha256':fixture_sha,'helper_loader_controls':loader,'cpp_link_passed':True,'owned_all_category_strings_references_and_packed_indices':True,'original_category_partial_dictionary_only':True,'original_full_set_power_dictionary_executed':False,'runtime_generation':False,'actor_authority':False,'original_hash_sanitized':False,'original_win32_abi_executed':False,'android_executed':False}
 with a.output.open('xb')as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0)as z:z.write((json.dumps(result,indent=2)+'\n').encode())
 print(json.dumps({'passed':True,'checks':checks,'cases':len(cases)}))
if __name__=='__main__':main()
