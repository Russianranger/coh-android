#!/usr/bin/env python3
"""Run original/patched distance checks and actual observer under ASan/UBSan."""
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
s = (a.source / rel).read_text()
original = (ROOT / 'upstream/ouroboros' / rel).read_text()
start = s.index('static void armportWorldDef(')
end = s.index('\n#define ARMPORT_WORLD_ACTIVE', start)
observer = s[start:end]
start = s.index('static INLINEDBG F32 closeEnough(')
end = s.index('static INLINEDBG int sphereInFrustum', start)
changed = s[start:end]
start = original.index('static INLINEDBG F32 closeEnough(')
end = original.index('static INLINEDBG int sphereInFrustum', start)
old = original[start:end].replace('closeEnough(', 'originalCloseEnough(')
program = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#define COH_ARMPORT_REFERENCE_I686 1
#include "armport_world_trace.h"
#define INLINEDBG
#define CALL_INC
#define SQR(x) ((x)*(x))
#define PARENT_FADE 1
#define HAS_FOG 2
#define VIS_DOORFRAME 4
#define CHILD_PARENT_FADE 8
#define TRICK_EDITORVISIBLE 16
#define TRICK_HIDE 32
#define _snprintf snprintf
typedef float F32;
typedef F32 Vec3[3];
typedef struct { unsigned flags1; } Trick;
typedef struct { Trick *trick; } Model;
typedef struct { const char *name; Model *model; int count; unsigned is_tray,
 has_fog, has_sound, has_light, editor_visible_only, has_cubemap; F32 lod_scale; } GroupDef;
typedef struct { GroupDef *def; unsigned flags_cache; F32 vis_dist_scaled_cache, radius; } GroupEnt;
typedef struct { int lod_fadenode; Vec3 node_mid; } DrawParams;
ArmPortWorldTrace armport_world_trace;
static unsigned records, calc_calls;
static const char *expected_name = "name=\"geo_unsafe__name\"";
static F32 lengthVec3Squared(const Vec3 v) { return v[0]*v[0]+v[1]*v[1]+v[2]*v[2]; }
static F32 calculateVisDist(GroupEnt *e) { ++calc_calls; return e->vis_dist_scaled_cache; }
static void armportZoneTrace(const char *stage, const char *detail) {
 assert(!strcmp(stage,"world.def")); assert(strlen(detail)<768);
 assert(!strchr(detail,'\n')); assert(!strchr(detail,'\r'));
 assert(strstr(detail,expected_name));
 assert(strstr(detail,"trick_editor=1 trick_hide=1")); ++records;
}
''' + observer + r'''
#define ARMPORT_WORLD_ACTIVE (armport_world_trace.active)
#define ARMPORT_WORLD_DEF(kind,ent,mid,dm,d,dv,lim,lv) armportWorldDef(kind,ent,mid,dm,d,dv,lim,lv)
''' + old + changed + r'''
int main(void) {
 Trick trick = {48}; Model model = {&trick};
 GroupDef def = {"geo\nunsafe\"\\name", &model, 3, 0, 0, 1, 0, 0, 0, 1};
 GroupEnt ent = {&def, 0, 10, 2}; DrawParams draw = {0,{3,4,0}};
 Vec3 mid = {0,0,0}; int on, f, fade, value, i, kind;
 /* Disabled observer must not inspect caller storage. */
 armportWorldDef(0, NULL, NULL, NULL, 0, 0, 0, 0); assert(!records);
 for(on=0;on<=1;++on) for(f=0;f<16;++f) for(fade=0;fade<3;++fade) for(value=0;value<4;++value) {
  F32 before,after; unsigned calls;
  memset(&armport_world_trace,0,sizeof(armport_world_trace)); armport_world_trace.active=on;
  ent.flags_cache=f; draw.lod_fadenode=fade; mid[0]=value==3?100:(F32)value;
  calc_calls=0; before=originalCloseEnough(&draw,mid,&ent); calls=calc_calls;
  calc_calls=0; after=closeEnough(&draw,mid,&ent,1);
  assert(memcmp(&before,&after,sizeof(F32))==0); assert(calls==calc_calls);
 }
 memset(&armport_world_trace,0,sizeof(armport_world_trace)); armport_world_trace.active=1; records=0;
 for(i=0;i<100;++i) for(kind=0;kind<4;++kind) armportWorldDef(kind,&ent,mid,mid,4,1,10,1);
 assert(records==16);
 for(kind=0;kind<4;++kind) assert(armport_world_trace.detail_samples[kind]==4);
 memset(&armport_world_trace,0,sizeof(armport_world_trace)); armport_world_trace.active=1;
 records=0; ent.flags_cache=0; draw.lod_fadenode=0; mid[0]=100;
 assert(closeEnough(&draw,mid,&ent,0)==0); assert(!records);
 assert(closeEnough(&draw,mid,&ent,1)==0); assert(records==1);
 assert(ent.def==&def && ent.flags_cache==0 && ent.vis_dist_scaled_cache==10 && ent.radius==2);
 /* Null and oversized names remain bounded; no formatting injection. */
 memset(&armport_world_trace,0,sizeof(armport_world_trace)); armport_world_trace.active=1;
 def.name=NULL; expected_name="name=\"\""; armportWorldDef(0,&ent,mid,mid,0,0,0,0);
 { char long_name[2048], expected[104];
   memset(long_name,'A',sizeof(long_name)); long_name[sizeof(long_name)-1]=0;
   memcpy(expected,"name=\"",6); memset(expected+6,'A',96); expected[102]='"'; expected[103]=0;
   def.name=long_name; expected_name=expected; armportWorldDef(0,&ent,mid,mid,0,0,0,0);
 }
 puts("384 original/patched distance cases agree; original calculateVisDist call counts agree; off/secondary path inert; 4 records per reason; sanitized bounded names");
 return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp); (root/'test.c').write_text(program)
    subprocess.run([os.environ.get('CC','cc'), '-std=c11','-Wall','-Wextra','-Werror',
                    '-fsanitize=address,undefined','-fno-omit-frame-pointer',
                    '-I',str(a.source/'Game/src/graphics'),str(root/'test.c'),'-o',str(root/'test')],check=True)
    subprocess.run([str(root/'test')],check=True)
