#!/usr/bin/env python3
"""Bounded complete raw power cache streaming; no source CRC/runtime association."""
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
 if LOCKED.get(p)!=hashlib.sha256(body).hexdigest():raise ValueError('helper not admitted '+str(p))
 m=types.ModuleType(n);m.__file__=str(p);exec(compile(body,str(p),'exec'),m.__dict__);return m
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=240,**kw)
 if p.returncode:raise RuntimeError(str(args)+'\n'+p.stdout[-6000:]+p.stderr[-6000:])
 return p.stdout
def loader_controls(work):
 p=work/'stale.py';p.write_text('value=1\n');py_compile.compile(str(p),doraise=True);st=p.stat();p.write_text('value=2\n');os.utime(p,ns=(st.st_atime_ns,st.st_mtime_ns));LOCKED[p.resolve()]=sha(p);assert module('stream_stale',p).value==2;p.write_text('value=3\n')
 try:module('stream_changed',p)
 except ValueError:pass
 else:raise ValueError('changed helper executed')
 LOCKED.pop(p.resolve());return {'stale_pyc_ignored':True,'changed_source_refused_before_execution':True}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--cache-zip',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 if not __debug__:raise ValueError('assertions required')
 helpers=[HERE/p for p in ('power_stream_schema.py','power_record_oracle.py','classes_oracle.py','origins_oracle.py','../costume-inputs/oracle.py','../costume-inputs/source-pins.json','../costume-inputs/coh_costume_inputs.h','../costume-tree/crc_provider.py','../stash32/oracle.py','../stash32/source-pins.json')];LOCKED.update({p.resolve():sha(p)for p in helpers});stream=module('power_stream_schema',helpers[0]);original=module('power_record',helpers[1]);original.module=module;classes=module('power_classes',helpers[2]);origin=module('power_origins',helpers[3]);small=module('power_small',helpers[4]);crc=module('power_crc',helpers[7]);stash=module('power_stash',helpers[8]);sourcepaths=[ROOT/'upstream/ouroboros'/p for p in set(stream.PATHS+original.EXTRA+classes.EXTRA+origin.EXTRA+small.PATHS+crc.PATHS+stash.PATHS)];sources=[HERE/'coh_power_stream.c',HERE/'../stash32/coh_stash32.c'];paths=set(helpers+sourcepaths+sources+[HERE/p for p in ('coh_power_stream.h','power_stream_schema.inc','test_power_stream.c','check_power_stream.py','POWER_STREAM.md')]);pending=[*sources,HERE/'coh_power_stream.h',HERE/'test_power_stream.c',helpers[6]];seen=set()
 while pending:
  p=pending.pop().resolve()
  if p in seen:continue
  seen.add(p);paths.add(p)
  for name in re.findall(r'^#include "([^"]+)"',p.read_text(),re.M):
   q=(p.parent/name).resolve()
   if q.is_file():pending.append(q)
 manifest_path=HERE/'../entities/qualification/costume-export-20261017/client-cache-manifest.json';paths.add(manifest_path);hashes={str(p.resolve().relative_to(ROOT)):sha(p)for p in sorted(paths)}
 if a.cache_zip.stat().st_size!=27071659 or sha(a.cache_zip)!='5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051':raise ValueError('exact donor ZIP required')
 pin=json.loads(manifest_path.read_text())['files']['data/bin/powers.bin'];assert pin['bytes']==62047164 and pin['sha256']=='25641e747c60e066016fcc7d2ce0a2e72f57d7d3953f7b1ff4b18b69e2d49c6d'
 texts={p:read(ROOT/'upstream/ouroboros'/p).decode().replace('\r\n','\n')for p in stream.PATHS};tables,tablepins=stream.schema(texts);descriptor=['/* Complete source-ordered persisted power table kinds; no schema CRC claim. */','typedef struct {unsigned char kind,sub;} PowerField;']
 for t,rows in enumerate(tables):descriptor.append('static const PowerField power_fields_%s[]={%s};'%(t,','.join('{%s,%s}'%(r['kind'],r['sub'])for r in rows)))
 descriptor+=['static const PowerField *const power_fields[]={'+','.join('power_fields_'+str(t)for t in range(5))+'};','static const unsigned power_field_counts[]={'+','.join(str(len(t))for t in tables)+'};'];assert(HERE/'power_stream_schema.inc').read_text()=='\n'.join(descriptor)+'\n';assert list(map(len,tables))==[180,63,3,4,47]
 checks={};binaries={};stack=[]
 with tempfile.TemporaryDirectory(prefix='coh-power-stream-')as tmp:
  work=Path(tmp);controls=loader_controls(work);originalroot=work/'source'
  for p in sourcepaths:
   q=originalroot/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(read(p))
  with zipfile.ZipFile(a.cache_zip)as z:
   info=z.getinfo('data/bin/powers.bin');assert info.file_size==pin['bytes']
   with z.open(info)as f:actual=stream.inspect(f,pin['bytes'],tables)
   assert actual['exact_sha256']==pin['sha256']
   rawpath=work/'powers.bin'
   with z.open(info)as f,rawpath.open('xb')as dst:
    while chunk:=f.read(65536):dst.write(chunk)
  ow=work/'original';ow.mkdir();lib,proof=original.build(originalroot,ow);output=C.create_string_buffer(65536);meta=(C.c_uint*16)();record_sha=hashlib.sha256();first=None;crcvalues=[];expected=work/'expected.bin'
  with rawpath.open('rb')as f,expected.open('xb')as exp:
   for row in actual['rows']:
    f.seek(row['begin']);raw=f.read(row['end']-row['begin']);n=lib.original_power_record(raw,len(raw),output,meta);wire=C.string_at(output,n);assert n==len(raw)and raw==wire and meta[0]==meta[1]==row['stored_crc'];record_sha.update(wire);crcvalues.append(meta[0]);first=first or raw
    n=struct.unpack_from('<H',raw,4)[0];full=row['begin']+6;at=4+(n+2+3)//4*4+4;n2=struct.unpack_from('<H',raw,at)[0];at+=(n2+2+3)//4*4;n3=struct.unpack_from('<H',raw,at)[0];short=row['begin']+at+2;exp.write(struct.pack('<5I2H',row['begin'],row['end'],full,short,meta[0],n,n3))
   sw=work/'stash';sw.mkdir();slib,sproof=stash.build(originalroot,sw);keys=(C.c_uint*len(crcvalues))(*crcvalues);slots=(C.c_uint*65536)();stats=(C.c_uint*8)();slib.original_build(keys,len(keys),32768,slots,stats);assert list(stats[:5])==[32768,20241,0,0,0];positions={v:i+1 for i,v in enumerate(crcvalues)};expectedslots=[positions.get(v,0)for v in slots];exp.write(struct.pack('<65536I',*expectedslots))
  variants=work/'variants.bin';variantproof=[]
  def pascal(s):return struct.pack('<H',len(s))+s+bytes((4-(len(s)+2)%4)%4)
  with variants.open('xb')as f:
   f.write(struct.pack('<I',6))
   for scenario in range(6):
    n=lib.original_power_variant(first,len(first),output,meta,scenario if scenario<5 else 0);raw=C.string_at(output,n);assert n<=65536;wire=b'CrypticS'+struct.pack('<I',actual['schema_crc'])+pascal(b'Parse6')+pascal(b'Files1')+struct.pack('<II',4,0)+struct.pack('<II',4+len(raw)*(2 if scenario==5 else 1),2 if scenario==5 else 1)+raw*(2 if scenario==5 else 1);digest=hashlib.sha256(wire).digest();f.write(struct.pack('<I',len(wire))+digest+wire);variantproof.append({'scenario':scenario,'bytes':len(wire),'sha256':digest.hex(),'original_stored_crc':meta[0],'original_computed_crc':meta[1],'power_vars':meta[5],'container_profile':'two identical original-written records'if scenario==5 else'one original-written record','native_expected_status':'COH_STATE'if scenario==3 else'COH_OK'})
  lib.original_power_records_close()
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else[]):
   exe=work/mode;run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-Wno-deprecated-declarations',*flags,*sources,HERE/'test_power_stream.c','-lcrypto','-o',exe]);checks[mode]=json.loads(run([exe,rawpath,expected,variants],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(exe)
  cpp=work/'header.cpp';cpp.write_text('#include "coh_power_stream.h"\nint main(){return coh_power_stream_find_crc(nullptr,0,nullptr)==COH_INVALID?0:1;}\n');objects=[]
  for i,s in enumerate(sources):obj=work/('cpp'+str(i)+'.o');run(['cc','-std=c11','-O2','-c',s,'-o',obj]);objects.append(obj)
  run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-o',work/'cpp']);run([work/'cpp'])
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    loc,n,kind=line.split('\t')
    if any(str(s)+':'in loc for s in sources):stack.append({'function':loc,'bytes':int(n),'kind':kind})
  assert stack and all(x['kind']in('static','dynamic,bounded')for x in stack)and sum(x['bytes']*4 for x in stack)<16384;expected_sha=sha(expected);variant_sha=sha(variants)
  ldd=run(['ldd',work/'release']);crypto=re.search(r'libcrypto[^ ]* => ([^ ]+)',ldd).group(1);dependency={'path':crypto,'sha256':sha(Path(crypto)),'version':run(['openssl','version']).strip(),'external_library_stack_sanitizer_closure':False}
 if hashes!={str(p.resolve().relative_to(ROOT)):sha(p)for p in sorted(paths)}:raise ValueError('source changed')
 assert all(x==checks['release']for x in checks.values())
 result={'schema':'coh-raw-power-stream-index-v1','passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).strip(),'source_sha256':hashes,'exact_input_bytes':pin['bytes'],'exact_input_sha256':pin['sha256'],'observed_schema_crc':hex(actual['schema_crc']),'original_record_codec':proof,'original_int_stash':sproof,'actual_records':actual['records_by_table'],'original_roundtrips':len(actual['rows']),'individual_crc_matches':len(actual['rows']),'concatenated_original_records_sha256':record_sha.hexdigest(),'original_stash_statistics':list(stats[:5]),'variants':variantproof,'expected_fixture_sha256':expected_sha,'variant_fixture_sha256':variant_sha,'source_table_sha256_lf':tablepins,'checks':checks,'binary_sha256':binaries,'native_stack':stack,'host_digest_dependency':dependency,'helper_loader_controls':controls,'cpp_link_passed':True,'original_binary_enum_defaults_shells':True,'source_schema_crc_recomputed':False,'full_original_dictionary_constructor_executed':False,'historical_cache_branch_admitted':False,'runtime_generation':False,'actor_authority':False,'leak_sanitizer_executed':False,'leak_sanitizer_environment':'ptrace disallows /proc task inspection; host buffers explicitly freed; ASan enabled without LSAN','original_oracle_sanitized':False,'original_win32_abi_executed':False,'android_executed':False}
 with a.output.open('xb')as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0)as z:z.write((json.dumps(result,indent=2)+'\n').encode())
 print(json.dumps({'passed':True,'original_records':len(actual['rows']),'checks':checks}))
if __name__=='__main__':main()
