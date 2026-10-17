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
def named_rows(raw,decoded):
 rows=[]
 for i,m in enumerate(decoded['modtables']):
  name=decoded['texts'][m['name_text']]['text'];begin,end=m['record'];n=struct.unpack_from('<H',raw,begin+4)[0];at=begin+6+n+(4-(n+2)%4)%4;count=struct.unpack_from('<I',raw,at)[0];at+=4;assert at+count*4==end;values=list(struct.unpack_from('<'+'I'*count,raw,at));rows.append({'class':m['owner'],'index':i,'name':name,'values':values})
 return rows
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--cache-zip',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 if not __debug__:raise ValueError('assertion controls required')
 helpers=[HERE/p for p in ('class_named_oracle.py','classes_oracle.py','classes_independent.py','class_schema.py','origins_oracle.py','../stash32/oracle.py','../costume-inputs/oracle.py','../costume-inputs/source-pins.json','../costume-inputs/coh_costume_inputs.h','../costume-tree/crc_provider.py','../stash32/source-pins.json')];LOCKED.update({p.resolve():sha(p.resolve())for p in helpers});oracle=module('named_original',helpers[0]);oracle.module=module;classes=module('named_classes',helpers[1]);ind=module('named_ind',helpers[2]);schema=module('named_schema',helpers[3]);origin=module('named_origin',helpers[4]);stash=module('named_stash',helpers[5]);small=module('named_small',helpers[6]);crc=module('named_crc',helpers[9]);sourcepaths=[ROOT/'upstream/ouroboros'/p for p in set(oracle.EXTRA+classes.EXTRA+origin.EXTRA+small.PATHS+crc.PATHS+stash.PATHS)];sources=[HERE/p for p in ('coh_class_named.c','coh_classes.c')];paths=set(helpers+sourcepaths+sources+[HERE/p for p in ('coh_class_named.h','test_class_named.c','check_class_named.py','CLASS_NAMED.md')]);pending=[*sources,HERE/'test_class_named.c',helpers[8]];seen=set()
 while pending:
  p=pending.pop().resolve()
  if p in seen:continue
  seen.add(p);paths.add(p)
  for name in re.findall(r'^#include "([^"]+)"',p.read_text(),re.M):
   q=(p.parent/name).resolve()
   if q.is_file():pending.append(q)
 hashes={str(p.resolve().relative_to(ROOT)):sha(p.resolve())for p in sorted(paths)}
 if a.cache_zip.stat().st_size!=27071659 or sha(a.cache_zip)!='5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051':raise ValueError('donor identity')
 with zipfile.ZipFile(a.cache_zip)as z:raws=[z.read('data/bin/'+n)for n in ('classes.bin','villain_classes.bin')]
 assert [hashlib.sha256(b).hexdigest()for b in raws]==['91af1ca0b304d77e56f356d54e1a880309b910c40f1729672cc0af1b83dd6733','bc0789f03941d845f9574f6df4dd1ad953ad35328a3d7323c07d02d92fdbd523']
 tables,_,_=schema.schema({p:read(ROOT/'upstream/ouroboros'/p).decode()for p,n in schema.TABLES});checks={};cases=[];stack=[];binaries={};query_count=0
 with tempfile.TemporaryDirectory(prefix='coh-class-named-')as tmp:
  work=Path(tmp);loader=controls(work);originalroot=work/'source'
  for p in sourcepaths:
   q=originalroot/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(read(p))
  ow=work/'original';ow.mkdir();lib,proof=oracle.build(originalroot,ow);fixture=work/'fixtures.bin';variants=[]
  for fi,raw in enumerate(raws):
   variants.append((fi,0,raw));begin=ind.decode(raw,tables)['begin']
   for variant in range(1,7):
    buf=C.create_string_buffer(8388608);n=lib.original_named_variant(raw,len(raw),begin,variant,buf);assert n;variants.append((fi,variant,buf.raw[:n]))
  with fixture.open('xb')as f:
   f.write(struct.pack('<I',len(variants)))
   for fi,variant,raw in variants:
    decoded=ind.decode(raw,tables);rows=named_rows(raw,decoded);stats=(C.c_uint*8)();accepted=lib.original_named_open(raw,len(raw),decoded['begin'],stats);duplicates=sum(1 for i,r in enumerate(rows)if any(p['class']==r['class']and p['name'].lower()==r['name'].lower()for p in rows[:i]));assert stats[0]==len(decoded['entries'])and stats[1]==duplicates and stats[2]==len(rows)and stats[4]==len(rows)-duplicates and accepted==int(not duplicates);work_cost=sum(1+(len(r['name'])if len(r['name'])==len(p['name'])else 0)for i,r in enumerate(rows)for p in rows[:i]if p['class']==r['class']);assert (work_cost>8388608)==(variant==6);status=7 if duplicates else 4 if variant==6 else 0;queries=[]
    if not status:
     for r in rows:
      if variant and r['class']!=0:continue
      name=r['name'].lower();values=r['values']
      for index in (0,len(values)//2,max(0,len(values)-1),0x7fffffff):
       present=C.c_uint();count=C.c_uint();word=0;expected_status=0
       if not values:expected_status=2
       else:word=lib.original_named_value(r['class'],name.encode(),index,C.byref(present),C.byref(count));assert present.value==1 and count.value==len(values)and word==values[min(index,len(values)-1)]
       queries.append((r['class'],name,index,expected_status,word,1,r['index'],min(index,len(values)-1)))
     for which in range(len(decoded['entries'])):
      present=C.c_uint();count=C.c_uint();name='unknown_missing_named_table';value=lib.original_named_value(which,name.encode(),0,C.byref(present),C.byref(count));assert not present.value and not count.value and value==0x3f800000;queries.append((which,name,0,0,value,0,0xffffffff,0xffffffff))
    lib.original_named_close();f.write(struct.pack('<II',len(raw),status));f.write(raw);f.write(struct.pack('<I',len(queries)))
    for which,name,index,st,value,found,table,applied in queries:
     b=name.encode();f.write(struct.pack('<II',which,len(b)));f.write(b);f.write(struct.pack('<6I',index,st,value,found,table,applied&0xffffffff))
    cases.append({'file':fi,'variant':variant,'bytes':len(raw),'wire_sha256':hashlib.sha256(raw).hexdigest(),'native_expected_status':status,'source_constructor_accepted':bool(accepted),'constructor_statistics':list(stats[:5]),'empty_rows':sum(not r['values']for r in rows),'comparison_work_bound_control':variant==6,'independent_comparison_work_cost':work_cost,'queries':len(queries),'query_projection_sha256':hashlib.sha256(json.dumps(queries).encode()).hexdigest()});query_count+=len(queries)
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else[]):
   exe=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,HERE/'test_class_named.c','-lcrypto','-o',exe]);checks[mode]=json.loads(run([exe,fixture],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(exe)
  cpp=work/'header.cpp';cpp.write_text('#include "coh_class_named.h"\nint main(){return coh_class_named_prepare(nullptr,nullptr,1,0)==COH_INVALID?0:1;}\n');objects=[]
  for i,source in enumerate(sources):
   obj=work/('cpp'+str(i)+'.o');run(['cc','-std=c99','-O2','-c',source,'-o',obj]);objects.append(obj)
  run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-o',work/'cpp']);run([work/'cpp'])
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    loc,n,kind=line.split('\t')
    if str(sources[0])+':'in loc:stack.append({'function':loc,'bytes':int(n),'kind':kind})
  assert stack and all(x['kind']in('static','dynamic,bounded')for x in stack)and sum(x['bytes']for x in stack)<8192;fixture_sha=sha(fixture)
 if hashes!={str(p.resolve().relative_to(ROOT)):sha(p.resolve())for p in sorted(paths)}:raise ValueError('source changed')
 assert all(x==checks['release']for x in checks.values())
 result={'schema':'coh-original-class-named-tables-v1','passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).strip(),'source_sha256':hashes,'original':proof,'cases':cases,'queries':query_count,'checks':checks,'binary_sha256':binaries,'native_stack':stack,'cpp_link_passed':True,'fixture_sha256':fixture_sha,'helper_loader_controls':loader,'runtime_generation':False,'actor_authority':False,'original_win32_abi_executed':False,'android_executed':False}
 with a.output.open('xb')as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0)as z:z.write((json.dumps(result,indent=2)+'\n').encode())
 print(json.dumps({'passed':True,'checks':checks,'cases':len(cases)}))
if __name__=='__main__':main()
