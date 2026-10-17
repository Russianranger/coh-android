#!/usr/bin/env python3
"""Exact donor origins Parse6+original CRC/lookup, compact native ownership."""
import argparse,ctypes as C,gzip,hashlib,importlib.util,json,os,re,struct,subprocess,tempfile,types,py_compile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def read(p):
 if str(p).startswith(str(ROOT/'upstream/ouroboros')+'/'):return subprocess.check_output(['git','-C',ROOT,'show','HEAD:'+str(p.relative_to(ROOT))])
 return p.read_bytes()
def sha(p):return hashlib.sha256(read(p)).hexdigest()
LOCKED={}
def module(n,p):
 p=p.resolve();body=p.read_bytes()
 if LOCKED.get(p)!=hashlib.sha256(body).hexdigest():raise ValueError('helper source not admitted '+str(p))
 m=types.ModuleType(n);m.__file__=str(p);exec(compile(body,str(p),'exec'),m.__dict__);return m
def loader_controls(work):
 p=work/'stale.py';p.write_text('value=1\n');py_compile.compile(str(p),doraise=True);stat=p.stat();p.write_text('value=2\n');os.utime(p,ns=(stat.st_atime_ns,stat.st_mtime_ns));LOCKED[p.resolve()]=sha(p)
 if module('origin_stale_control',p).value!=2:raise ValueError('stale PYC executed')
 p.write_text('value=3\n')
 try:module('origin_changed_control',p)
 except ValueError:pass
 else:raise ValueError('changed source executed')
 LOCKED.pop(p.resolve());return {'stale_pyc_ignored':True,'changed_source_refused_before_execution':True}
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=120,**kw)
 if p.returncode:raise RuntimeError(str(args)+'\n'+p.stdout[-6000:]+p.stderr[-6000:])
 return p.stdout
