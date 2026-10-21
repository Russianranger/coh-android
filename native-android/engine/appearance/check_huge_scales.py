#!/usr/bin/env python3
"""Original Appearance union/scaleHero mapping into the existing Huge sampler."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
NATIVE=HERE.parents[1]
ROOT=HERE.parents[2]
def raw(name):
 return subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT).replace(b'\r\n',b'\n').decode('latin1')
def extract(text,name):
 match=re.search(r'\b'+re.escape(name)+r'\s*\([^;]*?\)\s*\{',text,re.S)
 if not match:raise ValueError(name+' source function missing')
 start=text.rfind('\n',0,match.start())+1;depth=1;cursor=text.index('{',match.start())+1
 while depth:
  depth+=(text[cursor]=='{')-(text[cursor]=='}');cursor+=1
 return text[start:cursor]
def oracle():
 costume=raw('upstream/ouroboros/Common/entity/costume.h');start=costume.index('    union',costume.index('//    float fBodyScales'))
 end=costume.index('    int compressedScales',start);union=costume[start:end].strip()
 hero=extract(raw('upstream/ouroboros/Game/src/entity/costume_client.c'),'scaleHero')
 source=raw('upstream/i24/data/ent_types/huge.txt');fields={}
 for line in source.splitlines():
  words=line.split('#')[0].split()
  if len(words)>1:fields[words[0].lower()]=words[1:]
 def values(name):return ','.join(str(float(x))+'f' for x in fields[name])
 assert values('geomscale')=='1.0f,1.0f,1.0f'
 # Compile the actual source Appearance union and unchanged scaleHero. The
 # temporary Entity/Seq/menus are thin storage shims; SHOW_TEMPLATE is inactive.
 return '''#include <string.h>
 typedef float F32;typedef float Vec3[3];
 #define MAX_BODY_SCALES 30
 #define NUM_3D_BODY_SCALES 7
 typedef struct {'''+union+'''} Appearance;
 typedef struct {float geom[3];} Entity;
 enum {SHOW_TEMPLATE=1};static struct {int game_mode;} game_state;
 static Entity*playerPtr(void){return 0;}static Entity*playerPtrForShell(int x){(void)x;return 0;}
 static void entCostumeShare(Entity*a,Entity*b){(void)a;(void)b;}
 static void changeScale(Entity*e,float*v){memcpy(e->geom,v,12);}
 '''+hero+'''
 void source_scale_header(const float input[30],float output[53]){
 Appearance a;Entity e={{0}};memcpy(a.fScales,input,120);scaleHero(&e,a.fScale);
 const float type[18]={'''+','.join(values(key) for key in ('shoulderscaleskinny','shoulderscalefat','hipscale','neckscale','headscalemin','headscalemax'))+'''};
 memcpy(output,e.geom,12);output[3]=a.fBoneScale;output[4]=a.fShoulderScale;output[5]=a.fChestScale;output[6]=a.fWaistScale;output[7]=a.fHipScale;output[8]=a.fLegScale;output[9]=a.fArmScale;memcpy(output+10,a.fHeadScales,12);output[13]='''+values('legscaleratio')+''';memcpy(output+14,type,72);memcpy(output+32,a.f3DScales,84);
 }
 '''
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--mode',choices=['release','asan','ubsan','all'],default='all');args=parser.parse_args()
 source_bones=raw('upstream/ouroboros/Common/seq/bones.h').split('typedef enum BoneId',1)[1].split('BONEID_COUNT',1)[0]
 names=re.findall(r'\bBONEID_([A-Z0-9_]+)\s*,',source_bones)
 assert names==re.findall('"([A-Z0-9_]+)"',(HERE/'huge_bone_names.inc').read_text())
 results={}
 with tempfile.TemporaryDirectory(prefix='coh-huge-scales-') as temporary:
  work=Path(temporary);(work/'oracle.c').write_text(oracle())
  sources=[HERE/'coh_appearance_scales.c',HERE/'test_huge_scales.c',NATIVE/'character/coh_character.c',NATIVE/'engine/assets/coh_asset_geo.c',NATIVE/'src/coh_assets.c',work/'oracle.c']
  modes=['release','asan','ubsan'] if args.mode=='all' else [args.mode]
  for mode in modes:
   flags=['-O2'] if mode=='release' else ['-O1','-g','-fno-omit-frame-pointer','-fsanitize='+('address' if mode=='asan' else 'undefined')]
   exe=work/mode
   subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-fno-fast-math','-I'+str(NATIVE/'include'),*flags,*map(str,sources),'-lz','-lm','-o',str(exe)],check=True)
   env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
   results[mode]=json.loads(subprocess.check_output([str(exe)],env=env,text=True))
 print(json.dumps(results))
if __name__=='__main__':main()
