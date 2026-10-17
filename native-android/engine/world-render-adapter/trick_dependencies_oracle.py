"""Unchanged StAnim functions and isolated original AutoLOD copy branch observers."""
from pathlib import Path

def create(root,extract,stnames,lodrows):
 base=Path(root)/'upstream/ouroboros/Common/seq';anim=(base/'animtrackanimate.c').read_text();tricks=(base/'tricks.c').read_text();lod=(base/'AutoLOD.c').read_text();types=(base/'animtrack.h').read_text();flags=(base/'tricks.h').read_text()
 load='\n'.join(line.strip().split('//')[0] for line in types.splitlines() if line.strip().startswith(('LOAD_ALL ','LOAD_ALL_SHARED ')))
 stan=next(line.split('=',1)[1].split(',')[0].strip() for line in flags.splitlines() if line.strip().startswith('TRICK2_STANIMATE '))
 setup=extract(tricks,'static void setupTrick(');part=setup[setup.index('#ifndef OFFLINE'):setup.index('\n    if (trick->group_flags')]
 branch=extract(lod,'    if (!lod_info->force_auto && !no_lod && trick && trick->auto_lod)')
 code=r'''#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include "coh_wr_trick_types_internal.h"
struct BoneAnimTrack{int id;};
typedef struct{int bone_track_count;BoneAnimTrack*bone_tracks;}SkeletonAnimTrack;
static unsigned checks,load_calls,errors,lock_calls,unlock_calls;static int expected_shared,skeleton_absent,observed_load;static char observed_key[256];
static BoneAnimTrack tracks[3];static SkeletonAnimTrack skeleton;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"failed line%d: %s\n",__LINE__,#x);abort();}}while(0)
#define STR_COMBINE_BEGIN(buf) size_t cursor=0;buf[0]=0
#define STR_COMBINE_CAT(s) do{size_t n=strlen(s);assert(n<sizeof(buf)-cursor);memcpy(buf+cursor,s,n+1);cursor+=n;}while(0)
#define STR_COMBINE_END() ((void)0)
static void Errorf(const char*fmt,...){(void)fmt;errors++;}
static SkeletonAnimTrack*animGetAnimTrack(const char*key,int type,void*p){(void)p;load_calls++;observed_load=type;assert(strlen(key)<sizeof(observed_key));strcpy(observed_key,key);if(expected_shared)assert(unlock_calls==lock_calls+1);return skeleton_absent?NULL:&skeleton;}
static void sharedHeapMemoryManagerUnlock(void){unlock_calls++;}static void sharedHeapMemoryManagerLock(void){lock_calls++;}
'''+ 'enum{'+load+'};\n#define TRICK2_STANIMATE '+stan+'\n'+extract(anim,'const BoneAnimTrack * animFindTrackInSkeleton(')+extract(anim,'int setStAnim(')+'static void original_setup_animation(TrickInfo*trick,int shared_memory){\n'+part+'}\n'
 code+=r'''typedef struct{int force_auto;struct{unsigned is_from_trick;}bits;AutoLOD**lods;}ModelLODInfo;
static unsigned eaSize(AutoLOD***p){unsigned n=0;if(*p)while((*p)[n])n++;return n;}
static void eaPush(AutoLOD***p,AutoLOD*v){unsigned n=eaSize(p);AutoLOD**a=realloc(*p,((size_t)n+2)*sizeof(*a));assert(a);a[n]=v;a[n+1]=NULL;*p=a;}
static AutoLOD*dupAutoLOD(AutoLOD*v){AutoLOD*a=malloc(sizeof(*a));assert(a);*a=*v;return a;} /* shallow host observer: no strings mutated/freed */
static void original_copy_branch(ModelLODInfo*lod_info,int no_lod,TrickInfo*trick,float lod_far,float lod_farfade){
'''+branch+'}\n'
 code+='static const char*actual_st_names[]={'+','.join(__import__('json').dumps(n) for n in stnames)+'};\n'
 for i,children in enumerate(lodrows):
  code+='static AutoLOD actual_lods_'+str(i)+'[]={\n'
  for row in children:
   value=lambda name: next(v.value for v in row if v.name==name)
   floats=[value(x).hex()+'f' for x in ['AllowedError','LodNear','LodFar','LodNearFade','LodFarFade']]
   code+='{'+','.join(floats)+','+str(value('LodFlags'))+',0,'+(__import__('json').dumps(value('ModelName').decode()) if value('ModelName') else 'NULL')+',NULL},\n'
  code+='};\n'
 code+='static struct{AutoLOD*rows;unsigned count;}actual_lod_cases[]={'+','.join('{actual_lods_'+str(i)+',sizeof(actual_lods_'+str(i)+')/sizeof(AutoLOD)}' for i in range(len(lodrows)))+'};\n'
 return code
