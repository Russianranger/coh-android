#!/usr/bin/env python3
"""Bounded historical schedules and ReceivePowers boost-slot source closure."""
import argparse,ctypes as C,gzip,hashlib,io,json,os,re,struct,subprocess,tempfile,types,zipfile,py_compile
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
def run(args,**kw):
 r=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=240,**kw)
 if r.returncode:raise RuntimeError(str(args)+'\n'+r.stdout[-5000:]+r.stderr[-6000:])
 return r.stdout
def controls(work):
 p=work/'stale.py';p.write_text('value=1\n');py_compile.compile(str(p),doraise=True);st=p.stat();p.write_text('value=2\n');os.utime(p,ns=(st.st_atime_ns,st.st_mtime_ns));LOCKED[p.resolve()]=sha(p);assert module('stale',p).value==2;p.write_text('value=3\n')
 try:module('changed',p)
 except ValueError:pass
 else:raise ValueError('changed helper executed')
 LOCKED.pop(p.resolve());return {'stale_pyc_ignored':True,'changed_source_refused':True}
def words(*v):return struct.pack('<'+'I'*len(v),*[x&0xffffffff for x in v])
def pascal(s):
 b=s.encode();return struct.pack('<H',len(b))+b+bytes((4-(len(b)+2)%4)%4)
def segment(b):return words(len(b))+b
def schedule_cache(fields):return b'CrypticS'+words(0x9f2a61e2)+pascal('Parse6')+pascal('Files1')+segment(words(0))+segment(segment(b''.join(words(len(f))+words(*f)for f in fields)))
def schedule_decode(raw):
 at=12
 def u32():
  nonlocal at
  v=struct.unpack_from('<I',raw,at)[0];at+=4;return v
 def text():
  nonlocal at
  n=struct.unpack_from('<H',raw,at)[0];s=raw[at+2:at+2+n];at+=(n+5)//4*4;return s
 assert raw[:8]==b'CrypticS'and struct.unpack_from('<I',raw,8)[0]==0x9f2a61e2;assert text()==b'Parse6'and text()==b'Files1';end=at+4+u32();n=u32()
 for _ in range(n):text();u32()
 assert at==end;begin=at;assert at+4+u32()==len(raw);assert at+4+u32()==len(raw);fields=[]
 for _ in range(7):
  n=u32();values=list(struct.unpack_from('<'+'i'*n,raw,at));at+=4*n;fields.append(values)
 assert at==len(raw);return begin,fields
