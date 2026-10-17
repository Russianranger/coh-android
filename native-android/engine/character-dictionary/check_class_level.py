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
def projection(raw,entry,level,order):
 def scalar(index,default):
  begin,end=entry['fields'][index];n=struct.unpack_from('<I',raw,begin)[0]
  if not n:assert end==begin+4;return [default]*115
  assert n==1 and end-begin==468 and struct.unpack_from('<I',raw,begin+4)[0]==460
  return list(struct.unpack_from('<115I',raw,begin+8))
 rows=[];levels=0
 for index in range(27,31):
  begin,end=entry['fields'][index];n,size=struct.unpack_from('<II',raw,begin);assert n==1 and end==begin+8+size;at=begin+8;row=[0x3f800000]*115
  for j in range(115):
   n=struct.unpack_from('<I',raw,at)[0];at+=4;values=struct.unpack_from('<'+'I'*n,raw,at);at+=4*n
   if index==28 and j==20:levels=n
   row[order[j]]=values[min(level,n-1)]if n else 0x3f800000
  assert at==end;rows.append(row)
 return levels,rows+[scalar(19,0),scalar(20,0xc2c80000)]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--cache-zip',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 if not __debug__:raise ValueError('assertion controls required')
 helpers=[HERE/p for p in ('class_repack_oracle.py','classes_oracle.py','classes_independent.py','class_schema.py','origins_oracle.py','power_categories_independent.py','../costume-inputs/oracle.py','../costume-inputs/source-pins.json','../costume-inputs/coh_costume_inputs.h','../costume-tree/crc_provider.py')];LOCKED.update({p.resolve():sha(p.resolve())for p in helpers});oracle=module('level_original',helpers[0]);oracle.module=module;classes=module('level_classes',helpers[1]);ind=module('level_ind',helpers[2]);schema=module('level_schema',helpers[3]);origin=module('level_origin',helpers[4]);category=module('level_categories',helpers[5]);small=module('level_small',helpers[6]);crc=module('level_crc',helpers[9]);sourcepaths=[ROOT/'upstream/ouroboros'/p for p in set(oracle.EXTRA+classes.EXTRA+origin.EXTRA+small.PATHS+crc.PATHS)];sources=[HERE/p for p in ('coh_class_level.c','coh_classes.c','coh_power_categories.c')];paths=set(helpers+sourcepaths+sources+[HERE/p for p in ('coh_class_level.h','test_class_level.c','check_class_level.py','CLASS_LEVEL.md')]);pending=[*sources,HERE/'test_class_level.c',helpers[8]];seen=set()
 while pending:
  p=pending.pop().resolve()
  if p in seen:continue
  seen.add(p);paths.add(p)
  for name in re.findall(r'^#include "([^"]+)"',p.read_text(),re.M):
   q=(p.parent/name).resolve()
   if q.is_file():pending.append(q)
 hashes={str(p.resolve().relative_to(ROOT)):sha(p.resolve())for p in sorted(paths)}
 if a.cache_zip.stat().st_size!=27071659 or sha(a.cache_zip)!='5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051':raise ValueError('donor identity')
 with zipfile.ZipFile(a.cache_zip)as z:
  cats=z.read('data/bin/powercats.bin');raws=[z.read('data/bin/'+n)for n in ('classes.bin','villain_classes.bin')]
 assert hashlib.sha256(cats).hexdigest()=='67b46915b9bf4440de8f5cf8bf7dd4a9047daee7dc5cb96f2c2be3999f8fc5e7'
 assert [hashlib.sha256(b).hexdigest()for b in raws]==['91af1ca0b304d77e56f356d54e1a880309b910c40f1729672cc0af1b83dd6733','bc0789f03941d845f9574f6df4dd1ad953ad35328a3d7323c07d02d92fdbd523']
 names=[r['fields'][1]for r in category.decode(cats)['rows']];nameargs=(C.c_char_p*len(names))(*[n.encode()for n in names]);tables,tablepins,_=schema.schema({p:read(ROOT/'upstream/ouroboros'/p).decode()for p,n in schema.TABLES});checks={};cases=[];stack=[];binaries={};indices=[next(i for i,x in enumerate(tables[2])if x['name']==field['name'])for field in tables[3]];expected='/* Exact original scalar-schema indices for original table-schema fields. */\nstatic const uint8_t attribute_order[115]={'+','.join(map(str,indices))+'};\n';assert (HERE/'class_level_order.inc').read_text()==expected
 with tempfile.TemporaryDirectory(prefix='coh-class-level-')as tmp:
  work=Path(tmp);loader=controls(work);originalroot=work/'source'
  for p in sourcepaths:
   q=originalroot/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(read(p))
  ow=work/'original';ow.mkdir();lib,proof=oracle.build(originalroot,ow);fixture=work/'fixtures.bin'
  with fixture.open('xb')as f:
   f.write(struct.pack('<I',len(cats)));f.write(cats);f.write(struct.pack('<I',8));variantraws=[]
   for fi,original in enumerate(raws):
    variantraws.append((fi,0,original));begin=ind.decode(original,tables)['begin']
    for variant in range(1,4):
     buf=C.create_string_buffer(8388608);size=lib.original_repack_variant(original,len(original),begin,variant,buf);assert size;variantraws.append((fi,variant,buf.raw[:size]))
   for fi,variant,raw in variantraws:
    decoded=ind.decode(raw,tables);n=1 if variant else len(decoded['entries']);f.write(struct.pack('<I',len(raw)));f.write(raw);f.write(struct.pack('<I',n*3))
    for which in range(n):
     values=(C.c_uint*690)();meta=(C.c_uint*16)();assert lib.original_class_repack(raw,len(raw),decoded['begin'],which,0,0,nameargs,len(names),values,meta);levels=meta[0]
     for level in (0,levels//2,levels-1):
      assert lib.original_class_repack(raw,len(raw),decoded['begin'],which,level,0,nameargs,len(names),values,meta);project_levels,projected=projection(raw,decoded['entries'][which],level,indices);assert project_levels==meta[0] and [w for row in projected for w in row]==list(values);f.write(struct.pack('<IIII4I',which,level,meta[0],meta[1],*meta[3:7]));f.write(bytes(values));cases.append({'file':fi,'variant':variant,'class_index':which,'level':level,'levels':levels,'table_bytes':meta[1],'category_indices':list(meta[3:7]),'words_sha256':hashlib.sha256(bytes(values)).hexdigest()})
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else[]):
   exe=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,HERE/'test_class_level.c','-lcrypto','-o',exe]);checks[mode]=json.loads(run([exe,fixture],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(exe)
  cpp=work/'header.cpp';cpp.write_text('#include "coh_class_level.h"\nint main(){return coh_class_level_read(nullptr,nullptr,0,0,nullptr,nullptr,1,0)==COH_INVALID?0:1;}\n');objects=[]
  for i,source in enumerate(sources):
   obj=work/('cpp'+str(i)+'.o');run(['cc','-std=c99','-O2','-c',source,'-o',obj]);objects.append(obj)
  run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-o',work/'cpp']);run([work/'cpp'])
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    loc,n,kind=line.split('\t')
    if str(sources[0])+':'in loc:stack.append({'function':loc,'bytes':int(n),'kind':kind})
  assert stack and all(x['kind']in('static','dynamic,bounded')for x in stack)and sum(x['bytes']for x in stack)<16384;fixture_sha=sha(fixture)
 if hashes!={str(p.resolve().relative_to(ROOT)):sha(p.resolve())for p in sorted(paths)}:raise ValueError('source changed')
 assert all(x==checks['release']for x in checks.values())
 result={'schema':'coh-original-class-selected-level-v1','passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).strip(),'source_sha256':hashes,'original':proof,'cases':cases,'checks':checks,'binary_sha256':binaries,'native_stack':stack,'cpp_link_passed':True,'independent_all_690_words_per_case':True,'fixture_sha256':fixture_sha,'helper_loader_controls':loader,'runtime_generation':False,'actor_authority':False,'original_win32_abi_executed':False,'android_executed':False}
 with a.output.open('xb')as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0)as z:z.write((json.dumps(result,indent=2)+'\n').encode())
 print(json.dumps({'passed':True,'checks':checks,'cases':len(cases)}))
if __name__=='__main__':main()
