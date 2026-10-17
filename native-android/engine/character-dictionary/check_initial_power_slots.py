#!/usr/bin/env python3
"""Fresh empty-slot construction only; authentic historical definitions, no authority."""
import argparse,ctypes as C,gzip,hashlib,json,os,re,struct,tempfile,types,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];LOCKED={}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  while b:=f.read(65536):h.update(b)
 return h.hexdigest()
def module(n,p):
 p=p.resolve();body=p.read_bytes()
 if LOCKED.get(p)!=hashlib.sha256(body).hexdigest():raise ValueError('helper source not admitted '+str(p))
 m=types.ModuleType(n);m.__file__=str(p);exec(compile(body,str(p),'exec'),m.__dict__);return m
def fields(raw,tables):
 at=0;maximum=allowed=None
 def word():
  nonlocal at
  n=struct.unpack_from('<I',raw,at)[0];at+=4;return n
 def text():
  nonlocal at
  n=struct.unpack_from('<H',raw,at)[0];at+=(n+5)//4*4
 def record(table):
  nonlocal at,maximum,allowed
  end=at+4+word()
  for i,f in enumerate(tables[table]):
   k=f['kind']
   if k==1:text()
   elif k in(3,5,9):
    n=word()
    if table==0 and i==93:maximum=n if n<0x80000000 else n-0x100000000
   elif k==2:
    for _ in range(word()):text()
   elif k==4:
    n=word()
    if table==0 and i==80:allowed=n
    at+=4*n
   elif k==6:
    for _ in range(word()):record(f['sub'])
   elif k==7:at+=12
   elif k==8:at+=16
   else:raise ValueError(k)
   assert at<=end
  assert at==end
 record(0);assert at==len(raw)and maximum is not None and allowed is not None;return maximum,allowed
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cache-zip',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 if not __debug__:raise ValueError('assertions required')
 names=('initial_power_slots_oracle.py','boost_slots_oracle.py','check_power_boost_slots.py','power_record_oracle.py','classes_oracle.py','origins_oracle.py','power_stream_schema.py','../costume-inputs/oracle.py','../costume-inputs/source-pins.json','../costume-inputs/coh_costume_inputs.h','../costume-tree/crc_provider.py');helpers=[HERE/p for p in names];LOCKED.update({p.resolve():sha(p)for p in helpers});oracle=module('initial_original',helpers[0]);oracle.module=module;base=module('initial_base',helpers[2]);base.LOCKED=LOCKED;base.module=module;run=base.run;words=base.words;pascal=base.pascal;segment=base.segment;record=module('initial_record',helpers[3]);classes=module('initial_classes',helpers[4]);origin=module('initial_origin',helpers[5]);stream=module('initial_stream',helpers[6]);small=module('initial_small',helpers[7]);crc=module('initial_crc',helpers[10]);previous=module('initial_previous_extra',helpers[1]);sourcepaths=[ROOT/'upstream/ouroboros'/p for p in set(oracle.EXTRA+previous.EXTRA+record.EXTRA+classes.EXTRA+origin.EXTRA+stream.PATHS+small.PATHS+crc.PATHS)]
 sources=[HERE/p for p in('coh_initial_power_slots.c','coh_power_boost_slots.c','coh_schedules.c','coh_power_stream.c','../stash32/coh_stash32.c')];paths=set(helpers+sourcepaths+sources+[HERE/p for p in('test_initial_power_slots.c','check_initial_power_slots.py','INITIAL_POWER_SLOTS.md')]);pending=[*sources,HERE/'test_initial_power_slots.c',helpers[9]];seen=set()
 while pending:
  p=pending.pop().resolve()
  if p in seen:continue
  seen.add(p);paths.add(p)
  for name in re.findall(r'^#include "([^"]+)"',p.read_text(),re.M):
   q=(p.parent/name).resolve()
   if q.is_file():pending.append(q)
 hashes={str(p.resolve().relative_to(ROOT)):sha(p)for p in sorted(paths)}
 if a.cache_zip.stat().st_size!=27071659 or sha(a.cache_zip)!='5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051':raise ValueError('exact donor identity')
 cases=[];modes={};stack=[];actual_projections=hashlib.sha256();actual_slot_appends=0
 with tempfile.TemporaryDirectory(prefix='coh-initial-power-slots-')as tmp:
  work=Path(tmp);loader=base.controls(work);originalroot=work/'source'
  for p in sourcepaths:
   q=originalroot/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
  ow=work/'original';ow.mkdir();lib,proof=oracle.build(originalroot,ow);tables,pins=stream.schema({p:(originalroot/'upstream/ouroboros'/p).read_text()for p in stream.PATHS});assert tables[0][80]['name']=='BoostsAllowed'and tables[0][80]['source_token']=='INTARRAY';assert tables[0][93]['name']=='MaxBoosts';assert list(map(len,tables))==[180,63,3,4,47]
  descriptor=['/* Complete source-ordered persisted power table kinds; no schema CRC claim. */','typedef struct {unsigned char kind,sub;} PowerField;']
  for table,rows in enumerate(tables):descriptor.append('static const PowerField power_fields_%s[]={%s};'%(table,','.join('{%s,%s}'%(f['kind'],f['sub'])for f in rows)))
  descriptor+=['static const PowerField *const power_fields[]={'+','.join('power_fields_'+str(t)for t in range(5))+'};','static const unsigned power_field_counts[]={'+','.join(str(len(t))for t in tables)+'};'];assert(HERE/'power_stream_schema.inc').read_text()=='\n'.join(descriptor)+'\n'
  powerpath=work/'powers.bin'
  with zipfile.ZipFile(a.cache_zip)as z:
   schedules=z.read('data/bin/schedules.bin')
   with z.open('data/bin/powers.bin')as src,powerpath.open('xb')as dst:
    while chunk:=src.read(65536):dst.write(chunk)
  assert sha(powerpath)=='25641e747c60e066016fcc7d2ce0a2e72f57d7d3953f7b1ff4b18b69e2d49c6d'
  with powerpath.open('rb')as src:decoded=stream.inspect(src,powerpath.stat().st_size,tables)
  first=None;actual=[]
  with powerpath.open('rb')as src:
   for row in decoded['rows']:
    src.seek(row['begin']);raw=src.read(row['end']-row['begin']);assert len(raw)<=65536;first=first or raw;actual.append(fields(raw,tables))
  def cache(raw):return b'CrypticS'+words(decoded['schema_crc'])+pascal('Parse6')+pascal('Files1')+segment(words(0))+segment(words(1)+raw)
  scenarios=[('exact-historical',schedules,powerpath,actual,None)]
  for maximum,allowed in[(6,0),(6,1),(6,3),(0,1),(-1,1),(2147483647,1),(-2147483647,0),(-2147483647,1),(-2147483648,1)]:
   out=C.create_string_buffer(65536);n=lib.original_initial_variant(first,len(first),maximum,allowed,out);raw=out.raw[:n];assert fields(raw,tables)==(maximum,allowed);p=work/f'max-{maximum}-allowed-{allowed}.bin';p.write_bytes(cache(raw));scenarios.append((f'max-{maximum}-allowed-{allowed}',schedules,p,[(maximum,allowed)],raw))
  for name,thresholds in [('free-4096-bound',[0]*4096),('free-prefix-order',[-3,0,3,0]),('free-empty',[])]:
   out=C.create_string_buffer(65536);n=lib.original_initial_variant(first,len(first),2147483647,1,out);raw=out.raw[:n];p=work/(name+'.bin');p.write_bytes(cache(raw));scenarios.append((name,base.schedule_cache([thresholds]+[[]for _ in range(6)]),p,[(2147483647,1)],raw))
  args=[]
  for name,sraw,ppath,expectedfields,single in scenarios:
   spath=work/(name+'.schedules');spath.write_bytes(sraw);_,sfields=base.schedule_decode(sraw);sexpected=work/(name+'.schedule.expected');queries=[]
   with sexpected.open('xb')as dst:
    dst.write(words(sum(map(len,sfields))))
    for f in sfields:dst.write(words(len(f))+words(*f))
    for fi,f in enumerate(sfields):
     ptr=(C.c_int*len(f))(*f)
     for level in(-2147483648,-1,0,1,2,3,9,49,2147483647):queries.append((fi,level,lib.original_schedule_count(ptr,len(f),level)))
    dst.write(words(len(queries)))
    for q in queries:dst.write(words(*q))
    dst.write(words(0xabcdef01))
   expected=work/(name+'.expected');expectedcases=[];ptr=(C.c_int*len(sfields[0]))(*sfields[0]);safe=0;allowed_nonempty=0
   with ppath.open('rb')as src:
    for row,(maximum,allowed)in enumerate(expectedfields):
     if single is None:entry=decoded['rows'][row];src.seek(entry['begin']);raw=src.read(entry['end']-entry['begin'])
     else:raw=single
     variants=[((row*7)%61,(row*13)%70,row%9)]if single is None else[(0,0,0),(49,0,6),(0,49,2),(10,9,2048),(-1,0,1),(2147483647,2147483647,3)]
     for level,bought,wire in variants:
      free=0
      while free<len(sfields[0])and sfields[0][free]<=max(level-bought,0):free+=1
      purchased=max(0,wire-min(free,maximum));uncapped=purchased+free;ok=purchased<=2147483647 and uncapped<=2147483647;target=min(uncapped,maximum);slots=max(0,target)if allowed else 0
      if ok:
       values=(C.c_int*8)();lib.original_initial_power(raw,len(raw),ptr,len(sfields[0]),level,bought,wire,values);assert list(values)==[maximum,allowed,purchased,free,slots,0,1,target];safe+=1;allowed_nonempty+=bool(allowed)
       if single is None:actual_projections.update(bytes(values));actual_slot_appends+=slots
      else:
       values=(C.c_int*2)();lib.original_initial_fields(raw,len(raw),values);assert list(values)==[maximum,allowed]
      expectedcases.append((row,level,bought,wire,int(ok),maximum,allowed,free,purchased if purchased<=2147483647 else 0,target if ok else 0,slots if ok else 0))
   with expected.open('xb')as dst:
    dst.write(words(len(expectedcases)))
    for value in expectedcases:dst.write(words(*value))
    dst.write(words(0xabcdef01))
   args.append((spath,sexpected,ppath,expected,name));cases.append({'name':name,'schedule_sha256':sha(spath),'power_sha256':sha(ppath),'power_rows':len(expectedfields),'constructor_cases':len(expectedcases),'safe_original_constructor_executions':safe,'nonempty_BoostsAllowed_executions':allowed_nonempty,'signed_overflow_refusals':len(expectedcases)-safe,'expected_sha256':sha(expected)})
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else[]):
   exe=work/mode;run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,HERE/'test_initial_power_slots.c','-lcrypto','-o',exe]);modes[mode]={'binary_sha256':sha(exe),'checks':[json.loads(run([exe,*arg],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))for arg in args]}
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    loc,n,kind=line.split('\t')
    if any(x in loc for x in('coh_initial_power_slots.c:','coh_power_boost_slots.c:','coh_schedules.c:')):stack.append({'function':loc,'bytes':int(n),'kind':kind})
  assert stack and 4*sum(x['bytes']for x in stack)<16384 and all(x['kind']in('static','dynamic,bounded')for x in stack)
  cpp=work/'header.cpp';cpp.write_text('#include "coh_initial_power_slots.h"\nint main(){return coh_initial_power_slots_create(nullptr,nullptr,0,0,0,0,nullptr,nullptr,0,0)==COH_INVALID?0:1;}\n');objects=[]
  for i,source in enumerate(sources):obj=work/f'cpp-{i}.o';run(['cc','-std=c11','-O2','-c',source,'-o',obj]);objects.append(obj)
  run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-o',work/'cpp']);run([work/'cpp']);lib.original_power_records_close()
 assert all(sha(ROOT/p)==h for p,h in hashes.items()),'source changed';assert all(v['checks']==modes['release']['checks']for v in modes.values())
 result={'schema':'coh-historical-fresh-power-slots-v1','passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).strip(),'source_sha256':hashes,'original':proof,'source_descriptor_sha256_lf':pins,'descriptor_regenerated_exactly':True,'actual_original_constructors':len(actual),'actual_original_slot_append_calls':actual_slot_appends,'actual_original_constructor_projection_sha256':actual_projections.hexdigest(),'cases':cases,'modes':modes,'native_stack':stack,'conservative_new_and_callee_stack_sum_times4':4*sum(x['bytes']for x in stack),'cpp_link_passed':True,'helper_loader_controls':loader,'fresh_empty_slot_container_only':True,'runtime_generation':False,'actor_authority':False,'reused_or_temporary_duplicate_branch_selected':False,'whole_character_ReceivePowers_executed':False,'boost_objects_applied':False,'current_loader_generation_admitted':False,'original_win32_abi_executed':False,'android_executed':False,'original_oracle_sanitized':False,'lsan_executed':False}
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open('xb')as dst:
  with gzip.GzipFile(fileobj=dst,mode='wb',mtime=0)as gz:gz.write((json.dumps(result,indent=2)+'\n').encode())
 print(json.dumps({'passed':True,'cases':len(cases),'checks_per_mode':sum(x['checks']for x in modes['release']['checks']),'original_constructors':len(actual)}))
if __name__=='__main__':main()
