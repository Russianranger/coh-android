#!/usr/bin/env python3
"""Three source-defined no-MULTITEX/no-BUMPMAPS material recipes; caller owns build lock."""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,tempfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PINS={
'fixLightingScalesOnFallback':'924d40ac6e156cc1124b700b9f660326ff85c38cc753a4d11e697de3a0179787',
'setSwappableInfo':'f6c6cbbcf68b82ba8303bb07bc5565df8790626bf2f4d95aec470ef86d321589',
'getSwapX':'6690bf981b5dee7a0f6bf6f1b94d3d3156bf07b92ad917198c3ced9647854f23',
'automatic_branch':'c216fe866b3159d9c1ea0a0ca33bdd75784f11eb13e01f9bbef83e21c177eeee'}
RECIPES=[
('shader_villain_enforcer.txt','X_Enforcer_Glove_01_Mask','Glove_V_Enforcer_01','Swappable','5d21944687e7110da7b827030823cc498558b979aa455ac57a6842b16c52bea0'),
('shader_villain_male_robot.txt','X_FullHelm_Robot_01','Face_V_Helmet_Robotic_01','Face_V_Helmet_Robotic_01_dual','9cb947157af15444bf6892703276135d180c985efffeb553f55bc5f2f12e26ed'),
('shader_villain_gear_pads.txt','X_Gear_Pads','spadr_v_Gears_01','spadr_v_Gears_01_Mask','9c111bcd8114c3f718d9f3b7365c2ef50dfe146780be9847ca7a160a4cdf7d61')]
def raw(path):
 return subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT).replace(b'\r\n',b'\n').decode('latin1')
def pin(name,text,expected=None):
 if hashlib.sha256(text.encode()).hexdigest()!=(expected or PINS[name]):raise ValueError('Original source changed: '+name)
 return text
def extract(text,name):
 match=re.search(r'\b'+re.escape(name)+r'\s*\([^;]*?\)\s*\{',text,re.S)
 if not match:raise ValueError('Original function missing: '+name)
 start=text.rfind('\n',0,match.start())+1;depth=1;cursor=text.index('{',match.start())+1
 while depth:
  depth+=(text[cursor]=='{')-(text[cursor]=='}');cursor+=1
 return pin(name,text[start:cursor])
