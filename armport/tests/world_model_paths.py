#!/usr/bin/env python3
"""Exercise original/patched traversal prefix and model counters with fixtures."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True)
a = p.parse_args()
rel = 'Game/src/graphics/groupdrawinline.c'

def prefix(source, name):
    start = source.index('int drawDefInternal(')
    end = source.index('    // common rejections are above', start)
    return source[start:end].replace('drawDefInternal(', name + '(') + 'return 77;\n}\n'

program = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#define COH_ARMPORT_REFERENCE_I686 1
#include "armport_world_trace.h"
#define ONLY_EDITORVISIBLE 64
#define CALL_INIT
#define ARMPORT_WORLD_ACTIVE armport_world_trace.active
#define ARMPORT_WORLD_DEF(...) ((void)0)
typedef float F32;
typedef float Vec3[3];
typedef float Mat4[4][3];
typedef float (*Mat4Ptr)[3];
typedef int VisType;
typedef struct { void *model; } GroupDef;
typedef struct { GroupDef *def; unsigned flags_cache; Vec3 mid_cache; } GroupEnt;
typedef struct { int unused; } DefTracker, DrawParams;
static struct { int see_everything; } group_draw;
ArmPortWorldTrace armport_world_trace;
static F32 distance;
static int clip, transform_calls, distance_calls, frustum_calls;
static void mulVecMat4(Vec3 src,Mat4 mat,Vec3 dst) { (void)mat; memcpy(dst,src,sizeof(Vec3));++transform_calls; }
static F32 closeEnough(DrawParams *draw,Vec3 mid,GroupEnt *ent,...) { (void)draw;(void)mid;(void)ent;++distance_calls;return distance; }
static int sphereInFrustum(Vec3 mid,GroupEnt *ent) { (void)mid;(void)ent;++frustum_calls;return clip; }
''' + prefix((ROOT/'upstream/ouroboros'/rel).read_text(), 'before') + prefix((a.source/rel).read_text(), 'after') + r'''
int main(void) {
 int active, model, path, see, expected, old_calls[3], got;
 GroupDef def={0};GroupEnt ent={&def,0,{1,2,3}},saved;
 DrawParams draw={0};Mat4 matrix={{0}};
 for(active=0;active<2;++active) for(model=0;model<2;++model)
 for(path=0;path<4;++path) for(see=0;see<2;++see) {
  unsigned observed=(unsigned)(active && model), editor=(unsigned)(path==0 && !see);
  def.model=model?&def:NULL;ent.flags_cache=path==0?ONLY_EDITORVISIBLE:0;
  distance=path==1?0:1;clip=path==2?0:1;group_draw.see_everything=see;saved=ent;
  memset(&armport_world_trace,0,sizeof(armport_world_trace));armport_world_trace.active=active;
  transform_calls=distance_calls=frustum_calls=0;expected=before(&ent,matrix,NULL,0,&draw,0);
  old_calls[0]=transform_calls;old_calls[1]=distance_calls;old_calls[2]=frustum_calls;
  transform_calls=distance_calls=frustum_calls=0;got=after(&ent,matrix,NULL,0,&draw,0);
  assert(got==expected && old_calls[0]==transform_calls && old_calls[1]==distance_calls && old_calls[2]==frustum_calls);
  assert(!memcmp(&saved,&ent,sizeof(ent)));
  assert(armport_world_trace.model_visits==observed);
  assert(armport_world_trace.editor_model_skip==observed*editor);
  assert(armport_world_trace.distance_model_skip==observed*(path==1));
  assert(armport_world_trace.frustum_model_skip==observed*(path==2));
  assert(armport_world_trace.postchecks_model==observed*(expected==77));
 }
 puts("32 original/patched traversal-prefix paths agree: transform/distance/frustum call counts and input unchanged; model/nonmodel and disabled counters, editor/distance/frustum/pass categories correct");
 return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root/'test.c').write_text(program)
    subprocess.run([os.environ.get('CC','cc'), '-std=c11', '-Wall', '-Wextra',
                    '-Wno-unused-variable', '-Wno-unused-parameter', '-Werror',
                    '-fsanitize=address,undefined','-fno-omit-frame-pointer',
                    '-I',str(a.source/'Game/src/graphics'),str(root/'test.c'),'-o',str(root/'test')],check=True)
    subprocess.run([str(root/'test')],check=True)
