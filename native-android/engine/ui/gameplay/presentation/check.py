#!/usr/bin/env python3
"""Scoped offline presentation/source policy qualification; never live combat."""
import argparse
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
HERE=Path(__file__).resolve().parent
UI=HERE.parent.parent
SOURCES=[HERE/'coh_presentation.c',UI/'coh_ui.c',UI/'coh_hud.c',HERE.parent/'coh_hud_axis_navigation.c']
STRICT=['-std=c11','-Wall','-Wextra','-Werror','-Wpedantic']
def run(args,**kw):
 p=subprocess.run([str(a) for a in args],text=True,capture_output=True,**kw)
 if p.returncode:raise RuntimeError(f'{args}\n{p.stdout}\n{p.stderr}')
 return p.stdout

def extract(text,signature):
 start=text.index(signature);brace=text.index('{',start);depth=0
 for i in range(brace,len(text)):
  depth+=(text[i]=='{')-(text[i]=='}')
  if not depth:return text[start:i+1]
 raise ValueError('Unclosed source function')

def source_check(root,temp):
 pins=json.loads((HERE/'source-pins.json').read_text())
 for name,sha in pins['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,'Original source hash differs: '+name
 source=(root/'Game/src/player/playerState.c').read_text()
 shim='''#include <stdio.h>
#include <stdbool.h>
#include <stdint.h>
typedef uint32_t U32;
typedef struct {int db_id,svr_idx,erOwner,erCreator;} Entity;
#define FLOATER_MAX_STRING_LEN 128
#define MAX_FLOAT_DMG_TIME 40
#define kFloaterStyle_Damage 0
static Entity player={1,1,0,0};
static unsigned color;
static Entity *playerPtr(void){return &player;}
static int entity_TargetIsInVisionPhase(Entity *a,Entity *b){(void)a;(void)b;return 1;}
static Entity *erGetEnt(int owner){return owner?&player:NULL;}
static void addFloatingInfo(int n,char *text,U32 fg,U32 bg,U32 border,float scale,int time,float delay,int style,float *loc){
 (void)n;(void)text;(void)bg;(void)border;(void)scale;(void)time;(void)delay;(void)style;(void)loc;color=fg;
}
'''+extract(source,'void addFloatingDamage(')+'''
unsigned original(int damage,int self,int owned,int absorb){
 Entity victim={self?1:2,2,0,0},damager={owned?1:3,3,0,0};
 addFloatingDamage(&victim,&damager,damage,"Miss",NULL,absorb);return color;
}
'''
 src=temp/'original.c';src.write_text(shim);lib=temp/'original.so';run(['gcc',*STRICT,'-shared','-fPIC','-O2',src,'-o',lib])
 actual=temp/'presentation.so';run(['gcc',*STRICT,'-shared','-fPIC','-O2',*SOURCES,'-lm','-o',actual])
 oracle=C.CDLL(str(lib));native=C.CDLL(str(actual));oracle.original.argtypes=[C.c_int]*4;oracle.original.restype=C.c_uint
 native.coh_presentation_damage_color.argtypes=[C.c_int]*4;native.coh_presentation_damage_color.restype=C.c_uint
 count=0
 for damage in (-1000000000,-12345,-12,-1,0,1,12,12345,1000000000):
  for self in (0,1):
   for owned in (0,1):
    for absorb in (0,1):
     assert oracle.original(damage,self,owned,absorb)==native.coh_presentation_damage_color(damage,self,owned,absorb)
     count+=1
 # Pin the original mission/contact default and completed color fields, not a
 # claim of pixel-identical layouts or complete legacy SMF/mission behavior.
 for file,expected in [('Game/src/UI/uiMission.c',['0x00deffff','0x00ff44ff']),('Game/src/UI/uiContact.c',['0xffffffff','0x00ff33ff'])]:
  text=(root/file).read_text();colors=re.findall(r'/\* piColor\s*\*/\s*\(int \*\)(0x[0-9a-f]+)',text)
  assert colors[:2]==expected
 return {'status':'passed','compiled_original_damage_color_comparisons':count,'source_color_fields_checked':4,
         'hashes':pins,'scope':'Original damage/healing RGB decision body and mission/contact text colors only. New layout, timing and mock state are explicit mobile policy.'}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--ndk',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True)
 p.add_argument('--output',type=Path,required=True);p.add_argument('--sanitize',action='store_true');a=p.parse_args()
 with tempfile.TemporaryDirectory(prefix='coh-presentation-') as d:
  temp=Path(d);binary=temp/'test';run(['gcc',*STRICT,'-O2',*SOURCES,HERE/'test_presentation.c','-lm','-o',binary])
  report={'module':'Offline presentation panel and combat visual cues','implemented':True,'implementation_start_commit':'58caf1d4ab3b39757190f194100ccbc697d57857',
          'host':json.loads(run([binary])),'source':source_check(a.source_root,temp),'sanitizers':'not run',
          'android_emulator':'not run by this isolated worker; integrated support build qualification required',
          'physical_thor':'not run','live_combat':'not implemented or qualified','assets':json.loads((HERE/'asset-gaps.json').read_text())}
  if a.sanitize:
   sanitized=temp/'sanitized';run(['gcc',*STRICT,'-O1','-g','-fno-omit-frame-pointer','-fsanitize=address,undefined',*SOURCES,HERE/'test_presentation.c','-lm','-o',sanitized])
   report['sanitizer_tests']=json.loads(run([sanitized],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:abort_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')))
   report['sanitizers']='ASan + UBSan passed; fixed arenas, LSan disabled'
  toolchain=a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin';report['android_builds']={}
  for target in ('aarch64','x86_64'):
   lib=temp/('libpresentation-'+target+'.so');cc=toolchain/(target+'-linux-android26-clang')
   run([cc,*STRICT,'-O2','-shared','-fPIC',*SOURCES,'-lm','-Wl,--no-undefined','-o',lib])
   imports=run([toolchain/'llvm-nm','-u',lib]);assert not re.search(r'\b(malloc|calloc|realloc|free)(?:@|$)',imports,re.M)
   report['android_builds'][target]={'status':'shared library linked','api':26,'bytes':lib.stat().st_size,'sha256':hashlib.sha256(lib.read_bytes()).hexdigest(),'executed':False}
  axis=temp/'axis.json';args=['python',HERE.parent/'axis_check.py','--ndk',a.ndk,'--output',axis]
  if a.sanitize:args+=['--sanitize']
  run(args);report['reused_axis_regression']=json.loads(axis.read_text())
  report['no_direct_allocator_imports']=True
  report['source_hashes']={str(f.relative_to(UI)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [*SOURCES,HERE/'coh_presentation.h',HERE/'test_presentation.c',HERE/'check.py',HERE.parent/'coh_hud_axis_navigation.h']}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'output':str(a.output),'host':report['host'],'source_comparisons':report['source']['compiled_original_damage_color_comparisons'],'sanitizers':report['sanitizers'],'android':report['android_builds']}))
if __name__=='__main__':main()