def decode(raw):
 at=0
 def word():
  nonlocal at
  v=struct.unpack_from('<I',raw,at)[0];at+=4;return v
 def string():
  nonlocal at
  n=struct.unpack_from('<H',raw,at)[0];at+=2;s=raw[at:at+n];at+=n;at+=(4-(n+2)%4)%4;return s.decode('ascii')
 assert raw[:8]==b'CrypticS';at=8;crc=word();assert string()=='Parse6'and string()=='Files1';end=at+4+struct.unpack_from('<I',raw,at)[0];word();deps=word()
 for _ in range(deps):string();word()
 assert at==end;begin=at;end=at+4+struct.unpack_from('<I',raw,at)[0];word();count=word();rows=[]
 for _ in range(count):
  rowend=at+4+struct.unpack_from('<I',raw,at)[0];word();rows.append([string()for _ in range(5)]);assert at==rowend
 assert at==end==len(raw);return {'crc':crc,'begin':begin,'dependencies':deps,'rows':rows}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 helpers=[HERE/'origins_oracle.py',HERE/'../costume-inputs/oracle.py',HERE/'../costume-inputs/source-pins.json',HERE/'../costume-inputs/coh_costume_inputs.h',HERE/'../costume-tree/crc_provider.py'];before={str(p.resolve().relative_to(ROOT)):sha(p.resolve())for p in helpers}
 LOCKED.update({p.resolve():sha(p.resolve())for p in helpers});oracle=module('origin_oracle',helpers[0]);oracle.module=module;small=module('origin_small_paths',helpers[1]);crc=module('origin_crc_paths',helpers[-1]);original=small.PATHS+oracle.EXTRA+crc.PATHS;sourcepaths=[ROOT/'upstream/ouroboros'/p for p in original];sources=[HERE/'coh_origins.c'];paths=set(helpers+sourcepaths+sources+[HERE/n for n in('coh_origins.h','test_origins.c','check_origins.py','origins.bin','villain_origins.bin','ORIGINS.md')]);pending=[HERE/'coh_origins.c',HERE/'coh_origins.h',HERE/'test_origins.c',HERE/'../costume-inputs/coh_costume_inputs.h'];seen=set()
 while pending:
  p=pending.pop().resolve()
  if p in seen:continue
  seen.add(p);paths.add(p)
  for inc in re.findall(r'^#include \"([^\"]+)\"',p.read_text(),re.M):
   q=(p.parent/inc).resolve()
   if q.is_file():pending.append(q)
 hashes={str(p.resolve().relative_to(ROOT)):sha(p.resolve())for p in sorted(paths)}
 expected={'origins.bin':(504,'ec13f45bc83815bb6d2c440380360589217919c65cc637f94959e53c5410e033'),'villain_origins.bin':(124,'2432c9d535ef7021d2c86ab9ea2e7049148304721e88163af3a3a2611bbeba3a')};cases=[];lines=[];rows=[];checks={};binaries={};stack=[]
 with tempfile.TemporaryDirectory(prefix='coh-origins-')as tmp:
  work=Path(tmp);loader=loader_controls(work);originalroot=work/'source'
  for p in sourcepaths:
   dst=originalroot/p.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(read(p))
  ow=work/'oracle';ow.mkdir();lib,proof=oracle.build(originalroot,ow);originalcrc=lib.original_origin_crc()&0xffffffff;assert originalcrc==0x6d177c17
  for name,(size,digest)in expected.items():
   raw=(HERE/name).read_bytes();assert len(raw)==size and hashlib.sha256(raw).hexdigest()==digest;initial=decode(raw);assert initial['crc']==originalcrc
   for scenario in range(7):
    out=C.create_string_buffer(65536);words=(C.c_uint*1024)();text=C.create_string_buffer(65536);n=C.c_uint();written=lib.original_origin_tree(raw,len(raw),initial['begin'],out,words,text,C.byref(n),scenario);assert written;wire=out.raw[:written];decoded=decode(wire);assert decoded['crc']==originalcrc
    if not scenario:assert raw==wire
    flattened=b''.join(s.encode()+b'\0'for row in decoded['rows']for s in row);assert flattened==text.raw[:n.value];assert words[0]==len(decoded['rows']);indices=[]
    for row in decoded['rows']:
     match=max(i for i,r in enumerate(decoded['rows'])if r[0].lower()==row[0].lower());indices.extend([match,match])
    assert list(words[1:1+len(indices)])==indices and words[1+len(indices)]==0xffffffff
    idx=len(cases);lines.append('static const uint8_t wire_'+str(idx)+'[]={'+','.join(map(str,wire))+'};');lines.append('static const uint32_t indices_'+str(idx)+'[]={'+','.join(map(str,indices or[0]))+'};');lines.append('static const char text_'+str(idx)+'[]={'+','.join(map(str,flattened or b'\0'))+'};');literals='text_'+str(idx);rows.append('{wire_'+str(idx)+',sizeof(wire_'+str(idx)+'),'+str(len(decoded['rows']))+','+str(int(scenario==5))+','+literals+',indices_'+str(idx)+'}');cases.append({'input':name,'scenario':scenario,'wire_sha256':hashlib.sha256(wire).hexdigest(),'wire_hex':wire.hex(),'projection':decoded,'reverse_indices':indices})
  fixture='\n'.join(lines)+'\nstatic const Fixture fixtures[]={'+','.join(rows)+'};\n';(work/'fixtures.h').write_text(fixture)
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else[]):
   exe=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(work),*sources,HERE/'test_origins.c','-lcrypto','-o',exe]);checks[mode]=json.loads(run([exe],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(exe)
  cpp=work/'header.cpp';cpp.write_text('#include "coh_origins.h"\nint main(){return coh_origins_find(nullptr,CohBytes{nullptr,0},nullptr)==COH_INVALID?0:1;}\n');obj=work/'origins.o';run(['cc','-std=c99','-O2','-c',sources[0],'-o',obj]);run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,obj,'-o',work/'cpp']);run([work/'cpp'])
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    location,n,kind=line.split('\t')
    if str(sources[0])+':'in location:stack.append({'function':location,'bytes':int(n),'kind':kind})
  assert stack and all(x['kind']in('static','dynamic,bounded')for x in stack)and sum(x['bytes']for x in stack)<8192
 if before!={str(p.resolve().relative_to(ROOT)):sha(p.resolve())for p in helpers}or hashes!={str(p.resolve().relative_to(ROOT)):sha(p.resolve())for p in sorted(paths)}:raise ValueError('source/helper changed')
 assert all(c==checks['release']for c in checks.values())
 result={'schema':'coh-original-origins-compact-v1','passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).strip(),'source_sha256':hashes,'original':proof,'helper_loader_controls':loader,'original_schema_crc':originalcrc,'original_cases':cases,'checks':checks,'binary_sha256':binaries,'native_stack':stack,'fixture_header_sha256':hashlib.sha256(fixture.encode()).hexdigest(),'cpp_link_passed':True,'owned_strings':True,'runtime_shared_cache_generation':False,'serveronly_cache_association':False,'actor_authority':False,'original_oracle_sanitized':False,'android_executed':False}
 with a.output.open('xb')as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0)as z:z.write((json.dumps(result,indent=2)+'\n').encode())
 print(json.dumps({'passed':True,'checks':checks,'crc':hex(originalcrc)}))
if __name__=='__main__':main()
