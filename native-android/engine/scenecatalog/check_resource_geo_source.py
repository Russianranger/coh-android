#!/usr/bin/env python3
"""Original readModel v8 oracle plus real zero-draw source header controls."""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,tempfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];ENGINE=HERE.parent
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--geo',type=Path,required=True);p.add_argument('--sha256',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd,**kw):
 x=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=180,**kw)
 if x.returncode:raise RuntimeError(x.stdout+x.stderr)
 return x.stdout
if a.output.exists() or sha(a.geo)!=a.sha256:raise ValueError('New output/pinned body required')
original=ROOT/'upstream/ouroboros/Common/seq/anim.c';text=original.read_text();start=text.index('static int readModel(');at=text.index('{',start);depth=1;end=at+1
while depth:
 if text[end]=='{':depth+=1
 elif text[end]=='}':depth-=1
 end+=1
function=text[start:end]
shim=r'''#include "coh_resource_geo_source.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CLIENT 0
typedef uint8_t U8;typedef uint32_t U32;typedef int16_t S16;typedef float F32;typedef float Vec3[3];
typedef struct {uint32_t cell;Vec3 pos;F32 size,inv_size;int tag,num_bits;} PolyGrid;
typedef struct {int packsize;U32 unpacksize,data;} PackData;
typedef struct {U32 id,count;} TexID;
typedef struct {PackData tris,verts,norms,sts,sts3,weights,matidxs,grid,reductions,reflection_quads;} Pack;
typedef struct {U32 flags;F32 radius;int tex_count;S16 id;U8 loadstate;void *boneinfo,*trick,*ctris,*tags,*api,*extra,*gld;int vert_count,tri_count,reflection_quad_count;TexID *tex_idx;PolyGrid grid;char *name;Vec3 scale,min,max;Pack pack;} Model;
typedef Model ModelFormatOnDisk_v2;
#define copyVec3(a,b) memcpy(b,a,sizeof(Vec3))
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wpointer-sign"
'''+function+r'''
#pragma GCC diagnostic pop
unsigned original_read_model_compare(CohBytes row,const CohAssetGeo *g,uint32_t index,const CohAssetGeoModel *actual){
 (void)index;assert(sizeof(PackData)==12&&sizeof(PolyGrid)==32);Model m={0};int consumed=readModel(&m,(char*)row.data,8,(U8*)g->model_names.data,(U8*)g->material_ids.data);unsigned checks=0;
 #define SAME(x) do{checks++;if(!(x)){fprintf(stderr,"original readModel comparison %u failed\n",checks);exit(2);}}while(0)
 SAME(consumed==(int)row.size);SAME(!strcmp(m.name,actual->name));SAME(m.vert_count==(int)actual->vertex_count);SAME(m.tri_count==(int)actual->triangle_count);SAME(m.tex_count==(int)actual->material_count);SAME((uintptr_t)m.tex_idx-(uintptr_t)g->material_ids.data==actual->material_offset);SAME((uintptr_t)m.boneinfo==actual->bone_info_offset);SAME(!memcmp(m.scale,actual->scale,12));
 PackData *p[]={&m.pack.tris,&m.pack.verts,&m.pack.norms,&m.pack.sts,&m.pack.sts3,&m.pack.weights,&m.pack.matidxs,&m.pack.grid,&m.pack.reductions,&m.pack.reflection_quads};for(uint32_t k=0;k<actual->pack_count;k++){SAME((uint32_t)p[k]->packsize==actual->packs[k].packed_bytes);SAME(p[k]->unpacksize==actual->packs[k].unpacked_bytes);SAME(p[k]->data==actual->packs[k].offset);}return checks;
}
'''
sources=[HERE/'coh_resource_geo_source.c',ENGINE/'assets/coh_asset_geo.c',ENGINE/'assets/coh_asset_loader.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c',HERE/'tests/test_resource_geo_source.c']
deps=sources+[HERE/'coh_resource_geo_source.h',ENGINE/'assets/coh_asset_geo.h',ENGINE/'assets/coh_asset_loader.h',ENGINE/'coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',original,ROOT/'upstream/ouroboros/Common/seq/anim.h',ROOT/'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/components/gridpoly.h',Path(__file__)]
pins={str(p.relative_to(ROOT)):sha(p) for p in deps};modes={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
with tempfile.TemporaryDirectory(prefix='coh-original-source-zero-draw-') as tmp:
 tmp=Path(tmp);oracle=tmp/'oracle.c';oracle.write_text(shim)
 for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  binary=tmp/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-I'+str(HERE),'-I'+str(ROOT/'native-android/include'),*flags,*sources,oracle,'-lcrypto','-lz','-lm','-o',binary]);modes[mode]={'result':json.loads(run([binary,a.geo],env=env)),'binary_sha256':sha(binary)}
if any(modes[m]['result']!=modes['release']['result'] for m in modes):raise ValueError('Native mode controls differ')
if pins!={str(p.relative_to(ROOT)):sha(p) for p in deps} or sha(a.geo)!=a.sha256:raise ValueError('Inputs changed')
result={'passed':True,'source_sha256':pins,'actual_geo_sha256':a.sha256,'original_readModel_sha256_lf':hashlib.sha256(function.encode()).hexdigest(),'original_function_compiled_unchanged':True,'fixture_types':'explicit32bitPolyGrid/PackData layout shells; v8 pointer-offset copies zero-initialized in host pointers; not originalWin32ABI or v2 qualification','modes':modes,'assets_draw_ready':False,'source_generation_admitted':False,'world_authority':False,'android_executed':False,'leak_sanitizer':False}
a.output.parent.mkdir(parents=True,exist_ok=True)
with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'passed':True,'modes':modes}))
