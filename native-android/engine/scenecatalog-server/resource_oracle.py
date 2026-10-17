#!/usr/bin/env python3
"""Bounded read-only loaded resource observer. No server/capture/asset mutation."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,struct,subprocess,tempfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd,**kw):
 r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=180,**kw)
 if r.returncode:raise RuntimeError(r.stdout+r.stderr)
 return r.stdout

def prepare(root,work):
 spec=importlib.util.spec_from_file_location('resource_snapshot',HERE/'snapshot_oracle.py');snap=importlib.util.module_from_spec(spec);spec.loader.exec_module(snap)
 path,pins=snap.prepare(root,work);code=path.read_text()
 assert code.count('typedef struct { char *name; } Model;')==1
 code=code.replace('typedef struct { char *name; } Model;',(HERE/'resource_fixture_types.h').read_text())
 assert code.count('int main(int argc, char **argv)')==1
 code=code.replace('int main(int argc, char **argv)','static int snapshot_prior_fixture_main(int argc, char **argv)')
 spec=importlib.util.spec_from_file_location('resource_groups',root/'native-android/engine/replication/groups_oracle.py');oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
 anim=oracle.read_source(root,'Common/seq/anim.c')
 functions=['compareModelNamesAndLengths','compareModelBSearch','compareModelBSearchCallback','modelFind']
 blocks={name:oracle.extract(anim,name) for name in functions}
 pre='''
#include <strings.h>
#define __cdecl
#define strnicmp strncasecmp
#define min(a,b) ((a)<(b)?(a):(b))
#define GEO_USE_MASK 12
#define PERFINFO_AUTO_START(a,b) ((void)0)
#define PERFINFO_AUTO_STOP() ((void)0)
#define OUTPUT_VERBOSE 0
#define writeConsole(...) ((void)0)
typedef struct {const char*name;int namelen;} ModelSearchData;
static GeoLoadData*useThisGeoLoadData;
'''
 code+='\n'+pre+(HERE/'test_resources.c').read_text().replace('RESOURCE_ORIGINAL_MODEL_FIND','\n'.join(blocks.values()))
 path.write_text(code)
 source_paths=['Common/seq/anim.c','Common/seq/anim.h','Common/seq/tricks.h','Common/group/group.c','Common/group/groupfilelib.c','Game/src/render/thread/rt_model_cache.h']
 # Record exact LF-normalized original source identity; unchanged function bodies
 # are extracted directly, not reimplemented. No original ABI layout is inferred.
 pins['resource_source_sha256_lf']={p:hashlib.sha256(oracle.read_source(root,p).encode()).hexdigest() for p in source_paths}
 pins['unchanged_model_lookup_functions']={k:hashlib.sha256(v.encode()).hexdigest() for k,v in blocks.items()}
 expected=json.loads((HERE/'resource-source-pins.json').read_text())
 assert expected['sha256_lf']==pins['resource_source_sha256_lf']
 assert expected['functions_sha256_lf']==pins['unchanged_model_lookup_functions']
 return path,pins

def decode(data):
 if len(data)>64*1024**2:raise ValueError('stream bound')
 at=0;records=[]
 while at<len(data):
  if len(records)>=65536+64:raise ValueError('record count bound')
  if len(data)-at<192:raise ValueError('truncated header')
  h=struct.unpack_from('<46I',data,at+8)
  if data[at:at+8]!=b'COHRES01' or h[0:2]!=(1,192):raise ValueError('record envelope')
  size=h[2]
  if size<192 or size>128*1024 or size>len(data)-at:raise ValueError('record size')
  end=at+size;pos=at+192;strings=[]
  for off in (48,52,56,60,64,124):
   n=struct.unpack_from('<I',data,at+off)[0]
   if not n:strings.append(None);continue
   if n<2 or n>256 or n>end-pos or data[pos+n-1]!=0:raise ValueError('string extent')
   value=data[pos:pos+n-1]
   if any(x<32 or x>126 for x in value):raise ValueError('string contents')
   strings.append(value.decode('ascii'));pos+=n
  textures=[]
  count=struct.unpack_from('<I',data,at+96)[0]
  if count>256:raise ValueError('texture count bound')
  for _ in range(count):
   if end-pos<12:raise ValueError('texture header')
   tid,tris,n=struct.unpack_from('<III',data,pos);pos+=12
   if n<2 or n>256 or n>end-pos or data[pos+n-1]!=0:raise ValueError('texture extent')
   value=data[pos:pos+n-1]
   if any(x<32 or x>126 for x in value):raise ValueError('texture contents')
   textures.append((tid,tris,value.decode('ascii')));pos+=n
  if pos!=end:raise ValueError('record end')
  records.append({'owner_kind':h[4],'file':h[5],'slot':h[6],'original_id':h[7],'model_present':h[8],
   'capabilities':h[9],'row':h[15],'format':h[16],'strings':strings,'textures':textures})
  at=end
 return records

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--fixtures-output',type=Path);p.add_argument('--sanitize',action='store_true');a=p.parse_args()
 local=[HERE/n for n in ('source_resources.inc','resource_fixture_types.h','test_resources.c','resource_oracle.py','source_snapshot.inc','snapshot_oracle.py','resource-source-pins.json')]
 hashes={str(x.relative_to(ROOT)):sha(x) for x in local}
 with tempfile.TemporaryDirectory(prefix='coh-resource-observer-') as temp:
  work=Path(temp);source,pins=prepare(a.source_root.resolve(),work)
  modes=[('release',['-O0'])]
  if a.sanitize:modes += [('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
  checks={};binaries={};fixtures={}
  for mode,flags in modes:
   binary=work/mode
   run([os.environ.get('CC','cc'),'-std=c99','-w','-fno-strict-aliasing','-I'+str(HERE),'-I'+str(a.source_root/'native-android/include'),*flags,source,'-lm','-lz','-o',binary])
   env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1'}
   checks[mode]=json.loads(run([binary,work],env=env));binaries[mode]=sha(binary)
   raw=(work/'resources.cohres').read_bytes();records=decode(raw);fixtures[mode]=hashlib.sha256(raw).hexdigest()
   model=[r for r in records if r['model_present']]
   assert len(model)==1 and model[0]['row']==1 and model[0]['format']==8
   assert model[0]['strings'][1:5]==['piece__Stone','object_library/resources/exact_loaded.geo','Stone','tricks/exact.txt']
   assert model[0]['textures']==[(1,1,'stone_normal'),(0,2,'stone_base')]
   assert sum(r['owner_kind']==2 for r in records)==2
   assert all(r['capabilities']==1 for r in records)
   # Every truncation of a valid stream except an exact record boundary refuses.
   ends=set();at=0
   while at<len(raw):at+=struct.unpack_from('<I',raw,at+16)[0];ends.add(at)
   for cut in range(1,len(raw)):
    try:decode(raw[:cut]);assert cut in ends
    except ValueError:assert cut not in ends
  assert len(set(fixtures.values()))==1 and all(r==checks['release'] for r in checks.values())
  assert hashes=={str(x.relative_to(ROOT)):sha(x) for x in local}
  if a.fixtures_output:
   a.fixtures_output.mkdir(parents=True,exist_ok=True);(a.fixtures_output/'resources.cohres').write_bytes(raw)
  receipt={'schema':'coh-read-only-resource-source-observer-v1','passed':True,'native_source_checks':checks,'binary_sha256':binaries,'fixture_sha256':fixtures['release'],'fixture_records':len(records),'source_provenance':pins,'source_sha256':hashes,'unchanged_original_model_lookup':True,'source_observer_sanitized':a.sanitize,'fixture_only':True,'actual_runtime_executed':False,'capture_started':False,'client_materials_complete':False,'client_lods_complete':False,'assets_admitted':False,'world_authority':False,'leak_sanitizer':False}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':True,'output':str(a.output),'checks':checks['release']['checks'],'records':len(records)}))
if __name__=='__main__':main()