def oracle():
 tex=raw('upstream/ouroboros/Game/src/render/tex.c');render=raw('upstream/ouroboros/Game/src/render/rendermodel.c')
 functions=[extract(tex,'fixLightingScalesOnFallback'),extract(tex,'setSwappableInfo'),extract(render,'getSwapX')]
 start=tex.index('                // Auto-fallback mode');start=tex.index('                if (texopt->model_flags & OBJ_FANCYWATER)',start);end=tex.index('                fixLightingScalesOnFallback(bind);',start)
 branch=pin('automatic_branch',tex[start:end]);fixtures=[]
 for file,name,base,dual,expected in RECIPES:
  text=raw('upstream/i24/data/tricks/v_shaders/villains/male/'+file);match=re.search(r'^Texture\s+'+re.escape(name)+r'\s*$',text,re.M|re.I)
  if not match:raise ValueError('Source TexOpt missing: '+name)
  finish=re.search(r'^End\s*$',text[match.end():],re.M);block=pin(name,text[match.start():match.end()+finish.end()],expected);fields={}
  for line in block.splitlines()[1:-1]:
   words=line.split('//',1)[0].strip().split()
   if words:fields[words[0].casefold()]=words[1:]
  assert fields['base1']==[base] and fields['dualcolor1']==[dual]
  assert fields['base1scale']==fields['dualcolor1scale']==['1','1']
  assert fields['base1scroll']==fields['dualcolor1scroll']==['0','0']
  assert 'fallback' not in fields and 'ambientscale' not in fields and 'diffusescale' not in fields
  fixtures.append('{'+json.dumps(base)+','+json.dumps(dual)+'}')
 pre=r'''#include "coh_appearance_material.h"
#include <assert.h>
#include <stdbool.h>
#include <string.h>
#include <strings.h>
typedef float F32;
#define INLINEDBG
#define xcase break;case
#define xdefault break;default
#define assertmsg(x,msg) assert(x)
#define stricmp strcasecmp
enum {BLENDMODE_BUMPMAP_MULTIPLY=1,BLENDMODE_MULTIPLY,BLENDMODE_COLORBLEND_DUAL,BLENDMODE_ADDGLOW,BLENDMODE_ALPHADETAIL,BLENDMODE_SUNFLARE,BLENDMODE_BUMPMAP_COLORBLEND_DUAL,BLENDMODE_MULTI,BLENDMODE_MODULATE,BLENDMODE_WATER};
enum {BLEND_BASE1,BLEND_MULTIPLY1,BLEND_DUALCOLOR1,BLEND_ADDGLOW1,BLEND_BUMPMAP1,BLEND_COUNT};
enum {TEXLAYER_BASE=0,TEXLAYER_GENERIC=1,TEXLAYER_BUMPMAP1=2,TEXLAYER_MAX_LAYERS=3};
enum {TEXOPT_TREAT_AS_MULTITEX=1,TEXOPT_OLDTINT=2,GFXF_MULTITEX=1,GFXF_BUMPMAPS=2,OBJ_FANCYWATER=1,TEX_REPLACEABLE=1,BMB_NV1XWORLD=1};
typedef struct {const char *name;unsigned flags;} BasicTexture;
typedef struct {int shader,blend_bits;} BlendModeType;
typedef struct {float ambientScaleTrick[3],diffuseScaleTrick[3],ambientScale[3],diffuseScale[3];int multiply1Reflect;} ScrollsScales;
typedef struct {unsigned flags,model_flags;int swappable[BLEND_COUNT];const char *blend_names[BLEND_COUNT];ScrollsScales scrollsScales;} TexOpt;
typedef struct {BlendModeType bind_blend_mode;TexOpt *texopt;ScrollsScales *scrollsScales;int tex_swappable[TEXLAYER_MAX_LAYERS];BasicTexture *tex_layers[TEXLAYER_MAX_LAYERS];} TexBind;
typedef struct {BasicTexture *generic;} TextureOverride;
static struct {unsigned features;} rdr_caps;
static BasicTexture white={"none",0},black={"black",0};static BasicTexture *white_tex=&white,*black_tex=&black;
static BasicTexture objects[8];static unsigned object_count;
static BasicTexture *lookup(const char *name){
 if(!name||!strcasecmp(name,"none")||!strcasecmp(name,"Swappable"))return white_tex;
 assert(object_count<8);objects[object_count]=(BasicTexture){name,0};return &objects[object_count++];
}
static BasicTexture *texFindVerify(const char *name,BasicTexture *fallback,const char *field,const char *file,const char *trick){(void)field;(void)file;(void)trick;return name?lookup(name):fallback;}
static BlendModeType BlendMode(int shader,int bits){return (BlendModeType){shader,bits};}
static int texLayerIndexToBlendIndex(int layer){static const int index[]={BLEND_BASE1,BLEND_DUALCOLOR1,BLEND_BUMPMAP1};assert(layer>=0&&layer<3);return index[layer];}
static void scaleVec3(const float in[3],float factor,float out[3]){for(unsigned i=0;i<3;i++)out[i]=in[i]*factor;}
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-variable"
#pragma GCC diagnostic ignored "-Wswitch-unreachable"
'''
 code=pre+'\n'.join(functions)+'\n#pragma GCC diagnostic pop\n'
 code+='static const char *const source_leaves[][2]={'+','.join(fixtures)+'};\n'
 code+=r'''void source_material_recipe(unsigned recipe,const char *primary,const char *secondary,CohAppearanceMaterialRecipe *out){
 assert(recipe<=3);object_count=0;rdr_caps.features=0;
 TexBind storage={0},*bind=&storage;TexOpt option={0},*texopt=&option;
 bind->bind_blend_mode=BlendMode(BLENDMODE_COLORBLEND_DUAL,0);
 for(unsigned i=0;i<3;i++){option.scrollsScales.ambientScaleTrick[i]=1.f;option.scrollsScales.diffuseScaleTrick[i]=1.f;option.scrollsScales.ambientScale[i]=1.f;option.scrollsScales.diffuseScale[i]=1.f;}
 bind->scrollsScales=&option.scrollsScales;
 if(recipe){
  bind->texopt=texopt;texopt->flags=TEXOPT_TREAT_AS_MULTITEX;
  texopt->blend_names[BLEND_BASE1]=source_leaves[recipe-1][0];texopt->blend_names[BLEND_DUALCOLOR1]=source_leaves[recipe-1][1];
  texopt->swappable[BLEND_DUALCOLOR1]=!strcasecmp(texopt->blend_names[BLEND_DUALCOLOR1],"Swappable");
  bind->tex_layers[TEXLAYER_BASE]=lookup(texopt->blend_names[BLEND_BASE1]);
  int scale1=BLEND_MULTIPLY1;const char *trickFileName="source TexOpt",*trickName="bounded profile";
'''+branch+r'''
  (void)scale1;fixLightingScalesOnFallback(bind);setSwappableInfo(bind,texopt);
 }else{
  bind->tex_layers[TEXLAYER_BASE]=lookup(primary);bind->tex_layers[TEXLAYER_GENERIC]=white_tex;setSwappableInfo(bind,NULL);
 }
 TextureOverride swaps={lookup(secondary)};BasicTexture *generic=getSwapX(TEXLAYER_GENERIC,&swaps,bind->tex_layers[TEXLAYER_GENERIC],0,bind);
 CohAppearanceMaterialRecipe result={0};strcpy(result.basic[0],bind->tex_layers[TEXLAYER_BASE]->name);strcpy(result.basic[1],generic->name);
 result.automatic_fallback=!!recipe;result.generic_swappable=(unsigned)bind->tex_swappable[TEXLAYER_GENERIC];
 result.ambient_scale=bind->scrollsScales->ambientScale[0];result.diffuse_scale=bind->scrollsScales->diffuseScale[0];*out=result;
}
'''
 return code
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--mode',choices=['release','asan','ubsan','all'],default='all');args=parser.parse_args()
 modes=['release','asan','ubsan'] if args.mode=='all' else [args.mode];results={}
 with tempfile.TemporaryDirectory(prefix='coh-huge-materials-') as temporary:
  work=Path(temporary);source=work/'original-materials.c';source.write_text(oracle())
  for mode in modes:
   flags=['-O2'] if mode=='release' else ['-O1','-g','-fno-omit-frame-pointer','-fsanitize='+('address' if mode=='asan' else 'undefined')]
   binary=work/mode
   subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-fno-fast-math','-fno-pie','-no-pie','-I'+str(HERE),*flags,str(HERE/'coh_appearance_material.c'),str(HERE/'test_huge_materials.c'),str(source),'-lm','-o',str(binary)],check=True)
   env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
   results[mode]=json.loads(subprocess.check_output([str(binary)],env=env,text=True))
 print(json.dumps({'source_texopts':3,'unchanged_original_helpers':3,'source_hash_guards':True,'runs':results}))
if __name__=='__main__':main()
