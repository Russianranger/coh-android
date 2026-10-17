#!/usr/bin/env python3
"""Compare CLIENT LOD alpha projection with unchanged original modelCalcAlpha."""
import argparse,hashlib,json,os,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def function(text):
 start=text.index('static int modelCalcAlpha(');end=text.index('\nstatic F32 g_glowBrightScale',start)
 return text[start:end].strip()+'\n'
def run(cmd,**kw):
 p=subprocess.run(list(map(str,cmd)),capture_output=True,timeout=120,**kw)
 if p.returncode:raise ValueError(p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
 return p.stdout

def oracle(original):
 prefix='''#include "coh_wr_lod.h"
#include <math.h>
typedef float F32;typedef unsigned char U8;typedef int VisType;
#define VIS_DRAWALL 1
#define TRICK_NOFOG (1<<19)
#define TRICK_NIGHTLIGHT (1<<10)
#define TRICK2_HASADDGLOW (1<<0)
#define TRICK2_STIPPLE1 (1<<2)
#define TRICK2_STIPPLE2 (1<<3)
typedef struct{unsigned flags1,flags2;} Trick;
typedef struct{Trick*trick;} Model;
typedef struct{float lod_near,lod_nearfade,lod_far,lod_farfade,radius;int parent_fade,vis_window;Model*model;} GroupDef;
typedef struct{float lod_near,lod_nearfade,lod_far,lod_farfade;} AutoLOD;
typedef struct{int lod_fadenode,no_fog_clip;float node_radius,alpha;Trick*tricks;} DrawParams;
static struct{float lod_scale,lod_fade_range;} game_state;
static struct{float fog_far_dist;int fog_clip;} group_draw;
static struct{U8 lamp_alpha_byte;} g_sun;
'''
 wrapper='''
CohWrLodProjection original_project(const CohWrLodInput*q){
 unsigned f=q->flags;Trick mt={(f&32?TRICK_NOFOG:0)|(f&64?TRICK_NIGHTLIGHT:0),f&128?TRICK2_HASADDGLOW:0};
 Trick dt={0,(f&512?TRICK2_STIPPLE1:0)|(f&1024?TRICK2_STIPPLE2:0)};Model model={f&16?&mt:0};
 GroupDef def={q->definition_lod[0],q->definition_lod[1],q->definition_lod[2],q->definition_lod[3],q->definition_radius,!!(f&4),!!(f&8),&model};
 AutoLOD lod={q->selected_lod[0],q->selected_lod[1],q->selected_lod[2],q->selected_lod[3]};
 DrawParams draw={q->lod_fadenode,!!(f&2048),q->node_radius,q->draw_alpha,f&256?&dt:0};
 game_state.lod_scale=q->client_lod_scale;game_state.lod_fade_range=q->client_fade_range;group_draw.fog_far_dist=q->fog_far;group_draw.fog_clip=!!(f&4096);g_sun.lamp_alpha_byte=q->lamp_alpha;
 int fog=0;U8 stipple=0;int alpha=(f&2?original_debug:original_final)(&def,q->distance,q->scale,&draw,f&1?&lod:0,&fog,f&8192?VIS_DRAWALL:0,&stipple);
 return (CohWrLodProjection){alpha,fog,stipple};}
'''
 return prefix+original.replace('modelCalcAlpha(','original_debug(')+'\n#define FINAL 1\n'+original.replace('modelCalcAlpha(','original_final(')+wrapper

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('Fresh output required')
 pins=json.loads((HERE/'lod-source-pins.json').read_text())
 for path,h in pins.items():
  if sha(ROOT/path)!=h:raise ValueError('Original source pin differs '+path)
 source=ROOT/'upstream/ouroboros/Game/src/graphics/groupdrawinline.c';original=function(source.read_text())
 deps=[HERE/'coh_wr_lod.c',HERE/'coh_wr_lod.h',HERE/'tests/test_lod.c',HERE/'check_lod.py',HERE/'lod-source-pins.json',HERE.parent/'coh_contracts.h',*[ROOT/x for x in pins]]
 hashes={str(x.relative_to(ROOT)):sha(x) for x in deps};results={}
 with tempfile.TemporaryDirectory(prefix='coh-lod-') as directory:
  t=Path(directory);(t/'original.c').write_text(oracle(original))
  flags=['-std=c11','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-I',HERE]
  for mode,extra in [('release',['-O2']),('address',['-O1','-fsanitize=address','-no-pie']),('undefined',['-O1','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   run(['cc',*flags,*extra,HERE/'tests/test_lod.c',HERE/'coh_wr_lod.c',t/'original.c','-lm','-o',t/mode]);results[mode]=json.loads(run([t/mode],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
  mutations=[('near_boundary','if(dist<near)','if(dist<=near)'),('nightlight_addglow','!bit(q->flags,COH_WR_LOD_ADDGLOW)','bit(q->flags,COH_WR_LOD_ADDGLOW)'),('stipple_threshold_precision','q->draw_alpha<0.0001','q->draw_alpha<0.0001f')]
  for name,before,after in mutations:
   production=(HERE/'coh_wr_lod.c').read_text();assert before in production;(t/(name+'.c')).write_text(production.replace(before,after))
   run(['cc',*flags,'-O2',HERE/'tests/test_lod.c',t/(name+'.c'),t/'original.c','-lm','-o',t/name]);m=subprocess.run([str(t/name)],capture_output=True,timeout=60)
   if m.returncode==0:raise ValueError('Mutation escaped '+name)
 if hashes!={str(x.relative_to(ROOT)):sha(x) for x in deps}:raise ValueError('Source changed')
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps({'passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip(),'source_inputs_unchanged':True,'source_sha256':hashes,'unchanged_original_function_sha256_lf':hashlib.sha256(original.encode()).hexdigest(),'modes':results,'production_mutations_rejected':[x[0] for x in mutations],'client_semantic_authority':False,'android_execution':False,'world_authority':False},indent=2)+'\n');print(json.dumps({'passed':True,'modes':results}))
if __name__=='__main__':main()