def maxboosts(raw,tables):
 at=0;maximum=None
 def u32():
  nonlocal at
  n=struct.unpack_from('<I',raw,at)[0];at+=4;return n
 def text():
  nonlocal at
  n=struct.unpack_from('<H',raw,at)[0];at+=(n+5)//4*4
 def record(table):
  nonlocal at,maximum
  end=at+4+u32()
  for i,f in enumerate(tables[table]):
   k=f['kind']
   if k==1:text()
   elif k in(3,5,9):
    v=u32()
    if table==0 and i==93:maximum=v if v<0x80000000 else v-0x100000000
   elif k==2:
    for _ in range(u32()):text()
   elif k==4:
    n=u32();at+=4*n
   elif k==6:
    for _ in range(u32()):record(f['sub'])
   elif k==7:at+=12
   elif k==8:at+=16
   else:raise ValueError(k)
   assert at<=end
  assert at==end
 record(0);assert at==len(raw)and maximum is not None;return maximum
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cache-zip',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 if not __debug__:raise ValueError('assertions required')
 helpers=[HERE/p for p in ('boost_slots_oracle.py','power_record_oracle.py','classes_oracle.py','origins_oracle.py','power_stream_schema.py','../costume-inputs/oracle.py','../costume-inputs/source-pins.json','../costume-inputs/coh_costume_inputs.h','../costume-tree/crc_provider.py')];LOCKED.update({p.resolve():sha(p)for p in helpers});oracle=module('boost_original',helpers[0]);oracle.module=module;record=module('boost_record',helpers[1]);classes=module('boost_classes',helpers[2]);origin=module('boost_origin',helpers[3]);stream=module('boost_stream',helpers[4]);small=module('boost_small',helpers[5]);crc=module('boost_crc',helpers[8]);sourcepaths=[ROOT/'upstream/ouroboros'/p for p in set(oracle.EXTRA+record.EXTRA+classes.EXTRA+origin.EXTRA+small.PATHS+crc.PATHS)];sources=[HERE/p for p in ('coh_schedules.c','coh_power_boost_slots.c','coh_power_stream.c','../stash32/coh_stash32.c')];paths=set(helpers+sourcepaths+sources+[HERE/p for p in ('test_power_boost_slots.c','check_power_boost_slots.py','POWER_BOOST_SLOTS.md')]);pending=[*sources,HERE/'test_power_boost_slots.c',helpers[7]];seen=set()
 while pending:
  p=pending.pop().resolve()
  if p in seen:continue
  seen.add(p);paths.add(p)
  for name in re.findall(r'^#include "([^"]+)"',p.read_text(),re.M):
   q=(p.parent/name).resolve()
   if q.is_file():pending.append(q)
 hashes={str(p.resolve().relative_to(ROOT)):sha(p)for p in sorted(paths)}
 if a.cache_zip.stat().st_size!=27071659 or sha(a.cache_zip)!='5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051':raise ValueError('donor identity')
 cases=[];modes={};stack=[]
 with tempfile.TemporaryDirectory(prefix='coh-boost-slots-')as tmp:
  work=Path(tmp);loader=controls(work);originalroot=work/'source'
  for p in sourcepaths:
   q=originalroot/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
  ow=work/'original';ow.mkdir();lib,proof=oracle.build(originalroot,ow);lib.original_schedules_crc.restype=C.c_uint;assert lib.original_schedules_crc()==0x9f2a61e2;tables,pins=stream.schema({p:(originalroot/'upstream/ouroboros'/p).read_text()for p in stream.PATHS});assert tables[0][93]['name']=='MaxBoosts'and tables[0][93]['source_token']=='INT';assert list(map(len,tables))==[180,63,3,4,47]
  descriptor=['/* Complete source-ordered persisted power table kinds; no schema CRC claim. */','typedef struct {unsigned char kind,sub;} PowerField;']
  for table,rows in enumerate(tables):descriptor.append('static const PowerField power_fields_%s[]={%s};'%(table,','.join('{%s,%s}'%(f['kind'],f['sub'])for f in rows)))
  descriptor+=['static const PowerField *const power_fields[]={'+','.join('power_fields_'+str(t)for t in range(5))+'};','static const unsigned power_field_counts[]={'+','.join(str(len(t))for t in tables)+'};'];assert(HERE/'power_stream_schema.inc').read_text()=='\n'.join(descriptor)+'\n'
  powerpath=work/'powers.bin'
  with zipfile.ZipFile(a.cache_zip)as z:
   schedules=z.read('data/bin/schedules.bin')
   with z.open('data/bin/powers.bin')as src,powerpath.open('xb')as dst:
    while chunk:=src.read(65536):dst.write(chunk)
  assert sha(powerpath)=='25641e747c60e066016fcc7d2ce0a2e72f57d7d3953f7b1ff4b18b69e2d49c6d';begin,actualfields=schedule_decode(schedules)
  with powerpath.open('rb')as src:decoded=stream.inspect(src,powerpath.stat().st_size,tables)
  maxima=[];first=None
  with powerpath.open('rb')as src:
   for row in decoded['rows']:
    src.seek(row['begin']);raw=src.read(row['end']-row['begin']);assert len(raw)<=65536;first=first or raw;maximum=lib.original_power_maxboosts(raw,len(raw));assert maximum==maxboosts(raw,tables);maxima.append(maximum)
  singleton=work/'singleton.bin';singleton.write_bytes(b'CrypticS'+words(decoded['schema_crc'])+pascal('Parse6')+pascal('Files1')+segment(words(0))+segment(words(1)+first))
  scenarios=[('exact-historical',schedules,powerpath,maxima),('empty-arrays',schedule_cache([[]for _ in range(7)]),singleton,[maxima[0]]),('ordered-prefix-duplicates-unsorted',schedule_cache([[-3,0,0,3,1,9]]+[[]for _ in range(6)]),singleton,[maxima[0]]),('signed-thresholds',schedule_cache([[-2147483648,-1,0,2147483647]]+[[]for _ in range(6)]),singleton,[maxima[0]]),('aggregate-4096-bound',schedule_cache([[0]*4096]+[[]for _ in range(6)]),singleton,[maxima[0]])]
  for maximum in (-2147483648,-1,0,1,6,2147483647):
   out=C.create_string_buffer(65536);n=lib.original_power_maxboosts_variant(first,len(first),maximum,out);raw=out.raw[:n];assert lib.original_power_maxboosts(raw,n)==maxboosts(raw,tables)==maximum;p=work/('max'+str(maximum)+'.bin');p.write_bytes(b'CrypticS'+words(decoded['schema_crc'])+pascal('Parse6')+pascal('Files1')+segment(words(0))+segment(words(1)+raw));scenarios.append(('maxboosts-'+str(maximum),schedules,p,[maximum]))
  args=[]
  for name,sraw,ppath,maxvalues in scenarios:
   spath=work/(name+'.schedules');spath.write_bytes(sraw);sbegin,fields=schedule_decode(sraw);out=C.create_string_buffer(65536);values=(C.c_uint*4103)();n=lib.original_schedules(sraw,len(sraw),sbegin,out,values);assert out.raw[:n]==sraw;assert list(values[:7])==list(map(len,fields));assert list(values[7:7+sum(map(len,fields))])==[v&0xffffffff for f in fields for v in f]
   sexpected=work/(name+'.schedule.expected');queries=[]
   with sexpected.open('xb')as dst:
    dst.write(words(sum(map(len,fields))))
    for f in fields:dst.write(words(len(f))+words(*f))
    for fi,f in enumerate(fields):
     ptr=(C.c_int*len(f))(*f)
     for level in (-2147483648,-1,0,1,2,3,5,9,49,2147483647):
      count=0
      while count<len(f)and f[count]<=max(level,0):count+=1
      assert lib.original_schedule_count(ptr,len(f),level)==count;queries.append((fi,level,count))
    dst.write(words(len(queries)))
    for q in queries:dst.write(words(*q))
    dst.write(words(0xabcdef01))
   expected=work/(name+'.expected');expectedcases=[];ptr=(C.c_int*len(fields[0]))(*fields[0]);safe=0
   for row,maximum in enumerate(maxvalues):
    variants=[((row*7)%61,(row*13)%70,row%9)]if len(maxvalues)>1 else[(0,0,0),(49,0,6),(0,49,2),(10,9,2048),(-1,0,1),(2147483647,2147483647,3)]
    for level,bought,wire in variants:
     free=lib.original_schedule_count(ptr,len(fields[0]),level-bought);allowed=min(free,maximum);purchased=max(0,wire-allowed);ok=purchased<=2147483647
     if ok:
      source=(C.c_int*2)();assert lib.original_slot_arithmetic(ptr,len(fields[0]),level,bought,maximum,wire,source);assert list(source)==[allowed,purchased];safe+=1
     expectedcases.append((row,level,bought,wire,int(ok),maximum,free,allowed,purchased if ok else 0))
   with expected.open('xb')as dst:
    dst.write(words(len(expectedcases)))
    for v in expectedcases:dst.write(words(*v))
    dst.write(words(0xabcdef01))
   args.append((spath,sexpected,ppath,expected,name));cases.append({'name':name,'schedule_sha256':sha(spath),'schedule_words':sum(map(len,fields)),'power_sha256':sha(ppath),'power_rows':len(maxvalues),'arithmetic_cases':len(expectedcases),'safe_original_scalar_executions':safe,'overflow_refusals':len(expectedcases)-safe,'expected_sha256':sha(expected)})
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else[]):
   exe=work/mode;run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,HERE/'test_power_boost_slots.c','-lcrypto','-o',exe]);modes[mode]={'binary_sha256':sha(exe),'checks':[json.loads(run([exe,*arg],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))for arg in args]}
  for path in work.glob('*.su'):
   for line in path.read_text().splitlines():
    loc,n,kind=line.split('\t')
    if any(x in loc for x in('coh_schedules.c:','coh_power_boost_slots.c:')):stack.append({'function':loc,'bytes':int(n),'kind':kind})
  # record() recursion is source-descriptor bounded at4 frames. Conservatively
  # multiply the sum of every new function by4, including mutually exclusive ones.
  assert stack and 4*sum(s['bytes']for s in stack)<8192 and all(s['kind']in('static','dynamic,bounded')for s in stack)
  cpp=work/'header.cpp';cpp.write_text('#include "coh_power_boost_slots.h"\nint main(){return coh_power_boost_slots_prepare(nullptr,nullptr,0,0,0,0,nullptr,nullptr,0,0)==COH_INVALID?0:1;}\n');objects=[]
  for i,source in enumerate(sources):obj=work/f'cpp-{i}.o';run(['cc','-std=c11','-O2','-c',source,'-o',obj]);objects.append(obj)
  run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-o',work/'cpp']);run([work/'cpp']);lib.original_power_records_close()
 assert all(sha(ROOT/p)==h for p,h in hashes.items()),'source changed during execution';assert all(v['checks']==modes['release']['checks']for v in modes.values())
 result={'schema':'coh-historical-power-boost-slots-v1','passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).strip(),'source_sha256':hashes,'original':proof,'source_descriptor_sha256_lf':pins,'source_descriptor_regenerated_exactly':True,'original_schedules_schema_crc':'0x9f2a61e2','original_MaxBoosts_record_reads':len(maxima),'MaxBoosts_words_sha256':hashlib.sha256(words(*maxima)).hexdigest(),'cases':cases,'modes':modes,'native_stack':stack,'stack_conservative_new_module_sum_times4':4*sum(s['bytes']for s in stack),'cpp_link_passed':True,'helper_loader_controls':loader,'runtime_generation':False,'actor_authority':False,'whole_character_ReceivePowers_executed':False,'power_LevelFinalize_executed':False,'current_cache_loader_branch_executed':False,'android_executed':False,'original_win32_abi_executed':False,'external_crypto_library_stack_sanitizer_closure':False,'original_oracle_sanitized':False,'lsan_executed':False}
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open('xb')as dst:
  with gzip.GzipFile(fileobj=dst,mode='wb',mtime=0)as gz:gz.write((json.dumps(result,indent=2)+'\n').encode())
 print(json.dumps({'passed':True,'cases':len(cases),'checks_per_mode':sum(x['checks']for x in modes['release']['checks']),'power_rows':len(maxima)}))
if __name__=='__main__':main()
