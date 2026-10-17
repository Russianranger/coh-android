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
 if not __debug__:raise ValueError('assertion controls required')
 helpers=[HERE/p for p in ('power_set_hash_oracle.py','power_sets_oracle.py','power_sets_independent.py','classes_oracle.py','origins_oracle.py','../costume-inputs/oracle.py','../costume-inputs/source-pins.json','../costume-inputs/coh_costume_inputs.h','../costume-tree/crc_provider.py','../stash32/oracle.py','../stash32/source-pins.json','power_categories_independent.py')];LOCKED.update({p.resolve():sha(p.resolve())for p in helpers});oracle=module('sets_hash',helpers[0]);oracle.module=module;payload=module('sets_payload',helpers[1]);independent=module('sets_independent',helpers[2]);classes=module('sets_class_paths',helpers[3]);origin=module('sets_origin_paths',helpers[4]);small=module('sets_small_paths',helpers[5]);crc=module('sets_crc_paths',helpers[8]);stash=module('sets_stash_paths',helpers[9]);categories=module('sets_categories',helpers[11]);sourcepaths=[ROOT/'upstream/ouroboros'/p for p in set(oracle.EXTRA+payload.EXTRA+classes.EXTRA+origin.EXTRA+small.PATHS+crc.PATHS+stash.PATHS)];sources=[HERE/'coh_power_sets.c',HERE/'../stash32/coh_stash32.c'];paths=set(helpers+sourcepaths+sources+[HERE/p for p in ('coh_power_sets.h','test_power_sets.c','check_power_sets.py','POWER_SETS.md')]);pending=[*sources,HERE/'coh_power_sets.h',HERE/'test_power_sets.c',helpers[7]];seen=set()
 while pending:
  p=pending.pop().resolve()
  if p in seen:continue
  seen.add(p);paths.add(p)
  for name in re.findall(r'^#include "([^"]+)"',p.read_text(),re.M):
   q=(p.parent/name).resolve()
   if q.is_file():pending.append(q)
 manifest_path=HERE/'../entities/qualification/costume-export-20261017/client-cache-manifest.json';paths.add(manifest_path);hashes={str(p.resolve().relative_to(ROOT)):sha(p.resolve())for p in sorted(paths)}
 if a.cache_zip.stat().st_size!=27071659 or sha(a.cache_zip)!='5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051':raise ValueError('exact donor ZIP required')
 manifest=json.loads(manifest_path.read_text());pin=manifest['files']['data/bin/powersets.bin'];assert pin['bytes']==3179276 and pin['schema_crc']=='2fe0d52d'
 with zipfile.ZipFile(a.cache_zip)as z:
  info=z.getinfo('data/bin/powersets.bin');assert info.file_size==3179276
  with z.open(info)as f:raw=f.read(3179277);assert len(raw)==3179276 and not f.read(1)
  raw_categories=z.read('data/bin/powercats.bin');assert hashlib.sha256(raw_categories).hexdigest()==manifest['files']['data/bin/powercats.bin']['sha256']
 assert hashlib.sha256(raw).hexdigest()==pin['sha256']
 fields,pin=independent.schema(read(ROOT/'upstream/ouroboros/Common/entity/powers_load.c').decode());expected='/* Complete ordered original ParseBasePowerSet persisted field kinds. */\nstatic const uint8_t field_kinds[30]={'+','.join(str(x['kind'])for x in fields)+'};\n';assert(HERE/'power_set_schema.inc').read_text()==expected;actual=independent.decode(raw,fields);cat=categories.decode(raw_categories);setnames=[r['fields'][1]for r in actual['rows']];name_map={name.lower():i for i,name in reversed(list(enumerate(setnames)))};references=[{'category':ci,'reference':ri,'name':name,'allocated_set':name_map.get(name.lower())}for ci,row in enumerate(cat['rows'])for ri,name in enumerate(row['sets'])];reached={r['allocated_set']for r in references if r['allocated_set']is not None};association={'profile':'historical-name-audit-only','category_input_sha256':hashlib.sha256(raw_categories).hexdigest(),'category_rows':len(cat['rows']),'ordered_references':len(references),'missing':[r for r in references if r['allocated_set']is None],'unreferenced_allocated_sets':[{'index':i,'name':name}for i,name in enumerate(setnames)if i not in reached],'original_forward_pointer_function_executed':False,'generation_association_accepted':False,'complete_dictionary_join':False};cases=[];checks={};binaries={};stack=[]
 with tempfile.TemporaryDirectory(prefix='coh-power-sets-')as tmp:
  work=Path(tmp);loader=controls(work);originalroot=work/'source'
  for p in sourcepaths:
   q=originalroot/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(read(p))
  ow=work/'original';ow.mkdir();lib,proof=oracle.build(originalroot,ow);assert(lib.original_sets_crc()&0xffffffff)==actual['crc']==0x2fe0d52d;fixture=work/'fixtures.bin'
  with fixture.open('xb')as f:
   f.write(struct.pack('<I',8))
   for scenario in range(8):
    out=C.create_string_buffer(8388608);stats=(C.c_uint*8)();n=lib.original_sets_tree(raw,len(raw),actual['begin'],out,stats,scenario);assert n;wire=out.raw[:n];decoded=independent.decode(wire,fields)
    if not scenario:assert raw==wire
    assert stats[0]==len(decoded['rows'])and stats[1]==sum(len(r['fields'][21])for r in decoded['rows'])and stats[2]==sum(len(r['fields'][22])for r in decoded['rows']);indices=(C.c_uint*8192)();slots=(C.c_uint*16384)();stats=(C.c_uint*8)();accepted=lib.original_sets_hash(wire,len(wire),decoded['begin'],indices,slots,stats);names=[r['fields'][1]for r in decoded['rows']];first={};expected=[]
    for i,name in enumerate(names):first.setdefault(name.lower(),i);expected.append(first[name.lower()])
    assert list(indices[:len(names)])==expected and stats[0]==len(names)and stats[2]==len(first)and stats[3]==len(names)-len(first)and stats[4]==stats[5]==0 and accepted==int(not stats[3]);f.write(struct.pack('<II',len(wire),decoded['begin']));f.write(wire);f.write(struct.pack('<8I',len(names),decoded['dependency_count'],sum(len(r['fields'][21])for r in decoded['rows']),sum(len(r['fields'][22])for r in decoded['rows']),stats[1],stats[2],stats[3],accepted))
    for r in decoded['rows']:
     f.write(struct.pack('<II',*r['record']))
     for span in r['spans']:f.write(struct.pack('<II',*span))
    f.write(bytes(slots))
    for name,index in zip(names,expected):
     b=name.encode();f.write(struct.pack('<I',len(b)));f.write(b);f.write(struct.pack('<I',index))
    cases.append({'scenario':scenario,'original_constructor_accepted':bool(accepted),'constructor_statistics':list(stats[:6]),'bytes':len(wire),'wire_sha256':hashlib.sha256(wire).hexdigest(),'allocated_sets':len(names),'power_references':sum(len(r['fields'][21])for r in decoded['rows']),'pointer_indices':sum(len(r['fields'][22])for r in decoded['rows']),'original_slots_sha256':hashlib.sha256(bytes(slots)).hexdigest(),'first_winner_indices_sha256':hashlib.sha256(bytes(indices)[:4*len(names)]).hexdigest()})
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else[]):
   exe=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,HERE/'test_power_sets.c','-lcrypto','-o',exe]);checks[mode]=json.loads(run([exe,fixture],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(exe)
  cpp=work/'header.cpp';cpp.write_text('#include "coh_power_sets.h"\nint main(){return coh_power_sets_find(nullptr,CohBytes{nullptr,0},nullptr)==COH_INVALID?0:1;}\n');objects=[]
  for i,source in enumerate(sources):
   obj=work/('cpp'+str(i)+'.o');run(['cc','-std=c99','-O2','-c',source,'-o',obj]);objects.append(obj)
  run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-o',work/'cpp']);run([work/'cpp'])
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    loc,n,kind=line.split('\t')
    if any(str(source)+':'in loc for source in sources):stack.append({'function':loc,'bytes':int(n),'kind':kind})
  assert stack and all(x['kind']in('static','dynamic,bounded')for x in stack)and sum(x['bytes']for x in stack)<16384;fixture_sha=sha(fixture)
 if hashes!={str(p.resolve().relative_to(ROOT)):sha(p.resolve())for p in sorted(paths)}:raise ValueError('source changed')
 assert all(x==checks['release']for x in checks.values())
 result={'schema':'coh-original-power-sets-compact-v1','passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).strip(),'source_sha256':hashes,'original':proof,'original_schema_crc':'0x2fe0d52d','exact_input_bytes':len(raw),'exact_input_sha256':hashlib.sha256(raw).hexdigest(),'cases':cases,'checks':checks,'binary_sha256':binaries,'native_stack':stack,'fixture_sha256':fixture_sha,'helper_loader_controls':loader,'cpp_link_passed':True,'source_set_dictionary_only':True,'category_reference_audit':association,'runtime_generation':False,'actor_authority':False,'original_hash_sanitized':False,'original_win32_abi_executed':False,'android_executed':False}
 with a.output.open('xb')as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0)as z:z.write((json.dumps(result,indent=2)+'\n').encode())
 print(json.dumps({'passed':True,'checks':checks,'cases':len(cases)}))
if __name__=='__main__':main()
