#!/usr/bin/env python3
"""Compare bounded native automatic LOD construction with original CLIENT source."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
RESOURCE_SHA='8500764939215b576e5ff88056ec85b475785038e09600019846ff5a06eb1cd6'
LEDGER_SHA='46df6643795c3d06aa5b52b3c2fadeed1eac00a3693f33ac611bb5d990109e2a'
SOURCE_SHA='f34c46abac3e6e95bd5829d1d72a203756a7764872f6a9483c4377a05a546722'
LEDGER=ROOT/'native-android/engine/scenecatalog/evidence/root-model-texture-partitions-38994607354.json'
AUTO=ROOT/'upstream/ouroboros/Common/seq/AutoLOD.c'
OBSERVER=ROOT/'native-android/engine/scenecatalog-server/resource_oracle.py'
DEPS=[HERE/x for x in ['check_lod_autodata.py','coh_wr_lod.c','coh_wr_lod.h','tests/test_lod_autodata.c']]+[AUTO,ROOT/'upstream/ouroboros/Common/seq/AutoLOD.h',OBSERVER,LEDGER,ROOT/'native-android/engine/scenecatalog-server/source_resources.inc',HERE.parent/'coh_contracts.h']
def sha(body):return hashlib.sha256(body).hexdigest()
def run(command,**kw):
 p=subprocess.run(list(map(str,command)),capture_output=True,timeout=120,**kw)
 if p.returncode:raise ValueError(p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
 return p.stdout

def original_function(text):
 start=text.index('void lodinfoFillInAutoData(')
 opening=text.index('{',start)
 level=1
 for i in range(opening+1,len(text)):
  if text[i]=='{':level+=1
  if text[i]=='}':
   level-=1
   if not level:return text[start:i+1]+'\n'
 raise ValueError('unterminated original function')

def oracle(original):
 return r'''#include "coh_wr_lod.h"
#include <assert.h>
#include <string.h>
typedef float F32;
typedef struct {float max_error,lod_near,lod_far,lod_nearfade,lod_farfade;unsigned flags;} AutoLOD;
typedef struct {struct{unsigned is_automatic;}bits;AutoLOD**lods;} ModelLODInfo;
typedef struct {float shadow_dist,lod_near,lod_far,lod_nearfade,lod_farfade;} TrickInfo;
#define LOD_ERROR_TRICOUNT (1<<1)
#define LOD_USEFALLBACKMATERIAL (1<<7)
#define HIGH_POLY_CUTOFF2 2000
#define LOW_LOD_CUTOFF 200
#define DIST_OFFSET 125
static AutoLOD arena[4],*pointers[4];
static unsigned allocated,count,report_calls;
static TrickInfo trick;
static void trickSetExistenceErrorReporting(int value){assert(value==(int)(report_calls%2));report_calls++;}
static TrickInfo*trickFromObjectName(const char*name,const char*path){assert(name&&path);return &trick;}
static int observed_size(AutoLOD***array){assert(!*array||*array==pointers);return(int)count;}
static AutoLOD*allocAutoLOD(void){assert(allocated<4);return &arena[allocated++];}
static void observed_push(AutoLOD***array,AutoLOD*row){assert(count<4);*array=pointers;pointers[count++]=row;}
#define eaSize(array) observed_size(array)
#define eaPush(array,row) observed_push(array,row)
'''+original+r'''
CohWrAutoLodProjection original_autodata(const CohWrAutoLodInput*q){
 memset(arena,0,sizeof(arena));memset(pointers,0,sizeof(pointers));allocated=count=report_calls=0;
 trick=(TrickInfo){q->shadow_distance,q->trick_lod[0],q->trick_lod[2],q->trick_lod[1],q->trick_lod[3]};
 ModelLODInfo info={0};float distances[3];memcpy(distances,q->reduction_distances,sizeof(distances));
 char name[]="source_numeric_projection",geo[]="object_library/source.geo";
 lodinfoFillInAutoData(&info,name,geo,q->model_radius,(int)q->source_triangle_count,q->has_reduction_distances?distances:0);
 assert(report_calls==2&&info.bits.is_automatic&&count&&count==allocated);
 CohWrAutoLodProjection out={0};out.count=count;
 for(unsigned i=0;i<count;i++){AutoLOD*r=pointers[i];out.rows[i]=(CohWrAutoLodRow){r->max_error,r->lod_near,r->lod_nearfade,r->lod_far,r->lod_farfade,r->flags};}
 return out;
}
'''

def fixtures(body,ledger,observer):
 parsed=observer.decode(body)
 offsets=[]
 at=0
 while at<len(body):
  offsets.append(at)
  at+=struct.unpack_from('<I',body,at+16)[0]
 if at!=len(body) or len(parsed)!=len(offsets):raise ValueError('resource record offsets')
 rows=ledger['rows']
 if ledger['resources_sha256']!=RESOURCE_SHA or ledger['model_owner_rows']!=3083 or len(rows)!=3083:raise ValueError('root ledger')
 seen=set();lines=['static const CohWrAutoLodInput authentic_inputs[]={']
 for row in rows:
  ordinal=row['source_ordinal']
  if type(ordinal)!=int or ordinal<0 or ordinal>=len(parsed) or ordinal in seen:raise ValueError('source ordinal')
  seen.add(ordinal)
  observed=parsed[ordinal]
  if not observed['model_present'] or observed['strings'][1]!=row['model'] or observed['strings'][2]!=row['source_geo_name'] or observed['textures']!=[tuple(x) for x in row['textures']]:raise ValueError('exact root model observation')
  pos=offsets[ordinal]
  radius=struct.unpack_from('<f',body,pos+164)[0]
  near,far,nearfade,farfade,scale,shadow=struct.unpack_from('<6f',body,pos+168)
  triangles=struct.unpack_from('<I',body,pos+92)[0]
  def f(value):return value.hex()+'f'
  # Reduction distances were NOT captured. This tests the explicitly absent
  # array SOURCE projection; it does not infer the actual CLIENT array is absent.
  lines.append('{'+','.join([f(radius),f(shadow),'{'+','.join(map(f,[near,nearfade,far,farfade]))+'}','{0,0,0}',str(triangles),'0'])+'},')
 lines.append('};')
 return '\n'.join(lines)+'\n'

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--resources',type=Path,required=True)
 p.add_argument('--output',type=Path,required=True)
 a=p.parse_args()
 if a.output.exists():raise ValueError('fresh output required')
 before={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in DEPS}
 if sha(AUTO.read_bytes())!=SOURCE_SHA or sha(LEDGER.read_bytes())!=LEDGER_SHA:raise ValueError('original source/ledger identity differs')
 with a.resources.open('rb') as stream:body=stream.read(12596423)
 if len(body)!=12596422 or sha(body)!=RESOURCE_SHA:raise ValueError('exact retained resource capture differs')
 code=OBSERVER.read_bytes()
 if sha(code)!=before[str(OBSERVER.relative_to(ROOT))]:raise ValueError('observer changed before execution')
 spec=importlib.util.spec_from_file_location('lod_source_resources',OBSERVER)
 observer=importlib.util.module_from_spec(spec)
 exec(compile(code,str(OBSERVER),'exec'),observer.__dict__)
 fixture=fixtures(body,json.loads(LEDGER.read_bytes()),observer)
 original=original_function(AUTO.read_text())
 generated=oracle(original)
 results={};binary_hashes={};mutations=[]
 flags=['-std=c11','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-I',HERE]
 with tempfile.TemporaryDirectory(prefix='coh-lod-autodata-') as directory:
  temp=Path(directory)
  (temp/'original.c').write_text(generated)
  (temp/'lod-autodata-fixtures.h').write_text(fixture)
  for mode,extra in [('release',['-O2']),('address',['-O1','-fsanitize=address','-no-pie']),('undefined',['-O1','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   production=temp/(mode+'-production.o');source=temp/(mode+'-original.o');tests=temp/(mode+'-tests.o')
   run(['cc',*flags,*extra,'-c',HERE/'coh_wr_lod.c','-o',production])
   run(['cc',*flags,*extra,'-Wno-unused-parameter','-c',temp/'original.c','-o',source])
   run(['cc',*flags,*extra,'-I',temp,'-c',HERE/'tests/test_lod_autodata.c','-o',tests])
   binary=temp/mode
   run(['cc',*extra,production,source,tests,'-lm','-o',binary])
   results[mode]=json.loads(run([binary],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
   binary_hashes[mode]=sha(binary.read_bytes())
  changes=[('radius_boundary','q->model_radius>200','q->model_radius>=200'),('previous_triangle_count','triangle_count>200','q->source_triangle_count>200'),('strict_near_threshold','distance>previous->lod_near+125','distance>=previous->lod_near+125'),('far_trick_suppresses_default_fade','!farfade&&!lod_fromtrick','!farfade'),('first_quarter_high_poly','error<=0.5f||triangle_count<=2000','error<=0.75f||triangle_count<=2000')]
  production=(HERE/'coh_wr_lod.c').read_text()
  for name,old,new in changes:
   if production.count(old)!=1:raise ValueError('mutation marker differs '+name)
   changed=temp/(name+'.c');changed.write_text(production.replace(old,new))
   obj=temp/(name+'.o');binary=temp/name
   run(['cc',*flags,'-Wno-unused-variable','-O2','-c',changed,'-o',obj])
   run(['cc',obj,temp/'release-original.o',temp/'release-tests.o','-lm','-o',binary])
   result=subprocess.run([binary],capture_output=True,timeout=30)
   if not result.returncode:raise ValueError('production mutation escaped '+name)
   mutations.append(name)
 if before!={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in DEPS} or sha(a.resources.read_bytes())!=RESOURCE_SHA:raise ValueError('source/input readmission differs')
 proof={'passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip(),'source_sha256':before,'resources_sha256':RESOURCE_SHA,'root_ledger_sha256':LEDGER_SHA,'unchanged_original_function_sha256_lf':sha(original.encode()),'generated_original_sha256':sha(generated.encode()),'generated_fixture_sha256':sha(fixture.encode()),'modes':results,'binary_sha256':binary_hashes,'production_mutations_refused':mutations,'actual_root_numeric_observations':3083,'actual_CLIENT_reduction_arrays_captured':False,'authentic_field_no_array_source_projection':True,'synthetic_reduction_threshold_controls':True,'original_allocator_earray_lookup_observers':True,'full_LOD_dictionary_selection':False,'reduced_mesh_selected':False,'current_CLIENT_generation':False,'material_authority':False,'world_authority':False,'android_execution':False}
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps(proof,indent=2)+'\n')
 print(json.dumps({'passed':True,'modes':results,'mutations':mutations}))
if __name__=='__main__':main()
